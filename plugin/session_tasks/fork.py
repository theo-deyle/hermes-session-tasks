"""Copy a parent board to a branch session. This is the one write that a read may trigger."""

from __future__ import annotations

from dataclasses import replace

from . import aliases, rows, schema
from .db import ConnFactory, write_txn
from .model import Change, Clock


def fork_copy(connect: ConnFactory, branch_id: str, parent_root: str, clock: Clock) -> bool:
    """Give `branch_id` its own copy of the board of `parent_root`. Return True when it copied.

    The check and the copy share one write transaction. A second process that waited on
    the lock finds the first commit and copies nothing. A parent with no board leads to
    no write at all, so a plain read never creates an empty board.
    """
    with schema.open_db(connect) as conn, write_txn(conn):
        if aliases.get_alias(conn, branch_id) is not None:
            return False
        if rows.read_board(conn, branch_id) is not None:
            return False
        if rows.read_board(conn, parent_root) is None:
            return False
        now = clock()
        parent_items = rows.read_items(conn, parent_root)
        new_ids = {item.id: number for number, item in enumerate(parent_items, start=1)}
        rows.create_board(conn, branch_id, now, forked_from=parent_root)
        for item in parent_items:
            parent_id = None if item.parent_id is None else new_ids[item.parent_id]
            copy = replace(item, id=new_ids[item.id], parent_id=parent_id, rev=1)
            rows.insert_item(conn, branch_id, copy)
        rows.save_board(conn, branch_id, rev=1, next_item_id=len(parent_items) + 1, now=now)
        change = Change(rev=1, actor="agent", op="forked", item_id=None, text=parent_root, ts=now)
        rows.insert_change(conn, branch_id, change)
        aliases.put_alias(conn, branch_id, branch_id)
        return True
