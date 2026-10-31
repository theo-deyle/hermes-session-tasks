"""Tool text rules: name prefix, the todo boundary, the 60 character first sentence."""

from __future__ import annotations

import re
from typing import Any

from session_tasks import tool_text

SHORT_DESC_LIMIT = 60
SENTENCE_END = re.compile(r"[.!?](?=\s)")


def first_sentence(text: str) -> str:
    """Mirror the Hermes catalog rule: the first sentence ends at . ! or ? followed by a space."""
    match = SENTENCE_END.search(text)
    return text[: match.end()] if match else text


def property_names(node: Any) -> set[str]:
    """Collect every property name at any depth of a JSON schema."""
    names: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                names.update(value)
            names |= property_names(value)
    elif isinstance(node, list):
        for value in node:
            names |= property_names(value)
    return names


def test_board_read_name_starts_with_board_prefix() -> None:
    assert tool_text.BOARD_READ.startswith("board_")
    assert tool_text.BOARD_READ_SCHEMA["name"] == tool_text.BOARD_READ


def test_board_read_text_names_todo_only_inside_the_todo_list_token() -> None:
    description = tool_text.BOARD_READ_DESCRIPTION.lower()

    assert "todo" not in tool_text.BOARD_READ.lower()
    assert description.count("todo") == description.count("todo_list") == 1


def test_board_read_description_names_memory_and_kanban() -> None:
    description = tool_text.BOARD_READ_DESCRIPTION

    assert "memory" in description
    assert "kanban_*" in description


def test_board_read_first_sentence_fits_the_catalog_limit() -> None:
    sentence = first_sentence(tool_text.BOARD_READ_SCHEMA["description"])

    assert len(sentence) <= SHORT_DESC_LIMIT
    assert sentence == "Read Theo's task board with item ids and the revision."


def test_board_read_schema_declares_no_session_id_property() -> None:
    assert "session_id" not in property_names(tool_text.BOARD_READ_SCHEMA)


def test_first_sentence_helper_stops_at_the_first_period_and_space() -> None:
    assert first_sentence("One. Two.") == "One."
    assert first_sentence("No end") == "No end"
