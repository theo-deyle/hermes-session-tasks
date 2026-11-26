---
phase: 04-pane
plan: 06
subsystem: desktop-pane
tags: [hermes-desktop, add-line, subtask, optimistic-write, pytest]
status: complete

requires:
  - phase: 04-pane
    provides: plan 04-04 write path (sendOp, viewBoard, notice line), plan 04-05 ItemBlock and collapse state, plan 04-02 harness steps, plan 04-03 class guards
provides:
  - the Add an item line at the bottom of the list with Enter to save and the cursor kept for the next item
  - pending rows with no id for an add that waits for its reply
  - the Add subtask plus button on top-level rows and the Add a subtask line under the parent
affects: [04-07, 04-08]

requirements-completed: [PANE-04, PANE-06]

actuals:
  tokens: 6800
  tasks: 3
  commits: 7
plan_head_before: 2191ea75304431207ad9e009751b09ed2818f05e
plan_head_after: d65219e5a20176aabc1c927155d3a7b79a2ea419
commits: 7

tech-stack:
  added: []
  patterns:
    - a write guard lives in the shared ref (addBusy, subBusy), not only in state, because two key presses can arrive before the next render
    - AddLine is one stateless component for both lines; Pane owns the text and busy state
    - every class string sits in a className literal or a *_CLASS constant so the shipped-class guard scans it

key-files:
  created:
    - tests/test_pane_add.py
  modified:
    - plugin/desktop/plugin.js
    - tests/desktop_pane_harness.mjs
    - tests/test_desktop_plugin.py

key-decisions:
  - "The add guard is a ref flag as well as state. A stale render closure still holds addBusy false, so a state-only guard let a second Enter send a second write in the duringWrite test."
  - "Escape does nothing while the line's write is in flight, so a failed write can still put the typed text back."
  - "A subtask line is hidden while its parent is collapsed. Its text stays in state."
  - "The add line uses readOnly during a write, not disabled, so the cursor stays in the line (D-30)."

duration: 14 min
completed: 2026-11-01
---

# Phase 4 Plan 06: Add lines Summary

Theo can add an item from the Add an item line (Enter saves, the line empties and keeps focus) and add a subtask from a plus on each top-level row; both show a pending row at once and keep the typed text when the write is stale or fails.

## Accomplishments

- `applyOp(board, op, pendingKey)` handles `add`: a pending item `{id: null, pendingKey, parent_id, text, checked: false}` goes last, or after the last subtask of its parent. `viewBoard` now takes the pending entries and names each key `pending-<seq>`. The key never reaches the route.
- A pending row has `data-item-id` `pending`, a disabled checkbox, plain text, no chevron button and no plus.
- `AddLine` renders one `Input` with `maxLength` 500 and `size` `sm`. The main line sits after the last block, or under the empty state, with `mt-2`. No line shows without a focused chat.
- Add line rules: Enter trims and sends nothing when blank; Escape clears; blur changes nothing; Enter during a write sends nothing; a thrown error or an `ok: false` reply (including a full board of 100 items) restores the text, enables the line and shows `Could not save that change. Try again.`.
- The plus button (`Tip` and `aria-label` `Add subtask`, ghost `icon-xs`, `PLUS_CLASS` built from `REVEAL_CLASS` plus `shrink-0`) shows on top-level rows only. Rows carry the class `group`.
- The plus opens a focused `Add a subtask` line under the parent's last subtask, expands a collapsed parent, closes other empty lines and keeps lines that hold text. Enter posts `{op: 'add', text, parent_id}` with `base_rev`, and the line stays open and empty. Escape closes it. Blur closes it only when empty. A stale add shows the returned board, keeps the text and shows the stale notice, with exactly one POST.

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 (red) | failing end to end test for the add line | c9182ec |
| 1 (green) | add line with Enter and optimistic rows | 2a2f8b5 |
| 2 (red) | add line rule, failure and full board tests | 80d28e6 |
| 2 (green) | add line rules and failure restore | 44aa41a |
| 3 (red) | plus button and subtask line tests | 5b32244 |
| 3 (red fix) | seed the board in the subtask escape and blur test | ca7b581 |
| 3 (green) | plus button and subtask add line | d65219e |

