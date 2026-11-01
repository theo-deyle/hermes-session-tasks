"""Tests for scripts/install-desktop.ps1, run as `pwsh -File` with a fake scp first on PATH.

The fake scp is a bash script. It logs its arguments and copies FAKE_SCP_SOURCE to its last
argument, resolved against its working folder. It runs as a child process, so no socket opens.
"""

from __future__ import annotations

import hashlib
import os
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
