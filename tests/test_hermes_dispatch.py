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
