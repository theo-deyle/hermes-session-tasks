"""Schema v1, the `user_version` migration and the only way to open a migrated connection."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .db import ConnFactory, write_txn

SCHEMA_VERSION = 1

SCHEMA_V1: tuple[str, ...] = (
    """CREATE TABLE boards (
  root_id        TEXT PRIMARY KEY,
  rev            INTEGER NOT NULL DEFAULT 0,
  next_item_id   INTEGER NOT NULL DEFAULT 1,
  agent_seen_rev INTEGER NOT NULL DEFAULT 0,
  forked_from    TEXT,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL
)""",
    """CREATE TABLE items (
  root_id    TEXT NOT NULL REFERENCES boards(root_id) ON DELETE CASCADE,
  id         INTEGER NOT NULL,
  parent_id  INTEGER,
  position   INTEGER NOT NULL,
  text       TEXT NOT NULL,
  checked    INTEGER NOT NULL DEFAULT 0 CHECK (checked IN (0, 1)),
  rev        INTEGER NOT NULL,
  updated_by TEXT NOT NULL CHECK (updated_by IN ('agent', 'user')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (root_id, id),
  FOREIGN KEY (root_id, parent_id) REFERENCES items(root_id, id) ON DELETE CASCADE
)""",
    "CREATE INDEX items_by_parent ON items(root_id, parent_id, position)",
    "CREATE TABLE aliases (session_id TEXT PRIMARY KEY, root_id TEXT NOT NULL)",
    """CREATE TABLE changes (
  seq     INTEGER PRIMARY KEY AUTOINCREMENT,
  root_id TEXT NOT NULL REFERENCES boards(root_id) ON DELETE CASCADE,
  rev     INTEGER NOT NULL,
  actor   TEXT NOT NULL CHECK (actor IN ('agent', 'user')),
  op      TEXT NOT NULL,
  item_id INTEGER,
  text    TEXT,
  ts      TEXT NOT NULL
)""",
)

READ_VERSION = "PRAGMA user_version"
WRITE_VERSION = f"PRAGMA user_version = {SCHEMA_VERSION}"


class SchemaTooNew(RuntimeError):
    """The data file was written by a newer plugin. This code never downgrades a file."""


def _user_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(READ_VERSION).fetchone()
    return int(row[0])


def _check_not_newer(version: int) -> None:
    if version > SCHEMA_VERSION:
        raise SchemaTooNew(
            f"data file has schema version {version}, this plugin supports {SCHEMA_VERSION}"
        )


def migrate(conn: sqlite3.Connection) -> None:
    """Bring the file to schema v1. Safe to call on every open and from two processes.

    The version is read again inside the write lock, so two processes that open an
    empty file together apply the DDL once.
    """
    version = _user_version(conn)
    _check_not_newer(version)
    if version == SCHEMA_VERSION:
        return
    with write_txn(conn):
        version = _user_version(conn)
        _check_not_newer(version)
        if version == SCHEMA_VERSION:
            return
        for statement in SCHEMA_V1:
            conn.execute(statement)
        conn.execute(WRITE_VERSION)


@contextmanager
def open_db(connect: ConnFactory) -> Iterator[sqlite3.Connection]:
    """Open one migrated connection for one operation. The connection always closes."""
    conn = connect()
    try:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys=ON")
        migrate(conn)
        yield conn
    finally:
        conn.close()
