"""Script run by the gateway venv Python against a temporary HERMES_HOME. It prints one JSON object.

Arguments: plugin dir, Hermes checkout dir, fixture JSON path. The fixture JSON maps a
session id to `parent`, `end_reason`, `model_config` and `source`. This script is not a
pytest module: the gateway venv has no pytest. It never touches the real Hermes home,
because the caller sets HERMES_HOME to a temporary directory.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
PLUGIN_DIR, CHECKOUT_DIR, FIXTURE_PATH = sys.argv[1:4]
sys.path.insert(0, CHECKOUT_DIR)
sys.path.insert(0, PLUGIN_DIR)

from hermes_constants import get_hermes_home  # pyright: ignore[reportMissingImports]  # noqa: E402
from hermes_state import SessionDB  # pyright: ignore[reportMissingImports]  # noqa: E402
from session_tasks import paths, session_reader  # noqa: E402
from session_tasks.lineage import SessionResolver  # noqa: E402
from session_tasks.model import AddItem  # noqa: E402
from session_tasks.store import BoardStore  # noqa: E402

MISSING = "missing"


def state_db_digest(home: Path) -> str:
    """Hash state.db and its WAL frames, so a write by the plugin shows as a changed digest.

    A read only open makes SQLite create an empty `state.db-wal` file. An empty WAL file
    holds no data, so it counts as absent. Only a WAL with content can mean a write.
    """
    digest = hashlib.sha256()
    for name in ("state.db", "state.db-wal"):
        data = (home / name).read_bytes() if (home / name).exists() else b""
        if data:
            digest.update(name.encode())
            digest.update(data)
    return digest.hexdigest()


def create_sessions(fixture: dict[str, dict[str, Any]]) -> None:
    db = SessionDB()
    try:
        for session_id, spec in fixture.items():
            db.create_session(
                session_id,
                spec["source"],
                model_config=spec["model_config"],
                parent_session_id=spec["parent"],
            )
            if spec["end_reason"]:
                db.end_session(session_id, spec["end_reason"])
    finally:
        db.close()


def read_real(ids: list[str]) -> tuple[dict[str, Any], dict[str, bool], dict[str, list[str]]]:
    reader = session_reader.open_session_reader()
    try:
        sessions = {sid: reader.get_session(sid) for sid in ids}
        fork = {sid: reader.is_explicit_fork_child(sid) for sid in ids}
        lineage = {sid: reader.get_compression_lineage(sid) for sid in ids}
    finally:
        reader.close()
    return sessions, fork, lineage


def main() -> None:
    fixture = json.loads(Path(FIXTURE_PATH).read_text(encoding="utf-8"))
    ids = [*fixture, MISSING]
    home = get_hermes_home()
    create_sessions(fixture)
    store = BoardStore(paths.connect)
    store.apply("root", [AddItem("Call John")], actor="agent", base_rev=0)
    before = state_db_digest(home)
    resolver = SessionResolver(paths.connect, session_reader.open_session_reader)
    resolutions = {}
    for session_id in ids:
        found = resolver.resolve(session_id)
        resolutions[session_id] = [found.root_id, found.kind, found.forked_from]
    sessions, fork, lineage = read_real(ids)
    after = state_db_digest(home)
    conn = paths.connect()
    try:
        plugin_db_path = conn.execute("PRAGMA database_list").fetchone()[2]
    finally:
        conn.close()
    result = {
        "sessions": sessions,
        "fork": fork,
        "lineage": lineage,
        "resolutions": resolutions,
        "state_db_unchanged": before == after,
        "branch_texts": [item.text for item in store.get_board("br").items],
        "plugin_db_path": plugin_db_path,
    }
    print(json.dumps(result, default=str))


main()
