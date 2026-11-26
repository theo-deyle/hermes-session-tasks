"""The revision rule: stale writes return the current board and change nothing."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from session_tasks import rows
from session_tasks.db import ConnFactory
from session_tasks.model import (
    JOURNAL_KEEP,
    AddItem,
    Applied,
    Board,
    Op,
    RemoveItem,
    SetChecked,
    SetText,
    Stale,
)
from session_tasks.revision import check_base_rev, is_stale
from session_tasks.store import BoardStore

ROOT = "root-1"
TABLES = ("boards", "items", "aliases", "changes")


def apply(store: BoardStore, ops: list[Op], base_rev: int, root_id: str = ROOT) -> Applied:
    result = store.apply(root_id, ops, actor="agent", base_rev=base_rev)
    assert isinstance(result, Applied)
    return result


def dump(db_path: Path) -> dict[str, list[tuple[Any, ...]]]:
    with closing(sqlite3.connect(db_path)) as conn:
        return {t: conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall() for t in TABLES}


def seed_parent_with_subtask(store: BoardStore) -> Board:
    """Items: 1 parent (rev 1), 2 its subtask (rev 2). The board rev is 2."""
    apply(store, [AddItem("parent")], 0)
    return apply(store, [AddItem("child", parent_id=1)], 1).board


def test_item_at_base_rev_accepts_the_write(store: BoardStore) -> None:
    apply(store, [AddItem("a")], 0)
    apply(store, [SetText(1, "b")], 1)

    result = store.apply(ROOT, [SetText(1, "c")], actor="user", base_rev=2)

    assert isinstance(result, Applied)
    assert result.board.items[0].text == "c"


def test_item_one_rev_past_base_rev_is_stale_and_returns_the_current_board(
    store: BoardStore,
) -> None:
    apply(store, [AddItem("a")], 0)
    current = apply(store, [SetText(1, "b")], 1).board

    result = store.apply(ROOT, [SetText(1, "mine")], actor="user", base_rev=1)

    assert isinstance(result, Stale)
    assert (result.reason, result.op_index, result.item_id) == ("stale", 0, 1)
    assert result.board == current
    assert store.get_board(ROOT) == current


def test_stale_check_runs_before_the_no_op_check(store: BoardStore) -> None:
    apply(store, [AddItem("a")], 0)
    apply(store, [SetChecked(1, True)], 1)

    result = store.apply(ROOT, [SetChecked(1, True)], actor="user", base_rev=1)

    assert isinstance(result, Stale)


def test_base_rev_above_the_board_rev_makes_targeting_ops_stale_but_not_plain_adds(
    store: BoardStore,
) -> None:
    apply(store, [AddItem("a")], 0)

    set_text = store.apply(ROOT, [SetText(1, "b")], actor="user", base_rev=5)
    set_checked = store.apply(ROOT, [SetChecked(1, True)], actor="user", base_rev=5)
    remove = store.apply(ROOT, [RemoveItem(1)], actor="user", base_rev=5)
    subtask = store.apply(ROOT, [AddItem("s", parent_id=1)], actor="user", base_rev=5)
    plain = store.apply(ROOT, [AddItem("plain")], actor="user", base_rev=5)

    assert all(isinstance(r, Stale) for r in (set_text, set_checked, remove, subtask))
    assert isinstance(plain, Applied)


@pytest.mark.parametrize("base_rev", [-1, True, 1.0, "3", None])
def test_invalid_base_rev_raises_value_error(
    store: BoardStore, db_path: Path, base_rev: Any
) -> None:
    with pytest.raises(ValueError, match="base_rev"):
        store.apply(ROOT, [AddItem("a")], actor="agent", base_rev=base_rev)

    assert not db_path.exists()


def test_check_base_rev_returns_a_valid_value_unchanged() -> None:
    assert check_base_rev(0) == 0
    assert check_base_rev(7) == 7


def test_removing_a_parent_is_stale_when_a_subtask_changed_after_base_rev(
    store: BoardStore,
) -> None:
    seed_parent_with_subtask(store)
    current = apply(store, [SetText(2, "child, renamed")], 2).board

    result = store.apply(ROOT, [RemoveItem(1)], actor="user", base_rev=2)

    assert isinstance(result, Stale)
    assert (result.reason, result.item_id) == ("stale", 1)
    assert store.get_board(ROOT) == current


def test_removing_a_parent_is_stale_when_a_subtask_was_added_after_base_rev(
    store: BoardStore,
) -> None:
    apply(store, [AddItem("parent")], 0)
    current = apply(store, [AddItem("late child", parent_id=1)], 1).board

    result = store.apply(ROOT, [RemoveItem(1)], actor="user", base_rev=1)

    assert isinstance(result, Stale)
    assert store.get_board(ROOT) == current


def test_removing_a_parent_succeeds_when_no_subtask_changed_after_base_rev(
    store: BoardStore,
) -> None:
    seed_parent_with_subtask(store)

    result = store.apply(ROOT, [RemoveItem(1)], actor="user", base_rev=2)

    assert isinstance(result, Applied)
    assert result.board.items == ()


def test_two_ops_on_one_item_in_one_batch_apply_in_order(store: BoardStore) -> None:
    apply(store, [AddItem("a")], 0)

    result = apply(store, [SetText(1, "b"), SetChecked(1, True), SetText(1, "c")], 1)

    item = result.board.items[0]
    assert (item.text, item.checked, item.rev) == ("c", True, 2)
    assert (result.rev, result.changed_ids) == (2, (1,))


def test_remove_then_set_text_on_the_same_item_returns_not_found_at_op_index_1(
    store: BoardStore,
) -> None:
    before = apply(store, [AddItem("a")], 0).board

    result = store.apply(ROOT, [RemoveItem(1), SetText(1, "x")], actor="user", base_rev=1)

    assert isinstance(result, Stale)
    assert (result.reason, result.op_index, result.item_id) == ("not_found", 1, 1)
    assert result.board == before


def test_an_item_added_earlier_in_the_batch_can_be_edited_later_in_it(store: BoardStore) -> None:
    result = apply(store, [AddItem("a"), SetChecked(1, True)], 0)

    assert result.board.items[0].checked is True


def test_writers_on_different_items_never_conflict(store: BoardStore) -> None:
    apply(store, [AddItem("a")], 0)
    apply(store, [AddItem("b")], 1)
    apply(store, [SetText(1, "a2")], 2)

    result = store.apply(ROOT, [SetText(2, "b2")], actor="user", base_rev=2)

    assert isinstance(result, Applied)
    assert [item.text for item in result.board.items] == ["a2", "b2"]


def test_rejected_batch_leaves_rev_items_and_journal_unchanged(
    store: BoardStore, db_path: Path
) -> None:
    apply(store, [AddItem("a")], 0)
    apply(store, [AddItem("b")], 1)
    apply(store, [SetText(2, "b2")], 2)
    before = dump(db_path)

    ops: list[Op] = [SetText(1, "a2"), AddItem("new"), RemoveItem(2)]
    result = store.apply(ROOT, ops, actor="user", base_rev=1)

    assert isinstance(result, Stale)
    assert result.op_index == 2
    assert dump(db_path) == before


def test_first_failing_op_names_the_op_index(store: BoardStore) -> None:
    apply(store, [AddItem("a")], 0)
    apply(store, [AddItem("b")], 1)
    apply(store, [SetText(2, "b2")], 2)

    ops: list[Op] = [SetText(1, "a2"), SetText(99, "x"), SetText(2, "stale")]
    result = store.apply(ROOT, ops, actor="user", base_rev=1)

    assert isinstance(result, Stale)
    assert (result.reason, result.op_index, result.item_id) == ("not_found", 1, 99)


def test_rev_rises_by_exactly_one_per_batch_and_reads_back_as_int(store: BoardStore) -> None:
    first = apply(store, [AddItem("a"), AddItem("b"), AddItem("c"), AddItem("d")], 0)
    second = apply(store, [SetText(1, "a2"), SetChecked(2, True), RemoveItem(3)], 1)

    assert (first.rev, second.rev) == (1, 2)
    assert type(second.rev) is int
    assert all(type(item.id) is int and type(item.rev) is int for item in second.board.items)
    assert {item.rev for item in second.board.items} == {1, 2}
    assert type(second.board.rev) is int


def test_empty_batch_returns_applied_and_creates_no_board_row(
    store: BoardStore, db_path: Path
) -> None:
    result = store.apply(ROOT, [], actor="agent", base_rev=0)

    assert result == Applied(Board(ROOT, 0, 1, ()), 0, ())
    assert all(rows_ == [] for rows_ in dump(db_path).values())


def test_empty_batch_on_an_existing_board_keeps_the_rev(store: BoardStore) -> None:
    before = apply(store, [AddItem("a")], 0).board

    result = store.apply(ROOT, [], actor="agent", base_rev=0)

    assert result == Applied(before, 1, ())


def test_set_text_on_an_unknown_board_returns_stale_not_found(
    store: BoardStore, db_path: Path
) -> None:
    result = store.apply("nobody", [SetText(1, "x")], actor="user", base_rev=0)

    assert isinstance(result, Stale)
    assert (result.reason, result.op_index, result.item_id) == ("not_found", 0, 1)
    assert result.board == Board("nobody", 0, 1, ())
    assert all(rows_ == [] for rows_ in dump(db_path).values())


def test_journal_keeps_the_last_100_rows_per_board(store: BoardStore, connect: ConnFactory) -> None:
    apply(store, [AddItem("a"), AddItem("b"), AddItem("c")], 0, root_id="other")
    rev = apply(store, [AddItem("a")], 0).rev
    for n in range(150):
        rev = apply(store, [SetText(1, f"text {n}")], rev).rev

    with closing(connect()) as conn:
        journal = rows.read_changes(conn, ROOT)
        other = rows.read_changes(conn, "other")
    assert JOURNAL_KEEP == 100
    assert len(journal) == 100
    assert journal[-1].rev == rev
    assert journal[0].rev == rev - 99
    assert len(other) == 3


def test_a_pruned_board_does_not_touch_another_boards_rows(
    store: BoardStore, connect: ConnFactory
) -> None:
    apply(store, [AddItem("x")], 0, root_id="other")
    rev = apply(store, [AddItem("a")], 0).rev
    for n in range(110):
        rev = apply(store, [SetText(1, f"text {n}")], rev).rev
    apply(store, [SetText(1, "again")], 1, root_id="other")

    with closing(connect()) as conn:
        assert len(rows.read_changes(conn, "other")) == 2


def test_is_stale_is_a_pure_rule_over_the_pre_batch_board() -> None:
    board = Board(ROOT, 3, 3, ())

    assert is_stale(board, AddItem("a"), 0) is False
    assert is_stale(board, SetText(9, "x"), 0) is False
