"""The test pane, run in a node VM and wired to the real router through a loopback relay."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_client import PREFIX, load_plugin_api, make_client, unload_plugin_api
from conftest import ResolverFor
from rest_relay import RestRelay
from session_tasks.board_api import BoardApi
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JS = ROOT / "plugin" / "desktop" / "plugin.js"
HARNESS = Path(__file__).with_name("desktop_pane_harness.mjs")

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


@pytest.fixture(autouse=True)
def clean_core() -> Iterator[None]:
    unload_plugin_api()
    yield
    unload_plugin_api()


def run_harness(config: dict[str, Any], tmp_path: Path) -> dict[str, Any]:
    """Run the harness on plugin.js with `config` and return its one JSON line."""
    config_path = tmp_path / "harness-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    completed = subprocess.run(
        [
            "node",
            "--experimental-vm-modules",
            str(HARNESS),
            str(PLUGIN_JS),
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

    def run(self, tmp_path: Path, **config: Any) -> dict[str, Any]:
        with RestRelay(self.client) as relay:
            config.setdefault("focused", "s1")
            config.setdefault("steps", [])
            return run_harness({"baseUrl": relay.base_url + PREFIX, **config}, tmp_path)


@pytest.fixture
def rig(store: BoardStore, resolver_for: ResolverFor) -> Rig:
    return Rig(store, resolver_for)


def seed_call_john(store: BoardStore) -> None:
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)


def test_pane_shows_the_board_from_the_real_routes(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path)

    lines = result["lines"]
    assert "backend 0.1.0, api 1" in lines
    assert "pane 0.1.0, api 1" in lines
    assert "session s1, board rev 1" in lines
    assert "[ ] #1 Call John" in lines
    assert not [line for line in lines if line.startswith("Version mismatch")]
    calls = [(c["method"], c["path"]) for c in result["restCalls"]]
    assert ("GET", "/meta") in calls
    assert ("GET", "/board?session_id=s1") in calls
    contribution = result["contribution"]
    assert contribution["id"] == "pane"
    assert contribution["area"] == "panes"
    assert contribution["data"]["placement"] == "right"
    assert contribution["data"]["width"] == "320px"


def test_pane_with_no_focused_session_makes_no_board_call(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, focused=None)

    assert "no session focused" in result["lines"]
    assert "board is empty" in result["lines"]
    assert not [c for c in result["restCalls"] if c["path"].startswith("/board")]
