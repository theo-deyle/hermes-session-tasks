"""BoardStore: read a board and apply a batch of item operations."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from . import aliases, rows, schema
from .db import ConnFactory, read_txn, write_txn
from .model import (
    JOURNAL_KEEP,
    MAX_ITEMS,
    Actor,
    AddItem,
    Applied,
    BadParentRef,
    Board,
    BoardFull,
    Change,
    ChangeOp,
    Clock,
    DepthExceeded,
    Item,
    Op,
    RemoveItem,
    SetChecked,
    SetText,
    Stale,
    StaleReason,
    WriteResult,
    check_session_id,
    clean_text,
    utc_now,
)
from .revision import check_base_rev, is_stale, target_id


class _StaleSignal(Exception):
    """Carries a rejected write out of the transaction, so the transaction rolls back."""

    def __init__(self, reason: StaleReason, op_index: int, item_id: int | None) -> None:
        super().__init__(reason)
        self.reason: StaleReason = reason
        self.op_index = op_index
        self.item_id = item_id


@dataclass(slots=True)
class _Batch:
    """State of one batch inside its write transaction."""

    conn: sqlite3.Connection
    root_id: str
    ops: Sequence[Op]
    actor: Actor
    now: str
    new_rev: int
    base_rev: int
    pre: Board
    next_id: int
    changed: list[int] = field(default_factory=list)
    entries: list[tuple[ChangeOp, int]] = field(default_factory=list)
    added: dict[int, int] = field(default_factory=dict)

    def journal(self, op: ChangeOp, item_id: int, text: str) -> None:
        change = Change(self.new_rev, self.actor, op, item_id, text, self.now)
        rows.insert_change(self.conn, self.root_id, change)
        self.changed.append(item_id)
        self.entries.append((op, item_id))


def _read_board(conn: sqlite3.Connection, root_id: str) -> Board:
    row = rows.read_board(conn, root_id)
    if row is None:
        return Board(root_id, 0, 1, ())
    items = rows.read_items(conn, root_id)
    return Board(row.root_id, row.rev, row.next_item_id, items, row.forked_from)


def _require(batch: _Batch, index: int, item_id: int) -> Item:
    """Read an item from the live state of the transaction, or reject as not_found."""
    item = rows.read_item(batch.conn, batch.root_id, item_id)
    if item is None:
        raise _StaleSignal("not_found", index, item_id)
    return item


def _require_fresh(batch: _Batch, index: int, op: Op) -> None:
    """Reject an op whose target changed after `base_rev`. This reads the pre-batch board."""
    if is_stale(batch.pre, op, batch.base_rev):
        raise _StaleSignal("stale", index, target_id(op))


def _resolve_parent(batch: _Batch, index: int, op: AddItem) -> int | None:
    if op.parent_ref is None:
        return op.parent_id
    ref = op.parent_ref
    if op.parent_id is not None:
        raise BadParentRef("set parent_id or parent_ref, not both", index)
    if isinstance(ref, bool) or not isinstance(ref, int) or not 0 <= ref < index:
        raise BadParentRef("parent_ref must point to an earlier operation", index)
    if not isinstance(batch.ops[ref], AddItem):
        raise BadParentRef("parent_ref must point to an AddItem", index)
    return batch.added[ref]


def _add(batch: _Batch, index: int, op: AddItem) -> None:
    text = clean_text(op.text, index)
    parent_id = _resolve_parent(batch, index, op)
    if parent_id is not None:
        parent = _require(batch, index, parent_id)
        _require_fresh(batch, index, op)
        if parent.parent_id is not None:
            raise DepthExceeded("a subtask cannot have subtasks", index)
    item = Item(
        id=batch.next_id,
        parent_id=parent_id,
        position=rows.next_position(batch.conn, batch.root_id, parent_id),
        text=text,
        checked=op.checked,
        rev=batch.new_rev,
        updated_by=batch.actor,
        created_at=batch.now,
        updated_at=batch.now,
    )
    rows.insert_item(batch.conn, batch.root_id, item)
    batch.journal("add", item.id, text)
    batch.added[index] = item.id
    batch.next_id += 1


def _touch(
    batch: _Batch, item: Item, *, text: str | None = None, checked: bool | None = None
) -> Item:
    """Return the item with new text or checked state, the new board rev, actor and time."""
    return replace(
        item,
        text=item.text if text is None else text,
        checked=item.checked if checked is None else checked,
        rev=batch.new_rev,
        updated_by=batch.actor,
        updated_at=batch.now,
    )


def _set_text(batch: _Batch, index: int, op: SetText) -> None:
    text = clean_text(op.text, index)
    item = _require(batch, index, op.item_id)
    _require_fresh(batch, index, op)
    if text == item.text:
        return
    rows.update_item(batch.conn, batch.root_id, _touch(batch, item, text=text))
    batch.journal("text", item.id, text)


def _set_checked(batch: _Batch, index: int, op: SetChecked) -> None:
    item = _require(batch, index, op.item_id)
    _require_fresh(batch, index, op)
    if op.checked == item.checked:
        return
    rows.update_item(batch.conn, batch.root_id, _touch(batch, item, checked=op.checked))
    batch.journal("check" if op.checked else "uncheck", item.id, item.text)


def _remove(batch: _Batch, index: int, op: RemoveItem) -> None:
    item = _require(batch, index, op.item_id)
    _require_fresh(batch, index, op)
    subtasks = [
        row for row in rows.read_items(batch.conn, batch.root_id) if row.parent_id == item.id
    ]
    rows.delete_item(batch.conn, batch.root_id, item.id)
    for removed in (item, *subtasks):
        batch.journal("remove", removed.id, removed.text)


def _run_op(batch: _Batch, index: int, op: Op) -> None:
    match op:
        case AddItem():
            _add(batch, index, op)
        case SetText():
            _set_text(batch, index, op)
        case SetChecked():
            _set_checked(batch, index, op)
        case RemoveItem():
            _remove(batch, index, op)


@dataclass(frozen=True)
class BoardStore:
    connect: ConnFactory
    clock: Clock = utc_now

    def get_board(self, root_id: str) -> Board:
        """Read a board in one snapshot. An unknown root gives an empty board, no row."""
        check_session_id(root_id)
        with schema.open_db(self.connect) as conn, read_txn(conn):
            return _read_board(conn, root_id)

    def list_boards(self) -> tuple[rows.BoardSummary, ...]:
        """List every board root, newest first, with its open and total item counts."""
        with schema.open_db(self.connect) as conn, read_txn(conn):
            return rows.list_board_summaries(conn)

    def user_touched_ids(self, root_id: str) -> frozenset[int]:
        """Return the ids of items that Theo ever changed, read from the changes journal.

        `updated_by` only names the last writer. This set keeps Theo's mark after an agent
        change. The journal keeps the newest `JOURNAL_KEEP` rows, so an older touch can drop out.
        """
        check_session_id(root_id)
        with schema.open_db(self.connect) as conn, read_txn(conn):
            return rows.read_user_touched_ids(conn, root_id)

    def unseen_changes(self, root_id: str) -> rows.Unseen | None:
        """Return Theo's changes that the agent has not seen, or None when there are none.

        One read snapshot. The journal is covered when it still holds every row after
        `agent_seen_rev`: fewer than `JOURNAL_KEEP` rows, or an oldest rev at or below it.
        """
        check_session_id(root_id)
        with schema.open_db(self.connect) as conn, read_txn(conn):
            seen = rows.read_seen(conn, root_id)
            if seen is None or seen[0] <= seen[1]:
                return None
            rev, seen_rev = seen
            changes = rows.read_user_changes_after(conn, root_id, seen_rev)
            count, oldest_rev = rows.journal_span(conn, root_id)
            covered = count < JOURNAL_KEEP or oldest_rev <= seen_rev
            return rows.Unseen(rev, seen_rev, changes, covered)

    def mark_seen(self, root_id: str, rev: int) -> None:
        """Record that the agent has seen the board up to `rev`. The mark never moves down."""
        check_session_id(root_id)
        with schema.open_db(self.connect) as conn, write_txn(conn):
            rows.mark_seen(conn, root_id, rev)

    def apply(self, root_id: str, ops: Sequence[Op], *, actor: Actor, base_rev: int) -> WriteResult:
        """Apply a batch of operations in one write transaction, all or nothing.

        Return `Applied`, or `Stale` with the current board when a target is missing or
        changed after `base_rev`. A rule violation raises a `BoardError` subclass. Either
        way a rejected batch writes nothing.
        """
        check_session_id(root_id)
        check_base_rev(base_rev)
        if not ops:
            board = self.get_board(root_id)
            return Applied(board, board.rev, ())
        try:
            with schema.open_db(self.connect) as conn, write_txn(conn):
                return self._apply(conn, root_id, ops, actor, base_rev)
        except _StaleSignal as stale:
            board = self.get_board(root_id)
            return Stale(board, stale.reason, stale.op_index, stale.item_id)

    def _apply(
        self,
        conn: sqlite3.Connection,
        root_id: str,
        ops: Sequence[Op],
        actor: Actor,
        base_rev: int,
    ) -> Applied:
        now = self.clock()
        pre = _read_board(conn, root_id)
        row = rows.read_board(conn, root_id)
        if row is None:
            row = rows.create_board(conn, root_id, now)
            aliases.put_alias(conn, root_id, root_id)
        batch = _Batch(conn, root_id, ops, actor, now, row.rev + 1, base_rev, pre, row.next_item_id)
        for index, op in enumerate(ops):
            _run_op(batch, index, op)
        if rows.count_items(conn, root_id) > MAX_ITEMS:
            raise BoardFull(f"a board holds at most {MAX_ITEMS} items", None)
        if not batch.changed:
            return Applied(_read_board(conn, root_id), row.rev, ())
        rows.save_board(conn, root_id, batch.new_rev, batch.next_id, now)
        rows.prune_changes(conn, root_id, JOURNAL_KEEP)
        if actor == "agent":
            rows.advance_seen(conn, root_id, row.rev, batch.new_rev)
        changed_ids = tuple(dict.fromkeys(batch.changed))
        return Applied(_read_board(conn, root_id), batch.new_rev, changed_ids, tuple(batch.entries))
