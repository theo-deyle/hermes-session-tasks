"""Session id to board root: compression, reset, delegate, missing rows and compaction."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from conftest import FakeClock, ResolverFor
from fakes import (
    SEVEN_ROW_FIXTURE,
    FakeReaderFactory,
    FakeSessionReader,
    RaisingReaderFactory,
    ReaderBoom,
    SessionSpec,
)
from session_tasks import aliases, schema
from session_tasks.db import ConnFactory, write_txn
from session_tasks.lineage import Resolution, SessionResolver
from session_tasks.markdown import render
from session_tasks.model import AddItem, InvalidSession
from session_tasks.store import BoardStore

TABLES = ("boards", "items", "aliases", "changes")


def query(db_path: Path, sql: str) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(db_path)) as conn:
        return conn.execute(sql).fetchall()


def table_counts(db_path: Path) -> dict[str, int]:
    if not db_path.exists():
        return dict.fromkeys(TABLES, 0)
    return {name: query(db_path, f"SELECT COUNT(*) FROM {name}")[0][0] for name in TABLES}


def put_alias_row(connect: ConnFactory, session_id: str, root_id: str) -> None:
    with schema.open_db(connect) as conn, write_txn(conn):
        aliases.put_alias(conn, session_id, root_id)


def add_item(store: BoardStore, root_id: str, text: str = "Call John") -> None:
    store.apply(root_id, [AddItem(text)], actor="agent", base_rev=0)


class StringConfigReaderFactory(FakeReaderFactory):
    """Fake factory whose rows carry a raw `model_config` value, valid JSON or not."""

    def __init__(self, specs: dict[str, SessionSpec], raw_config: Any) -> None:
        super().__init__(specs)
        self._raw_config = raw_config

    def __call__(self) -> FakeSessionReader:
        reader = super().__call__()
        original = reader.get_session

        def get_session(session_id: str) -> dict[str, Any] | None:
            row = original(session_id)
            if row is not None:
                row["model_config"] = self._raw_config
            return row

        reader.get_session = get_session  # type: ignore[method-assign]
        return reader


def test_alias_hit_returns_the_root_without_opening_a_reader(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    resolver, factory = resolver_for({})
    add_item(store, "s1")
    put_alias_row(connect, "tip", "s1")

    plain = resolver.resolve("s1")
    compressed = resolver.resolve("tip")

    assert plain == Resolution("s1", "plain")
    assert compressed == Resolution("s1", "compression")
    assert factory.opens == 0


def test_compression_tip_and_middle_resolve_to_the_chain_root(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)
    add_item(store, "root")

    assert resolver.resolve("comp2") == Resolution("root", "compression")
    assert resolver.resolve("comp1") == Resolution("root", "compression")
    assert resolver.resolve("root") == Resolution("root", "plain")
    assert render(store.get_board("root"), include_ids=False) == "- [ ] Call John\n"


def test_compression_alias_is_written_only_when_the_root_has_a_board(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)

    first = resolver.resolve("comp2")
    assert first == Resolution("root", "compression")
    assert table_counts(db_path)["aliases"] == 0

    add_item(store, "root")
    resolver.resolve("comp2")

    assert query(db_path, "SELECT session_id, root_id FROM aliases ORDER BY session_id") == [
        ("comp2", "root"),
        ("root", "root"),
    ]


def test_resolving_one_id_twice_gives_equal_resolutions(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)
    add_item(store, "root")

    for session_id in ("comp2", "plain", "dg", "rs"):
        assert resolver.resolve(session_id) == resolver.resolve(session_id)


def test_reset_child_resolves_to_itself_and_reads_an_empty_board(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)
    add_item(store, "root")

    resolution = resolver.resolve("rs")

    assert resolution == Resolution("rs", "plain")
    assert store.get_board(resolution.root_id).items == ()
    assert query(db_path, "SELECT session_id FROM aliases WHERE session_id = 'rs'") == []


def test_delegate_resolves_to_the_delegator_root_and_writes_nothing(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)

    bare = resolver.resolve("dg")

    assert bare == Resolution("root", "delegate")
    assert table_counts(db_path) == dict.fromkeys(TABLES, 0)

    add_item(store, "root")
    before = table_counts(db_path)
    with_board = resolver.resolve("dg")

    assert with_board == Resolution("root", "delegate")
    assert query(db_path, "SELECT root_id FROM boards") == [("root",)]
    assert query(db_path, "SELECT session_id FROM aliases WHERE session_id = 'dg'") == []
    assert table_counts(db_path)["items"] == before["items"]
    assert table_counts(db_path)["changes"] == before["changes"]


def test_tool_source_child_with_a_parent_resolves_as_a_delegate(
    resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, _ = resolver_for({
        "p": SessionSpec(),
        "t": SessionSpec(parent="p", source="tool"),
    })

    assert resolver.resolve("t") == Resolution("p", "delegate")
    assert table_counts(db_path) == dict.fromkeys(TABLES, 0)


def test_fork_child_with_no_marker_and_no_parent_resolves_plain(
    resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, _ = resolver_for({"t": SessionSpec(source="tool")})

    assert resolver.resolve("t") == Resolution("t", "plain")
    assert table_counts(db_path) == dict.fromkeys(TABLES, 0)


def test_missing_session_row_resolves_plain_and_writes_no_alias(
    resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, factory = resolver_for({})

    assert resolver.resolve("nobody") == Resolution("nobody", "plain")
    assert factory.opens == 1
    assert table_counts(db_path) == dict.fromkeys(TABLES, 0)


def test_missing_state_db_resolves_plain_and_writes_no_alias(
    connect: ConnFactory, clock: FakeClock, db_path: Path
) -> None:
    factory = RaisingReaderFactory(sqlite3.OperationalError("unable to open database file"))
    resolver = SessionResolver(connect, factory, clock)

    assert resolver.resolve("s1") == Resolution("s1", "plain")
    assert factory.opens == 1
    assert table_counts(db_path) == dict.fromkeys(TABLES, 0)


def test_other_reader_open_errors_are_not_swallowed(connect: ConnFactory, clock: FakeClock) -> None:
    resolver = SessionResolver(connect, RaisingReaderFactory(RuntimeError("boom")), clock)

    with pytest.raises(RuntimeError, match="boom"):
        resolver.resolve("s1")


@pytest.mark.parametrize("raw_config", ["{not json", "[1, 2]", "5", "", None, '"text"'])
def test_bad_model_config_json_is_read_as_empty(
    connect: ConnFactory, clock: FakeClock, raw_config: Any
) -> None:
    specs = {"p": SessionSpec(), "t": SessionSpec(parent="p", source="tool")}
    factory = StringConfigReaderFactory(specs, raw_config)
    resolver = SessionResolver(connect, factory, clock)

    assert resolver.resolve("t") == Resolution("p", "delegate")
    assert factory.all_closed


@pytest.mark.parametrize(
    "method", ["get_session", "is_explicit_fork_child", "get_compression_lineage"]
)
def test_every_opened_reader_is_closed_also_when_a_reader_call_raises(
    connect: ConnFactory, clock: FakeClock, method: str
) -> None:
    factory = FakeReaderFactory({"s1": SessionSpec()}, raise_in=method)
    resolver = SessionResolver(connect, factory, clock)

    with pytest.raises(ReaderBoom):
        resolver.resolve("s1")

    assert factory.opens == 1
    assert factory.all_closed


@pytest.mark.parametrize("session_id", ["plain", "comp2", "dg", "rs", "root"])
def test_one_resolve_opens_at_most_one_reader(resolver_for: ResolverFor, session_id: str) -> None:
    resolver, factory = resolver_for(SEVEN_ROW_FIXTURE)

    resolver.resolve(session_id)

    assert factory.opens == 1
    assert factory.all_closed


def test_record_compaction_aliases_the_new_id_to_the_root_of_the_old_id(
    resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, factory = resolver_for({
        **SEVEN_ROW_FIXTURE,
        "tip": SessionSpec(parent="comp2"),
    })

    resolver.record_compaction("tip", "comp2")

    assert query(db_path, "SELECT session_id, root_id FROM aliases") == [("tip", "root")]
    assert factory.opens == 1
    assert factory.all_closed


@pytest.mark.parametrize(("new_id", "old_id"), [("a", ""), ("a", "   "), ("a", "a")])
def test_record_compaction_with_an_empty_or_equal_old_id_writes_nothing(
    resolver_for: ResolverFor, db_path: Path, new_id: str, old_id: str
) -> None:
    resolver, factory = resolver_for({})

    resolver.record_compaction(new_id, old_id)

    assert table_counts(db_path) == dict.fromkeys(TABLES, 0)
    assert factory.opens == 0


def test_record_compaction_finds_the_old_root_by_alias_then_lineage_then_the_old_id(
    resolver_for: ResolverFor, connect: ConnFactory, db_path: Path, clock: FakeClock
) -> None:
    resolver, factory = resolver_for(SEVEN_ROW_FIXTURE)
    put_alias_row(connect, "mid", "R")

    resolver.record_compaction("n1", "mid")
    assert factory.opens == 0

    resolver.record_compaction("n2", "comp2")
    assert factory.opens == 1

    resolver.record_compaction("n3", "unknown-old")
    gone = SessionResolver(connect, RaisingReaderFactory(sqlite3.OperationalError("x")), clock)
    gone.record_compaction("n4", "also-unknown")

    assert query(db_path, "SELECT session_id, root_id FROM aliases ORDER BY session_id") == [
        ("mid", "R"),
        ("n1", "R"),
        ("n2", "root"),
        ("n3", "unknown-old"),
        ("n4", "also-unknown"),
    ]


@pytest.mark.parametrize("session_id", ["", "   ", None, 7])
def test_record_compaction_with_a_blank_session_id_raises_invalid_session(
    resolver_for: ResolverFor, db_path: Path, session_id: Any
) -> None:
    resolver, _ = resolver_for({})

    with pytest.raises(InvalidSession):
        resolver.record_compaction(session_id, "old")

    assert table_counts(db_path) == dict.fromkeys(TABLES, 0)


COMPACTED_DELEGATE_FIXTURE: dict[str, SessionSpec] = {
    **SEVEN_ROW_FIXTURE,
    "dg": replace(SEVEN_ROW_FIXTURE["dg"], end_reason="compression"),
    "dg2": SessionSpec(parent="dg"),
}


def test_compressed_delegate_tip_resolves_to_the_delegator_root(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    add_item(store, "root")
    resolver, _ = resolver_for(COMPACTED_DELEGATE_FIXTURE)

    assert resolver.resolve("dg2") == Resolution("root", "compression")
    assert query(db_path, "SELECT root_id FROM aliases WHERE session_id = 'dg2'") == [("root",)]