Red lines: Task 1 gave `2 failed` (no add line). Task 2 gave `1 failed, 27 passed` once the harness blur step skipped an Input without a handler: only the Escape test failed. The other seven tests passed at once, because Task 1 built the limits, the failure restore and the in-flight guard (the ref guard). Task 3 gave `7 failed, 10 passed`. One of those seven (escape and blur) failed for a missing seed in the test itself, not for the missing plus; ca7b581 fixes the seed.

## Verification

- `uv run pytest tests/test_pane_add.py tests/test_pane_view.py tests/test_pane_writes.py tests/test_desktop_plugin.py tests/test_pane_harness.py -q -rs`: 98 passed, 0 skipped. tests/test_pane_add.py holds 17 tests. The hermes shipped-class test ran and passed, so `group`, `opacity-0`, `group-hover:opacity-100`, `group-focus-within:opacity-100` and `mt-2` ship in Desktop.
- ruff check, ruff format --check and pyright on tests/test_pane_add.py: clean. `node --check plugin/desktop/plugin.js`: clean.
- Acceptance greps: `const ADD_PLACEHOLDER = 'Add an item'` 1, `const MAX_TEXT_CHARS = 500` 1, `readOnly` 3, `const SUBTASK_PLACEHOLDER = 'Add a subtask'` 1, `group-focus-within:opacity-100` 1, `parent_id: ` 2. `-k full_board_rejects` and `-k enter_during_a_write`: 1 passed each.
- The oldest 04-06 commit is `test(04-06)`.
- plugin.js is 680 lines (ceiling 800). Em dash and en dash scan over plugin.js, tests/test_pane_add.py and tests/desktop_pane_harness.mjs: none found.
- `./scripts/check.sh` last lines:
  - `check: python 3.11 ok` (710 passed, coverage 97.49 percent, gate 80)
  - `check: python 3.14 ok` (710 passed)
  - `check: all ok`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Truncation test broke when plugin.js grew**
- **Found during:** Task 3
- **Issue:** `test_truncated_plugin_fails_the_check` cut the file at half length. With the new code the cut fell right after a top-level block and inside a line comment, which is valid syntax, so the test failed.
- **Fix:** The test now drops the final closing brace of the export list, which is always a syntax error.
- **Files modified:** tests/test_desktop_plugin.py
- **Committed in:** d65219e

**2. [Rule 3 - Blocking] Harness blur step failed on an Input with no onBlur**
- **Found during:** Task 2
- **Issue:** The plan says blur on the add line changes nothing, so the line has no blur handler. The harness called `onBlur` and threw.
- **Fix:** The harness skips the call when the Input has no `onBlur`, as the browser does. The `key` step with `blur: true` got the same guard.
- **Files modified:** tests/desktop_pane_harness.mjs
- **Committed in:** 80d28e6

**3. [Rule 1 - Bug] Test seed missing in the red tests**
- **Found during:** Task 3
- **Issue:** The escape and blur subtask test did not seed an item, so it failed for the wrong reason.
- **Fix:** Added the seed.
- **Files modified:** tests/test_pane_add.py
- **Committed in:** ca7b581

---

**Total deviations:** 3 auto-fixed (2 bug, 1 blocking)
**Impact on plan:** No scope change. One difference from the UI-SPEC, as the plan asked to record: the UI-SPEC Hover and focus reveal rule 2 says hidden buttons use `visibility: 'hidden'` and leave the tab order. Desktop ships no `group-hover:visible` or `group-focus-within:visible`, and the UI-SPEC forbids React hover state, so the hidden plus keeps its 24px space through `opacity-0` and stays in the tab order. Keyboard focus on it reveals it through `group-focus-within:opacity-100`.

## Issues Encountered

None.

## Notes

- `scrollIntoView` after an add is not visible to the harness. Plan 04-08 checks on the Mac that the add line stays in view.
- The harness does not record class names of row `div` elements, so `group` on the row is checked by a static test of the `*_CLASS` constants.
- The [sid] effect clears `addText` and `subLines` on a focus change. The busy flags are cleared by the write outcome callbacks, so a write in flight for the old session briefly leaves the new session's add line read only.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- tests/test_pane_add.py: FOUND
- plugin/desktop/plugin.js: FOUND
- Commits c9182ec, 2a2f8b5, 80d28e6, 44aa41a, 5b32244, ca7b581, d65219e: FOUND on main
