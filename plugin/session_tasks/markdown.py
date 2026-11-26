"""Render a board as a markdown checklist, parse a checklist, plan an import.

This module does no I/O. It imports the standard library and `.model` only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .model import MAX_TEXT_CHARS, AddItem, Board, Item, sanitize_text

SUBTASK_INDENT = "  "
TAB_WIDTH = 4
MAX_HINT_DIGITS = 18

# Text of this shape would read back as an id token. One backslash goes before it.
ESCAPED_HASH = re.compile(r"^\\*#[0-9]+(?:\s|$)")
ID_TOKEN = re.compile(r"^#([0-9]+) ")
THEMATIC_BREAK = re.compile(r"^\s{0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$")
ITEM_LINE = re.compile(r"^(\s*)[-*+]\s+(?:\[([ xX])\](?=\s|$)\s*)?(.*)$")


def _escape(text: str) -> str:
    return f"\\{text}" if ESCAPED_HASH.match(text) else text


def _line(item: Item, include_ids: bool) -> str:
    indent = SUBTASK_INDENT if item.parent_id is not None else ""
    box = "[x]" if item.checked else "[ ]"
    marker = f"#{item.id} " if include_ids else ""
    return f"{indent}- {box} {marker}{_escape(item.text)}\n"


def render(board: Board, *, include_ids: bool) -> str:
    """Return one line per item in board order. An empty board gives an empty string.

    The agent view passes `include_ids=True` (D-04). The clipboard view for the user
    passes `include_ids=False` (D-05). Text that starts with `#<digits>` gets one
    leading backslash, so `parse` reads it back unchanged.
    """
    return "".join(_line(item, include_ids) for item in board.items)


@dataclass(frozen=True, slots=True)
class ParsedItem:
    text: str
    checked: bool
    hint_id: int | None
    children: tuple[ParsedItem, ...]


@dataclass(frozen=True, slots=True)
class ParseResult:
    items: tuple[ParsedItem, ...]
    moved: int
    skipped_empty: int
    too_long: int


@dataclass(frozen=True, slots=True)
class ImportPlan:
    ops: tuple[AddItem, ...]
    overflow: int


@dataclass(frozen=True, slots=True)
class _RawLine:
    indent: int
    checked: bool
    text: str


@dataclass(slots=True)
class _Node:
    """A top-level item while the tree is built. Frozen into ParsedItem at the end."""

    text: str
    checked: bool
    hint_id: int | None
    children: list[ParsedItem] = field(default_factory=list)


@dataclass(slots=True)
class _Tally:
    moved: int = 0
    skipped_empty: int = 0
    too_long: int = 0


def _match_line(line: str) -> _RawLine | None:
    """Return the parts of a checklist or bullet line, or None for any other line."""
    if THEMATIC_BREAK.match(line):
        return None
    found = ITEM_LINE.match(line)
    if found is None:
        return None
    indent, mark, text = found.groups()
    return _RawLine(len(indent), mark in ("x", "X"), text)


def _clean_text(raw: str) -> tuple[str, int | None]:
    """Strip one id token, remove one escape backslash, then sanitise."""
    hint_id: int | None = None
    token = ID_TOKEN.match(raw)
    if token is not None:
        digits = token.group(1)
        hint_id = int(digits) if len(digits) <= MAX_HINT_DIGITS else None
        raw = raw[token.end() :]
    if raw.startswith("\\") and ESCAPED_HASH.match(raw):
        raw = raw[1:]
    return sanitize_text(raw), hint_id


def _freeze(node: _Node) -> ParsedItem:
    return ParsedItem(node.text, node.checked, node.hint_id, tuple(node.children))


def _build_tree(lines: list[_RawLine]) -> ParseResult:
    """Nest lines by indent column with a stack. Every line goes on the stack.

    A skipped line goes on as a placeholder (None). A line under a placeholder
    top-level entry becomes top-level itself.
    """
    tops: list[_Node] = []
    stack: list[tuple[int, _Node | None]] = []
    tally = _Tally()
    for line in lines:
        while stack and stack[-1][0] >= line.indent:
            stack.pop()
        depth = len(stack)
        text, hint_id = _clean_text(line.text)
        node: _Node | None = None
        if not text:
            tally.skipped_empty += 1
        elif len(text) > MAX_TEXT_CHARS:
            tally.too_long += 1
        else:
            node = _Node(text, line.checked, hint_id)
        root = stack[0][1] if depth else None
        if node is not None:
            if depth >= 2:
                tally.moved += 1
            if depth and root is not None:
                root.children.append(_freeze(node))
            else:
                tops.append(node)
        stack.append((line.indent, node))
    return ParseResult(
        tuple(_freeze(top) for top in tops), tally.moved, tally.skipped_empty, tally.too_long
    )


def parse(text: str) -> ParseResult:
    """Read a pasted checklist into items. No line is dropped without a count.

    Checklist lines and plain `-`, `*` and `+` bullets become items (D-08). Every
    other line is ignored. Nesting deeper than one subtask level moves up under the
    nearest top-level item and counts in `moved` (D-02). A line with empty text counts
    in `skipped_empty` (D-09). A line over 500 code points counts in `too_long` and
    the parse goes on (D-10).
    """
    expanded = text.expandtabs(TAB_WIDTH)
    matched = (_match_line(line) for line in expanded.splitlines())
    return _build_tree([raw for raw in matched if raw is not None])


def plan_import(result: ParseResult, capacity: int) -> ImportPlan:
    """Turn a parse result into AddItem ops in display order, up to `capacity` items.

    A subtask links to its parent with `parent_ref`. A parent comes before its
    subtasks, so a cut never leaves a subtask without its parent. Every item that
    does not fit counts in `overflow` (D-10).
    """
    if capacity < 0:
        raise ValueError("capacity must not be negative")
    ops: list[AddItem] = []
    overflow = 0
    for top in result.items:
        if len(ops) >= capacity:
            overflow += 1 + len(top.children)
            continue
        parent_index = len(ops)
        ops.append(AddItem(top.text, top.checked))
        for child in top.children:
            if len(ops) >= capacity:
                overflow += 1
                continue
            ops.append(AddItem(child.text, child.checked, parent_ref=parent_index))
    return ImportPlan(tuple(ops), overflow)
