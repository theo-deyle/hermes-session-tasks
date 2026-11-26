"""Tool text rules: name prefix, the todo boundary, the 60 character first sentence."""

from __future__ import annotations

import hashlib
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
    assert sentence == "Read the user's task board with item ids and the revision."


def test_board_read_schema_declares_an_optional_session_id() -> None:
    parameters = tool_text.BOARD_READ_SCHEMA["parameters"]

    assert parameters["properties"]["session_id"]["type"] == "string"
    assert set(parameters["properties"]) == {"session_id"}
    assert "required" not in parameters


def test_first_sentence_helper_stops_at_the_first_period_and_space() -> None:
    assert first_sentence("One. Two.") == "One."
    assert first_sentence("No end") == "No end"


EDIT_FIRST_SENTENCE = "Add to the board what the user must do, decide or remember."
EDIT_KEY_PHRASES = (
    "the user must do, decide or remember",
    "todo_list",
    "Ask the user one plain question",
    "confirmed true",
    "check it and tell the user in one line",
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


ALL_SCHEMAS = (
    tool_text.BOARD_READ_SCHEMA,
    tool_text.BOARD_EDIT_SCHEMA,
    tool_text.BOARD_SESSIONS_SCHEMA,
    tool_text.BOARD_COPY_SCHEMA,
)
PROMPT_SECTION_SHA256 = "1152f59e1f3fb469e08022149a7b026788e243450e4cb1ac00e9adb04b2ab636"
SESSIONS_FIRST_SENTENCE = "List the sessions that have a task board."
COPY_FIRST_SENTENCE = "Copy items from another session's board."


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
    for schema in ALL_SCHEMAS:
        for node in schema_nodes(schema):
            assert not COMBINATOR_KEYS & set(node)
            if "type" in node:
                assert isinstance(node["type"], str)


def test_no_schema_declares_session_id() -> None:
    assert "session_id" not in property_names(tool_text.BOARD_EDIT_SCHEMA)
    assert "session_id" not in property_names(tool_text.BOARD_COPY_SCHEMA)


def test_board_copy_schema_shape() -> None:
    parameters = tool_text.BOARD_COPY_SCHEMA["parameters"]
    item_ids = parameters["properties"]["item_ids"]

    assert tool_text.BOARD_COPY_SCHEMA["name"] == tool_text.BOARD_COPY == "board_copy"
    assert set(parameters["properties"]) == {"from_session_id", "item_ids"}
    assert parameters["properties"]["from_session_id"]["type"] == "string"
    assert parameters["required"] == ["from_session_id"]
    assert item_ids["type"] == "array"
    assert item_ids["items"] == {"type": "integer"}
    assert item_ids["maxItems"] == 100


def test_board_sessions_schema_has_no_property() -> None:
    parameters = tool_text.BOARD_SESSIONS_SCHEMA["parameters"]

    assert tool_text.BOARD_SESSIONS_SCHEMA["name"] == tool_text.BOARD_SESSIONS == "board_sessions"
    assert parameters == {"type": "object", "properties": {}}


def test_new_first_sentences_fit_the_catalog_limit() -> None:
    sessions = first_sentence(tool_text.BOARD_SESSIONS_SCHEMA["description"])
    copy = first_sentence(tool_text.BOARD_COPY_SCHEMA["description"])

    assert (sessions, copy) == (SESSIONS_FIRST_SENTENCE, COPY_FIRST_SENTENCE)
    assert sentence_fits(sessions)
    assert sentence_fits(copy)


def test_copy_is_only_on_theo_request() -> None:
    assert "Use it only when the user asks you to copy" in tool_text.BOARD_COPY_DESCRIPTION
    assert "only when the user asks" in skill_parts()[1]


def test_board_read_names_the_other_board_rule() -> None:
    description = tool_text.BOARD_READ_DESCRIPTION

    assert "read only" in description
    assert "not a base_rev" in description


def test_prompt_section_is_unchanged() -> None:
    digest = hashlib.sha256(tool_text.PROMPT_SECTION_TEXT.encode()).hexdigest()

    assert digest == PROMPT_SECTION_SHA256


def test_skill_names_the_four_tools() -> None:
    body = skill_parts()[1]

    for name in ("board_sessions", "board_copy", "board_read", "board_edit"):
        assert name in body
    assert "## Other sessions' boards" in body


def test_tool_texts_hold_no_count_session_id_or_date() -> None:
    for schema in ALL_SCHEMAS:
        text = str(schema)
        assert not re.search(r"\d{4}-\d{2}-\d{2}", text)
        assert not re.search(r"\bs\d\b", text)


def test_no_whole_board_property_exists() -> None:
    assert not WHOLE_BOARD_NAMES & property_names(tool_text.BOARD_EDIT_SCHEMA)


def test_tool_names_start_with_board_and_hold_no_todo() -> None:
    names = (
        tool_text.BOARD_READ,
        tool_text.BOARD_EDIT,
        tool_text.BOARD_SESSIONS,
        tool_text.BOARD_COPY,
    )
    for name in names:
        assert name.startswith("board_")
        assert "todo" not in name.lower()


def tool_description(tool: str) -> str:
    schemas = {schema["name"]: schema for schema in ALL_SCHEMAS}
    return str(schemas[tool]["description"])


@pytest.mark.parametrize("tool", ["board_read", "board_edit", "board_sessions", "board_copy"])
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
    assert len(sentence) == 59
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
PLAN_RULE = "When a job takes 3 or more steps, add your steps to the board first"
PLAN_CHECK_OFF = PLAN_RULE + ", then check each one off as you finish it."
BOTH_RULE = "The board holds the user's reminders and your plan together."
NOT_BOARD = "not todo_list, not memory, and not the kanban_* tools"
RETIRED_PLAN = (
    "working plan",
    "The board is the user's list",
    "the user's notes",
    "It is not your plan",
)
SKILL_DESCRIPTION_TEXT = (
    "Rules for the user's task board. "
    "When to add items, your own plan on the board, and when to ask the user first."
)
ORDERED_PHRASES = (
    "the user must do, decide or remember",
    PLAN_RULE,
    "todo_list",
    "the user's own message",
    "Ask the user one plain question",
)
RULE_EXPLICIT = "the user's own message"
RULE_OWN = "decide on your own"
AT_ONCE = "Do it at once with confirmed true"
ASK_ONLY = "Ask the user one plain question first only in two cases"
NO_SHORTCUT = "on your own decision"
RETIRED_ASK = "plain question before you"
CONFIRMED_DESCRIPTION = (
    "Set true when the user's own message named this remove, uncheck or reword, "
    "or after they answered your question about it in chat. "
    "Never set it true on your own decision."
)
SECTION_HARD_CAP = 4000
SECTION_TEXT_LIMIT = 1000
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)


