---
phase: 04-pane
fixed_at: 2026-11-01T00:00:00Z
review_path: .planning/phases/04-pane/04-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-11-01
**Source review:** `.planning/phases/04-pane/04-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (CR-01, WR-01, WR-02, WR-03, WR-04, WR-05)
- Fixed: 6
- Skipped: 0

Each fix has a test commit that failed on the old code through the real rig (`tests/pane_rig.py` against the real routes), then a fix commit that passes. IN-01 to IN-04 are out of scope and stay open.

**Where verification ran:** in the main checkout on branch `main`, not in a worktree. `./scripts/check.sh` ended with `check: all ok`:
- `check: python 3.11 ok` (ruff, format, pyright, 744 tests, coverage 97 percent, above the 80 percent gate)
- `check: python 3.14 ok` (ruff, format, pyright, 744 tests)
- `node --check plugin/desktop/plugin.js` passed.
- `plugin/desktop/plugin.js` is 799 lines (ceiling 800, was 789).

## Rig changes (in the first test commit, a6a588f)

`tests/desktop_pane_harness.mjs` gained these, all documented in its header:
- step `{"render": true}`: one render with effects and no waiting (for use inside `duringWrite`).
- step `{"peek": true}`: one render with no effects, the render phase without the commit.
- step `{"burst": [...]}`: inner steps with no render and no waiting between them.
- config `timeoutThrows`: every `ctx.setTimeout` throws, as after a plugin dispose.
- override value `"__empty__"`: the path resolves with nothing.

## Fixed Issues

### CR-01: A failed or stale text edit can reopen on another session's item and overwrite it

**Files modified:** `plugin/desktop/plugin.js`, `tests/desktop_pane_harness.mjs`, `tests/test_pane_edit_delete.py`
**Commits:** test a6a588f, fix c1077fc
**Applied fix:** The edit record carries `sid`. `saveEdit` sends nothing when `open.sid` differs from the focused session, sends the write with `open.sid` as the asked session (`sendOp` takes an optional third argument), and reopens the edit only when the focused session is the edit's own and its board holds the item. The test runs a blur between the render of a focus change and its effect, with both boards holding item 1. The old code sent a `set_text` to `s2` with `base_rev` 0.
**Status:** fixed: requires human verification (logic change in the edit and write path)

Note: the review's chain needs the board of the new session in the ref when the old write settles. The pane drops a reload reply while any write runs, so that state is hard to reach by timing alone. The test reaches it through the stale reply of the wrongly addressed write itself, which sets the board. The guard stops the chain at its first step.

### WR-01: One thrown error in the write queue stops every later write

**Files modified:** `plugin/desktop/plugin.js`, `tests/test_pane_writes.py`
**Commits:** test 6bed7b8, fix 65df9fd
**Applied fix:** The queue chain ends in `.catch(() => undefined)`. In `runWrite`, the code after the request runs in a `try` and `onOutcome` runs in its `finally`, so the busy flags always reset even when `showNotice` throws. `reload()` now runs before `showNotice` so a throwing notice cannot skip it. The test makes `ctx.setTimeout` throw, fails the first add, and checks that the second add still posts. The old code ended the run with the unhandled rejection.

### WR-02: Focus change leaves busy flags and the load notice behind

**Files modified:** `plugin/desktop/plugin.js`, `tests/test_pane_writes.py`
**Commits:** test 9ba239c, fix e9a7e3e (refactor 417a992 freed ten lines first, no behaviour change)
**Applied fix:** A `visit` counter in the ref goes up on every focus change in the `[sid]` effect. The add and subtask callbacks capture it and return when it changed, so an old write never touches a line of the new session, even after a return to the same session (A, B, A). The effect also resets `addBusy`, `subBusy` and `loadFailed`. This replaces the review's `sid:parentId` key option. Three tests: the new session's add line works while the old write runs, the old subtask write does not clear a new line of the same parent id, and the load notice does not follow a focus change.
**Status:** fixed: requires human verification (state handling across focus changes)

### WR-03: The pane changes a ref during render and drops the session rev on every return

**Files modified:** `plugin/desktop/plugin.js`, `tests/test_pane_writes.py`
**Commits:** test c5e12df, fix 7bf8911
**Applied fix:** The render no longer writes the ref. The `[sid]` effect sets `sid` and clears `board`. No code deletes a rev any more, so a return to a session sends its next write with the right `base_rev`, and the `revs["null"]` key is gone. `reload` already drops any lower rev. Two tests: a render that never commits does not move the write session, and a return to a session keeps its rev for the next add.
**Status:** fixed: requires human verification (ref lifecycle change)

### WR-04: A stale or failed text save can silently drop the typed text

**Files modified:** `plugin/desktop/plugin.js`, `tests/test_pane_edit_delete.py`
**Commits:** test 820af8e, fix ccbe507
**Applied fix:** A failed or stale save reopens the edit when it can (same session, item on the board, no other edit open). Otherwise it stores the text in `kept`, keyed by `sid:itemId`. `startEdit` starts the next edit of that item with the kept text and removes the entry. Two tests: another edit opened meanwhile, and the focus moved meanwhile.

### WR-05: `isMismatch` crashes the render when `/meta` returns nothing

**Files modified:** `plugin/desktop/plugin.js`, `tests/test_pane_writes.py`
**Commits:** test 6c2e0c7, fix 4fc2877
**Applied fix:** The guard is `!meta || meta.ok !== true`. The test returns an empty reply for `/meta`. The old code threw a TypeError in the render.

## Seen and not fixed

- A reload reply is dropped while any write runs, for any session. After a focus change during a write, the new session's board loads only on the next event, poll or failed write. Not in the review. It is a candidate for a later fix.
- Unsent text in the add line is still dropped on a focus change. The review lists it, but its Fix section does not ask for a restore, and `test_focus_change_drops_edit_and_typing` pins the drop.

---

_Fixed: 2026-11-01_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
