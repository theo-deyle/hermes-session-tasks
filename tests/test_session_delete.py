"""The `on_session_delete` callback removes a board when Hermes deletes its session (D-37)."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from conftest import FakeClock
from session_tasks.db import ConnFactory
from session_tasks.fork import fork_copy
from session_tasks.hooks import make_on_session_delete
from session_tasks.model import AddItem, SetChecked
from session_tasks.store import SQL_IN_CHUNK, BoardStore

TABLES = ("boards", "items", "changes", "aliases")


def count_for(db_path: Path, table: str, session_id: str) -> int:
    """Count the rows of `table` that belong to `session_id`."""
    column = "session_id" if table == "aliases" else "root_id"
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = ?", (session_id,))
        return int(row.fetchone()[0])


def test_a_deleted_session_takes_its_board(store: BoardStore, db_path: Path) -> None:
    store.apply("s1", [AddItem("Call John"), AddItem("Send quote")], actor="agent", base_rev=0)
    store.apply("s1", [SetChecked(1, True)], actor="user", base_rev=1)
    store.apply("s2", [AddItem("Keep me")], actor="agent", base_rev=0)

    result = make_on_session_delete(store)(
        session_id="s1",
        reason="delete",
        profile="default",
        sessions_dir="/tmp/x",
        telemetry_schema_version="hermes.observer.v1",
    )

    assert result is None
    for table in TABLES:
        assert count_for(db_path, table, "s1") == 0
    kept = store.get_board("s2")
    assert kept.rev == 1
    assert [item.text for item in kept.items] == ["Keep me"]


def put(store: BoardStore, root_id: str, *texts: str) -> None:
    store.apply(root_id, [AddItem(text) for text in texts], actor="agent", base_rev=0)


def test_archive_keeps_the_board(store: BoardStore) -> None:
    put(store, "s1", "one")
    put(store, "s1-root", "two")

    make_on_session_delete(store)(
        session_id="s1", reason="archive", profile="default", deleted_ids=["s1", "s1-root"]
    )

    assert [item.text for item in store.get_board("s1").items] == ["one"]
    assert [item.text for item in store.get_board("s1-root").items] == ["two"]


def test_bulk_delete_removes_every_listed_board(store: BoardStore, db_path: Path) -> None:
    for root_id in ("b1", "b2", "b3"):
        put(store, root_id, "x")

    make_on_session_delete(store)(session_id="b1", reason="delete", deleted_ids=["b1", "b2"])

    assert [summary.root_id for summary in store.list_boards()] == ["b3"]
    assert count_for(db_path, "aliases", "b1") == 0
    assert count_for(db_path, "aliases", "b2") == 0
    assert count_for(db_path, "aliases", "b3") == 1


def test_alias_only_match_keeps_the_board(store: BoardStore, db_path: Path) -> None:
    put(store, "root", "one", "two")
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("INSERT INTO aliases (session_id, root_id) VALUES ('tip', 'root')")

    make_on_session_delete(store)(session_id="tip", reason="delete")

    assert count_for(db_path, "aliases", "tip") == 0
    assert [item.text for item in store.get_board("root").items] == ["one", "two"]


def test_a_branch_board_survives_its_parent(
    store: BoardStore, connect: ConnFactory, clock: FakeClock
) -> None:
    put(store, "parent", "one", "two")
    assert fork_copy(connect, "br", "parent", clock)

    make_on_session_delete(store)(session_id="parent", reason="delete")

    assert store.get_board("parent").items == ()
    assert [item.text for item in store.get_board("br").items] == ["one", "two"]


BAD_PAYLOADS = [
    {"session_id": "", "deleted_ids": [None, "", "  ", 7]},
    {"session_id": "", "deleted_ids": "s1"},
    {"session_id": "", "deleted_ids": 7},
    {"session_id": 42},
    {"session_id": "   "},
    {"session_id": "s1", "reason": None},
    {"session_id": "s1", "reason": 3},
    {"session_id": "s1", "reason": ""},
    {"session_id": "s1", "reason": "   "},
]


@pytest.mark.parametrize("payload", BAD_PAYLOADS)
def test_bad_payloads_remove_nothing(store: BoardStore, payload: dict[str, object]) -> None:
    put(store, "s1", "one")
    call: dict[str, object] = {"reason": "delete", **payload}

    make_on_session_delete(store)(**call)

    assert [item.text for item in store.get_board("s1").items] == ["one"]


def test_store_fault_logs_a_warning_and_raises_nothing(caplog: pytest.LogCaptureFixture) -> None:
    def broken_connect() -> sqlite3.Connection:
        raise RuntimeError("service is down")

    callback = make_on_session_delete(BoardStore(broken_connect))

    with caplog.at_level(logging.WARNING, logger="session_tasks.hooks"):
        callback(session_id="s1", reason="delete")

    records = [r for r in caplog.records if r.name == "session_tasks.hooks"]
    assert [r.levelno for r in records] == [logging.WARNING]


def test_twelve_hundred_ids_are_deleted_in_chunks(store: BoardStore) -> None:
    ids = [f"id-{number}" for number in range(1200)]
    assert len(ids) > 2 * SQL_IN_CHUNK
    for index in (0, 600, 1199):
        put(store, ids[index], "x")
    put(store, "unlisted", "y")

    make_on_session_delete(store)(session_id=ids[0], reason="delete", deleted_ids=ids)

    assert [summary.root_id for summary in store.list_boards()] == ["unlisted"]


def test_a_delegate_id_in_the_list_removes_nothing_of_its_own(
    store: BoardStore, db_path: Path
) -> None:
    put(store, "parent", "one")
    put(store, "other", "two")

    make_on_session_delete(store)(
        session_id="parent", reason="delete", deleted_ids=["parent", "delegate-of-parent"]
    )

    assert [summary.root_id for summary in store.list_boards()] == ["other"]
    assert count_for(db_path, "aliases", "other") == 1
