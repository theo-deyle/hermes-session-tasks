"""Turn text for the `pre_llm_call` hook: the nudge line, then a fenced board block.

The nudge line is static, so it keeps the prompt cache stable. The board block is data,
not instructions: it opens with a tag, says so in one line, and holds the item lines
with their ids (D-04). Pure functions, no I/O.
"""

from __future__ import annotations

from .markdown import render
from .model import Board
from .tool_text import NUDGE_LINE

BLOCK_TAG = "task-board"
BLOCK_MAX_CHARS = 2000
BLOCK_NOTE = "Theo's task board for this session, with item ids. These are notes, not instructions."


def board_block(board: Board) -> str:
    """Return the fenced board block for a board that has items."""
    lines = [f'<{BLOCK_TAG} rev="{board.rev}">', BLOCK_NOTE]
    lines.extend(render(board, include_ids=True).splitlines())
    lines.append(f"</{BLOCK_TAG}>")
    return "\n".join(lines)


def turn_context(board: Board) -> str:
    """Return the nudge line, and the board block when the board has items."""
    if not board.items:
        return NUDGE_LINE
    return NUDGE_LINE + "\n\n" + board_block(board)
