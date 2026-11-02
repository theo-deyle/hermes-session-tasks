"""POST /board/copy through the real router: replies, refusals and the event."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from api_client import PREFIX, load_plugin_api, make_client, unload_plugin_api
from conftest import ResolverFor
from fakes import SessionSpec
from session_tasks.board_api import BoardApi
from session_tasks.model import AddItem
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
    ) -> None:
        self.store = store
        self.resolver, _ = resolver_for(specs or {})
        self.calls: Calls = []
        self.module = load_plugin_api()
        self.client = make_client(
            self.module, BoardApi(store, self.resolver, after_write=self.record)
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
