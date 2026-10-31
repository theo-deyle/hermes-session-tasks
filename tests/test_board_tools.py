"""`board_read` handler: empty board, blank session, spoofed argument, delegate, ordering."""

from __future__ import annotations

import json
from typing import Any

import pytest
from conftest import ResolverFor
from fakes import FakeReaderFactory, SessionSpec
from session_tasks.board_tools import BoardTools
from session_tasks.db import ConnFactory
from session_tasks.model import AddItem, RemoveItem
from session_tasks.results import NO_SESSION
from session_tasks.store import BoardStore


def tools_for(
    store: BoardStore, resolver_for: ResolverFor, specs: dict[str, SessionSpec] | None = None
) -> tuple[BoardTools, FakeReaderFactory]:
    resolver, factory = resolver_for(specs or {})
    return BoardTools(store, resolver), factory


def read(tools: BoardTools, session_id: str | None, args: dict[str, object] | None = None) -> Any:
    out = tools.board_read(args or {}, session_id=session_id)
    assert isinstance(out, str)
    return json.loads(out)


def count_rows(connect: ConnFactory, table: str) -> int:
    conn = connect()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_read_empty_board_returns_rev_zero_and_the_empty_note(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    tools, _ = tools_for(store, resolver_for)

    result = read(tools, "s1")

    assert result == {"ok": True, "rev": 0, "board": "", "note": "empty board"}
    assert count_rows(connect, "boards") == 0


def test_read_board_with_every_item_removed_keeps_its_rev_and_the_note(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)
    store.apply("s1", [RemoveItem(1)], actor="agent", base_rev=1)

    result = read(tools, "s1")

    assert result == {"ok": True, "rev": 2, "board": "", "note": "empty board"}


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_read_blank_session_returns_the_no_session_error(
    store: BoardStore, resolver_for: ResolverFor, blank: str | None
) -> None:
    tools, factory = tools_for(store, resolver_for)

    result = read(tools, blank)

    assert result == {"error": NO_SESSION}
    assert factory.opens == 0


def test_read_ignores_a_session_id_in_the_arguments(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("theirs")], actor="agent", base_rev=0)

    result = read(tools, "s1", {"session_id": "s2"})

    assert result["board"] == "- [ ] #1 mine\n"


def test_delegate_session_reads_the_delegator_board(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    specs = {
        "parent": SessionSpec(),
        "child": SessionSpec(parent="parent", model_config={"_delegate_from": "parent"}),
    }
    tools, _ = tools_for(store, resolver_for, specs)
    store.apply("parent", [AddItem("Call John")], actor="agent", base_rev=0)

    result = read(tools, "child")

    assert result == {"ok": True, "rev": 1, "board": "- [ ] #1 Call John\n"}


def test_read_keeps_two_equal_texts_as_two_items(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("Call John"), AddItem("Call John")], actor="agent", base_rev=0)

    result = read(tools, "s1")

    assert result["board"] == "- [ ] #1 Call John\n- [ ] #2 Call John\n"


def test_read_lists_subtasks_after_their_parent_in_display_order(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, _ = tools_for(store, resolver_for)
    store.apply("s1", [AddItem("parent"), AddItem("second")], actor="agent", base_rev=0)
    store.apply("s1", [AddItem("sub", parent_id=1)], actor="agent", base_rev=1)

    first = tools.board_read({}, session_id="s1")
    second = tools.board_read({}, session_id="s1")

    assert json.loads(first)["board"] == "- [ ] #1 parent\n  - [ ] #3 sub\n- [ ] #2 second\n"
    assert first == second
