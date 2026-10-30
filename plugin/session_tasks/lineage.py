"""Session id to board root. The reader is a Protocol, so tests need no Hermes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeAlias

from .db import ConnFactory
from .model import Clock, InvalidSession, utc_now


class SessionReader(Protocol):
    """The four public `SessionDB` methods the plugin uses."""

    def get_session(self, session_id: str) -> dict[str, Any] | None: ...

    def get_compression_lineage(self, session_id: str) -> list[str]: ...

    def is_explicit_fork_child(self, session_id: str) -> bool: ...

    def close(self) -> None: ...


ReaderFactory: TypeAlias = Callable[[], SessionReader]
ResolutionKind: TypeAlias = Literal["plain", "compression", "branch", "delegate"]


@dataclass(frozen=True, slots=True)
class Resolution:
    root_id: str
    kind: ResolutionKind
    forked_from: str | None = None


@dataclass(frozen=True)
class SessionResolver:
    connect: ConnFactory
    open_reader: ReaderFactory
    clock: Clock = utc_now

    def resolve(self, session_id: str) -> Resolution:
        """Return the board root for a session. Never defaults to an empty or shared key."""
        if not isinstance(session_id, str) or not session_id.strip():
            raise InvalidSession("session id must be a non-empty string")
        return self._walk(session_id)

    def _walk(self, session_id: str) -> Resolution:
        reader = self.open_reader()
        try:
            lineage = reader.get_compression_lineage(session_id)
        finally:
            reader.close()
        root_id = lineage[0] if lineage else session_id
        kind: ResolutionKind = "compression" if root_id != session_id else "plain"
        return Resolution(root_id, kind)
