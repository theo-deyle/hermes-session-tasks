"""The session picker, the menu and the read-only view of another board, run against the real router."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import PLUGIN_JS, Rig, button, checkbox, inputs, seed_call_john
from session_tasks.model import AddItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

OPEN_MENU = {"openMenu": True}
S2_TITLE = "Syncro ticket 4910"
SESSION_LIST = [{"id": "s2", "title": S2_TITLE, "preview": "", "_lineage_root_id": None}]
BANNER = "Read only. Viewing another session."


def seed_two_boards(rig: Rig) -> None:
    """Board s1 with `Call John` and board s2 with `Reply to the customer`."""
    seed_call_john(rig.store)
    rig.store.apply("s2", [AddItem("Reply to the customer")], actor="agent", base_rev=0)


def gets(result: dict[str, Any], path: str) -> list[dict[str, Any]]:
    """The GET calls of the harness `restCalls` with exactly this path."""
    return [c for c in result["restCalls"] if c["method"] == "GET" and c["path"] == path]


def test_pick_another_board_shows_it_read_only(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    opened = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[OPEN_MENU])

    assert {"method": "session.list", "params": {"limit": 200}} in opened["requestCalls"]
    assert len(gets(opened, "/boards")) == 1
    menu = opened["menuItems"]
    assert menu[0]["texts"][0] == "Untitled session"
    assert menu[0]["current"] is True
    assert menu[1] == {"separator": True}
    assert S2_TITLE in menu[2]["texts"]

    picked = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[OPEN_MENU, {"pick": S2_TITLE}])

    assert len(gets(picked, "/board?session_id=s2")) == 1
    assert BANNER in picked["lines"]
    assert "Reply to the customer" in picked["lines"]
    assert "Call John" not in picked["lines"]
    assert checkbox(picked, "1")["disabled"] is True
    assert inputs(picked, "Add an item") == []
    assert (
        button(picked, f"Session: {S2_TITLE}, 1 of 1 open")["label"]
        == f"Session: {S2_TITLE}, 1 of 1 open"
    )


NO_OTHER = "No other session has a board."
LIST_FAILED = "Could not load the session list. Reopen the list to retry."
LONG_ID = "20261102_133806_e5cc98"
S1_TITLE = "Lease renewal"
S1_LIST = [{"id": "s1", "title": S1_TITLE, "preview": "", "_lineage_root_id": None}]
TRUNCATE = {
    "overflow": "hidden",
    "textOverflow": "ellipsis",
    "whiteSpace": "nowrap",
    "minWidth": 0,
}
# The fake clock starts at 2026-10-30T12:00:00Z; the pane clock reads five minutes later.
NOW_MS = 1793361900000  # 2026-10-30T12:05:00Z


def session_row(
    session_id: str, title: str = "", preview: str = "", root: str | None = None
) -> dict[str, Any]:
    return {"id": session_id, "title": title, "preview": preview, "_lineage_root_id": root}


def rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The menu item records, without the separators."""
    return [entry for entry in result["menuItems"] if "texts" in entry]


def names(result: dict[str, Any]) -> list[str]:
    """The first text of each menu row, in render order."""
    return [entry["texts"][0] for entry in rows(result)]


def trigger_nodes(result: dict[str, Any], text: str) -> list[dict[str, Any]]:
    """The host nodes inside the picker Button with this text."""
    return [n for n in result["nodes"] if n["button"] and n["text"] == text]


def menu_nodes(result: dict[str, Any], text: str) -> list[dict[str, Any]]:
    """The host nodes outside any Button with this text, which are the menu row nodes."""
    return [n for n in result["nodes"] if not n["button"] and n["text"] == text]


def test_trigger_names_the_focused_board_and_its_count(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, sessionList=S1_LIST)

    button(result, f"Session: {S1_TITLE}, 1 of 1 open")
    (title,) = trigger_nodes(result, S1_TITLE)
    (count,) = trigger_nodes(result, "1 of 1 open")
    assert "text-sm" in title["className"]
    assert "font-medium" in title["className"]
    assert "shrink-0" in count["className"]
    assert "Choose a session" in result["tips"]


def test_trigger_hides_the_count_for_an_empty_board(rig: Rig, tmp_path: Path) -> None:
    result = rig.run(tmp_path, sessionList=S1_LIST)

    button(result, f"Session: {S1_TITLE}")
    assert [n for n in result["nodes"] if n["text"] == "0 of 0 open"] == []
    assert "The agent adds items here." in result["lines"]


def test_no_focused_chat_shows_no_picker(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, focused=None, sessionList=S1_LIST)

    assert [b for b in result["buttons"] if b["label"].startswith("Session:")] == []
    assert result["menuContent"] is None
    assert [c for c in result["restCalls"] if c["path"].startswith("/board")] == []
    assert result["requestCalls"] == []
    assert "Open a chat to see its items." in result["lines"]


