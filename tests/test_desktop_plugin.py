"""The test pane, run in a node VM and wired to the real router through a loopback relay."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_client import PREFIX, load_plugin_api, make_client, unload_plugin_api
from conftest import ResolverFor
from rest_relay import RestRelay
from session_tasks.board_api import BoardApi
from session_tasks.model import AddItem
from session_tasks.store import BoardStore

ROOT = Path(__file__).resolve().parent.parent
EVENT_TYPE = "plugin.hermes-session-tasks.board.updated"
PLUGIN_JS = ROOT / "plugin" / "desktop" / "plugin.js"
HARNESS = Path(__file__).with_name("desktop_pane_harness.mjs")

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


@pytest.fixture(autouse=True)
def clean_core() -> Iterator[None]:
    unload_plugin_api()
    yield
    unload_plugin_api()


def run_harness(config: dict[str, Any], tmp_path: Path) -> dict[str, Any]:
    """Run the harness on plugin.js with `config` and return its one JSON line."""
    config_path = tmp_path / "harness-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    completed = subprocess.run(
        [
            "node",
            "--experimental-vm-modules",
            str(HARNESS),
            str(PLUGIN_JS),
            str(config_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout.strip().splitlines()[-1])


class Rig:
    """A store, a resolver and the real router behind one loopback relay."""

    def __init__(self, store: BoardStore, resolver_for: ResolverFor) -> None:
        self.store = store
        resolver, _ = resolver_for({})
        self.client = make_client(load_plugin_api(), BoardApi(store, resolver))

    def run(self, tmp_path: Path, **config: Any) -> dict[str, Any]:
        with RestRelay(self.client) as relay:
            config.setdefault("focused", "s1")
            config.setdefault("steps", [])
            return run_harness({"baseUrl": relay.base_url + PREFIX, **config}, tmp_path)


@pytest.fixture
def rig(store: BoardStore, resolver_for: ResolverFor) -> Rig:
    return Rig(store, resolver_for)


def seed_call_john(store: BoardStore) -> None:
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)


def test_pane_shows_the_board_from_the_real_routes(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path)

    lines = result["lines"]
    assert "backend 0.1.0, api 1" in lines
    assert "pane 0.1.0, api 1" in lines
    assert "session s1, board rev 1" in lines
    assert "[ ] #1 Call John" in lines
    assert not [line for line in lines if line.startswith("Version mismatch")]
    calls = [(c["method"], c["path"]) for c in result["restCalls"]]
    assert ("GET", "/meta") in calls
    assert ("GET", "/board?session_id=s1") in calls
    contribution = result["contribution"]
    assert contribution["id"] == "pane"
    assert contribution["area"] == "panes"
    assert contribution["data"]["placement"] == "right"
    assert contribution["data"]["width"] == "320px"


def test_pane_with_no_focused_session_makes_no_board_call(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, focused=None)

    assert "no session focused" in result["lines"]
    assert "board is empty" in result["lines"]
    assert not [c for c in result["restCalls"] if c["path"].startswith("/board")]


def board_event(actor: str, rev: int, root_id: str = "s1") -> dict[str, Any]:
    """One `board.updated` event in the shape the listener gets: the ids sit in the payload."""
    return {
        "type": EVENT_TYPE,
        "session_id": "",
        "payload": {"session_id": "s1", "root_id": root_id, "rev": rev, "actor": actor},
    }


def board_gets(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        c for c in result["restCalls"] if c["method"] == "GET" and c["path"].startswith("/board")
    ]


def test_agent_event_line(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[{"event": board_event("agent", 9)}])

    agent_lines = [line for line in result["lines"] if line.startswith("agent event:")]
    assert len(agent_lines) == 1
    assert agent_lines[0].startswith("agent event: rev 9 at ")
    assert agent_lines[0].endswith("(this chat)")
    assert "pane event: none yet" in result["lines"]
    assert len(board_gets(result)) == 2
    assert result["eventTypes"] == [EVENT_TYPE]


def test_pane_event_line_and_other_chat(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[{"event": board_event("user", 4, root_id="zz")}])

    pane_lines = [line for line in result["lines"] if line.startswith("pane event:")]
    assert len(pane_lines) == 1
    assert pane_lines[0].startswith("pane event: rev 4 at ")
    assert pane_lines[0].endswith("(other chat)")
    assert "agent event: none yet" in result["lines"]


def test_event_with_no_focused_session_is_other_chat(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, focused=None, steps=[{"event": board_event("agent", 5)}])

    agent_lines = [line for line in result["lines"] if line.startswith("agent event:")]
    assert agent_lines[0].endswith("(other chat)")
    assert not board_gets(result)


def test_events_start_as_none_yet(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path)

    assert "agent event: none yet" in result["lines"]
    assert "pane event: none yet" in result["lines"]
    assert "write test: not run" in result["lines"]


def test_poll_interval(rig: Rig, tmp_path: Path) -> None:
    assert rig.run(tmp_path)["intervals"] == [6000]


def test_no_poll_without_a_focused_session(rig: Rig, tmp_path: Path) -> None:
    assert rig.run(tmp_path, focused=None)["intervals"] == []


def test_write_test_through_the_real_routes(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, steps=[{"click": "Run write test"}])

    posts = [c for c in result["restCalls"] if c["method"] == "POST"]
    assert [c["path"] for c in posts] == ["/board/edit", "/board/edit"]
    assert posts[0]["body"] == {
        "session_id": "s1",
        "ops": [{"op": "add", "text": "test item added by the pane"}],
    }
    assert posts[1]["body"] == {
        "session_id": "s1",
        "ops": [{"op": "set_checked", "item_id": 1, "checked": True}],
        "base_rev": 0,
    }
    board = rig.store.get_board("s1")
    assert board.rev == 2
    by_id = {item.id: item for item in board.items}
    assert by_id[2].text == "test item added by the pane"
    assert by_id[2].updated_by == "user"
    assert by_id[2].rev == 2
    assert by_id[1].checked is False
    lines = result["lines"]
    assert "write test: add ok at rev 2, stale write answered stale (stale) at rev 2" in lines
    assert "[ ] #1 Call John" in lines
    assert "[ ] #2 test item added by the pane" in lines


def test_write_test_on_an_empty_board_still_goes_stale(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, steps=[{"click": "Run write test"}])

    assert (
        "write test: add ok at rev 1, stale write answered stale (stale) at rev 1"
        in result["lines"]
    )
    assert rig.store.get_board("s1").rev == 1
    assert rig.store.get_board("s1").items[0].checked is False


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


def test_meta_failure_shows_backend_not_reached(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, restOverrides={"/meta": "__error__"})

    assert "backend not reached" in result["lines"]
    assert MISMATCH_LINE not in result["lines"]


def test_item_text_stays_plain_text(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s1", [AddItem("<b>bold</b>")], actor="agent", base_rev=0)

    result = rig.run(tmp_path)

    assert "[ ] #1 <b>bold</b>" in result["lines"]


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
