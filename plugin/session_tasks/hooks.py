"""Hook callbacks: the `board_edit` guard, the alias after a compaction, the turn text.

`pre_tool_call` fires for every tool call in the session. Its first statement returns
None for any tool but `board_edit`, so a fault here never blocks another tool. For
`board_edit` it fails closed: an argument it cannot read, or a board it cannot read,
blocks the call. It returns a block directive or None and nothing else (D-18).

`pre_llm_call` adds the nudge line and the board to each turn of a non-delegate session.
It returns a str or None and never raises (D-27, D-28).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

from . import edit_args, guard, nudge, tool_text
from .lineage import SessionResolver
from .model import BoardError
from .results import describe
from .store import BoardStore

GUARD_FAILED = "board_edit: the guard could not check this call. Try again."

log = logging.getLogger(__name__)


def _block(message: str) -> dict[str, str]:
    return {"action": "block", "message": message}


def _check(
    store: BoardStore, resolver: SessionResolver, args: object, session_id: object
) -> dict[str, str] | None:
    try:
        parsed = edit_args.parse(args if isinstance(args, Mapping) else {})
    except BoardError as exc:
        return _block("board_edit: " + describe(exc))
    if parsed.confirmed or not guard.has_candidates(parsed):
        return None
    if not isinstance(session_id, str) or not session_id.strip():
        return None
    resolution = resolver.resolve(session_id)
    if resolution.kind == "delegate":
        return None
    board = None
    user_touched: frozenset[int] = frozenset()
    if guard.needs_board(parsed):
        board = store.get_board(resolution.root_id)
        user_touched = store.user_touched_ids(resolution.root_id)
    reasons = guard.guarded_reasons(parsed, board, user_touched)
    return _block(guard.block_message(reasons)) if reasons else None


def make_pre_tool_call(
    store: BoardStore, resolver: SessionResolver
) -> Callable[..., dict[str, str] | None]:
    """Build the `pre_tool_call` callback. The session comes from the keyword, not the args."""

    def pre_tool_call(
        tool_name: str = "", args: object = None, session_id: object = "", **kwargs: object
    ) -> dict[str, str] | None:
        if tool_name != tool_text.BOARD_EDIT:
            return None
        try:
            return _check(store, resolver, args, session_id)
        except Exception:
            log.exception("board guard failed")
            return _block(GUARD_FAILED)

    return pre_tool_call


def make_post_compaction(resolver: SessionResolver) -> Callable[..., None]:
    """Build the `post_compaction` callback. It never raises."""

    def post_compaction(
        session_id: object = "", old_session_id: object = "", **kwargs: object
    ) -> None:
        if not isinstance(old_session_id, str) or not old_session_id.strip():
            return
        try:
            resolver.record_compaction(
                session_id if isinstance(session_id, str) else "", old_session_id
            )
        except Exception:
            log.exception("board alias after compaction failed")

    return post_compaction


def make_pre_llm_call(store: BoardStore, resolver: SessionResolver) -> Callable[..., str | None]:
    """Build the `pre_llm_call` callback. It returns the turn text, or None, and never raises."""

    def pre_llm_call(session_id: object = "", **kwargs: object) -> str | None:
        if not isinstance(session_id, str) or not session_id.strip():
            return None
        try:
            resolution = resolver.resolve(session_id)
            if resolution.kind == "delegate":
                return None
            return nudge.turn_context(store.get_board(resolution.root_id))
        except Exception:
            log.warning("board turn context failed", exc_info=True)
            return None

    return pre_llm_call
