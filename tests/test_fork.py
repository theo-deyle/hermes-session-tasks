"""A branch starts with a copy of its parent board, taken once, on its first touch."""

from __future__ import annotations

import logging
import multiprocessing as mp
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from conftest import ResolverFor
from fakes import SEVEN_ROW_FIXTURE, SessionSpec
from fork_race_worker import resolve_branch
from session_tasks.lineage import Resolution
from session_tasks.markdown import render
from session_tasks.model import AddItem, Applied, Board, RemoveItem, SetChecked, SetText
from session_tasks.store import BoardStore

TABLES = ("boards", "items", "aliases", "changes")
PARENT = "root"
BRANCH = "br"


def query(db_path: Path, sql: str) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(db_path)) as conn:
        return conn.execute(sql).fetchall()


def table_counts(db_path: Path) -> dict[str, int]:
    return {name: query(db_path, f"SELECT COUNT(*) FROM {name}")[0][0] for name in TABLES}


def applied(result: object) -> Applied:
    assert isinstance(result, Applied)
    return result


def seed_parent(store: BoardStore, root_id: str = PARENT) -> Board:
    """Build a parent board with ids 3, 5, 7 and 8 left after removes, one subtask and one check."""
    for text in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"):
        applied(store.apply(root_id, [AddItem(text)], actor="agent", base_rev=0))
    rev = store.get_board(root_id).rev
    applied(store.apply(root_id, [RemoveItem(n) for n in (1, 2, 4, 6)], actor="user", base_rev=rev))
    rev = store.get_board(root_id).rev
    ops = [AddItem("echo sub", parent_id=5), SetChecked(3, True)]
    applied(store.apply(root_id, ops, actor="user", base_rev=rev))
    return store.get_board(root_id)


def run_resolvers(db_path: Path, count: int) -> list[tuple[Any, ...]]:
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(count)
    queue = ctx.Queue()
    procs = [
        ctx.Process(target=resolve_branch, args=(str(db_path), BRANCH, barrier, queue))
        for _ in range(count)
    ]
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
    return results


def test_first_read_of_a_branch_copies_the_parent_board_with_new_ids(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    parent = seed_parent(store)
    assert sorted(item.id for item in parent.items) == [3, 5, 7, 8]
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)

    resolution = resolver.resolve(BRANCH)
    branch = store.get_board(BRANCH)

    assert resolution == Resolution(BRANCH, "branch", forked_from=PARENT)
    assert [item.id for item in branch.items] == [1, 2, 3, 4]
    assert [item.text for item in branch.items] == [
        "charlie",
        "echo",
        "echo sub",
        "golf",
    ]
    assert [item.checked for item in branch.items] == [True, False, False, False]
    assert [item.parent_id for item in branch.items] == [None, None, 2, None]
    assert {item.rev for item in branch.items} == {1}
    assert branch.next_item_id == 5
    assert branch.rev == 1
    assert branch.forked_from == PARENT
    assert query(
        db_path, f"SELECT rev, actor, op, item_id, text FROM changes WHERE root_id = '{BRANCH}'"
    ) == [(1, "agent", "forked", None, PARENT)]
    assert query(db_path, f"SELECT root_id FROM aliases WHERE session_id = '{BRANCH}'") == [
        (BRANCH,)
    ]


def test_branch_copy_keeps_display_order_and_parent_links(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    parent = seed_parent(store)
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)

    resolver.resolve(BRANCH)
    branch = store.get_board(BRANCH)

    assert render(branch, include_ids=False) == render(parent, include_ids=False)
    assert [(i.position, i.updated_by) for i in branch.items] == [
        (i.position, i.updated_by) for i in parent.items
    ]
    assert [(i.created_at, i.updated_at) for i in branch.items] == [
        (i.created_at, i.updated_at) for i in parent.items
    ]


def test_branch_whose_parent_is_a_compression_tip_copies_the_chain_root_board(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    seed_parent(store)
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)

    resolver.resolve(BRANCH)

    assert SEVEN_ROW_FIXTURE[BRANCH].parent == "comp2"
    assert store.get_board(BRANCH).forked_from == PARENT
    assert store.get_board("comp2").items == ()
    assert len(store.get_board(BRANCH).items) == 4


def test_branch_and_parent_resolve_to_different_roots(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    seed_parent(store)
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)

    assert resolver.resolve(BRANCH).root_id == BRANCH
    assert resolver.resolve("comp2").root_id == PARENT
    assert resolver.resolve(PARENT).root_id == PARENT


def test_branch_edits_do_not_reach_the_parent_and_the_reverse(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    parent = seed_parent(store)
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)
    resolver.resolve(BRANCH)
    branch = store.get_board(BRANCH)

    applied(store.apply(BRANCH, [SetText(1, "branch only")], actor="user", base_rev=branch.rev))
    assert store.get_board(PARENT) == parent

    branch_after = store.get_board(BRANCH)
    applied(store.apply(PARENT, [SetText(3, "parent only")], actor="user", base_rev=parent.rev))
    assert store.get_board(BRANCH) == branch_after
    assert resolver.resolve(BRANCH).root_id == BRANCH


