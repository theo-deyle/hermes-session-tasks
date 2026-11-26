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
