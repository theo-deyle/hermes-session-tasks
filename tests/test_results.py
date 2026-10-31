"""Result strings: failures carry a top-level `error`, successes never do."""

from __future__ import annotations

import json

from session_tasks.model import Board, BoardError
from session_tasks.results import describe, error_result, read_result

EMPTY_BOARD = Board(root_id="s1", rev=0, next_item_id=1, items=())


def test_describe_names_the_operation_when_the_error_has_one() -> None:
    assert describe(BoardError("item text is empty", 2)) == "op 2: item text is empty"


def test_describe_gives_the_rule_alone_when_the_error_has_no_operation() -> None:
    assert describe(BoardError("a board holds at most 100 items")) == (
        "a board holds at most 100 items"
    )


def test_error_result_holds_exactly_one_key_named_error() -> None:
    assert json.loads(error_result("nope")) == {"error": "nope"}


def test_read_result_has_no_error_key() -> None:
    assert "error" not in json.loads(read_result(EMPTY_BOARD))


def test_error_result_keeps_non_ascii_text_readable() -> None:
    assert "café" in error_result("café")
