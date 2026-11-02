"""Cross-session tools: board_copy, the cross board_read and board_sessions."""

from __future__ import annotations

import json
from typing import Any

from conftest import ResolverFor
from fakes import FakeReaderFactory, SessionSpec
from session_tasks.board_tools import BoardTools
from session_tasks.model import AddItem
from session_tasks.store import BoardStore
from session_tasks.titles import TitleLookup

Calls = list[tuple[str, str, int]]


def cross_tools(
    store: BoardStore, resolver_for: ResolverFor, specs: dict[str, SessionSpec]
) -> tuple[BoardTools, Calls, FakeReaderFactory]:
    """Build tools whose resolver and title lookup share one reader factory."""
    resolver, factory = resolver_for(specs)
    calls: Calls = []

    def record(root_id: str, session_id: str, rev: int) -> None:
        calls.append((root_id, session_id, rev))

    tools = BoardTools(store, resolver, after_write=record, titles=TitleLookup(factory))
    return tools, calls, factory


def call(tools: BoardTools, name: str, session_id: str | None, args: dict[str, object]) -> Any:
    out = getattr(tools, name)(args, session_id=session_id)
    assert isinstance(out, str)
    return json.loads(out)


def test_board_copy_copies_one_open_item_into_the_caller_board(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    tools, calls, _ = cross_tools(store, resolver_for, {"s1": SessionSpec(title="Lease renewal")})
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Call John")], actor="agent", base_rev=0)
    source_before = store.get_board("s2")

    result = call(tools, "board_copy", "s1", {"from_session_id": "s2"})

    assert result == {
        "ok": True,
        "rev": 2,
        "summary": "Copied 1 to Lease renewal. 0 skipped, already on the board.",
        "changed": ["- [ ] #2 Call John"],
    }
    assert calls == [("s1", "s1", 2)]
    assert store.get_board("s2") == source_before
