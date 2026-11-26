"""Version handshake data for GET /meta (D-29).

The backend version is the `version` line of `plugin.yaml`. `API_VERSION` is an integer
that bumps on any route or body change. The Desktop pane compares both with its own
constants and shows a banner on a mismatch.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from .paths import PLUGIN_NAME

API_VERSION = 1
UNKNOWN = "unknown"

_VERSION_LINE = re.compile(r"^version:\s*(\S+)\s*$", re.MULTILINE)

log = logging.getLogger(__name__)


def plugin_dir() -> Path:
    """The folder that holds `plugin.yaml`, one level above this package."""
    return Path(__file__).resolve().parent.parent


def read_backend_version(directory: Path) -> str:
    """Read the version line of `plugin.yaml` in `directory`. Never raises."""
    manifest = directory / "plugin.yaml"
    try:
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        log.warning("cannot read the backend version from %s: %s", manifest, exc)
        return UNKNOWN
    found = _VERSION_LINE.search(text)
    if found is None:
        log.warning("no version line in %s", manifest)
        return UNKNOWN
    return found.group(1)


def meta(directory: Path | None = None) -> dict[str, object]:
    """The GET /meta body. It holds no state and opens no data file."""
    return {
        "ok": True,
        "plugin_id": PLUGIN_NAME,
        "backend_version": read_backend_version(directory or plugin_dir()),
        "api_version": API_VERSION,
    }
