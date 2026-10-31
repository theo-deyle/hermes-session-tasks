"""`register(ctx)` wires both tools, both hooks, the prompt section and the skill. No gateway."""

from __future__ import annotations

import json
from pathlib import Path

from fakes import FakeCtx, FakeReaderFactory
from session_tasks import tool_text
from session_tasks.db import ConnFactory
from session_tasks.edit_args import OP_FIELDS
from session_tasks.model import AddItem
from session_tasks.store import BoardStore
from session_tasks.wiring import register, skill_path

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


def test_register_records_both_tools_in_one_toolset(connect: ConnFactory) -> None:
    ctx = registered(connect)

    assert sorted(ctx.tools) == ["board_edit", "board_read"]
    assert "" not in ctx.tools
    for entry in ctx.tools.values():
        assert entry["toolset"] == "task-board"
        assert entry["emoji"] == "\U0001f4cb"
    assert ctx.tools["board_read"]["schema"] is tool_text.BOARD_READ_SCHEMA
    assert ctx.tools["board_edit"]["schema"] is tool_text.BOARD_EDIT_SCHEMA


def test_register_records_both_hooks(connect: ConnFactory) -> None:
    ctx = registered(connect)

    assert sorted(ctx.hooks) == ["post_compaction", "pre_tool_call"]
    assert [len(callbacks) for callbacks in ctx.hooks.values()] == [1, 1]


def test_register_records_the_prompt_section(connect: ConnFactory) -> None:
    ctx = registered(connect)

    assert ctx.sections == [
        (tool_text.PROMPT_SECTION_ID, tool_text.PROMPT_SECTION_TEXT, tool_text.PROMPT_SECTION_MAX)
    ]


def test_register_records_the_skill(connect: ConnFactory) -> None:
    ctx = registered(connect)

    assert ctx.skills == [(tool_text.SKILL_NAME, skill_path(), tool_text.SKILL_DESCRIPTION)]
    assert skill_path().is_file()


def test_schema_matches_the_parser() -> None:
    item = tool_text.BOARD_EDIT_SCHEMA["parameters"]["properties"]["ops"]["items"]

    assert set(item["properties"]["op"]["enum"]) == set(OP_FIELDS)
    assert set(item["properties"]) == set().union(*OP_FIELDS.values())


def test_registered_edit_handler_and_hook_work_together(connect: ConnFactory) -> None:
    ctx = registered(connect)
    edit = ctx.tools["board_edit"]["handler"]
    guard = ctx.hooks["pre_tool_call"][0]
    add = {"ops": [{"op": "add", "text": "Call John"}]}
    remove = {"ops": [{"op": "remove", "item_id": 1}], "base_rev": 1}

    assert json.loads(edit(add, session_id="s1"))["ok"] is True
    directive = guard(tool_name="board_edit", args=remove, session_id="s1")
    applied = json.loads(edit({**remove, "confirmed": True}, session_id="s1"))

    assert directive is not None
    assert directive["action"] == "block"
    assert applied["changed"] == ["- removed #1"]
