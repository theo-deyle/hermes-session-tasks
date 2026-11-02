---
phase: 04-pane
verified: 2026-11-02T04:00:00Z
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
covered_digest: "v4:sha256:fe0b728ea75dfd2e363b0241301b8368bde9f8e20dd34fd622183bca6a08f569"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 4: Pane Verification Report

**Phase Goal:** Theo sees and edits the focused session's board in a right-side pane. The pane updates live when the agent writes.
**Verified:** 2026-11-02
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

The pane exists, holds real logic, and works against the real routes. The verifier read all 789 lines of `plugin/desktop/plugin.js` and did not rely on SUMMARY.md. The file the Mac ran in the live round is the file now in the repo: SHA-256 prefix `04adc10fda44b3cb` matches the value in 04-08-SUMMARY.md, and no file under `plugin`, `scripts` or `tests` changed after commit `2f3b6ca`.

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | SC1: A right-side pane shows the focused session's board, switches on focus change, and an empty board says the agent adds items here | VERIFIED | `register()` sets `placement: 'right'`, `dock`, `width: '320px'` (plugin.js 774-780). `Pane` reads `useValue(host.state.focusedStoredSessionId)` (415), reloads and resets local state in the `[sid]` effect (555-568). Empty state text "The agent adds items here." with hint "Add one below." (34-35, 736-737). Tests: `test_focus_change_shows_the_new_board`, `test_collapse_state_resets_on_focus_change`, `test_empty_board_shows_the_empty_state`, `test_no_focused_chat_shows_open_a_chat`, `test_plugin_name_and_registration`. Live steps 2 and 3 passed on the Mac. |
| 2  | SC2: Items show as checkboxes with indented, collapsible subtasks. A check shows at once and reconciles on the returned revision | VERIFIED | `buildTree`, `ItemRow` (SDK `Checkbox`), `Chevron`, `subtaskCountText`; `viewBoard` applies pending ops over the last server board (optimistic); `postOp` sends `base_rev` and `take()` adopts the returned rev. Tests: `test_check_reaches_the_store` (real router, store holds item 1 checked by `user` at rev 2), `test_check_shows_before_the_reply`, `test_collapse_hides_subtasks_and_keeps_the_count`, `test_expand_shows_the_subtasks_again`, `test_parent_and_subtasks_check_independently`. Live step 3 and 4 passed, step 4 checked in data.db. |
| 3  | SC3: Theo adds an item inline and keeps typing, edits text inline, adds a subtask, deletes an item and the pane confirms when subtasks go too | VERIFIED | Add line with Enter and fresh empty line (`submitAdd`, 584-599). Click-to-edit with Enter, Escape and blur (`startEdit`, `saveEdit`, `editHandlers`). Plus button opens subtask line (`openSubLine`, `submitSubtask`). Trash deletes at once, or opens `ConfirmDialog` with the count when children exist (`onDelete`, `confirmText`). Tests in `test_pane_add.py` and `test_pane_edit_delete.py`, including `test_enter_adds_and_the_line_is_ready_for_the_next`, `test_enter_then_blur_saves_once`, `test_trash_on_a_parent_asks_with_the_count`, `test_confirm_deletes_the_parent_and_its_subtasks`. Live steps 5 to 9 passed, each checked in data.db (items 9 and 10 by user, item 5 text change, item 12 parent 4, items 1 to 3 gone at rev 16). |
| 4  | SC4: The pane updates with no reload when the agent writes, through the event. Polling covers the case where no event arrives | VERIFIED | `ctx.onEvent(EVENT_TYPE, () => reload())` (570) and `ctx.setInterval(reload, POLL_MS)` with 6000 ms (567). `reload()` drops a reply while a write is in flight or when its rev is older than the newest accepted rev, so a poll never undoes a write. Tests: `test_event_reloads_the_focused_board`, `test_poll_interval`, `test_no_poll_without_a_focused_session`, `test_reload_reply_during_a_write_is_ignored`, `test_older_reload_reply_is_ignored`. Live step 3: Mac pane showed the agent's five items with no action by Theo. See the note under Advisory about event versus poll in the live round. |
| 5  | SC5: Theo copies the board as a plain markdown checklist. The pane is one plain ESM file with three allowed imports, SDK components, `var(--ui-*)` theme vars and no hardcoded colour | VERIFIED | `CopyButton` in `Header` with `text: () => boardMarkdown(items)`: `- [ ]` and `- [x]` lines, two-space subtask indent, no ids, a leading backslash on text that reads as an id token. Imports are exactly `@hermes/plugin-sdk`, `react`, `react/jsx-runtime` (lines 8-22). Grep for hex, `rgb(` and `hsl(` in plugin.js found none. Tests: `test_parent_with_subtasks_shows_as_a_group_and_copies_as_markdown`, `test_copy_escapes_a_leading_id_token`, `test_imports_are_on_the_allowlist`, `test_plugin_has_no_colour_literal`, `test_class_names_carry_no_palette_colour`, `test_styles_use_theme_colour_vars_only`, `test_every_plugin_class_ships_in_desktop`, `test_plugin_stays_under_the_line_ceiling`. Live step 10: the saved file equals the board line for line. `hermes plugins validate` passes "desktop surface - stays inside the plugin SDK surface". |
| 6  | D-30: One empty add line at the bottom. Enter saves and keeps the cursor in a fresh line. Escape clears. A plus on a top-level row opens a subtask line (two levels) | VERIFIED | `AddLine` rendered last in the list body (753-761); `onAddKeyDown`; plus only for `top && !pendingRow` (314-320); `test_subtask_rows_have_no_plus`, `test_escape_clears_and_blur_keeps`. |
| 7  | D-31: Click text to edit in place. Enter saves, Escape cancels, a click elsewhere saves. The checkbox stays clickable in edit mode | VERIFIED | `RowText` swaps the span for an `Input`; `onMouseDown` preventDefault on the checkbox hit area keeps the edit open (299-300). Tests: `test_click_text_edit_and_enter_saves`, `test_escape_cancels_the_edit`, `test_blur_saves_the_edit`, `test_check_during_an_edit_keeps_the_edit`. |
| 8  | D-32: Trash on row hover. No-subtask item deletes at once. An item with subtasks opens the SDK `ConfirmDialog` naming the count. No undo toast | VERIFIED | `RowButton` with `icons.Trash2` and `REVEAL_CLASS`; `DeleteConfirm` uses `ConfirmDialog` with `confirmText(count)`; no toast code exists. Tests listed in truth 3 plus `test_one_subtask_uses_the_singular`, `test_keep_item_sends_nothing`. Live steps 8 and 9 passed. |
| 9  | D-33: A checked item stays in place, struck through and muted. Header shows "N of M open" | VERIFIED | `DONE_STYLE` line-through, `DONE_CLASS` secondary text colour; `headerText` gives `${open} of ${total} open`. Tests: `test_checked_item_stays_in_place_struck_through`. Live step 4: strikethrough, line stayed. |
| 10 | D-34: Optimistic show with `base_rev`. Stale check or uncheck retries once. Stale add or edit is not retried and keeps the typed text. A one-line notice shows for a few seconds | VERIFIED | `writeOutcome` returns `retry` only for `set_checked`, not yet retried, with the item still on the new board; `postOp` loops once; `NOTICE_MS` 4000 via `ctx.setTimeout`. Tests: `test_stale_check_retries_once_on_the_new_rev`, `test_second_stale_reply_is_not_retried`, `test_stale_without_the_item_is_not_retried`, `test_stale_edit_keeps_the_typed_text`, `test_stale_subtask_add_keeps_the_text`, `test_notice_clears_when_its_timer_fires`, `test_writes_run_one_at_a_time`. |

