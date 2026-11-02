"""The seen mark: unseen Theo changes, the journal gap rule and the agent batch advance."""

from __future__ import annotations

from contextlib import closing

from session_tasks import fork
from session_tasks.db import ConnFactory
from session_tasks.model import JOURNAL_KEEP, AddItem, SetChecked, SetText
from session_tasks.rows import Unseen
from session_tasks.store import BoardStore

ROOT = "root-1"
HALF = JOURNAL_KEEP // 2 + 10


def seen_rev(connect: ConnFactory, root_id: str = ROOT) -> int:
    with closing(connect()) as conn:
        row = conn.execute("SELECT agent_seen_rev FROM boards WHERE root_id = ?", (root_id,))
        return int(row.fetchone()[0])


def agent_add(store: BoardStore, text: str, base_rev: int) -> None:
    store.apply(ROOT, [AddItem(text)], actor="agent", base_rev=base_rev)


def two_theo_batches(store: BoardStore, between: int | None = None) -> BoardStore:
    """Write 60 adds at rev 1 and 60 renames at rev 2, both as Theo. Optionally mark in between."""
    adds = [AddItem(f"item {index}") for index in range(HALF)]
    store.apply(ROOT, adds, actor="user", base_rev=0)
    if between is not None:
        store.mark_seen(ROOT, between)
    renames = [SetText(index, f"item {index} renamed") for index in range(1, HALF + 1)]
    store.apply(ROOT, renames, actor="user", base_rev=1)
    return store


def test_unknown_board_has_no_unseen_changes(store: BoardStore) -> None:
    assert store.unseen_changes("nobody") is None


def test_board_at_its_seen_rev_has_no_unseen_changes(store: BoardStore) -> None:
    agent_add(store, "Call John", 0)

    assert store.unseen_changes(ROOT) is None


def test_a_user_write_is_unseen_with_one_change(store: BoardStore) -> None:
    store.apply(ROOT, [AddItem("Call John")], actor="user", base_rev=0)

    unseen = store.unseen_changes(ROOT)

    assert isinstance(unseen, Unseen)
    assert (unseen.rev, unseen.seen_rev, unseen.covered) == (1, 0, True)
    assert [(c.actor, c.op, c.item_id, c.text) for c in unseen.changes] == [
        ("user", "add", 1, "Call John")
    ]


def test_agent_rows_are_left_out(store: BoardStore, connect: ConnFactory) -> None:
    store.apply(ROOT, [AddItem("Call John")], actor="user", base_rev=0)
    store.mark_seen(ROOT, 1)
    agent_add(store, "Book the van", 1)
    store.apply(ROOT, [AddItem("Pay the invoice")], actor="agent", base_rev=2)
    store.apply(ROOT, [SetChecked(1, True)], actor="user", base_rev=3)

    unseen = store.unseen_changes(ROOT)

    assert unseen is not None
    assert [(c.actor, c.op, c.item_id) for c in unseen.changes] == [("user", "check", 1)]


def test_mark_seen_never_moves_down(store: BoardStore, connect: ConnFactory) -> None:
    agent_add(store, "Call John", 0)

    store.mark_seen(ROOT, 5)
    store.mark_seen(ROOT, 3)

    assert seen_rev(connect) == 5


def test_an_agent_batch_on_a_seen_board_advances_seen(
    store: BoardStore, connect: ConnFactory
) -> None:
    agent_add(store, "Call John", 0)
    assert seen_rev(connect) == 1

    agent_add(store, "Book the van", 1)

    assert seen_rev(connect) == 2


def test_agent_edit_after_a_theo_edit_keeps_the_theo_change(
    store: BoardStore, connect: ConnFactory
) -> None:
    agent_add(store, "Call John", 0)
    store.apply(ROOT, [SetChecked(1, True)], actor="user", base_rev=1)
    agent_add(store, "Book the van", 2)

    unseen = store.unseen_changes(ROOT)

    assert seen_rev(connect) == 1
    assert unseen is not None
    assert (unseen.rev, unseen.seen_rev) == (3, 1)
    assert [(c.actor, c.op, c.item_id) for c in unseen.changes] == [("user", "check", 1)]


def test_a_user_write_never_moves_seen(store: BoardStore, connect: ConnFactory) -> None:
    agent_add(store, "Call John", 0)

    store.apply(ROOT, [SetChecked(1, True)], actor="user", base_rev=1)

    assert seen_rev(connect) == 1


def test_journal_below_the_keep_count_is_covered(store: BoardStore) -> None:
    store.apply(
        ROOT, [AddItem(f"item {i}") for i in range(JOURNAL_KEEP - 1)], actor="user", base_rev=0
    )

    unseen = store.unseen_changes(ROOT)

    assert unseen is not None
    assert unseen.covered is True


def test_exactly_100_rows_with_the_oldest_rev_one_above_seen_is_not_covered(
    store: BoardStore,
) -> None:
    two_theo_batches(store)

    unseen = store.unseen_changes(ROOT)

    assert unseen is not None
    assert (unseen.rev, unseen.seen_rev) == (2, 0)
    assert unseen.covered is False


def test_exactly_100_rows_with_the_oldest_rev_at_seen_is_covered(store: BoardStore) -> None:
    two_theo_batches(store, between=1)

    unseen = store.unseen_changes(ROOT)

    assert unseen is not None
    assert (unseen.rev, unseen.seen_rev) == (2, 1)
    assert unseen.covered is True


def test_a_forked_board_has_no_unseen_change(store: BoardStore, connect: ConnFactory) -> None:
    agent_add(store, "Call John", 0)

    assert fork.fork_copy(connect, "branch-1", ROOT, store.clock) is True
    unseen = store.unseen_changes("branch-1")

    assert unseen == Unseen(rev=1, seen_rev=0, changes=(), covered=True)
