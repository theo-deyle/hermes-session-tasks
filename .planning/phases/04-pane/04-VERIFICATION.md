---
phase: 04-pane
verified: 2026-11-01T23:30:00Z
status: passed
score: 10/10 must-haves verified
covered_files:
  - .planning/phases/04-pane/04-01-PLAN.md
  - .planning/phases/04-pane/04-01-SUMMARY.md
  - .planning/phases/04-pane/04-02-PLAN.md
  - .planning/phases/04-pane/04-02-SUMMARY.md
  - .planning/phases/04-pane/04-03-PLAN.md
  - .planning/phases/04-pane/04-03-SUMMARY.md
  - .planning/phases/04-pane/04-04-PLAN.md
  - .planning/phases/04-pane/04-04-SUMMARY.md
  - .planning/phases/04-pane/04-05-PLAN.md
  - .planning/phases/04-pane/04-05-SUMMARY.md
  - .planning/phases/04-pane/04-06-PLAN.md
  - .planning/phases/04-pane/04-06-SUMMARY.md
  - .planning/phases/04-pane/04-07-PLAN.md
  - .planning/phases/04-pane/04-07-SUMMARY.md
  - .planning/phases/04-pane/04-08-PLAN.md
  - .planning/phases/04-pane/04-08-SUMMARY.md
  - .planning/phases/04-pane/04-09-PLAN.md
  - .planning/phases/04-pane/04-09-SUMMARY.md
  - plugin/desktop/plugin.js
  - scripts/install-desktop.ps1
  - tests/conftest.py
  - tests/desktop_pane_harness.mjs
  - tests/pane_rig.py
  - tests/test_desktop_plugin.py
  - tests/test_install_script.py
  - tests/test_pane_add.py
  - tests/test_pane_edit_delete.py
  - tests/test_pane_harness.py
  - tests/test_pane_view.py
  - tests/test_pane_writes.py
covered_digest: "v4:sha256:30a9735f0db486693bdda3b84fe3fe20cfdd90325f2c7fc4a368253fdb6e182e"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 10/10
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 4: Pane Verification Report

**Phase Goal:** Theo sees and edits the focused session's board in a right-side pane. The pane updates live when the agent writes.
**Verified:** 2026-11-01
**Status:** passed
**Re-verification:** Yes - after the code review fixes (CR-01, WR-01 to WR-05). The previous report was stale because the fixes changed `plugin/desktop/plugin.js`, `tests/desktop_pane_harness.mjs`, `tests/test_pane_edit_delete.py` and `tests/test_pane_writes.py`.

## Goal Achievement

The verifier re-read all 799 lines of `plugin/desktop/plugin.js` as it stands now. The review fixes keep every earlier truth intact and add guards on the focus-change and error paths.

**The pane file changed after the Mac live round.** The Mac round (04-08-SUMMARY.md, 11 of 11 passed) ran the file with SHA-256 prefix `04adc10fda44b3cb` (789 lines). The file now has prefix `91b46447782493a5` (799 lines). The diff since the code review (`b0b729e`) is 94 changed lines in `plugin.js` plus 275 lines in the tests and harness. The changes touch only focus-change handling, edit session ownership, the write queue, busy-flag reset, `isMismatch` and the kept-text store. No render markup, class name, style or layout line changed. The visual criteria that the live round covered are therefore not affected, and no second human pass is requested.

Tests that cover the changed behaviour (each was written first and failed on the old code, per 04-REVIEW-FIX.md):

