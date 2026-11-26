"""Neutral wording guard: the plugin package names no person and no host (D-53).

`wording_findings` takes one file and returns one finding per hit. It has self-tests that
prove it reports a bad file. The tree test then proves that every text file in the
package has no finding. A finding holds the path, the line number and the kind of hit,
never the line text.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "plugin"
# Case sensitive, so a lowercase account name inside a URL never matches.
PERSON = re.compile(r"\bTheo\b")
HOST = re.compile(r"devpc", re.IGNORECASE)
TEXT_SUFFIXES = (".py", ".yaml", ".yml", ".md", ".js", ".json")
MIN_FILES = 30


def text_files(plugin_dir: Path) -> list[Path]:
    """Return the sorted text files under the package folder. Skip every `__pycache__` folder."""
    return sorted(
        path
        for path in plugin_dir.rglob("*")
        if path.is_file()
        and path.suffix in TEXT_SUFFIXES
        and "__pycache__" not in path.relative_to(plugin_dir).parts
    )


def wording_findings(path: Path, base: Path) -> list[str]:
    """Return one entry per hit: `<relative path>:<line>: person name` or `host name`."""
    relative = path.relative_to(base).as_posix()
    findings: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if PERSON.search(line):
            findings.append(f"{relative}:{number}: person name")
        if HOST.search(line):
            findings.append(f"{relative}:{number}: host name")
    return findings


def test_self_test_reports_both_names(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("clean line\nTheo wrote this\nruns on DevPC\n", encoding="utf-8")

    assert wording_findings(bad, tmp_path) == [
        "bad.py:2: person name",
        "bad.py:3: host name",
    ]


def test_self_test_clean_file_has_no_findings(tmp_path: Path) -> None:
    clean = tmp_path / "clean.md"
    clean.write_text("The user edits the board.\ngithub.com/theo-deyle/repo\n", encoding="utf-8")

    assert wording_findings(clean, tmp_path) == []


def test_self_test_skips_pycache(tmp_path: Path) -> None:
    (tmp_path / "session_tasks" / "__pycache__").mkdir(parents=True)
    (tmp_path / "session_tasks" / "__pycache__" / "cached.py").write_text("x", encoding="utf-8")
    (tmp_path / "session_tasks" / "real.py").write_text("x", encoding="utf-8")

    found = text_files(tmp_path)

    assert [path.name for path in found] == ["real.py"]


def test_scan_finds_the_package_files() -> None:
    found = text_files(PLUGIN_DIR)
    names = {path.relative_to(PLUGIN_DIR).as_posix() for path in found}

    assert len(found) >= MIN_FILES
    assert {"session_tasks/tool_text.py", "desktop/plugin.js", "README.md"} <= names


@pytest.mark.parametrize(
    "path",
    text_files(PLUGIN_DIR),
    ids=lambda path: path.relative_to(PLUGIN_DIR).as_posix(),
)
def test_file_names_no_person_or_host(path: Path) -> None:
    assert wording_findings(path, PLUGIN_DIR) == []
