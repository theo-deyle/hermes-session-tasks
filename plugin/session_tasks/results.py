"""Tool results as JSON strings. A failure has a top-level `error` key; a success never has one."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from .markdown import render
from .model import (
    AddItem,
    Applied,
    Board,
    BoardError,
    Op,
    RemoveItem,
    SetChecked,
    SetText,
    Stale,
)

NO_SESSION = "no session id; the board is not available here"
EMPTY_NOTE = "empty board"
DELEGATE_EDIT = (
    "board_edit does not work in a subagent session. "
    "Report the items to the session that started you; it adds them to the board."
)


def describe(exc: BoardError) -> str:
    """Name the failing operation and the rule. An error with no operation gives the rule alone."""
    if exc.op_index is not None:
        return f"op {exc.op_index}: {exc}"
    return str(exc)


def read_result(board: Board) -> str:
    """Return the board as markdown with ids, plus its revision (D-15).

    A board with no items adds the key `note` so the agent sees an empty board and not a fault.
    """
    result: dict[str, object] = {
        "ok": True,
        "rev": board.rev,
        "board": render(board, include_ids=True),
    }
    if not board.items:
        result["note"] = EMPTY_NOTE
    return json.dumps(result, ensure_ascii=False)


def error_result(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


_KIND_ORDER = ("added", "renamed", "checked", "unchecked", "removed")


def _kind(op: Op) -> str:
    match op:
        case AddItem():
            return "added"
        case SetText():
            return "renamed"
        case SetChecked(checked=True):
            return "checked"
        case SetChecked():
            return "unchecked"
        case RemoveItem():
            return "removed"


def _count_text(verb: str, count: int) -> str:
    return f"{verb} {count} item" if count == 1 else f"{verb} {count} items"


def summary_line(rev: int, ops: Sequence[Op], changed_ids: Sequence[int]) -> str:
    """Return one line such as `rev 7: added 3 items`. Counts follow the submitted ops."""
    if not changed_ids:
        return f"rev {rev}: no change"
    counts = Counter(_kind(op) for op in ops)
    parts = [_count_text(verb, counts[verb]) for verb in _KIND_ORDER if counts[verb]]
    return f"rev {rev}: " + ", ".join(parts)


def _changed_line(board: Board, item_id: int) -> str:
    item = board.item(item_id)
    if item is None:
        return f"- removed #{item_id}"
    return render(replace(board, items=(item,)), include_ids=True).rstrip("\n")


def applied_result(applied: Applied, ops: Sequence[Op]) -> str:
    """Return the new rev, a one-line summary and one agent-view line per changed item (D-13)."""
    result: dict[str, object] = {
        "ok": True,
        "rev": applied.rev,
        "summary": summary_line(applied.rev, ops, applied.changed_ids),
        "changed": [_changed_line(applied.board, item_id) for item_id in applied.changed_ids],
    }
    return json.dumps(result, ensure_ascii=False)


def _stale_text(stale: Stale, base_rev: int) -> str:
    if stale.reason == "not_found":
        return f"not found: #{stale.item_id} is not on the board (op {stale.op_index})"
    if stale.item_id is None:
        return f"stale: the board changed after rev {base_rev} (op {stale.op_index})"
    return f"stale: #{stale.item_id} changed after rev {base_rev} (op {stale.op_index})"


def stale_result(stale: Stale, base_rev: int) -> str:
    """Return a failure that carries the current board, so the agent can retry (D-14)."""
    result: dict[str, object] = {
        "error": _stale_text(stale, base_rev),
        "stale": True,
        "reason": stale.reason,
        "op_index": stale.op_index,
        "item_id": stale.item_id,
        "rev": stale.board.rev,
        "board": render(stale.board, include_ids=True),
    }
    return json.dumps(result, ensure_ascii=False)
