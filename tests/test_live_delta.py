"""The live test tools of phase 5: the scripted Theo edit, the run readers and the home builder.

`theo_edit.py` runs under the gateway venv Python against a temporary HERMES_HOME (marker
hermes). The other tests load the live scripts by file path and never start a gateway.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest
from conftest import HERMES_AGENT_REPO
from session_tasks import paths
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"
LIVE_DIR = Path(__file__).resolve().parent / "live" / "delta"
THEO_EDIT = LIVE_DIR / "theo_edit.py"
DELTA_LIVE = LIVE_DIR / "delta_live.py"
SESSION = "live-s1"


def load_live(name: str, path: Path) -> ModuleType:
    """Load a live script by its file path. The module is registered so dataclasses resolve."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


# ---- pure helpers of delta_live.py ----

NOTES = {5: "a" * 60, 10: "b" * 40, 15: "c" * 80, 20: "d" * 30, 25: "e" * 50}
RUNS = 30


def arm_pair(
    ratio: float = 0.3, notes: dict[int, str] | None = None
) -> tuple[list[object], list[object]]:
    """Return (edits, quiet) arms that satisfy every check, for the given token ratio."""
    live = load_live("delta_live", DELTA_LIVE)
    chosen = NOTES if notes is None else notes
    quiet = []
    edits = []
    for run in range(1, RUNS + 1):
        extra = sum(len(text) + live.JOINER for at, text in chosen.items() if at <= run)
        base = live.ArmRun(
            run=run,
            input_tokens=1000 + 50 * run,
            note=None,
            user_chars=40 * run,
            assistant_chars=10 * run,
        )
        quiet.append(base)
        edits.append(
            replace(
                base,
                note=chosen.get(run),
                user_chars=base.user_chars + extra,
                input_tokens=base.input_tokens + round(ratio * extra),
            )
        )
    return edits, quiet


def compare_pair(edits: list[object], quiet: list[object]) -> dict[str, object]:
    live = load_live("delta_live", DELTA_LIVE)
    return live.compare(edits, quiet, live.EDIT_RUNS)


def test_parse_result_reads_the_last_result_event() -> None:
    live = load_live("delta_live", DELTA_LIVE)
    lines = [
        "not json",
        json.dumps({"type": "assistant", "text": "hi"}),
        json.dumps({
            "type": "result",
            "session_id": "s-old",
            "exit_code": 1,
            "tokens": {"input": 5},
        }),
        json.dumps({
            "type": "result",
            "session_id": "s-new",
            "exit_code": 0,
            "tokens": {"input": 96089},
        }),
    ]

    assert live.parse_result(lines) == live.RunResult("s-new", 0, 96089)
    assert live.parse_result(lines[:2]) is None


def test_note_of_returns_the_added_text() -> None:
    live = load_live("delta_live", DELTA_LIVE)

    assert live.note_of("ok", "ok\n\nNOTE") == "NOTE"
    assert live.note_of("ok", None) is None
    assert live.note_of("ok", "ok") is None
    assert live.note_of("ok", "other\n\nNOTE") is None


def test_edit_ops_follow_the_script() -> None:
    live = load_live("delta_live", DELTA_LIVE)

    assert live.edit_ops(5) == [
        {"op": "add", "text": "Call John"},
        {"op": "add", "text": "Book the van"},
    ]
    assert live.edit_ops(10) == [{"op": "set_checked", "item_id": 1, "checked": True}]
    assert live.edit_ops(15) == [
        {"op": "set_text", "item_id": 2, "text": "Book the van for Friday"}
    ]
    assert live.edit_ops(20) == [{"op": "add", "text": "Pay the invoice"}]
    assert live.edit_ops(25) == [{"op": "remove", "item_id": 3}]
    assert live.edit_ops(6) is None


def test_split_reminder_separates_the_fixed_line() -> None:
    live = load_live("delta_live", DELTA_LIVE)

    assert live.split_reminder("R", "R") == (True, None)
    assert live.split_reminder("R\n\nNOTE", "R") == (True, "NOTE")
    assert live.split_reminder("NOTE", "R") == (False, "NOTE")
    assert live.split_reminder(None, "R") == (False, None)
    for text in ("R", "R\n\nNOTE", "NOTE", None):
        assert live.split_reminder(text, "") == (False, text)


def test_compare_passes_for_matching_arms() -> None:
    edits, quiet = arm_pair()

    report = compare_pair(edits, quiet)

    assert report["pass"] is True
    assert 0.29 < report["token_ratio"] < 0.31  # pyright: ignore[reportOperatorIssue]


def test_compare_passes_with_the_same_reminder_on_every_run_of_both_arms() -> None:
    edits, quiet = arm_pair()

    report = compare_pair(
        [replace(run, reminder=True) for run in edits],  # pyright: ignore[reportArgumentType]
        [replace(run, reminder=True) for run in quiet],  # pyright: ignore[reportArgumentType]
    )

    assert report["pass"] is True


def failing_cases() -> dict[str, tuple[str, list[object], list[object]]]:
    cases: dict[str, tuple[str, list[object], list[object]]] = {}

    edits, quiet = arm_pair()
    quiet[2] = replace(quiet[2], reminder=True)  # pyright: ignore[reportArgumentType]
    cases["reminder on one arm only"] = ("reminder_runs_match", edits, quiet)

    edits, quiet = arm_pair()
    quiet[7] = replace(quiet[7], note="x")  # pyright: ignore[reportArgumentType]
    cases["note on a quiet run"] = ("notes_only_on_edit_runs", edits, quiet)

    edits, quiet = arm_pair()
    edits[9] = replace(edits[9], note=None)  # pyright: ignore[reportArgumentType]
    cases["missing note on an edit run"] = ("notes_only_on_edit_runs", edits, quiet)

    edits, quiet = arm_pair()
    edits[11] = replace(edits[11], note="x")  # pyright: ignore[reportArgumentType]
    cases["note on a non-edit run"] = ("notes_only_on_edit_runs", edits, quiet)

    edits, quiet = arm_pair(notes={**NOTES, 5: "z" * 1001})
    cases["note of 1001 characters"] = ("every_note_within_cap", edits, quiet)

    edits, quiet = arm_pair()
    edits[-1] = replace(edits[-1], user_chars=edits[-1].user_chars + 1)  # pyright: ignore[reportAttributeAccessIssue]
    cases["user character difference off by one"] = ("user_char_diff_equals_notes", edits, quiet)

    edits, quiet = arm_pair(ratio=0.1)
    cases["token ratio 0.1"] = ("token_growth_ratio_in_band", edits, quiet)

    edits, quiet = arm_pair(ratio=0.6)
    cases["token ratio 0.6"] = ("token_growth_ratio_in_band", edits, quiet)
    return cases


@pytest.mark.parametrize("name", list(failing_cases()))
def test_compare_names_the_failed_check(name: str) -> None:
    key, edits, quiet = failing_cases()[name]

    report = compare_pair(edits, quiet)

    assert report["pass"] is False
    assert report[key] is False
