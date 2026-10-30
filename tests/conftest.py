"""Shared fixtures: tmp Hermes home, no network, fake clock, hermes marker skip."""

from __future__ import annotations

import functools
import os
import socket
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeAlias

import pytest
from fakes import FakeReaderFactory, SessionSpec
from session_tasks import paths
from session_tasks.db import ConnFactory
from session_tasks.lineage import SessionResolver
from session_tasks.store import BoardStore

pytest_plugins = ["home_guard"]

HERMES_AGENT_REPO = Path(
    os.environ.get("HERMES_AGENT_REPO", str(Path.home() / ".hermes" / "hermes-agent"))
).expanduser()
CLOCK_START = datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)
INTERNET_FAMILIES = (socket.AF_INET, socket.AF_INET6)


class FakeClock:
    """Each call returns the next microsecond after 2026-10-30T12:00:00.000000Z."""

    def __init__(self) -> None:
        self._ticks = 0

    def __call__(self) -> str:
        self._ticks += 1
        moment = CLOCK_START + timedelta(microseconds=self._ticks)
        return moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@pytest.fixture(autouse=True)
def hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every Hermes path at a tmp directory, never at the real ~/.hermes."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raise on an outbound AF_INET or AF_INET6 connect. AF_UNIX passes."""
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guarded_connect(self: socket.socket, address: Any) -> None:
        if self.family in INTERNET_FAMILIES:
            raise RuntimeError(f"network access blocked in tests: {address!r}")
        real_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: Any) -> int:
        if self.family in INTERNET_FAMILIES:
            raise RuntimeError(f"network access blocked in tests: {address!r}")
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "data.db"


@pytest.fixture
def connect(db_path: Path) -> ConnFactory:
    """Open the tmp data file the way production code opens it, one connection per call."""
    return functools.partial(paths.connect_path, db_path)


@pytest.fixture
def store(connect: ConnFactory, clock: FakeClock) -> BoardStore:
    return BoardStore(connect, clock)


ResolverFor: TypeAlias = Callable[
    [dict[str, SessionSpec]], tuple[SessionResolver, FakeReaderFactory]
]


@pytest.fixture
def resolver_for(connect: ConnFactory, clock: FakeClock) -> ResolverFor:
    """Build a resolver over fake sessions. The factory counts reader opens."""

    def build(specs: dict[str, SessionSpec]) -> tuple[SessionResolver, FakeReaderFactory]:
        factory = FakeReaderFactory(specs)
        return SessionResolver(connect, factory, clock), factory

    return build


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if HERMES_AGENT_REPO.is_dir():
        return
    skip = pytest.mark.skip(reason=f"hermes-agent checkout not found at {HERMES_AGENT_REPO}")
    for item in items:
        if "hermes" in item.keywords:
            item.add_marker(skip)
