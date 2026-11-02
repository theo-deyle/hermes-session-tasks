"""The live test tools of phase 6: seed a source board, read a board, list tool calls, stop a gateway.

usage:
  cross_live.py seed --session ID --title TEXT --ops JSON [--checkout DIR]
  cross_live.py board --data-db PATH --session ROOT
  cross_live.py calls FILE
  cross_live.py stop --home DIR

`seed` runs under the gateway venv Python, because it imports the Hermes session store and the
plugin. It creates the session row, sets its title and applies the ops through the same
`BoardApi.edit` the pane route uses, with a no-op publisher. seed never writes the real Hermes
home: it refuses an unset HERMES_HOME and the real `~/.hermes` before any Hermes import.
`board` uses the standard library only and opens the data file read only.
`calls` lists the tool uses of a stream-json run, with the rules of tests/live/own_job/analyze.py.
`stop` stops only a test gateway whose environment names the given home, through
`stop_test_gateway` of tests/live/delta/delta_live.py.

Every subcommand prints one JSON line on success.
Exit codes: 0 done, 1 the act did not apply, 2 usage, refusal or read error.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from urllib.parse import quote

sys.dont_write_bytecode = True
PLUGIN_DIR = Path(__file__).resolve().parents[3] / "plugin"
LIVE_DIR = Path(__file__).resolve().parents[1]
ANALYZE = LIVE_DIR / "own_job" / "analyze.py"
DELTA_LIVE = LIVE_DIR / "delta" / "delta_live.py"
DEFAULT_CHECKOUT = Path.home() / ".hermes" / "hermes-agent"
SOURCE = "cli"
APPLIED = 0
NOT_APPLIED = 1
USAGE_ERROR = 2


def refuse_real_home(env: Mapping[str, str], home: Path) -> str | None:
    """Return the reason to refuse a write, or None when HERMES_HOME names a test home."""
    named = env.get("HERMES_HOME", "").strip()
    if not named:
        return "HERMES_HOME is unset or blank: seed needs a test home"
    if Path(named).expanduser().resolve() == home.resolve():
        return f"HERMES_HOME names the real Hermes home {home}: seed refuses it"
    return None


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return USAGE_ERROR


def _checkout(argument: str | None) -> Path:
    if argument:
        return Path(argument).expanduser()
    configured = os.environ.get("HERMES_AGENT_REPO")
    return Path(configured).expanduser() if configured else DEFAULT_CHECKOUT


def _parse_ops(text: str) -> list[object] | None:
    try:
        ops = json.loads(text)
    except ValueError:
        return None
    return ops if isinstance(ops, list) else None


def cmd_seed(args: argparse.Namespace) -> int:
    reason = refuse_real_home(os.environ, Path.home() / ".hermes")
    if reason is not None:
        return _fail(reason)
    ops = _parse_ops(args.ops)
    if ops is None:
        return _fail("--ops must be a JSON list")
    sys.path.insert(0, str(_checkout(args.checkout)))
    sys.path.insert(0, str(PLUGIN_DIR))
    from hermes_state import SessionDB  # pyright: ignore[reportMissingImports]
    from session_tasks import board_api  # pyright: ignore[reportMissingImports]

    db = SessionDB()
    try:
        db.create_session(args.session, SOURCE)
        db.set_session_title(args.session, args.title)
    finally:
        db.close()

    def _no_publish(root_id: str, session_id: str, rev: int, actor: str) -> None:
        return None

    api = board_api.build(publish=_no_publish)  # pyright: ignore[reportArgumentType]
    answer = api.edit(args.session, ops, 0)
    reply = answer.body
    ok = reply.get("ok") is True
    changed = reply.get("changed_ids")
    print(
        json.dumps({
            "session": args.session,
            "title": args.title,
            "ok": ok,
            "rev": reply.get("rev"),
            "changed_ids": changed if isinstance(changed, list) else [],
        })
    )
    return APPLIED if ok else NOT_APPLIED


def open_ro(path: Path) -> sqlite3.Connection:
    """Open a SQLite file read only: a URI with mode=ro. A missing file raises."""
    return sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)


def _board_rows(conn: sqlite3.Connection, root: str) -> dict[str, object] | None:
    board = conn.execute(
        "SELECT rev, agent_seen_rev FROM boards WHERE root_id = ?", (root,)
    ).fetchone()
    if board is None:
        return None
    items = conn.execute(
        "SELECT id, parent_id, text, checked, updated_by FROM items WHERE root_id = ? ORDER BY id",
        (root,),
    ).fetchall()
    copied = conn.execute(
        "SELECT rev, actor, item_id, text FROM changes WHERE root_id = ? AND op = 'copied'"
        " ORDER BY seq",
        (root,),
    ).fetchall()
    return {
        "rev": int(board[0]),
        "agent_seen_rev": int(board[1]),
        "items": [
            {"id": r[0], "parent_id": r[1], "text": r[2], "checked": bool(r[3]), "updated_by": r[4]}
            for r in items
        ],
        "copied": [{"rev": r[0], "actor": r[1], "item_id": r[2], "text": r[3]} for r in copied],
    }


def read_board(data_db: Path, root: str) -> dict[str, object] | None:
    """Return rev, agent_seen_rev, items and copied rows of one board, or None when absent.

    The session id is mapped to its root through the aliases table. The file opens read only.
    """
    try:
        conn = open_ro(data_db)
    except sqlite3.Error:
        return None
    try:
        alias = conn.execute("SELECT root_id FROM aliases WHERE session_id = ?", (root,)).fetchone()
        return _board_rows(conn, alias[0] if alias else root)
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def cmd_board(args: argparse.Namespace) -> int:
    data_db = Path(args.data_db).expanduser()
    if not data_db.is_file():
        return _fail(f"no data file at {data_db}")
    board = read_board(data_db, args.session)
    if board is None:
        return _fail(f"no board for session {args.session}")
    print(json.dumps(board))
    return APPLIED


def _load(name: str, path: Path) -> ModuleType:
    """Load a sibling live script by its file path. The module is registered for dataclasses."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def tool_calls(path: Path) -> list[dict[str, object]]:
    """Return {name, args} for every tool use of a stream-json run, in order."""
    analyze = _load("cross_live_analyze", ANALYZE)
    return [
        {"name": analyze.effective_name(event), "args": analyze.tool_arguments(event)}
        for event in analyze.load_events(path)
        if event.get("type") == "tool_use"
    ]


