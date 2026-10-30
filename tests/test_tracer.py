"""First end to end test of the phase: session id to SQLite board to markdown."""

from __future__ import annotations

import functools
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fakes import FakeReaderFactory, SessionSpec
from session_tasks import paths, schema
from session_tasks.db import ConnFactory
from session_tasks.lineage import SessionResolver
from session_tasks.markdown import render
from session_tasks.model import AddItem, Applied, Board, Clock, InvalidSession, utc_now
from session_tasks.schema import SchemaTooNew
from session_tasks.store import BoardStore

TABLES = ("boards", "items", "aliases", "changes")


def make_connect(db_path: Path) -> ConnFactory:
    return functools.partial(paths.connect_path, db_path)


def make_resolver(
    connect: ConnFactory, specs: dict[str, SessionSpec], clock: Clock
) -> SessionResolver:
    return SessionResolver(connect, FakeReaderFactory(specs), clock)


def query(db_path: Path, sql: str) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(db_path)) as conn:
        return conn.execute(sql).fetchall()


def test_plain_session_write_reads_back_as_agent_and_clipboard_markdown(
    db_path: Path, clock: Clock
) -> None:
    connect = make_connect(db_path)
    store = BoardStore(connect, clock)
    resolver = make_resolver(connect, {"s1": SessionSpec()}, clock)

    root_id = resolver.resolve("s1").root_id
    result = store.apply(root_id, [AddItem("Call John")], actor="agent", base_rev=0)
    board = store.get_board(root_id)

    assert isinstance(result, Applied)
    assert result.rev == 1
    assert result.changed_ids == (1,)
    assert render(board, include_ids=True) == "- [ ] #1 Call John\n"
    assert render(board, include_ids=False) == "- [ ] Call John\n"


def test_compression_tip_reads_the_root_board(db_path: Path, clock: Clock) -> None:
    connect = make_connect(db_path)
    store = BoardStore(connect, clock)
    specs = {
        "root": SessionSpec(end_reason="compression"),
        "tip": SessionSpec(parent="root"),
    }
    resolver = make_resolver(connect, specs, clock)
    store.apply(
        resolver.resolve("root").root_id, [AddItem("Call John")], actor="agent", base_rev=0
    )

    resolution = resolver.resolve("tip")
    board = store.get_board(resolution.root_id)

    assert resolution.root_id == "root"
    assert resolution.kind == "compression"
    assert render(board, include_ids=True) == "- [ ] #1 Call John\n"


@pytest.mark.parametrize("session_id", ["", "   ", None, 42])
def test_blank_or_non_string_session_id_raises_invalid_session(
    db_path: Path, clock: Clock, session_id: Any
) -> None:
    resolver = make_resolver(make_connect(db_path), {}, clock)

    with pytest.raises(InvalidSession):
        resolver.resolve(session_id)


def test_unknown_root_reads_empty_board_and_creates_no_rows(
    db_path: Path, clock: Clock
) -> None:
    store = BoardStore(make_connect(db_path), clock)

    board = store.get_board("nobody")

    assert board == Board("nobody", 0, 1, ())
    for table in TABLES:
        assert query(db_path, f"SELECT COUNT(*) FROM {table}") == [(0,)]


def test_migrate_twice_changes_nothing(db_path: Path) -> None:
    connect = make_connect(db_path)
    with schema.open_db(connect):
        pass
    first = query(db_path, "SELECT type, name, sql FROM sqlite_master ORDER BY name")

    with schema.open_db(connect):
        pass
    second = query(db_path, "SELECT type, name, sql FROM sqlite_master ORDER BY name")

    assert query(db_path, "PRAGMA user_version") == [(1,)]
    assert first == second
    assert {"boards", "items", "aliases", "changes"} <= {row[1] for row in first}


def test_newer_schema_raises_schema_too_new(db_path: Path) -> None:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("PRAGMA user_version = 5")

    with pytest.raises(SchemaTooNew), schema.open_db(make_connect(db_path)):
        pass

    assert query(db_path, "PRAGMA user_version") == [(5,)]


def test_written_timestamps_are_utc_text_ending_in_z(db_path: Path, clock: Clock) -> None:
    store = BoardStore(make_connect(db_path), clock)
    store.apply("s1", [AddItem("Call John")], actor="user", base_rev=0)

    stamps = [
        *query(db_path, "SELECT created_at, updated_at FROM boards")[0],
        *query(db_path, "SELECT created_at, updated_at FROM items")[0],
        *query(db_path, "SELECT ts FROM changes")[0],
    ]

    assert len(stamps) == 5
    for stamp in stamps:
        assert isinstance(stamp, str)
        assert stamp.endswith("Z")
        datetime.fromisoformat(stamp)


def test_utc_now_ends_in_z_and_parses() -> None:
    stamp = utc_now()

    assert stamp.endswith("Z")
    assert datetime.fromisoformat(stamp).utcoffset() is not None


def test_data_file_runs_in_wal_mode(db_path: Path, clock: Clock) -> None:
    store = BoardStore(make_connect(db_path), clock)
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)

    assert query(db_path, "PRAGMA journal_mode") == [("wal",)]
