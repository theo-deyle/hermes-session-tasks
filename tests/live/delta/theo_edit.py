"""The live stand-in for Theo's pane write.

It runs under the gateway venv Python, because the plugin reads Hermes storage and the session
reader. It writes only the one session it is given, through the same `BoardApi.edit` the pane
route uses, and it uses the active HERMES_HOME. The publisher is a no-op: the real one imports
the gateway server stack, and a scripted edit needs no Desktop push.

usage: theo_edit.py --session ID --ops JSON [--checkout DIR]
Prints one JSON line. Exit 0 when the edit applied, 1 when it did not, 2 on a usage or read error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PLUGIN_DIR = Path(__file__).resolve().parents[3] / "plugin"
DEFAULT_CHECKOUT = Path.home() / ".hermes" / "hermes-agent"
USAGE_ERROR = 2


def _checkout(argument: str | None) -> Path:
    if argument:
        return Path(argument).expanduser()
    configured = os.environ.get("HERMES_AGENT_REPO")
    return Path(configured).expanduser() if configured else DEFAULT_CHECKOUT


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write one edit as Theo to one session board.")
    parser.add_argument("--session", required=True)
    parser.add_argument("--ops", required=True, help="a JSON list of board ops")
    parser.add_argument("--checkout", default=None, help="the Hermes checkout")
    return parser.parse_args(argv)


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return USAGE_ERROR


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    try:
        ops = json.loads(args.ops)
    except ValueError:
        return _fail("--ops is not valid JSON")
    if not isinstance(ops, list):
        return _fail("--ops must be a JSON list")
    sys.path.insert(0, str(_checkout(args.checkout)))
    sys.path.insert(0, str(PLUGIN_DIR))
    from session_tasks import board_api  # noqa: E402  # pyright: ignore[reportMissingImports]

    def _no_publish(root_id: str, session_id: str, rev: int, actor: str) -> None:
        return None

    api = board_api.build(publish=_no_publish)  # pyright: ignore[reportArgumentType]
    current = api.read(args.session)
    rev = current.body.get("rev")
    if not current.body.get("ok") or not isinstance(rev, int):
        return _fail("could not read the board rev")
    answer = api.edit(args.session, ops, rev)
    reply = answer.body
    ok = reply.get("ok") is True
    changed = reply.get("changed_ids")
    print(
        json.dumps({
            "status": answer.status,
            "ok": ok,
            "rev": reply.get("rev"),
            "summary": reply.get("summary"),
            "changed_ids": changed if isinstance(changed, list) else [],
        })
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
