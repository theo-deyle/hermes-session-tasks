"""The pane harness self-tests: a probe plugin runs in the node VM against the real routes."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pane_rig import PROBE_JS, Rig, button, checkbox, posts, seed_call_john, the_input
from session_tasks.model import AddItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

ADD = {"placeholder": "Probe add"}
DELETE_ROW_2 = {"click": {"label": "Probe delete", "row": "2"}}


def seed_two(rig: Rig) -> None:
    rig.store.apply("s1", [AddItem("Call John"), AddItem("Email Ann")], actor="agent", base_rev=0)


def test_probe_enter_adds_through_the_routes(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(
        tmp_path,
        plugin=PROBE_JS,
        steps=[
            {"type": {"input": ADD, "text": "Buy milk"}},
            {"key": {"input": ADD, "key": "Enter"}},
        ],
    )

    sent = posts(result)
    assert len(sent) == 1
    assert sent[0]["body"] == {
        "session_id": "s1",
        "ops": [{"op": "add", "text": "Buy milk"}],
        "base_rev": 0,
    }
    board = rig.store.get_board("s1")
    assert [item.text for item in board.items] == ["Buy milk"]
    assert board.items[0].updated_by == "user"
    assert the_input(result, placeholder="Probe add")["value"] == ""
    assert "Buy milk" in result["lines"]


def test_input_selector_needs_one_match(rig: Rig, tmp_path: Path) -> None:
    stderr = rig.error(
        tmp_path,
        plugin=PROBE_JS,
        steps=[{"type": {"input": {"placeholder": "No such input"}, "text": "x"}}],
    )

    assert "no input matches" in stderr


def test_click_by_label_and_row(rig: Rig, tmp_path: Path) -> None:
    seed_two(rig)

    result = rig.run(tmp_path, plugin=PROBE_JS, steps=[DELETE_ROW_2])

    assert result["confirm"] == {
        "open": True,
        "title": "Probe confirm",
        "description": "Probe body",
        "confirmLabel": "Probe yes",
        "cancelLabel": "Probe no",
        "destructive": True,
    }
    assert button(result, "Probe delete", row="2")["disabled"] is False


def test_click_with_two_matches_fails(rig: Rig, tmp_path: Path) -> None:
    seed_two(rig)

    stderr = rig.error(tmp_path, plugin=PROBE_JS, steps=[{"click": "Probe delete"}])

    assert "2 buttons labelled" in stderr


def test_click_on_a_disabled_button_fails(rig: Rig, tmp_path: Path) -> None:
    stderr = rig.error(tmp_path, plugin=PROBE_JS, steps=[{"click": "Probe copy all"}])

    assert "is disabled" in stderr


def test_confirm_sends_and_cancel_does_not(rig: Rig, tmp_path: Path) -> None:
    seed_two(rig)
    rev = rig.store.get_board("s1").rev

    cancelled = rig.run(tmp_path, plugin=PROBE_JS, steps=[DELETE_ROW_2, {"cancel": True}])

    assert posts(cancelled) == []
    assert cancelled["confirm"]["open"] is False
    assert len(rig.store.get_board("s1").items) == 2

    confirmed = rig.run(tmp_path, plugin=PROBE_JS, steps=[DELETE_ROW_2, {"confirm": True}])

    sent = posts(confirmed)
    assert [call["body"]["ops"] for call in sent] == [[{"op": "remove", "item_id": 2}]]
    assert sent[0]["body"]["base_rev"] == rev
    assert [item.text for item in rig.store.get_board("s1").items] == ["Call John"]
    assert confirmed["confirm"]["open"] is False


def test_confirm_without_a_dialog_fails(rig: Rig, tmp_path: Path) -> None:
    seed_two(rig)

    stderr = rig.error(tmp_path, plugin=PROBE_JS, steps=[{"confirm": True}])

    assert "no confirm dialog is open" in stderr


def test_click_text_and_blur(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    clicked = rig.run(tmp_path, plugin=PROBE_JS, steps=[{"clickText": "Call John"}])
    assert "probe clicked Call John" in clicked["lines"]

    blurred = rig.run(tmp_path, plugin=PROBE_JS, steps=[{"blur": ADD}])
    assert "probe blurred" in blurred["lines"]
    assert posts(blurred) == []

    escaped = rig.run(
        tmp_path,
        plugin=PROBE_JS,
        steps=[
            {"type": {"input": ADD, "text": "abc"}},
            {"key": {"input": ADD, "key": "Escape", "blur": True}},
        ],
    )
    assert the_input(escaped, placeholder="Probe add")["value"] == ""
    assert "probe blurred" in escaped["lines"]


def test_records_guard_nodes_tips_copy(rig: Rig, tmp_path: Path) -> None:
    seed_two(rig)

    result = rig.run(tmp_path, plugin=PROBE_JS)

    assert checkbox(result, "1")["guarded"] is True
    nodes = {node["text"]: node for node in result["nodes"]}
    assert nodes["Probe header"]["scroll"] is False
    assert nodes["Probe header"]["className"] == "probe-header"
    assert nodes["Call John"]["scroll"] is True
    assert nodes["Call John"]["row"] == "1"
    assert nodes["Call John"]["style"] == {"whiteSpace": "pre-wrap"}
    assert "Probe delete" in result["tips"]
    assert result["copy"] == {
        "text": "probe copy 2",
        "disabled": False,
        "label": "Probe copy",
        "appearance": "icon",
    }


def test_empty_state_lines(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, plugin=PROBE_JS)

    assert "Probe empty" in result["lines"]
    assert "Probe empty body" in result["lines"]
    assert any(node["text"] == "Probe empty" for node in result["nodes"])
    assert result["copy"]["disabled"] is True
