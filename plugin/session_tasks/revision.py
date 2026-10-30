"""The stale-write rule as pure functions over the pre-batch board. No SQL and no I/O."""

from __future__ import annotations

from .model import AddItem, Board, Op, RemoveItem


def check_base_rev(base_rev: object) -> int:
    """Return `base_rev` when it is a non-negative int. A bool or any other type is rejected."""
    if isinstance(base_rev, bool) or not isinstance(base_rev, int) or base_rev < 0:
        raise ValueError(f"base_rev must be a non-negative int, got {base_rev!r}")
    return base_rev


def target_id(op: Op) -> int | None:
    """Return the id of the existing item the operation targets, or None for a top-level add."""
    if isinstance(op, AddItem):
        return op.parent_id
    return op.item_id


def is_stale(pre: Board, op: Op, base_rev: int) -> bool:
    """Say whether `op` targets an item that changed after the caller's `base_rev`.

    `pre` is the board as it stood before the batch. A target that is not in `pre` is not
    stale: it is new in this batch or missing, and the store answers not_found for a
    missing one. A parent delete is also stale when any of its subtasks changed.
    """
    item_id = target_id(op)
    if item_id is None:
        return False
    item = pre.item(item_id)
    if item is None:
        return False
    if item.rev > base_rev or base_rev > pre.rev:
        return True
    if isinstance(op, RemoveItem):
        return any(child.rev > base_rev for child in pre.children(item_id))
    return False
