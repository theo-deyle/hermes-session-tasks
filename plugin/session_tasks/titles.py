"""Session titles for the agent side, read through the read-only Hermes door (D-39).

A lookup never raises.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from .lineage import ReaderFactory, SessionReader
from .model import sanitize_text

UNTITLED = "Untitled session"
FIRST_MESSAGES = 5
MESSAGE_TITLE_CHARS = 60

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TitleLookup:
    """Gives each board root a label. One reader serves one call."""

    open_reader: ReaderFactory | None

    def titles(self, root_ids: Sequence[str]) -> dict[str, str]:
        """Map each root id to its label. A fault gives `Untitled session`, never an error."""
        if not root_ids:
            return {}
        if self.open_reader is None:
            return dict.fromkeys(root_ids, UNTITLED)
        try:
            reader = self.open_reader()
        except sqlite3.OperationalError:
            log.warning("session titles unavailable: no session store")
            return dict.fromkeys(root_ids, UNTITLED)
        try:
            return {root_id: _safe_label(reader, root_id) for root_id in root_ids}
        finally:
            _close(reader)

    def title_of(self, root_id: str) -> str:
        return self.titles([root_id])[root_id]


def no_titles() -> TitleLookup:
    """A lookup with no reader: every label is `Untitled session`."""
    return TitleLookup(None)


def _safe_label(reader: SessionReader, root_id: str) -> str:
    try:
        return _label(reader, root_id)
    except Exception:
        log.warning("session title read failed", exc_info=True)
        return UNTITLED


def _close(reader: SessionReader) -> None:
    try:
        reader.close()
    except Exception:
        log.warning("session title reader close failed", exc_info=True)


def _label(reader: SessionReader, root_id: str) -> str:
    """The Hermes title, else the first user message, else `Untitled session`."""
    title = reader.get_session_title(root_id)
    if isinstance(title, str) and (clean := sanitize_text(title)):
        return clean
    for row in reader.get_messages(root_id, limit=FIRST_MESSAGES):
        content = row.get("content")
        if row.get("role") != "user" or not isinstance(content, str):
            continue
        if clean := sanitize_text(content):
            return clean[:MESSAGE_TITLE_CHARS].rstrip()
    return UNTITLED
