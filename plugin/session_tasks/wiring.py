"""Build the store, the resolver and the handlers, then register them with Hermes."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from . import hooks, paths, session_reader, tool_text
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
    """Register tools, hooks, prompt section and skill. Hermes calls this once."""
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
    ctx.register_tool(
        name=tool_text.BOARD_EDIT,
        toolset=tool_text.TOOLSET,
        schema=tool_text.BOARD_EDIT_SCHEMA,
        handler=tools.board_edit,
        emoji=tool_text.TOOL_EMOJI,
    )
    ctx.register_hook("pre_tool_call", hooks.make_pre_tool_call(store, resolver))
    ctx.register_hook("post_compaction", hooks.make_post_compaction(resolver))
    ctx.register_hook("pre_llm_call", hooks.make_pre_llm_call(store, resolver))
    ctx.register_system_prompt_section(
        tool_text.PROMPT_SECTION_ID,
        tool_text.PROMPT_SECTION_TEXT,
        max_chars=tool_text.PROMPT_SECTION_MAX,
    )
    ctx.register_skill(tool_text.SKILL_NAME, skill_path(), description=tool_text.SKILL_DESCRIPTION)
