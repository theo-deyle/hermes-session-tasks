"""Helpers that load `plugin_api.py` the way the Hermes dashboard host does, and call its routes."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fakes import FakeSessionReader
from fastapi import FastAPI
from fastapi.testclient import TestClient
from session_tasks import paths

CORE_KEY = "hermes_session_tasks_core"
MODULE_NAME = "hermes_dashboard_plugin_hermes-session-tasks"
PREFIX = "/api/plugins/hermes-session-tasks"
PLUGIN_API_PATH = Path(__file__).resolve().parent.parent / "plugin" / "dashboard" / "plugin_api.py"


def load_plugin_api() -> ModuleType:
    """Load the file by path, with no package, under the host module name (RESEARCH Answer 1)."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, PLUGIN_API_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(MODULE_NAME, None)
        raise
    return module


def unload_plugin_api() -> None:
    """Drop the router module and the core tree, so the next load starts clean."""
    sys.modules.pop(MODULE_NAME, None)
    for key in [k for k in sys.modules if k == CORE_KEY or k.startswith(CORE_KEY + ".")]:
        sys.modules.pop(key, None)


def make_client(module: ModuleType, api: object | None = None) -> TestClient:
    """Mount the router under the host prefix. An `api` replaces the one `get_api` builds."""
    app = FastAPI()
    app.include_router(module.router, prefix=PREFIX)
    if api is not None:
        app.dependency_overrides[module.get_api] = lambda: api
    return TestClient(app)


def _fake_module(monkeypatch: pytest.MonkeyPatch, name: str, **attributes: Any) -> None:
    module = ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def install_fake_hermes(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    """Fake the two Hermes modules the core imports, so no Hermes checkout is needed."""

    def plugin_db(name: str) -> Any:
        return paths.connect_path(db_path)

    def session_db(*args: Any, **kwargs: Any) -> FakeSessionReader:
        return FakeSessionReader({})

    _fake_module(monkeypatch, "plugins")
    _fake_module(monkeypatch, "plugins.plugin_storage", plugin_db=plugin_db)
    _fake_module(monkeypatch, "hermes_state", SessionDB=session_db)
