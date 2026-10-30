"""Subtasks: one level, cascade remove, no auto check, ordering and parent_ref rules."""

from __future__ import annotations

from contextlib import closing

import pytest
from session_tasks import rows
from session_tasks.db import ConnFactory
from session_tasks.model import (
    AddItem,
    Applied,
    BadParentRef,
    Board,
    DepthExceeded,
    Op,
    RemoveItem,
    SetChecked,
    SetText,
)
from session_tasks.store import BoardStore

ROOT = "root-1"


def apply(store: BoardStore, ops: list[Op], base_rev: int) -> Applied:
    result = store.apply(ROOT, ops, actor="agent", base_rev=base_rev)
    assert isinstance(result, Applied)
    return result


def seed_parent_with_two_subtasks(store: BoardStore) -> Board:
    """Items: 1 parent, 2 and 3 its subtasks. The board rev is 1."""
    ops: list[Op] = [AddItem("parent"), AddItem("one", parent_ref=0), AddItem("two", parent_ref=0)]
    return apply(store, ops, 0).board


def test_subtask_hangs_under_its_parent_with_parent_id(store: BoardStore) -> None:
    apply(store, [AddItem("parent")], 0)

    board = apply(store, [AddItem("child", parent_id=1)], 1).board

    assert [(item.id, item.parent_id) for item in board.items] == [(1, None), (2, 1)]


def test_subtask_hangs_under_its_parent_with_parent_ref(store: BoardStore) -> None:
    board = apply(store, [AddItem("parent"), AddItem("child", parent_ref=0)], 0).board

    assert [(item.id, item.parent_id) for item in board.items] == [(1, None), (2, 1)]


def test_subtask_of_a_subtask_raises_depth_exceeded_with_parent_id(store: BoardStore) -> None:
    before = seed_parent_with_two_subtasks(store)

    with pytest.raises(DepthExceeded) as caught:
        store.apply(ROOT, [AddItem("deep", parent_id=2)], actor="agent", base_rev=1)

    assert caught.value.op_index == 0
    assert store.get_board(ROOT) == before


def test_subtask_of_a_subtask_raises_depth_exceeded_with_parent_ref(store: BoardStore) -> None:
    ops: list[Op] = [AddItem("p"), AddItem("s", parent_ref=0), AddItem("deep", parent_ref=1)]

    with pytest.raises(DepthExceeded) as caught:
        store.apply(ROOT, ops, actor="agent", base_rev=0)

    assert caught.value.op_index == 2
    assert store.get_board(ROOT) == Board(ROOT, 0, 1, ())


@pytest.mark.parametrize(
    "ops",
    [
        [AddItem("a", parent_ref=1), AddItem("b")],
        [AddItem("a", parent_ref=0)],
        [AddItem("p"), SetText(1, "x"), AddItem("s", parent_ref=1)],
        [AddItem("p"), AddItem("s", parent_id=1, parent_ref=0)],
        [AddItem("p"), AddItem("s", parent_ref=-1)],
    ],
    ids=["forward", "self", "not-an-add", "both-set", "negative"],
)
def test_bad_parent_ref_raises_and_writes_nothing(store: BoardStore, ops: list[Op]) -> None:
    with pytest.raises(BadParentRef):
        store.apply(ROOT, ops, actor="agent", base_rev=0)

    assert store.get_board(ROOT) == Board(ROOT, 0, 1, ())


def test_parent_without_subtasks_is_valid_and_removing_its_last_subtask_keeps_it(
    store: BoardStore,
) -> None:
    apply(store, [AddItem("parent"), AddItem("only", parent_ref=0)], 0)

    board = apply(store, [RemoveItem(2)], 1).board

    assert [(item.id, item.parent_id) for item in board.items] == [(1, None)]


def test_removing_a_parent_removes_its_subtasks_and_journals_each_one(
    store: BoardStore, connect: ConnFactory
) -> None:
    seed_parent_with_two_subtasks(store)

    result = apply(store, [RemoveItem(1)], 1)

    with closing(connect()) as conn:
        removals = [c for c in rows.read_changes(conn, ROOT) if c.op == "remove"]
    assert result.board.items == ()
    assert result.changed_ids == (1, 2, 3)
    assert [(c.item_id, c.text, c.rev) for c in removals] == [
        (1, "parent", 2),
        (2, "one", 2),
        (3, "two", 2),
    ]


def test_checking_a_parent_leaves_its_subtasks_unchanged(store: BoardStore) -> None:
    before = seed_parent_with_two_subtasks(store)

    board = apply(store, [SetChecked(1, True)], 1).board

    assert board.items[0].checked is True
    assert board.items[1:] == before.items[1:]


def test_checking_a_subtask_leaves_its_parent_unchanged(store: BoardStore) -> None:
    before = seed_parent_with_two_subtasks(store)

    board = apply(store, [SetChecked(2, True), SetChecked(3, True)], 1).board

    assert board.items[0] == before.items[0]
    assert [item.checked for item in board.items[1:]] == [True, True]


def test_subtask_positions_count_within_their_parent(store: BoardStore) -> None:
    ops: list[Op] = [
        AddItem("a"),
        AddItem("b"),
        AddItem("a1", parent_ref=0),
        AddItem("b1", parent_ref=1),
        AddItem("a2", parent_ref=0),
        AddItem("b2", parent_ref=1),
    ]

    board = apply(store, ops, 0).board

    assert [(item.text, item.position) for item in board.items] == [
        ("a", 0),
        ("a1", 0),
        ("a2", 1),
        ("b", 1),
        ("b1", 0),
        ("b2", 1),
    ]
