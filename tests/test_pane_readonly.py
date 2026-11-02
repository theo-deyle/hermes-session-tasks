"""The read-only view of another session's board: Back, focus, live update, poll, states and the no-write rule."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import EVENT_TYPE, Rig, board_gets, checkbox, inputs, posts, seed_call_john
from session_tasks.markdown import render
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

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


EMPTY_TITLE = "This board is empty."
EMPTY_HINT = "Pick another session or go back."
FAILED_NOTICE = "Could not load the board. Retrying."
COLLAPSE_ROW_1 = {"click": {"label": "Collapse subtasks", "row": "1"}}
BACK_TO_S1 = {"click": f"Back to {S1_TITLE}"}


def seed_trip(store: BoardStore, sid: str, parent: str, *subtasks: str) -> None:
    """Item 1 `parent` with one subtask for each text in `subtasks`."""
    items = [AddItem(parent), *(AddItem(text, parent_ref=0) for text in subtasks)]
    store.apply(sid, items, actor="agent", base_rev=0)


def node(result: dict[str, Any], text: str) -> dict[str, Any]:
    found = [entry for entry in result["nodes"] if entry["text"] == text]
    assert len(found) == 1, f"{len(found)} nodes with text {text!r}"
    return found[0]


def test_empty_picked_board_shows_its_empty_state(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restSequences={"/board?session_id=s2": [fake_reply(1)]},
        steps=PICK_S2,
    )

    assert EMPTY_TITLE in result["lines"]
    assert EMPTY_HINT in result["lines"]
    assert "The agent adds items here." not in result["lines"]
    assert inputs(result, "Add an item") == []
    assert result["copy"]["disabled"] is True


def test_picked_board_load_failure_shows_the_notice_and_retries(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)
    sequences = {"/board?session_id=s2": ["__error__", "__relay__"]}

    failed = rig.run(tmp_path, sessionList=SESSION_LIST, restSequences=sequences, steps=PICK_S2)
    retried = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restSequences=sequences,
        steps=[*PICK_S2, {"interval": True}],
    )

    assert FAILED_NOTICE in failed["lines"]
    assert "Reply to the customer" not in failed["lines"]
    assert "Reply to the customer" in retried["lines"]
    assert FAILED_NOTICE not in retried["lines"]


def test_read_only_rows_keep_the_done_style(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)
    rig.store.apply("s2", [AddItem("Sent the quote", checked=True)], actor="agent", base_rev=1)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=PICK_S2)

    done = node(result, "Sent the quote")
    assert done["style"]["textDecoration"] == "line-through"
    assert "text-(--ui-text-secondary)" in done["className"]
    assert checkbox(result, "2")["checked"] is True
    assert checkbox(result, "2")["disabled"] is True
    assert "textDecoration" not in node(result, "Reply to the customer")["style"]


def test_collapse_works_and_has_its_own_map(rig: Rig, tmp_path: Path) -> None:
    seed_trip(rig.store, "s1", "Plan trip", "Book flight", "Pack")
    seed_trip(rig.store, "s2", "Plan move", "Rent van", "Box books")
    run: dict[str, Any] = {"sessionList": SESSION_LIST}

    picked = rig.run(tmp_path, steps=[COLLAPSE_ROW_1, *PICK_S2], **run)
    collapsed = rig.run(tmp_path, steps=[COLLAPSE_ROW_1, *PICK_S2, COLLAPSE_ROW_1], **run)
    back = rig.run(tmp_path, steps=[COLLAPSE_ROW_1, *PICK_S2, COLLAPSE_ROW_1, BACK_TO_S1], **run)
    again = rig.run(
        tmp_path, steps=[COLLAPSE_ROW_1, *PICK_S2, COLLAPSE_ROW_1, BACK_TO_S1, *PICK_S2], **run
    )

    assert "Rent van" in picked["lines"]
    assert "Rent van" not in collapsed["lines"]
    assert "0/2" in collapsed["lines"]
    assert "Plan trip" in back["lines"]
    assert "Book flight" not in back["lines"]
    assert "Rent van" in again["lines"]


def test_read_only_view_sends_no_write(rig: Rig, tmp_path: Path) -> None:
    seed_trip(rig.store, "s2", "Plan move", "Rent van", "Box books")
    seed_call_john(rig.store)
    config: dict[str, Any] = {"sessionList": SESSION_LIST}

    result = rig.run(
        tmp_path,
        steps=[*PICK_S2, COLLAPSE_ROW_1, {"click": {"label": "Expand subtasks", "row": "1"}}],
        **config,
    )

    # Row Copy adds to the focused board only; the picked board gets no write (plan 06-11).
    allowed = ("Session: ", "Back to ", "Collapse subtasks", "Expand subtasks", "Copy item to ")
    enabled = [b["label"] for b in result["buttons"] if not b["disabled"]]
    assert enabled
    assert all(label.startswith(allowed) for label in enabled)
    assert all(box["disabled"] for box in result["checkboxes"])
    assert result["inputs"] == []
    assert result["confirm"] is None or result["confirm"]["open"] is False
    assert posts(result) == []
    for text in ("Plan move", "Rent van", "Box books"):
        message = rig.error(tmp_path, steps=[*PICK_S2, {"clickText": text}], **config)
        assert f'no clickable text "{text}"' in message


def test_picking_the_focused_row_or_the_shown_row_goes_back(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)
    config: dict[str, Any] = {"sessionList": SESSION_LIST}

    focused = rig.run(tmp_path, steps=[*PICK_S2, OPEN_MENU, {"pick": S1_TITLE}], **config)
    shown = rig.run(tmp_path, steps=[*PICK_S2, OPEN_MENU, {"pick": S2_TITLE}], **config)

    for result in (focused, shown):
        assert BANNER not in result["lines"]
        assert board_paths(result)[-1] == "/board?session_id=s1"
        assert "Call John" in result["lines"]


def test_an_open_edit_is_saved_before_a_pick(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)
    steps = [
        {"clickText": "Call John"},
        {"type": {"input": {"row": "1"}, "text": "Call John at 3"}},
        *PICK_S2,
    ]

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=steps)

    (write,) = posts(result)
    assert write["path"] == "/board/edit"
    assert write["body"]["ops"] == [{"op": "set_text", "item_id": 1, "text": "Call John at 3"}]
    calls = result["restCalls"]
    s2_get = next(i for i, c in enumerate(calls) if c["path"] == "/board?session_id=s2")
    assert calls.index(write) < s2_get


def test_copy_as_markdown_copies_the_shown_board(rig: Rig, tmp_path: Path) -> None:
    seed_trip(rig.store, "s2", "Plan move", "Rent van", "Box books")
    seed_call_john(rig.store)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=PICK_S2)

    assert result["copy"]["text"] == render(rig.store.get_board("s2"), include_ids=False)
    assert result["copy"]["text"] == "- [ ] Plan move\n  - [ ] Rent van\n  - [ ] Box books\n"
