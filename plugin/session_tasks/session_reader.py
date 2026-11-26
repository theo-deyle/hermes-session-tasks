"""Hermes adapter: open the Hermes session store for reading. The only Hermes session store import.

Hermes v0.24 moved session storage behind `persistence_assembly`. Its `hermes_state.SessionDB`
stand-in lacks `get_compression_lineage`, `is_explicit_fork_child` and `get_session_title`. This
module uses the storage interface when Hermes has it, and `SessionDB` on an older Hermes.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from .lineage import SessionReader


def open_session_reader() -> SessionReader:
    """Open the active profile's session store read only. Hermes owns it; never write it.

    A missing store raises `sqlite3.OperationalError`, which the resolver treats as
    "no lineage known". The caller closes the reader.
    """
    try:
        import persistence_assembly  # pyright: ignore[reportMissingImports]
    except ImportError:
        from hermes_state import SessionDB  # pyright: ignore[reportMissingImports]

        return SessionDB(read_only=True)
    return _open_store_reader(persistence_assembly)


def _open_store_reader(assembly: Any) -> SessionReader:
    scope = assembly.profile_scope()
    location = assembly.store_location(scope)
    if location is None or not location.exists():
        raise sqlite3.OperationalError("no Hermes session store")
    handle = assembly.open_persistence_reader(scope.profile_dir)
    return _StoreReader(handle, handle.__enter__())


class _StoreReader:
    """The `SessionReader` methods on a store handle of the Hermes storage interface."""

    def __init__(self, handle: Any, store: Any) -> None:
        self._handle = handle
        self._store = store

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        record = self._store.sessions.get(session_id)
        return None if record is None else record.as_session_row()

    def get_compression_lineage(self, session_id: str) -> list[str]:
        return list(self._store.lineage.lineage(session_id))

    def is_explicit_fork_child(self, session_id: str) -> bool:
        return bool(self._store.lineage.is_fork_child(session_id))

    def get_session_title(self, session_id: str) -> str | None:
        row = self.get_session(session_id)
        title = None if row is None else row.get("title")
        return title if isinstance(title, str) else None

    def get_messages(self, session_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        from persistence.conversation.messages import (  # pyright: ignore[reportMissingImports]
            TranscriptRead,
        )

        rows = self._store.messages.read_transcript(session_id, TranscriptRead(limit=limit))
        return [row.as_wire_row() for row in rows]

    def close(self) -> None:
        handle, self._handle = self._handle, None
        if handle is not None:
            handle.__exit__(None, None, None)
