"""Parameterised SQL for the boards, items and changes tables."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import cast

from .model import Actor, Change, Item, display_order

BOARDS = "boards"
ITEMS = "items"
CHANGES = "changes"

BOARD_COLUMNS = "root_id, rev, next_item_id, forked_from, created_at, updated_at"
ITEM_COLUMNS = "id, parent_id, position, text, checked, rev, updated_by, created_at, updated_at"


@dataclass(frozen=True, slots=True)
class BoardRow:
    root_id: str
    rev: int
    next_item_id: int
    forked_from: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class BoardSummary:
    root_id: str
    rev: int
    open: int
    total: int
    updated_at: str


def read_board(conn: sqlite3.Connection, root_id: str) -> BoardRow | None:
    sql = f"SELECT {BOARD_COLUMNS} FROM {BOARDS} WHERE root_id = ?"
    row = conn.execute(sql, (root_id,)).fetchone()
    return None if row is None else BoardRow(*row)


def read_items(conn: sqlite3.Connection, root_id: str) -> tuple[Item, ...]:
    sql = f"SELECT {ITEM_COLUMNS} FROM {ITEMS} WHERE root_id = ?"
    found = (
        Item(
            id=row[0],
            parent_id=row[1],
            position=row[2],
            text=row[3],
            checked=bool(row[4]),
            rev=row[5],
            updated_by=cast(Actor, row[6]),
            created_at=row[7],
            updated_at=row[8],
        )
        for row in conn.execute(sql, (root_id,))
    )
    return display_order(found)


def create_board(
    conn: sqlite3.Connection, root_id: str, now: str, forked_from: str | None = None
) -> BoardRow:
    sql = (
        f"INSERT INTO {BOARDS} (root_id, rev, next_item_id, forked_from, created_at, updated_at) "
        "VALUES (?, 0, 1, ?, ?, ?)"
    )
    conn.execute(sql, (root_id, forked_from, now, now))
    return BoardRow(root_id, 0, 1, forked_from, now, now)


def save_board(
    conn: sqlite3.Connection, root_id: str, rev: int, next_item_id: int, now: str
) -> None:
    sql = f"UPDATE {BOARDS} SET rev = ?, next_item_id = ?, updated_at = ? WHERE root_id = ?"
    conn.execute(sql, (rev, next_item_id, now, root_id))


def insert_item(conn: sqlite3.Connection, root_id: str, item: Item) -> None:
    sql = f"INSERT INTO {ITEMS} (root_id, {ITEM_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    params = (
        root_id,
        item.id,
        item.parent_id,
        item.position,
        item.text,
        int(item.checked),
        item.rev,
        item.updated_by,
        item.created_at,
        item.updated_at,
    )
    conn.execute(sql, params)


def insert_change(conn: sqlite3.Connection, root_id: str, change: Change) -> None:
    sql = (
        f"INSERT INTO {CHANGES} (root_id, rev, actor, op, item_id, text, ts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    params = (root_id, change.rev, change.actor, change.op, change.item_id, change.text, change.ts)
    conn.execute(sql, params)


def next_position(conn: sqlite3.Connection, root_id: str, parent_id: int | None) -> int:
    """Return 0 for an empty sibling group, else the highest position plus 1."""
    if parent_id is None:
        sql = f"SELECT MAX(position) FROM {ITEMS} WHERE root_id = ? AND parent_id IS NULL"
        row = conn.execute(sql, (root_id,)).fetchone()
    else:
        sql = f"SELECT MAX(position) FROM {ITEMS} WHERE root_id = ? AND parent_id = ?"
        row = conn.execute(sql, (root_id, parent_id)).fetchone()
    return 0 if row is None or row[0] is None else int(row[0]) + 1


def _item_from_row(row: tuple[object, ...]) -> Item:
    return Item(
        id=cast(int, row[0]),
        parent_id=cast("int | None", row[1]),
        position=cast(int, row[2]),
        text=cast(str, row[3]),
        checked=bool(row[4]),
        rev=cast(int, row[5]),
        updated_by=cast(Actor, row[6]),
        created_at=cast(str, row[7]),
        updated_at=cast(str, row[8]),
    )


def read_item(conn: sqlite3.Connection, root_id: str, item_id: int) -> Item | None:
    sql = f"SELECT {ITEM_COLUMNS} FROM {ITEMS} WHERE root_id = ? AND id = ?"
    row = conn.execute(sql, (root_id, item_id)).fetchone()
    return None if row is None else _item_from_row(row)


def update_item(conn: sqlite3.Connection, root_id: str, item: Item) -> None:
    """Write the fields an operation can change: text, checked, rev, writer and time."""
    sql = (
        f"UPDATE {ITEMS} SET text = ?, checked = ?, rev = ?, updated_by = ?, updated_at = ? "
        "WHERE root_id = ? AND id = ?"
    )
    params = (
        item.text,
        int(item.checked),
        item.rev,
        item.updated_by,
        item.updated_at,
        root_id,
        item.id,
    )
    conn.execute(sql, params)


def delete_item(conn: sqlite3.Connection, root_id: str, item_id: int) -> None:
    """Delete one item. The foreign key cascade deletes its subtasks."""
    conn.execute(f"DELETE FROM {ITEMS} WHERE root_id = ? AND id = ?", (root_id, item_id))


def count_items(conn: sqlite3.Connection, root_id: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) FROM {ITEMS} WHERE root_id = ?", (root_id,)).fetchone()
    return int(row[0])


def read_changes(conn: sqlite3.Connection, root_id: str) -> tuple[Change, ...]:
    sql = f"SELECT rev, actor, op, item_id, text, ts FROM {CHANGES} WHERE root_id = ? ORDER BY seq"
    return tuple(Change(*row) for row in conn.execute(sql, (root_id,)))


def read_user_touched_ids(conn: sqlite3.Connection, root_id: str) -> frozenset[int]:
    """Return the ids of items that Theo changed, as the journal records it."""
    sql = (
        f"SELECT DISTINCT item_id FROM {CHANGES} "
        "WHERE root_id = ? AND actor = 'user' AND item_id IS NOT NULL"
    )
    return frozenset(int(row[0]) for row in conn.execute(sql, (root_id,)))


def prune_changes(conn: sqlite3.Connection, root_id: str, keep: int) -> None:
    """Delete this board's journal rows that are older than the newest `keep` rows."""
    sql = (
        f"DELETE FROM {CHANGES} WHERE root_id = ? AND seq NOT IN "
        f"(SELECT seq FROM {CHANGES} WHERE root_id = ? ORDER BY seq DESC LIMIT ?)"
    )
    conn.execute(sql, (root_id, root_id, keep))


def list_board_summaries(conn: sqlite3.Connection) -> tuple[BoardSummary, ...]:
    """Return one summary per board, newest first. A board with no items counts total 0."""
    sql = (
        "SELECT b.root_id, b.rev, "
        "COALESCE(SUM(CASE WHEN i.checked = 0 THEN 1 ELSE 0 END), 0), "
        f"COUNT(i.id), b.updated_at FROM {BOARDS} b LEFT JOIN {ITEMS} i ON i.root_id = b.root_id "
        "GROUP BY b.root_id ORDER BY b.updated_at DESC, b.root_id ASC"
    )
    return tuple(BoardSummary(*row) for row in conn.execute(sql))
