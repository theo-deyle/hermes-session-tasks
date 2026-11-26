"""The own-job pass rule: add a batch of steps, check them off, end with every item checked.

The test loads `tests/live/own_job/analyze.py` from its file path. No gateway runs here.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from session_tasks.db import ConnFactory
from session_tasks.model import AddItem, SetChecked
from session_tasks.store import BoardStore

ANALYZE = Path(__file__).resolve().parent / "live" / "own_job" / "analyze.py"

Event = dict[str, Any]


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("own_job_analyze", ANALYZE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analyze = load_module()


def add_ops(*texts: str) -> list[dict[str, object]]:
    return [{"op": "add", "text": text} for text in texts]


def check_ops(*ids: int, checked: bool = True) -> list[dict[str, object]]:
    return [{"op": "set_checked", "item_id": item_id, "checked": checked} for item_id in ids]


def direct(ops: list[dict[str, object]], call_id: str) -> Event:
    return {
        "type": "tool_use",
        "name": "board_edit",
        "tool_call_id": call_id,
        "input": {"ops": ops},
    }


def bridged(tool: str, arguments: object, call_id: str) -> Event:
    return {
        "type": "tool_use",
        "name": "tool_call",
        "tool_call_id": call_id,
        "input": {"name": tool, "arguments": arguments},
    }


def bridged_edit(ops: list[dict[str, object]], call_id: str) -> Event:
    return bridged("board_edit", json.dumps({"ops": ops, "base_rev": 1}), call_id)


def board_of(*checked: bool) -> dict[str, object]:
    items = [
        {"id": index, "text": f"step {index}", "checked": int(flag), "updated_by": "agent"}
        for index, flag in enumerate(checked, start=1)
    ]
    return {"root": "s1", "rev": 2, "items": items}


GOOD_EVENTS = [
    direct(add_ops("one", "two", "three"), "c1"),
    bridged_edit(check_ops(1, 2, 3), "c2"),
]


def test_a_run_that_adds_then_checks_every_step_passes() -> None:
    verdict = analyze.evaluate(GOOD_EVENTS, board_of(True, True, True))

    assert verdict["pass"] is True
    assert verdict["reasons"] == []
    assert verdict["board_edit_calls"] == 2
    assert verdict["add_batches"] == 1


def test_a_run_with_no_board_edit_fails() -> None:
    events = [{"type": "tool_use", "name": "terminal", "tool_call_id": "c1", "input": {}}]

    verdict = analyze.evaluate(events, board_of())

    assert verdict["pass"] is False
    assert verdict["board_edit_calls"] == 0
    assert any("add" in reason for reason in verdict["reasons"])


def test_a_run_that_adds_but_never_checks_fails() -> None:
    events = [direct(add_ops("one", "two"), "c1")]

    verdict = analyze.evaluate(events, board_of(False, False))

    assert verdict["pass"] is False
    assert any("check" in reason for reason in verdict["reasons"])


def test_a_run_with_one_unchecked_item_fails() -> None:
    verdict = analyze.evaluate(GOOD_EVENTS, board_of(True, True, False))

    assert verdict["pass"] is False
    assert any("unchecked" in reason for reason in verdict["reasons"])


def test_a_run_with_one_item_fails() -> None:
    events = [direct(add_ops("one"), "c1"), bridged_edit(check_ops(1), "c2")]

    verdict = analyze.evaluate(events, board_of(True))

    assert verdict["pass"] is False
    assert any("2 or more items" in reason for reason in verdict["reasons"])


def test_a_run_with_no_board_fails() -> None:
    verdict = analyze.evaluate(GOOD_EVENTS, None)

    assert verdict["pass"] is False
    assert verdict["reasons"]


def test_a_check_before_the_add_batch_does_not_count() -> None:
    events = [
        direct(check_ops(1), "c1"),
        direct(add_ops("one", "two"), "c2"),
    ]

    verdict = analyze.evaluate(events, board_of(True, True))

    assert verdict["pass"] is False
    assert any("check" in reason for reason in verdict["reasons"])


def test_an_uncheck_does_not_count_as_a_check() -> None:
    events = [direct(add_ops("one", "two"), "c1"), direct(check_ops(1, 2, checked=False), "c2")]

    verdict = analyze.evaluate(events, board_of(True, True))

    assert verdict["pass"] is False


def test_todo_list_calls_are_counted() -> None:
    events = [
        {"type": "tool_use", "name": "todo_list", "tool_call_id": "c1", "input": {}},
        bridged("todo_list", "{}", "c2"),
    ]

    verdict = analyze.evaluate(events, board_of())

    assert verdict["todo_list_calls"] == 2
    assert verdict["board_edit_calls"] == 0


def test_the_bridge_name_falls_back_to_tool_and_tool_name() -> None:
    first = {"type": "tool_use", "name": "tool_call", "input": {"tool": "board_edit", "ops": []}}
    second = {"type": "tool_use", "name": "tool_call", "input": {"tool_name": "board_edit"}}

    verdict = analyze.evaluate([first, second], None)

    assert verdict["board_edit_calls"] == 2


def test_read_board_follows_the_alias_and_opens_read_only(
    connect: ConnFactory, store: BoardStore, db_path: Path
) -> None:
    store.apply("s1", [AddItem("Call John"), AddItem("Book the van")], actor="agent", base_rev=0)
    store.apply("s1", [SetChecked(1, True)], actor="agent", base_rev=1)
    conn = connect()
    try:
        conn.execute("INSERT INTO aliases (session_id, root_id) VALUES ('s3', 's1')")
        conn.commit()
    finally:
        conn.close()
    before = db_path.stat().st_mtime_ns

    board = analyze.read_board(db_path, "s3")

    assert db_path.stat().st_mtime_ns == before
    assert board == {
        "root": "s1",
        "rev": 2,
        "items": [
            {"id": 1, "text": "Call John", "checked": 1, "updated_by": "agent"},
            {"id": 2, "text": "Book the van", "checked": 0, "updated_by": "agent"},
        ],
    }


def test_read_board_returns_none_for_a_missing_file_and_empty_for_an_unknown_session(
    store: BoardStore, db_path: Path, tmp_path: Path
) -> None:
    store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)

    assert analyze.read_board(tmp_path / "absent.db", "s1") is None
    assert analyze.read_board(db_path, "nobody") == {"root": None, "rev": None, "items": []}


def test_load_events_skips_lines_that_are_not_json(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text('{"type": "system"}\nnot json\n\n{"type": "result"}\n', encoding="utf-8")

    assert analyze.load_events(path) == [{"type": "system"}, {"type": "result"}]


def write_run(out: Path, name: str, events: list[Event], session_id: str = "s1") -> None:
    result = {"type": "result", "session_id": session_id, "exit_code": 0, "text": "done"}
    lines = [json.dumps(event) for event in [*events, result]]
    (out / f"{name}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize(("case", "expected"), [("pass", 0), ("fail", 1), ("missing", 2)], ids=str)
def test_main_exit_codes(
    case: str,
    expected: int,
    store: BoardStore,
    db_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "out"
    out.mkdir()
    store.apply("s1", [AddItem("one"), AddItem("two")], actor="agent", base_rev=0)
    if case == "pass":
        store.apply("s1", [SetChecked(1, True), SetChecked(2, True)], actor="agent", base_rev=1)
        write_run(
            out, "run-1", [direct(add_ops("one", "two"), "c1"), direct(check_ops(1, 2), "c2")]
        )
    elif case == "fail":
        write_run(out, "run-1", [direct(add_ops("one", "two"), "c1")])

    code = analyze.main(["--out", str(out), "--db", str(db_path), "run-1"])

    printed = capsys.readouterr().out.strip()
    assert code == expected
    if case != "missing":
        report = json.loads(printed.splitlines()[-1])
        assert report["run"] == "run-1"
        assert report["session_id"] == "s1"
        assert report["pass"] is (case == "pass")
