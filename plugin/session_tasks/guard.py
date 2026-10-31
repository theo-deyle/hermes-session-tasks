"""The hard guard rule: which `board_edit` ops need Theo's answer first (D-18, D-19).

A remove, an uncheck and a reword of an item that Theo touched are guarded. Adds and
checks are never guarded. These are pure functions. They do no I/O.
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


def _reason(op: Op, board: Board | None) -> str | None:
    if isinstance(op, RemoveItem):
        return f"remove of #{op.item_id}"
    if isinstance(op, SetChecked):
        return None if op.checked else f"uncheck of #{op.item_id}"
    if isinstance(op, SetText):
        # With no board, the author is unknown. Err toward asking.
        item = None if board is None else board.item(op.item_id)
        if board is None or (item is not None and item.updated_by == "user"):
            return f"reword of #{op.item_id}"
    return None


def guarded_reasons(parsed: ParsedEdit, board: Board | None) -> tuple[str, ...]:
    """Return one short reason per guarded op, in op order."""
    reasons = (_reason(op, board) for op in parsed.ops)
    return tuple(reason for reason in reasons if reason is not None)


def block_message(reasons: Sequence[str]) -> str:
    """Return the text that tells the agent to retry with confirmed or to ask Theo first."""
    return (
        f"board_edit: Theo must answer first for: {', '.join(reasons)}. "
        "If Theo's own message named the change, send the same call again with confirmed true. "
        "Otherwise ask him one plain question in chat first. "
        "After he answers, send the same call again with confirmed true."
    )
