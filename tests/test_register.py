"""`register(ctx)` wires `board_read` through a fake Hermes context. No gateway needed."""

from __future__ import annotations

import json
from pathlib import Path

from fakes import FakeCtx, FakeReaderFactory
from session_tasks.db import ConnFactory
from session_tasks.model import AddItem
from session_tasks.store import BoardStore
from session_tasks.wiring import register

MANIFEST = Path(__file__).resolve().parents[1] / "plugin" / "plugin.yaml"


def manifest_list(key: str) -> list[str]:
    """Read one list key of the flat manifest. Supports `key: []` and `- item` lines."""
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"{key}:"):
            continue
        if line.strip() == f"{key}: []":
            return []
        found: list[str] = []
        for entry in lines[index + 1 :]:
            if not entry.startswith("  - "):
                break
            found.append(entry[4:].strip())
        return found
    raise AssertionError(f"manifest has no key {key}")


def registered(connect: ConnFactory) -> FakeCtx:
    ctx = FakeCtx()
    register(ctx, connect=connect, open_reader=FakeReaderFactory({}))
    return ctx


def test_register_wires_board_read_end_to_end(connect: ConnFactory, store: BoardStore) -> None:
    ctx = registered(connect)
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)

    out = ctx.tools["board_read"]["handler"]({}, session_id="s1")

    assert isinstance(out, str)
    assert json.loads(out) == {"ok": True, "rev": 1, "board": "- [ ] #1 Call John\n"}


def test_board_read_registration_fields(connect: ConnFactory) -> None:
    entry = registered(connect).tools["board_read"]

    assert entry["toolset"] == "task-board"
    assert entry["emoji"] == "\U0001f4cb"
    assert entry["schema"]["name"] == "board_read"
    assert entry["schema"]["parameters"]["properties"] == {}


def test_manifest_provides_exactly_the_registered_tools_and_hooks(connect: ConnFactory) -> None:
    ctx = registered(connect)

    assert manifest_list("provides_tools") == sorted(ctx.tools)
    assert manifest_list("provides_hooks") == sorted(ctx.hooks)
