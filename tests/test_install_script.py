"""Tests for scripts/install-desktop.ps1, run as `pwsh -File` with a fake scp first on PATH.

The fake scp is a bash script. It logs its arguments and copies FAKE_SCP_SOURCE to its last
argument, resolved against its working folder. It runs as a child process, so no socket opens.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh 7 is not installed")

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "install-desktop.ps1"
REMOTE = "/home/theo/local_repo/hermes-session-tasks/plugin/desktop/plugin.js"
SOURCE_TEXT = "export default { id: 'x' }\n"
SLOT = Path("desktop-plugins") / "hermes-session-tasks"
TIMEOUT_SECONDS = 60

FAKE_SCP = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$FAKE_SCP_LOG"
if [ -n "${FAKE_SCP_FAIL_ALL:-}" ]; then exit 1; fi
if [ -n "${FAKE_SCP_FAIL_O:-}" ] && [ "$1" = "-O" ]; then exit 1; fi
for last; do :; done
cp "$FAKE_SCP_SOURCE" "$last"
"""


@dataclass(frozen=True)
class Rig:
    """A fake scp on a private bin folder, its call log and its source file."""

    root: Path
    bin_dir: Path
    log: Path
    source: Path

    def calls(self) -> list[str]:
        if not self.log.exists():
            return []
        return self.log.read_text(encoding="utf-8").splitlines()


def make_rig(root: Path, source_text: str = SOURCE_TEXT) -> Rig:
    bin_dir = root / "fakebin"
    bin_dir.mkdir(parents=True)
    scp = bin_dir / "scp"
    scp.write_text(FAKE_SCP, encoding="utf-8")
    scp.chmod(scp.stat().st_mode | stat.S_IXUSR)
    source = root / "source-plugin.js"
    source.write_text(source_text, encoding="utf-8")
    return Rig(root=root, bin_dir=bin_dir, log=root / "scp.log", source=source)


@pytest.fixture
def rig(tmp_path: Path) -> Rig:
    return make_rig(tmp_path / "rig-root")


def script_env(rig: Rig, extra: dict[str, str] | None = None) -> dict[str, str]:
    """The child environment: fake scp first on PATH, no Hermes variables, a tmp HOME."""
    env = dict(os.environ)
    for name in ("HERMES_HOME", "HERMES_DATA_DIR_SUFFIX"):
        env.pop(name, None)
    env["PATH"] = f"{rig.bin_dir}{os.pathsep}{env['PATH']}"
    env["HOME"] = str(rig.root / "user-home")
    env["FAKE_SCP_LOG"] = str(rig.log)
    env["FAKE_SCP_SOURCE"] = str(rig.source)
    env.update(extra or {})
    return env


def run_script(
    args: list[str], rig: Rig, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT), *args],
        env=script_env(rig, env_extra),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_script_installs_the_file_and_prints_path_and_hash(rig: Rig) -> None:
    home = rig.root / "home"

    result = run_script(["-HermesHome", str(home), "-DevpcHost", "devpc"], rig)

    slot = home / SLOT
    target = slot / "plugin.js"
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.read_text(encoding="utf-8") == SOURCE_TEXT
    assert f"installed: {target}" in result.stdout.splitlines()
    assert f"sha256: {sha256_hex(SOURCE_TEXT)}" in result.stdout.splitlines()
    assert rig.calls()[0] == f"-O -q devpc:{REMOTE} .plugin.js.new"
    assert not (slot / ".plugin.js.new").exists()
    assert not (slot / ".hermes-package.json").exists()


def dry_run_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    return result.stdout.splitlines()


def slot_files(home: Path) -> list[str]:
    return sorted(entry.name for entry in (home / SLOT).iterdir())


def seed_plugin(home: Path, text: str = "old plugin bytes") -> Path:
    slot = home / SLOT
    slot.mkdir(parents=True)
    target = slot / "plugin.js"
    target.write_text(text, encoding="utf-8")
    return target


def ps_literal(value: str | bool) -> str:
    if isinstance(value, bool):
        return "$true" if value else "$false"
    return f"'{value}'"


def resolve_home(rig: Rig, **params: str | bool) -> str:
    """Dot-source the script and print what Resolve-HermesHome returns for these inputs."""
    arguments = " ".join(f"-{name} {ps_literal(value)}" for name, value in params.items())
    command = f". '{SCRIPT}'; Resolve-HermesHome {arguments}"
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
        env=script_env(rig),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


