"""The live test tools of phase 6: seed a source board, read a board, list tool calls, stop a test gateway."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from conftest import HERMES_AGENT_REPO

GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"
LIVE_DIR = Path(__file__).resolve().parent / "live" / "cross"
CROSS_LIVE = LIVE_DIR / "cross_live.py"
SOURCE = "cross-src-1"
TITLE = "Phase 6 source board"
OPS = json.dumps([
    {"op": "add", "text": "Call John"},
    {"op": "add", "text": "Ask about the quote", "parent_ref": 0},
    {"op": "add", "text": "Book the van", "checked": True},
])


def load_live(name: str, path: Path) -> ModuleType:
    """Load a live script by its file path. The module is registered so dataclasses resolve."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def data_file(hermes_home: Path) -> Path:
    return hermes_home / "plugin-data" / "hermes-session-tasks" / "data.db"


def run_gateway_python(args: list[str], hermes_home: Path) -> subprocess.CompletedProcess[str]:
    if not GATEWAY_PYTHON.exists():
        pytest.skip(f"gateway venv python not found at {GATEWAY_PYTHON}")
    env = {**os.environ, "HERMES_HOME": str(hermes_home)}
    return subprocess.run(
        [str(GATEWAY_PYTHON), "-I", str(CROSS_LIVE), *args],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
        check=False,
    )


def last_json(text: str) -> dict[str, object]:
    return json.loads(text.strip().splitlines()[-1])


@pytest.mark.hermes
def test_seed_then_board_in_a_temporary_home(hermes_home: Path) -> None:
    seeded = run_gateway_python(
        ["seed", "--session", SOURCE, "--title", TITLE, "--ops", OPS], hermes_home
    )

    assert seeded.returncode == 0, seeded.stderr
    reply = last_json(seeded.stdout)
    assert reply["ok"] is True
    assert reply["rev"] == 1
    assert reply["title"] == TITLE

    shown = subprocess.run(
        [
            sys.executable,
            str(CROSS_LIVE),
            "board",
            "--data-db",
            str(data_file(hermes_home)),
            "--session",
            SOURCE,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert shown.returncode == 0, shown.stderr
    board = last_json(shown.stdout)
    assert board["rev"] == 1
    assert board["copied"] == []
    items = board["items"]
    assert isinstance(items, list)
    assert [(i["text"], i["parent_id"], i["checked"]) for i in items] == [
        ("Call John", None, False),
        ("Ask about the quote", 1, False),
        ("Book the van", None, True),
    ]
    assert {i["updated_by"] for i in items} == {"user"}
    state = sqlite3.connect(f"file:{hermes_home / 'state.db'}?mode=ro", uri=True)
    try:
        title = state.execute("SELECT title FROM sessions WHERE id = ?", (SOURCE,)).fetchone()
    finally:
        state.close()
    assert title == (TITLE,)