def skill_parts() -> tuple[str, str]:
    """Split SKILL.md into its frontmatter block and its body."""
    text = wiring.skill_path().read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---\n", 2)
    return frontmatter, body


def rule_text(surface: str) -> str:
    """Return the text of one surface that carries the ask rule."""
    if surface == "read":
        return tool_text.BOARD_READ_DESCRIPTION
    if surface == "description":
        return tool_text.BOARD_EDIT_DESCRIPTION
    if surface == "section":
        return tool_text.PROMPT_SECTION_TEXT
    if surface == "skill":
        return skill_parts()[1]
    properties = tool_text.BOARD_EDIT_SCHEMA["parameters"]["properties"]
    return str(properties["confirmed"]["description"])


@pytest.mark.parametrize("surface", ["description", "section", "skill"])
def test_explicit_instruction_rule_is_in_every_rule_text(surface: str) -> None:
    text = rule_text(surface)

    for phrase in (RULE_EXPLICIT, RULE_OWN, AT_ONCE, ASK_ONLY):
        assert phrase in text


@pytest.mark.parametrize("surface", ["description", "section", "skill"])
def test_retired_blanket_ask_rule_is_gone(surface: str) -> None:
    assert RETIRED_ASK not in rule_text(surface)


@pytest.mark.parametrize("surface", ["section", "skill", "confirmed"])
def test_confirmed_true_is_never_set_on_own_decision(surface: str) -> None:
    assert NO_SHORTCUT in rule_text(surface)


def test_confirmed_description_is_exact() -> None:
    assert rule_text("confirmed") == CONFIRMED_DESCRIPTION


@pytest.mark.parametrize("surface", ["description", "section", "skill"])
def test_plan_rule_is_in_every_rule_text(surface: str) -> None:
    assert PLAN_RULE in rule_text(surface)


@pytest.mark.parametrize("surface", ["description", "skill"])
def test_plan_rule_names_the_check_off(surface: str) -> None:
    assert PLAN_CHECK_OFF in rule_text(surface)


@pytest.mark.parametrize("surface", ["read", "description", "skill"])
def test_board_holds_both_lists(surface: str) -> None:
    assert BOTH_RULE in rule_text(surface)


@pytest.mark.parametrize("surface", ["read", "description", "section", "skill"])
def test_board_names_what_it_is_not(surface: str) -> None:
    assert NOT_BOARD in rule_text(surface)


@pytest.mark.parametrize("surface", ["read", "description", "section", "skill"])
def test_retired_plan_text_is_gone(surface: str) -> None:
    text = rule_text(surface)

    for phrase in RETIRED_PLAN:
        assert phrase not in text


def test_skill_description_is_exact() -> None:
    assert tool_text.SKILL_DESCRIPTION == SKILL_DESCRIPTION_TEXT


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
    for surface in ("description", "section", "skill"):
        text = rule_text(surface)
        indexes = [text.index(phrase) for phrase in ORDERED_PHRASES]
        assert indexes == sorted(set(indexes))


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
