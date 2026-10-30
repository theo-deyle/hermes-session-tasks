"""BoardStore: read a board and apply a batch of item operations."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from . import aliases, rows, schema
from .db import ConnFactory, read_txn, write_txn
from .model import (
    Actor,
    AddItem,
    Applied,
    Board,
    Change,
    Clock,
    Item,
    Op,
    WriteResult,
    clean_text,
    utc_now,
)


def _read_board(conn: sqlite3.Connection, root_id: str) -> Board:
    row = rows.read_board(conn, root_id)
    if row is None:
        return Board(root_id, 0, 1, ())
    items = rows.read_items(conn, root_id)
    return Board(row.root_id, row.rev, row.next_item_id, items, row.forked_from)


@dataclass(frozen=True)
class BoardStore:
    connect: ConnFactory
    clock: Clock = utc_now

    def get_board(self, root_id: str) -> Board:
        """Read a board in one snapshot. An unknown root gives an empty board, no row."""
        with schema.open_db(self.connect) as conn, read_txn(conn):
            return _read_board(conn, root_id)

    def apply(self, root_id: str, ops: Sequence[Op], *, actor: Actor, base_rev: int) -> WriteResult:
        """Apply a batch inside one write transaction. Plan 01-03 adds the revision rule."""
        if not ops:
            board = self.get_board(root_id)
            return Applied(board, board.rev, ())
        with schema.open_db(self.connect) as conn, write_txn(conn):
            return self._apply(conn, root_id, ops, actor)

    def _apply(
        self, conn: sqlite3.Connection, root_id: str, ops: Sequence[Op], actor: Actor
    ) -> WriteResult:
        now = self.clock()
        row = rows.read_board(conn, root_id)
        if row is None:
            row = rows.create_board(conn, root_id, now)
            aliases.put_alias(conn, root_id, root_id)
        new_rev = row.rev + 1
        next_id = row.next_item_id
        changed: list[int] = []
        for index, op in enumerate(ops):
            if not isinstance(op, AddItem) or op.parent_id is not None or op.parent_ref is not None:
                raise NotImplementedError(
                    "only top-level AddItem is built; plan 01-03 adds the rest"
                )
            text = clean_text(op.text, index)
            item = Item(
                id=next_id,
                parent_id=None,
                position=rows.next_position(conn, root_id, None),
                text=text,
                checked=op.checked,
                rev=new_rev,
                updated_by=actor,
                created_at=now,
                updated_at=now,
            )
            rows.insert_item(conn, root_id, item)
            rows.insert_change(conn, root_id, Change(new_rev, actor, "add", next_id, text, now))
            changed.append(next_id)
            next_id += 1
        rows.save_board(conn, root_id, new_rev, next_id, now)
        return Applied(_read_board(conn, root_id), new_rev, tuple(changed))
