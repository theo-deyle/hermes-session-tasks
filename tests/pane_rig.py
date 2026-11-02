"""The shared rig for the pane tests: a store, the real router, a loopback relay and the harness."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from api_client import PREFIX, load_plugin_api, make_client
from rest_relay import RestRelay
from session_tasks.board_api import BoardApi
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

if TYPE_CHECKING:
    from conftest import ResolverFor

ROOT = Path(__file__).resolve().parent.parent
EVENT_TYPE = "plugin.hermes-session-tasks.board.updated"
PLUGIN_JS = ROOT / "plugin" / "desktop" / "plugin.js"
HARNESS = Path(__file__).with_name("desktop_pane_harness.mjs")


def run_harness(config: dict[str, Any], tmp_path: Path, plugin: Path = PLUGIN_JS) -> dict[str, Any]:
    """Run the harness on `plugin` with `config` and return its one JSON line."""
    config_path = tmp_path / "harness-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    completed = subprocess.run(
        [
            "node",
            "--experimental-vm-modules",
            str(HARNESS),
            str(plugin),
            str(config_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout.strip().splitlines()[-1])


class Rig:
    """A store, a resolver and the real router behind one loopback relay."""

    def __init__(self, store: BoardStore, resolver_for: ResolverFor) -> None:
        self.store = store
        resolver, _ = resolver_for({})
        self.client = make_client(load_plugin_api(), BoardApi(store, resolver))

    def run(self, tmp_path: Path, plugin: Path = PLUGIN_JS, **config: Any) -> dict[str, Any]:
        with RestRelay(self.client) as relay:
            config.setdefault("focused", "s1")
            config.setdefault("steps", [])
            return run_harness({"baseUrl": relay.base_url + PREFIX, **config}, tmp_path, plugin)


def seed_call_john(store: BoardStore) -> None:
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)


def posts(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The POST entries of the harness `restCalls`."""
    return [c for c in result["restCalls"] if c["method"] == "POST"]


def board_gets(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        c for c in result["restCalls"] if c["method"] == "GET" and c["path"].startswith("/board")
    ]


def checkbox(result: dict[str, Any], row: str) -> dict[str, Any]:
    """The one checkbox record in the row `row`."""
    found = [box for box in result["checkboxes"] if box["row"] == row]
    assert len(found) == 1, f"{len(found)} checkboxes in row {row}"
    return found[0]
