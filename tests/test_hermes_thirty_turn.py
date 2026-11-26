"""The 30-turn token test without the model, through Hermes's own hook dispatch and composer.

The gateway venv Python runs `hermes_thirty_turn_snippet.py` against a temporary HERMES_HOME.
The test needs the hermes-agent checkout (marker hermes).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import HERMES_AGENT_REPO
from session_tasks import delta

pytestmark = pytest.mark.hermes

GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"
SNIPPET = Path(__file__).resolve().parent / "hermes_thirty_turn_snippet.py"
PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugin"
NOTE_TURNS = [5, 12, 20, 25]
SEPARATOR_LENGTH = len("\n\n")


def run_snippet(hermes_home: Path) -> dict[str, Any]:
    if not GATEWAY_PYTHON.exists():
        pytest.skip(f"gateway venv python not found at {GATEWAY_PYTHON}")
    env = {**os.environ, "HERMES_HOME": str(hermes_home)}
    done = subprocess.run(
        [str(GATEWAY_PYTHON), "-I", str(SNIPPET), str(PLUGIN_DIR), str(HERMES_AGENT_REPO)],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def note_at(arm: list[dict[str, Any]], turn: int) -> str:
    note = arm[turn - 1]["note"]
    assert isinstance(note, str)
    return note


def test_quiet_arm_adds_nothing_on_every_turn(hermes_home: Path) -> None:
    out = run_snippet(hermes_home)

    assert len(out["quiet"]) == 30
    assert [row["note"] for row in out["quiet"]] == [None] * 30
    assert [row["added"] for row in out["quiet"]] == [0] * 30


def test_notes_only_follow_theo_edits(hermes_home: Path) -> None:
    out = run_snippet(hermes_home)

    assert len(out["edits"]) == 30
    noted = [row["turn"] for row in out["edits"] if row["note"] is not None]
    assert noted == NOTE_TURNS
    assert all(row["added"] == 0 for row in out["edits"] if row["note"] is None)


def test_note_lines_name_each_change(hermes_home: Path) -> None:
    out = run_snippet(hermes_home)
    edits = out["edits"]

    first = note_at(edits, 5)
    assert "added #3 Call John" in first
    assert "added #4 Book the van" in first
    second = note_at(edits, 12)
    assert "checked #3" in second
    assert 'renamed #4 "Book the van for Friday"' in second
    assert "removed #4" in note_at(edits, 20)
    for turn in (5, 12, 20, 25):
        assert "Plan step" not in note_at(edits, turn)
    assert note_at(edits, 25) == delta.pointer_line(out["pointer_turn_rev"])


def test_every_note_is_within_the_cap(hermes_home: Path) -> None:
    out = run_snippet(hermes_home)

    notes = [row["note"] for row in out["edits"] if row["note"] is not None]
    assert len(notes) == len(NOTE_TURNS)
    assert all(len(note) <= delta.DELTA_MAX_CHARS for note in notes)


def test_thirty_turns_add_exactly_the_notes(hermes_home: Path) -> None:
    out = run_snippet(hermes_home)

    edits_total = sum(row["added"] for row in out["edits"])
    quiet_total = sum(row["added"] for row in out["quiet"])
    note_total = sum(
        len(row["note"]) + SEPARATOR_LENGTH for row in out["edits"] if row["note"] is not None
    )
    assert note_total > 0
    assert edits_total - quiet_total == note_total
