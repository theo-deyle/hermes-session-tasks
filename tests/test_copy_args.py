"""Arguments of board_copy and the target of board_read: forms, limits and errors."""

from __future__ import annotations

from session_tasks.copy_args import CopyArgs, parse, read_target


def test_parse_reads_the_three_arguments() -> None:
    parsed = parse({"from_session_id": " s2 ", "item_ids": [3, 1, 3], "base_rev": 4})

    assert parsed == CopyArgs("s2", (3, 1), 4)


def test_parse_without_item_ids_means_every_open_item() -> None:
    assert parse({"from_session_id": "s2"}) == CopyArgs("s2", None, None)


def test_read_target_names_another_board() -> None:
    assert read_target({"session_id": "s2"}) == "s2"
    assert read_target({}) is None
