"""Tool text rules: name prefix, the todo boundary, the 60 character first sentence."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from session_tasks import tool_text, wiring

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


EDIT_FIRST_SENTENCE = "Add to Theo's board what he must do, decide or remember."
EDIT_KEY_PHRASES = (
    "Theo must do, decide or remember",
    "todo_list",
    "Ask Theo one plain question",
    "confirmed true",
    "check it and tell Theo in one line",
    "base_rev",
)
COMBINATOR_KEYS = {"oneOf", "anyOf", "allOf", "not"}
WHOLE_BOARD_NAMES = {"items", "board", "markdown", "replace"}
ITEM_FIELD_TYPES = {
    "text": "string",
    "item_id": "integer",
    "checked": "boolean",
    "parent_id": "integer",
    "parent_ref": "integer",
}


def todo_check_passes(description: str) -> bool:
    """Count code points after lower(): todo may appear once, only inside todo_list."""
    return description.lower().count("todo") == description.count("todo_list") == 1


def sentence_fits(sentence: str) -> bool:
    return len(sentence) <= SHORT_DESC_LIMIT


def schema_nodes(node: Any) -> list[dict[str, Any]]:
    """Return every dict inside a JSON schema, at any depth."""
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        found.append(node)
        for value in node.values():
            found.extend(schema_nodes(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(schema_nodes(value))
    return found


def item_schema() -> dict[str, Any]:
    return tool_text.BOARD_EDIT_SCHEMA["parameters"]["properties"]["ops"]["items"]


def test_board_edit_schema_is_flat() -> None:
    parameters = tool_text.BOARD_EDIT_SCHEMA["parameters"]
    ops = parameters["properties"]["ops"]

    assert tool_text.BOARD_EDIT_SCHEMA["name"] == tool_text.BOARD_EDIT
    assert parameters["type"] == "object"
    assert set(parameters["properties"]) == {"ops", "base_rev", "confirmed"}
    assert parameters["required"] == ["ops"]
    assert ops["type"] == "array"
    assert ops["maxItems"] == 100
    assert item_schema()["required"] == ["op"]
    assert item_schema()["additionalProperties"] is False


def test_op_enum_has_exactly_four_values() -> None:
    enum = item_schema()["properties"]["op"]["enum"]

    assert enum == ["add", "set_text", "set_checked", "remove"]


def test_item_fields_are_the_five_op_fields() -> None:
    properties = item_schema()["properties"]

    assert {name: properties[name]["type"] for name in ITEM_FIELD_TYPES} == ITEM_FIELD_TYPES
    assert set(properties) == {"op", *ITEM_FIELD_TYPES}


def test_base_rev_and_confirmed_types() -> None:
    properties = tool_text.BOARD_EDIT_SCHEMA["parameters"]["properties"]

    assert properties["base_rev"]["type"] == "integer"
    assert properties["confirmed"]["type"] == "boolean"


def test_no_schema_holds_a_combinator_or_a_type_array() -> None:
    for schema in (tool_text.BOARD_READ_SCHEMA, tool_text.BOARD_EDIT_SCHEMA):
        for node in schema_nodes(schema):
            assert not COMBINATOR_KEYS & set(node)
            if "type" in node:
                assert isinstance(node["type"], str)


def test_no_schema_declares_session_id() -> None:
    assert "session_id" not in property_names(tool_text.BOARD_EDIT_SCHEMA)


def test_no_whole_board_property_exists() -> None:
    assert not WHOLE_BOARD_NAMES & property_names(tool_text.BOARD_EDIT_SCHEMA)


def test_tool_names_start_with_board_and_hold_no_todo() -> None:
    for name in (tool_text.BOARD_READ, tool_text.BOARD_EDIT):
        assert name.startswith("board_")
        assert "todo" not in name.lower()


def tool_description(tool: str) -> str:
    schemas = {
        tool_text.BOARD_READ: tool_text.BOARD_READ_SCHEMA,
        tool_text.BOARD_EDIT: tool_text.BOARD_EDIT_SCHEMA,
    }
    return schemas[tool]["description"]


@pytest.mark.parametrize("tool", ["board_read", "board_edit"])
def test_each_description_names_todo_list_once_and_holds_no_other_todo(tool: str) -> None:
    description = tool_description(tool)

    assert todo_check_passes(description)
    assert "memory" in description
    assert "kanban_*" in description


@pytest.mark.parametrize(
    "sample",
    ["Use todo_list and Todo here.", "Keep a TODO. Also todo_list.", "No boundary here."],
)
def test_todo_check_fails_on_other_spellings(sample: str) -> None:
    assert not todo_check_passes(sample)


def test_board_edit_first_sentence() -> None:
    sentence = first_sentence(tool_text.BOARD_EDIT_SCHEMA["description"])

    assert sentence == EDIT_FIRST_SENTENCE
    assert len(sentence) == 56
    assert sentence_fits(sentence)


def test_first_sentence_boundary() -> None:
    assert sentence_fits("a" * 59 + ".")
    assert not sentence_fits("a" * 60 + ".")


@pytest.mark.parametrize("phrase", EDIT_KEY_PHRASES)
def test_board_edit_description_carries_the_rules(phrase: str) -> None:
    assert phrase in tool_text.BOARD_EDIT_SCHEMA["description"]


SECTION_ID_RULE = re.compile(r"^[a-z0-9._-]{1,128}$")
SKILL_NAME_RULE = re.compile(r"^[a-zA-Z0-9_-]+$")
SECTION_PHRASES = (*EDIT_KEY_PHRASES[:5], "not instructions")
ORDERED_PHRASES = ("Theo must do, decide or remember", "todo_list", "Ask Theo one plain question")
SECTION_HARD_CAP = 4000
SECTION_TEXT_LIMIT = 1000
EM_DASH = "—"
EN_DASH = "–"


def skill_parts() -> tuple[str, str]:
    """Split SKILL.md into its frontmatter block and its body."""
    text = wiring.skill_path().read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---\n", 2)
    return frontmatter, body


def test_prompt_section_id_is_valid() -> None:
    assert SECTION_ID_RULE.match(tool_text.PROMPT_SECTION_ID)
    assert tool_text.PROMPT_SECTION_ID == "hermes-session-tasks.board-rules"


def test_prompt_section_text_is_static_and_small() -> None:
    text = tool_text.PROMPT_SECTION_TEXT

    assert isinstance(text, str)
    assert len(text) < SECTION_TEXT_LIMIT
    assert len(text) <= tool_text.PROMPT_SECTION_MAX
    assert tool_text.PROMPT_SECTION_MAX <= SECTION_HARD_CAP


@pytest.mark.parametrize("phrase", SECTION_PHRASES)
def test_prompt_section_and_skill_carry_every_key_phrase(phrase: str) -> None:
    assert phrase in tool_text.PROMPT_SECTION_TEXT
    assert phrase in skill_parts()[1]


def test_rules_come_in_order() -> None:
    for text in (tool_text.PROMPT_SECTION_TEXT, skill_parts()[1]):
        trigger, boundary, ask = (text.index(phrase) for phrase in ORDERED_PHRASES)
        assert trigger < boundary < ask


def test_skill_frontmatter() -> None:
    frontmatter, body = skill_parts()
    lines = frontmatter.splitlines()

    assert "name: board-rules" in lines
    assert f"description: {tool_text.SKILL_DESCRIPTION}" in lines
    assert tool_text.SKILL_NAME == "board-rules"
    assert SKILL_NAME_RULE.match(tool_text.SKILL_NAME)
    assert body.strip()


def test_skill_path_exists() -> None:
    assert wiring.skill_path().is_file()


def test_no_em_or_en_dash_in_tool_text_or_skill() -> None:
    for path in (Path(tool_text.__file__), wiring.skill_path()):
        text = path.read_text(encoding="utf-8")
        assert EM_DASH not in text
        assert EN_DASH not in text
