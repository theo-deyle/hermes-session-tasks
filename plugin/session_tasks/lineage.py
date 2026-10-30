"""Session id to board root. The reader is a Protocol, so tests need no Hermes."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypeAlias

from . import aliases, rows, schema
from .db import ConnFactory, read_txn, write_txn
from .fork import fork_copy
from .model import Clock, InvalidSession, utc_now

MAX_LINEAGE_HOPS = 20

log = logging.getLogger(__name__)


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


class _LineageLoop(Exception):
    """A parent chain loops or is longer than `MAX_LINEAGE_HOPS`."""


@dataclass
class _Walk:
    """State of one top-level resolve: at most one reader, and the ids seen so far."""

    open_reader: ReaderFactory
    visited: set[str] = field(default_factory=set)
    _reader: SessionReader | None = None
    _unreadable: bool = False

    def reader(self) -> SessionReader | None:
        """Open the reader on first use. None means there is no state.db to read."""
        if self._reader is None and not self._unreadable:
            try:
                self._reader = self.open_reader()
            except sqlite3.OperationalError:
                self._unreadable = True
        return self._reader

    def visit(self, session_id: str) -> None:
        if session_id in self.visited or len(self.visited) >= MAX_LINEAGE_HOPS:
            raise _LineageLoop(session_id)
        self.visited.add(session_id)

    def close(self) -> None:
        if self._reader is not None:
            self._reader.close()


def _check_id(session_id: object) -> str:
    if not isinstance(session_id, str) or not session_id.strip():
        raise InvalidSession("session id must be a non-empty string")
    return session_id


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _model_config(row: dict[str, Any]) -> dict[str, Any]:
    """Decode `model_config`. A non-string, invalid or non-dict value counts as empty."""
    raw = row.get("model_config")
    if not isinstance(raw, str):
        return {}
    try:
        decoded = json.loads(raw)
    except ValueError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _branched_from(row: dict[str, Any]) -> str:
    """Return the `_branched_from` marker: the top-level key first, then `model_config`."""
    return _text(row.get("_branched_from")) or _text(_model_config(row).get("_branched_from"))


def _delegator(row: dict[str, Any]) -> str:
    """Return the id of the session that started a delegate (subagent) session."""
    return _text(_model_config(row).get("_delegate_from")) or _text(row.get("parent_session_id"))


@dataclass(frozen=True)
class SessionResolver:
    connect: ConnFactory
    open_reader: ReaderFactory
    clock: Clock = utc_now

    def resolve(self, session_id: str) -> Resolution:
        """Return the board root for a session. Never defaults to an empty or shared key.

        A known alias answers with no reader. An alias miss uses one reader per call.
        A compression tip gets an alias once its root has a board. A branch gets a copy
        of its parent board on its first touch. A delegate (subagent) session answers
        with its delegator's root and gets nothing of its own.
        """
        walk = _Walk(self.open_reader)
        try:
            return self._resolve(_check_id(session_id), walk)
        except _LineageLoop as loop:
            log.warning("session lineage loops or is too long at %r; using the session id", loop)
            return Resolution(session_id, "plain")
        finally:
            walk.close()

    def record_compaction(self, session_id: str, old_session_id: str) -> None:
        """Alias the new session id to the board root of the session it replaced.

        Phase 2 calls this from the `post_compaction` hook.
        """
        new_id = _check_id(session_id)
        old_id = old_session_id.strip() if isinstance(old_session_id, str) else ""
        if not old_id or old_id == new_id:
            return
        walk = _Walk(self.open_reader)
        try:
            root_id = self._root_of_old(old_id, walk)
        except _LineageLoop as loop:
            log.warning("session lineage loops or is too long at %r; using the old id", loop)
            root_id = old_id
        finally:
            walk.close()
        if root_id == new_id:
            return
        with schema.open_db(self.connect) as conn, write_txn(conn):
            aliases.put_alias(conn, new_id, root_id)

    def _alias_of(self, session_id: str) -> str | None:
        with schema.open_db(self.connect) as conn, read_txn(conn):
            return aliases.get_alias(conn, session_id)

    def _root_of_old(self, old_id: str, walk: _Walk) -> str:
        """Use the same rule as `resolve`, so plain, compression, branch and delegate agree."""
        return self._resolve(old_id, walk).root_id

    def _resolve(self, session_id: str, walk: _Walk) -> Resolution:
        known = self._alias_of(session_id)
        if known is not None:
            return Resolution(known, "plain" if known == session_id else "compression")
        reader = walk.reader()
        if reader is None:
            return Resolution(session_id, "plain")
        walk.visit(session_id)
        row = reader.get_session(session_id)
        if row is None:
            return Resolution(session_id, "plain")
        if not reader.is_explicit_fork_child(session_id):
            return self._compression(session_id, reader, walk)
        branched = _branched_from(row)
        if branched:
            return self._branch(session_id, branched, walk)
        delegator = _delegator(row)
        if not delegator:
            return Resolution(session_id, "plain")
        return Resolution(self._resolve(delegator, walk).root_id, "delegate")

    def _compression(self, session_id: str, reader: SessionReader, walk: _Walk) -> Resolution:
        """Resolve a compression child through its chain root.

        The chain root can be a branch (it needs its parent copy) or a delegate (it uses the
        delegator root). `_resolve` on that root does both.
        """
        lineage = reader.get_compression_lineage(session_id)
        chain_root = lineage[0] if lineage else session_id
        if chain_root == session_id:
            return Resolution(session_id, "plain")
        root_id = chain_root
        if reader.is_explicit_fork_child(chain_root):
            root_id = self._resolve(chain_root, walk).root_id
        with schema.open_db(self.connect) as conn, write_txn(conn):
            if rows.read_board(conn, root_id) is not None:
                aliases.put_alias(conn, session_id, root_id)
        return Resolution(root_id, "compression")

    def _branch(self, session_id: str, branched: str, walk: _Walk) -> Resolution:
        """Resolve the parent first. The copy runs after every recursive resolve is done."""
        parent_root = self._resolve(branched, walk).root_id
        fork_copy(self.connect, session_id, parent_root, self.clock)
        return Resolution(session_id, "branch", forked_from=parent_root)
