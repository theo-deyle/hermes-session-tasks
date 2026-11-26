"""The pane view: subtask groups, collapse, done style, focus switch, empty states and copy."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import Rig, board_gets, button, checkbox, posts, seed_call_john
from session_tasks.markdown import render
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

COLLAPSE_ROW_1 = {"click": {"label": "Collapse subtasks", "row": "1"}}
EXPAND_ROW_1 = {"click": {"label": "Expand subtasks", "row": "1"}}
SECONDARY = "text-(--ui-text-secondary)"


def seed_trip(store: BoardStore, sid: str = "s1") -> None:
    """Item 1 `Plan trip` with subtasks 2 `Book flight` (checked) and 3 `Pack`."""
    store.apply(
        sid,
        [
            AddItem("Plan trip"),
            AddItem("Book flight", checked=True, parent_ref=0),
            AddItem("Pack", parent_ref=0),
        ],
        actor="agent",
        base_rev=0,
    )


def test_parent_with_subtasks_shows_as_a_group_and_copies_as_markdown(
    rig: Rig, tmp_path: Path
) -> None:
    seed_trip(rig.store)

    result = rig.run(tmp_path)

    lines = result["lines"]
    assert "2 of 3 open" in lines
    assert "1/2" in lines
    assert lines.index("Plan trip") < lines.index("Book flight") < lines.index("Pack")
    button(result, "Collapse subtasks", row="1")
    assert [b["row"] for b in result["buttons"] if b["label"] == "Collapse subtasks"] == ["1"]
    for row in ("1", "2", "3"):
        checkbox(result, row)
    copy = result["copy"]
    assert copy["text"] == render(rig.store.get_board("s1"), include_ids=False)
    assert copy["text"] == "- [ ] Plan trip\n  - [x] Book flight\n  - [ ] Pack\n"
    assert copy["label"] == "Copy as markdown"
    assert copy["appearance"] == "icon"
    assert copy["disabled"] is False
    assert "Collapse subtasks" in result["tips"]


def seed_three(store: BoardStore) -> None:
    store.apply(
        "s1",
        [AddItem("Call John"), AddItem("Email Ann"), AddItem("Book room")],
        actor="agent",
        base_rev=0,
    )


def node(result: dict[str, Any], text: str) -> dict[str, Any]:
    found = [entry for entry in result["nodes"] if entry["text"] == text]
    assert len(found) == 1, f"{len(found)} nodes with text {text!r}"
    return found[0]


def test_collapse_hides_subtasks_and_keeps_the_count(rig: Rig, tmp_path: Path) -> None:
    seed_trip(rig.store)

    result = rig.run(tmp_path, steps=[COLLAPSE_ROW_1])

    assert "Book flight" not in result["lines"]
    assert "Pack" not in result["lines"]
    assert "1/2" in result["lines"]
    assert "Plan trip" in result["lines"]
    button(result, "Expand subtasks", row="1")
    assert "Expand subtasks" in result["tips"]


def test_expand_shows_the_subtasks_again(rig: Rig, tmp_path: Path) -> None:
    seed_trip(rig.store)

    result = rig.run(tmp_path, steps=[COLLAPSE_ROW_1, EXPAND_ROW_1])

    assert "Book flight" in result["lines"]
    assert "Pack" in result["lines"]
    button(result, "Collapse subtasks", row="1")


def test_checked_item_stays_in_place_struck_through(rig: Rig, tmp_path: Path) -> None:
    seed_three(rig.store)

    result = rig.run(tmp_path, steps=[{"check": {"row": "2", "value": True}}])

    texts = ("Call John", "Email Ann", "Book room")
    assert [line for line in result["lines"] if line in texts] == list(texts)
    done = node(result, "Email Ann")
    assert done["style"]["textDecoration"] == "line-through"
    assert SECONDARY in done["className"]
    assert "textDecoration" not in node(result, "Call John")["style"]
    assert "2 of 3 open" in result["lines"]


def test_parent_and_subtasks_check_independently(rig: Rig, tmp_path: Path) -> None:
    seed_trip(rig.store)

    result = rig.run(tmp_path, steps=[{"check": {"row": "1", "value": True}}])

    sent = posts(result)
    assert [call["body"]["ops"] for call in sent] == [
        [{"op": "set_checked", "item_id": 1, "checked": True}]
    ]
    items = {item.id: item for item in rig.store.get_board("s1").items}
    assert items[1].checked is True
    assert items[3].checked is False
    assert "1/2" in result["lines"]


def test_focus_change_shows_the_new_board(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    rig.store.apply("s2", [AddItem("Email Ann")], actor="agent", base_rev=0)

    result = rig.run(tmp_path, steps=[{"focus": "s2"}])

    assert "/board?session_id=s2" in [call["path"] for call in board_gets(result)]
    assert "Email Ann" in result["lines"]
    assert "Call John" not in result["lines"]


def test_collapse_state_resets_on_focus_change(rig: Rig, tmp_path: Path) -> None:
    seed_trip(rig.store)
    rig.store.apply("s2", [AddItem("Email Ann")], actor="agent", base_rev=0)

    result = rig.run(tmp_path, steps=[COLLAPSE_ROW_1, {"focus": "s2"}, {"focus": "s1"}])

    assert "Book flight" in result["lines"]
    assert "Pack" in result["lines"]
    button(result, "Collapse subtasks", row="1")


def test_empty_board_shows_the_empty_state(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path)

    assert "The agent adds items here." in result["lines"]
    assert "Add one below." in result["lines"]
    assert not [line for line in result["lines"] if line.endswith(" open")]
    assert result["copy"]["disabled"] is True


def test_no_focused_chat_shows_open_a_chat(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, focused=None)

    assert "Open a chat to see its items." in result["lines"]
    assert result["copy"] is None
    assert not [call for call in result["restCalls"] if call["path"].startswith("/board")]


def test_copy_escapes_a_leading_id_token(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply(
        "s1",
        [AddItem("#12 lunch"), AddItem("plain", parent_ref=0)],
        actor="agent",
        base_rev=0,
    )

    result = rig.run(tmp_path)

    text = result["copy"]["text"]
    assert text == render(rig.store.get_board("s1"), include_ids=False)
    assert text.startswith("- [ ] \\#12 lunch\n")


def test_long_text_wraps_and_is_never_cut(rig: Rig, tmp_path: Path) -> None:
    long_text = ("word " * 100).strip().ljust(500, "x")
    assert len(long_text) == 500
    rig.store.apply("s1", [AddItem(long_text)], actor="agent", base_rev=0)

    result = rig.run(tmp_path)

    shown = node(result, long_text)
    assert shown["style"]["overflowWrap"] == "anywhere"
    assert shown["style"]["whiteSpace"] == "pre-wrap"
    assert "min-w-0" in shown["className"]
    assert "flex-1" in shown["className"]
    assert not [line for line in result["lines"] if line.endswith("…")]


def test_header_sits_outside_the_scroll_area(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(
        tmp_path,
        sessionList=[
            {"id": "s1", "title": "Lease renewal", "preview": "", "_lineage_root_id": None}
        ],
    )

    # The trigger holds the picker title and count; the always-rendered menu rows repeat the same texts.
    in_trigger = [entry for entry in result["nodes"] if entry["button"]]
    (title,) = [entry for entry in in_trigger if entry["text"] == "Lease renewal"]
    (count,) = [entry for entry in in_trigger if entry["text"] == "1 of 1 open"]
    assert title["scroll"] is False
    assert "text-sm" in title["className"]
    assert "font-medium" in title["className"]
    assert count["scroll"] is False
    assert node(result, "Call John")["scroll"] is True


def test_each_saved_row_shows_the_item_number_the_agent_uses(rig: Rig, tmp_path: Path) -> None:
    seed_trip(rig.store)

    result = rig.run(tmp_path)

    for number in ("1", "2", "3"):
        found = node(result, f"#{number}")
        assert found["row"] == number
        assert "text-(--ui-text-tertiary)" in found["className"]
        assert "select-none" in found["className"]
    assert "#2 Book flight" in render(rig.store.get_board("s1"), include_ids=True)
