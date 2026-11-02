"""The pane inline edit and delete: edit rules, reload and focus rules, trash and confirm dialog."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pane_rig import Rig, inputs, posts, seed_call_john, the_input

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

CALL = "Call John"
CALL_AT_3 = "Call John at 3"
ROW_1 = {"row": "1"}
ENTER = "Enter"


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
