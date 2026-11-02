"""The pane write path: optimistic display, stale retry, one write at a time and the notice line."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import EVENT_TYPE, Rig, board_gets, checkbox, posts, seed_call_john, stale_body
from session_tasks.board_json import board_dict
from session_tasks.model import AddItem, Board, RemoveItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

STALE_NOTICE = "Board changed, showing the latest"
WRITE_FAILED_NOTICE = "Could not save that change. Try again."
LOAD_FAILED_NOTICE = "Could not load the board. Retrying."
MISMATCH_LINE = "Version mismatch: update the desktop plugin on this machine"
NOTICE_MS = 4000
CHECK_ROW_1 = {"check": {"row": "1", "value": True}}
OUTSIDE_TEXT = {
    "outside": {
        "ops": [{"op": "set_text", "item_id": 1, "text": "Call John today"}],
        "base_rev": 1,
    }
}
CHECK_OP = [{"op": "set_checked", "item_id": 1, "checked": True}]
BOARD_EVENT = {"event": {"type": EVENT_TYPE}}
GET_BOARD = "/board?session_id=s1"
EDIT = "/board/edit"


def board_body(board: Board, sid: str) -> dict[str, Any]:
    """A board GET reply in the shape the route builds."""
    return {
        "ok": True,
        "session_id": sid,
        "root_id": board.root_id,
        "rev": board.rev,
        "board": board_dict(board),
    }


def seed_two(rig: Rig) -> None:
    seed_call_john(rig.store)
    rig.store.apply("s1", [AddItem("Email Ann")], actor="agent", base_rev=1)


def test_stale_check_retries_once_on_the_new_rev(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[OUTSIDE_TEXT, CHECK_ROW_1])

    sent = posts(result)
    assert [call["path"] for call in sent] == ["/board/edit", "/board/edit"]
    assert [call["body"]["ops"] for call in sent] == [CHECK_OP, CHECK_OP]
    assert [call["body"]["base_rev"] for call in sent] == [1, 2]
    board = rig.store.get_board("s1")
    assert board.rev == 3
    assert board.items[0].checked is True
    assert board.items[0].text == "Call John today"
    assert board.items[0].updated_by == "user"
    assert "Call John today" in result["lines"]
    assert "0 of 1 open" in result["lines"]
    assert STALE_NOTICE in result["lines"]
    assert NOTICE_MS in result["timeouts"]


def test_check_shows_before_the_reply(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[CHECK_ROW_1])

    at_write = [box for box in result["atWrite"][0]["checkboxes"] if box["row"] == "1"]
    assert [box["checked"] for box in at_write] == [True]


def test_second_stale_reply_is_not_retried(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    stale = stale_body(rig.store.get_board("s1"), "s1")

    result = rig.run(tmp_path, restSequences={EDIT: [stale, stale]}, steps=[CHECK_ROW_1])

    sent = posts(result)
    assert [call["body"]["base_rev"] for call in sent] == [1, 1]
    assert STALE_NOTICE in result["lines"]


def test_stale_without_the_item_is_not_retried(rig: Rig, tmp_path: Path) -> None:
    seed_two(rig)
    before = board_body(rig.store.get_board("s1"), "s1")
    rig.store.apply("s1", [RemoveItem(1)], actor="agent", base_rev=2)
    stale = stale_body(rig.store.get_board("s1"), "s1")

    result = rig.run(
        tmp_path,
        restSequences={GET_BOARD: [before], EDIT: [stale]},
        steps=[CHECK_ROW_1],
    )

    assert len(posts(result)) == 1
    assert "Email Ann" in result["lines"]
    assert "Call John" not in result["lines"]
    assert STALE_NOTICE in result["lines"]


def test_writes_run_one_at_a_time(rig: Rig, tmp_path: Path) -> None:
    seed_two(rig)

    result = rig.run(
        tmp_path,
        duringWrite=[{"check": {"row": "2", "value": True}}],
        steps=[CHECK_ROW_1],
    )

    sent = posts(result)
    assert [(call["body"]["ops"][0]["item_id"], call["body"]["base_rev"]) for call in sent] == [
        (1, 2),
        (2, 3),
    ]
    at_write = {box["row"]: box["checked"] for box in result["atWrite"][0]["checkboxes"]}
    assert at_write == {"1": True, "2": True}
    board = rig.store.get_board("s1")
    assert board.rev == 4
    assert [item.checked for item in board.items] == [True, True]


def test_reload_reply_during_a_write_is_ignored(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    injected = board_body(rig.store.get_board("s1"), "s1")
    injected["rev"] = 5
    injected["board"]["items"][0]["text"] = "Injected"

    result = rig.run(
        tmp_path,
        restSequences={GET_BOARD: ["__relay__", injected]},
        duringWrite=[BOARD_EVENT],
        steps=[CHECK_ROW_1],
    )

    assert len(board_gets(result)) == 2
    assert "Injected" not in result["atWrite"][0]["lines"]
    assert "Call John" in result["atWrite"][0]["lines"]
    row_1 = [box for box in result["atWrite"][0]["checkboxes"] if box["row"] == "1"]
    assert [box["checked"] for box in row_1] == [True]


def test_older_reload_reply_is_ignored(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    older = board_body(rig.store.get_board("empty"), "s1")

    result = rig.run(
        tmp_path,
        restSequences={GET_BOARD: ["__relay__", older]},
        steps=[BOARD_EVENT],
    )

    assert len(board_gets(result)) == 2
    assert "Call John" in result["lines"]


def test_thrown_write_error_shows_write_failed_and_reloads(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, restSequences={EDIT: ["__error__"]}, steps=[CHECK_ROW_1])

    assert WRITE_FAILED_NOTICE in result["lines"]
    assert checkbox(result, "1")["checked"] is False
    assert len(board_gets(result)) == 2
    assert NOTICE_MS in result["timeouts"]


def test_invalid_reply_shows_write_failed(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    invalid = {"ok": False, "error": "invalid", "op_index": 0, "rule": "r", "message": "m"}

    result = rig.run(tmp_path, restSequences={EDIT: [invalid]}, steps=[CHECK_ROW_1])

    assert WRITE_FAILED_NOTICE in result["lines"]
    assert "r" not in result["lines"]
    assert "m" not in result["lines"]
    assert checkbox(result, "1")["checked"] is False
    assert len(board_gets(result)) == 2


def test_load_failure_shows_load_failed_then_clears(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    failed = rig.run(tmp_path, restSequences={GET_BOARD: ["__error__"]})
    cleared = rig.run(tmp_path, restSequences={GET_BOARD: ["__error__"]}, steps=[BOARD_EVENT])

    assert LOAD_FAILED_NOTICE in failed["lines"]
    assert LOAD_FAILED_NOTICE not in cleared["lines"]
    assert "Call John" in cleared["lines"]


def test_notice_clears_when_its_timer_fires(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[OUTSIDE_TEXT, CHECK_ROW_1, {"timers": True}])

    assert STALE_NOTICE not in result["lines"]
    assert "Call John today" in result["lines"]


def test_write_failed_replaces_stale(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    stale = stale_body(rig.store.get_board("s1"), "s1")

    result = rig.run(tmp_path, restSequences={EDIT: [stale, "__error__"]}, steps=[CHECK_ROW_1])

    assert WRITE_FAILED_NOTICE in result["lines"]
    assert STALE_NOTICE not in result["lines"]


def test_mismatch_outranks_write_failed(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    meta = {"ok": True, "plugin_id": "x", "backend_version": "9.9.9", "api_version": 1}

    result = rig.run(
        tmp_path,
        restOverrides={"/meta": meta},
        restSequences={EDIT: ["__error__"]},
        steps=[CHECK_ROW_1],
    )

    assert MISMATCH_LINE in result["lines"]
    assert WRITE_FAILED_NOTICE not in result["lines"]


def test_notice_line_truncates(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[OUTSIDE_TEXT, CHECK_ROW_1])

    nodes = [node for node in result["nodes"] if node["text"] == STALE_NOTICE]
    assert len(nodes) == 1
    assert nodes[0]["style"] == {
        "whiteSpace": "nowrap",
        "overflow": "hidden",
        "textOverflow": "ellipsis",
    }
    assert {"text-xs", "text-(--ui-text-secondary)"} <= set(nodes[0]["className"].split())


# Review 04-REVIEW: the write queue, the busy flags and the focus rules.

ADD = "Add an item"
SUBTASK = "Add a subtask"


def add_text(text: str) -> dict[str, Any]:
    return {"type": {"input": {"placeholder": ADD}, "text": text}}


ADD_ENTER = {"key": {"input": {"placeholder": ADD}, "key": "Enter"}}


def test_one_thrown_error_does_not_stop_later_writes(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(
        tmp_path,
        timeoutThrows=True,
        restSequences={EDIT: ["__error__"]},
        steps=[add_text("First"), ADD_ENTER, add_text("Second"), ADD_ENTER],
    )

    assert [call["body"]["ops"][0]["text"] for call in posts(result)] == ["First", "Second"]
    assert [item.text for item in rig.store.get_board("s1").items] == ["Call John", "Second"]
