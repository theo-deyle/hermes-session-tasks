"""Test doubles for the Hermes session reader.

`FakeSessionReader` mirrors the four public `SessionDB` lineage methods that the plugin
uses. It imports no `session_tasks` module: the match with the plugin Protocol is structural.
The `hermes` contract test pins this fake to a real `SessionDB`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SessionSpec:
    parent: str | None = None
    end_reason: str | None = None
    model_config: dict[str, Any] | None = None
    source: str = "desktop"

    def marker(self, key: str) -> str:
        value = (self.model_config or {}).get(key)
        return value.strip() if isinstance(value, str) else ""


SEVEN_ROW_FIXTURE: dict[str, SessionSpec] = {
    "root": SessionSpec(end_reason="compression"),
    "comp1": SessionSpec(parent="root", end_reason="compression"),
    "comp2": SessionSpec(parent="comp1"),
    "br": SessionSpec(parent="comp2", model_config={"_branched_from": "comp2"}),
    "dg": SessionSpec(parent="comp2", model_config={"_delegate_from": "comp2"}),
    "rs": SessionSpec(parent="comp2", model_config={"_reset_from": "comp2"}),
    "plain": SessionSpec(),
}


class ReaderBoom(RuntimeError):
    """Raised by a fake reader method that a test chose to break."""


class FakeSessionReader:
    def __init__(self, specs: dict[str, SessionSpec], raise_in: str | None = None) -> None:
        self._specs = specs
        self._raise_in = raise_in
        self.closed = False

    def _maybe_raise(self, method: str) -> None:
        if self._raise_in == method:
            raise ReaderBoom(method)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        self._maybe_raise("get_session")
        spec = self._specs.get(session_id)
        if spec is None:
            return None
        row: dict[str, Any] = {
            "id": session_id,
            "source": spec.source,
            "parent_session_id": spec.parent,
            "end_reason": spec.end_reason,
            "model_config": json.dumps(spec.model_config) if spec.model_config else None,
        }
        # Hermes lifts these two markers to top-level keys. It does not lift _delegate_from.
        for key in ("_branched_from", "_reset_from"):
            if spec.marker(key):
                row[key] = spec.marker(key)
        return row

    def is_explicit_fork_child(self, session_id: str) -> bool:
        self._maybe_raise("is_explicit_fork_child")
        spec = self._specs.get(session_id)
        if spec is None:
            return False
        if spec.source == "tool":
            return True
        parent = spec.parent or ""
        return bool(parent) and parent in (
            spec.marker("_branched_from"),
            spec.marker("_delegate_from"),
        )

    def get_compression_lineage(self, session_id: str) -> list[str]:
        self._maybe_raise("get_compression_lineage")
        if session_id not in self._specs:
            return []
        if self.is_explicit_fork_child(session_id):
            return [session_id]
        root = session_id
        while self._is_compression_child(root):
            parent = self._specs[root].parent
            assert parent is not None
            root = parent
        lineage = [root]
        tip = root
        while (child := self._compression_child_of(tip)) is not None and child not in lineage:
            lineage.append(child)
            tip = child
        return lineage if session_id in lineage else [session_id]

    def close(self) -> None:
        self.closed = True

    def _is_compression_child(self, session_id: str) -> bool:
        spec = self._specs[session_id]
        parent = self._specs.get(spec.parent) if spec.parent else None
        return (
            parent is not None
            and parent.end_reason == "compression"
            and not self.is_explicit_fork_child(session_id)
            and spec.marker("_reset_from") != spec.parent
        )

    def _compression_child_of(self, session_id: str) -> str | None:
        for candidate, spec in self._specs.items():
            if spec.parent == session_id and self._is_compression_child(candidate):
                return candidate
        return None


class FakeReaderFactory:
    """Callable that opens a fake reader. It counts opens and keeps each reader."""

    def __init__(self, specs: dict[str, SessionSpec], raise_in: str | None = None) -> None:
        self._specs = specs
        self._raise_in = raise_in
        self.readers: list[FakeSessionReader] = []

    def __call__(self) -> FakeSessionReader:
        reader = FakeSessionReader(self._specs, self._raise_in)
        self.readers.append(reader)
        return reader

    @property
    def opens(self) -> int:
        return len(self.readers)

    @property
    def all_closed(self) -> bool:
        return all(reader.closed for reader in self.readers)


class RaisingReaderFactory:
    """Callable that raises on every open, like `SessionDB` when state.db is missing."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.opens = 0

    def __call__(self) -> FakeSessionReader:
        self.opens += 1
        raise self._exc


class FakeCtx:
    """Records what `register(ctx)` registers. It matches the Hermes plugin context by shape."""

    def __init__(self) -> None:
        self.tools: dict[str, dict[str, Any]] = {}
        self.hooks: dict[str, list[Callable[..., Any]]] = {}
        self.skills: list[tuple[str, Path, str]] = []
        self.sections: list[tuple[str, str, int]] = []

    def register_tool(
        self,
        name: str,
        toolset: str,
        schema: dict[str, Any],
        handler: Callable[..., Any],
        **kw: Any,
    ) -> None:
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler, **kw}

    def register_hook(self, hook_name: str, callback: Callable[..., Any]) -> None:
        self.hooks.setdefault(hook_name, []).append(callback)

    def register_skill(
        self, name: str, path: Path, description: str = "", frontmatter: Any = None
    ) -> None:
        self.skills.append((name, path, description))

    def register_system_prompt_section(
        self, id: str, content: str, *, position: str = "after_memory", max_chars: int = 4000
    ) -> None:
        self.sections.append((id, content, max_chars))
