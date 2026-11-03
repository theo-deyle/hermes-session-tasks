"""The user pages: install lines, identifier forms, the pane line, the disclosure, names and dashes (DEV-04, DEV-06)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_README = ROOT / "plugin" / "README.md"
ROOT_README = ROOT / "README.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"

CLI_INSTALL = "hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable"
CLI_UPDATE = "hermes plugins update hermes-session-tasks"
DESKTOP_URL = "https://github.com/theo-deyle/hermes-session-tasks#plugin"
DESKTOP_PATH_FORM = "theo-deyle/hermes-session-tasks/plugin"
PANE_LINE = "Closing the only pane disables the plugin."
DISCLOSURE_WORDS = ("read-only", "state.db", "no network")
SHORT_FORM = "theo-deyle/hermes-session-tasks#plugin"
GITHUB_PREFIX = "https://github.com/"

LONG_DASHES = (chr(0x2014), chr(0x2013))
PERSON_NAME = re.compile(r"\b(Theo|Deyle)\b")
HOST_WORDS = re.compile(r"devpc|devbox|donmor|don-mor|tailscale|/home/|/Users/", re.IGNORECASE)

USER_PAGES = [PLUGIN_README, ROOT_README]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section_after_heading(text: str, word: str) -> list[str]:
    """The lines under the first heading that holds `word`, up to the next heading."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("#") and word in line), None)
    assert start is not None, f"no heading holds {word!r}"
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        body.append(line)
    return body


@pytest.mark.parametrize("page", USER_PAGES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_user_page_holds_the_install_and_update_lines(page: Path) -> None:
    text = read(page)

    assert CLI_INSTALL in text
    assert CLI_UPDATE in text


@pytest.mark.parametrize("page", USER_PAGES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_user_page_holds_the_pane_line(page: Path) -> None:
    assert PANE_LINE in read(page)


@pytest.mark.parametrize("page", USER_PAGES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_user_page_discloses_what_it_stores_and_reads(page: Path) -> None:
    text = read(page)

    for word in DISCLOSURE_WORDS:
        assert word in text, f"missing disclosure word {word!r}"


@pytest.mark.parametrize("page", USER_PAGES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_pane_section_names_the_dialog_path_and_the_full_url(page: Path) -> None:
    section = "\n".join(section_after_heading(read(page), "pane in Hermes Desktop"))

    for word in ("Capabilities", "Plugins", "Install from Git"):
        assert word in section
    assert DESKTOP_URL in section
    assert DESKTOP_PATH_FORM in section


@pytest.mark.parametrize("page", USER_PAGES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_pane_section_never_uses_the_bare_short_form(page: Path) -> None:
    section = "\n".join(section_after_heading(read(page), "pane in Hermes Desktop"))

    for found in re.finditer(re.escape(SHORT_FORM), section):
        assert section[: found.start()].endswith(GITHUB_PREFIX), "short form without the URL prefix"


def test_root_readme_starts_with_the_plugin_readme() -> None:
    assert read(ROOT_README).startswith(read(PLUGIN_README))


def test_root_readme_points_to_contributing() -> None:
    assert "CONTRIBUTING.md" in read(ROOT_README)


@pytest.mark.parametrize("page", USER_PAGES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_user_page_names_no_person_and_no_host(page: Path) -> None:
    text = read(page)

    assert PERSON_NAME.search(text) is None
    assert HOST_WORDS.search(text) is None


@pytest.mark.parametrize(
    "page", [PLUGIN_README, ROOT_README, CONTRIBUTING], ids=lambda p: p.relative_to(ROOT).as_posix()
)
def test_doc_has_no_long_dashes(page: Path) -> None:
    text = read(page)

    assert not any(dash in text for dash in LONG_DASHES)


def test_name_and_host_rules_catch_what_they_guard() -> None:
    assert PERSON_NAME.search("Theo wrote this")
    assert PERSON_NAME.search("by Deyle")
    assert PERSON_NAME.search("by theo-deyle on GitHub") is None
    assert HOST_WORDS.search("ssh to DevPC")
    assert HOST_WORDS.search("see /home/someone")
