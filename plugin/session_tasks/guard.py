"""The hard guard rule: which `board_edit` ops need the user's answer first (D-18, D-19).

A remove, an uncheck and a reword of an item that the user touched are guarded. Adds and
checks are never guarded. An item counts as touched by the user when its last writer is the user
or when the changes journal holds a change by them. These are pure functions. They do no I/O.
"""

from __future__ import annotations

from collections.abc import Sequence

from .edit_args import ParsedEdit
from .model import Board, Op, RemoveItem, SetChecked, SetText


def _is_candidate(op: Op) -> bool:
    if isinstance(op, SetChecked):
        return not op.checked
    return isinstance(op, RemoveItem | SetText)


def has_candidates(parsed: ParsedEdit) -> bool:
    """Say whether any op might be guarded. A reword is a candidate until the board is read."""
    return any(_is_candidate(op) for op in parsed.ops)


def needs_board(parsed: ParsedEdit) -> bool:
    """Say whether the guard must read the board: only a reword depends on who wrote the item."""
    return any(isinstance(op, SetText) for op in parsed.ops)


def _reason(op: Op, board: Board | None, user_touched: frozenset[int]) -> str | None:
    if isinstance(op, RemoveItem):
        return f"remove of #{op.item_id}"
    if isinstance(op, SetChecked):
        return None if op.checked else f"uncheck of #{op.item_id}"
    if isinstance(op, SetText):
        # With no board, the author is unknown. Err toward asking.
        item = None if board is None else board.item(op.item_id)
        if board is None or (
            item is not None and (item.updated_by == "user" or item.id in user_touched)
        ):
            return f"reword of #{op.item_id}"
    return None


def guarded_reasons(
    parsed: ParsedEdit, board: Board | None, user_touched: frozenset[int] = frozenset()
) -> tuple[str, ...]:
    """Return one short reason per guarded op, in op order.

    `user_touched` holds the ids of items that the user ever changed, so an agent change
    after theirs does not lift the guard.
    """
    reasons = (_reason(op, board, user_touched) for op in parsed.ops)
    return tuple(reason for reason in reasons if reason is not None)


def block_message(reasons: Sequence[str]) -> str:
    """Return the text that tells the agent to retry with confirmed or to ask the user first."""
    return (
        f"board_edit: the user must answer first for: {', '.join(reasons)}. "
        "If the user's own message named the change, send the same call again with confirmed true. "
        "Otherwise ask them one plain question in chat first. "
        "After they answer, send the same call again with confirmed true."
    )
