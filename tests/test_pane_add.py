"""The pane add lines: the main add line, the plus button and the subtask add line."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import Rig, button, checkbox, posts, the_input
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


SUB = "Add a subtask"
PLUS_ROW_1 = {"click": {"label": "Add subtask", "row": "1"}}
PLUS_ROW_2 = {"click": {"label": "Add subtask", "row": "2"}}
STALE_NOTICE = "Board changed, showing the latest"
PLUGIN_SOURCE = (
    Path(__file__).resolve().parent.parent / "plugin" / "desktop" / "plugin.js"
).read_text(encoding="utf-8")


def sub_line(row: str, text: str) -> dict[str, object]:
    return {"type": {"input": {"placeholder": SUB, "row": row}, "text": text}}


def seed_plan_trip(store: BoardStore, subtask: bool = False) -> None:
    ops = [AddItem("Plan trip")]
    if subtask:
        ops.append(AddItem("Pack", parent_ref=0))
    store.apply("s1", ops, actor="agent", base_rev=0)


def sub_inputs(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [entry for entry in result["inputs"] if entry["placeholder"] == SUB]


def test_plus_opens_a_subtask_line_and_enter_adds_under_the_parent(
    rig: Rig, tmp_path: Path
) -> None:
    seed_plan_trip(rig.store)

    result = rig.run(tmp_path, steps=[PLUS_ROW_1, sub_line("1", "Pack"), press(ENTER, SUB, "1")])

    opened = rig.run(tmp_path, steps=[PLUS_ROW_1])
    line = the_input(opened, placeholder=SUB, row="1")
    assert line["autoFocus"] is True
    sent = posts(result)
    assert [call["body"]["ops"] for call in sent] == [
        [{"op": "add", "text": "Pack", "parent_id": 1}]
    ]
    assert sent[0]["body"]["base_rev"] == 1
    items = rig.store.get_board("s1").items
    assert [(item.id, item.text, item.parent_id) for item in items] == [
        (1, "Plan trip", None),
        (2, "Pack", 1),
    ]
    assert the_input(result, placeholder=SUB, row="1")["value"] == ""


def test_subtask_rows_have_no_plus(rig: Rig, tmp_path: Path) -> None:
    seed_plan_trip(rig.store, subtask=True)

    result = rig.run(tmp_path)

    button(result, "Add subtask", row="1")
    assert [b for b in result["buttons"] if b["label"] == "Add subtask" and b["row"] == "2"] == []


def test_plus_expands_a_collapsed_parent(rig: Rig, tmp_path: Path) -> None:
    seed_plan_trip(rig.store, subtask=True)
    collapse = {"click": {"label": "Collapse subtasks", "row": "1"}}

    result = rig.run(tmp_path, steps=[collapse, PLUS_ROW_1])

    assert "Pack" in result["lines"]
    the_input(result, placeholder=SUB)


def test_subtask_line_escape_and_blur(rig: Rig, tmp_path: Path) -> None:
    close = {"blur": {"placeholder": SUB}}
    escaped = rig.run(tmp_path, steps=[PLUS_ROW_1, press("Escape", SUB)])
    blurred = rig.run(tmp_path, steps=[PLUS_ROW_1, close])
    typed = rig.run(tmp_path, steps=[PLUS_ROW_1, sub_line("1", "Pa"), close])

    assert sub_inputs(escaped) == []
    assert sub_inputs(blurred) == []
    assert the_input(typed, placeholder=SUB)["value"] == "Pa"
    assert posts(typed) == []


def test_opening_another_line_keeps_typed_text(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s1", [AddItem("Plan trip"), AddItem("Call John")], actor="agent", base_rev=0)

    typed = rig.run(tmp_path, steps=[PLUS_ROW_1, sub_line("1", "Pack"), PLUS_ROW_2])
    empty = rig.run(tmp_path, steps=[PLUS_ROW_1, PLUS_ROW_2])

    assert sorted(entry["row"] for entry in sub_inputs(typed)) == ["1", "2"]
    assert the_input(typed, placeholder=SUB, row="1")["value"] == "Pack"
    assert [entry["row"] for entry in sub_inputs(empty)] == ["2"]


def test_stale_subtask_add_keeps_the_text(rig: Rig, tmp_path: Path) -> None:
    seed_plan_trip(rig.store)
    outside = {
        "outside": {
            "ops": [{"op": "set_text", "item_id": 1, "text": "Plan the trip"}],
            "base_rev": 1,
        }
    }

    result = rig.run(
        tmp_path,
        steps=[outside, PLUS_ROW_1, sub_line("1", "Pack"), press(ENTER, SUB, "1")],
    )

    sent = posts(result)
    assert len(sent) == 1
    assert sent[0]["body"]["base_rev"] == 1
    assert the_input(result, placeholder=SUB, row="1")["value"] == "Pack"
    assert "Plan the trip" in result["lines"]
    assert STALE_NOTICE in result["lines"]
    assert len(rig.store.get_board("s1").items) == 1


def test_plus_reveals_on_hover_and_focus(rig: Rig, tmp_path: Path) -> None:
    seed_plan_trip(rig.store)

    result = rig.run(tmp_path)

    classes = str(button(result, "Add subtask", row="1")["className"]).split()
    for token in ("opacity-0", "group-hover:opacity-100", "group-focus-within:opacity-100"):
        assert token in classes
    assert "Add subtask" in result["tips"]
    constants = re.findall(r"const [A-Z_]+_CLASS = '([^']*)'", PLUGIN_SOURCE)
    assert "group" in [token for value in constants for token in value.split()]
