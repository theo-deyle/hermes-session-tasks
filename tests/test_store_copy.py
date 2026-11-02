"""BoardStore.copy_items: the copy batch, its guards, its journal rows and the seen rule."""

from __future__ import annotations

from contextlib import closing

import pytest
from session_tasks import delta, rows
from session_tasks.db import ConnFactory
from session_tasks.markdown import render
from session_tasks.model import AddItem, Change, CopyApplied, NoSourceBoard, SameBoard, Stale
from session_tasks.results import summary_line
from session_tasks.store import BoardStore


def journal(connect: ConnFactory, root_id: str) -> tuple[Change, ...]:
    with closing(connect()) as conn:
        return rows.read_changes(conn, root_id)


def seed(store: BoardStore, root_id: str, *ops: AddItem) -> None:
    store.apply(root_id, list(ops), actor="agent", base_rev=0)


def test_copy_one_open_item_from_another_board(store: BoardStore, connect: ConnFactory) -> None:
    seed(store, "s2", AddItem("Call John"), AddItem("Book the van", checked=True))
    seed(store, "s1", AddItem("Mine"))
    source_before = store.get_board("s2")

    result = store.copy_items("s1", "s2", None, actor="agent")

    assert isinstance(result, CopyApplied)
    assert (result.copied, result.skipped, result.overflow) == (1, 0, 0)
    board = store.get_board("s1")
    assert render(board, include_ids=True) == "- [ ] #1 Mine\n- [ ] #2 Call John\n"
    copied = board.item(2)
    assert copied is not None
    assert copied.updated_by == "agent"
    assert copied.checked is False
    tail = journal(connect, "s1")[-2:]
    assert [(c.op, c.item_id, c.text, c.rev) for c in tail] == [
        ("add", 2, "Call John", board.rev),
        ("copied", 2, "s2#1", board.rev),
    ]
    assert store.get_board("s2") == source_before


def seen_rev(connect: ConnFactory, root_id: str) -> int:
    with closing(connect()) as conn:
        row = conn.execute("SELECT agent_seen_rev FROM boards WHERE root_id = ?", (root_id,))
        return int(row.fetchone()[0])


def board_count(connect: ConnFactory) -> int:
    with closing(connect()) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM boards").fetchone()[0])


def numbered(prefix: str, count: int) -> list[AddItem]:
    return [AddItem(f"{prefix} {index}") for index in range(count)]


def test_new_ids_continue_from_next_item_id_and_parents_come_first(store: BoardStore) -> None:
    seed(store, "s2", AddItem("p"), AddItem("kid", parent_ref=0))
    seed(store, "s1", AddItem("a"), AddItem("b"))
    result = store.copy_items("s1", "s2", None, actor="agent")
    assert isinstance(result, CopyApplied)
    board = store.get_board("s1")
    assert render(board, include_ids=True) == "- [ ] #1 a\n- [ ] #2 b\n- [ ] #3 p\n  - [ ] #4 kid\n"
    kid = board.item(4)
    assert kid is not None
    assert kid.parent_id == 3


def test_a_user_copy_belongs_to_the_user_and_leaves_seen_alone(
    store: BoardStore, connect: ConnFactory
) -> None:
    seed(store, "s2", AddItem("Call John"))
    seed(store, "s1", AddItem("Mine"))
    before = seen_rev(connect, "s1")
    store.copy_items("s1", "s2", None, actor="user")
    copied = store.get_board("s1").item(2)
    assert copied is not None
    assert copied.updated_by == "user"
    assert seen_rev(connect, "s1") == before


def test_an_agent_copy_advances_seen_when_the_agent_was_up_to_date(
    store: BoardStore, connect: ConnFactory
) -> None:
    seed(store, "s2", AddItem("Call John"))
    seed(store, "s1", AddItem("Mine"))
    result = store.copy_items("s1", "s2", None, actor="agent")
    assert isinstance(result, CopyApplied)
    assert seen_rev(connect, "s1") == result.applied.rev == 2


def test_an_agent_copy_leaves_seen_when_the_agent_was_behind(
    store: BoardStore, connect: ConnFactory
) -> None:
    seed(store, "s2", AddItem("Call John"))
    seed(store, "s1", AddItem("Mine"))
    store.apply("s1", [AddItem("Theo item")], actor="user", base_rev=1)
    store.copy_items("s1", "s2", None, actor="agent")
    assert seen_rev(connect, "s1") == 1


