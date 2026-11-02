"""The live test tools of phase 5: the scripted Theo edit, the run readers and the home builder.

`theo_edit.py` runs under the gateway venv Python against a temporary HERMES_HOME (marker
hermes). The other tests load the live scripts by file path and never start a gateway.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

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
) -> tuple[list[Any], list[Any]]:
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


FIXED_COST = 2000


def bare_from(quiet: list[Any]) -> list[Any]:
    """A bare arm: no note, the quiet arm's user characters, input tokens a fixed amount lower."""
    return [
        replace(run, input_tokens=run.input_tokens - FIXED_COST, reminder=False) for run in quiet
    ]


def compare_pair(
    edits: list[Any], quiet: list[Any], bare: list[Any] | None = None, reminder_chars: int = 0
) -> dict[str, object]:
    live = load_live("delta_live", DELTA_LIVE)
    chosen = bare_from(quiet) if bare is None else bare
    return live.compare(edits, quiet, chosen, live.EDIT_RUNS, reminder_chars)


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
        [replace(run, reminder=True) for run in edits],
        [replace(run, reminder=True) for run in quiet],
    )

    assert report["pass"] is True


def failing_cases() -> dict[str, tuple[str, list[Any], list[Any]]]:
    cases: dict[str, tuple[str, list[Any], list[Any]]] = {}

    edits, quiet = arm_pair()
    quiet[2] = replace(quiet[2], reminder=True)
    cases["reminder on one arm only"] = ("reminder_runs_match", edits, quiet)

    edits, quiet = arm_pair()
    quiet[7] = replace(quiet[7], note="x")
    cases["note on a quiet run"] = ("notes_only_on_edit_runs", edits, quiet)

    edits, quiet = arm_pair()
    edits[9] = replace(edits[9], note=None)
    cases["missing note on an edit run"] = ("notes_only_on_edit_runs", edits, quiet)

    edits, quiet = arm_pair()
    edits[11] = replace(edits[11], note="x")
    cases["note on a non-edit run"] = ("notes_only_on_edit_runs", edits, quiet)

    edits, quiet = arm_pair(notes={**NOTES, 5: "z" * 1001})
    cases["note of 1001 characters"] = ("every_note_within_cap", edits, quiet)

    edits, quiet = arm_pair()
    edits[-1] = replace(edits[-1], user_chars=edits[-1].user_chars + 1)
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


