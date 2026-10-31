"""Tool results as JSON strings. A failure has a top-level `error` key; a success never has one."""

from __future__ import annotations

import json

from .markdown import render
from .model import Board, BoardError

NO_SESSION = "no session id; the board is not available here"


def describe(exc: BoardError) -> str:
    """Name the failing operation and the rule. An error with no operation gives the rule alone."""
    if exc.op_index is not None:
        return f"op {exc.op_index}: {exc}"
    return str(exc)


def read_result(board: Board) -> str:
    """Return the board as markdown with ids, plus its revision."""
    result: dict[str, object] = {
        "ok": True,
        "rev": board.rev,
        "board": render(board, include_ids=True),
    }
    return json.dumps(result, ensure_ascii=False)


def error_result(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
