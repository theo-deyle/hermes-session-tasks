"""Connection factory type and the read and write transaction helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TypeAlias

ConnFactory: TypeAlias = Callable[[], sqlite3.Connection]


@contextmanager
def write_txn(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run the body inside one `BEGIN IMMEDIATE` transaction.

    The connection must be in autocommit mode (`isolation_level = None`). This is the
    only lock that spans processes: SQLite takes the write lock at `BEGIN IMMEDIATE`.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


@contextmanager
def read_txn(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run the body inside one deferred transaction, so all reads share one snapshot."""
    conn.execute("BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
