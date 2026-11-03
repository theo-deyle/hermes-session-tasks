"""POST /board/copy through the real router: replies, refusals and the event."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from api_client import PREFIX, load_plugin_api, make_client, unload_plugin_api
from conftest import ResolverFor
from fakes import SEVEN_ROW_FIXTURE, SessionSpec
from session_tasks import board_api
from session_tasks.board_api import BoardApi
from session_tasks.copy_args import SESSION_ID_MAX
from session_tasks.db import ConnFactory
from session_tasks.model import NO_SOURCE_BOARD, SAME_BOARD, AddItem, SetChecked
from session_tasks.results import DELEGATE_COPY
from session_tasks.store import BoardStore

Calls = list[tuple[str, str, int]]


@pytest.fixture(autouse=True)
def clean_core() -> Iterator[None]:
    unload_plugin_api()
    yield
    unload_plugin_api()


class CopyRig:
    """One client over one store and resolver, with a recorder as the after-write listener."""

    def __init__(
        self,
        store: BoardStore,
        resolver_for: ResolverFor,
        specs: dict[str, SessionSpec] | None = None,
        after_write: Callable[[str, str, int], None] | None = None,
    ) -> None:
        self.store = store
        self.resolver, _ = resolver_for(specs or {})
        self.calls: Calls = []
        self.module = load_plugin_api()
        self.client = make_client(
            self.module, BoardApi(store, self.resolver, after_write=after_write or self.record)
        )

    def record(self, root_id: str, session_id: str, rev: int) -> None:
        self.calls.append((root_id, session_id, rev))

    def post(self, body: dict[str, Any]) -> Any:
        return self.client.post(PREFIX + "/board/copy", json=body)


def test_copy_route_copies_one_item_into_the_target_board(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    rig = CopyRig(store, resolver_for)
    store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    store.apply("s2", [AddItem("Call John")], actor="agent", base_rev=0)
    source_before = store.get_board("s2")

    response = rig.post({"session_id": "s1", "from_session_id": "s2", "base_rev": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["root_id"] == "s1"
    assert body["rev"] == 2
    assert (body["copied"], body["skipped"], body["overflow"]) == (1, 0, 0)
    assert body["changed_ids"] == [2]
    assert body["summary"] == "rev 2: added 1 item"
    items = {item["id"]: item for item in body["board"]["items"]}
    assert items[2]["text"] == "Call John"
    assert items[2]["updated_by"] == "user"
    assert rig.calls == [("s1", "s1", 2)]
    assert store.get_board("s2") == source_before


def count_rows(connect: ConnFactory, table: str) -> int:
    conn = connect()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def seed(store: BoardStore, root_id: str, *texts: str) -> None:
    store.apply(root_id, [AddItem(text) for text in texts], actor="agent", base_rev=0)


def copy_body(**extra: Any) -> dict[str, Any]:
    return {"session_id": "s1", "from_session_id": "s2", **extra}


def test_extra_field_is_refused(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    rig = CopyRig(store, resolver_for)
    seed(store, "s2", "Call John")

    response = rig.post(copy_body(confirmed=True))

    assert response.status_code == 422
    assert count_rows(connect, "boards") == 1
    assert rig.calls == []


def test_bool_base_rev_is_refused(store: BoardStore, resolver_for: ResolverFor) -> None:
    rig = CopyRig(store, resolver_for)
    seed(store, "s2", "Call John")

    assert rig.post(copy_body(base_rev=True)).status_code == 422
    assert store.get_board("s1").items == ()


@pytest.mark.parametrize("field", ["session_id", "from_session_id"])
def test_long_session_ids_are_refused(
    store: BoardStore, resolver_for: ResolverFor, field: str
) -> None:
    rig = CopyRig(store, resolver_for)

    too_long = rig.post(copy_body(**{field: "x" * (SESSION_ID_MAX + 1)}))
    longest = rig.post(copy_body(**{field: "x" * SESSION_ID_MAX}))

    assert too_long.status_code == 422
    assert longest.status_code != 422


def test_blank_target_gives_no_session(store: BoardStore, resolver_for: ResolverFor) -> None:
    rig = CopyRig(store, resolver_for)
    seed(store, "s2", "Call John")

    response = rig.post(copy_body(session_id="   "))

    assert response.status_code == 400
    assert response.json()["error"] == "no_session"
    assert rig.calls == []


def test_delegate_target_is_refused(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    rig = CopyRig(store, resolver_for, SEVEN_ROW_FIXTURE)
    seed(store, "s2", "Call John")
    boards_before = count_rows(connect, "boards")
    items_before = count_rows(connect, "items")

    response = rig.post(copy_body(session_id="dg"))

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "invalid"
    assert body["message"] == DELEGATE_COPY
    assert (count_rows(connect, "boards"), count_rows(connect, "items")) == (
        boards_before,
        items_before,
    )
    assert rig.calls == []


def test_same_board_is_refused(store: BoardStore, resolver_for: ResolverFor) -> None:
    rig = CopyRig(store, resolver_for, SEVEN_ROW_FIXTURE)
    seed(store, "root", "Call John")
    before = store.get_board("root")

    response = rig.post(copy_body(session_id="comp2", from_session_id="comp1"))

    body = response.json()
    assert (response.status_code, body["ok"], body["error"]) == (200, False, "invalid")
    assert body["message"] == SAME_BOARD
    assert store.get_board("root") == before
    assert rig.calls == []


def test_source_without_a_board_is_refused(
    store: BoardStore, resolver_for: ResolverFor, connect: ConnFactory
) -> None:
    rig = CopyRig(store, resolver_for)

    response = rig.post(copy_body())

    body = response.json()
    assert (response.status_code, body["ok"], body["error"]) == (200, False, "invalid")
    assert body["message"] == NO_SOURCE_BOARD
    assert count_rows(connect, "boards") == 0
    assert rig.calls == []


@pytest.mark.parametrize(
    "item_ids",
    [[], [True], list(range(1, 102))],
    ids=["empty-list", "bool-id", "101-ids"],
)
def test_bad_item_ids_are_refused(
    store: BoardStore, resolver_for: ResolverFor, item_ids: list[Any]
) -> None:
    rig = CopyRig(store, resolver_for)
    seed(store, "s2", "Call John")

    response = rig.post(copy_body(item_ids=item_ids))

    body = response.json()
    assert (response.status_code, body["ok"], body["error"]) == (200, False, "invalid")
    assert body["rule"] and body["message"]
    assert store.get_board("s1").items == ()
    assert rig.calls == []


def test_missing_source_item_gives_the_stale_shape(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    rig = CopyRig(store, resolver_for)
    seed(store, "s1", "Mine")
    seed(store, "s2", "Call John")
    before = store.get_board("s1")

    response = rig.post(copy_body(item_ids=[9]))

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "stale"
    assert body["reason"] == "not_found"
    assert body["item_id"] == 9
    assert body["message"] == "not found: #9 is not on that session's board. Nothing was copied."
    assert body["root_id"] == "s1"
    assert body["rev"] == before.rev
    assert [item["text"] for item in body["board"]["items"]] == ["Mine"]
    assert store.get_board("s1") == before
    assert rig.calls == []


def test_absent_item_ids_copy_every_open_item(store: BoardStore, resolver_for: ResolverFor) -> None:
    rig = CopyRig(store, resolver_for)
    seed(store, "s2", "One", "Two", "Three", "Done")
    store.apply("s2", [SetChecked(4, True)], actor="agent", base_rev=1)

    body = rig.post(copy_body()).json()

    assert body["ok"] is True
    assert body["copied"] == 3
    assert [item["text"] for item in body["board"]["items"]] == ["One", "Two", "Three"]


def test_a_copy_of_nothing_calls_no_listener(store: BoardStore, resolver_for: ResolverFor) -> None:
    rig = CopyRig(store, resolver_for)
    seed(store, "s1", "Call John")
    seed(store, "s2", "Call John")

    body = rig.post(copy_body()).json()

    assert body["ok"] is True
    assert (body["copied"], body["skipped"], body["overflow"]) == (0, 1, 0)
    assert body["changed_ids"] == []
    assert rig.calls == []


def test_listener_fault_keeps_the_reply_ok(
    store: BoardStore, resolver_for: ResolverFor, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(root_id: str, session_id: str, rev: int) -> None:
        raise RuntimeError("listener down")

    rig = CopyRig(store, resolver_for, after_write=boom)
    seed(store, "s2", "Call John")

    with caplog.at_level(logging.WARNING, logger="session_tasks.board_api"):
        response = rig.post(copy_body())

    assert response.json()["ok"] is True
    assert [item.text for item in store.get_board("s1").items] == ["Call John"]
    records = [r for r in caplog.records if r.name == "session_tasks.board_api"]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING


def test_built_api_publishes_board_updated_for_the_target_as_user(
    connect: ConnFactory, store: BoardStore, resolver_for: ResolverFor
) -> None:
    published: list[tuple[str, str, int, str]] = []

    def record(root_id: str, session_id: str, rev: int, actor: str) -> None:
        published.append((root_id, session_id, rev, actor))

    _, factory = resolver_for({})
    api = board_api.build(connect, factory, publish=record)
    module = load_plugin_api()
    client = make_client(module, api)
    seed(store, "s2", "Call John")

    response = client.post(PREFIX + "/board/copy", json=copy_body())

    assert response.json()["ok"] is True
    assert published == [("s1", "s1", 1, "user")]
