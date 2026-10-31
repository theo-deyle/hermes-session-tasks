"""Result strings: failures carry a top-level `error`, successes never do."""

from __future__ import annotations

import json

import pytest
from session_tasks.model import (
    AddItem,
    Applied,
    Board,
    BoardError,
    Item,
    Op,
    RemoveItem,
    SetChecked,
    SetText,
    Stale,
)
from session_tasks.results import (
    applied_result,
    describe,
    error_result,
    read_result,
    stale_result,
    summary_line,
)

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


def item(
    item_id: int, text: str = "t", *, checked: bool = False, parent: int | None = None
) -> Item:
    return Item(item_id, parent, item_id, text, checked, 1, "agent", "t0", "t0")


def test_summary_line_counts_each_kind_in_fixed_order() -> None:
    ops: list[Op] = [
        RemoveItem(9),
        SetChecked(2, False),
        SetChecked(3, True),
        SetText(1, "x"),
        AddItem("a"),
        AddItem("b"),
    ]

    line = summary_line(7, ops, (1, 2, 3, 9, 10, 11))

    assert (
        line
        == "rev 7: added 2 items, renamed 1 item, checked 1 item, unchecked 1 item, removed 1 item"
    )


def test_summary_line_with_no_changed_ids_says_no_change() -> None:
    assert summary_line(4, [SetChecked(1, True)], ()) == "rev 4: no change"


def test_applied_result_is_a_str_without_error_or_board() -> None:
    board = Board("s1", 1, 2, (item(1, "Call John"),))

    out = applied_result(Applied(board, 1, (1,)), [AddItem("Call John")])

    assert isinstance(out, str)
    data = json.loads(out)
    assert data["ok"] is True
    assert "error" not in data
    assert "board" not in data


def test_applied_result_escapes_text_that_looks_like_an_id() -> None:
    board = Board("s1", 1, 2, (item(1, "#5 sneaky"),))

    data = json.loads(applied_result(Applied(board, 1, (1,)), [AddItem("#5 sneaky")]))

    assert data["changed"] == ["- [ ] #1 \\#5 sneaky"]


def test_stale_result_is_a_str_with_an_error_key() -> None:
    board = Board("s1", 3, 2, (item(1),))

    out = stale_result(Stale(board, "stale", 2, None), 1)

    assert isinstance(out, str)
    data = json.loads(out)
    assert data["error"] == "stale: the board changed after rev 1 (op 2)"
    assert data["rev"] == 3
    assert data["stale"] is True


@pytest.mark.parametrize("reason", ["stale", "not_found"])
def test_stale_result_always_holds_the_current_board(reason: str) -> None:
    board = Board("s1", 3, 2, (item(1, "one"),))

    data = json.loads(stale_result(Stale(board, reason, 0, 1), 2))  # pyright: ignore[reportArgumentType]

    assert data["board"] == "- [ ] #1 one\n"
    assert data["reason"] == reason
