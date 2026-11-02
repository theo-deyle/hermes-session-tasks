"""Live measurement tool for the note of Theo's board changes (standard library only).

Run it with `.venv-py3.14/bin/python -I`. The system python3 links SQLite 3.40.1.

Subcommands:
  result FILE      Print the session id, the exit code and the input tokens of the last
                   `result` event of a `hermes chat --format stream-json` run.
  rows --session   Print, for one session, the note the hook added to each user row, the text
                   length of each row, and the board rev and agent_seen_rev.
  arms --out DIR --plugin-home A --bare-home B
                   Run three interleaved headless arms on one query and judge them. The edits
                   arm gets Theo's scripted edits before runs 5, 10, 15, 20 and 25. The quiet
                   arm gets none. Both run in home A with the plugin on. The bare arm runs in
                   home B, the same config with the plugin off. Three numbers come out: the
                   notes size (edits minus quiet), the plugin fixed cost (quiet minus bare) and
                   the sum against the no-plugin arm (edits minus bare). SC3 reads as all three.
                   On every exit path it stops the test gateways it caused.
  ports --home DIR ... --real-home DIR
                   List the listening TCP ports of each test gateway and of the real gateway.
                   Exit 1 when a test port equals a real port or a test listener is not on
                   loopback, 2 when a gateway.pid is missing.

Exit codes: 0 pass, 1 measured fail, 2 broken run or read error.
Every state file opens read only (a sqlite URI with mode=ro). The tool prints lengths and the
plugin's own note text, never the text of a session it was not given.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
THEO_EDIT = HERE / "theo_edit.py"
OK_QUERY = HERE / "ok.txt"
AGENT_REPO = Path(os.environ.get("HERMES_AGENT_REPO") or Path.home() / ".hermes" / "hermes-agent")
GATEWAY_PYTHON = AGENT_REPO.expanduser() / "venv" / "bin" / "python"
DEFAULT_HOME = Path.home() / ".hermes"
DATA_RELATIVE = Path("plugin-data") / "hermes-session-tasks" / "data.db"

EDIT_RUNS = (5, 10, 15, 20, 25)
NOTE_MAX = 1000
TOKENS_PER_CHAR_MIN = 0.15
TOKENS_PER_CHAR_MAX = 0.5
JOINER = 2
RUN_TIMEOUT = 300
HOOK_FAULT = "pre_llm_call hook failed"
CHECKS = (
    "reminder_runs_match",
    "notes_only_on_edit_runs",
    "every_note_within_cap",
    "user_char_diff_equals_notes",
    "token_growth_ratio_in_band",
    "bare_arm_has_no_note",
    "fixed_user_chars_match_reminder",
    "fixed_cost_positive",
)
STOP_WAIT = 30.0
LOOPBACK = ("127.0.0.1", "::1")
PID_FIELD = re.compile(r"pid=(\d+)")

Ops = list[dict[str, object]]


class BrokenRun(Exception):
    """A run that cannot be judged: stop at once and spend no more model calls."""


@dataclass(frozen=True)
class RunResult:
    session_id: str
    exit_code: int
    input_tokens: int


@dataclass(frozen=True)
class ArmRun:
    run: int
    input_tokens: int
    note: str | None
    user_chars: int
    assistant_chars: int
    reminder: bool = False


def parse_result(lines: Iterable[str]) -> RunResult | None:
    """Return the values of the last well-formed `result` event, or None."""
    found: RunResult | None = None
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("type") != "result":
            continue
        tokens = event.get("tokens")
        session = event.get("session_id")
        code = event.get("exit_code")
        used = tokens.get("input") if isinstance(tokens, dict) else None
        if isinstance(session, str) and isinstance(code, int) and isinstance(used, int):
            found = RunResult(session, code, used)
    return found


def note_of(content: str, api_content: str | None) -> str | None:
    """Return the text the hook added after the user text, or None when nothing was added."""
    if api_content is None:
        return None
    prefix = content + "\n\n"
    if not api_content.startswith(prefix) or len(api_content) == len(prefix):
        return None
    return api_content[len(prefix) :]


def split_reminder(injected: str | None, reminder: str) -> tuple[bool, str | None]:
    """Split a fixed reminder line off the front of the injected text."""
    if not reminder or injected is None or not injected.startswith(reminder):
        return False, injected
    rest = injected[len(reminder) :]
    if not rest:
        return True, None
    if rest.startswith("\n\n") and len(rest) > JOINER:
        return True, rest[JOINER:]
    return False, injected


def edit_ops(run: int) -> Ops | None:
    """Return Theo's scripted edit for a run, or None when Theo does not edit before it."""
    script: dict[int, Ops] = {
        5: [{"op": "add", "text": "Call John"}, {"op": "add", "text": "Book the van"}],
        10: [{"op": "set_checked", "item_id": 1, "checked": True}],
        15: [{"op": "set_text", "item_id": 2, "text": "Book the van for Friday"}],
        20: [{"op": "add", "text": "Pay the invoice"}],
        25: [{"op": "remove", "item_id": 3}],
    }
    return script.get(run)


