"""Real Hermes SessionDB delete and archive paths reach the plugin and act on its boards.

The gateway venv Python runs `hermes_session_delete_snippet.py` against a temporary
HERMES_HOME. The test needs the hermes-agent checkout (marker hermes).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import HERMES_AGENT_REPO

pytestmark = pytest.mark.hermes

GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"
SNIPPET = Path(__file__).resolve().parent / "hermes_session_delete_snippet.py"
PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugin"


def run_snippet(hermes_home: Path) -> dict[str, Any]:
    if not GATEWAY_PYTHON.exists():
        pytest.skip(f"gateway venv python not found at {GATEWAY_PYTHON}")
    env = {**os.environ, "HERMES_HOME": str(hermes_home)}
    done = subprocess.run(
        [str(GATEWAY_PYTHON), "-I", str(SNIPPET), str(PLUGIN_DIR), str(HERMES_AGENT_REPO)],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_hermes_delete_paths_reach_the_plugin(hermes_home: Path) -> None:
    out = run_snippet(hermes_home)

    assert sorted(out["boards_left"]) == ["arch", "arch-root", "keep"]
    assert [event["reason"] for event in out["events"]] == ["delete", "delete", "delete", "archive"]
