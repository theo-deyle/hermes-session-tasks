"""Item operations on one board: add, rename, check, remove, caps, text rules and ordering."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from session_tasks import rows
from session_tasks.db import ConnFactory
from session_tasks.model import (
    AddItem,
    Applied,
    Board,
    BoardFull,
    EmptyText,
    InvalidSession,
    Item,
    RemoveItem,
    SetChecked,
    SetText,
    Stale,
    TextTooLong,
)
from session_tasks.store import BoardStore

ROOT = "root-1"


def add_texts(store: BoardStore, *texts: str, root_id: str = ROOT) -> Board:
    """Add each text as its own batch, so each item gets its own board rev."""
    board = store.get_board(root_id)
    for text in texts:
        result = store.apply(root_id, [AddItem(text)], actor="agent", base_rev=board.rev)
        assert isinstance(result, Applied)
        board = result.board
    return board


def journal_size(connect: ConnFactory, root_id: str = ROOT) -> int:
    with closing(connect()) as conn:
        return len(rows.read_changes(conn, root_id))


def test_add_stores_every_item_field(store: BoardStore) -> None:
    store.apply(ROOT, [AddItem("Call John")], actor="user", base_rev=0)

    item = store.get_board(ROOT).items[0]

    assert (item.id, item.parent_id, item.position) == (1, None, 0)
    assert (item.text, item.checked, item.rev, item.updated_by) == ("Call John", False, 1, "user")
    assert item.created_at.endswith("Z")
    assert item.updated_at == item.created_at


def test_add_with_checked_true_stores_a_checked_item(store: BoardStore) -> None:
    store.apply(ROOT, [AddItem("Done already", checked=True)], actor="agent", base_rev=0)

    assert store.get_board(ROOT).items[0].checked is True


def test_identical_texts_are_separate_items_with_distinct_ids(store: BoardStore) -> None:
    board = add_texts(store, "Call John", "Call John")

    assert [item.text for item in board.items] == ["Call John", "Call John"]
    assert [item.id for item in board.items] == [1, 2]


def test_set_text_and_set_checked_stamp_the_new_rev_and_the_actor(store: BoardStore) -> None:
    created = add_texts(store, "Call John").items[0]

    store.apply(ROOT, [SetText(1, "Call Jane")], actor="user", base_rev=1)
    renamed = store.get_board(ROOT).items[0]
    store.apply(ROOT, [SetChecked(1, True)], actor="agent", base_rev=2)
    checked = store.get_board(ROOT).items[0]

    assert (renamed.text, renamed.rev, renamed.updated_by) == ("Call Jane", 2, "user")
    assert renamed.updated_at > created.updated_at
    assert (checked.checked, checked.rev, checked.updated_by) == (True, 3, "agent")
    assert checked.updated_at > renamed.updated_at
    assert checked.created_at == created.created_at


def test_set_to_the_current_value_changes_nothing_and_keeps_the_rev(
    store: BoardStore, connect: ConnFactory
) -> None:
    before = add_texts(store, "Call John")
    journal_before = journal_size(connect)

    same_text = store.apply(ROOT, [SetText(1, "Call John")], actor="user", base_rev=1)
    same_check = store.apply(ROOT, [SetChecked(1, False)], actor="user", base_rev=1)

    assert isinstance(same_text, Applied) and isinstance(same_check, Applied)
    assert same_text.changed_ids == () and same_check.changed_ids == ()
    assert (same_text.rev, same_check.rev) == (1, 1)
    assert store.get_board(ROOT) == before
    assert journal_size(connect) == journal_before


@pytest.mark.parametrize("text", ["   ", "\t\n", "​", "\x07"])
def test_text_that_is_empty_after_sanitize_raises_empty_text(store: BoardStore, text: str) -> None:
    with pytest.raises(EmptyText):
        store.apply(ROOT, [AddItem(text)], actor="agent", base_rev=0)

    assert store.get_board(ROOT) == Board(ROOT, 0, 1, ())


def test_set_text_that_is_empty_after_sanitize_raises_and_keeps_the_item(
    store: BoardStore,
) -> None:
    before = add_texts(store, "Call John")

    with pytest.raises(EmptyText) as caught:
        store.apply(ROOT, [SetText(1, " ​ ")], actor="user", base_rev=1)

    assert caught.value.op_index == 0
    assert store.get_board(ROOT) == before


@pytest.mark.parametrize(
    "text",
    ["a" * 500, "é" * 250, "\U0001f600" * 500],
    ids=["ascii", "nfd", "emoji"],
)
def test_500_code_points_pass_and_501_raise_text_too_long(store: BoardStore, text: str) -> None:
    assert len(text) == 500

    store.apply(ROOT, [AddItem(text)], actor="agent", base_rev=0)
    with pytest.raises(TextTooLong):
        store.apply(ROOT, [AddItem(text + text[0])], actor="agent", base_rev=1)

    board = store.get_board(ROOT)
    assert [item.text for item in board.items] == [text]
    assert board.rev == 1


def test_zero_width_joiner_is_dropped_from_a_joined_emoji(store: BoardStore) -> None:
    store.apply(ROOT, [AddItem("\U0001f468‍\U0001f469")], actor="agent", base_rev=0)

    assert store.get_board(ROOT).items[0].text == "\U0001f468\U0001f469"


def test_exactly_100_items_pass_and_the_101st_raises_board_full_and_writes_nothing(
    store: BoardStore,
) -> None:
    full = store.apply(ROOT, [AddItem(f"item {n}") for n in range(100)], actor="agent", base_rev=0)
    assert isinstance(full, Applied)

    with pytest.raises(BoardFull) as caught:
        store.apply(ROOT, [AddItem("one too many")], actor="agent", base_rev=1)

    assert caught.value.op_index is None
    assert store.get_board(ROOT) == full.board


def test_a_batch_over_the_cap_on_a_fresh_board_writes_no_row(
    store: BoardStore, db_path: Path
) -> None:
    ops = [AddItem(f"item {n}") for n in range(101)]

    with pytest.raises(BoardFull):
        store.apply(ROOT, ops, actor="agent", base_rev=0)

    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM boards").fetchone() == (0,)
        assert conn.execute("SELECT COUNT(*) FROM items").fetchone() == (0,)


def test_a_batch_that_removes_and_adds_is_judged_by_its_end_state(store: BoardStore) -> None:
    store.apply(ROOT, [AddItem(f"item {n}") for n in range(100)], actor="agent", base_rev=0)

    result = store.apply(ROOT, [AddItem("new"), RemoveItem(1)], actor="agent", base_rev=1)

    assert isinstance(result, Applied)
    assert len(result.board.items) == 100


def test_new_item_goes_after_the_last_sibling(store: BoardStore) -> None:
    add_texts(store, "a", "b", "c")
    store.apply(ROOT, [RemoveItem(2)], actor="agent", base_rev=3)

    board = add_texts(store, "d")

    assert [(item.text, item.position) for item in board.items] == [("a", 0), ("c", 2), ("d", 3)]


def test_equal_positions_sort_by_id(store: BoardStore, connect: ConnFactory) -> None:
    add_texts(store, "a", "b", "c")
    with closing(connect()) as conn:
        conn.execute("UPDATE items SET position = 7")
        conn.commit()

    assert [item.id for item in store.get_board(ROOT).items] == [1, 2, 3]


def test_removed_highest_id_is_never_reused(store: BoardStore) -> None:
    add_texts(store, "a", "b", "c")
    store.apply(ROOT, [RemoveItem(3)], actor="agent", base_rev=3)
    store.apply(ROOT, [RemoveItem(1), RemoveItem(2)], actor="agent", base_rev=3)

    board = add_texts(store, "d")

    assert [item.id for item in board.items] == [4]
    assert board.next_item_id == 5


def test_two_reads_with_no_write_return_equal_boards(store: BoardStore) -> None:
    add_texts(store, "a", "b")
    store.apply(ROOT, [AddItem("sub", parent_id=1)], actor="agent", base_rev=2)

    assert store.get_board(ROOT) == store.get_board(ROOT)


def test_get_board_orders_top_level_by_position_with_subtasks_after_each_parent(
    store: BoardStore,
) -> None:
    add_texts(store, "a", "b")
    store.apply(
        ROOT,
        [AddItem("b1", parent_id=2), AddItem("a1", parent_id=1), AddItem("b2", parent_id=2)],
        actor="agent",
        base_rev=2,
    )

    items: tuple[Item, ...] = store.get_board(ROOT).items

    assert [item.text for item in items] == ["a", "a1", "b", "b1", "b2"]


def test_target_missing_returns_stale_not_found_with_the_current_board(
    store: BoardStore,
) -> None:
    before = add_texts(store, "a")

    result = store.apply(ROOT, [SetChecked(99, True)], actor="user", base_rev=1)

    assert isinstance(result, Stale)
    assert (result.reason, result.op_index, result.item_id) == ("not_found", 0, 99)
    assert result.board == before


@pytest.mark.parametrize("bad_key", ["", "   ", "\t\n", None, 7])
def test_store_rejects_a_blank_or_non_string_session_key(
    store: BoardStore, db_path: Path, bad_key: Any
) -> None:
    with pytest.raises(InvalidSession):
        store.apply(bad_key, [AddItem("x")], actor="agent", base_rev=0)
    with pytest.raises(InvalidSession):
        store.apply(bad_key, [], actor="agent", base_rev=0)
    with pytest.raises(InvalidSession):
        store.get_board(bad_key)

    assert not db_path.exists() or query_counts(db_path) == (0, 0)


def query_counts(db_path: Path) -> tuple[int, int]:
    with closing(sqlite3.connect(db_path)) as conn:
        boards = conn.execute("SELECT COUNT(*) FROM boards").fetchone()[0]
        aliases = conn.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
    return boards, aliases


def test_user_touched_ids_keep_theos_mark_after_an_agent_change(store: BoardStore) -> None:
    store.apply(ROOT, [AddItem("Theo's"), AddItem("Mine")], actor="agent", base_rev=0)
    store.apply(ROOT, [SetChecked(1, True)], actor="user", base_rev=1)
    store.apply(ROOT, [SetChecked(1, False)], actor="agent", base_rev=2)

    assert store.get_board(ROOT).item(1) is not None
    assert store.user_touched_ids(ROOT) == frozenset({1})


def test_user_touched_ids_is_empty_for_an_unknown_board(store: BoardStore) -> None:
    assert store.user_touched_ids("nothing-here") == frozenset()


def test_user_touched_ids_rejects_a_blank_session(store: BoardStore) -> None:
    with pytest.raises(InvalidSession):
        store.user_touched_ids(" ")
