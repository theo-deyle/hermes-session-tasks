"""Several spawned processes write one SQLite file at once and lose nothing."""

from __future__ import annotations

import functools
import multiprocessing as mp
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

from race_worker import add_items, add_one, check_one, edit_own_items
from session_tasks.model import AddItem, Applied
from session_tasks.paths import connect_path, is_wal_reset_vulnerable
from session_tasks.store import BoardStore

ROOT = "root-1"


def run_workers(
    target: Callable[..., None], args_list: list[tuple[Any, ...]]
) -> list[tuple[Any, ...]]:
    """Start one spawned process per args tuple, release them together, collect one result each."""
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(len(args_list))
    queue = ctx.Queue()
    procs = [ctx.Process(target=target, args=(*args, barrier, queue)) for args in args_list]
    try:
        for proc in procs:
            proc.start()
        results = [queue.get(timeout=60) for _ in procs]
        for proc in procs:
            proc.join(timeout=30)
            assert proc.exitcode == 0
    finally:
        for proc in procs:
            if proc.is_alive():
                proc.kill()
    assert not [r for r in results if r[0] == "error"], results
    return results


def query(db_path: Path, sql: str) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(db_path)) as conn:
        return conn.execute(sql).fetchall()


def parent_store(db_path: Path) -> BoardStore:
    return BoardStore(functools.partial(connect_path, db_path))


def test_four_processes_fill_a_fresh_file_to_the_cap_with_no_lost_write(db_path: Path) -> None:
    args = [(str(db_path), ROOT, f"p{i}", 25) for i in range(4)]

    results = run_workers(add_items, args)

    assert sorted(results) == [("ok", 25)] * 4
    assert query(db_path, "SELECT id FROM items ORDER BY id") == [(n,) for n in range(1, 101)]
    assert query(db_path, "SELECT rev FROM boards") == [(100,)]
    assert query(db_path, "PRAGMA user_version") == [(1,)]
    assert query(db_path, "SELECT COUNT(*) FROM boards") == [(1,)]
    assert query(db_path, "SELECT COUNT(*) FROM aliases") == [(1,)]
    # Same gate as the store's own file: WAL unless the linked SQLite has the WAL-reset bug.
    assert query(db_path, "PRAGMA journal_mode") == [
        ("delete",) if is_wal_reset_vulnerable() else ("wal",)
    ]


def test_four_processes_edit_their_own_items_with_no_lost_update(db_path: Path) -> None:
    store = parent_store(db_path)
    for n in range(100):
        result = store.apply(ROOT, [AddItem(f"item {n}")], actor="agent", base_rev=n)
        assert isinstance(result, Applied)
    assert query(db_path, "SELECT rev FROM boards") == [(100,)]
    args = [(str(db_path), ROOT, list(range(1 + 25 * i, 26 + 25 * i)), 6) for i in range(4)]

    results = run_workers(edit_own_items, args)

    assert sorted(results) == [("ok", 150, 0)] * 4
    assert query(db_path, "SELECT rev FROM boards") == [(700,)]
    texts = query(db_path, "SELECT id, text FROM items ORDER BY id")
    assert texts == [(n, f"r5-{n}") for n in range(1, 101)]
    assert query(db_path, "SELECT COUNT(*) FROM changes") == [(100,)]


def test_two_processes_racing_one_item_end_with_one_applied_and_one_stale(
    tmp_path: Path,
) -> None:
    for round_number in range(3):
        db_path = tmp_path / f"race-{round_number}.db"
        store = parent_store(db_path)
        setup = store.apply(ROOT, [AddItem("race me")], actor="agent", base_rev=0)
        assert isinstance(setup, Applied)
        args = [(str(db_path), ROOT, 1, setup.rev)] * 2

        results = run_workers(check_one, args)

        assert sorted(results) == [("applied",), ("stale",)]
        assert query(db_path, "SELECT checked, rev FROM items WHERE id = 1") == [(1, 2)]


def test_two_processes_adding_at_99_items_end_with_one_add_and_one_board_full(
    db_path: Path,
) -> None:
    ops = [AddItem(f"item {n}") for n in range(99)]
    setup = parent_store(db_path).apply(ROOT, ops, actor="agent", base_rev=0)
    assert isinstance(setup, Applied)

    results = run_workers(add_one, [(str(db_path), ROOT)] * 2)

    assert sorted(results) == [("applied",), ("board_full",)]
    assert query(db_path, "SELECT COUNT(*) FROM items") == [(100,)]