def cmd_calls(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser()
    try:
        calls = tool_calls(path)
    except OSError as exc:
        return _fail(f"cannot read {path}: {exc}")
    print(json.dumps(calls))
    return APPLIED


def cmd_stop(args: argparse.Namespace) -> int:
    delta = _load("cross_live_delta", DELTA_LIVE)
    home = Path(args.home).expanduser()
    result = delta.stop_test_gateway(home)
    print(json.dumps({"home": str(home), "result": result}))
    return NOT_APPLIED if result == "refused" else APPLIED


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Live test tools for the cross-session check.")
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed", help="create a titled session and its board in a test home")
    seed.add_argument("--session", required=True)
    seed.add_argument("--title", required=True)
    seed.add_argument("--ops", required=True, help="a JSON list of board ops")
    seed.add_argument("--checkout", default=None, help="the Hermes checkout")
    board = sub.add_parser("board", help="print one board read only")
    board.add_argument("--data-db", required=True)
    board.add_argument("--session", required=True)
    calls = sub.add_parser("calls", help="list the tool uses of a stream-json run")
    calls.add_argument("file")
    stop = sub.add_parser("stop", help="stop the gateway of one test home")
    stop.add_argument("--home", required=True)
    return parser


COMMANDS = {"seed": cmd_seed, "board": cmd_board, "calls": cmd_calls, "stop": cmd_stop}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
