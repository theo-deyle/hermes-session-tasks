"""The pane write path: optimistic display, stale retry, one write at a time and the notice line."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pane_rig import Rig, posts, seed_call_john

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

STALE_NOTICE = "Board changed, showing the latest"
NOTICE_MS = 4000
CHECK_ROW_1 = {"check": {"row": "1", "value": True}}
OUTSIDE_TEXT = {
    "outside": {
        "ops": [{"op": "set_text", "item_id": 1, "text": "Call John today"}],
        "base_rev": 1,
    }
}
CHECK_OP = [{"op": "set_checked", "item_id": 1, "checked": True}]


def test_stale_check_retries_once_on_the_new_rev(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[OUTSIDE_TEXT, CHECK_ROW_1])

    sent = posts(result)
    assert [call["path"] for call in sent] == ["/board/edit", "/board/edit"]
    assert [call["body"]["ops"] for call in sent] == [CHECK_OP, CHECK_OP]
    assert [call["body"]["base_rev"] for call in sent] == [1, 2]
    board = rig.store.get_board("s1")
    assert board.rev == 3
    assert board.items[0].checked is True
    assert board.items[0].text == "Call John today"
    assert board.items[0].updated_by == "user"
    assert "Call John today" in result["lines"]
    assert "0 of 1 open" in result["lines"]
    assert STALE_NOTICE in result["lines"]
    assert NOTICE_MS in result["timeouts"]
