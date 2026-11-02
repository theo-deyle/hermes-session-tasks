"""The shared rig for the pane tests: a store, the real router, a loopback relay and the harness."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from api_client import PREFIX, load_plugin_api, make_client
from rest_relay import RestRelay
from session_tasks.board_api import BoardApi
from session_tasks.board_json import board_dict
from session_tasks.model import AddItem, Board, Stale
from session_tasks.results import stale_text
from session_tasks.store import BoardStore

if TYPE_CHECKING:
    from conftest import ResolverFor

ROOT = Path(__file__).resolve().parent.parent
EVENT_TYPE = "plugin.hermes-session-tasks.board.updated"
PLUGIN_JS = ROOT / "plugin" / "desktop" / "plugin.js"
PROBE_JS = ROOT / "tests" / "fixtures" / "harness_probe.js"
HARNESS = Path(__file__).with_name("desktop_pane_harness.mjs")


def _run_node(
    config: dict[str, Any], tmp_path: Path, plugin: Path
) -> subprocess.CompletedProcess[str]:
    config_path = tmp_path / "harness-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return subprocess.run(
        [
            "node",
            "--experimental-vm-modules",
            str(HARNESS),
            str(plugin),
            str(config_path),
        ],
        cwd=ROOT,
        # UTC, so the time labels read the same on every machine.
        env={**os.environ, "TZ": "UTC"},
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def run_harness(config: dict[str, Any], tmp_path: Path, plugin: Path = PLUGIN_JS) -> dict[str, Any]:
    """Run the harness on `plugin` with `config` and return its one JSON line."""
    completed = _run_node(config, tmp_path, plugin)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout.strip().splitlines()[-1])


def harness_error(config: dict[str, Any], tmp_path: Path, plugin: Path = PLUGIN_JS) -> str:
    """Run the harness, assert that it fails, and return its stderr."""
    completed = _run_node(config, tmp_path, plugin)
    assert completed.returncode != 0, "the harness run was expected to fail"
    return completed.stderr


class Rig:
    """A store, a resolver and the real router behind one loopback relay."""

    def __init__(self, store: BoardStore, resolver_for: ResolverFor) -> None:
        self.store = store
        resolver, _ = resolver_for({})
        self.client = make_client(load_plugin_api(), BoardApi(store, resolver))

    def _config(self, relay: RestRelay, config: dict[str, Any]) -> dict[str, Any]:
        return {"baseUrl": relay.base_url + PREFIX, "focused": "s1", "steps": [], **config}

    def run(self, tmp_path: Path, plugin: Path = PLUGIN_JS, **config: Any) -> dict[str, Any]:
        with RestRelay(self.client) as relay:
            return run_harness(self._config(relay, config), tmp_path, plugin)

    def error(self, tmp_path: Path, plugin: Path = PLUGIN_JS, **config: Any) -> str:
        """Run a harness call that must fail and return its stderr."""
        with RestRelay(self.client) as relay:
            return harness_error(self._config(relay, config), tmp_path, plugin)


def seed_call_john(store: BoardStore) -> None:
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)


def posts(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The POST entries of the harness `restCalls`."""
    return [c for c in result["restCalls"] if c["method"] == "POST"]


def board_gets(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The GET calls of one board. `/boards` and `/board/copy` also start with `/board`, so they do not count."""
    return [
        c for c in result["restCalls"] if c["method"] == "GET" and c["path"].startswith("/board?")
    ]


def checkbox(result: dict[str, Any], row: str) -> dict[str, Any]:
    """The one checkbox record in the row `row`."""
    found = [box for box in result["checkboxes"] if box["row"] == row]
    assert len(found) == 1, f"{len(found)} checkboxes in row {row}"
    return found[0]


def inputs(
    result: dict[str, Any], placeholder: str | None = None, row: str | None = None
) -> list[dict[str, Any]]:
    """The Input records that match the placeholder and the row (a None filter matches all)."""
    return [
        entry
        for entry in result["inputs"]
        if (placeholder is None or entry["placeholder"] == placeholder)
        and (row is None or entry["row"] == row)
    ]


def the_input(
    result: dict[str, Any], placeholder: str | None = None, row: str | None = None
) -> dict[str, Any]:
    """The one Input record that matches the placeholder and the row."""
    found = inputs(result, placeholder, row)
    assert len(found) == 1, f"{len(found)} inputs match placeholder={placeholder} row={row}"
    return found[0]


def button(result: dict[str, Any], label: str, row: str | None = None) -> dict[str, Any]:
    """The one Button record with the label (and the row, when given)."""
    found = [
        entry
        for entry in result["buttons"]
        if entry["label"] == label and (row is None or entry["row"] == row)
    ]
    assert len(found) == 1, f"{len(found)} buttons labelled {label!r} in row {row}"
    return found[0]


def stale_body(board: Board, root_id: str) -> dict[str, Any]:
    """A stale reply body in the D-22 shape, built the way the router builds it."""
    stale = Stale(board, "stale", 0, None)
    return {
        "ok": False,
        "error": "stale",
        "reason": stale.reason,
        "op_index": stale.op_index,
        "item_id": stale.item_id,
        "message": stale_text(stale, max(board.rev - 1, 0)),
        "root_id": root_id,
        "rev": board.rev,
        "board": board_dict(board),
    }
