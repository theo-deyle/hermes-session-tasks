"""The copy rules of D-40 to D-42 as pure functions. No SQL, no clock."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .model import AddItem, Item, display_order


@dataclass(frozen=True, slots=True)
class CopyPlan:
    ops: tuple[AddItem, ...]
    source_ids: tuple[int, ...]
    skipped: int
    overflow: int
    missing_id: int | None
    missing_index: int | None


def plan_copy(
    source: Sequence[Item],
    item_ids: Sequence[int] | None,
    target: Sequence[Item],
    capacity: int,
) -> CopyPlan:
    """Plan the adds that copy open top-level items of `source`, up to `capacity` items."""
    if capacity < 0:
        raise ValueError("capacity must not be negative")
    ops: list[AddItem] = []
    source_ids: list[int] = []
    overflow = 0
    for item in display_order(source):
        if item.parent_id is not None or item.checked:
            continue
        if len(ops) >= capacity:
            overflow += 1
            continue
        ops.append(AddItem(item.text))
        source_ids.append(item.id)
    return CopyPlan(tuple(ops), tuple(source_ids), 0, overflow, None, None)
