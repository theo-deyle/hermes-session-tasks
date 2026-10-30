"""Hermes adapter: open the plugin SQLite file. Every call opens a new connection."""

from __future__ import annotations

import os
import sqlite3

PLUGIN_NAME = "hermes-session-tasks"


def connect() -> sqlite3.Connection:
    """Open the plugin data file through Hermes. Production wiring uses this function.

    Hermes owns WAL, the busy timeout and the old-SQLite fallback. The path follows the
    active Hermes home on every call, so nothing is cached.
    """
    from plugins.plugin_storage import plugin_db  # pyright: ignore[reportMissingImports]

    return plugin_db(PLUGIN_NAME)


def connect_path(path: str | os.PathLike[str]) -> sqlite3.Connection:
    """Open a plugin-shaped SQLite file at `path`, with no Hermes import.

    This is the twin of `connect()` for tests and tools that run without Hermes.
    Production wiring uses `connect()`.
    """
    conn = sqlite3.connect(path, timeout=5.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
    except BaseException:
        conn.close()
        raise
    return conn
