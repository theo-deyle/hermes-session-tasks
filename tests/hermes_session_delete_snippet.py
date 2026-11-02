"""Script run by the gateway venv Python against a temporary HERMES_HOME. It prints one JSON line.

Arguments: plugin dir, Hermes checkout dir. The script loads the plugin through Hermes's own
discovery, then deletes and archives sessions through a real `SessionDB`. A recorder sits next
to the plugin callback and keeps every `on_session_delete` payload. The script prints the root
ids whose board still exists and the recorded payloads. This script is not a pytest module: the
gateway venv has no pytest. It never touches the real Hermes home, because the caller sets
HERMES_HOME to a temporary directory.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PLUGIN_DIR, CHECKOUT_DIR = sys.argv[1:3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hermes_snippet_setup import link_and_enable, stub_gateway_server  # noqa: E402

# Link and enable, and stub the gateway module, before any Hermes import.
HOME = Path(os.environ["HERMES_HOME"])
link_and_enable(HOME, Path(PLUGIN_DIR))
sys.path.insert(0, CHECKOUT_DIR)
sys.path.insert(0, PLUGIN_DIR)
stub_gateway_server(lambda name, payload: None)

import hermes_cli.plugins as hermes_plugins  # noqa: E402  # pyright: ignore[reportMissingImports]
from hermes_state import SessionDB  # noqa: E402  # pyright: ignore[reportMissingImports]
from session_tasks import paths  # noqa: E402
from session_tasks.model import AddItem  # noqa: E402
from session_tasks.store import BoardStore  # noqa: E402

BOARDS = ("cli", "bulk1", "bulk2", "chain-root", "arch", "arch-root", "keep")
SESSIONS = (*BOARDS, "chain")


def chain_to(db: SessionDB, tip: str, root: str) -> None:
    """Make `tip` a compression tip of `root`, the way Hermes's own test does."""
    db.end_session(root, "compression")
    db._execute_write(
        lambda conn: conn.execute(
            "UPDATE sessions SET parent_session_id = ? WHERE id = ?", (root, tip)
        )
    )


def main() -> None:
    hermes_plugins.discover_plugins()
    events: list[dict[str, object]] = []

    def record(**kwargs: object) -> None:
        events.append({
            "session_id": kwargs.get("session_id"),
            "reason": kwargs.get("reason"),
            "deleted_ids": kwargs.get("deleted_ids"),
        })

    hermes_plugins.get_plugin_manager()._hooks.setdefault("on_session_delete", []).append(record)

    store = BoardStore(paths.connect)
    for root in BOARDS:
        store.apply(root, [AddItem("x")], actor="user", base_rev=0)

    db = SessionDB(db_path=HOME / "state.db")
    try:
        for session_id in SESSIONS:
            # No `append_message`: its first call in a new data root imports the agent loop,
            # which relaunches the process and runs this script a second time.
            db.create_session(session_id, source="cli")
        chain_to(db, "chain", "chain-root")
        chain_to(db, "arch", "arch-root")
        db.delete_session("cli")
        db.delete_sessions(["bulk1", "bulk2"])
        # The dashboard and Desktop delete paths pass `include_compression_chain=True`, because
        # their list rows carry chain tip ids. Without it Hermes deletes only the tip row.
        db.delete_session("chain", include_compression_chain=True)
        db.set_session_archived("arch", True)
    finally:
        db.close()

    boards_left = [summary.root_id for summary in store.list_boards()]
    print(json.dumps({"boards_left": boards_left, "events": events}))


main()
