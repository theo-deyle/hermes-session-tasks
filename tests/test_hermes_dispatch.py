"""Dispatch contract: the real Hermes registry loads the plugin and calls `board_read`.

The gateway venv Python runs `hermes_dispatch_snippet.py` against a temporary HERMES_HOME.
The test needs the hermes-agent checkout (marker hermes).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from conftest import HERMES_AGENT_REPO
from session_tasks import tool_text

pytestmark = pytest.mark.hermes

GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"
SNIPPET = Path(__file__).resolve().parent / "hermes_dispatch_snippet.py"
PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugin"
BOARD = "- [ ] #1 Call John\n"
NO_SESSION = "no session id; the board is not available here"


def run_snippet(hermes_home: Path) -> dict[str, object]:
    if not GATEWAY_PYTHON.exists():
        pytest.skip(f"gateway venv python not found at {GATEWAY_PYTHON}")
    env = {**os.environ, "HERMES_HOME": str(hermes_home)}
    done = subprocess.run(
        [str(GATEWAY_PYTHON), "-I", str(SNIPPET), str(PLUGIN_DIR), str(HERMES_AGENT_REPO)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_hermes_dispatches_board_read_with_the_handler_session(hermes_home: Path) -> None:
    out = run_snippet(hermes_home)

    expected = {"ok": True, "rev": 1, "board": BOARD}
    assert out["read"] == expected
    assert out["spoofed"] == expected
    assert out["no_session"] == {"error": NO_SESSION}
    assert "board_read" in out["tools"]  # pyright: ignore[reportOperatorIssue]


def first_sentence(description: str) -> str:
    return description.split(". ")[0].rstrip(".") + "."


def test_hermes_dispatches_board_edit_guard_hooks_prompt_and_skill(hermes_home: Path) -> None:
    out = run_snippet(hermes_home)

    edit_add = out["edit_add"]
    assert isinstance(edit_add, dict)
    assert edit_add["ok"] is True
    assert edit_add["rev"] == 2
    assert edit_add["changed"] == ["- [ ] #2 Book the van"]
    blocked = out["blocked"]
    assert isinstance(blocked, dict)
    assert "Theo must answer first for: remove of #1" in blocked["error"]
    raw_directive = out["raw_directive"]
    assert isinstance(raw_directive, list)
    assert raw_directive[0] == "block"
    assert out["other_directive"] == [None, None]
    confirmed = out["confirmed"]
    assert isinstance(confirmed, dict)
    assert confirmed["changed"] == ["- removed #1"]
    assert out["after_compaction"] == {"ok": True, "rev": 3, "board": "- [ ] #2 Book the van\n"}
    section = out["section_rendered"]
    assert isinstance(section, str)
    assert tool_text.PROMPT_SECTION_ID in section
    assert tool_text.PROMPT_SECTION_TEXT.splitlines()[0] in section
    assert "hermes-session-tasks:board-rules" in out["skills"]  # pyright: ignore[reportOperatorIssue]
    assert out["catalog_lines"] == {
        "board_read": first_sentence(tool_text.BOARD_READ_DESCRIPTION),
        "board_edit": first_sentence(tool_text.BOARD_EDIT_DESCRIPTION),
    }
