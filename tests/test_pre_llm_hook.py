"""The `pre_llm_call` hook: the note of Theo's changes, quiet turns, skips and faults."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

import pytest
from conftest import ResolverFor
from fakes import FakeCtx, FakeReaderFactory, RaisingReaderFactory, SessionSpec
from session_tasks import delta
from session_tasks.board_api import BoardApi
from session_tasks.db import ConnFactory
from session_tasks.hooks import make_pre_llm_call
from session_tasks.lineage import SessionResolver
from session_tasks.model import AddItem
from session_tasks.store import BoardStore
from session_tasks.wiring import register

Hook = Callable[..., str | None]


def broken_connect() -> sqlite3.Connection:
    raise RuntimeError("service is down")


def no_publish(root_id: str, session_id: str, rev: int, actor: str) -> None:
    """Take the four arguments of a publisher and do nothing."""


@pytest.fixture
def broken_store() -> BoardStore:
    return BoardStore(broken_connect)


@pytest.fixture
def broken_resolver() -> SessionResolver:
    return SessionResolver(broken_connect, RaisingReaderFactory(RuntimeError("no reader")))


@pytest.fixture
def hook(store: BoardStore, resolver_for: ResolverFor) -> Hook:
    resolver, _ = resolver_for({})
    return make_pre_llm_call(store, resolver)


def turn(hook: Hook, session_id: object = "s1") -> str | None:
    return hook(session_id=session_id, user_message="hi", is_first_turn=False)


def theo(connect: ConnFactory, session: str, ops: list[dict[str, object]], base_rev: int) -> None:
    """Write as Theo does in the pane: through `BoardApi.edit`, which uses actor user."""
    api = BoardApi(BoardStore(connect), SessionResolver(connect, FakeReaderFactory({})))
    assert api.edit(session, ops, base_rev).status == 200


def board_rows(connect: ConnFactory) -> int:
    conn = connect()
    try:
        return int(conn.execute("SELECT COUNT(*) FROM boards").fetchone()[0])
    finally:
        conn.close()


def test_a_theo_edit_in_the_pane_reaches_the_next_turn_once(connect: ConnFactory) -> None:
    ctx = FakeCtx()
    register(ctx, connect=connect, open_reader=FakeReaderFactory({}), publish=no_publish)
    edit = ctx.tools["board_edit"]["handler"]
    pre_llm = ctx.hooks["pre_llm_call"][0]
    edit({"ops": [{"op": "add", "text": "Call John"}]}, session_id="s1")

    assert pre_llm(session_id="s1", user_message="hi", is_first_turn=False) is None

    theo(connect, "s1", [{"op": "set_checked", "item_id": 1, "checked": True}], 1)
    expected = "\n".join([
        f'<{delta.DELTA_TAG} rev="2">',
        delta.DELTA_NOTE,
        "checked #1",
        f"</{delta.DELTA_TAG}>",
    ])

    assert pre_llm(session_id="s1", user_message="hi", is_first_turn=False) == expected
    assert pre_llm(session_id="s1", user_message="hi", is_first_turn=False) is None


def test_quiet_turn_returns_none_and_marks_nothing(
    hook: Hook, store: BoardStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)
    marks: list[tuple[str, int]] = []
    real_mark = BoardStore.mark_seen

    def recording_mark(self: BoardStore, root_id: str, rev: int) -> None:
        marks.append((root_id, rev))
        real_mark(self, root_id, rev)

    monkeypatch.setattr(BoardStore, "mark_seen", recording_mark)

    assert turn(hook) is None
    assert turn(hook) is None
    assert marks == []


def test_no_board_returns_none(hook: Hook, connect: ConnFactory) -> None:
    assert turn(hook, "s9") is None
    assert board_rows(connect) == 0


@pytest.mark.parametrize("session_id", [None, "", "   "])
def test_blank_session_returns_none(
    store: BoardStore, resolver_for: ResolverFor, session_id: object
) -> None:
    resolver, factory = resolver_for({})
    hook = make_pre_llm_call(store, resolver)

    assert hook(session_id=session_id, user_message="hi") is None
    assert factory.opens == 0


def test_delegate_session_returns_none(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    resolver, _ = resolver_for({
        "s1": SessionSpec(),
        "dg": SessionSpec(parent="s1", model_config={"_delegate_from": "s1"}),
    })
    hook = make_pre_llm_call(store, resolver)
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)
    theo(connect, "s1", [{"op": "set_checked", "item_id": 1, "checked": True}], 1)

    assert hook(session_id="dg", user_message="hi") is None
    out = turn(hook, "s1")
    assert out is not None
    assert "checked #1" in out


def test_store_fault_returns_none_and_logs_a_warning(
    broken_store: BoardStore,
    resolver_for: ResolverFor,
    caplog: pytest.LogCaptureFixture,
) -> None:
    resolver, _ = resolver_for({})
    hook = make_pre_llm_call(broken_store, resolver)

    with caplog.at_level(logging.WARNING):
        assert hook(session_id="s1") is None

    assert [(r.name, r.levelno) for r in caplog.records] == [
        ("session_tasks.hooks", logging.WARNING)
    ]


def test_resolver_fault_returns_none_and_logs_a_warning(
    store: BoardStore,
    broken_resolver: SessionResolver,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hook = make_pre_llm_call(store, broken_resolver)

    with caplog.at_level(logging.WARNING):
        assert hook(session_id="s1") is None

    assert [(r.name, r.levelno) for r in caplog.records] == [
        ("session_tasks.hooks", logging.WARNING)
    ]
