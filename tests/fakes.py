"""Test doubles for the Hermes session reader.

`FakeSessionReader` mirrors the four public `SessionDB` lineage methods that the plugin
uses. It imports no `session_tasks` module: the match with the plugin Protocol is structural.
The `hermes` contract test pins this fake to a real `SessionDB`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
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


class FakeSessionReader:
    def __init__(self, specs: dict[str, SessionSpec]) -> None:
        self._specs = specs
        self.closed = False

    def get_session(self, session_id: str) -> dict[str, Any] | None:
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

    def __init__(self, specs: dict[str, SessionSpec]) -> None:
        self._specs = specs
        self.readers: list[FakeSessionReader] = []

    def __call__(self) -> FakeSessionReader:
        reader = FakeSessionReader(self._specs)
        self.readers.append(reader)
        return reader

    @property
    def opens(self) -> int:
        return len(self.readers)

    @property
    def all_closed(self) -> bool:
        return all(reader.closed for reader in self.readers)
