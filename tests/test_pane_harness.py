"""The pane harness self-tests: a probe plugin runs in the node VM against the real routes."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pane_rig import PROBE_JS, Rig, posts, the_input

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

ADD = {"placeholder": "Probe add"}


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
