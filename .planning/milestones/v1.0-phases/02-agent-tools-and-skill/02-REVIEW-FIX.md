---
phase: 02-agent-tools-and-skill
fixed_at: 2026-10-31T12:00:00Z
review_path: .planning/phases/02-agent-tools-and-skill/02-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-10-31T12:00:00Z
**Source review:** .planning/phases/02-agent-tools-and-skill/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

Each fix has a test commit that failed on the old code, then a fix commit that passes. IN-01 to IN-04 are out of scope and stay open.

**Where verification ran:** in the main checkout on branch `main`, not in a worktree. `./scripts/check.sh` ended with `check: all ok` (ruff, format, pyright, pytest on Python 3.11 and 3.14, 444 tests). `env -u HERMES_HOME timeout 120 hermes plugins validate plugin/` ended with `Validation passed.`

## Fixed Issues

### CR-01: Reword guard is bypassed after the agent checks an item Theo wrote

**Files modified:** `plugin/session_tasks/guard.py`, `plugin/session_tasks/hooks.py`, `plugin/session_tasks/rows.py`, `plugin/session_tasks/store.py`, `tests/test_guard.py`, `tests/test_store_items.py`
**Commits:** test 6b34185, fix dfc941d
**Applied fix:** `updated_by` stays the last writer, and `_touch` is unchanged, so the Phase 4 agent-changed dot keeps its meaning. The review sketch made the author sticky in `_touch`. The fix reads the changes journal instead. New `BoardStore.user_touched_ids(root_id)` returns the ids with a journal row by the user actor. `hooks._check` passes that set to `guard.guarded_reasons`. The guard blocks a reword when the item's `updated_by` is user or its id is in the set. `guard.py` stays pure. The board_edit handler path is unchanged. Tests added: the hook regression (Theo adds, the agent checks, the agent rewords with no `confirmed` is blocked, and with `confirmed` passes), a guard test for an agent-owned item that Theo touched before, and three store tests.
**Status:** fixed: requires human verification (logic change in the guard rule)

Known limit: the journal keeps the newest 100 rows per board (`JOURNAL_KEEP`). Theo's touch on an item drops out of the set after more than 100 later changes, if the agent also changed that item since. The `SKILL.md` sentence "Any change by Theo makes the item his" is now true, so no text changed.

### WR-01: Very large integers escape the parser as raw exceptions

**Files modified:** `plugin/session_tasks/edit_args.py`, `tests/test_edit_args.py`
**Commits:** test cf0a0a6, fix 52459ad
**Applied fix:** `_whole` returns None for any value below 0 or above `MAX_WHOLE` (2**63 - 1). A digit string longer than 19 digits after leading zeros is rejected before `int()` runs, so the 4300 digit limit cannot raise. The existing "must be a whole number" error then fires with the op index, and `base_rev` gets its existing `BASE_REV_BAD` message. Tests added: `10**30`, a 5000 digit string and `2**63` for `item_id`, `parent_id`, `parent_ref` and `base_rev` (also on an add-only call), a negative id, the largest valid value, and a zero-padded digit string that still parses.

### WR-02: Success summary counts submitted ops, not changes

**Files modified:** `plugin/session_tasks/model.py`, `plugin/session_tasks/store.py`, `plugin/session_tasks/results.py`, `plugin/session_tasks/board_tools.py`, `tests/test_results.py`, `tests/test_store_subtasks.py`
**Commits:** test a9913ba, fix d080e0a
**Applied fix:** `Applied` has a new field `entries`, one (op, item id) pair per journal row of the batch, default empty. `summary_line(rev, entries)` counts distinct items per kind, and the op based `Counter` is gone. `applied_result(applied)` no longer takes `ops`. A repeated no-op check now reads "checked 1 item", and a cascade remove of a parent with one subtask reads "removed 2 items". Tests added: the repeated check through the handler, the corrected cascade assertion, an item counted once per kind, and the entries of a cascade remove in the store.
**Status:** fixed: requires human verification (the summary wording now follows journal rows)

---

_Fixed: 2026-10-31T12:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