| Fix | Test | File |
|-----|------|------|
| CR-01 | `test_blur_after_a_focus_change_never_writes_to_the_new_session` | tests/test_pane_edit_delete.py |
| WR-04 | `test_failed_text_is_kept_when_another_edit_opened_meanwhile`, `test_failed_text_is_kept_when_the_focus_changed_meanwhile` | tests/test_pane_edit_delete.py |
| WR-01 | `test_one_thrown_error_does_not_stop_later_writes` | tests/test_pane_writes.py |
| WR-02 | `test_add_line_of_the_new_session_works_while_the_old_write_runs`, `test_old_subtask_write_does_not_touch_the_line_of_the_same_parent_later`, `test_load_failed_notice_does_not_follow_a_focus_change` | tests/test_pane_writes.py |
| WR-03 | `test_returning_to_a_session_keeps_its_rev_for_the_next_write`, `test_a_render_that_never_commits_does_not_move_the_write_session` | tests/test_pane_writes.py |
| WR-05 | `test_empty_meta_reply_does_not_crash_the_render` | tests/test_pane_writes.py |

The verifier read the code of each fix and found it matches the test:

- CR-01: the edit record carries `sid` (plugin.js 677). `saveEdit` returns without a write when `open.sid !== state.sid` (689) and sends the write with `open.sid` as the asked session (695). The failure path reopens the edit only when the focused session is the edit's own and its board holds the item (692-694).
- WR-01: the queue ends in `.catch(() => undefined)` (592). `onOutcome` runs in a `finally` (539-541). Busy flags always reset.
- WR-02: a `visit` counter goes up in the `[sid]` effect (561). The add and subtask callbacks capture it and return when it changed (604, 647). The effect resets `addBusy`, `subBusy` and `loadFailed` (562-570).
- WR-03: the render writes no ref. The `[sid]` effect sets `current.sid` (559). No code deletes a rev.
- WR-04: a failed or stale save goes to `kept[sid:itemId]` when the edit cannot reopen (694). `startEdit` starts from the kept text (675-676).
- WR-05: `isMismatch` guards `!meta` (200).

## Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | SC1: A right-side pane shows the focused session's board, switches on focus change, and an empty board says the agent adds items here | VERIFIED | `register()` sets `placement: 'right'`, `dock`, `width: '320px'` (788). `Pane` reads `useValue(host.state.focusedStoredSessionId)` (414). The `[sid]` effect resets local state and reloads (558-577). `shown` hides a board that belongs to another session (435). Empty state "The agent adds items here." with hint "Add one below." (34-35, 747). Tests: `test_focus_change_shows_the_new_board`, `test_collapse_state_resets_on_focus_change`, `test_empty_board_shows_the_empty_state`, `test_no_focused_chat_shows_open_a_chat`, `test_plugin_name_and_registration`. Live steps 2 and 3 passed. |
| 2  | SC2: Items show as checkboxes with indented, collapsible subtasks. A check shows at once and reconciles on the returned revision | VERIFIED | `buildTree`, `ItemRow` (SDK `Checkbox`), `Chevron`, `subtaskCountText`. `viewBoard` applies pending ops over the last server board. `postOp` sends `base_rev` and `take()` adopts the returned rev. Tests: `test_check_reaches_the_store`, `test_check_shows_before_the_reply`, `test_collapse_hides_subtasks_and_keeps_the_count`, `test_expand_shows_the_subtasks_again`, `test_parent_and_subtasks_check_independently`. Live steps 3 and 4 passed. |
| 3  | SC3: Theo adds an item inline and keeps typing, edits text inline, adds a subtask, deletes an item and the pane confirms when subtasks go too | VERIFIED | `submitAdd` (596-612), `startEdit` and `saveEdit` (669-696), `openSubLine` and `submitSubtask` (631-651), `onDelete` and `confirmDelete` with `ConfirmDialog` (711-720). Tests in `test_pane_add.py` and `test_pane_edit_delete.py`, including `test_enter_adds_and_the_line_is_ready_for_the_next`, `test_enter_then_blur_saves_once`, `test_trash_on_a_parent_asks_with_the_count`, `test_confirm_deletes_the_parent_and_its_subtasks`. Live steps 5 to 9 passed, each checked in data.db. |
| 4  | SC4: The pane updates with no reload when the agent writes, through the event. Polling covers the case where no event arrives | VERIFIED | `ctx.onEvent(EVENT_TYPE, () => reload())` (579) and `ctx.setInterval(reload, POLL_MS)` with 6000 ms (576). `reload()` drops a reply while a write is in flight or when its rev is lower than the newest accepted rev (475-491). Tests: `test_event_reloads_the_focused_board`, `test_poll_interval`, `test_no_poll_without_a_focused_session`, `test_reload_reply_during_a_write_is_ignored`, `test_older_reload_reply_is_ignored`. Live step 3: the Mac pane showed the agent's five items with no action by Theo. See Advisory 1. |
| 5  | SC5: Theo copies the board as a plain markdown checklist. The pane is one plain ESM file with three allowed imports, SDK components, `var(--ui-*)` theme vars and no hardcoded colour | VERIFIED | `CopyButton` with `text: () => boardMarkdown(items)` (223-228). Imports are exactly `@hermes/plugin-sdk`, `react`, `react/jsx-runtime` (8-22). Grep for hex, `rgb(` and `hsl(` found none. Tests: `test_parent_with_subtasks_shows_as_a_group_and_copies_as_markdown`, `test_copy_escapes_a_leading_id_token`, `test_imports_are_on_the_allowlist`, `test_plugin_has_no_colour_literal`, `test_styles_use_theme_colour_vars_only`, `test_plugin_stays_under_the_line_ceiling` (799 of 800 lines). `hermes plugins validate` passes "desktop surface - stays inside the plugin SDK surface". Live step 10 passed. |
| 6  | D-30: One empty add line at the bottom. Enter saves and keeps the cursor in a fresh line. Escape clears. A plus on a top-level row opens a subtask line (two levels) | VERIFIED | `AddLine` last in the list body (763-771); `onAddKeyDown` (615-618); plus only for `top && !pendingRow` (313). Tests: `test_subtask_rows_have_no_plus`, `test_escape_clears_and_blur_keeps`. |
| 7  | D-31: Click text to edit in place. Enter saves, Escape cancels, a click elsewhere saves. The checkbox stays clickable in edit mode | VERIFIED | `RowText` swaps the span for an `Input` (267-285). `onMouseDown` preventDefault on the checkbox hit area (299). Tests: `test_click_text_edit_and_enter_saves`, `test_escape_cancels_the_edit`, `test_blur_saves_the_edit`, `test_check_during_an_edit_keeps_the_edit`. The review fixes add session ownership to the edit and keep this path intact. |
| 8  | D-32: Trash on row hover. No-subtask item deletes at once. An item with subtasks opens the SDK `ConfirmDialog` naming the count. No undo toast | VERIFIED | `RowButton` with `icons.Trash2` and `REVEAL_CLASS`; `DeleteConfirm` with `confirmText(count)`. No toast code. Tests as in truth 3 plus `test_one_subtask_uses_the_singular`, `test_keep_item_sends_nothing`. Live steps 8 and 9 passed. |
| 9  | D-33: A checked item stays in place, struck through and muted. Header shows "N of M open" | VERIFIED | `DONE_STYLE` line-through, `DONE_CLASS`, `headerText`. Test: `test_checked_item_stays_in_place_struck_through`. Live step 4 passed. |
| 10 | D-34: Optimistic show with `base_rev`. Stale check or uncheck retries once. Stale add or edit is not retried and keeps the typed text. A one-line notice shows for a few seconds | VERIFIED | `writeOutcome` returns `retry` only for `set_checked`, once, with the item on the new board (187-193); `postOp` loops once (505-520); `NOTICE_MS` 4000 via `ctx.setTimeout`. The review fixes strengthen "keeps the typed text": a failed save reopens the edit or stores the text in `kept` (WR-04). Tests: `test_stale_check_retries_once_on_the_new_rev`, `test_second_stale_reply_is_not_retried`, `test_stale_without_the_item_is_not_retried`, `test_stale_edit_keeps_the_typed_text`, `test_stale_subtask_add_keeps_the_text`, `test_notice_clears_when_its_timer_fires`, `test_writes_run_one_at_a_time`, and the two WR-04 tests above. |

