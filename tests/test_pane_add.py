"""The pane add lines: the main add line, the plus button and the subtask add line."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pane_rig import Rig, checkbox, posts, the_input
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

ADD = "Add an item"
ENTER = "Enter"


def add_line(text: str) -> dict[str, object]:
    return {"type": {"input": {"placeholder": ADD}, "text": text}}


def press(key: str, placeholder: str = ADD, row: str | None = None) -> dict[str, object]:
    selector: dict[str, str] = {"placeholder": placeholder}
    if row is not None:
        selector["row"] = row
    return {"key": {"input": selector, "key": key}}


def texts(store: BoardStore, sid: str = "s1") -> list[str]:
    return [item.text for item in store.get_board(sid).items]


def test_enter_adds_and_the_line_is_ready_for_the_next(rig: Rig, tmp_path: Path) -> None:
    steps = [add_line("Call John"), press(ENTER), add_line("Email Ann"), press(ENTER)]

    result = rig.run(tmp_path, steps=steps)

    sent = posts(result)
    assert [call["body"]["ops"] for call in sent] == [
        [{"op": "add", "text": "Call John"}],
        [{"op": "add", "text": "Email Ann"}],
    ]
    assert [call["body"]["base_rev"] for call in sent] == [0, 1]
    board = rig.store.get_board("s1")
    assert [item.text for item in board.items] == ["Call John", "Email Ann"]
    assert {item.updated_by for item in board.items} == {"user"}
    line = the_input(result, placeholder=ADD)
    assert line["value"] == ""
    assert line["readOnly"] is False


def test_new_item_shows_at_once_and_the_line_waits(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, steps=[add_line("Call John"), press(ENTER)])

    held = result["atWrite"][0]
    line = [entry for entry in held["inputs"] if entry["placeholder"] == ADD]
    assert len(line) == 1
    assert line[0]["value"] == "Call John"
    assert line[0]["readOnly"] is True
    pending = [box for box in held["checkboxes"] if box["row"] == "pending"]
    assert len(pending) == 1
    assert pending[0]["label"] == "Call John"
    assert pending[0]["disabled"] is True
    assert checkbox(result, "1")["label"] == "Call John"


FAILED_NOTICE = "Could not save that change. Try again."
EMPTY_TITLE = "The agent adds items here."


def test_add_trims_and_ignores_blank_text(rig: Rig, tmp_path: Path) -> None:
    blank = rig.run(tmp_path, steps=[add_line("   "), press(ENTER)])
    padded = rig.run(tmp_path, steps=[add_line("  Call John  "), press(ENTER)])

    assert posts(blank) == []
    assert [call["body"]["ops"] for call in posts(padded)] == [[{"op": "add", "text": "Call John"}]]
    assert texts(rig.store) == ["Call John"]


def test_escape_clears_and_blur_keeps(rig: Rig, tmp_path: Path) -> None:
    escaped = rig.run(tmp_path, steps=[add_line("Draft"), press("Escape")])
    blurred = rig.run(tmp_path, steps=[add_line("Draft"), {"blur": {"placeholder": ADD}}])

    assert the_input(escaped, placeholder=ADD)["value"] == ""
    assert the_input(blurred, placeholder=ADD)["value"] == "Draft"
    assert posts(escaped) == []
    assert posts(blurred) == []


def test_add_line_limits(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path)

    line = the_input(result, placeholder=ADD)
    assert line["maxLength"] == 500
    assert line["size"] == "sm"


def test_add_line_sits_under_the_empty_state(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path)

    assert EMPTY_TITLE in result["lines"]
    the_input(result, placeholder=ADD)


def test_no_add_line_without_a_focused_chat(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, focused=None)

    assert [entry for entry in result["inputs"] if entry["placeholder"] == ADD] == []


def test_failed_add_restores_the_text(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(
        tmp_path,
        restSequences={"/board/edit": ["__error__"]},
        steps=[add_line("Call John"), press(ENTER)],
    )

    line = the_input(result, placeholder=ADD)
    assert line["value"] == "Call John"
    assert line["readOnly"] is False
    assert FAILED_NOTICE in result["lines"]
    assert texts(rig.store) == []


def test_full_board_rejects_the_add_and_keeps_the_text(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s1", [AddItem(f"item {n}") for n in range(100)], actor="agent", base_rev=0)

    result = rig.run(tmp_path, steps=[add_line("One more"), press(ENTER)])

    assert FAILED_NOTICE in result["lines"]
    assert the_input(result, placeholder=ADD)["value"] == "One more"
    assert len(rig.store.get_board("s1").items) == 100


def test_enter_during_a_write_sends_nothing(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(
        tmp_path,
        duringWrite=[press(ENTER)],
        steps=[add_line("Call John"), press(ENTER)],
    )

    assert len(posts(result)) == 1
    assert texts(rig.store) == ["Call John"]
