"""`board.updated` goes out after every changed write, from the tool and from the route.

A recording fake stands in for `hermes_cli.plugin_events`. The code under test uses the
default wiring and no injected publisher. One test runs the real Hermes name function in
the gateway venv (marker hermes).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
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
from fakes import FakeCtx, FakeReaderFactory, SessionSpec
from session_tasks import board_api, events
from session_tasks.board_api import BoardApi
from session_tasks.board_tools import BoardTools
from session_tasks.db import ConnFactory
from session_tasks.lineage import SessionResolver
from session_tasks.model import AddItem, SetText
from session_tasks.store import BoardStore
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


DELEGATE_SPECS = {
    "s1": SessionSpec(),
    "dg": SessionSpec(parent="s1", model_config={"_delegate_from": "s1"}),
}

Writer = Callable[[dict[str, Any], str | None], Any]


def tool_writer(connect: ConnFactory) -> Writer:
    ctx = FakeCtx()
    register(ctx, connect=connect, open_reader=FakeReaderFactory(DELEGATE_SPECS))
    handler = ctx.tools["board_edit"]["handler"]

    def write(args: dict[str, Any], session_id: str | None) -> Any:
        return json.loads(handler(args, session_id=session_id))

    return write


def route_writer(connect: ConnFactory) -> Writer:
    api = board_api.build(connect, FakeReaderFactory(DELEGATE_SPECS))
    client = make_client(load_plugin_api(), api)

    def write(args: dict[str, Any], session_id: str | None) -> Any:
        response = client.post(PREFIX + "/board/edit", json={"session_id": session_id, **args})
        return response.json()

    return write


@pytest.fixture(params=["tool", "route"])
def writer(request: pytest.FixtureRequest, connect: ConnFactory) -> Writer:
    return tool_writer(connect) if request.param == "tool" else route_writer(connect)


def seed_two_revs(store: BoardStore) -> None:
    store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)
    store.apply("s1", [SetText(1, "b")], actor="user", base_rev=1)


@pytest.mark.parametrize(
    ("args", "session_id"),
    [
        ({"ops": []}, "s1"),
        ({"ops": [{"op": "set_checked", "item_id": 1, "checked": False}], "base_rev": 2}, "s1"),
        ({"ops": [{"op": "set_text", "item_id": 1, "text": "x"}], "base_rev": 1}, "s1"),
        ({"ops": [{"op": "add", "text": "  "}]}, "s1"),
        ({"ops": [{"op": "add", "text": "x"}]}, "   "),
        ({"ops": [{"op": "add", "text": "x"}]}, "dg"),
    ],
    ids=["no-ops", "no-change", "stale", "rule-error", "blank-session", "delegate"],
)
def test_no_event_without_a_change(
    writer: Writer,
    store: BoardStore,
    broadcasts: list[BroadcastCall],
    args: dict[str, Any],
    session_id: str,
) -> None:
    seed_two_revs(store)

    writer(args, session_id)

    assert broadcasts == []


def test_two_changed_writes_give_rising_revs(
    writer: Writer, broadcasts: list[BroadcastCall]
) -> None:
    writer(add_args("a"), "s1")
    writer(add_args("b"), "s1")

    assert [payload["rev"] for _, _, payload in broadcasts] == [1, 2]


@pytest.mark.parametrize("kind", ["tool", "route"])
def test_the_listener_sees_the_committed_rev(
    kind: str, store: BoardStore, resolver_for: Any
) -> None:
    seen: list[tuple[int, int]] = []

    def publisher(root_id: str, session_id: str, rev: int, actor: str) -> None:
        seen.append((rev, store.get_board(root_id).rev))

    after_write = events.listener("agent", publisher)
    resolver, _ = resolver_for({})
    for text in ("a", "b"):
        if kind == "tool":
            BoardTools(store, resolver, after_write=after_write).board_edit(
                add_args(text), session_id="s1"
            )
        else:
            BoardApi(store, resolver, after_write=after_write).edit(
                "s1", add_args(text)["ops"], None
            )

    assert seen == [(1, 1), (2, 2)]


@pytest.fixture
def failing_broadcast(monkeypatch: pytest.MonkeyPatch) -> None:
    def broadcast_plugin_event(plugin_id: str, event: str, payload: dict[str, Any]) -> None:
        raise RuntimeError("socket down")

    child = ModuleType("hermes_cli.plugin_events")
    child.broadcast_plugin_event = broadcast_plugin_event  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", ModuleType("hermes_cli"))
    monkeypatch.setitem(sys.modules, "hermes_cli.plugin_events", child)


def event_warnings(caplog: pytest.LogCaptureFixture, suffix: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.levelno == logging.WARNING and r.name.endswith(suffix)]


@pytest.mark.usefixtures("failing_broadcast")
def test_publish_fault_keeps_the_tool_result(
    connect: ConnFactory, store: BoardStore, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        result = tool_edit(connect, add_args(), "s1")

    assert result["ok"] is True
    assert [item.text for item in store.get_board("s1").items] == ["a"]
    assert len(event_warnings(caplog, "session_tasks.events")) == 1


@pytest.mark.usefixtures("failing_broadcast")
def test_publish_fault_keeps_the_route_reply(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
    store: BoardStore,
    caplog: pytest.LogCaptureFixture,
) -> None:
    install_fake_hermes(monkeypatch, db_path)
    client = make_client(load_plugin_api())

    with caplog.at_level(logging.WARNING):
        response = client.post(PREFIX + "/board/edit", json={"session_id": "s1", **add_args()})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert [item.text for item in store.get_board("s1").items] == ["a"]
    assert len(event_warnings(caplog, ".events")) == 1


def test_missing_hermes_logs_and_returns(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setitem(sys.modules, "hermes_cli.plugin_events", None)

    with caplog.at_level(logging.WARNING):
        result = events.publish("s1", "s1", 1, "agent")

    assert result is None
    assert len(event_warnings(caplog, "session_tasks.events")) == 1


def test_payload_holds_no_text(writer: Writer, broadcasts: list[BroadcastCall]) -> None:
    writer(add_args("secret words"), "s1")

    ((_, _, payload),) = broadcasts
    assert set(payload) == {"session_id", "root_id", "rev", "actor"}
    assert all("secret words" not in str(value) for value in payload.values())
