"""Arguments of board_copy and the target of board_read: forms, limits and errors."""

from __future__ import annotations

from typing import Any

import pytest
from session_tasks import edit_args
from session_tasks.copy_args import (
    FROM_REQUIRED,
    ITEM_IDS_BAD,
    ITEM_IDS_EMPTY,
    SESSION_ID_MAX,
    TARGET_BAD,
    CopyArgs,
    CopyArgsError,
    parse,
    read_target,
)


def raises(args: dict[str, Any]) -> CopyArgsError:
    with pytest.raises(CopyArgsError) as info:
        parse(args)
    return info.value


def test_parse_reads_the_three_arguments() -> None:
    parsed = parse({"from_session_id": " s2 ", "item_ids": [3, 1, 3], "base_rev": 4})

    assert parsed == CopyArgs("s2", (3, 1), 4)


def test_parse_without_item_ids_means_every_open_item() -> None:
    assert parse({"from_session_id": "s2"}) == CopyArgs("s2", None, None)


def test_read_target_names_another_board() -> None:
    assert read_target({"session_id": "s2"}) == "s2"
    assert read_target({}) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("[2, 5]", (2, 5)), (5, (5,)), ("5", (5,)), (["2", 5], (2, 5))],
)
def test_item_ids_accept_the_coerced_forms(raw: object, expected: tuple[int, ...]) -> None:
    assert parse({"from_session_id": "s2", "item_ids": raw}).item_ids == expected


@pytest.mark.parametrize("raw", [[], "[]"])
def test_empty_item_ids_list_is_an_error(raw: object) -> None:
    assert str(raises({"from_session_id": "s2", "item_ids": raw})) == ITEM_IDS_EMPTY


@pytest.mark.parametrize("raw", [{"a": 1}, "x", 1.5])
def test_item_ids_of_another_shape_are_an_error(raw: object) -> None:
    assert str(raises({"from_session_id": "s2", "item_ids": raw})) == ITEM_IDS_BAD


@pytest.mark.parametrize("bad", [True, 0, -2, 2.0, None])
def test_bad_ids_name_their_index(bad: object) -> None:
    error = raises({"from_session_id": "s2", "item_ids": [1, bad]})

    assert "item_ids[1]" in str(error)


def test_more_than_100_ids_is_an_error() -> None:
    error = raises({"from_session_id": "s2", "item_ids": list(range(1, 102))})

    assert "at most 100 item ids per call" in str(error)
    assert (
        len(parse({"from_session_id": "s2", "item_ids": list(range(1, 101))}).item_ids or ()) == 100
    )
    repeated = [n % 100 + 1 for n in range(150)]
    assert len(parse({"from_session_id": "s2", "item_ids": repeated}).item_ids or ()) == 100


def test_a_raw_list_over_1000_entries_is_refused_before_the_loop() -> None:
    error = raises({"from_session_id": "s2", "item_ids": [1] * 1001})

    assert "at most 100 item ids per call" in str(error)


@pytest.mark.parametrize("value", ["missing", "", "   ", 7, None])
def test_from_session_id_rules(value: object) -> None:
    args: dict[str, Any] = {} if value == "missing" else {"from_session_id": value}

    assert str(raises(args)) == FROM_REQUIRED


def test_from_session_id_length_limit() -> None:
    error = raises({"from_session_id": "x" * (SESSION_ID_MAX + 1)})

    assert "at most 256 characters" in str(error)
    assert parse({"from_session_id": "x" * SESSION_ID_MAX}).from_session_id == "x" * 256


@pytest.mark.parametrize("bad", [True, -1, "x"])
def test_base_rev_rules(bad: object) -> None:
    assert str(raises({"from_session_id": "s2", "base_rev": bad})) == edit_args.BASE_REV_BAD


def test_base_rev_text_digits_and_absent() -> None:
    assert parse({"from_session_id": "s2", "base_rev": "7"}).base_rev == 7
    assert parse({"from_session_id": "s2"}).base_rev is None


def test_other_keys_are_ignored() -> None:
    args = {"from_session_id": "s2", "session_id": "s9", "confirmed": True}

    assert parse(args) == CopyArgs("s2", None, None)


def test_read_target_rules() -> None:
    assert read_target({"session_id": "  "}) is None
    for bad in (5, ["s2"]):
        with pytest.raises(CopyArgsError) as info:
            read_target({"session_id": bad})
        assert str(info.value) == TARGET_BAD
    with pytest.raises(CopyArgsError, match="at most 256 characters"):
        read_target({"session_id": "x" * (SESSION_ID_MAX + 1)})
    assert read_target({"session_id": "x" * SESSION_ID_MAX}) == "x" * SESSION_ID_MAX
