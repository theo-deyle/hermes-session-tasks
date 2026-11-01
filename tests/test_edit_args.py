"""The board_edit argument parser: raw and coerced forms, op mapping, errors and base_rev."""

from __future__ import annotations

import json
from typing import Any

import pytest
from session_tasks.edit_args import MAX_OPS, OP_FIELDS, EditArgsError, ParsedEdit, parse
from session_tasks.model import AddItem, BoardError, RemoveItem, SetChecked, SetText

OPS: list[dict[str, Any]] = [
    {"op": "add", "text": "Call John"},
    {"op": "set_text", "item_id": 3, "text": "Call John today"},
    {"op": "set_checked", "item_id": 3, "checked": True},
    {"op": "remove", "item_id": 4},
]


def raises(args: dict[str, Any]) -> EditArgsError:
    with pytest.raises(EditArgsError) as info:
        parse(args)
    return info.value


def test_parse_maps_each_op_kind_to_its_dataclass() -> None:
    parsed = parse({"ops": OPS, "base_rev": 5})

    assert parsed.ops == (
        AddItem("Call John"),
        SetText(3, "Call John today"),
        SetChecked(3, True),
        RemoveItem(4),
    )
    assert parsed.base_rev == 5
    assert parsed.confirmed is False


def test_parse_reads_parent_id_and_parent_ref_on_add() -> None:
    ops = [
        {"op": "add", "text": "Parent"},
        {"op": "add", "text": "Child", "parent_ref": 0},
        {"op": "add", "text": "Sub", "parent_id": 2, "checked": True},
    ]

    parsed = parse({"ops": ops, "base_rev": 1})

    assert parsed.ops == (
        AddItem("Parent"),
        AddItem("Child", parent_ref=0),
        AddItem("Sub", checked=True, parent_id=2),
    )


def test_op_fields_is_an_immutable_mapping() -> None:
    assert set(OP_FIELDS) == {"add", "set_text", "set_checked", "remove"}
    with pytest.raises(TypeError):
        OP_FIELDS["add"] = frozenset()  # type: ignore[index]


RAW_PAIRS = [
    ({"ops": OPS, "base_rev": 5}, {"ops": json.dumps(OPS), "base_rev": 5}),
    (
        {"ops": [{"op": "add", "text": "a"}]},
        {"ops": {"op": "add", "text": "a"}},
    ),
    (
        {"ops": [{"op": "add", "text": "a"}]},
        {"ops": [json.dumps({"op": "add", "text": "a"})]},
    ),
    ({"ops": OPS, "base_rev": 4}, {"ops": OPS, "base_rev": "4"}),
    (
        {"ops": [], "confirmed": True},
        {"ops": [], "confirmed": "true"},
    ),
    ({"ops": [], "confirmed": True}, {"ops": [], "confirmed": "True"}),
    ({"ops": [], "confirmed": True}, {"ops": [], "confirmed": "TRUE"}),
    (
        {"ops": [{"op": "add", "text": "a", "checked": False}]},
        {"ops": [{"op": "add", "text": "a", "checked": "false"}]},
    ),
    (
        {"ops": [{"op": "remove", "item_id": 3}], "base_rev": 1},
        {"ops": [{"op": "remove", "item_id": "3"}], "base_rev": 1},
    ),
]


@pytest.mark.parametrize(("coerced", "raw"), RAW_PAIRS)
def test_raw_and_coerced_forms_give_equal_results(
    coerced: dict[str, Any], raw: dict[str, Any]
) -> None:
    assert parse(raw) == parse(coerced)


def test_missing_ops_raises() -> None:
    for args in ({}, {"ops": None}):
        error = raises(args)
        assert "ops" in str(error)
        assert error.op_index is None


def test_empty_ops_parses_to_an_empty_tuple() -> None:
    assert parse({"ops": []}) == ParsedEdit(ops=(), base_rev=None, confirmed=False)


@pytest.mark.parametrize("ops", ["not json", 7, "[1", '"text"'])
def test_ops_that_are_not_a_list_raise(ops: object) -> None:
    error = raises({"ops": ops})

    assert str(error) == "ops must be a JSON list of operations"


def test_element_that_is_not_an_object_raises_with_the_index() -> None:
    error = raises({"ops": [{"op": "add", "text": "a"}, 5]})

    assert error.op_index == 1
    assert "an operation must be an object" in str(error)


def test_unknown_op_kind_raises_with_the_op_index() -> None:
    error = raises({"ops": [{"op": "add", "text": "a"}, {"op": "clear"}]})

    assert error.op_index == 1
    assert "op must be one of add, set_text, set_checked, remove" in str(error)


def test_unknown_field_raises_with_the_op_index() -> None:
    error = raises({
        "ops": [{"op": "add", "text": "a"}, {"op": "remove", "item_id": 3, "text": "x"}]
    })

    assert error.op_index == 1
    assert "unknown field 'text' for remove" in str(error)


def test_unknown_field_reports_the_first_in_sorted_order() -> None:
    error = raises({"ops": [{"op": "add", "text": "a", "zeta": 1, "alpha": 2}]})

    assert "unknown field 'alpha' for add" in str(error)


@pytest.mark.parametrize(
    "op",
    [
        {"op": "remove", "item_id": True},
        {"op": "add", "text": "a", "parent_ref": False},
        {"op": "remove", "item_id": 1.5},
        {"op": "remove", "item_id": "x"},
        {"op": "remove", "item_id": "-3"},
    ],
)
def test_bool_or_other_non_integer_where_a_whole_number_belongs_raises(
    op: dict[str, Any],
) -> None:
    error = raises({"ops": [op], "base_rev": 1})

    assert "must be a whole number" in str(error)
    assert error.op_index == 0


