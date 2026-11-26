"""The copy rules of D-40 to D-42 as pure functions. No SQL, no clock."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .model import AddItem, Item, display_order


@dataclass(frozen=True, slots=True)
class CopyPlan:
    ops: tuple[AddItem, ...]
    source_ids: tuple[int, ...]
    skipped: int
    overflow: int
    missing_id: int | None
    missing_index: int | None


@dataclass(frozen=True, slots=True)
class _Group:
    """One item to copy as a top-level item, with the subtasks that come with it."""

    head: Item
    kids: tuple[Item, ...]


@dataclass(slots=True)
class _Tally:
    ops: list[AddItem] = field(default_factory=list)
    source_ids: list[int] = field(default_factory=list)
    skipped: int = 0
    overflow: int = 0


def _groups(source: Sequence[Item], chosen: frozenset[int] | None) -> list[_Group]:
    """Select what to copy, in display order (D-40, A3).

    With no `chosen` set, an open item is selected with its open subtasks, and an open
    subtask of a checked parent becomes a top-level item. With a `chosen` set, a chosen
    item is selected with its open or chosen subtasks, and a chosen subtask whose parent is
    not chosen becomes a top-level item at its parent's place.
    """
    ordered = display_order(source)
    kids_of: dict[int, list[Item]] = {}
    for item in ordered:
        if item.parent_id is not None:
            kids_of.setdefault(item.parent_id, []).append(item)
    groups: list[_Group] = []
    for top in ordered:
        if top.parent_id is not None:
            continue
        subtasks = kids_of.get(top.id, [])
        if chosen is None:
            wanted = [kid for kid in subtasks if not kid.checked]
            selected = not top.checked
        else:
            wanted = [kid for kid in subtasks if not kid.checked or kid.id in chosen]
            selected = top.id in chosen
        if selected:
            groups.append(_Group(top, tuple(wanted)))
            continue
        for kid in subtasks:
            if (chosen is None and not kid.checked) or (chosen is not None and kid.id in chosen):
                groups.append(_Group(kid, ()))
    return groups


def _first_missing(source: Sequence[Item], item_ids: Sequence[int]) -> tuple[int, int] | None:
    known = {item.id for item in source}
    for index, item_id in enumerate(item_ids):
        if item_id not in known:
            return item_id, index
    return None


def _take_group(group: _Group, texts: set[str], capacity: int, tally: _Tally) -> None:
    """Add a group to the tally: skip duplicates (D-42), then cut at the capacity."""
    head = group.head
    if head.text in texts:
        tally.skipped += 1 + len(group.kids)
        return
    if len(tally.ops) >= capacity:
        tally.overflow += 1
    else:
        head_index = len(tally.ops)
        tally.ops.append(AddItem(head.text))
        tally.source_ids.append(head.id)
        texts.add(head.text)
        for kid in group.kids:
            _take_kid(kid, head_index, texts, capacity, tally)
        return
    for kid in group.kids:
        if kid.text in texts:
            tally.skipped += 1
        else:
            tally.overflow += 1


def _take_kid(kid: Item, head_index: int, texts: set[str], capacity: int, tally: _Tally) -> None:
    if kid.text in texts:
        tally.skipped += 1
    elif len(tally.ops) >= capacity:
        tally.overflow += 1
    else:
        tally.ops.append(AddItem(kid.text, parent_ref=head_index))
        tally.source_ids.append(kid.id)
        texts.add(kid.text)


def plan_copy(
    source: Sequence[Item],
    item_ids: Sequence[int] | None,
    target: Sequence[Item],
    capacity: int,
) -> CopyPlan:
    """Plan the adds that copy items of `source` onto a board that holds `target`.

    `item_ids` None copies every open item. Else it copies the named items, checked or not.
    Every copy starts unchecked. A text equal to an open target text, or to a text planned
    earlier in this batch, is skipped and counted, and a skipped parent skips its subtasks.
    The plan holds at most `capacity` ops, and a parent comes before its subtasks, so the
    cut never leaves a subtask without its parent. An unknown id gives a plan with no op.
    """
    if capacity < 0:
        raise ValueError("capacity must not be negative")
    chosen: frozenset[int] | None = None
    if item_ids is not None:
        missing = _first_missing(source, item_ids)
        if missing is not None:
            return CopyPlan((), (), 0, 0, missing[0], missing[1])
        chosen = frozenset(item_ids)
    texts = {item.text for item in target if not item.checked}
    tally = _Tally()
    for group in _groups(source, chosen):
        _take_group(group, texts, capacity, tally)
    return CopyPlan(
        tuple(tally.ops), tuple(tally.source_ids), tally.skipped, tally.overflow, None, None
    )
