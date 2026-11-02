"""The pane inline edit and delete: edit rules, reload and focus rules, trash and confirm dialog."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pane_rig import EVENT_TYPE, Rig, button, checkbox, inputs, posts, seed_call_john, the_input
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

CALL = "Call John"
CALL_AT_3 = "Call John at 3"
ROW_1 = {"row": "1"}
ENTER = "Enter"
ADD = "Add an item"
STALE = "Board changed, showing the latest"
CLICK_CALL = {"clickText": CALL}
RELOAD = {"event": {"type": EVENT_TYPE}}


def seed(store: BoardStore, *texts: str, sid: str = "s1") -> None:
    """One board write per text, so each text raises the rev by one."""
    for text in texts:
        store.apply(sid, [AddItem(text)], actor="agent", base_rev=store.get_board(sid).rev)


def outside(*ops: dict[str, object], base_rev: int) -> dict[str, object]:
    return {"outside": {"ops": list(ops), "base_rev": base_rev}}


def edit_text(text: str, row: str = "1") -> dict[str, object]:
    return {"type": {"input": {"row": row}, "text": text}}


def press(key: str, row: str = "1", blur: bool = False) -> dict[str, object]:
    step: dict[str, object] = {"input": {"row": row}, "key": key}
    if blur:
        step["blur"] = True
    return {"key": step}


def test_click_text_edit_and_enter_saves(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    opened = rig.run(tmp_path, steps=[{"clickText": CALL}])
    result = rig.run(
        tmp_path,
        steps=[{"clickText": CALL}, edit_text(CALL_AT_3), press(ENTER)],
    )

    assert the_input(opened, row="1")["value"] == CALL
    sent = posts(result)
    assert [call["body"]["ops"] for call in sent] == [
        [{"op": "set_text", "item_id": 1, "text": CALL_AT_3}]
    ]
    assert sent[0]["body"]["base_rev"] == 1
    item = rig.store.get_board("s1").items[0]
    assert item.text == CALL_AT_3
    assert item.updated_by == "user"
    assert CALL_AT_3 in result["lines"]
    assert inputs(result, row="1") == []


def test_escape_cancels_the_edit(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[CLICK_CALL, edit_text("Call Bob"), press("Escape")])

    assert posts(result) == []
    assert CALL in result["lines"]
    assert inputs(result, row="1") == []


def test_blur_saves_the_edit(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[CLICK_CALL, edit_text(CALL_AT_3), {"blur": ROW_1}])

    assert [call["body"]["ops"] for call in posts(result)] == [
        [{"op": "set_text", "item_id": 1, "text": CALL_AT_3}]
    ]
    assert rig.store.get_board("s1").items[0].text == CALL_AT_3


def test_unchanged_or_blank_text_sends_nothing(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    unchanged = rig.run(tmp_path, steps=[CLICK_CALL, press(ENTER)])
    blank = rig.run(tmp_path, steps=[CLICK_CALL, edit_text("   "), press(ENTER)])

    assert posts(unchanged) == []
    assert posts(blank) == []
    assert CALL in blank["lines"]
    assert [item.text for item in rig.store.get_board("s1").items] == [CALL]


def test_enter_then_blur_saves_once(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[CLICK_CALL, edit_text(CALL_AT_3), press(ENTER, blur=True)])

    assert len(posts(result)) == 1


def test_check_during_an_edit_keeps_the_edit(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    steps = [CLICK_CALL, edit_text(CALL_AT_3), {"check": {"row": "1", "value": True}}]

    mid = rig.run(tmp_path, steps=steps)
    sent = posts(mid)

    assert [call["body"]["ops"][0]["op"] for call in sent] == ["set_checked"]
    assert the_input(mid, row="1")["value"] == CALL_AT_3
    assert checkbox(mid, "1")["guarded"] is True
    done = rig.run(tmp_path, steps=[*steps, press(ENTER)])
    last = posts(done)[-1]
    assert last["body"]["ops"][0]["op"] == "set_text"
    assert last["body"]["base_rev"] == 2


def test_second_edit_saves_the_first(rig: Rig, tmp_path: Path) -> None:
    seed(rig.store, CALL, "Email Ann")

    result = rig.run(
        tmp_path,
        steps=[CLICK_CALL, edit_text(CALL_AT_3), {"clickText": "Email Ann"}],
    )

    assert [call["body"]["ops"] for call in posts(result)] == [
        [{"op": "set_text", "item_id": 1, "text": CALL_AT_3}]
    ]
    assert the_input(result, row="2")["value"] == "Email Ann"
    assert inputs(result, row="1") == []


def test_done_item_can_be_edited(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s1", [AddItem(CALL, checked=True)], actor="agent", base_rev=0)

    result = rig.run(tmp_path, steps=[CLICK_CALL])

    the_input(result, row="1")


def test_edit_input_limits(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    line = the_input(rig.run(tmp_path, steps=[CLICK_CALL]), row="1")

    assert line["maxLength"] == 500
    assert line["size"] == "sm"
    assert line["autoFocus"] is True


def test_stale_edit_keeps_the_typed_text(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    check = {"op": "set_checked", "item_id": 1, "checked": True}

    result = rig.run(
        tmp_path,
        steps=[outside(check, base_rev=1), CLICK_CALL, edit_text(CALL_AT_3), press(ENTER)],
    )

    sent = [call for call in posts(result) if call["body"]["ops"][0]["op"] == "set_text"]
    assert len(sent) == 1
    assert sent[0]["body"]["base_rev"] == 1
    assert the_input(result, row="1")["value"] == CALL_AT_3
    assert STALE in result["lines"]
    assert rig.store.get_board("s1").items[0].text == CALL


def test_reload_keeps_an_open_edit(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[CLICK_CALL, edit_text(CALL_AT_3), RELOAD])

    assert the_input(result, row="1")["value"] == CALL_AT_3


def test_reload_keeps_the_add_text_and_collapse(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply(
        "s1", [AddItem("Plan trip"), AddItem("Pack", parent_ref=0)], actor="agent", base_rev=0
    )
    collapse = {"click": {"label": "Collapse subtasks", "row": "1"}}

    result = rig.run(
        tmp_path,
        steps=[collapse, {"type": {"input": {"placeholder": ADD}, "text": "Draft"}}, RELOAD],
    )

    assert the_input(result, placeholder=ADD)["value"] == "Draft"
    button(result, "Expand subtasks", row="1")


def test_edit_closes_when_its_item_is_gone(rig: Rig, tmp_path: Path) -> None:
    seed(rig.store, CALL, "Email Ann")
    gone = {"op": "remove", "item_id": 1}

    result = rig.run(
        tmp_path,
        steps=[CLICK_CALL, edit_text("x"), outside(gone, base_rev=2), RELOAD],
    )

    assert inputs(result, row="1") == []
    assert STALE in result["lines"]


def test_focus_change_drops_edit_and_typing(rig: Rig, tmp_path: Path) -> None:
    seed(rig.store, CALL)
    seed(rig.store, "Email Ann", sid="s2")

    result = rig.run(
        tmp_path,
        steps=[
            CLICK_CALL,
            {"type": {"input": {"placeholder": ADD}, "text": "Draft"}},
            {"focus": "s2"},
        ],
    )

    assert inputs(result, row="1") == []
    assert the_input(result, placeholder=ADD)["value"] == ""