def test_branch_read_when_the_parent_has_no_board_writes_nothing(
    resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)

    resolution = resolver.resolve(BRANCH)

    assert resolution == Resolution(BRANCH, "branch", forked_from=PARENT)
    assert table_counts(db_path) == dict.fromkeys(TABLES, 0)


def test_branch_copies_on_a_later_read_after_the_parent_gets_a_board(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    resolver, _ = resolver_for(SEVEN_ROW_FIXTURE)
    resolver.resolve(BRANCH)
    assert table_counts(db_path)["boards"] == 0

    applied(store.apply(PARENT, [AddItem("Call John")], actor="agent", base_rev=0))
    resolver.resolve(BRANCH)

    assert render(store.get_board(BRANCH), include_ids=False) == "- [ ] Call John\n"
    assert store.get_board(BRANCH).forked_from == PARENT


def test_second_resolve_of_a_copied_branch_copies_nothing(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    seed_parent(store)
    resolver, factory = resolver_for(SEVEN_ROW_FIXTURE)
    resolver.resolve(BRANCH)
    before = table_counts(db_path)
    opens = factory.opens

    second = resolver.resolve(BRANCH)

    assert second == Resolution(BRANCH, "plain")
    assert table_counts(db_path) == before
    assert factory.opens == opens
    assert store.get_board(BRANCH).forked_from == PARENT


def test_branch_of_a_branch_copies_through_the_middle_branch(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    seed_parent(store, "a")
    resolver, _ = resolver_for({
        "a": SessionSpec(),
        "b": SessionSpec(parent="a", model_config={"_branched_from": "a"}),
        "c": SessionSpec(parent="b", model_config={"_branched_from": "b"}),
    })

    resolution = resolver.resolve("c")

    assert resolution == Resolution("c", "branch", forked_from="b")
    middle, last = store.get_board("b"), store.get_board("c")
    assert middle.forked_from == "a"
    assert last.forked_from == "b"
    assert render(last, include_ids=False) == render(store.get_board("a"), include_ids=False)


def test_branch_cycle_writes_nothing_and_raises_nothing(
    resolver_for: ResolverFor, db_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    resolver, _ = resolver_for({
        "x": SessionSpec(parent="y", model_config={"_branched_from": "y"}),
        "y": SessionSpec(parent="x", model_config={"_branched_from": "x"}),
    })

    with caplog.at_level(logging.WARNING):
        resolution = resolver.resolve("x")

    assert resolution == Resolution("x", "plain")
    assert table_counts(db_path) == dict.fromkeys(TABLES, 0)
    assert "loops" in caplog.text


def test_branch_chain_longer_than_the_hop_limit_writes_nothing(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    specs = {"s0": SessionSpec()}
    for n in range(1, 25):
        specs[f"s{n}"] = SessionSpec(
            parent=f"s{n - 1}", model_config={"_branched_from": f"s{n - 1}"}
        )
    applied(store.apply("s0", [AddItem("Call John")], actor="agent", base_rev=0))
    before = table_counts(db_path)
    resolver, _ = resolver_for(specs)

    assert resolver.resolve("s24") == Resolution("s24", "plain")
    assert table_counts(db_path) == before


def test_two_processes_resolving_one_branch_copy_it_once(store: BoardStore, db_path: Path) -> None:
    seed_parent(store)

    results = run_resolvers(db_path, 4)

    assert not [r for r in results if r[0] == "error"], results
    assert {root_id for root_id, _ in results} == {BRANCH}
    assert query(db_path, f"SELECT COUNT(*) FROM boards WHERE root_id = '{BRANCH}'") == [(1,)]
    assert query(
        db_path, f"SELECT COUNT(*) FROM changes WHERE root_id = '{BRANCH}' AND op = 'forked'"
    ) == [(1,)]
    assert query(db_path, f"SELECT id FROM items WHERE root_id = '{BRANCH}' ORDER BY id") == [
        (1,),
        (2,),
        (3,),
        (4,),
    ]


COMPRESSED_BRANCH_FIXTURE: dict[str, SessionSpec] = {
    **SEVEN_ROW_FIXTURE,
    "br": replace(SEVEN_ROW_FIXTURE["br"], end_reason="compression"),
    "br2": SessionSpec(parent="br"),
}


def test_branch_compressed_before_its_first_touch_still_gets_the_parent_copy(
    store: BoardStore, resolver_for: ResolverFor, db_path: Path
) -> None:
    parent = seed_parent(store)
    resolver, _ = resolver_for(COMPRESSED_BRANCH_FIXTURE)

    resolution = resolver.resolve("br2")
    branch = store.get_board(BRANCH)

    assert resolution == Resolution(BRANCH, "compression")
    assert render(branch, include_ids=False) == render(parent, include_ids=False)
    assert branch.forked_from == PARENT
    sql = "SELECT session_id, root_id FROM aliases WHERE session_id LIKE 'br%' ORDER BY 1"
    assert query(db_path, sql) == [("br", BRANCH), ("br2", BRANCH)]
