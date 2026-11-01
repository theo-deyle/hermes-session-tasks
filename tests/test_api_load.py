"""A Hermes-style load of `plugin_api.py` serves the board that a tool call wrote."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from api_client import (
    CORE_KEY,
    MODULE_NAME,
    PREFIX,
    install_fake_hermes,
    load_plugin_api,
    make_client,
    unload_plugin_api,
)
from fakes import FakeSessionReader
from session_tasks.board_tools import BoardTools
from session_tasks.db import ConnFactory
from session_tasks.lineage import SessionResolver
from session_tasks.store import BoardStore

MANIFEST = Path(__file__).resolve().parent.parent / "plugin" / "dashboard" / "manifest.json"


@pytest.fixture(autouse=True)
def clean_core() -> Iterator[None]:
    unload_plugin_api()
    yield
    unload_plugin_api()


def tool_writes(connect: ConnFactory, text: str) -> None:
    store = BoardStore(connect)
    resolver = SessionResolver(connect, lambda: FakeSessionReader({}))
    tools = BoardTools(store, resolver)
    out = tools.board_edit({"ops": [{"op": "add", "text": text}]}, session_id="s1")
    assert json.loads(str(out))["ok"] is True


def test_host_load_serves_the_board_the_tool_wrote(
    monkeypatch: pytest.MonkeyPatch, db_path: Path, connect: ConnFactory
) -> None:
    install_fake_hermes(monkeypatch, db_path)
    module = load_plugin_api()
    tool_writes(connect, "Call John")
    client = make_client(module)

    response = client.get(PREFIX + "/board", params={"session_id": "s1"})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["session_id"] == "s1"
    assert body["root_id"] == "s1"
    assert body["rev"] == 1
    (item,) = body["board"]["items"]
    assert item["id"] == 1
    assert item["text"] == "Call John"
    assert item["checked"] is False
    assert item["updated_by"] == "agent"
    assert item["parent_id"] is None


def test_host_load_keeps_core_under_its_own_key(
    monkeypatch: pytest.MonkeyPatch, db_path: Path
) -> None:
    install_fake_hermes(monkeypatch, db_path)
    module = load_plugin_api()
    client = make_client(module)

    assert client.get(PREFIX + "/board", params={"session_id": "s1"}).status_code == 200

    assert module.__name__ == MODULE_NAME
    assert CORE_KEY in sys.modules
    store_module = sys.modules[CORE_KEY + ".store"]
    assert Path(str(store_module.__file__)).parent.name == "session_tasks"
    assert Path(str(store_module.__file__)).parent.parent.name == "plugin"

    unload_plugin_api()
    again = make_client(load_plugin_api())
    assert again.get(PREFIX + "/board", params={"session_id": "s1"}).status_code == 200


def test_missing_session_id_returns_422(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    install_fake_hermes(monkeypatch, db_path)
    client = make_client(load_plugin_api())

    assert client.get(PREFIX + "/board").status_code == 422


def test_manifest_names_the_api_file_and_hides_the_tab() -> None:
    assert json.loads(MANIFEST.read_text(encoding="utf-8")) == {
        "name": "hermes-session-tasks",
        "api": "plugin_api.py",
        "tab": {"hidden": True},
    }

