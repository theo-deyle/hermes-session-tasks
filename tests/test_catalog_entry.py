"""The catalog entry file matches the plugin manifest and passes the Hermes catalog checks (DEV-06, D-51).

The stdlib tests read both files line by line, because the dev group has no YAML parser.
The two `hermes` tests run the Hermes validator and the Hermes loader in the gateway
Python. They skip when the Hermes checkout is absent.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from conftest import HERMES_AGENT_REPO

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "hermes-session-tasks.yaml"
MANIFEST = ROOT / "plugin" / "plugin.yaml"
GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"
VALIDATOR = HERMES_AGENT_REPO / "scripts" / "validate_plugin_catalog.py"
REPO_URL = "https://github.com/theo-deyle/hermes-session-tasks"
INSTALL_IDENTIFIER = f"{REPO_URL}#plugin"
SUBPROCESS_TIMEOUT_SECONDS = 120
SCALAR_LINE = r"^{key}:\s*(.*?)\s*$"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
PERSON = re.compile(r"\bTheo\b")
HOST = re.compile(r"devpc", re.IGNORECASE)
LOADER_SNIPPET = (
    "import sys\n"
    "from pathlib import Path\n"
    "import hermes_yaml\n"
    "from hermes_cli.plugin_catalog import entry_from_mapping\n"
    "path = Path(sys.argv[1])\n"
    "data = hermes_yaml.safe_load(path.read_text(encoding='utf-8'))\n"
    "entry = entry_from_mapping(data, str(path))\n"
    "assert entry is not None, 'the loader rejected the entry'\n"
    "print(entry.install_identifier)\n"
)


def scalar(path: Path, key: str) -> str:
    """Return the raw text after `key:` of the first top-level line, with no quote removal."""
    pattern = re.compile(SCALAR_LINE.format(key=re.escape(key)), re.MULTILINE)
    found = pattern.search(path.read_text(encoding="utf-8"))
    assert found is not None, f"{path.name} has no top-level {key} line"
    return found.group(1)


def unquoted(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def is_quoted(raw: str) -> bool:
    return len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'"


def list_values(path: Path, key: str) -> list[str]:
    """Return the `- item` lines under the indented `key:` line, in file order."""
    items: list[str] = []
    inside = False
    key_pattern = re.compile(rf"^(\s*){re.escape(key)}:\s*$")
    key_indent = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not inside:
            found = key_pattern.match(line)
            if found is not None:
                inside = True
                key_indent = len(found.group(1))
            continue
        item = re.match(r"^(\s*)-\s+(.*?)\s*$", line)
        if item is not None and len(item.group(1)) >= key_indent:
            items.append(unquoted(item.group(2)))
            continue
        if line.strip() == "":
            continue
        break
    assert items, f"{path.name} has no list under {key}"
    return items


def test_name_repo_and_subdir() -> None:
    assert scalar(CATALOG, "name") == scalar(MANIFEST, "name")
    assert scalar(CATALOG, "repo") == REPO_URL
    assert scalar(CATALOG, "subdir") == "plugin"


def test_version_is_quoted_and_equals_the_manifest() -> None:
    raw = scalar(CATALOG, "version")

    assert is_quoted(raw)
    assert unquoted(raw) == scalar(MANIFEST, "version")


def test_sha_is_a_quoted_placeholder() -> None:
    raw = scalar(CATALOG, "sha")
    lines = CATALOG.read_text(encoding="utf-8").splitlines()

    assert is_quoted(raw)
    assert HEX40.match(unquoted(raw))
    assert any(line.startswith("# PLACEHOLDER") for line in lines)


def test_requires_hermes_tier_and_category() -> None:
    assert unquoted(scalar(CATALOG, "requires_hermes")) == unquoted(
        scalar(MANIFEST, "requires_hermes")
    )
    assert scalar(CATALOG, "tier") == "community"
    assert scalar(CATALOG, "category") == "desktop"


def test_capabilities_equal_the_manifest_lists() -> None:
    assert list_values(CATALOG, "provides_tools") == list_values(MANIFEST, "provides_tools")
    assert list_values(CATALOG, "provides_hooks") == list_values(MANIFEST, "provides_hooks")


def test_description_holds_the_disclosure_and_no_personal_name() -> None:
    description = unquoted(scalar(CATALOG, "description"))

    for phrase in ("read-only", "state.db", "no network"):
        assert phrase in description, f"description lacks {phrase!r}"
    assert PERSON.search(description) is None
    assert HOST.search(description) is None


def test_the_known_issue_is_listed() -> None:
    assert list_values(CATALOG, "known_issues") == ["Closing the only pane disables the plugin."]


@pytest.mark.hermes
def test_hermes_validator_accepts_the_entry() -> None:
    result = subprocess.run(
        [str(GATEWAY_PYTHON), str(VALIDATOR), str(CATALOG)],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: 1 file(s) valid" in result.stdout


@pytest.mark.hermes
def test_hermes_loader_gives_the_install_identifier() -> None:
    result = subprocess.run(
        [str(GATEWAY_PYTHON), "-c", LOADER_SNIPPET, str(CATALOG)],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
        cwd=HERMES_AGENT_REPO,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == INSTALL_IDENTIFIER
