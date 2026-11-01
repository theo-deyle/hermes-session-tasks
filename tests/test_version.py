"""GET /meta hands the backend version and the API version to the Desktop pane (API-03, D-29)."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from api_client import PREFIX, load_plugin_api, make_client, unload_plugin_api
from session_tasks import paths, version

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "plugin" / "plugin.yaml"
PYPROJECT = ROOT / "pyproject.toml"
VERSION_LINE = re.compile(r"^version:\s*(\S+)\s*$", re.MULTILINE)
PYPROJECT_LINE = re.compile(r'^version\s*=\s*"([^"]+)"\s*$', re.MULTILINE)


def manifest_value(key: str) -> str:
    """Read one scalar key of the flat manifest. Only `version` is needed today."""
    assert key == "version"
    found = VERSION_LINE.search(MANIFEST.read_text(encoding="utf-8"))
    assert found is not None, f"manifest has no {key} line"
    return found.group(1)


@pytest.fixture(autouse=True)
def clean_core() -> Iterator[None]:
    unload_plugin_api()
    yield
    unload_plugin_api()


def test_meta_route_returns_both_versions() -> None:
    client = make_client(load_plugin_api())

    reply = client.get(PREFIX + "/meta")

    assert reply.status_code == 200
    assert reply.json() == {
        "ok": True,
        "plugin_id": "hermes-session-tasks",
        "backend_version": "0.1.0",
        "api_version": 1,
    }


def test_backend_version_matches_the_manifest() -> None:
    assert version.read_backend_version(version.plugin_dir()) == manifest_value("version")
    assert version.plugin_dir() == MANIFEST.parent


def test_pyproject_version_matches_the_manifest() -> None:
    found = PYPROJECT_LINE.search(PYPROJECT.read_text(encoding="utf-8"))
    assert found is not None
    assert found.group(1) == manifest_value("version")


@pytest.mark.parametrize(
    "manifest_text",
    [None, "name: hermes-session-tasks\ndescription: no version line here\n"],
    ids=["no-manifest-file", "no-version-line"],
)
def test_missing_manifest_gives_unknown(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, manifest_text: str | None
) -> None:
    if manifest_text is not None:
        (tmp_path / "plugin.yaml").write_text(manifest_text, encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        found = version.read_backend_version(tmp_path)

    assert found == "unknown"
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1


def test_unreadable_manifest_gives_unknown(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "plugin.yaml").mkdir()

    with caplog.at_level(logging.WARNING):
        found = version.read_backend_version(tmp_path)

    assert found == "unknown"
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_meta_holds_no_state_and_opens_no_data_file(hermes_home: Path) -> None:
    client = make_client(load_plugin_api())

    first = client.get(PREFIX + "/meta")
    second = client.get(PREFIX + "/meta")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert not (hermes_home / "plugin-data").exists()


def test_meta_with_no_manifest_answers_unknown(tmp_path: Path) -> None:
    body = version.meta(tmp_path)

    assert body["backend_version"] == "unknown"
    assert body["ok"] is True
    assert body["plugin_id"] == paths.PLUGIN_NAME
    assert body["api_version"] == version.API_VERSION


PLUGIN_JS = ROOT / "plugin" / "desktop" / "plugin.js"
JS_PLUGIN_VERSION = re.compile(r"^const PLUGIN_VERSION = '([^']+)'$", re.MULTILINE)
JS_API_VERSION = re.compile(r"^const API_VERSION = (\d+)$", re.MULTILINE)


def test_pane_plugin_version_matches_the_manifest() -> None:
    found = JS_PLUGIN_VERSION.search(PLUGIN_JS.read_text(encoding="utf-8"))

    assert found is not None, "plugin.js has no PLUGIN_VERSION constant"
    assert found.group(1) == manifest_value("version")


def test_pane_api_version_matches_the_backend() -> None:
    found = JS_API_VERSION.search(PLUGIN_JS.read_text(encoding="utf-8"))

    assert found is not None, "plugin.js has no API_VERSION constant"
    assert int(found.group(1)) == version.API_VERSION