**Score:** 10/10 truths verified (0 present, behavior-unverified)

Every behavior-dependent truth (optimistic reconcile, one write at a time, stale retry, reload never undoing a write, text kept on failure, no write to another session after a focus change) has a named passing test that runs through the real router in `tests/pane_rig.py`. None rests on symbol presence.

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `plugin/desktop/plugin.js` | Real pane, one plain ESM file | VERIFIED | 799 lines (ceiling 800, guarded by `test_plugin_stays_under_the_line_ceiling`). Substantive, wired by `register()`, data from `ctx.rest('/board')` and `/board/edit`. `node --check` passes. |
| `tests/pane_rig.py`, `tests/desktop_pane_harness.mjs`, `tests/conftest.py` | Harness and rig | VERIFIED | The harness gained `render`, `peek`, `burst`, `timeoutThrows` and `"__empty__"` steps for the review tests. The full suite runs through it. |
| `tests/test_desktop_plugin.py`, `tests/test_pane_*.py` | Pane suites | VERIFIED | All pass in the full gate (744 tests). |
| `scripts/install-desktop.ps1` | Optional `-RemotePath` with a safe-path guard | VERIFIED | Unchanged since the previous report. Tests in `tests/test_install_script.py` pass. |

## Key Link Verification

The previous report records that `verify.key-links` cannot read plans 04 to 09 (non-file values in the `from` field). The verifier checked each link by hand against the current code.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| plugin.js `postOp` | `plugin_api.py` | `ctx.rest('/board/edit', { method: 'POST', body: { session_id, ops, base_rev } })` | WIRED | plugin.js 508-511; `test_check_reaches_the_store` runs it against the real router. |
| plugin.js `Header` | `boardMarkdown` | `CopyButton text` | WIRED | 223-228. |
| add line and subtask line | `sendOp` | `submitAdd`, `submitSubtask` | WIRED | 603, 646. |
| `saveEdit`, `confirmDelete`, `onDelete`, `onCheck` | `sendOp` | op objects | WIRED | 690, 719, 712, 722. |
| `DeleteConfirm` | SDK `ConfirmDialog` | import and use | WIRED | import line 11, use line 397. |
| `Pane` | `host.onEvent` stream | `ctx.onEvent(EVENT_TYPE, ...)` | WIRED | 579. |
| `saveEdit` | focused session guard | `open.sid` against `state.sid`, asked session passed to `sendOp` | WIRED | 689, 695; CR-01 test. |
| `install-desktop.ps1` | scp | `Copy-RemoteFile` | WIRED | Unchanged. |

## Data-Flow Trace (Level 4)

| Artifact | Data variable | Source | Produces real data | Status |
|----------|---------------|--------|--------------------|--------|
| `Pane` list | `shown.board` then `viewBoard(...)` | `ctx.rest('/board?session_id=')` through `reload()` and `take()` | Yes. The rig uses the real router and store. Live: five agent items matched data.db. | FLOWING |
| `Header` count | `openCounts(items)` | same board | Yes | FLOWING |
| Copy text | `boardMarkdown(items)` | same board | Yes. Live paste equalled the board. | FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| plugin.js parses | `node --check plugin/desktop/plugin.js` | exit 0 | PASS |
| Full gate | `./scripts/check.sh` | `check: all ok`. 744 passed on 3.11 (coverage 97.49 percent, gate 80) and 744 passed on 3.14. ruff, format and pyright clean. | PASS |
| Plugin admission | `timeout 120 hermes plugins validate .../plugin` | `Validation passed.` including "desktop surface - stays inside the plugin SDK surface" | PASS |
| Debt markers | grep TBD, FIXME, XXX, TODO, HACK over the changed files | none | PASS |
| Colour literals | grep hex, `rgb(`, `hsl(` in plugin.js | none | PASS |
| Imports | grep `import` in plugin.js | only the three allowed specifiers | PASS |

## Probe Execution

