"""The live test tools of phase 5: the scripted Theo edit, the run readers and the home builder.

`theo_edit.py` runs under the gateway venv Python against a temporary HERMES_HOME (marker
hermes). The other tests load the live scripts by file path and never start a gateway.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from conftest import HERMES_AGENT_REPO
from session_tasks import paths
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"
LIVE_DIR = Path(__file__).resolve().parent / "live" / "delta"
THEO_EDIT = LIVE_DIR / "theo_edit.py"
SESSION = "live-s1"


def run_gateway_python(
    script: Path, args: list[str], hermes_home: Path
) -> subprocess.CompletedProcess[str]:
    if not GATEWAY_PYTHON.exists():
        pytest.skip(f"gateway venv python not found at {GATEWAY_PYTHON}")
    env = {**os.environ, "HERMES_HOME": str(hermes_home)}
    return subprocess.run(
        [str(GATEWAY_PYTHON), "-I", str(script), *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        check=False,
    )


def data_file(hermes_home: Path) -> Path:
    return hermes_home / "plugin-data" / "hermes-session-tasks" / "data.db"


def edit(hermes_home: Path, ops: str) -> subprocess.CompletedProcess[str]:
    return run_gateway_python(THEO_EDIT, ["--session", SESSION, "--ops", ops], hermes_home)


@pytest.mark.hermes
def test_theo_edit_writes_as_theo_in_a_temporary_home(hermes_home: Path) -> None:
    first = edit(hermes_home, '[{"op": "add", "text": "Call John"}]')

    assert first.returncode == 0, first.stderr
    reply = json.loads(first.stdout.strip().splitlines()[-1])
    assert reply["ok"] is True
    assert reply["rev"] == 1
    conn = paths.connect_path(data_file(hermes_home))
    try:
        item = conn.execute("SELECT text, updated_by FROM items WHERE id = 1").fetchone()
        journal = conn.execute("SELECT actor FROM changes").fetchall()
    finally:
        conn.close()
    assert item == ("Call John", "user")
    assert journal == [("user",)]

    second = edit(hermes_home, '[{"op": "set_checked", "item_id": 1, "checked": true}]')

    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout.strip().splitlines()[-1])["rev"] == 2


@pytest.mark.hermes
def test_theo_edit_leaves_other_boards_alone(hermes_home: Path) -> None:
    file = data_file(hermes_home)
    file.parent.mkdir(parents=True)
    BoardStore(lambda: paths.connect_path(file)).apply(
        "other", [AddItem("Keep me")], actor="agent", base_rev=0
    )

    done = edit(hermes_home, '[{"op": "add", "text": "Call John"}]')

    assert done.returncode == 0, done.stderr
    conn = paths.connect_path(file)
    try:
        other = conn.execute("SELECT rev FROM boards WHERE root_id = 'other'").fetchone()
    finally:
        conn.close()
    assert other == (1,)


@pytest.mark.hermes
def test_theo_edit_rejects_bad_ops_json(hermes_home: Path) -> None:
    done = edit(hermes_home, "not json")

    assert done.returncode == 2
    assert not data_file(hermes_home).exists()
