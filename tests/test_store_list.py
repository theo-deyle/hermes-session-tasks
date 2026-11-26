"""BoardStore.list_boards: counts, empty boards, and a stable order."""

from __future__ import annotations

from session_tasks.db import ConnFactory
from session_tasks.model import AddItem, RemoveItem
from session_tasks.rows import BoardSummary
from session_tasks.store import BoardStore

SAME_TIME = "2026-10-30T12:00:00.000000Z"


def test_new_file_lists_no_boards(store: BoardStore) -> None:
    assert store.list_boards() == ()


def test_counts_open_and_total_items_for_each_root(store: BoardStore) -> None:
    store.apply(
        "a", [AddItem("x"), AddItem("y", checked=True), AddItem("z")], actor="agent", base_rev=0
    )

    (summary,) = store.list_boards()

    assert (summary.root_id, summary.rev, summary.open, summary.total) == ("a", 1, 2, 3)


def test_a_board_with_every_item_removed_has_total_zero(store: BoardStore) -> None:
    store.apply("a", [AddItem("x")], actor="agent", base_rev=0)
    store.apply("a", [RemoveItem(1)], actor="user", base_rev=1)

    (summary,) = store.list_boards()

    assert (summary.root_id, summary.rev, summary.open, summary.total) == ("a", 2, 0, 0)


def test_boards_come_newest_first(store: BoardStore) -> None:
    for root in ("a", "b", "c"):
        store.apply(root, [AddItem("x")], actor="agent", base_rev=0)

    assert [summary.root_id for summary in store.list_boards()] == ["c", "b", "a"]


def test_equal_updated_at_sorts_by_root_id(connect: ConnFactory) -> None:
    same_time = BoardStore(connect, lambda: SAME_TIME)
    for root in ("b", "a"):
        same_time.apply(root, [AddItem("x")], actor="agent", base_rev=0)

    assert same_time.list_boards() == (
        BoardSummary("a", 1, 1, 1, SAME_TIME),
        BoardSummary("b", 1, 1, 1, SAME_TIME),
    )
