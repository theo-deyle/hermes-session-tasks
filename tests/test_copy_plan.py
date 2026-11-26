"""plan_copy: selection, the skip rule, the cap and a missing id, as pure rules."""

from __future__ import annotations

import pytest
from session_tasks.copy_plan import plan_copy
from session_tasks.model import AddItem, Item

STAMP = "2026-10-30T12:00:00.000000Z"


def item(
    item_id: int,
    text: str,
    *,
    checked: bool = False,
    parent: int | None = None,
    position: int | None = None,
) -> Item:
    return Item(
        id=item_id,
        parent_id=parent,
        position=item_id if position is None else position,
        text=text,
        checked=checked,
        rev=1,
        updated_by="user",
        created_at=STAMP,
        updated_at=STAMP,
    )


def test_all_open_brings_open_subtasks_under_their_parent() -> None:
    source = [
        item(1, "p"),
        item(2, "c2", parent=1),
        item(3, "c3", parent=1, checked=True),
    ]
    plan = plan_copy(source, None, [], 100)
    assert plan.ops == (AddItem("p"), AddItem("c2", parent_ref=0))
    assert plan.source_ids == (1, 2)


def test_all_open_moves_an_open_subtask_of_a_checked_parent_to_top_level() -> None:
    source = [item(1, "p", checked=True), item(2, "c", parent=1)]
    plan = plan_copy(source, None, [], 100)
    assert plan.ops == (AddItem("c"),)
    assert plan.source_ids == (2,)


def test_all_open_skips_checked_top_level_items() -> None:
    source = [item(1, "done", checked=True), item(2, "open")]
    plan = plan_copy(source, None, [], 100)
    assert plan.ops == (AddItem("open"),)
    assert plan.source_ids == (2,)


def test_chosen_ids_copy_in_display_order_checked_or_not() -> None:
    source = [item(1, "one"), item(2, "two"), item(3, "three", checked=True)]
    plan = plan_copy(source, (3, 1), [], 100)
    assert plan.ops == (AddItem("one"), AddItem("three"))
    assert plan.source_ids == (1, 3)


def test_chosen_parent_brings_its_open_subtasks() -> None:
    source = [
        item(1, "p", checked=True),
        item(2, "open kid", parent=1),
        item(3, "done kid", parent=1, checked=True),
    ]
    plan = plan_copy(source, (1,), [], 100)
    assert plan.ops == (AddItem("p"), AddItem("open kid", parent_ref=0))


def test_chosen_subtask_without_its_parent_becomes_top_level() -> None:
    source = [item(1, "p"), item(2, "kid", parent=1), item(3, "other")]
    plan = plan_copy(source, (2, 3), [], 100)
    assert plan.ops == (AddItem("kid"), AddItem("other"))
    assert plan.source_ids == (2, 3)


def test_chosen_parent_and_chosen_checked_subtask_copy_the_subtask_under_the_parent() -> None:
    source = [item(1, "p"), item(2, "kid", parent=1, checked=True)]
    plan = plan_copy(source, (1, 2), [], 100)
    assert plan.ops == (AddItem("p"), AddItem("kid", parent_ref=0))


def test_open_target_text_is_skipped_and_counted() -> None:
    plan = plan_copy([item(1, "Call John")], None, [item(7, "Call John")], 100)
    assert (plan.ops, plan.skipped, plan.overflow) == ((), 1, 0)


def test_compare_is_case_sensitive() -> None:
    plan = plan_copy([item(1, "call john")], None, [item(7, "Call John")], 100)
    assert plan.ops == (AddItem("call john"),)
    assert plan.skipped == 0


def test_checked_target_text_does_not_block() -> None:
    plan = plan_copy([item(1, "Call John")], None, [item(7, "Call John", checked=True)], 100)
    assert plan.ops == (AddItem("Call John"),)
    assert plan.skipped == 0


def test_a_text_planned_earlier_in_the_batch_counts_as_open() -> None:
    plan = plan_copy([item(1, "same"), item(2, "same")], None, [], 100)
    assert plan.ops == (AddItem("same"),)
    assert plan.skipped == 1


def test_a_skipped_parent_skips_its_subtasks_and_counts_each() -> None:
    source = [item(1, "p"), item(2, "a", parent=1), item(3, "b", parent=1)]
    plan = plan_copy(source, None, [item(9, "p")], 100)
    assert (plan.ops, plan.skipped, plan.overflow) == ((), 3, 0)


def test_capacity_cuts_in_display_order_and_counts_overflow() -> None:
    source = [item(1, "p"), item(2, "a", parent=1), item(3, "b", parent=1)]
    plan = plan_copy(source, None, [], 2)
    assert plan.ops == (AddItem("p"), AddItem("a", parent_ref=0))
    assert plan.overflow == 1
    none_fit = plan_copy(source, None, [], 0)
    assert (none_fit.ops, none_fit.overflow) == ((), 3)


def test_a_parent_that_does_not_fit_takes_its_subtasks_into_overflow() -> None:
    source = [item(1, "x"), item(2, "p"), item(3, "a", parent=2)]
    plan = plan_copy(source, None, [], 1)
    assert plan.ops == (AddItem("x"),)
    assert plan.overflow == 2


def test_skipped_items_use_no_capacity() -> None:
    source = [item(1, "dup"), item(2, "new")]
    plan = plan_copy(source, None, [item(9, "dup")], 1)
    assert plan.ops == (AddItem("new"),)
    assert (plan.skipped, plan.overflow) == (1, 0)


def test_unknown_id_names_the_first_missing_id_and_its_index() -> None:
    plan = plan_copy([item(1, "one")], (1, 9, 8), [], 100)
    assert (plan.missing_id, plan.missing_index, plan.ops) == (9, 1, ())


def test_negative_capacity_raises_value_error() -> None:
    with pytest.raises(ValueError, match="capacity"):
        plan_copy([], None, [], -1)
