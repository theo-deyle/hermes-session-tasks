"""Seeded random round trip of render and parse, and import planning."""

from __future__ import annotations

import random

import pytest
from session_tasks.markdown import ParseResult, parse, plan_import, render
from session_tasks.model import AddItem, Board, Item, sanitize_text

NOW = "2026-10-30T00:00:00.000000Z"
BOARD_COUNT = 500
TEXT_POOL = (
    "#12 x",
    "#7",
    "\\#12 x",
    "\\\\#3",
    "[x] y",
    "- z",
    "* star",
    "x #3",
    "#12abc",
    "\U0001f600 smile",
    "✅",
    "y" * 500,
    "Call John",
    "Book the room",
    "Order parts",
    "Email the supplier about invoice 4411",
)

Tree = list[tuple[str, bool, list[tuple[str, bool]]]]


def make_item(item_id: int, parent_id: int | None, text: str, checked: bool) -> Item:
    return Item(
        id=item_id,
        parent_id=parent_id,
        position=item_id,
        text=text,
        checked=checked,
        rev=1,
        updated_by="agent",
        created_at=NOW,
        updated_at=NOW,
    )


def random_board(rng: random.Random) -> Board:
    """Build a two-level board in display order with sequential ids."""
    items: list[Item] = []
    next_id = 1
    for _ in range(rng.randint(0, 12)):
        parent_id = next_id
        items.append(make_item(next_id, None, draw_text(rng), rng.random() < 0.5))
        next_id += 1
        for _ in range(rng.randint(0, 3)):
            items.append(make_item(next_id, parent_id, draw_text(rng), rng.random() < 0.5))
            next_id += 1
    return Board("root-1", 1, next_id, tuple(items))


def draw_text(rng: random.Random) -> str:
    # The store only holds sanitised text, so the generator does the same.
    return sanitize_text(rng.choice(TEXT_POOL))


def board_tree(board: Board) -> Tree:
    return [
        (top.text, top.checked, [(sub.text, sub.checked) for sub in board.children(top.id)])
        for top in board.top_level()
    ]


def parsed_tree(result: ParseResult) -> Tree:
    return [
        (top.text, top.checked, [(sub.text, sub.checked) for sub in top.children])
        for top in result.items
    ]


def checklist(count: int, *, subtasks_per_item: int = 0) -> str:
    lines: list[str] = []
    for number in range(count):
        lines.append(f"- [ ] item {number}")
        lines.extend(f"  - [x] sub {number}.{sub}" for sub in range(subtasks_per_item))
    return "\n".join(lines) + "\n"


def test_plan_import_links_subtasks_with_parent_ref_in_display_order() -> None:
    result = parse("- [ ] a\n  - [x] b\n  - [ ] c\n- [x] d\n  - [ ] e\n")

    plan = plan_import(result, 100)

    assert plan.overflow == 0
    assert plan.ops == (
        AddItem("a", False),
        AddItem("b", True, parent_ref=0),
        AddItem("c", False, parent_ref=0),
        AddItem("d", True),
        AddItem("e", False, parent_ref=3),
    )


def test_plan_import_with_capacity_equal_to_the_count_has_no_overflow() -> None:
    result = parse(checklist(4, subtasks_per_item=1))

    plan = plan_import(result, 8)

    assert len(plan.ops) == 8
    assert plan.overflow == 0


def test_plan_import_with_zero_capacity_returns_no_ops_and_counts_every_item() -> None:
    result = parse(checklist(3, subtasks_per_item=2))

    plan = plan_import(result, 0)

    assert plan.ops == ()
    assert plan.overflow == 9


def test_plan_import_cut_never_leaves_a_subtask_without_its_parent() -> None:
    result = parse(checklist(3, subtasks_per_item=2))

    for capacity in range(10):
        plan = plan_import(result, capacity)

        assert len(plan.ops) + plan.overflow == 9
        assert len(plan.ops) == min(capacity, 9)
        for index, op in enumerate(plan.ops):
            if op.parent_ref is not None:
                assert op.parent_ref < index
                assert plan.ops[op.parent_ref].parent_ref is None


def test_plan_import_keeps_checked_state() -> None:
    plan = plan_import(parse("- [x] done\n- [ ] open\n- plain\n"), 10)

    assert [op.checked for op in plan.ops] == [True, False, False]


def test_plan_import_rejects_negative_capacity() -> None:
    with pytest.raises(ValueError, match="negative"):
        plan_import(parse("- [ ] a\n"), -1)


def test_plan_import_of_an_empty_result_has_no_ops_and_no_overflow() -> None:
    plan = plan_import(parse(""), 5)

    assert plan.ops == ()
    assert plan.overflow == 0


def test_a_501_code_point_line_does_not_stop_the_import_of_the_next_line() -> None:
    text = f"- [ ] {'z' * 500}\n- [ ] {'z' * 501}\n- [ ] after\n"

    result = parse(text)
    plan = plan_import(result, 100)

    assert result.too_long == 1
    assert [op.text for op in plan.ops] == ["z" * 500, "after"]
    assert plan.overflow == 0


def test_500_random_boards_round_trip_with_ids_on() -> None:
    rng = random.Random(1234)

    for _ in range(BOARD_COUNT):
        board = random_board(rng)

        result = parse(render(board, include_ids=True))

        assert parsed_tree(result) == board_tree(board)
        assert (result.moved, result.skipped_empty, result.too_long) == (0, 0, 0)
        expected_ids = [item.id for item in board.items if item.parent_id is None]
        assert [top.hint_id for top in result.items] == expected_ids
        for top in result.items:
            sub_ids = [item.id for item in board.items if item.parent_id == top.hint_id]
            assert [sub.hint_id for sub in top.children] == sub_ids


def test_500_random_boards_round_trip_with_ids_off() -> None:
    rng = random.Random(1234)

    for _ in range(BOARD_COUNT):
        board = random_board(rng)

        result = parse(render(board, include_ids=False))

        assert parsed_tree(result) == board_tree(board)
        assert (result.moved, result.skipped_empty, result.too_long) == (0, 0, 0)
        assert all(top.hint_id is None for top in result.items)


def test_hint_id_parses_an_18_digit_run_and_gives_none_for_a_longer_run() -> None:
    longest = "9" * 18
    text = f"- [ ] #{longest} ok\n- [ ] #{'9' * 19} long\n- [ ] #{'7' * 5000} huge\n"

    result = parse(text)

    assert [(top.text, top.hint_id) for top in result.items] == [
        ("ok", int(longest)),
        ("long", None),
        ("huge", None),
    ]


def test_stored_text_survives_a_round_trip_unchanged() -> None:
    texts = ["#3 x", "#7", "\\#12 x", "\\\\#3", "[x] y", "- z", "\U0001f600", "✅ done"]
    items = tuple(make_item(index + 1, None, text, False) for index, text in enumerate(texts))
    board = Board("root-1", 1, len(items) + 1, items)

    for include_ids in (True, False):
        result = parse(render(board, include_ids=include_ids))

        assert [top.text for top in result.items] == texts
