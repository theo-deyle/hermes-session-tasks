"""Render a board as a markdown checklist. This module does no I/O."""

from __future__ import annotations

from .model import Board, Item

SUBTASK_INDENT = "  "


def _line(item: Item, include_ids: bool) -> str:
    indent = SUBTASK_INDENT if item.parent_id is not None else ""
    box = "[x]" if item.checked else "[ ]"
    marker = f"#{item.id} " if include_ids else ""
    return f"{indent}- {box} {marker}{item.text}\n"


def render(board: Board, *, include_ids: bool) -> str:
    """Return one line per item in board order. An empty board gives an empty string.

    The agent view passes `include_ids=True` (D-04). The clipboard view for the user
    passes `include_ids=False` (D-05).
    """
    return "".join(_line(item, include_ids) for item in board.items)