def _reminder_runs(arm: Sequence[ArmRun]) -> set[int]:
    return {item.run for item in arm if item.reminder}


def _notes_only_on_edit_runs(
    edits: Sequence[ArmRun], quiet: Sequence[ArmRun], edit_runs: Sequence[int]
) -> bool:
    if any(item.note is not None for item in quiet):
        return False
    return {item.run for item in edits if item.note is not None} == set(edit_runs)


def _user_diff_matches_notes(edits: Sequence[ArmRun], quiet: Sequence[ArmRun]) -> bool:
    expected = 0
    for loud, calm in zip(edits, quiet, strict=True):
        if loud.note is not None:
            expected += len(loud.note) + JOINER
        if loud.user_chars - calm.user_chars != expected:
            return False
    return True


def _fixed_user_chars_match(
    quiet: Sequence[ArmRun], bare: Sequence[ArmRun], reminder_chars: int
) -> bool:
    """Quiet minus bare user characters must equal the reminder lines alone (0 without one)."""
    unit = reminder_chars + JOINER if reminder_chars else 0
    expected = 0
    for calm, plain in zip(quiet, bare, strict=True):
        if calm.reminder:
            expected += unit
        if calm.user_chars - plain.user_chars != expected:
            return False
    return True


def compare(
    edits: Sequence[ArmRun],
    quiet: Sequence[ArmRun],
    bare: Sequence[ArmRun],
    edit_runs: Sequence[int],
    reminder_chars: int = 0,
) -> dict[str, object]:
    """Judge the three arms. `pass` is True only when every check holds."""
    report: dict[str, object] = {key: False for key in CHECKS}
    if not edits or len(edits) != len(quiet) or len(edits) != len(bare):
        report["pass"] = False
        return report
    first_e, last_e = edits[0], edits[-1]
    first_q, last_q = quiet[0], quiet[-1]
    first_b, last_b = bare[0], bare[-1]
    growth_diff = (last_e.input_tokens - first_e.input_tokens) - (
        last_q.input_tokens - first_q.input_tokens
    )
    user_diff = last_e.user_chars - last_q.user_chars
    assistant_diff = last_e.assistant_chars - last_q.assistant_chars
    char_diff = user_diff + assistant_diff
    ratio = growth_diff / char_diff if char_diff > 0 else None
    notes = [item.note for item in edits if item.note is not None]
    fixed_run1 = first_q.input_tokens - first_b.input_tokens
    fixed_last = last_q.input_tokens - last_b.input_tokens
    edits_minus_quiet = last_e.input_tokens - last_q.input_tokens
    report["reminder_runs_match"] = _reminder_runs(edits) == _reminder_runs(quiet)
    report["notes_only_on_edit_runs"] = _notes_only_on_edit_runs(edits, quiet, edit_runs)
    report["every_note_within_cap"] = all(len(note) <= NOTE_MAX for note in notes)
    report["user_char_diff_equals_notes"] = _user_diff_matches_notes(edits, quiet)
    report["token_growth_ratio_in_band"] = (
        ratio is not None
        and growth_diff > 0
        and TOKENS_PER_CHAR_MIN <= ratio <= TOKENS_PER_CHAR_MAX
    )
    report["bare_arm_has_no_note"] = all(item.note is None for item in bare)
    report["fixed_user_chars_match_reminder"] = _fixed_user_chars_match(quiet, bare, reminder_chars)
    report["fixed_cost_positive"] = fixed_run1 > 0
    report["notes_chars"] = sum(len(note) for note in notes)
    report["user_char_diff"] = user_diff
    report["assistant_char_diff"] = assistant_diff
    report["token_growth_diff"] = growth_diff
    report["token_ratio"] = ratio
    report["fixed_cost_tokens_run1"] = fixed_run1
    report["fixed_cost_tokens_runN"] = fixed_last
    report["edits_minus_quiet_tokens_runN"] = edits_minus_quiet
    report["edits_minus_bare_tokens_runN"] = last_e.input_tokens - last_b.input_tokens
    report["pass"] = all(report[key] is True for key in CHECKS)
    return report


def open_ro(path: Path) -> sqlite3.Connection:
    """Open a SQLite file read only: a URI with mode=ro. A missing file raises."""
    return sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)