HOME_CASES: list[tuple[str, dict[str, str | bool], str]] = [
    ("env-home", {"EnvHome": "/x/h"}, "/x/h"),
    ("env-profiles-parent", {"EnvHome": "/x/.hermes/profiles/work"}, "/x/.hermes"),
    ("env-wins-on-windows", {"EnvHome": "/x/h", "OnWindows": True, "RegistryHome": "/r/h"}, "/x/h"),
    ("windows-registry", {"OnWindows": True, "RegistryHome": "/r/h"}, "/r/h"),
    ("windows-localappdata", {"OnWindows": True, "LocalAppData": "/x/Local"}, "/x/Local/hermes"),
    (
        "windows-suffix",
        {"OnWindows": True, "LocalAppData": "/x/Local", "Suffix": "-dev"},
        "/x/Local/hermes-dev",
    ),
    (
        "windows-legacy-only",
        {
            "OnWindows": True,
            "LocalAppData": "/x/Local",
            "UserHome": "/x/u",
            "LegacyExists": True,
        },
        "/x/u/.hermes",
    ),
    (
        "windows-legacy-ignored-with-suffix",
        {
            "OnWindows": True,
            "LocalAppData": "/x/Local",
            "UserHome": "/x/u",
            "LegacyExists": True,
            "Suffix": "-dev",
        },
        "/x/Local/hermes-dev",
    ),
    (
        "windows-both-exist",
        {
            "OnWindows": True,
            "LocalAppData": "/x/Local",
            "UserHome": "/x/u",
            "DefaultExists": True,
            "LegacyExists": True,
        },
        "/x/Local/hermes",
    ),
    ("posix-default", {"UserHome": "/x/u"}, "/x/u/.hermes"),
    ("posix-suffix", {"UserHome": "/x/u", "Suffix": "-dev"}, "/x/u/.hermes-dev"),
]


@pytest.mark.parametrize(
    ("params", "expected"),
    [pytest.param(params, expected, id=case_id) for case_id, params, expected in HOME_CASES],
)
def test_resolve_hermes_home_follows_the_desktop_rule(
    rig: Rig, params: dict[str, str | bool], expected: str
) -> None:
    assert resolve_home(rig, **params) == expected


def test_default_home_on_linux_is_dot_hermes(rig: Rig) -> None:
    result = run_script(["-DryRun"], rig)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"home: {rig.root / 'user-home' / '.hermes'}" in dry_run_lines(result)


def test_env_hermes_home_wins(rig: Rig) -> None:
    home = rig.root / "env-home"

    result = run_script(["-DryRun"], rig, {"HERMES_HOME": str(home)})

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"home: {home}" in dry_run_lines(result)


def test_relative_hermes_home_is_refused(rig: Rig) -> None:
    result = run_script(["-HermesHome", "rel/path"], rig)

    assert result.returncode == 1
    assert "full path" in result.stderr
    assert not rig.log.exists()


@pytest.mark.parametrize("host", ["-oProxyCommand=touch x", "dev pc", "devpc;rm"])
def test_bad_host_is_refused(rig: Rig, host: str) -> None:
    home = rig.root / "home"

    result = run_script(["-HermesHome", str(home), f"-DevpcHost:{host}"], rig)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "refusing" in result.stderr
    assert not rig.log.exists()
    assert not home.exists()


def test_empty_host_name_is_refused(rig: Rig) -> None:
    command = f". '{SCRIPT}'; Test-DevpcHost -Name ''"
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
        env=script_env(rig),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )

    assert result.stdout.strip() == "False", result.stdout + result.stderr


@pytest.mark.parametrize("host", ["theo@devpc", "devpc.tail1234.ts.net"])
def test_good_host_passes_the_guard(rig: Rig, host: str) -> None:
    result = run_script(["-HermesHome", str(rig.root / "home"), "-DevpcHost", host, "-DryRun"], rig)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"copy: {host}:{REMOTE}" in dry_run_lines(result)


def test_dry_run_writes_nothing(rig: Rig) -> None:
    home = rig.root / "home"

    result = run_script(["-HermesHome", str(home), "-DryRun"], rig)

    assert result.returncode == 0, result.stdout + result.stderr
    lines = dry_run_lines(result)
    assert f"slot: {home / SLOT}" in lines
    assert "dry run: nothing written" in lines
    assert not home.exists()
    assert not rig.log.exists()