def test_target_at_98_items_copies_2_and_reports_overflow_3(store: BoardStore) -> None:
    seed(store, "s2", *numbered("src", 5))
    seed(store, "s1", *numbered("mine", 98))
    result = store.copy_items("s1", "s2", None, actor="agent")
    assert isinstance(result, CopyApplied)
    assert (result.copied, result.skipped, result.overflow) == (2, 0, 3)
    assert len(store.get_board("s1").items) == 100


def test_target_at_100_items_copies_0_without_error(store: BoardStore) -> None:
    seed(store, "s2", *numbered("src", 3))
    seed(store, "s1", *numbered("mine", 100))
    result = store.copy_items("s1", "s2", None, actor="agent")
    assert isinstance(result, CopyApplied)
    assert (result.copied, result.skipped, result.overflow) == (0, 0, 3)
    assert len(store.get_board("s1").items) == 100


def test_unknown_id_returns_stale_and_writes_nothing(
    store: BoardStore, connect: ConnFactory
) -> None:
    seed(store, "s2", AddItem("one"))
    seed(store, "s1", AddItem("Mine"))
    target_before = store.get_board("s1")
    source_before = store.get_board("s2")
    journals = (journal(connect, "s1"), journal(connect, "s2"))
    result = store.copy_items("s1", "s2", [1, 9], actor="agent")
    assert isinstance(result, Stale)
    assert (result.reason, result.item_id, result.op_index) == ("not_found", 9, 1)
    assert result.board == target_before
    assert store.get_board("s1") == target_before
    assert store.get_board("s2") == source_before
    assert (journal(connect, "s1"), journal(connect, "s2")) == journals


def test_no_source_board_raises_and_writes_nothing(store: BoardStore, connect: ConnFactory) -> None:
    seed(store, "s1", AddItem("Mine"))
    before = board_count(connect)
    with pytest.raises(NoSourceBoard):
        store.copy_items("s1", "ghost", None, actor="agent")
    assert board_count(connect) == before
    assert store.get_board("s1").rev == 1


def test_same_root_raises_same_board(store: BoardStore, connect: ConnFactory) -> None:
    seed(store, "s1", AddItem("Mine"))
    with pytest.raises(SameBoard):
        store.copy_items("s1", "s1", None, actor="agent")
    assert board_count(connect) == 1


def test_a_copy_of_nothing_creates_no_board_row(store: BoardStore, connect: ConnFactory) -> None:
    seed(store, "s2", AddItem("done", checked=True))
    before = board_count(connect)
    result = store.copy_items("s9", "s2", None, actor="agent")
    assert isinstance(result, CopyApplied)
    assert result.copied == 0
    assert board_count(connect) == before
    seed(store, "s1", AddItem("Mine"))
    again = store.copy_items("s1", "s2", None, actor="agent")
    assert isinstance(again, CopyApplied)
    assert again.applied.rev == 1


def test_every_copied_item_gets_one_copied_row(store: BoardStore, connect: ConnFactory) -> None:
    seed(store, "s2", *numbered("src", 3))
    seed(store, "s1", AddItem("Mine"))
    result = store.copy_items("s1", "s2", None, actor="user")
    assert isinstance(result, CopyApplied)
    rows_copied = [c for c in journal(connect, "s1") if c.op == "copied"]
    assert [(c.item_id, c.text, c.rev, c.actor) for c in rows_copied] == [
        (2, "s2#1", 2, "user"),
        (3, "s2#2", 2, "user"),
        (4, "s2#3", 2, "user"),
    ]


def test_summary_line_counts_only_adds(store: BoardStore) -> None:
    seed(store, "s2", *numbered("src", 3))
    seed(store, "s1", AddItem("Mine"))
    result = store.copy_items("s1", "s2", None, actor="agent")
    assert isinstance(result, CopyApplied)
    applied = result.applied
    assert summary_line(applied.rev, applied.entries) == "rev 2: added 3 items"


def test_a_user_copy_shows_as_added_lines_in_the_delta_note(store: BoardStore) -> None:
    seed(store, "s2", AddItem("Call John"), AddItem("Pay rent"))
    seed(store, "s1", AddItem("Mine"))
    store.copy_items("s1", "s2", None, actor="user")
    unseen = store.unseen_changes("s1")
    assert unseen is not None
    note = delta.delta_note(unseen.rev, unseen.changes, unseen.covered)
    assert note is not None
    assert "added #2 Call John" in note
    assert "added #3 Pay rent" in note
    assert "copied" not in note
