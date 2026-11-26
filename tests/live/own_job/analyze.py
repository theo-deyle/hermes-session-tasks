"""Measure one headless own-job run: did the agent plan on the board and check it off?

Usage: analyze.py [--out DIR] [--db FILE] <name>

Reads `<out>/<name>.jsonl` (the `hermes chat --format stream-json` output) and the board
of the run's session in the data file. The data file opens read only, so a run never
changes the real boards here.

Pass rule (Phase 3, success criterion 0):
1. One `board_edit` call carries 2 or more `add` ops.
2. A later `board_edit` call carries a `set_checked` op with checked true.
3. The final board holds 2 or more items and every item is checked.

Exit code: 0 on pass, 1 on a measured fail, 2 on a read error.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

BOARD_EDIT = "board_edit"
TODO_LIST = "todo_list"
BRIDGE = "tool_call"
MIN_ADDS = 2
MIN_ITEMS = 2
DEFAULT_DB = Path.home() / ".hermes" / "plugin-data" / "hermes-session-tasks" / "data.db"

Event = dict[str, Any]
Board = dict[str, Any]


def load_events(path: Path) -> list[Event]:
    """Read a JSONL file. A line that is not a JSON object is skipped."""
    events: list[Event] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _input(event: Event) -> dict[str, Any]:
    value = event.get("input")
    return value if isinstance(value, dict) else {}


def effective_name(event: Event) -> object:
    """Return the tool name. A `tool_call` bridge use names the real tool inside its input."""
    name = event.get("name")
    if name != BRIDGE:
        return name
    inner = _input(event)
    return inner.get("name") or inner.get("tool") or inner.get("tool_name") or f"{BRIDGE}?"


def tool_arguments(event: Event) -> dict[str, Any]:
    """Return the arguments of a tool use. Bridged arguments may be a JSON string."""
    inner = _input(event)
    args: object = inner.get("arguments", inner) if event.get("name") == BRIDGE else inner
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return {}
    return args if isinstance(args, dict) else {}


def _ops(event: Event) -> list[dict[str, Any]]:
    ops = tool_arguments(event).get("ops")
    if isinstance(ops, str):
        try:
            ops = json.loads(ops)
        except ValueError:
            return []
    return [op for op in ops if isinstance(op, dict)] if isinstance(ops, list) else []


def _edit_calls(events: list[Event]) -> list[list[dict[str, Any]]]:
    return [
        _ops(event)
        for event in events
        if event.get("type") == "tool_use" and effective_name(event) == BOARD_EDIT
    ]


def _count_calls(events: list[Event], tool: str) -> int:
    return sum(
        1 for event in events if event.get("type") == "tool_use" and effective_name(event) == tool
    )


def _first_add_batch(calls: list[list[dict[str, Any]]]) -> int | None:
    for index, ops in enumerate(calls):
        if sum(1 for op in ops if op.get("op") == "add") >= MIN_ADDS:
            return index
    return None


def _checks_after(calls: list[list[dict[str, Any]]], start: int) -> bool:
    return any(
        op.get("op") == "set_checked" and op.get("checked") is True
        for ops in calls[start + 1 :]
        for op in ops
    )


def _board_items(board: Board | None) -> list[dict[str, Any]]:
    items = board.get("items") if board else None
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def evaluate(events: list[Event], board: Board | None) -> dict[str, Any]:
    """Apply the three-part pass rule. Each unmet part adds one plain reason."""
    calls = _edit_calls(events)
    batch = _first_add_batch(calls)
    items = _board_items(board)
    unchecked = [item for item in items if not item.get("checked")]
    checks = {
        "add_batch": batch is not None,
        "check_after_add": batch is not None and _checks_after(calls, batch),
        "all_checked": len(items) >= MIN_ITEMS and not unchecked,
    }
    reasons: list[str] = []
    if not checks["add_batch"]:
        reasons.append(f"no board_edit call with {MIN_ADDS} or more add ops")
    if not checks["check_after_add"]:
        reasons.append("no later board_edit call with a set_checked op with checked true")
    if board is None:
        reasons.append("the board could not be read")
    elif len(items) < MIN_ITEMS:
        reasons.append(f"the final board must hold {MIN_ITEMS} or more items")
    elif unchecked:
        reasons.append(f"the final board has {len(unchecked)} unchecked items")
    return {
        "board_edit_calls": len(calls),
        "todo_list_calls": _count_calls(events, TODO_LIST),
        "add_batches": sum(
            1 for ops in calls if sum(1 for op in ops if op.get("op") == "add") >= MIN_ADDS
        ),
        "checks": checks,
        "pass": all(checks.values()),
        "reasons": reasons,
    }


def read_board(db_path: Path, session_id: str) -> Board | None:
    """Read the board of a session, read only. None when the data file is absent."""
    if not db_path.exists():
        return None
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT root_id FROM aliases WHERE session_id=?", (session_id,)
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT root_id FROM boards WHERE root_id=?", (session_id,)
            ).fetchone()
        if row is None:
            return {"root": None, "rev": None, "items": []}
        root = row[0]
        rev = conn.execute("SELECT rev FROM boards WHERE root_id=?", (root,)).fetchone()
        rows = conn.execute(
            "SELECT id, text, checked, updated_by FROM items WHERE root_id=? ORDER BY position, id",
            (root,),
        ).fetchall()
    finally:
        conn.close()
    items = [
        {"id": item_id, "text": text, "checked": checked, "updated_by": updated_by}
        for item_id, text, checked, updated_by in rows
    ]
    return {"root": root, "rev": rev[0] if rev else None, "items": items}


def _result(events: list[Event]) -> Event:
    results = [event for event in events if event.get("type") == "result"]
    return results[-1] if results else {}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Measure one headless own-job run.")
    parser.add_argument("name", help="run name: the file <out>/<name>.jsonl")
    parser.add_argument("--out", type=Path, default=Path.cwd(), help="folder with the run output")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="plugin data file")
    args = parser.parse_args(argv)
    try:
        events = load_events(args.out / f"{args.name}.jsonl")
        final = _result(events)
        session_id = final.get("session_id")
        board = read_board(args.db, session_id) if isinstance(session_id, str) else None
    except (OSError, sqlite3.Error) as exc:
        print(f"analyze: cannot read the run: {exc}", file=sys.stderr)
        return 2
    verdict = evaluate(events, board)
    report = {
        "run": args.name,
        "session_id": session_id,
        "exit_code": final.get("exit_code"),
        **verdict,
        "board": board,
    }
    print(json.dumps(report, default=str))
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