No `probe-*.sh` scripts exist and no plan declares one. Step 7c: SKIPPED.

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PANE-01 | 04-01, 04-05, 04-08 | Right-side pane follows the focused session | SATISFIED | Truth 1 |
| PANE-02 | 04-05, 04-08 | Checkboxes with indented, collapsible subtasks | SATISFIED | Truth 2 |
| PANE-03 | 04-01, 04-04, 04-08 | Check and uncheck, optimistic, reconcile on revision | SATISFIED | Truths 2 and 10 |
| PANE-04 | 04-02, 04-06, 04-08 | Add inline and keep typing | SATISFIED | Truths 3 and 6 |
| PANE-05 | 04-02, 04-07, 04-08 | Edit text inline | SATISFIED | Truths 3 and 7 |
| PANE-06 | 04-06, 04-08 | Add a subtask | SATISFIED | Truths 3 and 6 |
| PANE-07 | 04-02, 04-07, 04-08 | Delete, confirm when subtasks go | SATISFIED | Truths 3 and 8 |
| PANE-08 | 04-04, 04-07, 04-08 | Live update through the event, poll fallback | SATISFIED | Truth 4 |
| PANE-11 | 04-02, 04-05, 04-08 | Copy as plain markdown checklist | SATISFIED | Truth 5 |
| PANE-12 | 04-02, 04-05, 04-08 | Empty state says the agent adds items here | SATISFIED | Truth 1 |
| PANE-13 | 04-01, 04-03, 04-08 | One plain ESM file, three imports, SDK components, theme vars, no colour | SATISFIED | Truth 5 |

Cross-check: all 11 IDs in the phase requirement list appear in the `requirements` field of at least one PLAN and in REQUIREMENTS.md. No ORPHANED requirement. PANE-09 and PANE-10 map to Phase 6 and are out of scope. Plan 04-09 also lists DEV-05, which REQUIREMENTS.md maps to Phase 3. This is not a Phase 4 gap.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | No debt markers. Empty initial state values (`useState('')`, `useState({})`, `kept: {}`) are overwritten by the board fetch or by input. | Info | No stubs. |

## Human Verification Required

None. The Mac live round (11 of 11 steps, each compared with a read-only data.db query) covers the visual and feel-of-use criteria. The review fixes change no markup, class or style, so those results still hold. The changed logic has rig tests that run through the real routes.

## Advisory

| # | Finding | Category | Note |
|---|---------|----------|------|
| 1 | The live round cannot tell the broadcast event from the 6 s poll. | other | Both paths have passing pane tests. The goal holds either way. Not a blocker. |
| 2 | `REQUIREMENTS.md` still lists PANE-01 to PANE-08 and PANE-11 to PANE-13 as `[ ]` and `Pending`. `ROADMAP.md` shows the Phase 4 line as `[ ]`. | other | Bookkeeping. The phase-complete step flips them. |
| 3 | Plans 04-04 to 04-09 write non-file values in `key_links.from`, so `verify.key-links` cannot run on them. | other | Fix the plan template later. No effect on the verdict. |
| 4 | A reload reply is dropped while any write runs, for any session. After a focus change during a write, the new board loads on the next event, poll (6 s) or failed write. Unsent add-line text is dropped on a focus change. | other | Recorded in 04-REVIEW-FIX.md as a candidate for a later fix. The 6 s poll bounds the delay. Does not break any success criterion. |
| 5 | Review items IN-01 to IN-04 stay open (`-RemotePath` allows `..` segments, the rig never fires the poll interval, two source-text tests, `Pane` is one long function). | other | Info only, per 04-REVIEW-DISPOSITION.md. |

## Gaps Summary

No gaps. Every ROADMAP success criterion and every decision D-30 to D-34 holds in the current code. The review fixes (CR-01, WR-01 to WR-05) are present in `plugin.js`, each backed by a test that runs through the real routes. The full gate, `node --check` and `hermes plugins validate` pass on the current file.

---

_Verified: 2026-11-01_
_Verifier: Claude (gsd-verifier)_
