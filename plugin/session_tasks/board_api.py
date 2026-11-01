"""The route logic. Every outcome is a reply; a request fault never raises."""

from __future__ import annotations

from dataclasses import dataclass

from . import edit_args, paths, session_reader
from .board_json import board_dict
from .db import ConnFactory
from .lineage import ReaderFactory, Resolution, SessionResolver
from .model import Applied, BoardError, InvalidSession, Stale
from .results import DELEGATE_EDIT, NO_SESSION, describe, stale_text, summary_line
from .store import BoardStore


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


def _stale_reply(stale: Stale, base_rev: int, root_id: str) -> ApiReply:
    body: dict[str, object] = {
        "ok": False,
        "error": "stale",
        "reason": stale.reason,
        "op_index": stale.op_index,
        "item_id": stale.item_id,
        "message": stale_text(stale, base_rev),
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


@dataclass(frozen=True)
class BoardApi:
    store: BoardStore
    resolver: SessionResolver

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
        return _applied_reply(result, root_id)


def build(
    connect: ConnFactory = paths.connect,
    open_reader: ReaderFactory = session_reader.open_session_reader,
) -> BoardApi:
    """Build the api over the production adapters. The router calls this on every request."""
    return BoardApi(BoardStore(connect), SessionResolver(connect, open_reader))
