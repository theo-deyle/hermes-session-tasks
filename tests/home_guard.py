"""Session guard for the real Hermes plugin data directory.

This plugin writes only `<HERMES_HOME>/plugin-data/hermes-session-tasks`. A test run that
creates that directory, or an entry under it, in the real home is a bug. The hooks here
take a snapshot of entry names at session start and compare it at session finish. They read
names only and never open a file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

WATCHED = Path("plugin-data") / "hermes-session-tasks"
SIDECAR_ENDINGS = ("-wal", "-shm", "-journal")

Snapshot = frozenset[str] | None
_SNAPSHOTS: pytest.StashKey[dict[Path, Snapshot]] = pytest.StashKey()


def real_home_roots() -> tuple[Path, ...]:
    """The real Hermes home paths: `~/.hermes`, plus `HERMES_HOME` when set and different."""
    roots = [Path.home() / ".hermes"]
    configured = os.environ.get("HERMES_HOME")
    if configured and Path(configured) not in roots:
        roots.append(Path(configured))
    return tuple(roots)


def snapshot(root: Path) -> Snapshot:
    """Paths of the watched directory and every entry under it, relative to `root`.

    Returns None when the watched directory does not exist.
    """
    watched = root / WATCHED
    if not watched.is_dir():
        return None
    entries = {WATCHED.as_posix()}
    for current, directories, files in os.walk(watched):
        for name in (*directories, *files):
            if name.endswith(SIDECAR_ENDINGS):
                continue
            entries.add((Path(current) / name).relative_to(root).as_posix())
    return frozenset(entries)


def new_entries(before: Snapshot, after: Snapshot) -> tuple[str, ...]:
    """Sorted paths in `after` that are not in `before`. None counts as empty."""
    return tuple(sorted((after or frozenset()) - (before or frozenset())))


def pytest_sessionstart(session: pytest.Session) -> None:
    # Runs before any fixture, so the autouse HERMES_HOME fixture has not changed the environment.
    session.config.stash[_SNAPSHOTS] = {root: snapshot(root) for root in real_home_roots()}


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    before = session.config.stash.get(_SNAPSHOTS, {})
    gained: list[str] = []
    for root, earlier in before.items():
        gained.extend(new_entries(earlier, snapshot(root)))
    if gained:
        sys.stderr.write(f"real Hermes home gained: {', '.join(sorted(gained))}\n")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
