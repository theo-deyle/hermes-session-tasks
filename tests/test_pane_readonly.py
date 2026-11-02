"""The read-only view of another session's board: Back, focus, live update, poll, states and the no-write rule."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import EVENT_TYPE, Rig, board_gets, inputs, posts, seed_call_john
from session_tasks.model import AddItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

OPEN_MENU = {"openMenu": True}
BANNER = "Read only. Viewing another session."
S1_TITLE = "Lease renewal"
S2_TITLE = "Syncro ticket 4910"
S3_TITLE = "Third chat"
SESSION_LIST = [
    {"id": "s1", "title": S1_TITLE, "preview": "", "_lineage_root_id": None},
    {"id": "s2", "title": S2_TITLE, "preview": "", "_lineage_root_id": None},
    {"id": "s3", "title": S3_TITLE, "preview": "", "_lineage_root_id": None},
]
PICK_S2 = [OPEN_MENU, {"pick": S2_TITLE}]


def seed_two_boards(rig: Rig) -> None:
    """Board s1 with `Call John` and board s2 with `Reply to the customer`."""
    seed_call_john(rig.store)
    rig.store.apply("s2", [AddItem("Reply to the customer")], actor="agent", base_rev=0)


def test_back_returns_to_the_focused_board_and_keeps_the_add_line(rig: Rig, tmp_path: Path) -> None:
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


def board_paths(result: dict[str, Any]) -> list[str]:
    return [c["path"] for c in board_gets(result)]


def event(root_id: str | None, *, payload: bool = True) -> dict[str, Any]:
    """One `board.updated` event for the root, or one with no payload."""
    body: dict[str, Any] = {"type": EVENT_TYPE, "session_id": ""}
    if payload:
        body["payload"] = {"session_id": "s1", "root_id": root_id, "rev": 9, "actor": "agent"}
    return body


def fake_reply(rev: int, *texts: str) -> dict[str, Any]:
    """A board reply of s2 with these top-level items."""
    items = [
        {"id": i, "text": text, "checked": False, "parent_id": None}
        for i, text in enumerate(texts, start=1)
    ]
    return {"ok": True, "root_id": "s2", "rev": rev, "board": {"items": items}}


def test_focus_change_returns_to_the_focused_board(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"focus": "s3"}])

    assert BANNER not in result["lines"]
    assert board_paths(result)[-1] == "/board?session_id=s3"
    assert any(b["label"].startswith(f"Session: {S3_TITLE}") for b in result["buttons"])
    assert "Reply to the customer" not in result["lines"]


def test_event_for_the_shown_root_reloads_it(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)
    before = rig.run(tmp_path, sessionList=SESSION_LIST, steps=PICK_S2)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"event": event("s2")}])

    assert len(board_paths(result)) == len(board_paths(before)) + 1
    assert board_paths(result)[-1] == "/board?session_id=s2"


def test_event_for_another_root_reloads_nothing(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)
    before = rig.run(tmp_path, sessionList=SESSION_LIST, steps=PICK_S2)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"event": event("s1")}])

    assert board_paths(result) == board_paths(before)


def test_event_without_a_payload_reloads_the_shown_board(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    result = rig.run(
        tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"event": event(None, payload=False)}]
    )

    assert board_paths(result)[-2:] == ["/board?session_id=s2"] * 2


def test_event_for_the_focused_root_reloads_the_focused_board(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[{"event": event("s1")}])

    assert board_paths(result) == ["/board?session_id=s1"] * 2


def test_poll_reloads_the_picked_board_not_the_focused_one(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)
    before = rig.run(tmp_path, sessionList=SESSION_LIST, steps=PICK_S2)

    result = rig.run(
        tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"interval": True}, {"interval": True}]
    )

    assert board_paths(result)[len(board_paths(before)) :] == ["/board?session_id=s2"] * 2


def test_an_older_picked_reply_is_dropped(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)
    sequence = [fake_reply(3, "Rev three"), fake_reply(2, "Rev two")]

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restSequences={"/board?session_id=s2": sequence},
        steps=[*PICK_S2, {"interval": True}],
    )

    assert "Rev three" in result["lines"]
    assert "Rev two" not in result["lines"]


def test_a_picked_board_change_shows_after_the_poll(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)
    write = {"outside": {"session_id": "s2", "ops": [{"op": "add", "text": "Added later"}]}}

    result = rig.run(
        tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, write, {"interval": True}]
    )

    assert "Added later" in result["lines"]
    assert BANNER in result["lines"]
