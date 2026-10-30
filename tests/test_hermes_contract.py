"""Contract tests against the real Hermes checkout. They need `HERMES_AGENT_REPO` (marker hermes)."""

from __future__ import annotations

import dataclasses
import json
import os
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from conftest import HERMES_AGENT_REPO
from fakes import SEVEN_ROW_FIXTURE, FakeSessionReader
from session_tasks import paths

pytestmark = pytest.mark.hermes

GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"
SNIPPET = Path(__file__).resolve().parent / "hermes_contract_snippet.py"
PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugin"
MISSING = "missing"
PRAGMAS = ("journal_mode", "foreign_keys", "busy_timeout")


@pytest.fixture
def hermes_checkout(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Put the checkout on sys.path for one test. Remove every module the test imported."""
    known = set(sys.modules)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.syspath_prepend(str(HERMES_AGENT_REPO))
    try:
        yield HERMES_AGENT_REPO
    finally:
        for name in set(sys.modules) - known:
            del sys.modules[name]


def pragma_values(conn: sqlite3.Connection) -> dict[str, Any]:
    return {name: conn.execute(f"PRAGMA {name}").fetchone()[0] for name in PRAGMAS}


def project(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Reduce a `sessions` row to the keys the fake carries. Apply it to both sides."""
    if row is None:
        return None
    projected: dict[str, Any] = {
        key: row.get(key) for key in ("id", "source", "parent_session_id", "end_reason")
    }
    for key in ("_branched_from", "_reset_from"):
        if key in row:
            projected[key] = row[key]
    projected["model_config"] = decode_config(row.get("model_config"))
    return projected


def decode_config(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except ValueError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def test_plugin_db_lands_under_hermes_home_with_the_expected_pragmas(
    hermes_checkout: Path, hermes_home: Path
) -> None:
    conn = paths.connect()
    try:
        values = pragma_values(conn)
        location = conn.execute("PRAGMA database_list").fetchone()[2]
    finally:
        conn.close()

    expected = hermes_home / "plugin-data" / "hermes-session-tasks" / "data.db"
    assert Path(location).resolve() == expected.resolve()
    assert values == {"journal_mode": "wal", "foreign_keys": 1, "busy_timeout": 5000}
    assert not (hermes_home / "state.db").exists()


def test_connect_path_twin_reports_the_same_pragmas_as_plugin_db(
    hermes_checkout: Path, tmp_path: Path
) -> None:
    with closing(paths.connect()) as real, closing(paths.connect_path(tmp_path / "t.db")) as twin:
        assert pragma_values(twin) == pragma_values(real)


def test_fake_reader_and_resolver_match_the_real_session_db(
    tmp_path: Path, hermes_home: Path
) -> None:
    if not GATEWAY_PYTHON.exists():
        pytest.skip(f"gateway venv python not found at {GATEWAY_PYTHON}")
    fixture_json = tmp_path / "fixture.json"
    fixture = {sid: dataclasses.asdict(spec) for sid, spec in SEVEN_ROW_FIXTURE.items()}
    fixture_json.write_text(json.dumps(fixture), encoding="utf-8")
    env = {
        **os.environ,
        "HERMES_HOME": str(hermes_home),
        "PYTEST_CURRENT_TEST": "contract",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    done = subprocess.run(
        [
            str(GATEWAY_PYTHON),
            "-I",
            str(SNIPPET),
            str(PLUGIN_DIR),
            str(HERMES_AGENT_REPO),
            str(fixture_json),
        ],
        cwd=HERMES_AGENT_REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )

    assert done.returncode == 0, done.stderr
    real = json.loads(done.stdout)
    fake = FakeSessionReader(SEVEN_ROW_FIXTURE)
    for session_id in [*SEVEN_ROW_FIXTURE, MISSING]:
        assert real["fork"][session_id] == fake.is_explicit_fork_child(session_id), session_id
        assert real["lineage"][session_id] == fake.get_compression_lineage(session_id), session_id
        assert project(real["sessions"][session_id]) == project(fake.get_session(session_id)), (
            session_id
        )
    resolutions = real["resolutions"]
    assert resolutions["root"][:2] == ["root", "plain"]
    assert resolutions["comp1"][:2] == ["root", "compression"]
    assert resolutions["comp2"][:2] == ["root", "compression"]
    assert resolutions["br"] == ["br", "branch", "root"]
    assert resolutions["dg"][:2] == ["root", "delegate"]
    assert resolutions["rs"][:2] == ["rs", "plain"]
    assert resolutions["plain"][:2] == ["plain", "plain"]
    assert resolutions[MISSING][:2] == [MISSING, "plain"]
    assert real["state_db_unchanged"] is True
    assert real["branch_texts"] == ["Call John"]
    expected = hermes_home / "plugin-data" / "hermes-session-tasks" / "data.db"
    assert Path(real["plugin_db_path"]).resolve() == expected.resolve()
