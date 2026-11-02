"""Session titles for the agent side, read through the read-only Hermes door (D-39). A lookup never raises."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .lineage import ReaderFactory, SessionReader

UNTITLED = "Untitled session"
FIRST_MESSAGES = 5
MESSAGE_TITLE_CHARS = 60


@dataclass(frozen=True)
class TitleLookup:
    """Gives each board root a label. One reader serves one call."""

    open_reader: ReaderFactory | None

    def titles(self, root_ids: Sequence[str]) -> dict[str, str]:
        """Map each root id to its label."""
        if not root_ids:
            return {}
        if self.open_reader is None:
            return {root_id: UNTITLED for root_id in root_ids}
        reader = self.open_reader()
        try:
            return {root_id: _label(reader, root_id) for root_id in root_ids}
        finally:
            reader.close()

    def title_of(self, root_id: str) -> str:
        return self.titles([root_id])[root_id]


def no_titles() -> TitleLookup:
    """A lookup with no reader: every label is `Untitled session`."""
    return TitleLookup(None)


def _label(reader: SessionReader, root_id: str) -> str:
    return reader.get_session_title(root_id) or UNTITLED
