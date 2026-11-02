---
phase: 06-cross-session-boards
plan: 04
subsystem: desktop-pane
tags: [pane, session-picker, dropdown-menu, read-only-view, harness, desktop-plugin]
status: complete

requires:
  - phase: 04-desktop-pane
    provides: Pane, ItemRow, ItemBlock, Header, Notice, harness and pane_rig
  - phase: 06-cross-session-boards
    provides: GET /boards and GET /board?session_id= routes (plans 06-01, 06-02)
provides:
  - picker row (PickerRow) as the first element of the pane, replacing the header count
  - menu of every board with Hermes titles, fallbacks, order, count and time labels
  - read-only view of another session's board under a banner (disabled checkboxes, no write control)
  - pure helpers shortId, titleMap, boardLabel, menuName, menuSubLine, orderBoards, updatedLabel, pickerAriaLabel
  - harness: DropdownMenu stubs, host.request stub, openMenu, pick, interval steps, calls, sessionList, nowMs
affects: [06-06 Back, focus rule, live updates and read-only edge states, 06-11 copy buttons, 06-12 live Mac check]

actuals:
  tokens: 14200
  tasks: 2
  commits: 4

plan_head_before: 629855182069c1c0e81762a24e79d590b1127a1d
plan_head_after: e75af173ec3a49e416628fa41185286f282c5516
commits: 4

tech-stack:
  added: []
  patterns:
    - "pure helpers exported from the one plain pane file and tested through the harness `calls` key"
    - "menu refreshes on open only (GET /boards plus session.list), never on the poll"
    - "read-only view is a branch on actions.readOnly: no write control is rendered, not hidden"

key-files:
  created:
    - tests/test_pane_picker.py
  modified:
    - plugin/desktop/plugin.js
    - tests/desktop_pane_harness.mjs
    - tests/pane_rig.py
    - tests/test_pane_view.py
    - tests/test_pane_harness.py
    - tests/test_desktop_plugin.py

key-decisions:
  - "The pane stays one plain file over the 800 line soft ceiling (Desktop loads one uncompiled file and refuses a relative import). MAX_PLUGIN_LINES moved from 800 to 1200 with the reason in a comment."
  - "The harness walks the children of a Button, so the trigger title and count show in nodes and lines; nodes carry a `button` flag."
  - "The harness `calls` key tests the pure helpers directly; pane_rig runs node with TZ=UTC."
  - "Selecting the focused row or the row already shown returns to the focused board and reloads it. A focus change clears the picked board. Both follow the UI-SPEC; the Back button itself stays for plan 06-06."

patterns-established:
  - "Menu and trigger share MenuRow and view data; the focused board is pinned first, then a separator, then the others newest first."
  - "Title and count nodes carry TRUNCATE_STYLE and NOWRAP_STYLE; the harness asserts these structural rules."

requirements-completed: [PANE-09]

coverage:
  - id: D1
    description: "Picker row shows the shown board by its Hermes title with an open count and replaces the header count"
    requirement: PANE-09
    verification:
      - kind: integration
        ref: "tests/test_pane_picker.py#test_trigger_names_the_focused_board_and_its_count"
        status: pass
      - kind: integration
        ref: "tests/test_pane_view.py#test_header_sits_outside_the_scroll_area"
        status: pass
  - id: D2
    description: "Menu lists the focused board first, then others newest first, with title join, fallbacks, count and time labels"
    requirement: PANE-09
    verification:
      - kind: integration
        ref: "tests/test_pane_picker.py#test_menu_lists_focused_first_then_newest_first"
        status: pass
      - kind: integration
        ref: "tests/test_pane_picker.py#test_time_labels"
        status: pass
  - id: D3
    description: "Picking another board shows its items read only under the banner, with disabled checkboxes and no add line"
    requirement: PANE-09
    verification:
      - kind: integration
        ref: "tests/test_pane_picker.py#test_pick_another_board_shows_it_read_only"
        status: pass
  - id: D4
    description: "Menu failure and empty states, session.list failure, and the call schedule (mount, focus, open; never the poll)"
    requirement: PANE-09
    verification:
      - kind: integration
        ref: "tests/test_pane_picker.py#test_boards_failure_gives_the_list_failed_line_and_reopen_retries"
        status: pass
      - kind: integration
        ref: "tests/test_pane_picker.py#test_session_list_loads_on_mount_and_on_focus_change_not_on_the_poll"
        status: pass
