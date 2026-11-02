"""The read-only view of another session's board: Back, focus, live update, poll, states and the no-write rule."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import Rig, board_gets, inputs, posts, seed_call_john
from session_tasks.model import AddItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

OPEN_MENU = {"openMenu": True}
BANNER = "Read only. Viewing another session."
S1_TITLE = "Lease renewal"
S2_TITLE = "Syncro ticket 4910"
SESSION_LIST = [
    {"id": "s1", "title": S1_TITLE, "preview": "", "_lineage_root_id": None},
    {"id": "s2", "title": S2_TITLE, "preview": "", "_lineage_root_id": None},
]
PICK_S2 = [OPEN_MENU, {"pick": S2_TITLE}]


def seed_two_boards(rig: Rig) -> None:
    """Board s1 with `Call John` and board s2 with `Reply to the customer`."""
    seed_call_john(rig.store)
    rig.store.apply("s2", [AddItem("Reply to the customer")], actor="agent", base_rev=0)


def test_back_returns_to_the_focused_board_and_keeps_the_add_line(
    rig: Rig, tmp_path: Path
) -> None:
    seed_two_boards(rig)
    steps = [
        {"type": {"input": {"placeholder": "Add an item"}, "text": "Buy milk"}},
        *PICK_S2,
        {"click": f"Back to {S1_TITLE}"},
    ]

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=steps)

    assert board_gets(result)[-1]["path"] == "/board?session_id=s1"
    assert BANNER not in result["lines"]
    assert [i["value"] for i in inputs(result, "Add an item")] == ["Buy milk"]
    assert any(b["label"].startswith(f"Session: {S1_TITLE}") for b in result["buttons"])
    assert posts(result) == []
