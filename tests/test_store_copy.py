"""BoardStore.copy_items: the copy batch, its guards, its journal rows and the seen rule."""

from __future__ import annotations

from contextlib import closing

from session_tasks import rows
from session_tasks.db import ConnFactory
from session_tasks.markdown import render
from session_tasks.model import AddItem, Change, CopyApplied
from session_tasks.store import BoardStore


def journal(connect: ConnFactory, root_id: str) -> tuple[Change, ...]:
    with closing(connect()) as conn:
        return rows.read_changes(conn, root_id)


def seed(store: BoardStore, root_id: str, *ops: AddItem) -> None:
    store.apply(root_id, list(ops), actor="agent", base_rev=0)


def test_copy_one_open_item_from_another_board(store: BoardStore, connect: ConnFactory) -> None:
    seed(store, "s2", AddItem("Call John"), AddItem("Book the van", checked=True))
    seed(store, "s1", AddItem("Mine"))
    source_before = store.get_board("s2")

    result = store.copy_items("s1", "s2", None, actor="agent")

    assert isinstance(result, CopyApplied)
    assert (result.copied, result.skipped, result.overflow) == (1, 0, 0)
    board = store.get_board("s1")
    assert render(board, include_ids=True) == "- [ ] #1 Mine\n- [ ] #2 Call John\n"
    copied = board.item(2)
    assert copied is not None
    assert copied.updated_by == "agent"
    assert copied.checked is False
    tail = journal(connect, "s1")[-2:]
    assert [(c.op, c.item_id, c.text, c.rev) for c in tail] == [
        ("add", 2, "Call John", board.rev),
        ("copied", 2, "s2#1", board.rev),
    ]
    assert store.get_board("s2") == source_before