**Score:** 10/10 truths verified (0 present, behavior-unverified)

Behavior-dependent truths (optimistic reconcile, one write at a time, stale retry, reload never undoing a write, edit and add text kept on failure) each have a named passing test that exercises the transition against the real router through `tests/rest_relay.py`. None rests on symbol presence alone.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `plugin/desktop/plugin.js` | Real pane, one plain ESM file | VERIFIED | 789 lines (ceiling 800, guarded by `test_plugin_stays_under_the_line_ceiling`). Substantive, wired by `register()`, data flows from `ctx.rest('/board')` and `/board/edit` (Level 4 below). `node --check` passes. |
| `tests/pane_rig.py`, `tests/desktop_pane_harness.mjs`, `tests/conftest.py` | Harness and rig | VERIFIED | `verify.artifacts` passed for plans 01 to 03 (5/5, 4/4, 1/1). |
| `tests/test_desktop_plugin.py`, `tests/test_pane_*.py` | Pane suites | VERIFIED | 142 test functions across the pane and install suites; all pass. |
| `scripts/install-desktop.ps1` | Optional `-RemotePath` with a safe-path guard | VERIFIED | Parameter at line 38 with the old literal as default; `Test-RemotePath` guard refuses an unsafe path before any scp call (190-191). Tests in `tests/test_install_script.py`. |

`verify.artifacts` passed on every plan (9 of 9 plans, all artifacts).

### Key Link Verification

