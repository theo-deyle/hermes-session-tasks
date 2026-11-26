"""Cross-session tools: board_copy, the cross board_read and board_sessions."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

import pytest
from conftest import ResolverFor
from fakes import SEVEN_ROW_FIXTURE, FakeReaderFactory, SessionSpec
from session_tasks import copy_args
from session_tasks.board_tools import BoardTools
from session_tasks.db import ConnFactory
from session_tasks.model import NO_SOURCE_BOARD, SAME_BOARD, AddItem, RemoveItem, SetChecked
from session_tasks.results import (
    DELEGATE_COPY,
    NO_SESSION,
    NO_SESSIONS_NOTE,
    OTHER_BOARD_NOTE,
    SESSIONS_SHOWN,
)
from session_tasks.store import BoardStore
from session_tasks.titles import UNTITLED, TitleLookup

Calls = list[tuple[str, str, int]]


def cross_tools(
    store: BoardStore, resolver_for: ResolverFor, specs: dict[str, SessionSpec]
) -> tuple[BoardTools, Calls, FakeReaderFactory]:
    """Build tools whose resolver and title lookup share one reader factory."""
    resolver, factory = resolver_for(specs)
    calls: Calls = []

    def record(root_id: str, session_id: str, rev: int) -> None:
        calls.append((root_id, session_id, rev))

    tools = BoardTools(store, resolver, after_write=record, titles=TitleLookup(factory))
    return tools, calls, factory


def call(tools: BoardTools, name: str, session_id: str | None, args: dict[str, object]) -> Any:
    out = getattr(tools, name)(args, session_id=session_id)
    assert isinstance(out, str)
    return json.loads(out)


def test_board_copy_copies_one_open_item_into_the_caller_board(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, calls, _ = cross_tools(store, resolver_for, {"s1": SessionSpec(title="Lease renewal")})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Call John")], actor="agent", base_rev=0)
    source_before = store.get_board("s2")

    result = call(tools, "board_copy", "s1", {"from_session_id": "s2"})

    assert result == {
        "ok": True,
        "rev": 2,
        "summary": "Copied 1 to Lease renewal. 0 skipped, already on the board.",
        "changed": ["- [ ] #2 Call John"],
    }
    assert calls == [("s1", "s1", 2)]
    assert store.get_board("s2") == source_before


def count_rows(connect: ConnFactory, table: str) -> int:
    conn = connect()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def seen(connect: ConnFactory, root: str) -> int:
    conn = connect()
    try:
        row = conn.execute("SELECT agent_seen_rev FROM boards WHERE root_id = ?", (root,))
        return int(row.fetchone()[0])
    finally:
        conn.close()


def test_an_argument_session_id_never_changes_the_target(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    store.apply("s2", [AddItem("Call John")], actor="agent", base_rev=0)

    result = call(tools, "board_copy", "s1", {"from_session_id": "s2", "session_id": "s3"})

    assert result["changed"] == ["- [ ] #1 Call John"]
    assert [item.text for item in store.get_board("s1").items] == ["Call John"]
    conn = connect()
    try:
        assert conn.execute("SELECT 1 FROM boards WHERE root_id = 's3'").fetchone() is None
    finally:
        conn.close()


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_caller_gives_no_session(
    store: BoardStore, resolver_for: ResolverFor, blank: str | None
) -> None:
    tools, calls, factory = cross_tools(store, resolver_for, {})

    result = call(tools, "board_copy", blank, {"from_session_id": "s2"})

    assert result == {"error": NO_SESSION}
    assert factory.opens == 0
    assert calls == []


def test_delegate_cannot_copy(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, calls, _ = cross_tools(store, resolver_for, SEVEN_ROW_FIXTURE)
    store.apply("s2", [AddItem("Call John")], actor="agent", base_rev=0)
    boards, changes = count_rows(connect, "boards"), count_rows(connect, "changes")

    result = call(tools, "board_copy", "dg", {"from_session_id": "s2"})

    assert result == {"error": DELEGATE_COPY}
    assert (count_rows(connect, "boards"), count_rows(connect, "changes")) == (boards, changes)
    assert calls == []


def test_copy_from_the_own_board_is_refused(store: BoardStore, resolver_for: ResolverFor) -> None:
    tools, calls, _ = cross_tools(store, resolver_for, SEVEN_ROW_FIXTURE)
    store.apply("root", [AddItem("Call John")], actor="agent", base_rev=0)

    result = call(tools, "board_copy", "comp2", {"from_session_id": "comp1"})

    assert result == {"error": SAME_BOARD}
    assert [item.text for item in store.get_board("root").items] == ["Call John"]
    assert calls == []


def test_copy_from_a_session_with_no_board_is_refused(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, calls, _ = cross_tools(store, resolver_for, {})

    result = call(tools, "board_copy", "s1", {"from_session_id": "s9"})

    assert result == {"error": NO_SOURCE_BOARD}
    assert count_rows(connect, "boards") == 0
    assert calls == []


def test_a_missing_item_names_the_id_and_copies_nothing(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, calls, _ = cross_tools(store, resolver_for, {})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Call John")], actor="agent", base_rev=0)
    before = (store.get_board("s1"), store.get_board("s2"))

    result = call(tools, "board_copy", "s1", {"from_session_id": "s2", "item_ids": [1, 9]})

    assert result == {"error": "not found: #9 is not on that session's board. Nothing was copied."}
    assert (store.get_board("s1"), store.get_board("s2")) == before
    assert calls == []


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({"from_session_id": "s2", "item_ids": []}, copy_args.ITEM_IDS_EMPTY),
        (
            {"from_session_id": "s2", "item_ids": [True]},
            "item_ids[0] must be a whole number of 1 or more",
        ),
        ({"from_session_id": "  "}, copy_args.FROM_REQUIRED),
        ({"from_session_id": "s2", "item_ids": list(range(1, 102))}, copy_args.TOO_MANY_IDS),
    ],
    ids=["empty-list", "bool-id", "blank-source", "101-ids"],
)
def test_bad_arguments_give_the_parser_message(
    store: BoardStore,
    resolver_for: ResolverFor,
    connect: ConnFactory,
    args: dict[str, object],
    message: str,
) -> None:
    tools, calls, _ = cross_tools(store, resolver_for, {})
    store.apply("s2", [AddItem("Call John")], actor="agent", base_rev=0)
    changes = count_rows(connect, "changes")

    result = call(tools, "board_copy", "s1", args)

    assert result == {"error": message}
    assert count_rows(connect, "changes") == changes
    assert calls == []


def test_skipped_items_are_counted_in_the_sentence(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {"s1": SessionSpec(title="Lease renewal")})
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Call John"), AddItem("Book the van")], actor="agent", base_rev=0)

    result = call(tools, "board_copy", "s1", {"from_session_id": "s2"})

    assert result["summary"] == "Copied 1 to Lease renewal. 1 skipped, already on the board."
    assert result["changed"] == ["- [ ] #2 Book the van"]


def test_the_cap_sentence_follows_only_when_items_were_cut(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {"s1": SessionSpec(title="Lease renewal")})
    store.apply("s1", [AddItem(f"Own {n}") for n in range(98)], actor="agent", base_rev=0)
    store.apply("s2", [AddItem(f"Plan {n}") for n in range(5)], actor="agent", base_rev=0)

    result = call(tools, "board_copy", "s1", {"from_session_id": "s2"})

    assert result["summary"] == (
        "Copied 2 to Lease renewal. 0 skipped, already on the board."
        " 3 not copied, the board holds 100 items."
    )
    assert len(store.get_board("s1").items) == 100


def test_a_copy_of_nothing_calls_no_listener(store: BoardStore, resolver_for: ResolverFor) -> None:
    tools, calls, _ = cross_tools(store, resolver_for, {"s1": SessionSpec(title="Lease renewal")})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Done thing")], actor="agent", base_rev=0)
    store.apply("s2", [SetChecked(1, True)], actor="agent", base_rev=1)

    result = call(tools, "board_copy", "s1", {"from_session_id": "s2"})

    assert result == {
        "ok": True,
        "rev": 1,
        "summary": "Copied 0 to Lease renewal. 0 skipped, already on the board.",
        "changed": [],
    }
    assert calls == []


def test_listener_fault_keeps_the_result_ok(
    store: BoardStore, resolver_for: ResolverFor, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(root_id: str, session_id: str, rev: int) -> None:
        raise RuntimeError("listener down")

    resolver, factory = resolver_for({})
    tools = BoardTools(store, resolver, after_write=boom, titles=TitleLookup(factory))
    store.apply("s2", [AddItem("Call John")], actor="agent", base_rev=0)

    with caplog.at_level(logging.WARNING, logger="session_tasks.board_tools"):
        result = call(tools, "board_copy", "s1", {"from_session_id": "s2"})

    assert result["ok"] is True
    assert [item.text for item in store.get_board("s1").items] == ["Call John"]
    records = [r for r in caplog.records if r.name == "session_tasks.board_tools"]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING


def test_a_compressed_source_id_reaches_its_root_board(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, SEVEN_ROW_FIXTURE)
    store.apply("root", [AddItem("Call John")], actor="agent", base_rev=0)

    result = call(tools, "board_copy", "plain", {"from_session_id": "comp2"})

    assert result["changed"] == ["- [ ] #1 Call John"]
    assert [item.text for item in store.get_board("plain").items] == ["Call John"]


def test_changed_lines_keep_parent_before_subtask(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply(
        "s2",
        [AddItem("Plan the trip"), AddItem("Book the flight", parent_ref=0)],
        actor="agent",
        base_rev=0,
    )

    result = call(tools, "board_copy", "s1", {"from_session_id": "s2"})

    assert result["changed"] == ["- [ ] #2 Plan the trip", "  - [ ] #3 Book the flight"]


def test_agent_copy_advances_seen_when_up_to_date(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Call John")], actor="agent", base_rev=0)
    assert seen(connect, "s1") == 1

    result = call(tools, "board_copy", "s1", {"from_session_id": "s2"})

    assert result["rev"] == 2
    assert seen(connect, "s1") == 2


def test_board_read_names_another_board_and_marks_nothing(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    specs = {"s2": SessionSpec(title="Syncro ticket 4910")}
    tools, calls, _ = cross_tools(store, resolver_for, specs)
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Reply to the customer")], actor="agent", base_rev=0)
    before = (
        seen(connect, "s1"),
        seen(connect, "s2"),
        count_rows(connect, "boards"),
        count_rows(connect, "changes"),
    )

    result = call(tools, "board_read", "s1", {"session_id": "s2"})

    assert result == {
        "ok": True,
        "rev": 1,
        "session_id": "s2",
        "title": "Syncro ticket 4910",
        "note": OTHER_BOARD_NOTE,
        "board": "- [ ] #1 Reply to the customer\n",
    }
    after = (
        seen(connect, "s1"),
        seen(connect, "s2"),
        count_rows(connect, "boards"),
        count_rows(connect, "changes"),
    )
    assert after == before
    assert calls == []


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_argument_is_an_own_read(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory, blank: str
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply("s1", [AddItem("Also mine")], actor="user", base_rev=1)

    result = call(tools, "board_read", "s1", {"session_id": blank})

    assert result == {"ok": True, "rev": 2, "board": "- [ ] #1 Mine\n- [ ] #2 Also mine\n"}
    assert seen(connect, "s1") == 2


def test_an_id_of_the_own_lineage_is_an_own_read(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, SEVEN_ROW_FIXTURE)
    store.apply("root", [AddItem("Call John")], actor="agent", base_rev=0)

    result = call(tools, "board_read", "comp2", {"session_id": "comp1"})

    assert result == {"ok": True, "rev": 1, "board": "- [ ] #1 Call John\n"}
    assert seen(connect, "root") == 1


@pytest.mark.parametrize("bad", [5, ["s2"]])
def test_a_non_string_argument_is_an_error(
    store: BoardStore, resolver_for: ResolverFor, bad: object
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)

    result = call(tools, "board_read", "s1", {"session_id": bad})

    assert result == {"error": copy_args.TARGET_BAD}


def test_an_unknown_id_gives_no_board_and_creates_no_row(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    boards = count_rows(connect, "boards")

    result = call(tools, "board_read", "s1", {"session_id": "typo"})

    assert result == {"error": NO_SOURCE_BOARD}
    assert count_rows(connect, "boards") == boards


def test_a_delegate_can_read_another_board_and_marks_nothing(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, SEVEN_ROW_FIXTURE)
    store.apply("root", [AddItem("Parent item")], actor="agent", base_rev=0)
    store.apply("plain", [AddItem("Other item")], actor="agent", base_rev=0)
    before = (seen(connect, "root"), seen(connect, "plain"))

    result = call(tools, "board_read", "dg", {"session_id": "plain"})

    assert result["ok"] is True
    assert result["board"] == "- [ ] #1 Other item\n"
    assert (seen(connect, "root"), seen(connect, "plain")) == before


def test_an_empty_other_board_says_so(store: BoardStore, resolver_for: ResolverFor) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    store.apply("s2", [AddItem("Gone soon")], actor="agent", base_rev=0)
    store.apply("s2", [RemoveItem(1)], actor="agent", base_rev=1)

    result = call(tools, "board_read", "s1", {"session_id": "s2"})

    assert result["rev"] == 2
    assert result["board"] == ""
    assert result["note"].endswith("; empty board")


def test_a_cross_read_of_a_branch_id_copies_its_parent_board_once(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, SEVEN_ROW_FIXTURE)
    store.apply("root", [AddItem("Parent item")], actor="agent", base_rev=0)

    first = call(tools, "board_read", "plain", {"session_id": "br"})

    assert first["ok"] is True
    assert first["board"] == "- [ ] #1 Parent item\n"
    assert first["session_id"] == "br"
    conn = connect()
    try:
        assert conn.execute("SELECT 1 FROM boards WHERE root_id = 'br'").fetchone() is not None
    finally:
        conn.close()
    rows = (count_rows(connect, "boards"), count_rows(connect, "changes"))

    second = call(tools, "board_read", "plain", {"session_id": "br"})

    assert second == first
    assert (count_rows(connect, "boards"), count_rows(connect, "changes")) == rows


def test_the_title_falls_back_to_untitled(store: BoardStore, resolver_for: ResolverFor) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {"s2": SessionSpec()})
    store.apply("s2", [AddItem("Item")], actor="agent", base_rev=0)

    result = call(tools, "board_read", "s1", {"session_id": "s2"})

    assert result["title"] == UNTITLED


def stamps(store: BoardStore) -> dict[str, str]:
    return {summary.root_id: summary.updated_at for summary in store.list_boards()}


def lines_of(result: Any) -> Sequence[str]:
    assert result["ok"] is True
    return result["sessions"]


def test_board_sessions_lists_boards_newest_first_with_titles(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    specs = {
        "s1": SessionSpec(title="Lease renewal"),
        "s2": SessionSpec(messages=(("user", "Reply to the customer about 4910"),)),
        "s3": SessionSpec(),
    }
    tools, _, _ = cross_tools(store, resolver_for, specs)
    store.apply("s3", [AddItem("Three")], actor="agent", base_rev=0)
    store.apply("s1", [AddItem("A"), AddItem("B"), AddItem("C")], actor="agent", base_rev=0)
    store.apply("s1", [SetChecked(2, True)], actor="agent", base_rev=1)
    store.apply("s2", [AddItem("Reply")], actor="agent", base_rev=0)
    at = stamps(store)

    result = call(tools, "board_sessions", "s1", {})

    assert result == {
        "ok": True,
        "sessions": [
            f"- Reply to the customer about 4910 | s2 | 1 of 1 open | updated {at['s2']}",
            f"- Lease renewal | s1 | 2 of 3 open | updated {at['s1']} (this session)",
            f"- Untitled session | s3 | 1 of 1 open | updated {at['s3']}",
        ],
        "more": 0,
    }


def test_equal_update_times_sort_by_root_id(
    connect: ConnFactory, resolver_for: ResolverFor
) -> None:
    same = BoardStore(connect, lambda: "2026-10-30T12:00:00.000000Z")
    tools, _, _ = cross_tools(same, resolver_for, {})
    for root in ("b", "c", "a"):
        same.apply(root, [AddItem("Item")], actor="agent", base_rev=0)

    result = call(tools, "board_sessions", None, {})

    ids = [line.split(" | ")[1] for line in lines_of(result)]
    assert ids == ["a", "b", "c"]


def test_equal_titles_are_both_listed(store: BoardStore, resolver_for: ResolverFor) -> None:
    specs = {"s1": SessionSpec(title="Same"), "s2": SessionSpec(title="Same")}
    tools, _, _ = cross_tools(store, resolver_for, specs)
    store.apply("s1", [AddItem("One")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Two")], actor="agent", base_rev=0)

    result = call(tools, "board_sessions", None, {})

    assert [line.split(" | ")[:2] for line in lines_of(result)] == [
        ["- Same", "s2"],
        ["- Same", "s1"],
    ]


def test_no_board_gives_an_empty_list_and_the_note(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})

    result = call(tools, "board_sessions", "s1", {})

    assert result == {"ok": True, "sessions": [], "more": 0, "note": NO_SESSIONS_NOTE}
    assert count_rows(connect, "boards") == 0


def test_a_caller_with_no_board_gets_no_own_marker(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    store.apply("s2", [AddItem("Theirs")], actor="agent", base_rev=0)

    result = call(tools, "board_sessions", "s1", {})

    assert len(lines_of(result)) == 1
    assert "(this session)" not in lines_of(result)[0]


def test_more_than_50_boards_lists_50_and_counts_the_rest(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    for number in range(SESSIONS_SHOWN + 3):
        store.apply(f"s{number:02d}", [AddItem("Item")], actor="agent", base_rev=0)

    result = call(tools, "board_sessions", None, {})

    assert len(lines_of(result)) == SESSIONS_SHOWN
    assert result["more"] == 3
    assert "s52" in lines_of(result)[0]


def test_board_sessions_writes_nothing_and_is_repeatable(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, calls, _ = cross_tools(store, resolver_for, {})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Theirs")], actor="agent", base_rev=0)
    before = (
        count_rows(connect, "boards"),
        count_rows(connect, "changes"),
        seen(connect, "s1"),
        seen(connect, "s2"),
    )

    first = call(tools, "board_sessions", "s1", {})
    second = call(tools, "board_sessions", "s1", {})

    assert first == second
    after = (
        count_rows(connect, "boards"),
        count_rows(connect, "changes"),
        seen(connect, "s1"),
        seen(connect, "s2"),
    )
    assert after == before
    assert calls == []


@pytest.mark.parametrize("blank", [None, ""])
def test_blank_keyword_still_lists_without_a_marker(
    store: BoardStore, resolver_for: ResolverFor, blank: str | None
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, {})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)

    result = call(tools, "board_sessions", blank, {})

    assert len(lines_of(result)) == 1
    assert "(this session)" not in lines_of(result)[0]


def test_a_delegate_caller_marks_the_delegator_board(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _, _ = cross_tools(store, resolver_for, SEVEN_ROW_FIXTURE)
    store.apply("root", [AddItem("Parent item")], actor="agent", base_rev=0)
    store.apply("plain", [AddItem("Other item")], actor="agent", base_rev=0)

    result = call(tools, "board_sessions", "dg", {})

    marked = [line for line in lines_of(result) if line.endswith("(this session)")]
    assert len(marked) == 1
    assert " | root | " in marked[0]


def test_one_reader_serves_every_title(store: BoardStore, resolver_for: ResolverFor) -> None:
    resolver, _ = resolver_for({})
    title_factory = FakeReaderFactory({"s1": SessionSpec(title="One")})
    tools = BoardTools(store, resolver, titles=TitleLookup(title_factory))
    for root in ("s1", "s2", "s3"):
        store.apply(root, [AddItem("Item")], actor="agent", base_rev=0)

    result = call(tools, "board_sessions", "s1", {})

    assert len(lines_of(result)) == 3
    assert title_factory.opens == 1
    assert title_factory.all_closed
