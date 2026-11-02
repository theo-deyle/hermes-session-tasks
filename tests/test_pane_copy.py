"""Copy from another session's board into the focused board: buttons, queue, replies and the notice."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import Rig, posts
from session_tasks.model import AddItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

OPEN_MENU = {"openMenu": True}
S1_TITLE = "Lease renewal"
S2_TITLE = "Syncro ticket 4910"
SESSION_LIST = [
    {"id": "s1", "title": S1_TITLE, "preview": "", "_lineage_root_id": None},
    {"id": "s2", "title": S2_TITLE, "preview": "", "_lineage_root_id": None},
]
PICK_S2 = [OPEN_MENU, {"pick": S2_TITLE}]
ROW_COPY = {"label": f"Copy item to {S1_TITLE}", "row": "1"}
BACK_TO_S1 = {"click": f"Back to {S1_TITLE}"}
REPLY = "Reply to the customer"


def seed(rig: Rig) -> None:
    """Board s1 holds `Mine` at rev 1 and board s2 holds `Reply to the customer`."""
    rig.store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    rig.store.apply("s2", [AddItem(REPLY)], actor="agent", base_rev=0)


def copied_sentence(result: dict[str, Any]) -> str:
    """The copied notice as one sentence, joined from its pieces."""
    found = [entry for entry in result["titled"] if entry["title"].startswith("Copied ")]
    assert len(found) == 1, f"{len(found)} copied notices"
    return "".join(found[0]["texts"])


def test_row_copy_copies_one_item_into_the_focused_board(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    steps = [*PICK_S2, {"click": ROW_COPY}]

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=steps)

    (copy,) = posts(result)
    assert copy["path"] == "/board/copy"
    assert copy["body"] == {
        "session_id": "s1",
        "from_session_id": "s2",
        "item_ids": [1],
        "base_rev": 1,
    }
    sentence = "Copied 1 to Lease renewal. 0 skipped, already on the board."
    assert copied_sentence(result) == sentence
    assert "Read only. Viewing another session." in result["lines"]
    assert [i.text for i in rig.store.get_board("s2").items] == [REPLY]
    s1_items = rig.store.get_board("s1").items
    assert [i.text for i in s1_items] == ["Mine", REPLY]
    assert s1_items[1].id == 2
    assert s1_items[1].updated_by == "user"


def test_after_a_copy_back_shows_the_copied_item(rig: Rig, tmp_path: Path) -> None:
    seed(rig)

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        steps=[*PICK_S2, {"click": ROW_COPY}, BACK_TO_S1],
    )

    assert "Read only. Viewing another session." not in result["lines"]
    assert "Mine" in result["lines"]
    assert REPLY in result["lines"]
    assert [c["path"] for c in posts(result)] == ["/board/copy"]
