"""Phase 1 end to end: each ROADMAP success criterion runs through store, markdown and lineage.

Each test wires a `SessionResolver` and a `BoardStore` on the same data file, the way the
Phase 2 service does. The session id resolves first. The store then gets the root id.
"""

from __future__ import annotations

from pathlib import Path

from conftest import ResolverFor
from fakes import SessionSpec
from session_tasks.lineage import Resolution
from session_tasks.markdown import ParsedItem, parse, plan_import, render
from session_tasks.model import (
    MAX_ITEMS,
    MAX_TEXT_CHARS,
    AddItem,
    Applied,
    Board,
    SetChecked,
    SetText,
    Stale,
)
from session_tasks.store import BoardStore

CHAIN: dict[str, SessionSpec] = {
    "root": SessionSpec(end_reason="compression"),
    "tip1": SessionSpec(parent="root", end_reason="compression"),
    "tip2": SessionSpec(parent="tip1"),
    "br": SessionSpec(parent="tip2", model_config={"_branched_from": "tip2"}),
    "dg": SessionSpec(parent="tip2", model_config={"_delegate_from": "tip2"}),
    "rs": SessionSpec(parent="tip2", model_config={"_reset_from": "tip2"}),
}

PASTED = "\n".join([
    "## Today",
    "- [ ] Call John",
    "  - [x] Ask about the quote",
    "    - [ ] Confirm the date",
    "- [X] Book the van",
    "- Buy milk",
    "- [ ]",
    f"- [ ] {'x' * (MAX_TEXT_CHARS + 1)}",
    "- [ ] Short line after the long one",
])

CANONICAL = (
    "- [ ] Call John\n"
    "  - [x] Ask about the quote\n"
    "  - [ ] Confirm the date\n"
    "- [x] Book the van\n"
    "- [ ] Buy milk\n"
    "- [ ] Short line after the long one\n"
)


def seed_root(store: BoardStore) -> Board:
    """Write a board with two top-level items and one subtask on the session `root`."""
    ops = [AddItem("Call John"), AddItem("Ask about the quote", parent_ref=0), AddItem("Book van")]
    result = store.apply("root", ops, actor="agent", base_rev=0)
    assert isinstance(result, Applied)
    return result.board


def state_of(board: Board, item_id: int) -> tuple[str, bool]:
    item = board.item(item_id)
    assert item is not None
    return item.text, item.checked


def flatten_hints(items: tuple[ParsedItem, ...]) -> list[int | None]:
    hints: list[int | None] = []
    for item in items:
        hints.append(item.hint_id)
        hints.extend(flatten_hints(item.children))
    return hints


def test_agent_and_user_share_one_board_and_a_stale_write_gets_the_current_board(
    store: BoardStore, hermes_home: Path, db_path: Path
) -> None:
    first = seed_root(store)
    user = store.apply("root", [SetChecked(1, True)], actor="user", base_rev=first.rev)
    assert isinstance(user, Applied)

    stale = store.apply("root", [SetText(1, "Call John today")], actor="agent", base_rev=first.rev)

    assert isinstance(stale, Stale)
    assert stale.reason == "stale"
    current = stale.board.item(1)
    assert current is not None
    assert current.checked is True
    assert current.updated_by == "user"
    assert current.text == "Call John"
    assert stale.board == store.get_board("root")
    assert db_path.exists()
    assert not (hermes_home / "state.db").exists()


def test_every_item_field_is_set_and_a_subtask_hangs_under_its_parent(store: BoardStore) -> None:
    board = seed_root(store)

    subtask = board.item(2)
    assert subtask is not None
    assert subtask.parent_id == 1
    assert [item.id for item in board.children(1)] == [2]
    for item in board.items:
        assert item.id >= 1
        assert item.position >= 0
        assert item.text
        assert item.rev >= 1
        assert item.updated_by == "agent"
        assert item.created_at.endswith("Z")
        assert item.updated_at.endswith("Z")
    assert [item.parent_id for item in board.items] == [None, 1, None]


def test_board_survives_rotating_compression_through_the_hook_and_without_it(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    resolver, _ = resolver_for(CHAIN)
    written = seed_root(store)

    resolver.record_compaction("tip1", "root")
    through_hook = resolver.resolve("tip1")
    through_walk = resolver.resolve("tip2")

    assert through_hook == Resolution("root", "compression")
    assert through_walk == Resolution("root", "compression")
    assert store.get_board(through_hook.root_id).items == written.items
    assert store.get_board(through_walk.root_id).items == written.items


def test_branch_shows_parent_items_and_edits_stay_apart(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    resolver, _ = resolver_for(CHAIN)
    parent = seed_root(store)

    resolution = resolver.resolve("br")
    branch = store.get_board(resolution.root_id)

    assert resolution == Resolution("br", "branch", forked_from="root")
    assert render(branch, include_ids=False) == render(parent, include_ids=False)

    to_branch = store.apply("br", [SetText(1, "Branch edit")], actor="user", base_rev=branch.rev)
    to_parent = store.apply("root", [SetChecked(3, True)], actor="agent", base_rev=parent.rev)
    assert isinstance(to_branch, Applied)
    assert isinstance(to_parent, Applied)

    assert state_of(to_parent.board, 1) == ("Call John", False)
    assert state_of(to_branch.board, 1) == ("Branch edit", False)
    assert state_of(to_parent.board, 3) == ("Book van", True)
    assert state_of(to_branch.board, 3) == ("Book van", False)


def test_reset_session_gets_an_empty_board_and_a_delegate_reads_the_delegator_root(
    store: BoardStore, resolver_for: ResolverFor
) -> None:
    resolver, _ = resolver_for(CHAIN)
    seed_root(store)

    reset = resolver.resolve("rs")
    delegate = resolver.resolve("dg")

    assert reset == Resolution("rs", "plain")
    assert store.get_board(reset.root_id).items == ()
    assert delegate == Resolution("root", "delegate")
    assert len(store.get_board(delegate.root_id).items) == 3


def test_pasted_checklist_round_trips_through_the_store_with_subtasks(store: BoardStore) -> None:
    result = parse(PASTED)
    plan = plan_import(result, MAX_ITEMS - 0)

    applied = store.apply("root", plan.ops, actor="user", base_rev=0)

    assert isinstance(applied, Applied)
    assert result.moved == 1
    assert result.skipped_empty == 1
    assert result.too_long == 1
    assert plan.overflow == 0
    board = applied.board
    assert "Short line after the long one" in [item.text for item in board.items]
    assert render(board, include_ids=False) == CANONICAL
    reparsed = parse(render(board, include_ids=True))
    assert flatten_hints(reparsed.items) == [item.id for item in board.items]
    assert [item.text for item in board.children(1)] == [
        "Ask about the quote",
        "Confirm the date",
    ]


def test_import_into_a_nearly_full_board_stops_at_the_cap(store: BoardStore) -> None:
    fill = [AddItem(f"Filler {number}") for number in range(98)]
    filled = store.apply("root", fill, actor="agent", base_rev=0)
    assert isinstance(filled, Applied)
    pasted = "\n".join(f"- [ ] Imported {number}" for number in range(5))

    plan = plan_import(parse(pasted), MAX_ITEMS - 98)
    applied = store.apply("root", plan.ops, actor="user", base_rev=filled.rev)

    assert len(plan.ops) == 2
    assert plan.overflow == 3
    assert isinstance(applied, Applied)
    assert len(applied.board.items) == MAX_ITEMS
    assert [item.text for item in applied.board.items[-2:]] == ["Imported 0", "Imported 1"]
