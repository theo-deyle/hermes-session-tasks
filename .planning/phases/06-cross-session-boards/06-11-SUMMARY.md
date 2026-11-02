---
phase: 06-cross-session-boards
plan: 11
subsystem: desktop-pane
tags: [pane, copy, write-queue, notice, harness]
status: complete

requires:
  - phase: 06-cross-session-boards
    provides: picker and read-only view (06-04, 06-06), POST /board/copy (06-09)
provides:
  - Row Copy button on top-level read-only rows (aria-label `Copy item to {focused label}`)
  - Copy all open to {focused label} button in the header row
  - copyItems and runCopy inside the one-at-a-time write queue
  - copied notice (copyNoticeText) as three pieces on one line
affects: [06-12 live Mac check]

actuals:
  tokens: 8400
  tasks: 3
  commits: 6

plan_head_before: 60d965b313db5b3aa5fd06c702c79405c3f4ce81
plan_head_after: e16137e365ccc9fb7814b181c2d75db942284c40
commits: 6

tech-stack:
  added: []
  patterns:
    - "a copy keeps its session and root from click time and reads base_rev when it runs in the queue"
    - "one ref flag (copyBusy) set before the request is queued guards a double click"

key-files:
  created:
    - tests/test_pane_copy.py
  modified:
    - plugin/desktop/plugin.js
    - tests/desktop_pane_harness.mjs
    - tests/test_pane_readonly.py

key-decisions:
  - "The copy notice shows for 'copied' only when the asked session is still focused. Stale and failed notices show regardless, as in Phase 4."
  - "copyBusy is not reset on a focus change: the request is still in flight, so the controls stay off until its outcome."
  - "plugin.js is 1342 lines, under the 1400 ceiling, so MAX_PLUGIN_LINES stays as plan 06-06 left it."

requirements-completed: [PANE-10]

duration: 40 min
completed: 2026-11-02
---

# Phase 6 Plan 11: Pane copy Summary

Theo copies one item, or all open items, from another session's board into the focused board with one click, and the pane says how many copied, how many skipped and how many the 100 item cap cut.

## What changed

- Row `Copy` button (`variant: 'ghost'`, `size: 'sm'`, Phase 4 reveal classes) on every top-level row of the read-only view, checked or not. Subtask rows have none.
- `CopyAllButton` (`variant: 'outline'`, `size: 'sm'`, `min-w-0`, label span with the truncation style, full label in the Tip and aria-label) in the header row before the markdown `CopyButton`. Disabled when the shown board has no open item or a copy runs.
- `copyItems(itemIds, label)` reads the focused sid and the picked root at click time, sets the `copyBusy` ref and state, and chains `runCopy` on the write queue. `runCopy` counts as `inFlight`, reads `base_rev` when it runs, sends one `POST /board/copy` with `session_id`, `from_session_id`, `base_rev` and `item_ids` (row Copy only), and never retries.
- Replies: ok goes through `take(asked, reply)` and shows the copied notice if that session is still focused. Stale takes the board, reloads the picked board and shows `Board changed, showing the latest`. Anything else, or a throw, reloads the focused board and shows `Could not save that change. Try again.`
- `copyNoticeText` (exported) returns `{head, title, tail, full}`. The `Notice` renders a copied notice as three spans in one flex line with the full sentence as `title`; only the title span truncates.
- Harness additions: Button records `variant`, `size` and `text`; a `titled` output (elements with a string `title`, with their texts and direct host children); `atWrite` now holds `buttons`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing no-write test**
- **Found during:** Task 1 and Task 2 GREEN
- **Issue:** `test_read_only_view_sends_no_write` in tests/test_pane_readonly.py lists the allowed enabled button labels. The new Copy buttons are enabled by design.
- **Fix:** Added `Copy item to ` and `Copy all open to ` to the allowed prefixes. The test still asserts that no POST goes out.
- **Files modified:** tests/test_pane_readonly.py
- **Commits:** 53ceb1b, 0b62b1f

**2. [Rule 3 - Blocking] Harness could not see the notice pieces or the button class and text**
- **Found during:** Task 1 RED
- **Issue:** The copied notice is a container with span children and no direct text, so the harness recorded no node for it. Button `variant`, `size` and visible text were not recorded, and `atWrite` held no buttons.
- **Fix:** The harness additions listed above.
- **Files modified:** tests/desktop_pane_harness.mjs
- **Commits:** b9ddc66, 65bb5da

### Notes on TDD order

The first 06-11 commit is a test commit (b9ddc66). Task 1 GREEN already held the full `runCopy` outcome handling (stale, failed, focus rule), so the Task 2 RED run failed on 5 tests (Copy all open, the disabled cases and the cap clause) and the other 10 passed at once and pin that behavior. Task 3 RED failed on the layout tests only (3 failures).

`test_a_copy_waits_for_a_write_in_flight` loads the picked board during the held check with the harness `interval` step (the poll reloads the shown board without the write queue), then renders and clicks Copy.

## Commits

1. b9ddc66 test(06-11): add failing end to end test for a row copy
2. 53ceb1b feat(06-11): copy one item from another board into the focused board
3. 4032c35 test(06-11): add copy queue, reply and focus tests
4. 0b62b1f feat(06-11): copy all open, queue order and copy replies
5. 65bb5da test(06-11): add copied notice layout and priority tests
6. e16137e feat(06-11): the copied notice keeps its counts visible on one line

## Verification

- `uv run pytest tests/test_pane_copy.py`: 26 passed
- All pane files (copy, readonly, picker, view, writes, add, edit_delete, harness, desktop_plugin): 203 passed
- `uv run pytest tests/test_desktop_plugin.py -m hermes`: 1 passed
- `node --check plugin/desktop/plugin.js`: ok
- `hermes plugins validate plugin/`: Validation passed.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`: clean
- plugin.js is 1342 lines against the 1400 ceiling. No em dash or en dash in the files written.
- `./scripts/check.sh` not run (the orchestrator runs the wave gate).

## Known Stubs

None.

## Threat Flags

None. T-6-35 is covered by `test_row_copy_copies_one_item_into_the_focused_board` and `test_focus_change_during_a_copy_keeps_its_session`, T-6-36 by `test_double_click_sends_one_copy` and `test_a_copy_is_never_retried`, T-6-37 by `test_a_copy_waits_for_a_write_in_flight`.

## Self-Check: PASSED

- plugin/desktop/plugin.js, tests/test_pane_copy.py, tests/desktop_pane_harness.mjs, tests/test_pane_readonly.py present.
- Commits b9ddc66, 53ceb1b, 4032c35, 0b62b1f, 65bb5da, e16137e are ancestors of HEAD.
