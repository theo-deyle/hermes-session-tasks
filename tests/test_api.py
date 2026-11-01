"""Board routes through the real router: reply shapes (D-22), transport faults, edge rules."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from typing import Any

import pytest
from api_client import PREFIX, load_plugin_api, make_client, unload_plugin_api
from conftest import ResolverFor
from fakes import SessionSpec
from fastapi.testclient import TestClient
from session_tasks import edit_args
from session_tasks.board_api import BoardApi
from session_tasks.board_tools import BoardTools
from session_tasks.db import ConnFactory
from session_tasks.model import AddItem, SetText
from session_tasks.results import DELEGATE_EDIT, NO_SESSION
from session_tasks.store import BoardStore

DELEGATE_SPECS = {
    "s1": SessionSpec(),
    "dg": SessionSpec(parent="s1", model_config={"_delegate_from": "s1"}),
}


@pytest.fixture(autouse=True)
def clean_core() -> Iterator[None]:
    unload_plugin_api()
    yield
    unload_plugin_api()


class Rig:
    """One client over one store and resolver, plus helpers for the common calls."""

    def __init__(
        self,
        store: BoardStore,
        resolver_for: ResolverFor,
        specs: dict[str, SessionSpec] | None = None,
    ) -> None:
        self.store = store
        self.resolver, _ = resolver_for(specs or {})
        self.module = load_plugin_api()
        self.client = make_client(self.module, BoardApi(store, self.resolver))

    def post(self, body: dict[str, Any]) -> Any:
        return self.client.post(PREFIX + "/board/edit", json=body)

    def edit(self, ops: list[dict[str, Any]], session_id: str = "s1", **extra: Any) -> Any:
        return self.post({"session_id": session_id, "ops": ops, **extra})

    def get(self, session_id: str = "s1") -> Any:
        return self.client.get(PREFIX + "/board", params={"session_id": session_id})


@pytest.fixture
def rig(store: BoardStore, resolver_for: ResolverFor) -> Rig:
    return Rig(store, resolver_for)


def add_op(text: str, **extra: Any) -> dict[str, Any]:
    return {"op": "add", "text": text, **extra}


def count_rows(connect: ConnFactory, table: str) -> int:
    conn = connect()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_add_returns_the_new_rev_and_the_board(rig: Rig) -> None:
    response = rig.edit([add_op("Call John")])

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["root_id"] == "s1"
    assert body["rev"] == 1
    assert body["summary"] == "rev 1: added 1 item"
    assert body["changed_ids"] == [1]
    assert body["board"]["items"][0]["updated_by"] == "user"


def test_stale_write_returns_200_with_the_current_board(rig: Rig) -> None:
    rig.store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)
    rig.store.apply("s1", [SetText(1, "b")], actor="user", base_rev=1)

    response = rig.edit([{"op": "set_checked", "item_id": 1, "checked": True}], base_rev=1)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "stale"
    assert body["reason"] == "stale"
    assert body["op_index"] == 0
    assert body["item_id"] == 1
    assert body["message"] == "stale: #1 changed after rev 1 (op 0)"
    assert body["rev"] == 2
    assert body["board"]["rev"] == 2
    assert rig.get().json()["rev"] == 2


def test_missing_item_returns_not_found(rig: Rig) -> None:
    response = rig.edit([{"op": "set_checked", "item_id": 9, "checked": True}], base_rev=0)

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is False
    assert body["reason"] == "not_found"
    assert body["message"] == "not found: #9 is not on the board (op 0)"


RULE_CASES = [
    pytest.param(
        {"ops": [add_op("  ")]}, 0, "item text is empty", "op 0: item text is empty", id="empty"
    ),
    pytest.param(
        {"ops": [{"op": "set_checked", "item_id": 1, "checked": True}]},
        0,
        edit_args.BASE_REV_MISSING,
        f"op 0: {edit_args.BASE_REV_MISSING}",
        id="base-rev-missing",
    ),
    pytest.param(
        {"ops": [add_op("x")], "base_rev": -1},
        None,
        edit_args.BASE_REV_BAD,
        edit_args.BASE_REV_BAD,
        id="base-rev-bad",
    ),
]


@pytest.mark.parametrize(("extra", "op_index", "rule", "message"), RULE_CASES)
def test_rule_error_returns_200_invalid(
    rig: Rig, extra: dict[str, Any], op_index: int | None, rule: str, message: str
) -> None:
    response = rig.post({"session_id": "s1", **extra})

    body = response.json()
    assert response.status_code == 200
    assert body == {
        "ok": False,
        "error": "invalid",
        "op_index": op_index,
        "rule": rule,
        "message": message,
    }
    assert rig.store.get_board("s1").rev == 0


def test_a_101st_item_is_an_invalid_reply_and_writes_nothing(rig: Rig) -> None:
    rig.store.apply("s1", [AddItem(f"item {n}") for n in range(100)], actor="agent", base_rev=0)

    response = rig.edit([add_op("one too many")])

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is False
    assert body["error"] == "invalid"
    assert body["op_index"] is None
    assert rig.store.get_board("s1").rev == 1


def test_delegate_session_cannot_edit(store: BoardStore, resolver_for: ResolverFor) -> None:
    rig = Rig(store, resolver_for, DELEGATE_SPECS)
    store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)
    before = store.get_board("s1")

    response = rig.edit([add_op("sneaky")], session_id="dg")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "error": "invalid",
        "op_index": None,
        "rule": DELEGATE_EDIT,
        "message": DELEGATE_EDIT,
    }
    assert store.get_board("s1") == before


def test_confirmed_field_is_refused(rig: Rig) -> None:
    response = rig.edit([add_op("x")], confirmed=True)

    assert response.status_code == 422
    assert rig.store.get_board("s1").rev == 0


def test_user_remove_needs_no_confirmation(rig: Rig) -> None:
    rig.edit([add_op("mine")])

    response = rig.edit([{"op": "remove", "item_id": 1}], base_rev=1)

    body = response.json()
    assert body["ok"] is True
    assert body["board"]["items"] == []


TRANSPORT_CASES = [
    pytest.param({"session_id": "", "ops": []}, 422, None, id="empty-session"),
    pytest.param({"session_id": "   ", "ops": []}, 400, "no_session", id="blank-session"),
    pytest.param({"session_id": "s1", "ops": "x"}, 422, None, id="ops-string"),
    pytest.param({"session_id": "s1", "ops": [], "base_rev": "2"}, 422, None, id="base-rev-string"),
]


@pytest.mark.parametrize(("body", "status", "error"), TRANSPORT_CASES)
def test_transport_faults_keep_4xx(
    rig: Rig, body: dict[str, Any], status: int, error: str | None
) -> None:
    response = rig.post(body)

    assert response.status_code == status
    if error is not None:
        assert response.json() == {"ok": False, "error": error, "message": NO_SESSION}


def test_blank_session_on_get_returns_400(rig: Rig) -> None:
    response = rig.get("   ")

    assert response.status_code == 400
    assert response.json()["error"] == "no_session"


def test_route_takes_the_session_from_the_body(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    rig = Rig(store, resolver_for, {"s1": SessionSpec(), "s3": SessionSpec()})
    store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)
    rig.resolver.record_compaction("s3", "s1")

    response = rig.edit([add_op("b")], session_id="s3")

    body = response.json()
    assert body["ok"] is True
    assert body["root_id"] == "s1"
    assert store.get_board("s1").rev == 2


def test_get_for_a_session_with_no_board_creates_no_row(rig: Rig, connect: ConnFactory) -> None:
    response = rig.get("fresh")

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert body["rev"] == 0
    assert body["board"]["items"] == []
    assert count_rows(connect, "boards") == 0


def test_empty_ops_write_nothing(rig: Rig, connect: ConnFactory) -> None:
    response = rig.edit([], session_id="unknown")

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert body["rev"] == 0
    assert body["changed_ids"] == []
    assert count_rows(connect, "boards") == 0


def test_repeat_check_is_no_change(rig: Rig) -> None:
    rig.store.apply("s1", [AddItem("a")], actor="agent", base_rev=0)
    check = [{"op": "set_checked", "item_id": 1, "checked": True}]
    first = rig.edit(check, base_rev=1).json()

    second = rig.edit(check, base_rev=first["rev"]).json()

    assert first["rev"] == 2
    assert first["changed_ids"] == [1]
    assert second["ok"] is True
    assert second["rev"] == 2
    assert second["changed_ids"] == []


def test_repeat_add_batch_adds_new_items(rig: Rig) -> None:
    batch = [add_op("a"), add_op("b")]

    first = rig.edit(batch).json()
    second = rig.edit(batch).json()

    assert first["rev"] == 1
    assert second["rev"] == 2
    assert [item["id"] for item in second["board"]["items"]] == [1, 2, 3, 4]


def test_equal_texts_stay_two_items(rig: Rig) -> None:
    body = rig.edit([add_op("same"), add_op("same")]).json()

    items = body["board"]["items"]
    assert [item["text"] for item in items] == ["same", "same"]
    assert [item["id"] for item in items] == [1, 2]


def test_items_come_in_display_order(rig: Rig) -> None:
    body = rig.edit([add_op("a"), add_op("b"), add_op("c", parent_id=1)]).json()

    items = body["board"]["items"]
    assert [item["id"] for item in items] == [1, 3, 2]
    assert [item["parent_id"] for item in items] == [None, 1, None]


def test_two_gets_return_equal_bodies(rig: Rig) -> None:
    rig.edit([add_op("a"), add_op("b")])

    assert rig.get().json() == rig.get().json()


def test_route_and_tool_writers_lose_no_write(store: BoardStore, resolver_for: ResolverFor) -> None:
    rig = Rig(store, resolver_for)
    rig.edit([add_op("seed")])
    tools = BoardTools(store, rig.resolver)
    statuses: list[int] = []
    errors: list[BaseException] = []

    def route_writer() -> None:
        try:
            client: TestClient = make_client(rig.module, BoardApi(store, rig.resolver))
            for n in range(20):
                statuses.append(
                    client.post(
                        PREFIX + "/board/edit",
                        json={"session_id": "s1", "ops": [add_op(f"route {n}")]},
                    ).status_code
                )
        except BaseException as exc:
            errors.append(exc)

    def tool_writer() -> None:
        try:
            for n in range(20):
                out = tools.board_edit({"ops": [add_op(f"tool {n}")]}, session_id="s1")
                assert json.loads(str(out))["ok"] is True
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=route_writer), threading.Thread(target=tool_writer)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    assert not any(thread.is_alive() for thread in threads)
    assert all(status < 500 for status in statuses)
    board = store.get_board("s1")
    assert len(board.items) == 41
    assert board.rev == 41


def test_boards_lists_roots_newest_first(rig: Rig) -> None:
    for root in ("a", "b", "c"):
        rig.store.apply(root, [AddItem("x"), AddItem("y", checked=True)], actor="agent", base_rev=0)
    rig.resolver.record_compaction("s9", "a")

    response = rig.client.get(PREFIX + "/boards")

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert [board["root_id"] for board in body["boards"]] == ["c", "b", "a"]
    newest = body["boards"][0]
    assert set(newest) == {"root_id", "rev", "open", "total", "updated_at"}
    assert (newest["rev"], newest["open"], newest["total"]) == (1, 1, 2)


def test_boards_lists_nothing_when_no_board_exists(rig: Rig) -> None:
    assert rig.client.get(PREFIX + "/boards").json() == {"ok": True, "boards": []}