---

# Phase 6 Plan 4: Session picker and read-only view Summary

**Picker row with Hermes titles, a menu of every board, and a read-only view of another session's board, in the one plain pane file.**

## Performance

- **Tasks:** 2 of 2
- **Commits:** 4 (test, feat, test, feat)
- **Pane file:** 799 lines before, 1148 lines after (ceiling 1200)

## Accomplishments

- The picker row is the first element of the pane. It shows the shown board title, the `{open} of {total} open` count (hidden at total 0) and a caret. It replaces the Phase 4 header count.
- The menu lists the focused board first, a separator, then every other board newest `updated_at` first (no time last, ties by root id). Each row has name, sub-line, count, time label, and `icons.Check` plus `aria-current` on the shown board.
- Titles come from `host.request('session.list', { limit: 200 })`, joined on `_lineage_root_id ?? id`. The title chain is title, preview, `Untitled session` with the short id.
- `GET /boards` and `session.list` run when the menu opens. `session.list` also runs on mount and on a focus change. Neither runs on the 6000 ms poll.
- A pick loads `GET /board?session_id=<root>` and shows the items under the banner `Read only. Viewing another session.` Checkboxes are disabled. The view has no add line, edit, plus, trash or subtask line. Chevron collapse works through its own collapse map.
- Empty menu and failure lines: `No other session has a board.` and `Could not load the session list. Reopen the list to retry.`
- Harness: DropdownMenu stubs, `host.request` stub, `openMenu`, `pick`, `interval` steps, `calls`, `sessionList` and `nowMs` config, `menuItems`, `menuContent`, `requestCalls` and `callResults` outputs.

## Task Commits

1. Task 1 RED: `ecd0828` test(06-04): add failing end to end test for the session picker
2. Task 1 GREEN: `921cb48` feat(06-04): session picker with titles and a read-only view of another board
3. Task 2 RED: `b77d4db` test(06-04): add picker label, order, time and state tests
4. Task 2 GREEN: `e75af17` feat(06-04): picker labels, order, time labels and list states

## Decisions Made

Planner decisions recorded as the plan asked:

1. One pane file over the 800 line soft ceiling. Reason: Desktop loads one uncompiled file and refuses a relative import. `MAX_PLUGIN_LINES = 1200`.
2. The harness walks the children of a `Button` after it records the button.
3. The harness `calls` key gives the pure helpers direct tests.
4. `pane_rig._run_node` sets `TZ=UTC`.

Assumptions:

- RESEARCH A7: `Date.parse` takes the 6-digit fraction. Settled by `test_time_labels` (`2026-11-02T14:03:11.123456Z` gives `56 min ago`).
- RESEARCH Q2: `host.request('session.list')` from a plugin pane is documented but unproven in a real Desktop. The harness stub proves the pane side only. The live check in plan 06-11 and 06-12 is the proof; the fallback labels are the failure path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Harness steps the plan did not name**
- **Found during:** Task 2 (`test_session_list_loads_on_mount_and_on_focus_change_not_on_the_poll`, time label rows)
- **Issue:** The plan says to use `timers` steps for poll ticks, but the harness `setInterval` stub never calls its callback, and `Date.now()` inside the pane is the real clock. Neither test could run as written.
- **Fix:** Added the `interval` step (runs every uncancelled `ctx.setInterval` callback once) and the `nowMs` config key (fixes `Date.now()` in the plugin VM context). Documented both in the harness header.
- **Files modified:** tests/desktop_pane_harness.mjs
- **Commit:** b77d4db

