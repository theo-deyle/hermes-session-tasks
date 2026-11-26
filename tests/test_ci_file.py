"""The CI workflow runs the house gate with read-only rights and pinned actions (DEV-06, D-52)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
EXPECTED_ACTIONS = {
    "actions/checkout@v7",
    "actions/setup-node@v7",
    "astral-sh/setup-uv@v10.3.3",
}
USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)\s*$")
PIN = re.compile(r"@v\d")


def lines() -> list[str]:
    return WORKFLOW.read_text(encoding="utf-8").splitlines()


def uses_values() -> list[str]:
    found: list[str] = []
    for line in lines():
        match = USES_LINE.match(line)
        if match is not None:
            found.append(match.group(1))
    return found


def test_the_workflow_file_exists() -> None:
    assert WORKFLOW.is_file()


def test_it_runs_the_house_gate_and_the_syntax_check() -> None:
    stripped = [line.strip() for line in lines()]

    assert "run: ./scripts/check.sh" in stripped
    assert "run: node --check plugin/desktop/plugin.js" in stripped


def test_it_runs_on_push_and_on_pull_request() -> None:
    stripped = [line.strip() for line in lines()]

    assert "push:" in stripped
    assert "pull_request:" in stripped


def test_rights_are_read_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert re.search(r"^permissions:\n\s+contents: read$", text, re.MULTILINE)


def test_the_actions_are_exactly_the_three_pinned_ones() -> None:
    values = uses_values()

    assert set(values) == EXPECTED_ACTIONS
    assert all(PIN.search(value) for value in values)


def test_the_runner_skips_the_hermes_tests_and_has_a_time_limit() -> None:
    stripped = [line.strip() for line in lines()]

    assert "HERMES_AGENT_REPO: /nonexistent/hermes-agent" in stripped
    assert any(line.startswith("timeout-minutes:") for line in stripped)


def test_it_reads_no_secret_and_has_no_privileged_trigger() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "secrets." not in text
    assert "pull_request_target" not in text