`verify.key-links` returned failures for plans 04 to 09. Every failure has the same cause: the plan wrote a function name or an endpoint in the `from` field, which the tool reads as a file path ("Source file not found (from: must be a relative file path...)"). These are plan-authoring format faults, not code faults. The verifier checked each link by hand:

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| plugin.js `postOp` | `plugin_api.py` | `ctx.rest('/board/edit', { method: 'POST', body: { session_id, ops, base_rev } })` | WIRED | plugin.js 512-515; exercised end to end by `test_check_reaches_the_store` against the real router. |
| plugin.js `Header` | `boardMarkdown` | `CopyButton text` | WIRED | plugin.js 224-229. |
| plugin.js add line and subtask line | `sendOp` | `submitAdd`, `submitSubtask` | WIRED | plugin.js 591, 635. |
| plugin.js `saveEdit`, `confirmDelete`, `onDelete`, `onCheck` | `sendOp` | op objects | WIRED | plugin.js 674, 694, 701, 705. |
| plugin.js `DeleteConfirm` | SDK `ConfirmDialog` | import and use | WIRED | import line 11, use line 398. |
| plugin.js `Pane` | `host.onEvent` stream | `ctx.onEvent(EVENT_TYPE, ...)` | WIRED | plugin.js 570. |
| Mac pane | devpc backend | live round | WIRED | Live steps 3 to 10, each matched in data.db. |
| `install-desktop.ps1` | scp | `Copy-RemoteFile "${DevpcHost}:$RemotePath"` | WIRED | script lines 151-167. |

### Data-Flow Trace (Level 4)

| Artifact | Data variable | Source | Produces real data | Status |
|----------|---------------|--------|--------------------|--------|
| `Pane` list | `server.board` then `viewBoard(...)` | `ctx.rest('/board?session_id=')` through `reload()` and `take()` | Yes. Harness uses the real router and store. Live: five agent items shown, matched data.db rev 1. | FLOWING |
| `Header` count | `openCounts(items)` | same board | Yes | FLOWING |
| Copy text | `boardMarkdown(items)` | same board | Yes. Live paste equalled the board. | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| plugin.js parses | `node --check plugin/desktop/plugin.js` | exit 0 | PASS |
| Full gate | `./scripts/check.sh` | `check: all ok`; 734 passed on 3.11 and 734 on 3.14; coverage 97.49 percent (gate 80); ruff, format and pyright clean | PASS |
| Plugin admission | `timeout 120 hermes plugins validate .../plugin` | `Validation passed.` including "desktop surface - stays inside the plugin SDK surface" | PASS |
| File proven live is the file in the repo | `sha256sum plugin/desktop/plugin.js` and `git diff --stat 2f3b6ca HEAD -- plugin scripts tests` | prefix `04adc10fda44b3cb`, equal to 04-08-SUMMARY.md; empty diff | PASS |

### Probe Execution

No `probe-*.sh` scripts exist in this repo and no plan declares one. Step 7c: SKIPPED (no probes).

### Requirements Coverage

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

Cross-check: all 11 IDs in the phase requirement list appear in at least one PLAN `requirements` field and in REQUIREMENTS.md. No ORPHANED requirement. PANE-09 and PANE-10 map to Phase 6 in REQUIREMENTS.md and are out of scope here. Plan 04-09 lists DEV-05, which REQUIREMENTS.md and ROADMAP.md map to Phase 3. Plan 04-09 only unblocks the Phase 3 Windows steps (03-10 to 03-12), so DEV-05 stays pending under Phase 3. This is not a Phase 4 gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | Grep for TBD, FIXME, XXX, TODO, HACK in plugin.js, install script and the pane tests found only the `placeholder` prop names | Info | No debt markers, no stubs. Every grep hit for empty initial state (`useState('')`, `useState({})`) is overwritten by the board fetch or by input. |

### Human Verification Required

None. The Mac live round in 04-08-SUMMARY.md (11 of 11 steps, each compared with a read-only data.db query) covers the visual and feel-of-use criteria. This includes the two layout defects Theo found at step 1, which were fixed in the same turn with a failing test first (`8828317`, `2f3b6ca`).

### Advisory

| # | Finding | Category | Note |
|---|---------|----------|------|
| 1 | The live round shows the agent's write reached the Mac pane with no action by Theo, but it cannot tell the broadcast event from the 6 s poll. | other | The pane side of both paths has passing tests (`test_event_reloads_the_focused_board`, `test_poll_interval`). The goal holds either way, because the poll covers a missing event. If Theo wants proof that the event reaches a remote Mac, a timed check under 6 s settles it. This is not a Phase 4 blocker. |
| 2 | `REQUIREMENTS.md` still lists PANE-01 to PANE-08 and PANE-11 to PANE-13 as `[ ]` and `Pending`. `ROADMAP.md` shows the Phase 4 line as `[ ]`. | other | Bookkeeping only. The phase-complete step should flip them after this report. |
| 3 | Plans 04-04 to 04-09 write non-file values in `key_links.from`, so `verify.key-links` cannot run on them. | other | Fix the plan template in a later phase. No effect on this verdict. |

### Gaps Summary

No gaps. Every ROADMAP success criterion and every decision D-30 to D-34 holds in the code, in the tests that exercise the real routes, and in the Mac live round. The full gate, `node --check` and `hermes plugins validate` all pass on the file that Theo tested.

---

_Verified: 2026-11-02_
_Verifier: Claude (gsd-verifier)_
