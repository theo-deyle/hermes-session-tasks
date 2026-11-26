"""The two Hermes adapters, tested with fake Hermes modules. No Hermes checkout is needed."""

from __future__ import annotations

import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from session_tasks import paths, session_reader
from session_tasks.paths import PLUGIN_NAME


def install_module(monkeypatch: pytest.MonkeyPatch, name: str, **attributes: Any) -> ModuleType:
    module = ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def test_connect_opens_plugin_db_with_the_plugin_name_on_every_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    def plugin_db(name: str) -> sqlite3.Connection:
        calls.append(name)
        return paths.connect_path(tmp_path / "data.db")

    install_module(monkeypatch, "plugins")
    install_module(monkeypatch, "plugins.plugin_storage", plugin_db=plugin_db)

    first, second = paths.connect(), paths.connect()
    first.close()
    second.close()

    assert PLUGIN_NAME == "hermes-session-tasks"
    assert calls == ["hermes-session-tasks", "hermes-session-tasks"]


def test_open_session_reader_builds_session_db_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    class FakeSessionDB:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            seen.append((args, kwargs))

    install_module(monkeypatch, "hermes_state", SessionDB=FakeSessionDB)

    reader = session_reader.open_session_reader()

    assert isinstance(reader, FakeSessionDB)
    assert seen == [((), {"read_only": True})]


def test_connect_path_sets_wal_busy_timeout_and_foreign_keys(tmp_path: Path) -> None:
    with closing(paths.connect_path(tmp_path / "data.db")) as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == ("delete" if paths.is_wal_reset_vulnerable() else "wal")
        assert conn.execute("PRAGMA foreign_keys").fetchone() == (1,)
        assert conn.execute("PRAGMA busy_timeout").fetchone() == (5000,)


@pytest.mark.parametrize(
    ("version", "vulnerable"),
    [
        ((3, 6, 22), False),  # pre-WAL SQLite, nothing to reset
        ((3, 7, 0), True),  # first affected release
        ((3, 44, 5), True),
        ((3, 44, 6), False),  # first 3.44 backport
        ((3, 50, 6), True),
        ((3, 50, 7), False),  # first 3.50 backport
        ((3, 51, 2), True),  # last affected release
        ((3, 51, 3), False),  # upstream fix
    ],
)
def test_is_wal_reset_vulnerable_matches_the_documented_range(
    version: tuple[int, int, int], vulnerable: bool
) -> None:
    assert paths.is_wal_reset_vulnerable(version) is vulnerable


class _FakeRecord:
    def __init__(self, row: dict[str, Any]) -> None:
        self._row = row

    def as_session_row(self) -> dict[str, Any]:
        return dict(self._row)


class _FakeTranscriptRow:
    def __init__(self, row: dict[str, Any]) -> None:
        self._row = row

    def as_wire_row(self) -> dict[str, Any]:
        return dict(self._row)


class _FakeLineage:
    def lineage(self, session_id: str) -> tuple[str, ...]:
        return ("root", session_id)

    def is_fork_child(self, session_id: str) -> bool:
        return session_id == "fork"


class _FakeStore:
    """The parts of the Hermes store handle the adapter uses: sessions, lineage, messages."""

    def __init__(self) -> None:
        self.closed = 0
        self.requests: list[Any] = []
        self.sessions = self
        self.lineage = _FakeLineage()
        self.messages = self

    def get(self, session_id: str) -> _FakeRecord | None:
        return _FakeRecord({"id": "s1", "title": "Trip"}) if session_id == "s1" else None

    def read_transcript(self, session_id: str, request: Any) -> tuple[_FakeTranscriptRow, ...]:
        self.requests.append(request)
        return (_FakeTranscriptRow({"role": "user", "content": "hi"}),)


def install_storage_interface(
    monkeypatch: pytest.MonkeyPatch, store: _FakeStore, location: Path | None
) -> list[Any]:
    """Fake `persistence_assembly` and `persistence.conversation.messages`. Returns the open targets."""
    opened: list[Any] = []

    class Scope:
        profile_dir = Path("/profile")

    class Handle:
        def __enter__(self) -> _FakeStore:
            return store

        def __exit__(self, *exc: object) -> None:
            store.closed += 1

    def open_persistence_reader(target: Any) -> Handle:
        opened.append(target)
        return Handle()

    install_module(
        monkeypatch,
        "persistence_assembly",
        open_persistence_reader=open_persistence_reader,
        profile_scope=Scope,
        store_location=lambda scope: location,
    )
    install_module(monkeypatch, "persistence")
    install_module(monkeypatch, "persistence.conversation")
    install_module(
        monkeypatch,
        "persistence.conversation.messages",
        TranscriptRead=lambda **kwargs: kwargs,
    )
    return opened


def test_open_session_reader_prefers_the_storage_interface(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = _FakeStore()
    state_db = tmp_path / "state.db"
    state_db.touch()
    opened = install_storage_interface(monkeypatch, store, state_db)

    reader = session_reader.open_session_reader()

    assert opened == [Path("/profile")]
    assert reader.get_session("s1") == {"id": "s1", "title": "Trip"}
    assert reader.get_session("missing") is None
    assert reader.get_session_title("s1") == "Trip"
    assert reader.get_session_title("missing") is None
    assert reader.get_compression_lineage("s2") == ["root", "s2"]
    assert reader.is_explicit_fork_child("fork") is True
    assert reader.is_explicit_fork_child("s1") is False
    assert reader.get_messages("s1", limit=5) == [{"role": "user", "content": "hi"}]
    assert store.requests == [{"limit": 5}]
    reader.close()
    reader.close()
    assert store.closed == 1


def test_open_session_reader_reports_a_missing_store_as_operational_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened = install_storage_interface(monkeypatch, _FakeStore(), tmp_path / "state.db")

    with pytest.raises(sqlite3.OperationalError):
        session_reader.open_session_reader()

    assert opened == []
