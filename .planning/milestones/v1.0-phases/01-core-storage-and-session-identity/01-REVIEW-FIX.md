---
phase: 01-core-storage-and-session-identity
fixed_at: 2026-10-30T19:00:00Z
review_path: .planning/phases/01-core-storage-and-session-identity/01-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 1: Code Review Fix Report

**Fixed at:** 2026-10-30T19:00:00Z
**Source review:** .planning/phases/01-core-storage-and-session-identity/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

Each fix has a test that failed on the old code and passes on the new code.

**Where verification ran:** in the main checkout on branch `main`, not in a worktree. The caller named `main` as the working branch. `./scripts/check.sh` ended with `check: all ok` (ruff, format, pyright, pytest on Python 3.11 and 3.14, 210 tests, coverage 97.09 percent).

## Fixed Issues

### CR-01: A compressed branch never gets the copy of its parent board

**Files modified:** `plugin/session_tasks/lineage.py`, `tests/test_fork.py`, `tests/test_lineage.py`
**Commit:** 5414833
**Applied fix:** `_compression` now takes the chain root. When the chain root is an explicit fork child, it calls `_resolve` on that root. A branch root then gets its parent copy before the alias is stored. The review sketch used a new `_ensure_branch_copy` helper. The fix reuses `_resolve` instead, so the rule stays in one place. The hook path (`record_compaction`) is covered by the WR-01 commit. Test added: a branch compressed before its first touch, resolved through its tip, shows the parent items.
**Status:** fixed: requires human verification (logic change in session identity)

### WR-01: A compressed delegate session writes to a board that its delegator does not use

**Files modified:** `plugin/session_tasks/lineage.py`, `tests/test_fork.py`, `tests/test_lineage.py`
**Commit:** 03546aa
**Applied fix:** `_root_of_old` now returns `_resolve(old_id).root_id`, as the review proposed. `record_compaction` catches a lineage loop and falls back to the old id. A compacted delegate now aliases to the delegator root. A compacted branch gets its parent copy before the alias is stored. This also closes the hook path of CR-01. Tests added: delegate compaction through the hook, a compressed delegate tip through `resolve`, a branch compaction through the hook, and a looping delegate chain in the hook.
**Status:** fixed: requires human verification (logic change in session identity)

Side effect to know: `record_compaction` now runs the same resolve as `resolve`. It can write an alias for an older session in the chain when that chain root already has a board. This matches what `resolve` already does for the same id.

### WR-02: `BoardStore` accepts a blank or whitespace session key

**Files modified:** `plugin/session_tasks/model.py`, `plugin/session_tasks/lineage.py`, `plugin/session_tasks/store.py`, `tests/test_store_items.py`
**Commit:** 0550837
**Applied fix:** Added `check_session_id` to `model.py`. `lineage.py` calls it in place of its private `_check_id`. `BoardStore.get_board` and `BoardStore.apply` call it first, before any file opens, also when `ops` is empty. Test added for `""`, whitespace, a tab and newline, `None` and an integer. The test also checks that no board or alias row exists afterward. Public signatures are unchanged.

### WR-03: The real-home guard cannot see a write to an existing file

**Files modified:** `tests/home_guard.py`, `tests/test_layout.py`
**Commit:** efeec9a
**Applied fix:** `snapshot` now maps each path to a stamp: `(size, mtime_ns)` for a file and a fixed stamp for a directory. `new_entries` returns paths that are new or whose stamp changed. Sidecar names (`-wal`, `-shm`, `-journal`) stay skipped. The session message now reads `real Hermes home changed:`. Tests added: a rewrite with a new size, a same-size rewrite found by its changed time, and a whole-session case with an existing `data.db`.

Known limit: once the plugin runs on this machine, a live gateway can write the real `data.db` while the test suite runs. The guard then fails the run. This is the cost of the check the review asked for.

---

_Fixed: 2026-10-30T19:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
