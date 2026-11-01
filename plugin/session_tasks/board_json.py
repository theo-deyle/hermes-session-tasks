"""Core objects to JSON dicts for the routes. Item text stays plain text. This module does no I/O."""

from __future__ import annotations

from .model import Board, Item, display_order


def item_dict(item: Item) -> dict[str, object]:
    return {
        "id": item.id,
        "parent_id": item.parent_id,
        "position": item.position,
        "text": item.text,
        "checked": item.checked,
        "rev": item.rev,
        "updated_by": item.updated_by,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def board_dict(board: Board) -> dict[str, object]:
    """Return the board with its items in display order, each subtask after its parent."""
    return {
        "root_id": board.root_id,
        "rev": board.rev,
        "forked_from": board.forked_from,
        "items": [item_dict(item) for item in display_order(board.items)],
    }