@pytest.mark.parametrize(
    "op",
    [
        {"op": "remove", "item_id": 10**30},
        pytest.param({"op": "remove", "item_id": "9" * 5000}, id="5000-digit-string"),
        {"op": "remove", "item_id": 2**63},
        {"op": "add", "text": "a", "parent_id": 10**30},
        {"op": "add", "text": "a", "parent_ref": 10**30},
        {"op": "remove", "item_id": -5},
    ],
)
def test_integers_outside_the_sqlite_range_raise_a_whole_number_error(
    op: dict[str, Any],
) -> None:
    error = raises({"ops": [{"op": "add", "text": "first"}, op], "base_rev": 1})

    assert "must be a whole number" in str(error)
    assert error.op_index == 1


def test_the_largest_sqlite_integer_still_parses() -> None:
    parsed = parse({"ops": [{"op": "remove", "item_id": 2**63 - 1}], "base_rev": 2**63 - 1})

    assert parsed.ops == (RemoveItem(2**63 - 1),)
    assert parsed.base_rev == 2**63 - 1


@pytest.mark.parametrize(
    "base_rev", [10**30, pytest.param("9" * 5000, id="5000-digit-string"), 2**63]
)
def test_base_rev_outside_the_sqlite_range_raises_even_on_an_add_only_call(
    base_rev: object,
) -> None:
    error = raises({"ops": [{"op": "add", "text": "a"}], "base_rev": base_rev})

    assert str(error) == "base_rev must be a whole number of 0 or more"


@pytest.mark.parametrize(
    "op",
    [
        {"op": "remove", "item_id": 0},
        {"op": "add", "text": "a", "parent_id": -1},
        {"op": "add", "text": "a", "parent_ref": -1},
    ],
)
def test_negative_or_zero_ids_raise(op: dict[str, Any]) -> None:
    error = raises({"ops": [op], "base_rev": 1})

    assert error.op_index == 0


def test_parent_ref_zero_is_valid() -> None:
    parsed = parse({"ops": [{"op": "add", "text": "a", "parent_ref": 0}]})

    assert parsed.ops == (AddItem("a", parent_ref=0),)


@pytest.mark.parametrize("text", [5, None, ["a"]])
def test_text_that_is_not_a_string_raises(text: object) -> None:
    error = raises({"ops": [{"op": "add", "text": text}]})

    assert error.op_index == 0


def test_missing_required_field_names_the_kind_and_field() -> None:
    error = raises({"ops": [{"op": "set_checked", "item_id": 3}], "base_rev": 1})

    assert "set_checked needs checked" in str(error)
    assert error.op_index == 0


def test_more_than_max_ops_raises_and_the_cap_itself_parses() -> None:
    adds = [{"op": "add", "text": "a"}] * (MAX_OPS + 1)

    error = raises({"ops": adds})
    assert str(error) == f"at most {MAX_OPS} operations per call"
    assert error.op_index is None
    assert len(parse({"ops": adds[:MAX_OPS]}).ops) == MAX_OPS


@pytest.mark.parametrize(
    "op",
    [
        {"op": "set_text", "item_id": 3, "text": "x"},
        {"op": "set_checked", "item_id": 3, "checked": True},
        {"op": "remove", "item_id": 3},
        {"op": "add", "text": "x", "parent_id": 3},
    ],
)
def test_base_rev_required_when_an_op_targets_an_existing_item(op: dict[str, Any]) -> None:
    error = raises({"ops": [{"op": "add", "text": "first"}, op]})

    assert error.op_index == 1
    assert "base_rev is required" in str(error)
    assert "board_read" in str(error)


def test_top_level_and_parent_ref_adds_need_no_base_rev() -> None:
    ops = [{"op": "add", "text": "a"}, {"op": "add", "text": "b", "parent_ref": 0}]

    assert parse({"ops": ops}).base_rev is None


@pytest.mark.parametrize("base_rev", [-1, True, "x", 1.5, "-2"])
def test_bad_base_rev_raises(base_rev: object) -> None:
    error = raises({"ops": [], "base_rev": base_rev})

    assert str(error) == "base_rev must be a whole number of 0 or more"


@pytest.mark.parametrize("confirmed", ["yes", 1, 0, "1"])
def test_bad_confirmed_raises(confirmed: object) -> None:
    error = raises({"ops": [], "confirmed": confirmed})

    assert "confirmed must be true or false" in str(error)


def test_none_for_an_optional_field_counts_as_absent() -> None:
    parsed = parse({"ops": [{"op": "add", "text": "a", "parent_id": None, "checked": None}]})

    assert parsed.ops == (AddItem("a"),)


def test_none_for_a_required_field_raises() -> None:
    error = raises({"ops": [{"op": "remove", "item_id": None}], "base_rev": 1})

    assert "remove needs item_id" in str(error)


def test_unknown_top_level_keys_are_ignored() -> None:
    plain = parse({"ops": OPS, "base_rev": 2})

    assert parse({"ops": OPS, "base_rev": 2, "session_id": "evil"}) == plain


def test_edit_args_error_is_a_board_error() -> None:
    assert issubclass(EditArgsError, BoardError)


def test_parse_does_not_clean_text() -> None:
    parsed = parse({"ops": [{"op": "add", "text": "  spaced \n out  "}]})

    assert parsed.ops == (AddItem("  spaced \n out  "),)
