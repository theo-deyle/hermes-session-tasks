"""The Session tasks pane, run in a node VM and wired to the real router through a loopback relay."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import HERMES_AGENT_REPO
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
    # Drop the final closing brace of the export list: always a syntax error, wherever blocks end.
    checked = node_check(plugin_source.rstrip()[:-1])

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


CLASS_LITERAL_RE = re.compile(r"className:\s*'([^']*)'|const [A-Z_]+_CLASS = '([^']*)'")
DESKTOP_SRC = HERMES_AGENT_REPO / "apps" / "desktop" / "src"
DESKTOP_SUFFIXES = (".ts", ".tsx", ".css")


def class_tokens(source: str) -> list[str]:
    """Every class name in a `className` literal or a `*_CLASS` constant, in order, once each."""
    found: dict[str, None] = {}
    for match in CLASS_LITERAL_RE.finditer(source):
        for token in "".join(g for g in match.groups() if g is not None).split():
            found.setdefault(token)
    return list(found)


def unshipped_classes(tokens: list[str], desktop_src: Path) -> list[str]:
    """The tokens that no Desktop source file holds. Desktop compiles only the classes it uses."""
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(desktop_src.rglob("*"))
        if path.is_file() and path.suffix in DESKTOP_SUFFIXES
    )
    return [token for token in tokens if token not in text]


def test_class_tokens_reads_props_and_constants() -> None:
    source = "const ROW_CLASS = 'flex gap-1'\njsx('div', { className: 'p-2 flex' })"

    assert class_tokens(source) == ["flex", "gap-1", "p-2"]


def test_unshipped_classes_reports_a_missing_name(tmp_path: Path) -> None:
    (tmp_path / "view.tsx").write_text("const a = 'flex gap-1'\n", encoding="utf-8")

    assert unshipped_classes(["flex", "probe-not-shipped"], tmp_path) == ["probe-not-shipped"]


@pytest.mark.hermes
def test_every_plugin_class_ships_in_desktop(plugin_source: str) -> None:
    tokens = class_tokens(plugin_source)

    assert tokens
    missing = unshipped_classes(tokens, DESKTOP_SRC)
    assert missing == [], f"classes that Desktop does not compile: {missing}"


PALETTE_RE = re.compile(
    r"-(red|green|blue|zinc|gray|neutral|slate|amber|emerald|rose|sky|white|black)\b"
)
STYLE_COLOUR_RE = re.compile(r"(color|background|backgroundColor|borderColor):\s*'(?!var\(--ui-)")
TEMPLATE_CLASS_RE = re.compile(r"className:\s*\x60")
# The pane is one plain file: Desktop loads one uncompiled file and refuses a relative import
# (06-UI-SPEC.md, Registry Safety), so it cannot split. The house 800 line rule is soft; this keeps a ceiling.
MAX_PLUGIN_LINES = 1200


def over_line_ceiling(source: str) -> bool:
    return len(source.splitlines()) > MAX_PLUGIN_LINES


def test_class_names_carry_no_palette_colour(plugin_source: str) -> None:
    offenders = [t for t in class_tokens(plugin_source) if PALETTE_RE.search(t)]

    assert offenders == []


def test_palette_scan_catches_colour_classes() -> None:
    assert PALETTE_RE.search("text-red-500") is not None
    assert PALETTE_RE.search("bg-zinc-800") is not None
    assert PALETTE_RE.search("text-(--ui-text-secondary)") is None
    assert PALETTE_RE.search("border-b") is None


def test_styles_use_theme_colour_vars_only(plugin_source: str) -> None:
    assert STYLE_COLOUR_RE.search(plugin_source) is None


def test_style_colour_scan_catches_named_colours() -> None:
    assert STYLE_COLOUR_RE.search("color: 'red'") is not None
    assert STYLE_COLOUR_RE.search("backgroundColor: 'white'") is not None
    assert STYLE_COLOUR_RE.search("color: 'var(--ui-text-secondary)'") is None


def test_class_names_are_plain_literals(plugin_source: str) -> None:
    assert TEMPLATE_CLASS_RE.search(plugin_source) is None


def test_literal_scan_catches_a_template_class() -> None:
    assert TEMPLATE_CLASS_RE.search("{ className: `a ${b}` }") is not None
    assert TEMPLATE_CLASS_RE.search("{ className: 'a b' }") is None


def test_plugin_stays_under_the_line_ceiling(plugin_source: str) -> None:
    assert not over_line_ceiling(plugin_source)


def test_line_ceiling_catches_a_long_file() -> None:
    assert over_line_ceiling("x\n" * (MAX_PLUGIN_LINES + 1))
    assert not over_line_ceiling("x\n" * MAX_PLUGIN_LINES)


# Mac live check, plan 04-08 step 1: the unchecked box was invisible on the dark theme, and every
# row carried an empty chevron column on the left, so the items did not line up with the add line.


def test_checkbox_border_is_visible(plugin_source: str) -> None:
    assert "const CHECK_CLASS = 'border-(--ui-text-tertiary)'" in plugin_source
    assert "className: CHECK_CLASS" in plugin_source


def test_rows_without_subtasks_start_at_the_checkbox(plugin_source: str) -> None:
    assert "if (!hasChildren) return null" in plugin_source
    row_start = "children: [\n      jsx('span', {\n        className: HIT_CLASS"
    assert row_start in plugin_source
