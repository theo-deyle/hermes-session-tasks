---
phase: 06-cross-session-boards
plan: 06
subsystem: desktop-pane
tags: [pane, read-only-view, back, live-update, poll, rev-rule, harness]
status: complete

requires:
  - phase: 06-cross-session-boards
    provides: picker, menu and read-only branch of the pane (plan 06-04)
provides:
  - Back button in the read-only banner (aria-label `Back to {focused label}`)
  - back(), shownRoot(), reloadPicked(), reloadShown() in the pane
  - board.updated listener that matches payload.root_id against the shown board
  - poll that reloads the shown board only
  - per-root rev rule for the picked board
  - pick loads the other board after a saved edit
affects: [06-11 copy buttons, 06-12 live Mac check]

actuals:
  tokens: 9800
  tasks: 3
  commits: 6

plan_head_before: 6bcddd35eff6b3cc70818e1b11f364cfe928f2b8
plan_head_after: f893f6f8d92b75d5337f3e683fb54c6a7c1a0f67
commits: 6

tech-stack:
  added: []
  patterns:
    - "picked board has its own rev map (rootRevs, keyed by root id) beside the focused revs map"
    - "a pick chains its load on the write queue, so a saved edit goes out first"

key-files:
  created:
    - tests/test_pane_readonly.py
  modified:
    - plugin/desktop/plugin.js
    - tests/pane_rig.py
    - tests/test_desktop_plugin.py

key-decisions:
  - "board_gets in tests/pane_rig.py keeps only GET paths that start with `/board?`, because `/boards` and `/board/copy` also start with `/board` (planner decision from the plan)."
  - "MAX_PLUGIN_LINES moved from 1200 to 1400 with the reason in a comment: the pane is one uncompiled file with no relative import. plugin.js is 1203 lines."
  - "The event listener reloads the shown board when the payload, the root or the shown root is missing, and ignores an event for another root."

requirements-completed: [PANE-09]

duration: 30 min
completed: 2026-11-02
---

# Phase 6 Plan 6: Read-only view finish Summary

Back, the root-matched live update, the poll of the shown board and the per-root rev rule finish the read-only view of another session's board.

## What changed

- `ReadOnlyBanner` now holds `Read only. Viewing another session.` and a `Back` text button (`variant: 'text'`, `size: 'inline'`, class `underline`). `back()` clears the picked board and reloads the focused board at once. The add line text, the subtask lines and the pending writes stay in state.
- `shownRoot()` returns the picked root, else the focused root recorded by `take()`.
- `reloadPicked()` drops a reply when the picked board changed meanwhile or when its rev is below `rootRevs[picked]`. A failure sets the load notice and the poll retries it.
- `reloadShown()` calls `reloadPicked()` or `reload()`. The poll interval calls it, so the focused board is not reloaded in the background while another board shows.
- The `board.updated` listener reads `payload.root_id`: it reloads the shown board on a match, a missing root or a missing shown root, and does nothing for another root.
- `pick()` loads the other board through `state.queue.then(reloadPicked)`, so a write queued by `saveEdit()` goes out before the GET of the picked board.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing names kept for the empty-state constants**
- **Found during:** Task 3
- **Issue:** The plan names `PICKED_EMPTY_TITLE` and `PICKED_EMPTY_HINT`. Plan 06-04 already shipped the same strings as `READ_ONLY_EMPTY_TITLE` and `READ_ONLY_EMPTY_HINT`, with the empty state, the picked collapse map, the disabled copy button and the read-only branch of the rows.
- **Fix:** Kept the 06-04 names. No second pair of constants.
- **Files modified:** none

**2. [Rule 1 - Bug] The GET of the picked board went before the saved edit**
- **Found during:** Task 3 RED (`test_an_open_edit_is_saved_before_a_pick`)
- **Issue:** `sendOp` chains the write on the queue, so the POST went out one microtask after the GET.
- **Fix:** `pick()` chains `reloadPicked` on `state.queue`.
- **Files modified:** plugin/desktop/plugin.js
- **Commit:** f893f6f

**3. [Rule 3 - Blocking] Line ceiling raised**
- **Found during:** Task 2
- **Issue:** plugin.js reached 1202 lines, above the 1200 line test ceiling.
- **Fix:** `MAX_PLUGIN_LINES` 1200 to 1400, reason in the comment (one uncompiled file, no relative import), as the dispatch said.
- **Files modified:** tests/test_desktop_plugin.py
- **Commit:** 249313d

**4. Harness step name**
- The plan says `timers` for the poll. Plan 06-04 added the `interval` step, and the poll tests use it.

### Notes on TDD order

The first 06-06 commit is a test commit (`19d08ee`). Task 3 RED failed on one test only. The empty state, the collapse map and the markdown copy were complete in plan 06-04, so those tests pass at once and pin that behavior. `test_an_older_picked_reply_is_dropped` also passed before Task 2 GREEN, because the poll did not touch the picked board yet; it checks the rev rule now that the poll reloads it.

## Commits

1. 19d08ee test(06-06): add failing end to end test for Back
2. 150a94d feat(06-06): Back returns to the focused board
3. 4c80579 test(06-06): add focus, event and poll tests for the read-only view
4. 249313d feat(06-06): live update and poll follow the shown board
5. f46e7d5 test(06-06): add read-only state and no-write tests
6. f893f6f feat(06-06): read-only states and the no-write rule

## Verification

- `uv run pytest tests/test_pane_readonly.py`: 17 passed
- Pane files (picker, desktop_plugin, view, writes, add, edit_delete, harness): 160 passed
- `uv run pytest tests/test_desktop_plugin.py -m hermes`: 1 passed
- `node --check plugin/desktop/plugin.js`: ok
- `hermes plugins validate plugin/`: Validation passed.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`: clean
- Acceptance: 17 tests in test_pane_readonly.py, `Pick another session or go back.` appears once, `startswith("/board?")` once in pane_rig.py, no em dash or en dash.
- `./scripts/check.sh` not run (the orchestrator runs the wave gate).

## Known Stubs

None.

## Threat Flags

None. T-6-17 is covered by `test_read_only_view_sends_no_write`, T-6-18 by `test_focus_change_returns_to_the_focused_board` and `test_an_older_picked_reply_is_dropped`.

## Self-Check: PASSED

- plugin/desktop/plugin.js, tests/test_pane_readonly.py, tests/pane_rig.py, tests/test_desktop_plugin.py present.
- Commits 19d08ee, 150a94d, 4c80579, 249313d, f46e7d5, f893f6f are ancestors of HEAD.
