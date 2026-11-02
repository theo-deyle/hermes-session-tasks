"""The route logic. Every outcome is a reply; a request fault never raises."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from . import copy_args, edit_args, events, paths, session_reader
from .board_json import board_dict
from .db import ConnFactory
from .lineage import ReaderFactory, Resolution, SessionResolver
from .model import (
    NO_SOURCE_BOARD,
    SAME_BOARD,
    Applied,
    BoardError,
    CopyApplied,
    InvalidSession,
    Stale,
)
from .results import (
    DELEGATE_COPY,
    DELEGATE_EDIT,
    NO_SESSION,
    describe,
    source_missing_text,
    stale_text,
    summary_line,
)
from .store import BoardStore

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ApiReply:
    status: int
    body: dict[str, object]


def _no_session() -> ApiReply:
    return ApiReply(400, {"ok": False, "error": "no_session", "message": NO_SESSION})


def _invalid(op_index: int | None, rule: str, message: str) -> ApiReply:
    body: dict[str, object] = {
        "ok": False,
        "error": "invalid",
        "op_index": op_index,
        "rule": rule,
        "message": message,
    }
    return ApiReply(200, body)


def _stale_reply(stale: Stale, base_rev: int, root_id: str, message: str | None = None) -> ApiReply:
    body: dict[str, object] = {
        "ok": False,
        "error": "stale",
        "reason": stale.reason,
        "op_index": stale.op_index,
        "item_id": stale.item_id,
        "message": message if message is not None else stale_text(stale, base_rev),
        "root_id": root_id,
        "rev": stale.board.rev,
        "board": board_dict(stale.board),
    }
    return ApiReply(200, body)


def _applied_reply(applied: Applied, root_id: str) -> ApiReply:
    body: dict[str, object] = {
        "ok": True,
        "root_id": root_id,
        "rev": applied.rev,
        "summary": summary_line(applied.rev, applied.entries),
        "changed_ids": list(applied.changed_ids),
        "board": board_dict(applied.board),
    }
    return ApiReply(200, body)


def _copied_reply(result: CopyApplied, root_id: str) -> ApiReply:
    reply = _applied_reply(result.applied, root_id)
    body = {
        **reply.body,
        "copied": result.copied,
        "skipped": result.skipped,
        "overflow": result.overflow,
    }
    return ApiReply(reply.status, body)


def _no_listener(root_id: str, session_id: str, rev: int) -> None:
    return None


@dataclass(frozen=True)
class BoardApi:
    store: BoardStore
    resolver: SessionResolver
    after_write: events.WriteListener = _no_listener

    def _resolve(self, session_id: str) -> Resolution | None:
        """Return the resolution, or None when the session id is blank or invalid."""
        if not isinstance(session_id, str) or not session_id.strip():
            return None
        try:
            return self.resolver.resolve(session_id)
        except InvalidSession:
            return None

    def read(self, session_id: str) -> ApiReply:
        """Return the board of a session. A delegate reads its delegator board, as board_read does."""
        resolution = self._resolve(session_id)
        if resolution is None:
            return _no_session()
        board = self.store.get_board(resolution.root_id)
        body: dict[str, object] = {
            "ok": True,
            "session_id": session_id,
            "root_id": resolution.root_id,
            "rev": board.rev,
            "board": board_dict(board),
        }
        return ApiReply(200, body)

    def list_boards(self) -> ApiReply:
        boards = [
            {
                "root_id": summary.root_id,
                "rev": summary.rev,
                "open": summary.open,
                "total": summary.total,
                "updated_at": summary.updated_at,
            }
            for summary in self.store.list_boards()
        ]
        return ApiReply(200, {"ok": True, "boards": boards})

    def edit(self, session_id: str, ops: object, base_rev: object) -> ApiReply:
        """Apply Theo's ops as actor user. No confirmed key exists: the D-18 guard is for tools."""
        resolution = self._resolve(session_id)
        if resolution is None:
            return _no_session()
        if resolution.kind == "delegate":
            return _invalid(None, DELEGATE_EDIT, DELEGATE_EDIT)
        root_id = resolution.root_id
        base = 0
        try:
            parsed = edit_args.parse({"ops": ops, "base_rev": base_rev})
            # Zero is safe: every op on an existing item needs a base_rev.
            base = parsed.base_rev if parsed.base_rev is not None else 0
            result = self.store.apply(root_id, parsed.ops, actor="user", base_rev=base)
        except BoardError as exc:
            return _invalid(exc.op_index, str(exc), describe(exc))
        if isinstance(result, Stale):
            return _stale_reply(result, base, root_id)
        if result.changed_ids:
            # The write is committed already. A listener fault must not turn it into an error.
            try:
                self.after_write(root_id, session_id, result.rev)
            except Exception:
                log.warning("board after_write listener failed", exc_info=True)
        return _applied_reply(result, root_id)

    def copy(
        self, session_id: str, from_session_id: object, item_ids: object, base_rev: object
    ) -> ApiReply:
        """Copy items of another board onto the target board as actor user (D-46).

        The target is the focused session. The source board is only read, and a delegate
        target is refused before any write.
        """
        target = self._resolve(session_id)
        if target is None:
            return _no_session()
        if target.kind == "delegate":
            return _invalid(None, DELEGATE_COPY, DELEGATE_COPY)
        root_id = target.root_id
        base = 0
        try:
            parsed = copy_args.parse({
                "from_session_id": from_session_id,
                "item_ids": item_ids,
                "base_rev": base_rev,
            })
            base = parsed.base_rev if parsed.base_rev is not None else 0
            source = self._resolve(parsed.from_session_id)
            if source is None:
                return _invalid(None, NO_SOURCE_BOARD, NO_SOURCE_BOARD)
            if source.root_id == root_id:
                return _invalid(None, SAME_BOARD, SAME_BOARD)
            result = self.store.copy_items(root_id, source.root_id, parsed.item_ids, actor="user")
        except BoardError as exc:
            return _invalid(exc.op_index, str(exc), describe(exc))
        if isinstance(result, Stale):
            message = source_missing_text(result.item_id or 0)
            return _stale_reply(result, base, root_id, message)
        if result.applied.changed_ids:
            # The copy is committed already. A listener fault must not turn it into an error.
            try:
                self.after_write(root_id, session_id, result.applied.rev)
            except Exception:
                log.warning("board after_write listener failed", exc_info=True)
        return _copied_reply(result, root_id)


def build(
    connect: ConnFactory = paths.connect,
    open_reader: ReaderFactory = session_reader.open_session_reader,
    publish: events.Publisher = events.publish,
) -> BoardApi:
    """Build the api over the production adapters. The router calls this on every request."""
    return BoardApi(
        BoardStore(connect),
        SessionResolver(connect, open_reader),
        after_write=events.listener("user", publish),
    )
