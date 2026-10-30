"""Fixed-case tests for the markdown renderer and the checklist parser."""

from __future__ import annotations

from session_tasks.markdown import ParsedItem, ParseResult, parse, render
from session_tasks.model import Board, Item

NOW = "2026-10-30T00:00:00.000000Z"
CAP_LINE = "x" * 500


def item(item_id: int, text: str, *, checked: bool = False, parent_id: int | None = None) -> Item:
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


def board_of(*items: Item) -> Board:
    return Board(root_id="root-1", rev=1, next_item_id=len(items) + 1, items=tuple(items))


def shape(result: ParseResult) -> list[tuple[str, bool, list[tuple[str, bool]]]]:
    """Reduce a parse result to (text, checked, [(child text, child checked)])."""
    return [
        (top.text, top.checked, [(child.text, child.checked) for child in top.children])
        for top in result.items
    ]


def counts(result: ParseResult) -> tuple[int, int, int]:
    return (result.moved, result.skipped_empty, result.too_long)


# render


def test_render_agent_view_shows_ids_and_two_space_subtasks() -> None:
    board = board_of(item(1, "Call John"), item(2, "Book the room", checked=True, parent_id=1))

    assert render(board, include_ids=True) == "- [ ] #1 Call John\n  - [x] #2 Book the room\n"


def test_render_clipboard_view_has_no_ids() -> None:
    board = board_of(item(1, "Call John"), item(2, "Book the room", checked=True, parent_id=1))

    assert render(board, include_ids=False) == "- [ ] Call John\n  - [x] Book the room\n"


def test_render_escapes_text_that_starts_with_a_hash_number() -> None:
    board = board_of(item(1, "#3 priority"), item(2, "#7"), item(3, "\\#12 x"))

    assert render(board, include_ids=False) == (
        "- [ ] \\#3 priority\n- [ ] \\#7\n- [ ] \\\\#12 x\n"
    )
    assert render(board, include_ids=True) == (
        "- [ ] #1 \\#3 priority\n- [ ] #2 \\#7\n- [ ] #3 \\\\#12 x\n"
    )


def test_render_leaves_hash_text_without_the_shape_alone() -> None:
    board = board_of(item(1, "#12abc"), item(2, "x #3"), item(3, "#"))

    assert render(board, include_ids=False) == "- [ ] #12abc\n- [ ] x #3\n- [ ] #\n"


def test_render_empty_board_gives_an_empty_string() -> None:
    assert render(board_of(), include_ids=True) == ""


# parse: line kinds


def test_parse_reads_checked_unchecked_and_uppercase_x() -> None:
    result = parse("- [ ] a\n- [x] b\n- [X] c\n")

    assert shape(result) == [("a", False, []), ("b", True, []), ("c", True, [])]
    assert counts(result) == (0, 0, 0)


def test_parse_reads_plain_dash_star_and_plus_bullets_as_unchecked() -> None:
    result = parse("- dash\n* star\n+ plus\n")

    assert shape(result) == [("dash", False, []), ("star", False, []), ("plus", False, [])]


def test_parse_ignores_headings_paragraphs_numbered_lists_thematic_breaks_and_blank_lines() -> None:
    text = "# Title\n\nsome paragraph\n1. numbered\n---\n- - -\n* * *\n___\n\n- [ ] real\n"

    result = parse(text)

    assert shape(result) == [("real", False, [])]
    assert counts(result) == (0, 0, 0)


def test_parse_treats_a_box_without_a_following_space_as_plain_text() -> None:
    result = parse("- [ ]foo\n")

    assert shape(result) == [("[ ]foo", False, [])]


# parse: ids and escapes


def test_parse_strips_one_id_token_and_records_hint_id() -> None:
    result = parse("- [ ] #3 Call John\n  - [x] #4 #5 nested\n- [ ] #x not an id\n")

    assert result.items[0] == ParsedItem(
        "Call John",
        False,
        3,
        (ParsedItem("#5 nested", True, 4, ()),),
    )
    assert result.items[1] == ParsedItem("#x not an id", False, None, ())


