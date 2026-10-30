"""Hermes adapter: open the Hermes session store for reading. The only `hermes_state` import."""

from __future__ import annotations

from .lineage import SessionReader


def open_session_reader() -> SessionReader:
    """Open the active profile's `state.db` read only. Hermes owns that file; never write it.

    `SessionDB(read_only=True)` opens the file with `mode=ro`. A missing `state.db` raises
    `sqlite3.OperationalError`, which the resolver treats as "no lineage known". The caller
    closes the reader.
    """
    from hermes_state import SessionDB  # pyright: ignore[reportMissingImports]

    return SessionDB(read_only=True)
