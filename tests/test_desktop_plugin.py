"""The Session tasks pane, run in a node VM and wired to the real router through a loopback relay."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pane_rig import (
    EVENT_TYPE,
    HARNESS,
    PLUGIN_JS,
    ROOT,
    Rig,
    board_gets,
    checkbox,
    posts,
    seed_call_john,
)
from session_tasks.model import AddItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def test_check_reaches_the_store(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[{"check": {"row": "1", "value": True}}])

    sent = posts(result)
    assert len(sent) == 1
    assert sent[0]["path"] == "/board/edit"
    assert sent[0]["body"] == {
        "session_id": "s1",
        "ops": [{"op": "set_checked", "item_id": 1, "checked": True}],
        "base_rev": 1,
    }
    board = rig.store.get_board("s1")
    assert board.rev == 2
    assert board.items[0].checked is True
    assert board.items[0].updated_by == "user"
    box = checkbox(result, "1")
    assert box["checked"] is True
    assert box["label"] == "Call John"
    assert "Call John" in result["lines"]
    assert "0 of 1 open" in result["lines"]


def test_pane_shows_the_board_from_the_real_routes(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path)

    assert "Call John" in result["lines"]
    assert "1 of 1 open" in result["lines"]
    assert checkbox(result, "1")["checked"] is False
    assert not [line for line in result["lines"] if line.startswith("Version mismatch")]
    calls = [(c["method"], c["path"]) for c in result["restCalls"]]
    assert ("GET", "/meta") in calls
    assert ("GET", "/board?session_id=s1") in calls
    contribution = result["contribution"]
    assert contribution["id"] == "pane"
    assert contribution["area"] == "panes"
    assert contribution["data"]["placement"] == "right"
    assert contribution["data"]["dock"] == {"pane": "workspace", "pos": "right"}
    assert contribution["data"]["width"] == "320px"


def test_pane_with_no_focused_session_makes_no_board_call(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, focused=None)

    assert result["checkboxes"] == []
    assert not [c for c in result["restCalls"] if c["path"].startswith("/board")]


def board_event(actor: str, rev: int, root_id: str = "s1") -> dict[str, Any]:
    """One `board.updated` event in the shape the listener gets: the ids sit in the payload."""
    return {
        "type": EVENT_TYPE,
        "session_id": "",
        "payload": {"session_id": "s1", "root_id": root_id, "rev": rev, "actor": actor},
    }


def test_event_reloads_the_focused_board(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[{"event": board_event("agent", 9)}])

    assert len(board_gets(result)) == 2
    assert result["eventTypes"] == [EVENT_TYPE]


def test_event_with_no_focus_makes_no_board_call(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, focused=None, steps=[{"event": board_event("agent", 5)}])

    assert not board_gets(result)


def test_poll_interval(rig: Rig, tmp_path: Path) -> None:
    assert rig.run(tmp_path)["intervals"] == [6000]


def test_no_poll_without_a_focused_session(rig: Rig, tmp_path: Path) -> None:
    assert rig.run(tmp_path, focused=None)["intervals"] == []


MISMATCH_LINE = "Version mismatch: update the desktop plugin on this machine"


@pytest.mark.parametrize(
    ("override", "shown"),
    [
        ({"backend_version": "9.9.9", "api_version": 1}, True),
        ({"backend_version": "0.1.0", "api_version": 2}, True),
        (None, False),
    ],
    ids=["backend-version", "api-version", "match"],
)
def test_banner_on_backend_mismatch(
    rig: Rig, tmp_path: Path, override: dict[str, Any] | None, shown: bool
) -> None:
    extra: dict[str, Any] = {}
    if override is not None:
        extra["restOverrides"] = {"/meta": {"ok": True, "plugin_id": "x", **override}}

    result = rig.run(tmp_path, **extra)

    assert (MISMATCH_LINE in result["lines"]) is shown


def test_meta_failure_shows_no_banner_and_loads_the_board(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, restOverrides={"/meta": "__error__"})

    assert MISMATCH_LINE not in result["lines"]
    assert "Call John" in result["lines"]


def test_item_text_stays_plain_text(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s1", [AddItem("<b>bold</b>")], actor="agent", base_rev=0)

    result = rig.run(tmp_path)

    assert "<b>bold</b>" in result["lines"]


def test_plugin_name_and_registration(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path)

    assert result["name"] == "Session tasks"
    assert result["contribution"] == {
        "id": "pane",
        "area": "panes",
        "title": "Session tasks",
        "data": {
            "placement": "right",
            "dock": {"pane": "workspace", "pos": "right"},
            "width": "320px",
        },
    }


HOOK_PLUGIN = """import { useState } from 'react'
import { jsx } from 'react/jsx-runtime'

