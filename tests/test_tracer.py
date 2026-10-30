"""First end to end test of the phase: session id to SQLite board to markdown."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from conftest import ResolverFor
from fakes import SessionSpec
from session_tasks import schema
from session_tasks.db import ConnFactory
from session_tasks.markdown import render
from session_tasks.model import AddItem, Applied, Board, EmptyText, InvalidSession, utc_now
from session_tasks.schema import SchemaTooNew
from session_tasks.store import BoardStore

TABLES = ("boards", "items", "aliases", "changes")


def query(db_path: Path, sql: str) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(db_path)) as conn:
        return conn.execute(sql).fetchall()


def test_plain_session_write_reads_back_as_agent_and_clipboard_markdown(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    resolver, _ = resolver_for({"s1": SessionSpec()})

    root_id = resolver.resolve("s1").root_id
    result = store.apply(root_id, [AddItem("Call John")], actor="agent", base_rev=0)
    board = store.get_board(root_id)

    assert isinstance(result, Applied)
    assert result.rev == 1
    assert result.changed_ids == (1,)
    assert render(board, include_ids=True) == "- [ ] #1 Call John\n"
    assert render(board, include_ids=False) == "- [ ] Call John\n"


def test_compression_tip_reads_the_root_board(store: BoardStore, resolver_for: ResolverFor) -> None:
    resolver, _ = resolver_for({
        "root": SessionSpec(end_reason="compression"),
        "tip": SessionSpec(parent="root"),
    })
    store.apply(resolver.resolve("root").root_id, [AddItem("Call John")], actor="agent", base_rev=0)

    resolution = resolver.resolve("tip")
    board = store.get_board(resolution.root_id)

    assert resolution.root_id == "root"
    assert resolution.kind == "compression"
    assert render(board, include_ids=True) == "- [ ] #1 Call John\n"


@pytest.mark.parametrize("session_id", ["", "   ", None, 42])
def test_blank_or_non_string_session_id_raises_invalid_session(
    resolver_for: ResolverFor, session_id: Any
) -> None:
    resolver, _ = resolver_for({})

    with pytest.raises(InvalidSession):
        resolver.resolve(session_id)


def test_unknown_root_reads_empty_board_and_creates_no_rows(
    store: BoardStore, db_path: Path
) -> None:
    board = store.get_board("nobody")

    assert board == Board("nobody", 0, 1, ())
    for table in TABLES:
        assert query(db_path, f"SELECT COUNT(*) FROM {table}") == [(0,)]


def test_migrate_twice_changes_nothing(connect: ConnFactory, db_path: Path) -> None:
    with schema.open_db(connect):
        pass
    first = query(db_path, "SELECT type, name, sql FROM sqlite_master ORDER BY name")

    with schema.open_db(connect):
        pass
    second = query(db_path, "SELECT type, name, sql FROM sqlite_master ORDER BY name")

    assert query(db_path, "PRAGMA user_version") == [(1,)]
    assert first == second
    assert {"boards", "items", "aliases", "changes"} <= {row[1] for row in first}


def test_newer_schema_raises_schema_too_new(connect: ConnFactory, db_path: Path) -> None:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("PRAGMA user_version = 5")

    with pytest.raises(SchemaTooNew), schema.open_db(connect):
        pass

    assert query(db_path, "PRAGMA user_version") == [(5,)]


def test_written_timestamps_are_utc_text_ending_in_z(store: BoardStore, db_path: Path) -> None:
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


def test_data_file_runs_in_wal_mode(store: BoardStore, db_path: Path) -> None:
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)

    assert query(db_path, "PRAGMA journal_mode") == [("wal",)]


def test_first_write_creates_the_board_row_and_the_alias_row_in_one_transaction(
    store: BoardStore, db_path: Path
) -> None:
    with pytest.raises(EmptyText):
        store.apply("fresh", [AddItem("ok"), AddItem("   ")], actor="agent", base_rev=0)
    assert query(db_path, "SELECT COUNT(*) FROM boards") == [(0,)]
    assert query(db_path, "SELECT COUNT(*) FROM aliases") == [(0,)]

    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)

    assert query(db_path, "SELECT root_id FROM boards") == [("s1",)]
    assert query(db_path, "SELECT session_id, root_id FROM aliases") == [("s1", "s1")]


def test_second_resolve_hits_alias_and_opens_no_reader(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    resolver, factory = resolver_for({"s1": SessionSpec()})
    first = resolver.resolve("s1")
    opens_after_first = factory.opens
    store.apply(first.root_id, [AddItem("Call John")], actor="agent", base_rev=0)

    second = resolver.resolve("s1")

    assert opens_after_first == 1
    assert factory.opens == opens_after_first
    assert second.root_id == "s1"
    assert second.kind == "plain"
    assert factory.all_closed


def test_compression_tip_resolves_through_the_alias_after_the_first_walk(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, factory = resolver_for({
        "root": SessionSpec(end_reason="compression"),
        "tip": SessionSpec(parent="root"),
    })
    store.apply("root", [AddItem("Call John")], actor="agent", base_rev=0)

    first = resolver.resolve("tip")
    opens_after_first = factory.opens
    second = resolver.resolve("tip")

    assert opens_after_first == 1
    assert factory.opens == opens_after_first
    assert (first.root_id, first.kind) == ("root", "compression")
    assert (second.root_id, second.kind) == ("root", "compression")
    assert query(db_path, "SELECT session_id, root_id FROM aliases ORDER BY session_id") == [
        ("root", "root"),
        ("tip", "root"),
    ]


def test_plain_session_without_a_board_writes_no_alias(
    resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, _ = resolver_for({"s1": SessionSpec()})

    resolver.resolve("s1")

    assert query(db_path, "SELECT COUNT(*) FROM aliases") == [(0,)]