def test_parse_unescapes_exactly_one_backslash() -> None:
    result = parse("- [ ] \\#3 priority\n- [ ] \\\\#12 x\n- [ ] \\#7\n- [ ] \\n kept\n")

    assert [top.text for top in result.items] == ["#3 priority", "\\#12 x", "#7", "\\n kept"]
    assert [top.hint_id for top in result.items] == [None, None, None, None]


# parse: nesting


def test_parse_moves_a_depth_two_line_under_the_nearest_top_level_item() -> None:
    result = parse("- [ ] a\n  - [ ] b\n    - [ ] c\n      - [x] d\n- [ ] e\n")

    assert shape(result) == [
        ("a", False, [("b", False), ("c", False), ("d", True)]),
        ("e", False, []),
    ]
    assert result.moved == 2


def test_parse_does_not_count_a_depth_one_line_as_moved() -> None:
    result = parse("- [ ] a\n  - [ ] b\n")

    assert counts(result) == (0, 0, 0)


def test_parse_makes_an_indented_first_line_top_level() -> None:
    result = parse("    - [ ] a\n  - [ ] b\n    - [ ] c\n")

    assert shape(result) == [("a", False, []), ("b", False, [("c", False)])]
    assert result.moved == 0


# parse: skips


def test_parse_skips_and_counts_empty_text_lines() -> None:
    result = parse("- [ ]\n- [x]\n- [X]\n- [x]    \n- \n- [ ] keep\n")

    assert shape(result) == [("keep", False, [])]
    assert counts(result) == (0, 5, 0)


def test_parse_skips_a_line_that_is_empty_after_sanitising() -> None:
    result = parse("- [ ] \u200b\u200d\n- [ ] ok\n")

    assert shape(result) == [("ok", False, [])]
    assert result.skipped_empty == 1


def test_parse_skips_and_counts_lines_over_500_code_points_and_keeps_importing() -> None:
    text = f"- [ ] first\n- [ ] {CAP_LINE}y\n- [ ] last\n"

    result = parse(text)

    assert shape(result) == [("first", False, []), ("last", False, [])]
    assert counts(result) == (0, 0, 1)


def test_parse_imports_a_line_of_exactly_500_code_points() -> None:
    result = parse(f"- [ ] {CAP_LINE}\n")

    assert shape(result) == [(CAP_LINE, False, [])]
    assert counts(result) == (0, 0, 0)


def test_children_of_a_skipped_parent_become_top_level() -> None:
    result = parse("- [ ]\n  - [ ] a\n  - [x] b\n- [ ] c\n  - [ ] d\n")

    assert shape(result) == [("a", False, []), ("b", True, []), ("c", False, [("d", False)])]
    assert counts(result) == (0, 1, 0)


def test_children_of_a_too_long_parent_become_top_level() -> None:
    result = parse(f"- [ ] {CAP_LINE}z\n  - [ ] a\n")

    assert shape(result) == [("a", False, [])]
    assert counts(result) == (0, 0, 1)


# parse: input forms


def test_parse_accepts_crlf_and_tabs() -> None:
    result = parse("- [ ] a\r\n\t- [x] b\r\n\t\t- [ ] c\r\n")

    assert shape(result) == [("a", False, [("b", True), ("c", False)])]
    assert result.moved == 1


def test_parse_accepts_a_tab_as_four_columns() -> None:
    result = parse("- [ ] a\n    - [ ] b\n\t- [ ] c\n")

    assert shape(result) == [("a", False, [("b", False), ("c", False)])]
    assert result.moved == 0


def test_parse_sanitises_text() -> None:
    result = parse("- [ ] a\u00a0b\u200bc  d\n")

    assert shape(result) == [("a bc d", False, [])]


def test_parse_of_an_empty_string_gives_an_empty_result() -> None:
    assert parse("") == ParseResult((), 0, 0, 0)