def test_menu_lists_focused_first_then_newest_first(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("old", [AddItem("a")], actor="agent", base_rev=0)
    seed_call_john(rig.store)
    rig.store.apply("new", [AddItem("b")], actor="agent", base_rev=0)
    session_list = [session_row("old", "Old board"), session_row("new", "New board")]

    result = rig.run(tmp_path, sessionList=session_list, steps=[OPEN_MENU])

    assert names(result) == ["Untitled session", "New board", "Old board"]
    assert result["menuItems"][1] == {"separator": True}
    assert rows(result)[0]["texts"][1] == "this session - s1"


def test_order_board_ties_and_missing_times(rig: Rig, tmp_path: Path) -> None:
    same = "2026-10-30T12:00:00.000001Z"
    boards = [
        {"root_id": "b", "updated_at": same},
        {"root_id": "z", "updated_at": None},
        {"root_id": "f", "updated_at": same},
        {"root_id": "a", "updated_at": same},
        {"root_id": "n", "updated_at": "2026-10-31T00:00:00.000000Z"},
        {"root_id": "y"},
    ]

    result = rig.run(tmp_path, calls=[{"fn": "orderBoards", "args": [boards, "f"]}])

    (ordered,) = result["callResults"]
    assert [b["root_id"] for b in ordered["others"]] == ["n", "a", "b", "y", "z"]
    assert ordered["focused"]["root_id"] == "f"


def test_title_join_uses_the_lineage_root(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s2", [AddItem("a")], actor="agent", base_rev=0)
    rig.store.apply("s3", [AddItem("b")], actor="agent", base_rev=0)
    session_list = [
        session_row("tip", "Chain", root="s2"),
        session_row("s3", "Direct", root=None),
        session_row("s2", "Compressed away"),
    ]

    result = rig.run(tmp_path, sessionList=session_list, steps=[OPEN_MENU])

    assert "Chain" in names(result)
    assert "Direct" in names(result)
    assert "Compressed away" not in names(result)


def test_preview_is_the_second_choice(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s2", [AddItem("a")], actor="agent", base_rev=0)

    result = rig.run(
        tmp_path,
        sessionList=[session_row("s2", title="", preview="First message here")],
        steps=[OPEN_MENU],
    )

    assert "First message here" in names(result)
    other = [r for r in rows(result) if r["texts"][0] == "First message here"][0]
    assert other["texts"][1] == "1 of 1 open"


def test_missing_session_gives_untitled_with_the_short_id(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply(LONG_ID, [AddItem("a")], actor="agent", base_rev=0)
    rig.store.apply("s1", [AddItem("b")], actor="agent", base_rev=0)

    result = rig.run(tmp_path, sessionList=[], steps=[OPEN_MENU])

    first, second = rows(result)
    assert first["texts"][:2] == ["Untitled session", "this session - s1"]
    assert second["texts"][:2] == ["Untitled session", "e5cc98"]
    button(result, "Session: Untitled session s1, 1 of 1 open")

    focused = rig.run(tmp_path, focused=LONG_ID, sessionList=[], steps=[OPEN_MENU])

    assert rows(focused)[0]["texts"][:2] == ["Untitled session", "this session - e5cc98"]
    button(focused, "Session: Untitled session e5cc98, 1 of 1 open")


def test_first_row_for_a_root_wins(rig: Rig, tmp_path: Path) -> None:
    session_rows = [session_row("a", "First", root="r"), session_row("b", "Second", root="r")]

    result = rig.run(tmp_path, calls=[{"fn": "titleMap", "args": [session_rows]}])

    assert result["callResults"] == [{"r": "First"}]


def test_only_the_focused_board_gives_the_no_other_line(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)

    result = rig.run(tmp_path, sessionList=S1_LIST, steps=[OPEN_MENU])

    focused, none = rows(result)
    assert focused["texts"][0] == S1_TITLE
    assert none == {"texts": [NO_OTHER], "disabled": True, "current": False, "check": False}


def test_boards_failure_gives_the_list_failed_line_and_reopen_retries(
    rig: Rig, tmp_path: Path
) -> None:
    seed_call_john(rig.store)
    rig.store.apply("s2", [AddItem("a")], actor="agent", base_rev=0)
    sequences = {"/boards": ["__error__"]}

    failed = rig.run(tmp_path, restSequences=sequences, steps=[OPEN_MENU])

    focused, line = rows(failed)
    assert focused["current"] is True
    assert line["texts"] == [LIST_FAILED]
    assert line["disabled"] is True

    again = rig.run(tmp_path, restSequences=sequences, steps=[OPEN_MENU, OPEN_MENU])

    assert len(gets(again, "/boards")) == 2
    assert len(rows(again)) == 2
    assert all(not r["disabled"] for r in rows(again))


def test_session_list_failure_keeps_fallback_labels_and_no_error_line(
    rig: Rig, tmp_path: Path
) -> None:
    seed_two_boards(rig)

    result = rig.run(tmp_path, sessionList="__error__", steps=[OPEN_MENU])

    assert names(result) == ["Untitled session", "Untitled session"]
    assert "Call John" in result["lines"]
    assert not [line for line in result["lines"] if "Could not" in line or "Hermes" in line]
    assert result["requestCalls"] != []


def test_session_list_loads_on_mount_and_on_focus_change_not_on_the_poll(
    rig: Rig, tmp_path: Path
) -> None:
    seed_two_boards(rig)
    interval = {"interval": True}

    mounted = rig.run(tmp_path, steps=[interval, interval])
    assert len(mounted["requestCalls"]) == 1
    assert len(gets(mounted, "/board?session_id=s1")) == 3
    assert gets(mounted, "/boards") == []

    full = rig.run(tmp_path, steps=[{"focus": "s2"}, interval, interval, OPEN_MENU])
    assert len(full["requestCalls"]) == 3
    assert len(gets(full, "/boards")) == 1


def test_opening_the_menu_twice_gives_the_same_rows(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    once = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[OPEN_MENU])
    twice = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[OPEN_MENU, OPEN_MENU])

    assert len(gets(twice, "/boards")) == 2
    assert twice["menuItems"] == once["menuItems"]
    assert len(rows(twice)) == 2


def test_fifty_boards_render_in_the_one_content(rig: Rig, tmp_path: Path) -> None:
    seed_call_john(rig.store)
    for number in range(50):
        rig.store.apply(f"board-{number:02d}", [AddItem("x")], actor="agent", base_rev=0)

    result = rig.run(tmp_path, steps=[OPEN_MENU])

    assert len(rows(result)) == 51
    assert result["menuContent"] == {"style": {"width": "304px"}, "align": "start"}


def test_shown_board_row_has_the_check_and_aria_current(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    opened = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[OPEN_MENU])

    assert [(r["current"], r["check"]) for r in rows(opened)] == [(True, True), (False, False)]

    picked = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[OPEN_MENU, {"pick": S2_TITLE}])

    assert [(r["current"], r["check"]) for r in rows(picked)] == [(False, False), (True, True)]


def test_menu_rows_show_the_count_and_the_time(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, nowMs=NOW_MS, steps=[OPEN_MENU])

    focused, other = rows(result)
    assert focused["texts"] == ["Untitled session", "this session - s1", "1 of 1 open", "5 min ago"]
    assert other["texts"] == [S2_TITLE, "1 of 1 open", "5 min ago"]


NOW = 1793631600000  # 2026-11-02T15:00:00Z
TIME_CASES = [
    ("2026-11-02T15:00:00Z", "just now"),
    ("2026-11-02T15:10:00Z", "just now"),
    ("2026-11-02T14:59:01Z", "just now"),
    ("2026-11-02T14:59:00Z", "1 min ago"),
    ("2026-11-02T14:00:01Z", "59 min ago"),
    ("2026-11-02T14:00:00Z", "today 14:00"),
    ("2026-11-02T00:05:00Z", "today 00:05"),
    ("2026-10-30T09:12:00Z", "Oct 30"),
    ("2025-10-30T09:12:00Z", "Oct 30, 2025"),
    (None, None),
    ("", None),
    ("not a date", None),
    ("2026-11-02T14:03:11.123456Z", "56 min ago"),
]


def test_time_labels(rig: Rig, tmp_path: Path) -> None:
    calls = [{"fn": "updatedLabel", "args": [iso, NOW]} for iso, _ in TIME_CASES]

    result = rig.run(tmp_path, calls=calls)

    assert result["callResults"] == [label for _, label in TIME_CASES]


@pytest.mark.parametrize("title", ["T" * 60, "Ten chars!", ""])
def test_truncation_styles(rig: Rig, tmp_path: Path, title: str) -> None:
    seed_call_john(rig.store)
    label = title or "Untitled session s1"

    result = rig.run(
        tmp_path,
        sessionList=[session_row("s1", title)],
        steps=[OPEN_MENU],
    )

    (trigger_title,) = trigger_nodes(result, label)
    assert trigger_title["style"] == TRUNCATE
    (trigger_count,) = trigger_nodes(result, "1 of 1 open")
    assert "shrink-0" in trigger_count["className"]
    assert trigger_count["style"] == {"whiteSpace": "nowrap"}
    name = title or "Untitled session"
    (menu_name,) = [n for n in menu_nodes(result, name) if n["style"] == TRUNCATE]
    assert "font-medium" in menu_name["className"]
    (menu_count,) = menu_nodes(result, "1 of 1 open")
    assert menu_count["style"] == {"whiteSpace": "nowrap"}


def test_menu_right_block_and_check_slot_never_shrink() -> None:
    plugin_source = PLUGIN_JS.read_text(encoding="utf-8")
    assert "MENU_RIGHT_CLASS = 'flex shrink-0 flex-col" in plugin_source
    assert "CARET_CLASS = 'size-4 shrink-0'" in plugin_source


def test_banner_uses_only_the_yellow_border_token(rig: Rig, tmp_path: Path) -> None:
    seed_two_boards(rig)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[OPEN_MENU, {"pick": S2_TITLE}])

    (banner,) = [n for n in result["nodes"] if n["text"] == BANNER]
    classes = banner["className"].split()
    assert "border-(--ui-yellow)" in classes
    assert "text-(--ui-text-primary)" in classes
    assert [c for c in classes if "(--ui-" in c] == [
        "border-(--ui-yellow)",
        "text-(--ui-text-primary)",
    ]
    assert banner["scroll"] is False
