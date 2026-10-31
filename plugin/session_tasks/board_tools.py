"""Tool handlers. The session comes from the `session_id` keyword and never from the arguments."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .lineage import SessionResolver
from .model import InvalidSession
from .results import NO_SESSION, error_result, read_result
from .store import BoardStore


@dataclass(frozen=True)
class BoardTools:
    store: BoardStore
    resolver: SessionResolver

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
        return read_result(self.store.get_board(resolution.root_id))
