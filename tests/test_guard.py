"""The guard rule: which `board_edit` ops need Theo's answer first. Pure functions, no I/O."""

from __future__ import annotations

from session_tasks.edit_args import ParsedEdit
from session_tasks.guard import block_message, guarded_reasons, has_candidates, needs_board
from session_tasks.model import (
    Actor,
    AddItem,
    Board,
    Item,
    Op,
    RemoveItem,
    SetChecked,
    SetText,
)

STAMP = "2026-10-30T12:00:00.000000Z"


def parsed(*ops: Op, confirmed: bool = False) -> ParsedEdit:
    return ParsedEdit(ops=ops, base_rev=1, confirmed=confirmed)


def item(item_id: int, updated_by: Actor) -> Item:
    return Item(
        id=item_id,
        parent_id=None,
        position=item_id,
        text=f"item {item_id}",
        checked=False,
        rev=1,
        updated_by=updated_by,
        created_at=STAMP,
        updated_at=STAMP,
    )


def board(*items: Item) -> Board:
    return Board(root_id="s1", rev=1, next_item_id=len(items) + 1, items=items)


def test_remove_of_any_item_is_guarded() -> None:
    reasons = guarded_reasons(parsed(RemoveItem(3)), board(item(3, "agent")))

    assert reasons == ("remove of #3",)


def test_uncheck_is_guarded_and_check_is_not() -> None:
    assert guarded_reasons(parsed(SetChecked(5, False)), None) == ("uncheck of #5",)
    assert guarded_reasons(parsed(SetChecked(5, True)), None) == ()


def test_reword_of_an_item_theo_touched_is_guarded() -> None:
    reasons = guarded_reasons(parsed(SetText(2, "new")), board(item(2, "user")))

    assert reasons == ("reword of #2",)


def test_reword_of_an_item_only_the_agent_touched_is_not_guarded() -> None:
    assert guarded_reasons(parsed(SetText(2, "new")), board(item(2, "agent"))) == ()


def test_reword_of_an_id_not_on_the_board_is_not_guarded() -> None:
    assert guarded_reasons(parsed(SetText(9, "new")), board(item(2, "user"))) == ()


def test_reword_with_no_board_is_guarded() -> None:
    assert guarded_reasons(parsed(SetText(2, "new")), None) == ("reword of #2",)


def test_adds_in_any_count_are_not_guarded() -> None:
    ops = tuple(AddItem(f"a{n}", parent_id=1 if n % 2 else None) for n in range(30))

    assert guarded_reasons(parsed(*ops), board(item(1, "user"))) == ()


def test_reasons_keep_op_order() -> None:
    ops = (
        AddItem("x"),
        RemoveItem(3),
        SetChecked(4, True),
        SetChecked(5, False),
        SetText(6, "y"),
    )

    reasons = guarded_reasons(parsed(*ops), board(item(6, "user")))

    assert reasons == ("remove of #3", "uncheck of #5", "reword of #6")


def test_block_message_text_is_exact() -> None:
    message = block_message(("remove of #3", "uncheck of #5"))

    assert message == (
        "board_edit: Theo must answer first for: remove of #3, uncheck of #5. "
        "Ask him one plain question in chat, then send the same call again with confirmed true."
    )


def test_needs_board_is_true_only_when_a_set_text_op_exists() -> None:
    assert needs_board(parsed(SetText(1, "a"))) is True
    assert needs_board(parsed(AddItem("a"), RemoveItem(1), SetChecked(1, False))) is False
    assert needs_board(parsed()) is False


def test_has_candidates_is_false_for_adds_and_checks_only() -> None:
    assert has_candidates(parsed(AddItem("a"), SetChecked(1, True))) is False
    assert has_candidates(parsed()) is False


def test_has_candidates_is_true_for_remove_uncheck_and_set_text() -> None:
    assert has_candidates(parsed(RemoveItem(1))) is True
    assert has_candidates(parsed(SetChecked(1, False))) is True
    assert has_candidates(parsed(AddItem("a"), SetText(1, "b"))) is True