def test_plain_scp_is_the_fallback(rig: Rig) -> None:
    home = rig.root / "home"

    result = run_script(["-HermesHome", str(home)], rig, {"FAKE_SCP_FAIL_O": "1"})

    assert result.returncode == 0, result.stdout + result.stderr
    calls = rig.calls()
    assert calls == [
        f"-O -q devpc:{REMOTE} .plugin.js.new",
        f"-q devpc:{REMOTE} .plugin.js.new",
    ]
    assert (home / SLOT / "plugin.js").read_text(encoding="utf-8") == SOURCE_TEXT


def test_failed_copy_keeps_the_old_file(rig: Rig) -> None:
    home = rig.root / "home"
    target = seed_plugin(home)

    result = run_script(["-HermesHome", str(home)], rig, {"FAKE_SCP_FAIL_ALL": "1"})

    assert result.returncode == 1
    assert "scp failed" in result.stderr
    assert len(rig.calls()) == 2
    assert target.read_text(encoding="utf-8") == "old plugin bytes"
    assert slot_files(home) == ["plugin.js"]


@pytest.mark.parametrize("source_text", ["", "console.log(1)\n"], ids=["empty", "no-export"])
def test_file_without_export_default_is_refused(rig: Rig, source_text: str) -> None:
    home = rig.root / "home"
    target = seed_plugin(home)
    rig.source.write_text(source_text, encoding="utf-8")

    result = run_script(["-HermesHome", str(home)], rig)

    assert result.returncode == 1
    assert "export default" in result.stderr
    assert target.read_text(encoding="utf-8") == "old plugin bytes"
    assert slot_files(home) == ["plugin.js"]


def test_directory_in_place_of_plugin_js_is_refused(rig: Rig) -> None:
    home = rig.root / "home"
    (home / SLOT / "plugin.js").mkdir(parents=True)

    result = run_script(["-HermesHome", str(home)], rig)

    assert result.returncode == 1
    assert "directory" in result.stderr
    assert not rig.log.exists()


def test_second_run_gives_the_same_hash(rig: Rig) -> None:
    home = rig.root / "home"

    first = run_script(["-HermesHome", str(home)], rig)
    second = run_script(["-HermesHome", str(home)], rig)

    assert first.returncode == 0 and second.returncode == 0
    first_hash = [line for line in dry_run_lines(first) if line.startswith("sha256:")]
    second_hash = [line for line in dry_run_lines(second) if line.startswith("sha256:")]
    assert first_hash == second_hash == [f"sha256: {sha256_hex(SOURCE_TEXT)}"]
    assert slot_files(home) == ["plugin.js"]


def test_output_lines_come_in_order(rig: Rig) -> None:
    result = run_script(["-HermesHome", str(rig.root / "home")], rig)

    lines = dry_run_lines(result)
    labels = ["home:", "slot:", "copy:", "installed:", "sha256:"]
    positions = [
        next(i for i, line in enumerate(lines) if line.startswith(label)) for label in labels
    ]
    assert positions == sorted(positions)


def test_script_source_has_no_expression_runner_and_no_marker_file() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "Invoke-Expression" not in text
    assert "iex " not in text
    assert ".hermes-package.json" not in text


README = Path(__file__).resolve().parent.parent / "README.md"
LONG_DASHES = (chr(0x2014), chr(0x2013))


def readme_text() -> str:
    return README.read_text(encoding="utf-8")


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


@pytest.mark.parametrize("word", ["Mac", "Windows PC"])
def test_readme_has_steps_for_each_machine(word: str) -> None:
    body = section_after_heading(readme_text(), word)

    numbered = [line for line in body if re.match(r"\d+\. ", line)]
    assert [line.split(".")[0] for line in numbered][:2] == ["1", "2"]


def test_readme_names_the_script_and_its_parameters() -> None:
    text = readme_text()

    for needle in ("install-desktop.ps1", "pwsh -NoProfile -File", "-DevpcHost", "-DryRun"):
        assert needle in text


def test_readme_names_the_windows_home_and_the_reload() -> None:
    text = readme_text()

    assert "%LOCALAPPDATA%\\hermes" in text
    assert "~/.hermes/desktop-plugins/hermes-session-tasks/plugin.js" in text
    assert "Reload desktop plugins" in text


def test_readme_warns_that_closing_the_pane_disables_the_plugin() -> None:
    text = readme_text()

    assert "closing the only pane" in text.lower()
    assert "Reset layout" in text


def test_readme_has_no_long_dashes() -> None:
    text = readme_text()

    assert not any(dash in text for dash in LONG_DASHES)
