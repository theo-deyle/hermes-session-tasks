"""Tool handlers. The session comes from the `session_id` keyword and never from the arguments."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from . import edit_args
from .events import WriteListener
from .lineage import SessionResolver
from .model import BoardError, InvalidSession, Stale
from .results import (
    DELEGATE_EDIT,
    NO_SESSION,
    applied_result,
    describe,
    error_result,
    read_result,
    stale_result,
)
from .store import BoardStore

log = logging.getLogger(__name__)


def _no_listener(root_id: str, session_id: str, rev: int) -> None:
    return None


@dataclass(frozen=True)
class BoardTools:
    store: BoardStore
    resolver: SessionResolver
    after_write: WriteListener = _no_listener

    def board_read(
        self, args: Mapping[str, object], session_id: str | None = None, **kwargs: object
    ) -> str:
        """Return the board of the calling session. `args` is never read (TOOL-06)."""
        if not isinstance(session_id, str) or not session_id.strip():
            return error_result(NO_SESSION)
        try:
            resolution = self.resolver.resolve(session_id)
        except InvalidSession:
            return error_result(NO_SESSION)
        board = self.store.get_board(resolution.root_id)
        # A delegate reads the delegator's board, but the delegator never sees that result.
        if resolution.kind != "delegate":
            self._mark_seen(resolution.root_id, board.rev)
        return read_result(board)

    def _mark_seen(self, root_id: str, rev: int) -> None:
        """Record that the agent saw the board at `rev`. A fault here never breaks a tool result."""
        try:
            self.store.mark_seen(root_id, rev)
        except Exception:
            log.warning("board seen mark failed", exc_info=True)

    def board_edit(
        self, args: Mapping[str, object], session_id: str | None = None, **kwargs: object
    ) -> str:
        """Apply the ops of one call to the board of the calling session.

        The session comes from the keyword only. The handler does not check `confirmed`:
        the `pre_tool_call` hook is the hard guard (D-18).
        """
        if not isinstance(session_id, str) or not session_id.strip():
            return error_result(NO_SESSION)
        try:
            resolution = self.resolver.resolve(session_id)
        except InvalidSession:
            return error_result(NO_SESSION)
        if resolution.kind == "delegate":
            return error_result(DELEGATE_EDIT)
        try:
            parsed = edit_args.parse(args)
            # Zero is safe: every op on an existing item needs a base_rev, and a
            # top-level or parent_ref add is never stale.
            base_rev = parsed.base_rev if parsed.base_rev is not None else 0
            result = self.store.apply(
                resolution.root_id, parsed.ops, actor="agent", base_rev=base_rev
            )
        except BoardError as exc:
            return error_result(describe(exc))
        if isinstance(result, Stale):
            # The stale or not-found reply carries the whole board, so the agent saw it.
            self._mark_seen(resolution.root_id, result.board.rev)
            return stale_result(result, base_rev)
        if result.changed_ids:
            # The write is committed already. A listener fault must not turn it into an
            # error result, or the agent would repeat the adds.
            try:
                self.after_write(resolution.root_id, session_id, result.rev)
            except Exception:
                log.warning("board after_write listener failed", exc_info=True)
        return applied_result(result)
