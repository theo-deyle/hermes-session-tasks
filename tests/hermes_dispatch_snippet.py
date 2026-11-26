"""Script run by the gateway venv Python against a temporary HERMES_HOME. It prints one JSON line.

Arguments: plugin dir, Hermes checkout dir. The script links the plugin dir into the temporary
Hermes home, enables it, lets Hermes discover it, then calls `handle_function_call` the way the
agent loop does. This script is not a pytest module: the gateway venv has no pytest. It never
touches the real Hermes home, because the caller sets HERMES_HOME to a temporary directory.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True
PLUGIN_DIR, CHECKOUT_DIR = sys.argv[1:3]
SLUG = "hermes-session-tasks"
TOOLSET = "task-board"


def link_and_enable(home: Path) -> None:
    plugins = home / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    (plugins / SLUG).symlink_to(Path(PLUGIN_DIR), target_is_directory=True)
    (home / "config.yaml").write_text(f"plugins:\n  enabled:\n    - {SLUG}\n", encoding="utf-8")


# Link and enable first: importing `model_tools` can run plugin discovery once, and a
# discovery that runs before the link exists would never see the plugin.
link_and_enable(Path(os.environ["HERMES_HOME"]))
sys.path.insert(0, CHECKOUT_DIR)
sys.path.insert(0, PLUGIN_DIR)

# A board write publishes `board.updated`. Hermes sends it through `tui_gateway.server`, and
# importing that module in this bare process pulls in the whole gateway stack. A recording
# stand-in keeps the real `broadcast_plugin_event` and its name check in the path.
BROADCASTS: list[list[object]] = []


def record_broadcast(name: str, payload: dict[str, object]) -> None:
    BROADCASTS.append([name, payload])


_gateway_server = ModuleType("tui_gateway.server")
_gateway_server._broadcast_global_event = record_broadcast  # type: ignore[attr-defined]
sys.modules["tui_gateway"] = ModuleType("tui_gateway")
sys.modules["tui_gateway.server"] = _gateway_server

import hermes_cli.plugins as hermes_plugins  # noqa: E402  # pyright: ignore[reportMissingImports]
from hermes_cli.plugins_dispatch import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    format_system_prompt_sections,
)
from hermes_state import SessionDB  # noqa: E402  # pyright: ignore[reportMissingImports]
from model_tools import handle_function_call  # noqa: E402  # pyright: ignore[reportMissingImports]
from session_tasks import paths  # noqa: E402
from session_tasks.model import AddItem, SetChecked  # noqa: E402
from session_tasks.store import BoardStore  # noqa: E402
from tools.registry import registry  # noqa: E402  # pyright: ignore[reportMissingImports]
from tools.tool_search_catalog import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    _short_desc,
)


def call(args: dict[str, object], session_id: str | None, tool: str = "board_read") -> object:
    raw = handle_function_call(tool, args, session_id=session_id)
    return json.loads(raw)


def directive(tool: str, args: dict[str, object], session_id: str) -> list[object]:
    return list(hermes_plugins.get_pre_tool_call_directive(tool, args, session_id=session_id))


def catalog_lines() -> dict[str, str]:
    lines: dict[str, str] = {}
    for name in ("board_read", "board_edit", "board_sessions", "board_copy"):
        entry = registry.get_entry(name)
        lines[name] = _short_desc(entry.schema["description"]) if entry else ""
    return lines


def pre_llm(session_id: str) -> list[str]:
    """Fire pre_llm_call the way the agent loop does; keep the str results only."""
    results = hermes_plugins.invoke_hook(
        "pre_llm_call",
        session_id=session_id,
        task_id="t1",
        turn_id="u1",
        user_message="hi",
        conversation_history=[],
        is_first_turn=True,
        model="m",
        platform="cli",
        parent_session_id="",
        sender_id="",
    )
    return [item for item in results if isinstance(item, str)]


REMOVE_ONE: dict[str, object] = {"ops": [{"op": "remove", "item_id": 1}], "base_rev": 2}
RAW_REMOVE: dict[str, object] = {"ops": '[{"op": "remove", "item_id": 1}]', "base_rev": "2"}


def create_session_rows() -> None:
    """Create the Hermes rows of s1 and s2 so board_sessions finds a real title for s2."""
    db = SessionDB()
    try:
        db.create_session("s1", "desktop")
        db.create_session("s2", "desktop")
        db.set_session_title("s2", "Source board")
    finally:
        db.close()


def seen_rev(root_id: str) -> int | None:
    """Read `agent_seen_rev` of one board with one SELECT on the plugin data file."""
    conn = paths.connect()
    try:
        row = conn.execute(
            "SELECT agent_seen_rev FROM boards WHERE root_id = ?", (root_id,)
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else int(row[0])


def main() -> None:
    create_session_rows()
    hermes_plugins.discover_plugins()
    store = BoardStore(paths.connect)
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Call John"), AddItem("Book the van")], actor="agent", base_rev=0)
    store.apply("s2", [SetChecked(2, True)], actor="agent", base_rev=1)
    result: dict[str, object] = {
        "read": call({}, "s1"),
        "no_session": call({}, None),
        "tools": sorted(registry.get_tool_names_for_toolset(TOOLSET)),
    }
    result["seen_before"] = seen_rev("s1")
    result["cross_read"] = call({"session_id": "s2"}, "s1")
    result["seen_after"] = seen_rev("s1")
    result["pre_llm"] = pre_llm("s1")
    result["pre_llm_blank"] = pre_llm("")
    BoardStore(paths.connect).apply("s5", [AddItem("Call John")], actor="user", base_rev=0)
    result["pre_llm_theo"] = pre_llm("s5")
    result["pre_llm_again"] = pre_llm("s5")
    add: dict[str, object] = {"ops": [{"op": "add", "text": "Book the van"}]}
    result["edit_add"] = call(add, "s1", "board_edit")
    result["blocked"] = call(REMOVE_ONE, "s1", "board_edit")
    result["raw_directive"] = directive("board_edit", RAW_REMOVE, "s1")
    result["other_directive"] = directive("read_file", {"path": "/tmp/x"}, "s1")
    result["confirmed"] = call({**REMOVE_ONE, "confirmed": True}, "s1", "board_edit")
    hermes_plugins.invoke_hook(
        "post_compaction",
        session_id="s3",
        old_session_id="s1",
        kind="summarize",
        reason="manual",
    )
    result["after_compaction"] = call({}, "s3")
    result["sessions"] = call({}, "s1", "board_sessions")
    result["copy"] = call({"from_session_id": "s2"}, "s1", "board_copy")
    sections = hermes_plugins.render_system_prompt_sections({"session_id": "s1"})
    result["section_rendered"] = format_system_prompt_sections(sections)
    result["skills"] = sorted(hermes_plugins.get_plugin_manager()._plugin_skills)
    result["catalog_lines"] = catalog_lines()
    result["broadcasts"] = BROADCASTS
    print(json.dumps(result))


main()
