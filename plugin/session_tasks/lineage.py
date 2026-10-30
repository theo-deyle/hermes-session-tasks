"""Session id to board root. The reader is a Protocol, so tests need no Hermes."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeAlias

from . import aliases, rows, schema
from .db import ConnFactory, read_txn, write_txn
from .model import Clock, InvalidSession, utc_now


class SessionReader(Protocol):
    """The four public `SessionDB` methods the plugin uses."""

    def get_session(self, session_id: str) -> dict[str, Any] | None: ...

    def get_compression_lineage(self, session_id: str) -> list[str]: ...

    def is_explicit_fork_child(self, session_id: str) -> bool: ...

    def close(self) -> None: ...


ReaderFactory: TypeAlias = Callable[[], SessionReader]
ResolutionKind: TypeAlias = Literal["plain", "compression", "branch", "delegate"]


@dataclass(frozen=True, slots=True)
class Resolution:
    root_id: str
    kind: ResolutionKind
    forked_from: str | None = None


@dataclass(frozen=True)
class SessionResolver:
    connect: ConnFactory
    open_reader: ReaderFactory
    clock: Clock = utc_now

    def resolve(self, session_id: str) -> Resolution:
        """Return the board root for a session. Never defaults to an empty or shared key.

        A known alias answers with no reader. An alias miss walks the compression lineage
        with one reader. A compression tip gets an alias once its root has a board.
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise InvalidSession("session id must be a non-empty string")
        with schema.open_db(self.connect) as conn:
            with read_txn(conn):
                known = aliases.get_alias(conn, session_id)
            if known is not None:
                return Resolution(known, "plain" if known == session_id else "compression")
            found = self._walk(session_id)
            if found.kind == "compression":
                _remember(conn, session_id, found.root_id)
            return found

    def _walk(self, session_id: str) -> Resolution:
        reader = self.open_reader()
        try:
            lineage = reader.get_compression_lineage(session_id)
        finally:
            reader.close()
        root_id = lineage[0] if lineage else session_id
        kind: ResolutionKind = "compression" if root_id != session_id else "plain"
        return Resolution(root_id, kind)


def _remember(conn: sqlite3.Connection, session_id: str, root_id: str) -> None:
    with write_txn(conn):
        if rows.read_board(conn, root_id) is not None:
            aliases.put_alias(conn, session_id, root_id)
