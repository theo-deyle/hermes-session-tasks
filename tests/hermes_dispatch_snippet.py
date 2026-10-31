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

import hermes_cli.plugins as hermes_plugins  # noqa: E402  # pyright: ignore[reportMissingImports]
from hermes_cli.plugins_dispatch import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    format_system_prompt_sections,
)
from model_tools import handle_function_call  # noqa: E402  # pyright: ignore[reportMissingImports]
from session_tasks import paths  # noqa: E402
from session_tasks.model import AddItem  # noqa: E402
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
    for name in ("board_read", "board_edit"):
        entry = registry.get_entry(name)
        lines[name] = _short_desc(entry.schema["description"]) if entry else ""
    return lines


REMOVE_ONE: dict[str, object] = {"ops": [{"op": "remove", "item_id": 1}], "base_rev": 2}
RAW_REMOVE: dict[str, object] = {"ops": '[{"op": "remove", "item_id": 1}]', "base_rev": "2"}


def main() -> None:
    hermes_plugins.discover_plugins()
    BoardStore(paths.connect).apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)
    result: dict[str, object] = {
        "read": call({}, "s1"),
        "spoofed": call({"session_id": "s2"}, "s1"),
        "no_session": call({}, None),
        "tools": sorted(registry.get_tool_names_for_toolset(TOOLSET)),
    }
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
    sections = hermes_plugins.render_system_prompt_sections({"session_id": "s1"})
    result["section_rendered"] = format_system_prompt_sections(sections)
    result["skills"] = sorted(hermes_plugins.get_plugin_manager()._plugin_skills)
    result["catalog_lines"] = catalog_lines()
    print(json.dumps(result))


main()
