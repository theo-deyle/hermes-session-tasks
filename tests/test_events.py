"""`board.updated` goes out after every changed write, from the tool and from the route.

A recording fake stands in for `hermes_cli.plugin_events`. The code under test uses the
default wiring and no injected publisher. One test runs the real Hermes name function in
the gateway venv (marker hermes).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from api_client import (
    PREFIX,
    install_fake_hermes,
    load_plugin_api,
    make_client,
    unload_plugin_api,
)
from conftest import HERMES_AGENT_REPO
from fakes import FakeCtx, FakeReaderFactory
from session_tasks.db import ConnFactory
from session_tasks.lineage import SessionResolver
from session_tasks.wiring import register

GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"
SNIPPET = """
import sys

sys.dont_write_bytecode = True
plugin_dir, checkout_dir = sys.argv[1:3]
sys.path.insert(0, checkout_dir)
sys.path.insert(0, plugin_dir)
from hermes_cli.plugin_events import plugin_event_name
from session_tasks import events

print(plugin_event_name(events.PLUGIN_ID, events.EVENT))
events.publish("a", "a", 1, "user")
print("no raise")
"""
PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugin"
WIRE_NAME = "plugin.hermes-session-tasks.board.updated"

BroadcastCall = tuple[str, str, dict[str, Any]]


@pytest.fixture(autouse=True)
def clean_core() -> Iterator[None]:
    unload_plugin_api()
    yield
    unload_plugin_api()


@pytest.fixture
def broadcasts(monkeypatch: pytest.MonkeyPatch) -> list[BroadcastCall]:
    """Install a fake `hermes_cli.plugin_events` that records each broadcast call."""
    calls: list[BroadcastCall] = []

    def broadcast_plugin_event(plugin_id: str, event: str, payload: dict[str, Any]) -> None:
        calls.append((plugin_id, event, payload))

    parent = ModuleType("hermes_cli")
    child = ModuleType("hermes_cli.plugin_events")
    child.broadcast_plugin_event = broadcast_plugin_event  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", parent)
    monkeypatch.setitem(sys.modules, "hermes_cli.plugin_events", child)
    return calls


def tool_edit(connect: ConnFactory, args: dict[str, Any], session_id: str | None) -> Any:
    """Call the registered `board_edit` handler through the default wiring."""
    ctx = FakeCtx()
    register(ctx, connect=connect, open_reader=FakeReaderFactory({}))
    return json.loads(ctx.tools["board_edit"]["handler"](args, session_id=session_id))


def add_args(text: str = "a") -> dict[str, Any]:
    return {"ops": [{"op": "add", "text": text}]}


def test_tool_write_reaches_the_broadcast(
    connect: ConnFactory, broadcasts: list[BroadcastCall]
) -> None:
    result = tool_edit(connect, add_args(), "s1")

    assert result["ok"] is True
    assert broadcasts == [
        (
            "hermes-session-tasks",
            "board.updated",
            {"session_id": "s1", "root_id": "s1", "rev": 1, "actor": "agent"},
        )
    ]


def test_route_write_reaches_the_broadcast(
    monkeypatch: pytest.MonkeyPatch, db_path: Path, broadcasts: list[BroadcastCall]
) -> None:
    install_fake_hermes(monkeypatch, db_path)
    client = make_client(load_plugin_api())

    response = client.post(PREFIX + "/board/edit", json={"session_id": "s1", **add_args()})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert broadcasts == [
        (
            "hermes-session-tasks",
            "board.updated",
            {"session_id": "s1", "root_id": "s1", "rev": 1, "actor": "user"},
        )
    ]


def test_an_alias_session_publishes_its_own_id_and_the_root(
    connect: ConnFactory, broadcasts: list[BroadcastCall]
) -> None:
    tool_edit(connect, add_args("seed"), "s1")
    SessionResolver(connect, FakeReaderFactory({})).record_compaction("s3", "s1")
    broadcasts.clear()

    result = tool_edit(connect, add_args("more"), "s3")

    assert result["ok"] is True
    assert broadcasts == [
        (
            "hermes-session-tasks",
            "board.updated",
            {"session_id": "s3", "root_id": "s1", "rev": 2, "actor": "agent"},
        )
    ]


@pytest.mark.hermes
def test_hermes_event_name_matches_the_wire_name(tmp_path: Path, hermes_home: Path) -> None:
    if not GATEWAY_PYTHON.exists():
        pytest.skip(f"gateway venv python not found at {GATEWAY_PYTHON}")
    work = tmp_path / "work"
    work.mkdir()
    env = {**os.environ, "HERMES_HOME": str(hermes_home)}

    done = subprocess.run(
        [str(GATEWAY_PYTHON), "-I", "-c", SNIPPET, str(PLUGIN_DIR), str(HERMES_AGENT_REPO)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=work,
        check=False,
    )

    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().splitlines() == [WIRE_NAME, "no raise"]
    assert not (hermes_home / "plugin-data").exists()
