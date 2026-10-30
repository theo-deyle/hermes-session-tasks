"""Board types, operations, results, errors, caps and text rules. This module does no I/O."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, TypeAlias

Actor: TypeAlias = Literal["agent", "user"]
ChangeOp: TypeAlias = Literal["add", "text", "check", "uncheck", "remove", "forked"]
StaleReason: TypeAlias = Literal["stale", "not_found"]
Clock: TypeAlias = Callable[[], str]

MAX_ITEMS = 100
MAX_TEXT_CHARS = 500
MAX_DEPTH = 1
JOURNAL_KEEP = 100

DROPPED_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co"})


def utc_now() -> str:
    """Return the current UTC time as ISO 8601 text with microseconds and a Z suffix."""
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Item:
    id: int
    parent_id: int | None
    position: int
    text: str
    checked: bool
    rev: int
    updated_by: Actor
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class Board:
    root_id: str
    rev: int
    next_item_id: int
    items: tuple[Item, ...]
    forked_from: str | None = None

    def item(self, item_id: int) -> Item | None:
        for candidate in self.items:
            if candidate.id == item_id:
                return candidate
        return None

    def top_level(self) -> tuple[Item, ...]:
        return tuple(item for item in self.items if item.parent_id is None)

    def children(self, item_id: int) -> tuple[Item, ...]:
        return tuple(item for item in self.items if item.parent_id == item_id)


def _sort_key(item: Item) -> tuple[int, int]:
    return (item.position, item.id)


def display_order(items: Iterable[Item]) -> tuple[Item, ...]:
    """Order top-level items by (position, id), each followed by its subtasks."""
    pool = sorted(items, key=_sort_key)
    subtasks: dict[int, list[Item]] = {}
    for item in pool:
        if item.parent_id is not None:
            subtasks.setdefault(item.parent_id, []).append(item)
    ordered: list[Item] = []
    for item in pool:
        if item.parent_id is None:
            ordered.append(item)
            ordered.extend(subtasks.get(item.id, ()))
    return tuple(ordered)


@dataclass(frozen=True, slots=True)
class AddItem:
    text: str
    checked: bool = False
    parent_id: int | None = None
    parent_ref: int | None = None


@dataclass(frozen=True, slots=True)
class SetText:
    item_id: int
    text: str


@dataclass(frozen=True, slots=True)
class SetChecked:
    item_id: int
    checked: bool


@dataclass(frozen=True, slots=True)
class RemoveItem:
    item_id: int


Op: TypeAlias = AddItem | SetText | SetChecked | RemoveItem


@dataclass(frozen=True, slots=True)
class Applied:
    board: Board
    rev: int
    changed_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Stale:
    board: Board
    reason: StaleReason
    op_index: int
    item_id: int | None


WriteResult: TypeAlias = Applied | Stale


@dataclass(frozen=True, slots=True)
class Change:
    rev: int
    actor: Actor
    op: ChangeOp
    item_id: int | None
    text: str | None
    ts: str


class BoardError(ValueError):
    """A rule of the board rejected a write. `op_index` names the failing operation."""

    def __init__(self, message: str, op_index: int | None = None) -> None:
        super().__init__(message)
        self.op_index = op_index


class EmptyText(BoardError):
    pass


class TextTooLong(BoardError):
    pass


class BoardFull(BoardError):
    pass


class DepthExceeded(BoardError):
    pass


class BadParentRef(BoardError):
    pass


class InvalidSession(ValueError):
    """The session id is empty, blank or not a string."""


def sanitize_text(text: str) -> str:
    """Return one-line text that cannot forge a second checklist line.

    Every whitespace character becomes a space. Then every character in the Unicode
    categories Cc, Cf, Cs and Co is dropped. Then runs of spaces collapse to one.
    Category Cf includes U+200D (zero-width joiner) and the tag characters U+E0020 to
    U+E007F. A multi-part emoji joined by U+200D is therefore stored as its parts with
    no joiner. A single-code-point emoji is stored unchanged.

    The drop step runs before the collapse step. The reverse order can leave a double
    space and break idempotence.
    """
    spaced = "".join(" " if char.isspace() else char for char in text)
    kept = "".join(char for char in spaced if unicodedata.category(char) not in DROPPED_CATEGORIES)
    return " ".join(kept.split())


def clean_text(text: str, op_index: int | None = None) -> str:
    """Sanitise `text`, then reject an empty or over-long result.

    Length counts Unicode code points of the stored text. The text is not normalised.
    """
    cleaned = sanitize_text(text)
    if not cleaned:
        raise EmptyText("item text is empty", op_index)
    if len(cleaned) > MAX_TEXT_CHARS:
        raise TextTooLong(f"item text is longer than {MAX_TEXT_CHARS} characters", op_index)
    return cleaned
