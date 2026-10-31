"""`board_read` handler: empty board, blank session, spoofed argument, delegate, ordering."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from conftest import ResolverFor
from fakes import FakeReaderFactory, SessionSpec
from session_tasks.board_tools import BoardTools
from session_tasks.db import ConnFactory
from session_tasks.markdown import render
from session_tasks.model import AddItem, RemoveItem, SetChecked, SetText
from session_tasks.results import DELEGATE_EDIT, NO_SESSION
from session_tasks.store import BoardStore


def tools_for(
    store: BoardStore, resolver_for: ResolverFor, specs: dict[str, SessionSpec] | None = None
) -> tuple[BoardTools, FakeReaderFactory]:
    resolver, factory = resolver_for(specs or {})
    return BoardTools(store, resolver), factory


def read(tools: BoardTools, session_id: str | None, args: dict[str, object] | None = None) -> Any:
    out = tools.board_read(args or {}, session_id=session_id)
    assert isinstance(out, str)
    return json.loads(out)


def count_rows(connect: ConnFactory, table: str) -> int:
    conn = connect()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_read_empty_board_returns_rev_zero_and_the_empty_note(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _ = tools_for(store, resolver_for)

    result = read(tools, "s1")

    assert result == {"ok": True, "rev": 0, "board": "", "note": "empty board"}
    assert count_rows(connect, "boards") == 0


def test_read_board_with_every_item_removed_keeps_its_rev_and_the_note(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)
    store.apply("s1", [RemoveItem(1)], actor="agent", base_rev=1)

    result = read(tools, "s1")

    assert result == {"ok": True, "rev": 2, "board": "", "note": "empty board"}


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_read_blank_session_returns_the_no_session_error(
    store: BoardStore, resolver_for: ResolverFor, blank: str | None
) -> None:
    tools, factory = tools_for(store, resolver_for)

    result = read(tools, blank)

    assert result == {"error": NO_SESSION}
    assert factory.opens == 0


def test_read_ignores_a_session_id_in_the_arguments(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("theirs")], actor="agent", base_rev=0)

    result = read(tools, "s1", {"session_id": "s2"})

    assert result["board"] == "- [ ] #1 mine\n"


def test_delegate_session_reads_the_delegator_board(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    specs = {
        "parent": SessionSpec(),
        "child": SessionSpec(parent="parent", model_config={"_delegate_from": "parent"}),
    }
    tools, _ = tools_for(store, resolver_for, specs)
    store.apply("parent", [AddItem("Call John")], actor="agent", base_rev=0)

    result = read(tools, "child")

    assert result == {"ok": True, "rev": 1, "board": "- [ ] #1 Call John\n"}


def test_read_keeps_two_equal_texts_as_two_items(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("Call John"), AddItem("Call John")], actor="agent", base_rev=0)

    result = read(tools, "s1")

    assert result["board"] == "- [ ] #1 Call John\n- [ ] #2 Call John\n"


def test_read_lists_subtasks_after_their_parent_in_display_order(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("parent"), AddItem("second")], actor="agent", base_rev=0)
    store.apply("s1", [AddItem("sub", parent_id=1)], actor="agent", base_rev=1)

    first = tools.board_read({}, session_id="s1")
    second = tools.board_read({}, session_id="s1")

    assert json.loads(first)["board"] == "- [ ] #1 parent\n  - [ ] #3 sub\n- [ ] #2 second\n"
    assert first == second


def edit(
    tools: BoardTools, args: dict[str, object], session_id: str | None = "s1"
) -> dict[str, Any]:
    out = tools.board_edit(args, session_id=session_id)
    assert isinstance(out, str)
    return json.loads(out)


def add_op(text: str, **extra: object) -> dict[str, object]:
    return {"op": "add", "text": text, **extra}


def test_edit_adds_items_and_returns_the_changed_lines(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)

    result = edit(
        tools,
        {
            "ops": [
                add_op("Call John"),
                add_op("Book the van"),
                add_op("Ask about the quote", parent_ref=0),
            ]
        },
    )

    assert result == {
        "ok": True,
        "rev": 1,
        "summary": "rev 1: added 3 items",
        "changed": [
            "- [ ] #1 Call John",
            "- [ ] #2 Book the van",
            "  - [ ] #3 Ask about the quote",
        ],
    }
    assert "board" not in result
    assert "error" not in result


def test_edit_renames_checks_unchecks_and_removes_in_one_call(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply(
        "s1",
        [AddItem("a"), AddItem("b"), AddItem("c", checked=True), AddItem("d")],
        actor="agent",
        base_rev=0,
    )

    result = edit(
        tools,
        {
            "ops": [
                {"op": "set_text", "item_id": 1, "text": "a2"},
                {"op": "set_checked", "item_id": 2, "checked": True},
                {"op": "set_checked", "item_id": 3, "checked": False},
                {"op": "remove", "item_id": 4},
            ],
            "base_rev": 1,
        },
    )

    assert result["summary"] == (
        "rev 2: renamed 1 item, checked 1 item, unchecked 1 item, removed 1 item"
    )
    assert result["changed"] == ["- [ ] #1 a2", "- [x] #2 b", "- [ ] #3 c", "- removed #4"]


def test_remove_of_a_parent_lists_its_subtasks_as_removed(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("parent"), AddItem("sub", parent_ref=0)], actor="agent", base_rev=0)

    result = edit(tools, {"ops": [{"op": "remove", "item_id": 1}], "base_rev": 1})

    assert result["summary"] == "rev 2: removed 1 item"
    assert result["changed"] == ["- removed #1", "- removed #2"]


def test_two_ops_on_one_item_apply_in_order(store: BoardStore, resolver_for: ResolverFor) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("a"), AddItem("b"), AddItem("c")], actor="agent", base_rev=0)

    result = edit(
        tools,
        {
            "ops": [
                {"op": "set_text", "item_id": 3, "text": "c2"},
                {"op": "set_checked", "item_id": 3, "checked": True},
            ],
            "base_rev": 1,
        },
    )

    assert result["changed"] == ["- [x] #3 c2"]
    assert result["summary"] == "rev 2: renamed 1 item, checked 1 item"


def test_repeat_add_batch_adds_new_items(store: BoardStore, resolver_for: ResolverFor) -> None:
    tools, _ = tools_for(store, resolver_for)
    batch: dict[str, object] = {"ops": [add_op("same"), add_op("same")]}

    first = edit(tools, batch)
    second = edit(tools, batch)

    assert first["changed"] == ["- [ ] #1 same", "- [ ] #2 same"]
    assert second["changed"] == ["- [ ] #3 same", "- [ ] #4 same"]


def test_repeat_check_with_the_current_value_is_no_change(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("a", checked=True)], actor="agent", base_rev=0)

    result = edit(
        tools, {"ops": [{"op": "set_checked", "item_id": 1, "checked": True}], "base_rev": 1}
    )

    assert result == {"ok": True, "rev": 1, "summary": "rev 1: no change", "changed": []}


def test_empty_ops_writes_nothing(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _ = tools_for(store, resolver_for)

    result = edit(tools, {"ops": []})

    assert result == {"ok": True, "rev": 0, "summary": "rev 0: no change", "changed": []}
    assert count_rows(connect, "boards") == 0


def test_missing_ops_returns_the_ops_required_error(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)

    assert edit(tools, {}) == {"error": "ops is required: a list of operations"}


def test_stale_write_returns_the_current_board(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)
    store.apply("s1", [SetChecked(1, True)], actor="user", base_rev=1)
    before = store.get_board("s1")

    result = edit(tools, {"ops": [{"op": "set_text", "item_id": 1, "text": "new"}], "base_rev": 1})

    assert result["error"].startswith("stale: #1 changed after rev 1 (op 0)")
    assert result["stale"] is True
    assert result["reason"] == "stale"
    assert result["op_index"] == 0
    assert result["item_id"] == 1
    assert result["rev"] == 2
    assert result["board"] == render(before, include_ids=True)
    assert store.get_board("s1") == before


def test_not_found_returns_the_not_found_text(store: BoardStore, resolver_for: ResolverFor) -> None:
    tools, _ = tools_for(store, resolver_for)

    result = edit(tools, {"ops": [{"op": "remove", "item_id": 9}], "base_rev": 0})

    assert result["error"] == "not found: #9 is not on the board (op 0)"
    assert result["reason"] == "not_found"


def test_base_rev_equal_to_the_item_rev_is_fresh_and_one_below_is_stale(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)
    store.apply("s1", [SetText(1, "b")], actor="user", base_rev=1)

    stale = edit(
        tools, {"ops": [{"op": "set_checked", "item_id": 1, "checked": True}], "base_rev": 1}
    )
    fresh = edit(
        tools, {"ops": [{"op": "set_checked", "item_id": 1, "checked": True}], "base_rev": 2}
    )

    assert stale["stale"] is True
    assert fresh["ok"] is True


def seed_hundred(store: BoardStore) -> None:
    store.apply("s1", [AddItem(f"i{n}") for n in range(100)], actor="agent", base_rev=0)


@pytest.mark.parametrize(
    ("ops", "expected"),
    [
        ([add_op("ok"), add_op("   ")], "op 1: item text is empty"),
        ([add_op("x" * 501)], "op 0: item text is longer than 500 characters"),
        ([add_op("sub of sub", parent_id=2)], "op 0:"),
        ([add_op("early", parent_ref=1), add_op("later")], "op 0:"),
    ],
    ids=["empty-text", "too-long", "depth", "bad-parent-ref"],
)
def test_rule_errors_name_the_op_index_and_write_nothing(
    store: BoardStore, resolver_for: ResolverFor, ops: list[dict[str, object]], expected: str
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("parent"), AddItem("sub", parent_ref=0)], actor="agent", base_rev=0)
    before = store.get_board("s1")

    result = edit(tools, {"ops": ops, "base_rev": before.rev})

    assert set(result) == {"error"}
    assert result["error"].startswith(expected)
    assert store.get_board("s1") == before


def test_a_101st_item_is_a_rule_error_and_writes_nothing(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    seed_hundred(store)
    before = store.get_board("s1")

    result = edit(tools, {"ops": [add_op("one too many")]})

    assert "a board holds at most 100 items" in result["error"]
    assert store.get_board("s1") == before


@pytest.mark.parametrize("session_id", [None, "", "   "])
def test_edit_blank_session_returns_no_session(
    store: BoardStore, resolver_for: ResolverFor, session_id: str | None
) -> None:
    tools, _ = tools_for(store, resolver_for)

    assert edit(tools, {"ops": [add_op("x")]}, session_id) == {"error": NO_SESSION}


def test_edit_ignores_a_session_id_in_the_arguments(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)

    edit(tools, {"ops": [add_op("mine")], "session_id": "s2"}, "s1")

    assert [item.text for item in store.get_board("s1").items] == ["mine"]
    assert store.get_board("s2").items == ()


def test_delegate_session_cannot_edit(store: BoardStore, resolver_for: ResolverFor) -> None:
    tools, _ = tools_for(store, resolver_for, DELEGATE_SPECS)
    store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)
    before = store.get_board("s1")

    result = edit(tools, {"ops": [add_op("sneaky")]}, "dg")

    assert result == {"error": DELEGATE_EDIT}
    assert store.get_board("s1") == before


def test_checking_a_parent_leaves_its_subtasks_unchecked(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("parent"), AddItem("sub", parent_ref=0)], actor="agent", base_rev=0)

    result = edit(
        tools, {"ops": [{"op": "set_checked", "item_id": 1, "checked": True}], "base_rev": 1}
    )

    assert result["changed"] == ["- [x] #1 parent"]
    assert store.get_board("s1").item(2) is not None
    assert not store.get_board("s1").item(2).checked  # pyright: ignore[reportOptionalMemberAccess]


DELEGATE_SPECS = {
    "s1": SessionSpec(),
    "dg": SessionSpec(parent="s1", model_config={"_delegate_from": "s1"}),
}


def recording_tools(store: BoardStore, resolver_for: ResolverFor, calls: list[str]) -> BoardTools:
    resolver, _ = resolver_for(DELEGATE_SPECS)
    return BoardTools(store, resolver, after_write=calls.append)


def test_after_write_runs_once_with_the_root_after_a_change(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    calls: list[str] = []
    tools = recording_tools(store, resolver_for, calls)

    edit(tools, {"ops": [add_op("a")]})

    assert calls == ["s1"]


@pytest.mark.parametrize(
    ("args", "session_id"),
    [
        ({"ops": []}, "s1"),
        ({"ops": [{"op": "set_checked", "item_id": 1, "checked": False}], "base_rev": 2}, "s1"),
        ({"ops": [{"op": "set_text", "item_id": 1, "text": "x"}], "base_rev": 1}, "s1"),
        ({"ops": [add_op("  ")]}, "s1"),
        ({"ops": [add_op("x")]}, None),
        ({"ops": [add_op("x")]}, "dg"),
    ],
    ids=["no-ops", "no-change", "stale", "rule-error", "blank-session", "delegate"],
)
def test_after_write_stays_silent_when_nothing_changed(
    store: BoardStore, resolver_for: ResolverFor, args: dict[str, object], session_id: str | None
) -> None:
    calls: list[str] = []
    tools = recording_tools(store, resolver_for, calls)
    store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)
    store.apply("s1", [SetText(1, "b")], actor="user", base_rev=1)

    edit(tools, args, session_id)

    assert calls == []


def test_a_failing_after_write_still_returns_the_applied_result(
    store: BoardStore, resolver_for: ResolverFor, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(root_id: str) -> None:
        raise RuntimeError("listener down")

    resolver, _ = resolver_for({})
    tools = BoardTools(store, resolver, after_write=boom)

    with caplog.at_level(logging.WARNING, logger="session_tasks.board_tools"):
        result = edit(tools, {"ops": [add_op("a")]})

    assert result["ok"] is True
    assert [item.text for item in store.get_board("s1").items] == ["a"]
    records = [r for r in caplog.records if r.name == "session_tasks.board_tools"]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
