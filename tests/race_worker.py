"""Workers for the spawn race tests.

They live here and not in a test module, because the spawned child cannot import a test
module under `--import-mode=importlib`. Each worker opens its own store inside the child,
so only plain strings, ints and lists cross the process boundary.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Barrier
from typing import Any

from session_tasks.model import AddItem, Applied, BoardFull, SetChecked, SetText
from session_tasks.paths import connect_path
from session_tasks.store import BoardStore

BARRIER_WAIT_SECONDS = 30


def _store(db_path: str) -> BoardStore:
    return BoardStore(functools.partial(connect_path, db_path))


def _run(barrier: Barrier, queue: Queue[Any], body: Callable[[], tuple[Any, ...]]) -> None:
    """Wait for the start signal, run `body`, and always put exactly one result on the queue."""
    try:
        barrier.wait(BARRIER_WAIT_SECONDS)
        queue.put(body())
    except Exception as exc:
        queue.put(("error", repr(exc)))


def add_items(
    db_path: str, root_id: str, tag: str, count: int, barrier: Barrier, queue: Queue[Any]
) -> None:
    def body() -> tuple[Any, ...]:
        store = _store(db_path)
        applied = 0
        for n in range(count):
            result = store.apply(root_id, [AddItem(f"{tag}-{n}")], actor="agent", base_rev=0)
            applied += isinstance(result, Applied)
        return ("ok", applied)

    _run(barrier, queue, body)


def edit_own_items(
    db_path: str,
    root_id: str,
    item_ids: list[int],
    rounds: int,
    barrier: Barrier,
    queue: Queue[Any],
) -> None:
    def body() -> tuple[Any, ...]:
        store = _store(db_path)
        applied = stale = 0
        for rnd in range(rounds):
            for item_id in item_ids:
                base_rev = store.get_board(root_id).rev
                ops = [SetText(item_id, f"r{rnd}-{item_id}")]
                result = store.apply(root_id, ops, actor="user", base_rev=base_rev)
                if isinstance(result, Applied):
                    applied += 1
                else:
                    stale += 1
        return ("ok", applied, stale)

    _run(barrier, queue, body)


def check_one(
    db_path: str, root_id: str, item_id: int, base_rev: int, barrier: Barrier, queue: Queue[Any]
) -> None:
    def body() -> tuple[Any, ...]:
        result = _store(db_path).apply(
            root_id, [SetChecked(item_id, True)], actor="user", base_rev=base_rev
        )
        return ("applied",) if isinstance(result, Applied) else ("stale",)

    _run(barrier, queue, body)


def add_one(db_path: str, root_id: str, barrier: Barrier, queue: Queue[Any]) -> None:
    def body() -> tuple[Any, ...]:
        try:
            _store(db_path).apply(root_id, [AddItem("last seat")], actor="agent", base_rev=0)
        except BoardFull:
            return ("board_full",)
        return ("applied",)

    _run(barrier, queue, body)
