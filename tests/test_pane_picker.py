"""The session picker, the menu and the read-only view of another board, run against the real router."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import Rig, button, checkbox, inputs, seed_call_john
from session_tasks.model import AddItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

OPEN_MENU = {"openMenu": True}
S2_TITLE = "Syncro ticket 4910"
SESSION_LIST = [{"id": "s2", "title": S2_TITLE, "preview": "", "_lineage_root_id": None}]
BANNER = "Read only. Viewing another session."


def seed_two_boards(rig: Rig) -> None:
    """Board s1 with `Call John` and board s2 with `Reply to the customer`."""
    seed_call_john(rig.store)
    rig.store.apply("s2", [AddItem("Reply to the customer")], actor="agent", base_rev=0)


def gets(result: dict[str, Any], path: str) -> list[dict[str, Any]]:
    """The GET calls of the harness `restCalls` with exactly this path."""
    return [c for c in result["restCalls"] if c["method"] == "GET" and c["path"] == path]


def test_pick_another_board_shows_it_read_only(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    opened = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[OPEN_MENU])

    assert {"method": "session.list", "params": {"limit": 200}} in opened["requestCalls"]
    assert len(gets(opened, "/boards")) == 1
    menu = opened["menuItems"]
    assert menu[0]["texts"][0] == "Untitled session"
    assert menu[0]["current"] is True
    assert menu[1] == {"separator": True}
    assert S2_TITLE in menu[2]["texts"]

    picked = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[OPEN_MENU, {"pick": S2_TITLE}])

    assert len(gets(picked, "/board?session_id=s2")) == 1
    assert BANNER in picked["lines"]
    assert "Reply to the customer" in picked["lines"]
    assert "Call John" not in picked["lines"]
    assert checkbox(picked, "1")["disabled"] is True
    assert inputs(picked, "Add an item") == []
    assert (
        button(picked, f"Session: {S2_TITLE}, 1 of 1 open")["label"]
        == f"Session: {S2_TITLE}, 1 of 1 open"
    )
