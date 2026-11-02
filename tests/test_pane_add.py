"""The pane add lines: the main add line, the plus button and the subtask add line."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pane_rig import Rig, checkbox, posts, the_input
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