function Child() {
  %(child)s
  return jsx('div', { children: 'child' })
}

function Top() {
  %(top)s
  return jsx(Child, {})
}

export default {
  id: 'hook-probe',
  name: 'Hook probe',
  register(ctx) {
    ctx.register({ id: 'pane', area: 'panes', title: 'Probe', data: {}, render: () => jsx(Top, {}) })
  }
}
"""


def run_probe(tmp_path: Path, child: str, top: str) -> subprocess.CompletedProcess[str]:
    """Run the harness on a tiny plugin whose hooks sit in the child or in the top component."""
    plugin = tmp_path / "probe.js"
    plugin.write_text(HOOK_PLUGIN % {"child": child, "top": top}, encoding="utf-8")
    config = tmp_path / "probe-config.json"
    config.write_text(json.dumps({"focused": None, "steps": []}), encoding="utf-8")
    return subprocess.run(
        ["node", "--experimental-vm-modules", str(HARNESS), str(plugin), str(config)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_hooks_outside_the_top_level_component_fail_the_harness(tmp_path: Path) -> None:
    completed = run_probe(tmp_path, child="useState(0)", top="")

    assert completed.returncode != 0
    assert "hooks run only in the top-level pane component" in completed.stderr


def test_hooks_in_the_top_level_component_pass(tmp_path: Path) -> None:
    completed = run_probe(tmp_path, child="", top="useState(0)")

    assert completed.returncode == 0, completed.stderr


# The Desktop loader's own import regex: apps/desktop/src/contrib/runtime-loader.ts:72.
IMPORT_RE = re.compile(r"""(from\s*|import\s*\(\s*|import\s+)(['"])([^'"]+)\2""")
ALLOWED_IMPORTS = frozenset({"@hermes/plugin-sdk", "react", "react/jsx-runtime"})
COLOUR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\s*\(")


def import_specifiers(source: str) -> list[str]:
    """Every module name the loader regex finds. Stricter than the loader: it scans text too."""
    return [match.group(3) for match in IMPORT_RE.finditer(source)]


def import_findings(source: str) -> list[str]:
    """The specifiers that are not on the allowlist."""
    return [name for name in import_specifiers(source) if name not in ALLOWED_IMPORTS]


def node_check(source: str) -> subprocess.CompletedProcess[str]:
    """Syntax-check `source` as an ES module read from stdin (RESEARCH Pitfall 1)."""
    return subprocess.run(
        ["node", "--input-type=module", "--check"],
        input=source,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture(scope="module")
def plugin_source() -> str:
    return PLUGIN_JS.read_text(encoding="utf-8")


def test_plugin_passes_the_stdin_module_check(plugin_source: str) -> None:
    checked = node_check(plugin_source)

    assert checked.returncode == 0, checked.stderr


def test_truncated_plugin_fails_the_check(plugin_source: str) -> None:
    checked = node_check(plugin_source[: len(plugin_source) // 2])

    assert checked.returncode != 0


def test_jsx_fails_the_check() -> None:
    checked = node_check("export default () => <div/>\n")

    assert checked.returncode != 0


def test_imports_are_on_the_allowlist(plugin_source: str) -> None:
    found = import_specifiers(plugin_source)

    assert found
    assert import_findings(plugin_source) == []


@pytest.mark.parametrize(
    ("source", "offender"),
    [
        ("import x from 'lodash'\n", "lodash"),
        ("const m = import('x')\n", "x"),
        ('import "side-effect"\n', "side-effect"),
    ],
    ids=["static", "dynamic", "bare"],
)
def test_allowlist_rejects_other_imports(source: str, offender: str) -> None:
    assert import_findings(source) == [offender]


def test_plugin_has_no_colour_literal(plugin_source: str) -> None:
    assert COLOUR_RE.search(plugin_source) is None


def test_colour_scan_catches_literals() -> None:
    assert COLOUR_RE.search("color: #fff") is not None
    assert COLOUR_RE.search("color: rgba(0, 0, 0, 0.5)") is not None
    assert COLOUR_RE.search("text-(--ui-text-secondary) #1 #${id}") is None


def test_plugin_sets_no_raw_html_and_uses_no_socket(plugin_source: str) -> None:
    for banned in ("dangerouslySetInnerHTML", "innerHTML", "ctx.socket"):
        assert banned not in plugin_source


def test_plugin_never_names_todo(plugin_source: str) -> None:
    assert "todo" not in plugin_source.lower()
