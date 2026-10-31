"""The `pre_tool_call` guard hook and the `post_compaction` hook, built over real stores."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import ResolverFor
from fakes import FakeReaderFactory, RaisingReaderFactory, SessionSpec
from session_tasks.db import ConnFactory
from session_tasks.guard import block_message
from session_tasks.hooks import GUARD_FAILED, make_post_compaction, make_pre_tool_call
from session_tasks.lineage import SessionResolver
from session_tasks.model import AddItem, SetChecked
from session_tasks.store import BoardStore

Hook = Callable[..., dict[str, str] | None]


def broken_connect() -> sqlite3.Connection:
    raise RuntimeError("service is down")


@pytest.fixture
def broken_store() -> BoardStore:
    return BoardStore(broken_connect)


@pytest.fixture
def broken_resolver() -> SessionResolver:
    return SessionResolver(broken_connect, RaisingReaderFactory(RuntimeError("no reader")))


def run(
    hook: Hook,
    args: object,
    session_id: object = "s1",
    tool_name: str = "board_edit",
) -> dict[str, str] | None:
    return hook(
        tool_name=tool_name,
        args=args,
        task_id="t1",
        session_id=session_id,
        tool_call_id="c1",
        turn_id="u1",
        api_request_id="r1",
        middleware_trace=[],
    )


def remove_call(item_id: int = 1, **extra: object) -> dict[str, object]:
    return {"ops": [{"op": "remove", "item_id": item_id}], "base_rev": 1, **extra}


@pytest.fixture
def hook(store: BoardStore, resolver_for: ResolverFor) -> Hook:
    resolver, _ = resolver_for({})
    return make_pre_tool_call(store, resolver)


def seed_agent_item(store: BoardStore, session: str = "s1") -> None:
    store.apply(session, [AddItem("Call John")], actor="agent", base_rev=0)


def seed_user_touched_item(store: BoardStore, session: str = "s1") -> None:
    seed_agent_item(store, session)
    store.apply(session, [SetChecked(1, True)], actor="user", base_rev=1)


@pytest.mark.parametrize("tool_name", ["terminal", "read_file", "board_read", "memory", ""])
def test_pre_tool_call_returns_none_for_other_tools_with_a_broken_service(
    broken_store: BoardStore, broken_resolver: SessionResolver, tool_name: str
) -> None:
    hook = make_pre_tool_call(broken_store, broken_resolver)

    assert run(hook, remove_call(), tool_name=tool_name) is None
    assert run(hook, "garbage", tool_name=tool_name) is None


def test_pre_tool_call_blocks_an_unconfirmed_remove(store: BoardStore, hook: Hook) -> None:
    seed_agent_item(store)

    result = run(hook, remove_call())

    assert result == {"action": "block", "message": block_message(("remove of #1",))}
    assert result is not None
    assert "remove of #1" in result["message"]
    assert "If Theo's own message named the change" in result["message"]


def test_pre_tool_call_blocks_an_unconfirmed_uncheck(store: BoardStore, hook: Hook) -> None:
    seed_agent_item(store)
    args = {"ops": [{"op": "set_checked", "item_id": 1, "checked": False}], "base_rev": 1}

    result = run(hook, args)

    assert result == {"action": "block", "message": block_message(("uncheck of #1",))}


@pytest.mark.parametrize(
    ("ops_text", "confirmed", "blocked"),
    [
        ("remove", "false", True),
        ("remove", "False", True),
        ("remove", "true", False),
        ("remove", "TRUE", False),
    ],
)
def test_pre_tool_call_reads_raw_string_arguments(
    store: BoardStore, hook: Hook, ops_text: str, confirmed: str, blocked: bool
) -> None:
    seed_agent_item(store)
    args = {
        "ops": json.dumps([{"op": ops_text, "item_id": "1"}]),
        "base_rev": "1",
        "confirmed": confirmed,
    }

    result = run(hook, args)

    assert (result is not None) is blocked


def test_pre_tool_call_passes_a_confirmed_call_with_no_io(
    broken_store: BoardStore, broken_resolver: SessionResolver
) -> None:
    hook = make_pre_tool_call(broken_store, broken_resolver)

    assert run(hook, remove_call(confirmed=True)) is None


def test_pre_tool_call_passes_an_empty_call_with_no_io(
    broken_store: BoardStore, broken_resolver: SessionResolver
) -> None:
    hook = make_pre_tool_call(broken_store, broken_resolver)

    assert run(hook, {"ops": []}) is None


def test_pre_tool_call_passes_adds_and_checks_in_any_count(
    store: BoardStore, hook: Hook, db_path: Path
) -> None:
    ops: list[dict[str, object]] = [{"op": "add", "text": f"a{n}"} for n in range(20)]
    ops += [{"op": "set_checked", "item_id": n, "checked": True} for n in (1, 2, 3)]

    assert run(hook, {"ops": ops, "base_rev": 3}) is None
    assert not db_path.exists()


def test_pre_tool_call_guards_a_reword_of_an_item_theo_touched(
    store: BoardStore, hook: Hook
) -> None:
    seed_user_touched_item(store)
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=2)
    reword_theirs = {"ops": [{"op": "set_text", "item_id": 1, "text": "x"}], "base_rev": 3}
    reword_mine = {"ops": [{"op": "set_text", "item_id": 2, "text": "x"}], "base_rev": 3}

    assert run(hook, reword_theirs) == {
        "action": "block",
        "message": block_message(("reword of #1",)),
    }
    assert run(hook, reword_mine) is None


def test_pre_tool_call_blocks_one_guarded_op_among_many_adds(store: BoardStore, hook: Hook) -> None:
    seed_agent_item(store)
    ops: list[dict[str, object]] = [{"op": "add", "text": f"a{n}"} for n in range(5)]
    ops.insert(3, {"op": "remove", "item_id": 1})

    result = run(hook, {"ops": ops, "base_rev": 1})

    assert result == {"action": "block", "message": block_message(("remove of #1",))}


def test_pre_tool_call_lists_guarded_ops_in_op_order(store: BoardStore, hook: Hook) -> None:
    seed_agent_item(store)
    ops = [
        {"op": "set_checked", "item_id": 1, "checked": False},
        {"op": "remove", "item_id": 1},
    ]

    result = run(hook, {"ops": ops, "base_rev": 1})

    assert result is not None
    assert "uncheck of #1, remove of #1" in result["message"]


def test_pre_tool_call_blocks_unparseable_arguments_with_the_rule_text(hook: Hook) -> None:
    result = run(hook, {"ops": "not json"})

    assert result is not None
    assert result["action"] == "block"
    assert result["message"].startswith("board_edit: ")
    assert "ops must be a JSON list of operations" in result["message"]


def test_pre_tool_call_blocks_arguments_that_are_not_a_mapping(hook: Hook) -> None:
    result = run(hook, None)

    assert result is not None
    assert "ops is required" in result["message"]


def test_pre_tool_call_names_the_op_index_of_a_bad_op(hook: Hook) -> None:
    result = run(hook, {"ops": [{"op": "add", "text": "a"}, {"op": "clear"}]})

    assert result is not None
    assert "op 1:" in result["message"]


def test_pre_tool_call_fails_closed_when_the_board_cannot_be_read(
    broken_store: BoardStore,
    resolver_for: ResolverFor,
    caplog: pytest.LogCaptureFixture,
) -> None:
    resolver, _ = resolver_for({})
    hook = make_pre_tool_call(broken_store, resolver)
    args = {"ops": [{"op": "set_text", "item_id": 1, "text": "x"}], "base_rev": 1}

    with caplog.at_level(logging.ERROR):
        result = run(hook, args)

    assert result == {"action": "block", "message": GUARD_FAILED}
    assert "board guard failed" in caplog.text


def test_pre_tool_call_returns_none_in_a_delegate_session(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    resolver, _ = resolver_for({
        "root": SessionSpec(),
        "dg": SessionSpec(parent="root", model_config={"_delegate_from": "root"}),
    })
    hook = make_pre_tool_call(store, resolver)
    seed_agent_item(store, "root")

    assert run(hook, remove_call(), session_id="dg") is None


@pytest.mark.parametrize("session_id", ["", "   ", None, 7])
def test_pre_tool_call_returns_none_for_a_blank_session(hook: Hook, session_id: object) -> None:
    assert run(hook, remove_call(), session_id=session_id) is None


def test_pre_tool_call_uses_the_keyword_session_not_args(store: BoardStore, hook: Hook) -> None:
    seed_user_touched_item(store, "s1")
    seed_agent_item(store, "s2")
    reword = {"ops": [{"op": "set_text", "item_id": 1, "text": "x"}], "base_rev": 3}

    blocked = run(hook, {**reword, "session_id": "s2"}, session_id="s1")
    passed = run(hook, {**reword, "session_id": "s1"}, session_id="s2")

    assert blocked is not None
    assert passed is None


def test_hook_returns_only_block_or_none(
    store: BoardStore,
    hook: Hook,
    broken_store: BoardStore,
    broken_resolver: SessionResolver,
) -> None:
    seed_user_touched_item(store)
    broken = make_pre_tool_call(broken_store, broken_resolver)
    calls: list[tuple[Hook, object, str]] = [
        (hook, remove_call(), "board_edit"),
        (hook, remove_call(confirmed=True), "board_edit"),
        (hook, {"ops": [{"op": "add", "text": "a"}]}, "board_edit"),
        (hook, {"ops": "bad"}, "board_edit"),
        (
            hook,
            {"ops": [{"op": "set_text", "item_id": 1, "text": "x"}], "base_rev": 2},
            "board_edit",
        ),
        (hook, remove_call(), "terminal"),
        (
            broken,
            {"ops": [{"op": "set_text", "item_id": 1, "text": "x"}], "base_rev": 1},
            "board_edit",
        ),
        (broken, remove_call(), "read_file"),
    ]

    results = [run(h, args, tool_name=name) for h, args, name in calls]

    assert any(result is not None for result in results)
    for result in results:
        assert result is None or (
            set(result) == {"action", "message"} and result["action"] == "block"
        )


def test_post_compaction_forwards_both_ids(resolver_for: ResolverFor) -> None:
    resolver, _ = resolver_for({})
    hook = make_post_compaction(resolver)

    hook(session_id="s2", old_session_id="s1", kind="summarize", reason="manual")

    assert resolver.resolve("s2").root_id == "s1"


@pytest.mark.parametrize("old_id", ["", "  ", None, 5])
def test_post_compaction_skips_a_blank_old_id_with_no_io(
    connect: ConnFactory, old_id: object
) -> None:
    calls: list[int] = []

    def counting() -> sqlite3.Connection:
        calls.append(1)
        return connect()

    factory = FakeReaderFactory({})
    hook = make_post_compaction(SessionResolver(counting, factory))

    hook(session_id="s2", old_session_id=old_id)

    assert calls == []
    assert factory.opens == 0


def test_post_compaction_never_raises(
    broken_resolver: SessionResolver, caplog: pytest.LogCaptureFixture
) -> None:
    hook = make_post_compaction(broken_resolver)

    with caplog.at_level(logging.ERROR):
        hook(session_id="s2", old_session_id="s1")
        hook(session_id="", old_session_id="s1")

    assert "board alias after compaction failed" in caplog.text