@dataclass(frozen=True)
class Row:
    id: int
    role: str
    content: str
    api_content: str | None


def read_rows(state_db: Path, session_id: str) -> list[Row]:
    """Return the active rows of one session, oldest first. Only this session is selected."""
    conn = open_ro(state_db)
    try:
        found = conn.execute(
            "SELECT id, role, content, api_content FROM messages"
            " WHERE session_id = ? AND active = 1 ORDER BY id",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    return [Row(int(r[0]), str(r[1]), "" if r[2] is None else str(r[2]), r[3]) for r in found]


def read_board(data_db: Path, session_id: str) -> dict[str, int] | None:
    """Return rev and agent_seen_rev of the board the session maps to, or None."""
    try:
        conn = open_ro(data_db)
    except sqlite3.Error:
        return None
    try:
        alias = conn.execute(
            "SELECT root_id FROM aliases WHERE session_id = ?", (session_id,)
        ).fetchone()
        root = alias[0] if alias else session_id
        board = conn.execute(
            "SELECT rev, agent_seen_rev FROM boards WHERE root_id = ?", (root,)
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return None if board is None else {"rev": int(board[0]), "agent_seen_rev": int(board[1])}


def read_system_prompt_chars(state_db: Path, session_id: str) -> int | None:
    """Return the length of `sessions.system_prompt` of one session, or None."""
    try:
        conn = open_ro(state_db)
    except sqlite3.Error:
        return None
    try:
        found = conn.execute(
            "SELECT length(system_prompt) FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return None if found is None or found[0] is None else int(found[0])


def _alive(pid: int) -> bool:
    """True while the process runs. A zombie counts as ended."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return False
    return stat.rpartition(")")[2].split()[:1] != ["Z"]


def _environ_home(pid: int) -> str | None:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return None
    for item in raw.split(b"\0"):
        if item.startswith(b"HERMES_HOME="):
            return item[len(b"HERMES_HOME=") :].decode("utf-8", errors="replace")
    return None


def stop_test_gateway(home: Path) -> str:
    """Stop the gateway of one test home. Return `stopped`, `not running` or `refused`.

    SIGTERM goes only to the PID of `<home>/gateway.pid` when both its `hermes_home` field and
    the HERMES_HOME of the process name this test home. It never signals the real gateway.
    """
    try:
        record = json.loads((home / "gateway.pid").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "not running"
    except (OSError, ValueError):
        return "refused"
    pid = record.get("pid") if isinstance(record, dict) else None
    named = record.get("hermes_home") if isinstance(record, dict) else None
    if not isinstance(pid, int) or isinstance(pid, bool) or not isinstance(named, str):
        return "refused"
    if Path(named).resolve() != home.resolve():
        return "refused"
    if not _alive(pid):
        return "not running"
    environ_home = _environ_home(pid)
    if environ_home is None or Path(environ_home).resolve() != home.resolve():
        return "refused"
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + STOP_WAIT
    while time.monotonic() < deadline:
        if not _alive(pid):
            return "stopped"
        time.sleep(0.2)
    return "refused"


def parse_ss(text: str, pid: int) -> set[tuple[str, int]]:
    """Return the (address, port) pairs that one PID listens on, from `ss -ltnp` output."""
    found: set[tuple[str, int]] = set()
    for line in text.splitlines():
        if pid not in {int(match) for match in PID_FIELD.findall(line)}:
            continue
        columns = line.split()
        if len(columns) < 4:
            continue
        address, _, port = columns[3].rpartition(":")
        if port.isdigit():
            found.add((address.strip("[]"), int(port)))
    return found


def port_clash(test: set[tuple[str, int]], real: set[tuple[str, int]]) -> list[str]:
    """Name every test port that a real gateway also uses, and every test listener off loopback."""
    real_ports = {port for _, port in real}
    lines: list[str] = []
    for address, port in sorted(test):
        if port in real_ports:
            lines.append(f"test port {port} is also a real gateway port")
        if address not in LOOPBACK:
            lines.append(f"test listener {address}:{port} is not on loopback")
    return lines


def _injected(row: Row, reminder: str) -> tuple[bool, str | None]:
    return split_reminder(note_of(row.content, row.api_content), reminder)


def build_runs(rows: Sequence[Row], tokens: Sequence[int], reminder: str) -> list[ArmRun]:
    """Build one ArmRun per user row. Characters are cumulative up to each run."""
    users = [row for row in rows if row.role == "user"]
    runs: list[ArmRun] = []
    user_total = 0
    for index, row in enumerate(users):
        user_total += len(row.api_content or row.content)
        stop = users[index + 1].id if index + 1 < len(users) else None
        assistant_total = sum(
            len(other.content)
            for other in rows
            if other.role == "assistant" and (stop is None or other.id < stop)
        )
        has_reminder, note = _injected(row, reminder)
        runs.append(
            ArmRun(
                run=index + 1,
                input_tokens=tokens[index] if index < len(tokens) else 0,
                note=note,
                user_chars=user_total,
                assistant_chars=assistant_total,
                reminder=has_reminder,
            )
        )
    return runs


def session_report(
    state_db: Path, data_db: Path, session_id: str, reminder: str
) -> dict[str, object]:
    rows = read_rows(state_db, session_id)
    users: list[dict[str, object]] = []
    assistants: list[dict[str, object]] = []
    for row in rows:
        if row.role == "user":
            has_reminder, note = _injected(row, reminder)
            users.append({
                "id": row.id,
                "note": note,
                "reminder": has_reminder,
                "content_chars": len(row.content),
            })
        elif row.role == "assistant":
            assistants.append({"id": row.id, "chars": len(row.content)})
    return {
        "session_id": session_id,
        "user_rows": users,
        "assistant_rows": assistants,
        "board": read_board(data_db, session_id),
    }


def _read_reminder(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8").rstrip("\r\n")


def _run(
    command: Sequence[str], home: Path, stdout: Path | None = None, stderr: Path | None = None
) -> int:
    env = {**os.environ, "HERMES_HOME": str(home)}
    out = stdout.open("wb") if stdout else subprocess.DEVNULL
    err = stderr.open("wb") if stderr else subprocess.DEVNULL
    try:
        done = subprocess.run(list(command), cwd=REPO, env=env, stdout=out, stderr=err, check=False)
    finally:
        for handle in (out, err):
            if not isinstance(handle, int):
                handle.close()
    return done.returncode


def write_edit(home: Path, session_id: str, ops: Ops) -> None:
    """Write Theo's scripted edit to the one session. Anything but exit 0 is a broken run."""
    code = _run(
        [
            str(GATEWAY_PYTHON),
            "-I",
            str(THEO_EDIT),
            "--session",
            session_id,
            "--ops",
            json.dumps(ops),
        ],
        home,
    )
    if code != 0:
        raise BrokenRun(f"theo_edit.py exited {code} for session {session_id}")


def run_turn(home: Path, name: str, run: int, out: Path, resume: str | None) -> RunResult:
    """Run one headless turn. Raise BrokenRun on any fault that makes the run useless."""
    jsonl = out / f"{name}-{run}.jsonl"
    err = out / f"{name}-{run}.err"
    command = [
        "timeout",
        str(RUN_TIMEOUT),
        "hermes",
        "chat",
        "--query-file",
        str(OK_QUERY),
        "--oneshot",
        "-Q",
        "--format",
        "stream-json",
    ]
    if resume:
        command += ["--resume", resume]
    code = _run(command, home, jsonl, err)
    if code != 0:
        raise BrokenRun(f"hermes exited {code} on {name} run {run}")
    if HOOK_FAULT in err.read_text(encoding="utf-8", errors="replace"):
        raise BrokenRun(f"{HOOK_FAULT} on {name} run {run}")
    result = parse_result(jsonl.read_text(encoding="utf-8", errors="replace").splitlines())
    if result is None:
        raise BrokenRun(f"no result event on {name} run {run}")
    return result


def run_arms(
    arms: Sequence[tuple[str, Path]], runs: int, out: Path
) -> tuple[dict[str, str], dict[str, list[int]]]:
    """Run the arms interleaved. Return the session id and the input tokens of every arm."""
    sessions: dict[str, str] = {}
    tokens: dict[str, list[int]] = {name: [] for name, _ in arms}
    for run in range(1, runs + 1):
        for name, home in arms:
            ops = edit_ops(run) if name == "edits" else None
            if ops is not None:
                write_edit(home, sessions[name], ops)
            result = run_turn(home, name, run, out, sessions.get(name))
            sessions.setdefault(name, result.session_id)
            tokens[name].append(result.input_tokens)
    return sessions, tokens


def cmd_result(args: argparse.Namespace) -> int:
    result = parse_result(Path(args.file).read_text(encoding="utf-8").splitlines())
    if result is None:
        print("no result event", file=sys.stderr)
        return 2
    print(json.dumps(asdict(result)))
    return 0


def cmd_rows(args: argparse.Namespace) -> int:
    state_db = Path(args.state_db) if args.state_db else DEFAULT_HOME / "state.db"
    data_db = Path(args.data_db) if args.data_db else DEFAULT_HOME / DATA_RELATIVE
    try:
        report = session_report(state_db, data_db, args.session, _read_reminder(args.reminder_file))
    except sqlite3.Error as exc:
        print(f"read error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report))
    return 0


def _arms_body(
    args: argparse.Namespace, out: Path, plugin_home: Path, bare_home: Path
) -> tuple[int, dict[str, object] | None]:
    """Run and judge the arms. Return (exit code, report). A broken run gives (2, None)."""
    reminder = _read_reminder(args.reminder_file)
    arms = [("edits", plugin_home), ("quiet", plugin_home), ("bare", bare_home)]
    try:
        sessions, tokens = run_arms(arms, args.runs, out)
        built = {
            name: build_runs(read_rows(path / "state.db", sessions[name]), tokens[name], reminder)
            for name, path in arms
        }
        prompts = {
            name: read_system_prompt_chars(path / "state.db", sessions[name]) for name, path in arms
        }
    except (BrokenRun, sqlite3.Error) as exc:
        print(f"broken run: {exc}", file=sys.stderr)
        return 2, None
    report = compare(built["edits"], built["quiet"], built["bare"], EDIT_RUNS, len(reminder))
    report["system_prompt_chars_plugin"] = prompts["quiet"]
    report["system_prompt_chars_bare"] = prompts["bare"]
    report["sessions"] = sessions
    report["runs"] = {
        name: [
            {"run": item.run, "input_tokens": item.input_tokens, "note": item.note}
            for item in built[name]
        ]
        for name in built
    }
    return (0 if report["pass"] is True else 1), report


def cmd_arms(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    plugin_home = Path(args.plugin_home).expanduser().resolve()
    bare_home = Path(args.bare_home).expanduser().resolve()
    try:
        code, report = _arms_body(args, out, plugin_home, bare_home)
    finally:
        gateways = {
            "plugin": stop_test_gateway(plugin_home),
            "bare": stop_test_gateway(bare_home),
        }
    if report is None:
        print(json.dumps({"test_gateways": gateways}), file=sys.stderr)
        return code
    report["test_gateways"] = gateways
    text = json.dumps(report)
    (out / "arms-report.json").write_text(text, encoding="utf-8")
    print(text)
    return code


def _gateway_pid(home: Path) -> int:
    record = json.loads((home / "gateway.pid").read_text(encoding="utf-8"))
    pid = record.get("pid") if isinstance(record, dict) else None
    if not isinstance(pid, int) or isinstance(pid, bool):
        raise ValueError("gateway.pid has no pid")
    return pid


def cmd_ports(args: argparse.Namespace) -> int:
    homes = [Path(item).expanduser() for item in args.home]
    try:
        pids = {str(home): _gateway_pid(home) for home in homes}
        real_pid = _gateway_pid(Path(args.real_home).expanduser())
    except (OSError, ValueError) as exc:
        print(f"gateway.pid error: {exc}", file=sys.stderr)
        return 2
    done = subprocess.run(
        ["timeout", "10", "ss", "-ltnp"], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        print(f"ss exited {done.returncode}", file=sys.stderr)
        return 2
    real = parse_ss(done.stdout, real_pid)
    tests = {name: parse_ss(done.stdout, pid) for name, pid in pids.items()}
    clash = [line for name in tests for line in port_clash(tests[name], real)]
    print(
        json.dumps({
            "homes": {name: sorted(found) for name, found in tests.items()},
            "real": sorted(real),
            "clash": clash,
        })
    )
    return 1 if clash else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    sub = parser.add_subparsers(dest="command", required=True)
    result = sub.add_parser("result", help="read the last result event of a run")
    result.add_argument("file")
    rows = sub.add_parser("rows", help="read the notes of one session")
    rows.add_argument("--session", required=True)
    rows.add_argument("--state-db", default=None)
    rows.add_argument("--data-db", default=None)
    rows.add_argument("--reminder-file", default=None)
    arms = sub.add_parser("arms", help="run and judge the token arms")
    arms.add_argument("--out", required=True)
    arms.add_argument("--plugin-home", required=True)
    arms.add_argument("--bare-home", required=True)
    arms.add_argument("--runs", type=int, default=30)
    arms.add_argument("--reminder-file", default=None)
    ports = sub.add_parser("ports", help="compare the ports of the test and real gateways")
    ports.add_argument("--home", action="append", required=True)
    ports.add_argument("--real-home", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    handlers = {"result": cmd_result, "rows": cmd_rows, "arms": cmd_arms, "ports": cmd_ports}
    try:
        return handlers[args.command](args)
    except OSError as exc:
        print(f"read error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
