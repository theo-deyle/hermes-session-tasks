"""Session guard for the real Hermes plugin data directory.

This plugin writes only `<HERMES_HOME>/plugin-data/hermes-session-tasks`. A test run that
creates that directory, or an entry under it, in the real home is a bug. A test run that
rewrites a file that already exists there is the same bug. The hooks here take a snapshot at
session start and compare it at session finish. The snapshot holds each entry name with the
size and change time of a file. The hooks never open a file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

WATCHED = Path("plugin-data") / "hermes-session-tasks"
SIDECAR_ENDINGS = ("-wal", "-shm", "-journal")

Stamp = tuple[int, int]
Snapshot = dict[str, Stamp] | None
DIRECTORY_STAMP: Stamp = (0, 0)
_SNAPSHOTS: pytest.StashKey[dict[Path, Snapshot]] = pytest.StashKey()


def real_home_roots() -> tuple[Path, ...]:
    """The real Hermes home paths: `~/.hermes`, plus `HERMES_HOME` when set and different."""
    roots = [Path.home() / ".hermes"]
    configured = os.environ.get("HERMES_HOME")
    if configured and Path(configured) not in roots:
        roots.append(Path(configured))
    return tuple(roots)


def snapshot(root: Path) -> Snapshot:
    """Map each path of the watched directory to a stamp, relative to `root`.

    A file stamp is (size, mtime_ns). A directory stamp is fixed, because a directory time
    changes when a sidecar file comes and goes. Returns None when the directory is missing.
    """
    watched = root / WATCHED
    if not watched.is_dir():
        return None
    entries: dict[str, Stamp] = {WATCHED.as_posix(): DIRECTORY_STAMP}
    for current, directories, files in os.walk(watched):
        for name in directories:
            path = Path(current) / name
            entries[path.relative_to(root).as_posix()] = DIRECTORY_STAMP
        for name in files:
            if name.endswith(SIDECAR_ENDINGS):
                continue
            path = Path(current) / name
            stat = path.stat()
            entries[path.relative_to(root).as_posix()] = (stat.st_size, stat.st_mtime_ns)
    return entries


def new_entries(before: Snapshot, after: Snapshot) -> tuple[str, ...]:
    """Sorted paths in `after` that are new or whose stamp changed. None counts as empty."""
    earlier = before or {}
    return tuple(
        sorted(path for path, stamp in (after or {}).items() if earlier.get(path) != stamp)
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    # Runs before any fixture, so the autouse HERMES_HOME fixture has not changed the environment.
    session.config.stash[_SNAPSHOTS] = {root: snapshot(root) for root in real_home_roots()}


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    before = session.config.stash.get(_SNAPSHOTS, {})
    gained: list[str] = []
    for root, earlier in before.items():
        gained.extend(new_entries(earlier, snapshot(root)))
    if gained:
        sys.stderr.write(f"real Hermes home changed: {', '.join(sorted(gained))}\n")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
