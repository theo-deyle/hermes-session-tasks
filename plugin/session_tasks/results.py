"""Tool results as JSON strings. A failure has a top-level `error` key; a success never has one."""

from __future__ import annotations

import json
from collections.abc import Sequence

from .markdown import render
from .model import Applied, Board, BoardError, Op, Stale

NO_SESSION = "no session id; the board is not available here"
EMPTY_NOTE = "empty board"
DELEGATE_EDIT = ""


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


def summary_line(rev: int, ops: Sequence[Op], changed_ids: Sequence[int]) -> str:
    return ""


def applied_result(applied: Applied, ops: Sequence[Op]) -> str:
    return ""


def stale_result(stale: Stale, base_rev: int) -> str:
    return ""
