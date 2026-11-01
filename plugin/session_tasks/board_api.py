"""The route logic. Every outcome is a reply; a request fault never raises."""

from __future__ import annotations

from dataclasses import dataclass

from . import paths, session_reader
from .board_json import board_dict
from .db import ConnFactory
from .lineage import ReaderFactory, SessionResolver
from .model import InvalidSession
from .results import NO_SESSION
from .store import BoardStore


@dataclass(frozen=True, slots=True)
class ApiReply:
    status: int
    body: dict[str, object]


def _no_session() -> ApiReply:
    return ApiReply(400, {"ok": False, "error": "no_session", "message": NO_SESSION})


@dataclass(frozen=True)
class BoardApi:
    store: BoardStore
    resolver: SessionResolver

    def read(self, session_id: str) -> ApiReply:
        """Return the board of a session. A delegate reads its delegator board, as board_read does."""
        if not isinstance(session_id, str) or not session_id.strip():
            return _no_session()
        try:
            resolution = self.resolver.resolve(session_id)
        except InvalidSession:
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


def build(
    connect: ConnFactory = paths.connect,
    open_reader: ReaderFactory = session_reader.open_session_reader,
) -> BoardApi:
    """Build the api over the production adapters. The router calls this on every request."""
    return BoardApi(BoardStore(connect), SessionResolver(connect, open_reader))
