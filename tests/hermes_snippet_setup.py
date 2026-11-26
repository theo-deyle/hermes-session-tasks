"""Setup helpers for the gateway venv snippets, which are not pytest modules.

A snippet puts this directory on `sys.path`, then imports this module. The helpers never
touch the real Hermes home: the caller sets HERMES_HOME to a temporary directory first.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

SLUG = "hermes-session-tasks"


def link_and_enable(home: Path, plugin_dir: Path) -> None:
    """Link the plugin dir into `home/plugins` and enable it in `home/config.yaml`.

    Call this before the first Hermes import: importing `model_tools` can run plugin
    discovery once, and a discovery that runs before the link exists never sees the plugin.
    """
    plugins = home / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    (plugins / SLUG).symlink_to(plugin_dir, target_is_directory=True)
    (home / "config.yaml").write_text(f"plugins:\n  enabled:\n    - {SLUG}\n", encoding="utf-8")


def stub_gateway_server(record: Callable[[str, dict[str, object]], None]) -> None:
    """Install stand-ins for `tui_gateway` and `tui_gateway.server`.

    A board write publishes `board.updated` through `tui_gateway.server`. Importing the real
    module in a bare process pulls in the whole gateway stack. The stand-in calls `record`
    and keeps the real `broadcast_plugin_event` and its name check in the path.
    """
    server = ModuleType("tui_gateway.server")
    server._broadcast_global_event = record  # type: ignore[attr-defined]
    sys.modules["tui_gateway"] = ModuleType("tui_gateway")
    sys.modules["tui_gateway.server"] = server
