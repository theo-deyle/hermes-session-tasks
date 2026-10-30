"""Parameterised SQL for the aliases table: session id to board root id."""

from __future__ import annotations

import sqlite3

ALIASES = "aliases"


def get_alias(conn: sqlite3.Connection, session_id: str) -> str | None:
    row = conn.execute(f"SELECT root_id FROM {ALIASES} WHERE session_id = ?", (session_id,))
    found = row.fetchone()
    return None if found is None else str(found[0])


def put_alias(conn: sqlite3.Connection, session_id: str, root_id: str) -> None:
    """Record an alias. The first alias wins and an alias never moves."""
    sql = f"INSERT OR IGNORE INTO {ALIASES} (session_id, root_id) VALUES (?, ?)"
    conn.execute(sql, (session_id, root_id))
