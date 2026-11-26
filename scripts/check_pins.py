"""Pin gate: compare the dev-group pins with uv.lock, the gateway venv and the Hermes pins.

Run it before the first `uv sync` and in every check.sh run. It uses the standard
library only, so it runs without the project environment.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = "https://pypi.org/simple"
GATEWAY_PACKAGES = ("fastapi", "starlette", "pydantic", "httpx")
HERMES_PINNED_TOOLS = ("pytest", "ruff")
PIP_TIMEOUT_SECONDS = 60


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_dev_pins(pyproject: Path) -> dict[str, str]:
    """Return {package: version} for every `name==version` entry of the dev group."""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    pins: dict[str, str] = {}
    for entry in data.get("dependency-groups", {}).get("dev", []):
        match = re.fullmatch(r"\s*([A-Za-z0-9._-]+)\s*==\s*([^\s;]+)\s*", str(entry))
        if match is None:
            raise ValueError(f"dev entry is not an exact pin: {entry!r}")
        pins[normalize(match.group(1))] = match.group(2)
    return pins


def read_lock(lock: Path) -> tuple[dict[str, str], list[str]]:
    """Return ({package: version}, [findings]) for uv.lock, without the project entry."""
    data = tomllib.loads(lock.read_text(encoding="utf-8"))
    versions: dict[str, str] = {}
    findings: list[str] = []
    for package in data.get("package", []):
        name = normalize(package["name"])
        source = package.get("source", {})
        if "virtual" in source or "editable" in source:
            continue
        versions[name] = package.get("version", "")
        if source.get("registry") != REGISTRY:
            findings.append(f"source: {name} is not from {REGISTRY}: {source!r}")
    return versions, findings


def compare_lock(pins: dict[str, str], locked: dict[str, str]) -> list[str]:
    findings: list[str] = []
    for name, version in sorted(pins.items()):
        if locked.get(name) != version:
            findings.append(f"lock: {name} pin {version} but uv.lock has {locked.get(name)}")
    return findings


def hermes_repo() -> Path:
    default = Path.home() / ".hermes" / "hermes-agent"
    return Path(os.environ.get("HERMES_AGENT_REPO", str(default))).expanduser()


def gateway_versions(repo: Path) -> tuple[dict[str, str] | None, str]:
    """Return ({package: version}, reason). The dict is None when the venv cannot be read."""
    python = repo / "venv" / "bin" / "python"
    if not python.is_file():
        return None, f"gateway venv python not found at {python}"
    try:
        result = subprocess.run(
            [str(python), "-m", "pip", "list", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=PIP_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "gateway pip list timed out"
    if result.returncode != 0:
        return None, f"gateway pip list exited {result.returncode}"
    rows = json.loads(result.stdout)
    return {normalize(row["name"]): row["version"] for row in rows}, ""


def compare_gateway(pins: dict[str, str], gateway: dict[str, str]) -> list[str]:
    findings: list[str] = []
    for name in GATEWAY_PACKAGES:
        if gateway.get(name) != pins.get(name):
            findings.append(
                f"gateway: {name} pin {pins.get(name)} but gateway has {gateway.get(name)}"
            )
    return findings


def compare_hermes_pins(pins: dict[str, str], hermes_pyproject: Path) -> list[str]:
    text = hermes_pyproject.read_text(encoding="utf-8")
    findings: list[str] = []
    for name in HERMES_PINNED_TOOLS:
        match = re.search(rf'["\']{re.escape(name)}==([^"\'\s]+)["\']', text)
        hermes_version = match.group(1) if match else None
        if hermes_version != pins.get(name):
            findings.append(f"hermes: {name} pin {pins.get(name)} but hermes pins {hermes_version}")
    return findings


def main() -> int:
    pins = read_dev_pins(ROOT / "pyproject.toml")
    lock_path = ROOT / "uv.lock"
    if not lock_path.is_file():
        print("lock: uv.lock is missing; run `uv lock` first")
        return 1
    locked, findings = read_lock(lock_path)
    findings.extend(compare_lock(pins, locked))

    repo = hermes_repo()
    if not (repo / "pyproject.toml").is_file():
        print(f"skip: hermes checkout not found at {repo}")
    else:
        gateway, reason = gateway_versions(repo)
        if gateway is None:
            print(f"skip: {reason}")
        else:
            findings.extend(compare_gateway(pins, gateway))
        findings.extend(compare_hermes_pins(pins, repo / "pyproject.toml"))

    for finding in findings:
        print(finding)
    if findings:
        return 1
    print("pins ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