**2. [Rule 1 - Bug] Menu item texts missed a plain string child**
- **Found during:** Task 2 (disabled `No other session has a board.` item)
- **Issue:** `texts` collected only host descendants, so an item whose child is a string had empty texts.
- **Fix:** `texts` now includes the item's own direct strings first.
- **Files modified:** tests/desktop_pane_harness.mjs
- **Commit:** b77d4db

**3. [Rule 2 - Missing critical] Way back from the read-only view**
- **Found during:** Task 1 (Back arrives only in plan 06-06)
- **Issue:** Without a way back, a pick would trap the pane in the read-only view until the chat changed.
- **Fix:** Selecting the focused row or the shown row returns to the focused board and reloads it (UI-SPEC Picker menu 5). A focus change clears the picked board (UI-SPEC Read-only view 9). The Back button stays in plan 06-06.
- **Files modified:** plugin/desktop/plugin.js
- **Commit:** 921cb48

**4. Tests that adapt to the new DOM shape**
- `test_header_sits_outside_the_scroll_area` finds the title and the count among the nodes inside the trigger Button, because the always-rendered menu rows repeat the same texts. (tests/test_pane_view.py, ecd0828, finished in 921cb48)
- The banner is a `div` whose direct child is the text, so the node carries the banner class. Plan 06-06 adds Back beside it. (e75af17)

**5. Commit attribution line**
- The dispatch asked for `Co-Authored-By: Claude Fable 5.1`. The session attribution reminder names `Claude Sonnet 5.5`, which is the model that ran this plan. The four commits carry the Sonnet 5.5 line.

### Notes on TDD order

Task 1 builds all pure helpers and the full picker (the plan puts them in Task 1 step 3). Task 2 RED therefore failed on four tests only (truncation styles x3, banner class), and the label, order and time tests passed against the Task 1 code. The first 06-04 commit is the test commit `ecd0828`.

## Issues Encountered

- The pane file is 1148 lines, 52 below the 1200 ceiling. Plans 06-06 (Back, live updates, edge states) and 06-11 (copy buttons, notice) will add more. Raise `MAX_PLUGIN_LINES` again with a reason, or trim, when one of them hits the ceiling. This is flagged for the orchestrator.

## Verification

- `uv run pytest tests/test_pane_picker.py tests/test_pane_view.py tests/test_pane_writes.py tests/test_pane_add.py tests/test_pane_edit_delete.py tests/test_pane_harness.py tests/test_desktop_plugin.py -q -rs`: 160 passed
- `uv run pytest tests/test_desktop_plugin.py -q -rs -m hermes`: 1 passed (every new class ships in Desktop)
- `node --check plugin/desktop/plugin.js`: ok
- `hermes plugins validate plugin/`: Validation passed.
- `grep -c "^def test_" tests/test_pane_picker.py`: 22 (plan asks 17 or more; the file also has 3 parametrized cases)
- Acceptance greps: `DropdownMenuTrigger` 2, `host.request` 1, banner string 1, no `dangerouslySetInnerHTML`, no colour literal, no em dash or en dash.
- `./scripts/check.sh` (wave end gate, python 3.11 and 3.14): 942 passed per interpreter, coverage 97 percent. Last line: `check: all ok`

## Known Stubs

None.

## Threat Flags

None. T-6-10 (text children only, no raw HTML), T-6-11 (call schedule test) and T-6-12 (read-only view renders no write control) are all covered by tests.

## Self-Check: PASSED

- plugin/desktop/plugin.js, tests/test_pane_picker.py, tests/desktop_pane_harness.mjs, tests/pane_rig.py present.
- Commits ecd0828, 921cb48, b77d4db, e75af17 are ancestors of HEAD.
