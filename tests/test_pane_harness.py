"""The pane harness self-tests: a probe plugin runs in the node VM against the real routes."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pane_rig import (
    EVENT_TYPE,
    PROBE_JS,
    Rig,
    board_gets,
    button,
    checkbox,
    posts,
    seed_call_john,
    stale_body,
    the_input,
)
from session_tasks.model import AddItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

ADD = {"placeholder": "Probe add"}
BOARD_EVENT = {"type": EVENT_TYPE}
ENTER_ADD = [
    {"type": {"input": ADD, "text": "Buy milk"}},
    {"key": {"input": ADD, "key": "Enter"}},
]
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


def test_focus_step_loads_the_new_session(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    rig.store.apply("s2", [AddItem("Email Ann")], actor="agent", base_rev=0)

    result = rig.run(tmp_path, plugin=PROBE_JS, steps=[{"focus": "s2"}])

    assert {"method": "GET", "path": "/board?session_id=s2", "body": None} in result["restCalls"]
    assert "Email Ann" in result["lines"]
    assert "probe session s2" in result["lines"]
    assert "Call John" not in result["lines"]


def test_outside_step_writes_without_a_pane_call(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(
        tmp_path,
        plugin=PROBE_JS,
        steps=[{"outside": {"ops": [{"op": "add", "text": "From outside"}]}}],
    )

    assert result["outsideCalls"][0]["reply"]["ok"] is True
    assert result["outsideCalls"][0]["body"]["session_id"] == "s1"
    assert posts(result) == []
    assert [item.text for item in rig.store.get_board("s1").items] == ["From outside"]


def test_timers_step_runs_pending_callbacks(rig: Rig, tmp_path: Path) -> None:
    before = rig.run(tmp_path, plugin=PROBE_JS, steps=[{"click": "Probe timer"}])
    assert before["timeouts"] == [4000]
    assert "probe timer fired" not in before["lines"]

    after = rig.run(tmp_path, plugin=PROBE_JS, steps=[{"click": "Probe timer"}, {"timers": True}])
    assert "probe timer fired" in after["lines"]

    cancelled = rig.run(
        tmp_path, plugin=PROBE_JS, steps=[{"click": "Probe timer cancel"}, {"timers": True}]
    )
    assert cancelled["timeouts"] == [4000]
    assert "probe timer fired" not in cancelled["lines"]


def test_rest_sequences_then_relay(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    fake_item = {"id": 1, "text": "Fake", "checked": False, "parent_id": None}
    fake = {"ok": True, "root_id": "s1", "rev": 1, "board": {"items": [fake_item]}}

    result = rig.run(
        tmp_path,
        plugin=PROBE_JS,
        restSequences={"/board?session_id=s1": [fake, "__relay__"]},
        steps=[],
    )
    assert "Fake" in result["lines"]
    assert "Call John" not in result["lines"]

    reloaded = rig.run(
        tmp_path,
        plugin=PROBE_JS,
        restSequences={"/board?session_id=s1": [fake, "__relay__"]},
        steps=[{"event": BOARD_EVENT}],
    )
    assert "Call John" in reloaded["lines"]
    assert "Fake" not in reloaded["lines"]


def test_rest_sequences_error_entry(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(
        tmp_path, plugin=PROBE_JS, restSequences={"/board/edit": ["__error__"]}, steps=ENTER_ADD
    )

    assert "probe write failed" in result["lines"]
    assert rig.store.get_board("s1").items == ()


def test_during_write_capture(rig: Rig, tmp_path: Path) -> None:
    held = rig.run(tmp_path, plugin=PROBE_JS, duringWrite=[{"event": BOARD_EVENT}], steps=ENTER_ADD)

    assert len(held["atWrite"]) == 1
    at_write = held["atWrite"][0]
    assert at_write["inputs"][0]["placeholder"] == "Probe add"
    assert at_write["inputs"][0]["readOnly"] is True
    assert "Buy milk" in at_write["lines"]
    assert the_input(held, placeholder="Probe add")["readOnly"] is False

    plain = rig.run(tmp_path, plugin=PROBE_JS, steps=ENTER_ADD)
    assert len(board_gets(held)) == len(board_gets(plain)) + 1


def test_stale_body_shape(rig: Rig) -> None:
    seed_call_john(rig.store)
    board = rig.store.get_board("s1")

    body = stale_body(board, "s1")

    assert set(body) == {
        "ok",
        "error",
        "reason",
        "op_index",
        "item_id",
        "message",
        "root_id",
        "rev",
        "board",
    }
    assert body["ok"] is False
    assert body["error"] == "stale"
    assert body["board"]["items"][0]["text"] == board.items[0].text


def test_unknown_step_fails(rig: Rig, tmp_path: Path) -> None:
    stderr = rig.error(tmp_path, plugin=PROBE_JS, steps=[{"dance": True}])

    assert "unknown step" in stderr


# The menu steps, the host.request stub and the `calls` key, run against the real pane.


def test_open_menu_and_pick_steps(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    rig.store.apply("s2", [AddItem("Email Ann")], actor="agent", base_rev=0)
    session_list = [{"id": "s2", "title": "Other", "preview": "", "_lineage_root_id": None}]

    none = rig.error(tmp_path, plugin=PROBE_JS, steps=[{"openMenu": True}])
    assert "0 menus are rendered" in none

    picked = rig.run(
        tmp_path, sessionList=session_list, steps=[{"openMenu": True}, {"pick": "Other"}]
    )
    assert "Email Ann" in picked["lines"]

    missing = rig.error(tmp_path, steps=[{"openMenu": True}, {"pick": "No such board"}])
    assert "no menu item named" in missing

    alone = rig.error(
        tmp_path,
        steps=[{"openMenu": True}, {"pick": "No other session has a board."}],
        restSequences={"/boards": [{"ok": True, "boards": []}]},
    )
    assert "is disabled" in alone


def test_host_request_stub_records_and_rejects(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    rows = [{"id": "s1", "title": "Mine", "preview": "", "_lineage_root_id": None}]

    listed = rig.run(tmp_path, sessionList=rows)

    assert listed["requestCalls"] == [{"method": "session.list", "params": {"limit": 200}}]
    assert "Mine" in listed["lines"]

    rejected = rig.run(tmp_path, sessionList="__error__")

    assert len(rejected["requestCalls"]) == 1
    assert "Call John" in rejected["lines"]


def test_calls_config_records_results(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(
        tmp_path,
        calls=[
            {"fn": "headerText", "args": [{"open": 1, "total": 2}]},
            {"fn": "shortId", "args": ["20261102_133806_e5cc98"]},
        ],
    )

    assert result["callResults"] == ["1 of 2 open", "e5cc98"]

    stderr = rig.error(tmp_path, calls=[{"fn": "noSuchExport", "args": []}])

    assert "no export named noSuchExport" in stderr


def test_interval_step_runs_the_poll(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    ticked = rig.run(tmp_path, steps=[{"interval": True}, {"interval": True}])

    assert len(board_gets(ticked)) == 3
