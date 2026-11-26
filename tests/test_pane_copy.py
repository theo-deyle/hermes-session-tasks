"""Copy from another session's board into the focused board: buttons, queue, replies and the notice."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pane_rig import Rig, board_gets, button, posts, stale_body
from session_tasks.model import AddItem

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

OPEN_MENU = {"openMenu": True}
S1_TITLE = "Lease renewal"
S2_TITLE = "Syncro ticket 4910"
SESSION_LIST = [
    {"id": "s1", "title": S1_TITLE, "preview": "", "_lineage_root_id": None},
    {"id": "s2", "title": S2_TITLE, "preview": "", "_lineage_root_id": None},
]
PICK_S2 = [OPEN_MENU, {"pick": S2_TITLE}]
ROW_COPY = {"label": f"Copy item to {S1_TITLE}", "row": "1"}
BACK_TO_S1 = {"click": f"Back to {S1_TITLE}"}
COPY_ALL = f"Copy all open to {S1_TITLE}"
ROW_ARIA = f"Copy item to {S1_TITLE}"
WRITE_FAILED = "Could not save that change. Try again."
STALE = "Board changed, showing the latest"
REPLY = "Reply to the customer"


def seed(rig: Rig) -> None:
    """Board s1 holds `Mine` at rev 1 and board s2 holds `Reply to the customer`."""
    rig.store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    rig.store.apply("s2", [AddItem(REPLY)], actor="agent", base_rev=0)


def copied_sentence(result: dict[str, Any]) -> str:
    """The copied notice as one sentence, joined from its pieces."""
    found = [entry for entry in result["titled"] if entry["title"].startswith("Copied ")]
    assert len(found) == 1, f"{len(found)} copied notices"
    return "".join(found[0]["texts"])


def test_row_copy_copies_one_item_into_the_focused_board(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    steps = [*PICK_S2, {"click": ROW_COPY}]

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=steps)

    (copy,) = posts(result)
    assert copy["path"] == "/board/copy"
    assert copy["body"] == {
        "session_id": "s1",
        "from_session_id": "s2",
        "item_ids": [1],
        "base_rev": 1,
    }
    sentence = "Copied 1 to Lease renewal. 0 skipped, already on the board."
    assert copied_sentence(result) == sentence
    assert "Read only. Viewing another session." in result["lines"]
    assert [i.text for i in rig.store.get_board("s2").items] == [REPLY]
    s1_items = rig.store.get_board("s1").items
    assert [i.text for i in s1_items] == ["Mine", REPLY]
    assert s1_items[1].id == 2
    assert s1_items[1].updated_by == "user"


def test_after_a_copy_back_shows_the_copied_item(rig: Rig, tmp_path: Path) -> None:
    seed(rig)

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        steps=[*PICK_S2, {"click": ROW_COPY}, BACK_TO_S1],
    )

    assert "Read only. Viewing another session." not in result["lines"]
    assert "Mine" in result["lines"]
    assert REPLY in result["lines"]
    assert [c["path"] for c in posts(result)] == ["/board/copy"]


def seed_s1(rig: Rig) -> None:
    rig.store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)


def seed_s2(rig: Rig, *items: AddItem) -> None:
    rig.store.apply("s2", list(items), actor="agent", base_rev=0)


def test_copy_all_open_omits_item_ids(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s1", [AddItem("Mine")], actor="agent", base_rev=0)
    seed_s2(rig, AddItem("One"), AddItem("Two"), AddItem("Done", checked=True))

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"click": COPY_ALL}])

    (copy,) = posts(result)
    assert copy["path"] == "/board/copy"
    assert copy["body"] == {"session_id": "s1", "from_session_id": "s2", "base_rev": 1}
    assert copied_sentence(result) == "Copied 2 to Lease renewal. 0 skipped, already on the board."
    assert [i.text for i in rig.store.get_board("s1").items] == ["Mine", "One", "Two"]


def test_copy_all_open_is_disabled_without_open_items(rig: Rig, tmp_path: Path) -> None:
    seed_s1(rig)
    seed_s2(rig, AddItem("Done", checked=True))

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=PICK_S2)

    assert button(result, COPY_ALL)["disabled"] is True
    assert button(result, ROW_ARIA, row="1")["disabled"] is False


def test_empty_picked_board_disables_both_copy_controls(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    empty = {"ok": True, "root_id": "s2", "rev": 1, "board": {"items": []}}

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restSequences={"/board?session_id=s2": [empty]},
        steps=PICK_S2,
    )

    assert button(result, COPY_ALL)["disabled"] is True
    assert result["copy"]["disabled"] is True


def test_subtask_rows_have_no_copy_button_and_checked_top_level_rows_have_one(
    rig: Rig, tmp_path: Path
) -> None:
    seed_s1(rig)
    seed_s2(
        rig,
        AddItem("Plan move", checked=True),
        AddItem("Rent van", parent_ref=0),
        AddItem("Box books", parent_ref=0),
        AddItem("Second"),
    )

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=PICK_S2)

    rows = [b["row"] for b in result["buttons"] if b["label"] == ROW_ARIA]
    assert rows == ["1", "4"]
    assert not any(
        b["row"] in ("2", "3") and b["label"].startswith("Copy") for b in result["buttons"]
    )


def test_a_copy_waits_for_a_write_in_flight(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    # The menu loads first; during the held check the pane picks s2, loads it with a poll and clicks Copy.
    during = [{"pick": S2_TITLE}, {"interval": True}, {"render": True}, {"click": ROW_COPY}]

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        steps=[OPEN_MENU, {"check": {"row": "1", "value": True}}],
        duringWrite=during,
    )

    assert [(p["path"], p["body"]["base_rev"]) for p in posts(result)] == [
        ("/board/edit", 1),
        ("/board/copy", 2),
    ]
    assert [i.text for i in rig.store.get_board("s1").items] == ["Mine", REPLY]


def test_double_click_sends_one_copy(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    click = {"click": ROW_COPY}

    result = rig.run(
        tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"burst": [click, click]}]
    )

    assert [p["path"] for p in posts(result)] == ["/board/copy"]
    held = [b for b in result["atWrite"][0]["buttons"] if b["label"].startswith("Copy")]
    assert [b["label"] for b in held] == [COPY_ALL, ROW_ARIA]
    assert all(b["disabled"] for b in held)


def test_a_copy_is_never_retried(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    stale = stale_body(rig.store.get_board("s1"), "s1")

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restSequences={"/board/copy": [stale, stale]},
        steps=[*PICK_S2, {"click": ROW_COPY}],
    )

    assert [p["path"] for p in posts(result)] == ["/board/copy"]


def after_post(result: dict[str, Any]) -> list[str]:
    """The paths of the board GETs that came after the first POST."""
    calls = result["restCalls"]
    first = next(i for i, c in enumerate(calls) if c["method"] == "POST")
    return [c["path"] for c in calls[first:] if c in board_gets(result)]


def test_source_item_gone_reloads_and_shows_the_stale_notice(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    stale = stale_body(rig.store.get_board("s1"), "s1")

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restSequences={"/board/copy": [stale]},
        steps=[*PICK_S2, {"click": ROW_COPY}],
    )

    assert STALE in result["lines"]
    (stale_notice,) = [n for n in result["nodes"] if n["text"] == STALE]
    assert stale_notice["role"] == "status"
    assert after_post(result) == ["/board?session_id=s2"]


@pytest.mark.parametrize(
    "reply",
    ["__error__", {"ok": False, "error": "invalid", "message": "no"}],
    ids=["throws", "invalid"],
)
def test_a_failed_copy_reloads_the_focused_board_and_shows_the_failed_notice(
    rig: Rig, tmp_path: Path, reply: Any
) -> None:
    seed(rig)

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restSequences={"/board/copy": [reply]},
        steps=[*PICK_S2, {"click": ROW_COPY}],
    )

    assert WRITE_FAILED in result["lines"]
    assert after_post(result) == ["/board?session_id=s1"]


def test_focus_change_during_a_copy_keeps_its_session(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    board = {"items": [{"id": 1, "text": "Mine", "checked": False, "parent_id": None}]}
    ok = {
        "ok": True,
        "root_id": "s1",
        "rev": 5,
        "copied": 1,
        "skipped": 0,
        "overflow": 0,
        "board": board,
    }
    add = {"input": {"placeholder": "Add an item"}}

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restSequences={"/board/copy": [ok]},
        duringWrite=[{"focus": "s3"}, {"render": True}],
        steps=[
            *PICK_S2,
            {"click": ROW_COPY},
            {"focus": "s1"},
            {"type": {**add, "text": "Next"}},
            {"key": {**add, "key": "Enter"}},
        ],
    )

    first, second = posts(result)
    assert first["body"]["session_id"] == "s1"
    assert not any(line.startswith("Copied ") for line in result["lines"])
    assert second["path"] == "/board/edit"
    assert second["body"]["base_rev"] == 5


def test_an_already_open_text_is_skipped(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s1", [AddItem("Mine"), AddItem(REPLY)], actor="agent", base_rev=0)
    seed_s2(rig, AddItem(REPLY))

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"click": ROW_COPY}])

    sentence = "Copied 0 to Lease renewal. 1 skipped, already on the board."
    assert copied_sentence(result) == sentence


def test_cap_clause_shows_only_when_items_were_cut(rig: Rig, tmp_path: Path) -> None:
    rig.store.apply("s1", [AddItem(f"Item {n}") for n in range(99)], actor="agent", base_rev=0)
    seed_s2(rig, AddItem("One"), AddItem("Two"))

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"click": COPY_ALL}])

    assert copied_sentence(result) == (
        "Copied 1 to Lease renewal. 0 skipped, already on the board."
        " 1 not copied, the board holds 100 items."
    )


def notice_of(result: dict[str, Any]) -> dict[str, Any]:
    """The one titled element of the copied notice."""
    found = [entry for entry in result["titled"] if entry["title"].startswith("Copied ")]
    assert len(found) == 1, f"{len(found)} copied notices"
    return found[0]


def copied_args(copied: int, skipped: int, overflow: int) -> dict[str, Any]:
    return {"copied": copied, "skipped": skipped, "overflow": overflow, "label": "Lease renewal"}


@pytest.mark.parametrize(
    ("args", "tail"),
    [
        (copied_args(0, 0, 0), ". 0 skipped, already on the board."),
        (copied_args(1, 0, 0), ". 0 skipped, already on the board."),
        (copied_args(3, 2, 0), ". 2 skipped, already on the board."),
        (
            copied_args(2, 0, 1),
            ". 0 skipped, already on the board. 1 not copied, the board holds 100 items.",
        ),
    ],
)
def test_copy_notice_text(rig: Rig, tmp_path: Path, args: dict[str, Any], tail: str) -> None:
    result = rig.run(tmp_path, calls=[{"fn": "copyNoticeText", "args": [args]}])

    (pieces,) = result["callResults"]
    assert pieces == {
        "head": f"Copied {args['copied']} to ",
        "title": "Lease renewal",
        "tail": tail,
        "full": f"Copied {args['copied']} to Lease renewal{tail}",
    }


def test_copied_notice_is_three_pieces_on_one_line(rig: Rig, tmp_path: Path) -> None:
    seed(rig)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[*PICK_S2, {"click": ROW_COPY}])

    notice = notice_of(result)
    assert notice["title"] == "Copied 1 to Lease renewal. 0 skipped, already on the board."
    assert notice["role"] == "status"
    assert notice["style"] == {
        "whiteSpace": "nowrap",
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "display": "flex",
    }
    assert {"text-xs", "text-(--ui-text-secondary)"} <= set(notice["className"].split())
    head, title, tail = notice["pieces"]
    assert [p["text"] for p in (head, title, tail)] == notice["texts"]
    assert "shrink-0" in head["className"].split()
    assert "shrink-0" in tail["className"].split()
    assert title["style"] == {
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "whiteSpace": "nowrap",
        "minWidth": 0,
    }
    assert head["style"] is None
    assert tail["style"] is None


def test_a_long_title_truncates_only_in_the_title_piece(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    long_title = "Renewal of the lease for the north shop " + "x" * 20
    assert len(long_title) == 60
    session_list = [{**SESSION_LIST[0], "title": long_title}, SESSION_LIST[1]]
    row = {"label": f"Copy item to {long_title}", "row": "1"}

    result = rig.run(tmp_path, sessionList=session_list, steps=[*PICK_S2, {"click": row}])

    notice = notice_of(result)
    assert notice["texts"] == [
        "Copied 1 to ",
        long_title,
        ". 0 skipped, already on the board.",
    ]
    assert notice["title"] == "".join(notice["texts"])
    assert notice["pieces"][1]["style"]["textOverflow"] == "ellipsis"
    assert notice["pieces"][0]["style"] is None


def test_copied_notice_clears_after_4000_ms(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    steps = [*PICK_S2, {"click": ROW_COPY}]

    shown = rig.run(tmp_path, sessionList=SESSION_LIST, steps=steps)
    cleared = rig.run(tmp_path, sessionList=SESSION_LIST, steps=[*steps, {"timers": True}])

    assert 4000 in shown["timeouts"]
    assert any(t["title"].startswith("Copied ") for t in shown["titled"])
    assert not any(t["title"].startswith("Copied ") for t in cleared["titled"])


def test_notice_priority_mismatch_beats_copied(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    mismatch = "Version mismatch: update the desktop plugin on this machine"
    meta = {"ok": True, "plugin_id": "x", "backend_version": "9.9.9", "api_version": 1}

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restOverrides={"/meta": meta},
        steps=[*PICK_S2, {"click": ROW_COPY}],
    )

    assert mismatch in result["lines"]
    assert result["titled"] == []


def test_a_later_stale_notice_replaces_the_copied_one(rig: Rig, tmp_path: Path) -> None:
    seed(rig)
    stale = stale_body(rig.store.get_board("s1"), "s1")

    result = rig.run(
        tmp_path,
        sessionList=SESSION_LIST,
        restSequences={"/board/copy": ["__relay__", stale]},
        steps=[*PICK_S2, {"click": ROW_COPY}, {"click": ROW_COPY}],
    )

    assert STALE in result["lines"]
    assert result["titled"] == []


def test_copy_all_open_label_truncates(rig: Rig, tmp_path: Path) -> None:
    seed(rig)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=PICK_S2)

    copy_all = button(result, COPY_ALL)
    assert copy_all["variant"] == "outline"
    assert copy_all["size"] == "sm"
    assert "min-w-0" in copy_all["className"].split()
    assert COPY_ALL in result["tips"]
    spans = [n for n in result["nodes"] if n["text"] == COPY_ALL and n["button"]]
    assert len(spans) == 1
    assert spans[0]["style"]["textOverflow"] == "ellipsis"
    assert spans[0]["style"]["minWidth"] == 0


def test_row_copy_keeps_its_space(rig: Rig, tmp_path: Path) -> None:
    seed(rig)

    result = rig.run(tmp_path, sessionList=SESSION_LIST, steps=PICK_S2)

    row_copy = button(result, ROW_ARIA, row="1")
    assert row_copy["variant"] == "ghost"
    assert row_copy["size"] == "sm"
    classes = row_copy["className"].split()
    for wanted in ("opacity-0", "group-hover:opacity-100", "group-focus-within:opacity-100"):
        assert wanted in classes
    assert row_copy["text"] == "Copy"
