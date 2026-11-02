"""The pane view: subtask groups, collapse, done style, focus switch, empty states and copy."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pane_rig import Rig, button, checkbox
from session_tasks.markdown import render
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


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
