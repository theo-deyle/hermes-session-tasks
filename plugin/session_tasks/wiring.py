"""Build the store, the resolver and the handlers, then register them with Hermes."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from . import paths, session_reader, tool_text
from .board_tools import BoardTools
from .db import ConnFactory
from .lineage import ReaderFactory, SessionResolver
from .store import BoardStore


class PluginContext(Protocol):
    """The part of the Hermes plugin context that `register` uses."""

    def register_tool(
        self,
        name: str,
        toolset: str,
        schema: dict[str, Any],
        handler: Callable[..., Any],
        **kwargs: Any,
    ) -> object: ...

    def register_hook(self, hook_name: str, callback: Callable[..., Any]) -> object: ...

    def register_skill(
        self, name: str, path: Path, description: str = "", frontmatter: Any = None
    ) -> object: ...

    def register_system_prompt_section(
        self, id: str, content: str, *, position: str = "after_memory", max_chars: int = 4000
    ) -> object: ...


def skill_path() -> Path:
    return Path(__file__).resolve().parent.parent / "skills" / "board-rules" / "SKILL.md"


def register(
    ctx: PluginContext,
    *,
    connect: ConnFactory = paths.connect,
    open_reader: ReaderFactory = session_reader.open_session_reader,
) -> None:
    """Register the plugin tools. Hermes calls this once with its own `connect` and reader."""
    store = BoardStore(connect)
    resolver = SessionResolver(connect, open_reader)
    tools = BoardTools(store, resolver)
    ctx.register_tool(
        name=tool_text.BOARD_READ,
        toolset=tool_text.TOOLSET,
        schema=tool_text.BOARD_READ_SCHEMA,
        handler=tools.board_read,
        emoji=tool_text.TOOL_EMOJI,
    )
