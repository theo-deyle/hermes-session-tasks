"""Parameterised SQL for the aliases table: session id to board root id."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

ALIASES = "aliases"


def get_alias(conn: sqlite3.Connection, session_id: str) -> str | None:
    row = conn.execute(f"SELECT root_id FROM {ALIASES} WHERE session_id = ?", (session_id,))
    found = row.fetchone()
    return None if found is None else str(found[0])


def put_alias(conn: sqlite3.Connection, session_id: str, root_id: str) -> None:
    """Record an alias. The first alias wins and an alias never moves."""
    sql = f"INSERT OR IGNORE INTO {ALIASES} (session_id, root_id) VALUES (?, ?)"
    conn.execute(sql, (session_id, root_id))


def delete_aliases(conn: sqlite3.Connection, ids: Sequence[str]) -> None:
    """Delete every alias row whose session id or root id is in `ids`. It never deletes a board."""
    if not ids:
        return
    placeholders = ",".join("?" * len(ids))
    sql = (
        f"DELETE FROM {ALIASES} WHERE session_id IN ({placeholders}) OR root_id IN ({placeholders})"
    )
    conn.execute(sql, (*ids, *ids))
