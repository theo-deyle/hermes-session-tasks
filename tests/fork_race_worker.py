"""Worker for the branch fork race test.

It lives here and not in a test module, because the spawned child cannot import a test
module under `--import-mode=importlib`. The child builds its own resolver, so only plain
strings cross the process boundary.
"""

from __future__ import annotations

import functools
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Barrier
from typing import Any

from fakes import SEVEN_ROW_FIXTURE, FakeReaderFactory
from session_tasks.lineage import SessionResolver
from session_tasks.paths import connect_path

BARRIER_WAIT_SECONDS = 30


def resolve_branch(db_path: str, branch_id: str, barrier: Barrier, queue: Queue[Any]) -> None:
    """Wait for the start signal, resolve `branch_id`, and put exactly one result on the queue."""
    try:
        resolver = SessionResolver(
            functools.partial(connect_path, db_path), FakeReaderFactory(SEVEN_ROW_FIXTURE)
        )
        barrier.wait(BARRIER_WAIT_SECONDS)
        resolution = resolver.resolve(branch_id)
        queue.put((resolution.root_id, resolution.kind))
    except Exception as exc:
        queue.put(("error", repr(exc)))