def seed_state_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT,"
        " content TEXT, api_content TEXT, active INTEGER)"
    )
    rows = [
        (1, "s1", "user", "ok", None, 1),
        (2, "s1", "assistant", "ok", None, 1),
        (3, "s1", "user", "ok", "ok\n\nNOTE", 1),
        (4, "s1", "assistant", "ok!", None, 1),
        (5, "s1", "user", "ok", "ok\n\nGONE", 0),
        (6, "other", "user", "secret words", None, 1),
    ]
    conn.executemany("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()


def test_rows_report_reads_only_the_given_session_read_only(tmp_path: Path) -> None:
    live = load_live("delta_live", DELTA_LIVE)
    state = tmp_path / "state.db"
    seed_state_db(state)

    report = live.session_report(state, tmp_path / "missing.db", "s1", "")

    assert [row["note"] for row in report["user_rows"]] == [None, "NOTE"]
    assert [row["chars"] for row in report["assistant_rows"]] == [2, 3]
    assert report["board"] is None
    assert "secret words" not in json.dumps(report)
    with pytest.raises(sqlite3.OperationalError):
        live.open_ro(state).execute("INSERT INTO messages (id) VALUES (99)")


def test_build_runs_counts_cumulative_characters(tmp_path: Path) -> None:
    live = load_live("delta_live", DELTA_LIVE)
    state = tmp_path / "state.db"
    seed_state_db(state)

    runs = live.build_runs(live.read_rows(state, "s1"), [100, 130], "")

    assert [(r.run, r.input_tokens, r.note) for r in runs] == [(1, 100, None), (2, 130, "NOTE")]
    assert [r.user_chars for r in runs] == [2, 2 + len("ok\n\nNOTE")]
    assert [r.assistant_chars for r in runs] == [2, 5]


# ---- twin test homes, the no-plugin arm, the gateway stop and the port check ----

MAKE_HOME = LIVE_DIR / "make_home.py"
SOURCE_MARKERS = ("MARKER-BASE-URL-1", "MARKER-SECRET-2")
FAKE_SOURCE: dict[str, Any] = {
    "_config_version": 7,
    "model": {"provider": "prov", "default": "m1", "base_url": SOURCE_MARKERS[0]},
    "platforms": {"telegram": {"enabled": True}, "webhook": {"enabled": True}},
    "mcp_servers": {"kb": {"oauth": {"client_secret": SOURCE_MARKERS[1]}}},
    "secrets": {"command": "get-secret"},
    "memory": {"provider": "hindsight", "memory_enabled": True},
    "gateway": {"multiplex_profiles": True},
    "kanban": {"on": True},
    "telemetry": {"on": True},
    "updates": {"check": True, "interval": 3},
    "fallback_providers": ["other"],
    "agent": {"max_turns": 5},
    "plugins": {
        "enabled": ["prov", "a", "b", "c", "d"],
        "entries": {"prov": {"mode": "x"}, "a": {"mode": "y"}},
    },
}


def write_source(root: Path, **changes: Any) -> Path:
    """Write a fake source home with a config, the three secret files and a provider plugin."""
    home = root / "source-home"
    (home / "plugins" / "prov").mkdir(parents=True)
    (home / ".env").write_text("TOKEN=abc\n", encoding="utf-8")
    (home / "auth.json").write_text("{}", encoding="utf-8")
    (home / "mcp-tokens").mkdir()
    # JSON is valid YAML, so the dev environment needs no PyYAML to write the source.
    (home / "config.yaml").write_text(json.dumps({**FAKE_SOURCE, **changes}), encoding="utf-8")
    return home


def run_make_home(
    root: Path, hermes_home: Path, *extra: str, out: Path | None = None, source: Path | None = None
) -> subprocess.CompletedProcess[str]:
    home = source or write_source(root)
    repo_plugin = root / "repo-plugin"
    repo_plugin.mkdir(exist_ok=True)
    args = [
        "--out",
        str(out or root / "out"),
        "--source",
        str(home / "config.yaml"),
        "--plugins-dir",
        str(home / "plugins"),
        "--repo-plugin",
        str(repo_plugin),
        *extra,
    ]
    return run_gateway_python(MAKE_HOME, args, hermes_home)


PARSE_YAML = "import json, sys, yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))"


def written_config(out: Path) -> dict[str, Any]:
    """Parse the written config.yaml with the gateway Python, which has PyYAML."""
    done = subprocess.run(
        [str(GATEWAY_PYTHON), "-I", "-c", PARSE_YAML, str(out / "config.yaml")],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return json.loads(done.stdout)


@pytest.mark.hermes
def test_make_home_keeps_only_the_allowlist(tmp_path: Path, hermes_home: Path) -> None:
    done = run_make_home(tmp_path, hermes_home)

    assert done.returncode == 0, done.stderr
    config = written_config(tmp_path / "out")
    for dropped in ("mcp_servers", "secrets", "gateway", "kanban", "telemetry"):
        assert dropped not in config
    assert "fallback_providers" not in config
    assert config["updates"] == {"check": False}
    assert all(block == {"enabled": False} for block in config["platforms"].values())
    assert {"telegram", "webhook"} <= set(config["platforms"])
    assert config["memory"]["memory_enabled"] is False
    assert config["model"] == FAKE_SOURCE["model"]


@pytest.mark.hermes
def test_make_home_enables_only_the_provider_or_also_the_board_plugin(
    tmp_path: Path, hermes_home: Path
) -> None:
    bare = run_make_home(tmp_path, hermes_home, out=tmp_path / "bare")
    plugin = run_make_home(tmp_path, hermes_home, "--with-plugin", out=tmp_path / "plugin")

    assert bare.returncode == 0, bare.stderr
    assert plugin.returncode == 0, plugin.stderr
    assert written_config(tmp_path / "bare")["plugins"]["enabled"] == ["prov"]
    assert written_config(tmp_path / "plugin")["plugins"]["enabled"] == [
        "prov",
        "hermes-session-tasks",
    ]
    linked = tmp_path / "plugin" / "plugins"
    assert (linked / "prov").is_symlink()
    assert (linked / "prov").resolve() == (tmp_path / "source-home" / "plugins" / "prov").resolve()
    assert (linked / "hermes-session-tasks").resolve() == (tmp_path / "repo-plugin").resolve()
    assert not (tmp_path / "bare" / "plugins" / "hermes-session-tasks").exists()


@pytest.mark.hermes
def test_make_home_holds_no_secret_file(tmp_path: Path, hermes_home: Path) -> None:
    done = run_make_home(tmp_path, hermes_home, "--with-plugin")

    assert done.returncode == 0, done.stderr
    for name in (".env", "auth.json", "mcp-tokens"):
        assert not (tmp_path / "out" / name).exists()
    helped = run_gateway_python(MAKE_HOME, ["--help"], hermes_home).stdout
    options = {word.rstrip(",") for word in helped.split() if word.startswith("-")}
    assert options == {
        "-h",
        "--help",
        "--out",
        "--with-plugin",
        "--source",
        "--plugins-dir",
        "--repo-plugin",
    }


def test_make_home_turns_every_listener_off() -> None:
    make_home = load_live("make_home", MAKE_HOME)
    source = {"platforms": {"telegram": {"enabled": True}, "webhook": {"enabled": True}}}

    config = make_home.test_home_config(source, "prov", False)

    assert config["platforms"] == {
        "telegram": {"enabled": False},
        "webhook": {"enabled": False},
        "api_server": {"enabled": False},
        "msgraph_webhook": {"enabled": False},
    }
    assert config["proxy"]["enabled"] is False
    assert config["updates"]["check"] is False
    assert config["plugins"]["auto_update_check_hours"] == 0


@pytest.mark.hermes
def test_make_home_refuses_a_kept_port(tmp_path: Path, hermes_home: Path) -> None:
    refused = run_make_home(
        tmp_path, hermes_home, source=write_source(tmp_path, web={"port": 8644})
    )

    assert refused.returncode == 2
    assert not (tmp_path / "out").exists()
    allowed = write_source(tmp_path / "ok", web={"port": 0}, streaming={"transport": "auto"})
    passed = run_make_home(tmp_path / "ok", hermes_home, source=allowed)
    assert passed.returncode == 0, passed.stderr


@pytest.mark.hermes
def test_make_home_prints_no_config_value(tmp_path: Path, hermes_home: Path) -> None:
    done = run_make_home(tmp_path, hermes_home, "--with-plugin")

    assert done.returncode == 0, done.stderr
    for marker in SOURCE_MARKERS:
        assert marker not in done.stdout
        assert marker not in done.stderr
    assert set(json.loads(done.stdout)) == {"home", "enabled", "kept_keys", "listeners_off"}


@pytest.mark.hermes
def test_make_home_refuses_the_real_home_and_a_secret_looking_kept_key(
    tmp_path: Path, hermes_home: Path
) -> None:
    source = write_source(tmp_path)
    inside = source / "test-home"

    refused_home = run_make_home(tmp_path, hermes_home, out=inside, source=source)

    assert refused_home.returncode == 2
    assert not inside.exists()
    leaky = write_source(tmp_path / "leaky", agent={"api_key": "abc"})
    refused_key = run_make_home(tmp_path / "leaky", hermes_home, source=leaky)
    assert refused_key.returncode == 2
    assert not (tmp_path / "leaky" / "out").exists()
    assert "abc" not in refused_key.stdout + refused_key.stderr


@pytest.mark.hermes
def test_make_home_sets_private_modes(tmp_path: Path, hermes_home: Path) -> None:
    done = run_make_home(tmp_path, hermes_home)

    assert done.returncode == 0, done.stderr
    assert (tmp_path / "out").stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "out" / "config.yaml").stat().st_mode & 0o777 == 0o600


def three_arms(**changes: Any) -> tuple[list[Any], list[Any], list[Any]]:
    edits, quiet = arm_pair()
    return edits, quiet, bare_from(quiet)


def test_compare_three_arms_passes_with_a_positive_fixed_cost() -> None:
    edits, quiet, bare = three_arms()

    report = compare_pair(edits, quiet, bare)

    assert report["pass"] is True
    assert report["fixed_cost_tokens_run1"] == FIXED_COST
    assert report["fixed_cost_tokens_runN"] == FIXED_COST
    assert (
        report["edits_minus_bare_tokens_runN"]
        == report["fixed_cost_tokens_runN"] + report["edits_minus_quiet_tokens_runN"]  # pyright: ignore[reportOperatorIssue]
    )


def test_compare_names_a_note_on_a_bare_run() -> None:
    edits, quiet, bare = three_arms()
    bare[3] = replace(bare[3], note="x")

    report = compare_pair(edits, quiet, bare)

    assert report["pass"] is False
    assert report["bare_arm_has_no_note"] is False


def test_compare_names_a_fixed_user_char_difference_off_by_one() -> None:
    edits, quiet, bare = three_arms()
    bare[-1] = replace(bare[-1], user_chars=bare[-1].user_chars + 1)

    report = compare_pair(edits, quiet, bare)

    assert report["pass"] is False
    assert report["fixed_user_chars_match_reminder"] is False


def test_compare_names_a_fixed_cost_that_is_not_positive() -> None:
    edits, quiet, bare = three_arms()
    bare[0] = replace(bare[0], input_tokens=quiet[0].input_tokens)

    report = compare_pair(edits, quiet, bare)

    assert report["pass"] is False
    assert report["fixed_cost_positive"] is False


def test_fixed_user_chars_with_a_reminder() -> None:
    reminder_chars = 10
    extra = reminder_chars + 2
    edits, quiet = arm_pair()
    quiet = [
        replace(run, reminder=True, user_chars=run.user_chars + extra * run.run) for run in quiet
    ]
    edits = [
        replace(run, reminder=True, user_chars=run.user_chars + extra * run.run) for run in edits
    ]
    bare = [
        replace(run, user_chars=run.user_chars - extra * run.run, reminder=False) for run in quiet
    ]

    passed = compare_pair(edits, quiet, bare, reminder_chars)
    wrong = compare_pair(
        edits,
        quiet,
        bare[:-1] + [replace(bare[-1], user_chars=bare[-1].user_chars + 1)],
        reminder_chars,
    )

    assert quiet[-1].user_chars - bare[-1].user_chars == 30 * 12
    assert passed["pass"] is True
    assert wrong["fixed_user_chars_match_reminder"] is False


def write_pid_file(home: Path, pid: int, hermes_home: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "gateway.pid").write_text(
        json.dumps({"pid": pid, "kind": "hermes-gateway", "hermes_home": str(hermes_home)}),
        encoding="utf-8",
    )


def test_stop_refuses_a_pid_file_for_another_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live = load_live("delta_live", DELTA_LIVE)
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: calls.append((pid, sig)))
    home = tmp_path / "test-home"
    write_pid_file(home, os.getpid(), tmp_path / "another-home")

    assert live.stop_test_gateway(home) == "refused"
    assert calls == []


