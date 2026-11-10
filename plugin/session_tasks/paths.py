"""Hermes adapter: open the plugin SQLite file. Every call opens a new connection."""

from __future__ import annotations

import os
import sqlite3
import time

PLUGIN_NAME = "hermes-session-tasks"
WAL_LOCK_RETRIES = 8


def connect() -> sqlite3.Connection:
    """Open the plugin data file through Hermes. Production wiring uses this function.

    Hermes owns WAL, the busy timeout and the old-SQLite fallback. The path follows the
    active Hermes home on every call, so nothing is cached.
    """
    from plugins.plugin_storage import plugin_db  # pyright: ignore[reportMissingImports]

    return plugin_db(PLUGIN_NAME)


def is_wal_reset_vulnerable(version_info: tuple[int, ...] | None = None) -> bool:
    """Whether SQLite has the WAL-reset bug (3.7.0-3.51.2; fixed 3.51.3, backports 3.50.7/3.44.6).

    Hermes keeps the same range in `hermes_cli.sqlite_runtime.is_sqlite_wal_reset_vulnerable` and
    gates every WAL activation on it. The twin repeats the range because it must not import Hermes;
    keep the two in step. https://sqlite.org/wal.html#walresetbug
    """
    info = tuple(sqlite3.sqlite_version_info if version_info is None else version_info)
    return not (
        info < (3, 7, 0)
        or info >= (3, 51, 3)
        or (3, 50, 7) <= info < (3, 51, 0)
        or (3, 44, 6) <= info < (3, 45, 0)
    )


def _enable_wal(conn: sqlite3.Connection) -> None:
    """Switch to WAL. Retry the transient "database is locked" that a concurrent first open causes.

    Hermes does the same in `hermes_cli.sqlite_util.open_db`, so this twin behaves like `connect()`:
    a build carrying the WAL-reset bug stays in DELETE, exactly as `apply_wal_with_fallback()` leaves it.
    """
    for attempt in range(WAL_LOCK_RETRIES):
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as exc:
            if str(exc).lower() != "database is locked" or attempt + 1 == WAL_LOCK_RETRIES:
                raise
            time.sleep(0.01 * 2**attempt)


def connect_path(path: str | os.PathLike[str]) -> sqlite3.Connection:
    """Open a plugin-shaped SQLite file at `path`, with no Hermes import.

    This is the twin of `connect()` for tests and tools that run without Hermes.
    Production wiring uses `connect()`.
    """
    conn = sqlite3.connect(path, timeout=5.0)
    try:
        if not is_wal_reset_vulnerable():
            _enable_wal(conn)
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
    except BaseException:
        conn.close()
        raise
    return conn
