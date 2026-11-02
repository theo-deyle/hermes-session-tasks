"""The `on_session_delete` callback removes a board when Hermes deletes its session (D-37)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from session_tasks.hooks import make_on_session_delete
from session_tasks.model import AddItem, SetChecked
from session_tasks.store import BoardStore

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
