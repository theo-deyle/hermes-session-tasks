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
sys.path.insert(0, CHECKOUT_DIR)
sys.path.insert(0, PLUGIN_DIR)

from hermes_cli.plugins import discover_plugins  # pyright: ignore[reportMissingImports]  # noqa: E402
from model_tools import handle_function_call  # pyright: ignore[reportMissingImports]  # noqa: E402
from session_tasks import paths  # noqa: E402
from session_tasks.model import AddItem  # noqa: E402
from session_tasks.store import BoardStore  # noqa: E402
from tools.registry import registry  # pyright: ignore[reportMissingImports]  # noqa: E402

SLUG = "hermes-session-tasks"
TOOLSET = "task-board"


def link_and_enable(home: Path) -> None:
    plugins = home / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    (plugins / SLUG).symlink_to(Path(PLUGIN_DIR), target_is_directory=True)
    (home / "config.yaml").write_text(
        f"plugins:\n  enabled:\n    - {SLUG}\n", encoding="utf-8"
    )


def call(args: dict[str, object], session_id: str | None) -> object:
    raw = handle_function_call("board_read", args, session_id=session_id)
    return json.loads(raw)


def main() -> None:
    home = Path(os.environ["HERMES_HOME"])
    link_and_enable(home)
    discover_plugins()
    BoardStore(paths.connect).apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)
    result = {
        "read": call({}, "s1"),
        "spoofed": call({"session_id": "s2"}, "s1"),
        "no_session": call({}, None),
        "tools": sorted(registry.get_tool_names_for_toolset(TOOLSET)),
    }
    print(json.dumps(result))


main()
