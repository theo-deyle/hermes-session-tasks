---
phase: 04-pane
plan: 07
subsystem: desktop-pane
tags: [hermes-desktop, inline-edit, delete, confirm-dialog, pytest]
status: complete

requires:
  - phase: 04-pane
    provides: plan 04-06 add lines and REVEAL_CLASS, plan 04-04 sendOp and the stale notice, plan 04-02 harness steps confirm and cancel, plan 04-03 class guards
provides:
  - click an item's text to edit it in place (Enter saves, Escape cancels, blur saves, the checkbox stays live)
  - the reload and focus rules that keep an open edit, the add text and the collapse state
  - a trash button on every saved row, and the SDK confirm dialog when subtasks go with the item
affects: [04-08]

requirements-completed: [PANE-05, PANE-07, PANE-08]

actuals:
  tokens: 5100
  tasks: 3
  commits: 6
plan_head_before: 9e8c9d54d1aa044da177706b98e82e97c546fa5a
plan_head_after: b9fc87c29ef8e3c87f9a74dbb73b01bf507decd2
commits: 6

tech-stack:
  added: []
  patterns:
    - ItemBlock and ItemRow take one `actions` object, so a new row action adds no prop to either
    - RowButton is one ghost icon button for the plus and the trash; both use ROW_BUTTON_CLASS
    - the edit Input reuses AddLine, so the add line, the subtask line and the edit share one Input setup
    - the open edit lives in state and in a ref copy; handlers read the ref

key-files:
  created:
    - tests/test_pane_edit_delete.py
  modified:
    - plugin/desktop/plugin.js

key-decisions:
  - "saveEdit reads the edit from the ref and clears it first, so an Enter followed by a blur sends one write."
  - "A stale or failed set_text puts the typed text back only when no other edit is open and the last accepted board still holds the item."
  - "A new server board without the item under edit closes the edit and shows the stale notice; a board that holds the item changes nothing."
  - "The SDK ConfirmDialog has no Cancel focus option, so Enter confirms, as UI-SPEC Delete rule 4 says."

duration: 45 min
completed: 2026-11-01
---

# Phase 4 Plan 07: Edit and delete Summary

Theo clicks an item's text to edit it in place (Enter or a click elsewhere saves, Escape cancels) and deletes with a trash icon that confirms through the SDK dialog only when subtasks go too; a live update never resets his typing.

## Accomplishments

- `applyOp` handles `set_text` and `remove` (a remove drops the item and its subtasks), so both show at once through `viewBoard`.
- `RowText` shows the item text as a clickable span or as one `Input` (`maxLength` 500, `size` `sm`, `autoFocus`, caret to the end). `startEdit` saves an open edit first, so one row is in edit mode at most. A done item can be edited.
- `saveEdit` sends `set_text` with the pane's newest `base_rev`. Blank or unchanged text sends nothing and never deletes. The checkbox hit area prevents the mouse-down default, so a check during an edit keeps the Input.
- A stale or failed edit is not retried: the pane shows the returned board and reopens the Input with the typed text.
- A new server board that lacks the item under edit closes the edit and shows the stale notice. A focus change clears the edit, the add text, the subtask lines and the delete question.
- A `Delete item` trash button (Tip and `aria-label`) sits on every saved row with `REVEAL_CLASS` and `shrink-0`. An item with no subtasks is removed at once. An item with subtasks opens `DeleteConfirm` (SDK `ConfirmDialog`): `Delete this item?`, `Delete this item and its {n} subtasks?` (`1 subtask` for one), `Delete item and subtasks`, `Keep item`, destructive. `Keep item` sends nothing.
- A parent remove after a subtask changed is answered stale: the pane shows the returned board and removes nothing (T-04-21).

## Task Commits

| Task | Step | Commit |
|------|------|--------|
| 1 | red: failing end to end edit test | 69eb646 |
| 1 | green: inline text edit | 1e47b59 |
| 2 | red: 13 edit rule, stale, reload and focus tests (3 failed) | 004cfce |
| 2 | green: edit rules and typing protection | cc566ad |
| 3 | red: 8 delete and confirm tests (8 failed) | a762a05 |
| 3 | green: trash icon and confirm dialog | b9fc87c |

Red lines: Task 1 gave `1 failed` (no click handler on the text). Task 2 gave `3 failed, 11 passed`: the checkbox guard, the edit closing when its item is gone, and the focus reset. The other ten rules already held because Task 1 built `saveEdit` with the blank, unchanged and ref rules. Task 3 gave `8 failed, 14 passed` (no trash button).

## Verification

- `uv run pytest tests/test_pane_edit_delete.py tests/test_pane_add.py tests/test_pane_view.py tests/test_pane_writes.py tests/test_pane_harness.py tests/test_desktop_plugin.py -q -rs`: 120 passed, 0 skipped. tests/test_pane_edit_delete.py holds 22 tests.
- ruff check, ruff format --check and pyright on tests/test_pane_edit_delete.py: clean. `node --check plugin/desktop/plugin.js`: clean.
- Acceptance greps: `set_text` 3, `setSelectionRange` 1, `preventDefault()` 1, `Delete item and subtasks` 1, `Keep item` 1, `ConfirmDialog` 2 lines, `function confirmText` 1. `-k "enter_then_blur_saves_once or stale_edit_keeps"`: 2 passed.
- The oldest 04-07 commit is `test(04-07)`.
- plugin.js is 786 lines (ceiling 800; it was 680). Em dash and en dash scan over plugin.js and tests/test_pane_edit_delete.py: none found.
- `./scripts/check.sh` last lines:
  - `check: python 3.11 ok` (732 passed, coverage 97.49 percent, gate 80)
  - `check: python 3.14 ok` (732 passed)
  - `check: all ok`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Row code refactored to stay under the 800 line ceiling**
- **Found during:** Task 3
- **Issue:** After the edit code plugin.js was 762 lines, and the delete code took it to 807 with the ceiling at 800.
- **Fix:** `ItemRow` and `ItemBlock` take one `actions` object (done in Task 1). `RowButton` replaces `PlusButton`. The subtask line passes its props from `subtaskHandlers` by spread. The export list sits on four lines.
- **Files modified:** plugin/desktop/plugin.js
- **Commit:** 1e47b59, b9fc87c

**2. [Rule 2 - Missing critical] Delete question cleared on a focus change**
- **Found during:** Task 3
- **Issue:** The plan clears the edit, add text and subtask lines on a focus change but not the open delete dialog. A dialog left open would delete an item of the other session.
- **Fix:** The `[sid]` effect also calls `setConfirm(null)`. The last accepted board ref also resets when the focused session changes.
- **Files modified:** plugin/desktop/plugin.js
- **Commit:** b9fc87c, 1e47b59

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** No scope change. The `PlusButton` component is now `RowButton`; no test named it.

## Known Stubs

None.

## Threat Flags

None. T-04-21, T-04-22 and T-04-23 are mitigated by the tests named in the plan.

## Next Phase Readiness

Ready for 04-08 (look check on the Mac). The 320px overflow check there covers the look; this plan covers the classes.

## Self-Check: PASSED

- tests/test_pane_edit_delete.py and plugin/desktop/plugin.js exist.
- Commits 69eb646, 1e47b59, 004cfce, cc566ad, a762a05 and b9fc87c are on main.