def test_stop_reports_not_running_without_a_pid_file(tmp_path: Path) -> None:
    live = load_live("delta_live", DELTA_LIVE)

    assert live.stop_test_gateway(tmp_path / "test-home") == "not running"


def test_stop_ends_a_process_whose_environment_names_the_home(tmp_path: Path) -> None:
    live = load_live("delta_live", DELTA_LIVE)
    home = tmp_path / "test-home"
    home.mkdir()
    child = subprocess.Popen(["sleep", "60"], env={**os.environ, "HERMES_HOME": str(home)})
    write_pid_file(home, child.pid, home)
    try:
        assert live.stop_test_gateway(home) == "stopped"
    finally:
        child.kill()
        child.wait()


def test_stop_refuses_a_process_whose_environment_names_another_home(tmp_path: Path) -> None:
    live = load_live("delta_live", DELTA_LIVE)
    home = tmp_path / "test-home"
    home.mkdir()
    child = subprocess.Popen(
        ["sleep", "60"], env={**os.environ, "HERMES_HOME": str(tmp_path / "real")}
    )
    write_pid_file(home, child.pid, home)
    try:
        assert live.stop_test_gateway(home) == "refused"
        assert child.poll() is None
    finally:
        child.kill()
        child.wait()


SS_SAMPLE = """State  Recv-Q Send-Q  Local Address:Port  Peer Address:PortProcess
LISTEN 0      128           0.0.0.0:8644       0.0.0.0:*    users:(("hermes",pid=2635829,fd=43))
LISTEN 0      2048        127.0.0.1:43759      0.0.0.0:*    users:(("hermes",pid=2635829,fd=23))
LISTEN 0      4096        127.0.0.1:27019      0.0.0.0:*
LISTEN 0      128              [::]:8644          [::]:*    users:(("hermes",pid=2635829,fd=44))
LISTEN 0      2048        127.0.0.1:44041      0.0.0.0:*    users:(("hermes",pid=324070,fd=11))
"""


def test_parse_ss_reads_the_ports_of_one_pid() -> None:
    live = load_live("delta_live", DELTA_LIVE)

    assert live.parse_ss(SS_SAMPLE, 2635829) == {
        ("0.0.0.0", 8644),
        ("127.0.0.1", 43759),
        ("::", 8644),
    }


def test_port_clash_names_a_shared_port_and_a_public_listener() -> None:
    live = load_live("delta_live", DELTA_LIVE)
    real = {("0.0.0.0", 8644)}

    assert any("8644" in line for line in live.port_clash({("127.0.0.1", 8644)}, real))
    assert any("0.0.0.0" in line for line in live.port_clash({("0.0.0.0", 51000)}, real))
    assert live.port_clash({("127.0.0.1", 51000)}, real) == []
