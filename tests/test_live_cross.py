"""The live test tools of phase 6: seed a source board, read a board, list tool calls, stop a test gateway."""

from __future__ import annotations

import hashlib
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
from session_tasks import paths
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

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


# ---- refusals, the board read, the call listing and the gateway stop ----


def seed_argv() -> list[str]:
    return ["seed", "--session", SOURCE, "--title", TITLE, "--ops", OPS]


def test_seed_refuses_the_real_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cross = load_live("cross_live_refuse", CROSS_LIVE)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    real = tmp_path / ".hermes"
    monkeypatch.setenv("HERMES_HOME", str(real))

    code = cross.main(seed_argv())

    assert code == 2
    assert "refuses" in capsys.readouterr().err
    assert not real.exists()


def test_seed_refuses_an_unset_home(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cross = load_live("cross_live_unset", CROSS_LIVE)
    monkeypatch.delenv("HERMES_HOME", raising=False)

    assert cross.main(seed_argv()) == 2
    assert "HERMES_HOME" in capsys.readouterr().err


def test_refuse_real_home_allows_a_test_home(tmp_path: Path) -> None:
    cross = load_live("cross_live_allow", CROSS_LIVE)

    assert (
        cross.refuse_real_home({"HERMES_HOME": str(tmp_path / "test")}, tmp_path / ".hermes")
        is None
    )
    assert cross.refuse_real_home({"HERMES_HOME": "  "}, tmp_path / ".hermes") is not None


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_board_reads_items_and_copied_rows_read_only(tmp_path: Path) -> None:
    cross = load_live("cross_live_board", CROSS_LIVE)
    file = tmp_path / "data.db"
    store = BoardStore(lambda: paths.connect_path(file))
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply(
        "s2",
        [AddItem("Call John"), AddItem("Book the van", checked=True)],
        actor="agent",
        base_rev=0,
    )
    store.copy_items("s1", "s2", None, actor="agent")
    before = digest(file)

    board = cross.read_board(file, "s1")

    assert board is not None
    assert board["rev"] == 2
    assert [i["text"] for i in board["items"]] == ["Mine", "Call John"]
    new_id = board["items"][1]["id"]
    assert board["copied"] == [
        {"rev": 2, "actor": "agent", "item_id": new_id, "text": "s2#1"},
    ]
    assert digest(file) == before


def test_board_reports_a_missing_board_with_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cross = load_live("cross_live_noboard", CROSS_LIVE)
    file = tmp_path / "data.db"
    BoardStore(lambda: paths.connect_path(file)).apply(
        "s1", [AddItem("Mine")], actor="agent", base_rev=0
    )

    code = cross.main(["board", "--data-db", str(file), "--session", "nope"])

    assert code == 2
    assert "no board" in capsys.readouterr().err


def test_board_reports_a_missing_file_with_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cross = load_live("cross_live_nofile", CROSS_LIVE)

    code = cross.main(["board", "--data-db", str(tmp_path / "none.db"), "--session", "s1"])

    assert code == 2
    assert "no data file" in capsys.readouterr().err


def test_calls_lists_tool_uses_and_bridged_calls(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cross = load_live("cross_live_calls", CROSS_LIVE)
    run = tmp_path / "run.jsonl"
    lines = [
        json.dumps({"type": "tool_use", "name": "board_sessions", "input": {}}),
        json.dumps({
            "type": "tool_use",
            "name": "tool_call",
            "input": {"name": "board_copy", "arguments": '{"from_session_id": "cross-src-1"}'},
        }),
        json.dumps({"type": "text", "text": "done"}),
        "not json",
    ]
    run.write_text("\n".join(lines) + "\n", encoding="utf-8")
    expected = [
        {"name": "board_sessions", "args": {}},
        {"name": "board_copy", "args": {"from_session_id": "cross-src-1"}},
    ]

    assert cross.tool_calls(run) == expected
    assert cross.main(["calls", str(run)]) == 0
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1]) == expected


def test_stop_reports_not_running_without_a_pid_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cross = load_live("cross_live_stop", CROSS_LIVE)

    code = cross.main(["stop", "--home", str(tmp_path)])

    assert code == 0
    assert "not running" in capsys.readouterr().out


def test_stop_refuses_a_pid_file_that_names_another_home(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cross = load_live("cross_live_refused", CROSS_LIVE)
    home = tmp_path / "test-home"
    home.mkdir()
    record = {"pid": os.getpid(), "hermes_home": str(tmp_path / "other")}
    (home / "gateway.pid").write_text(json.dumps(record), encoding="utf-8")

    code = cross.main(["stop", "--home", str(home)])

    assert code == 1
    assert "refused" in capsys.readouterr().out
