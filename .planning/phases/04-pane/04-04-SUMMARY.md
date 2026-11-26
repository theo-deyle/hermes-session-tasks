---
phase: 04-pane
plan: 04
subsystem: desktop-pane
tags: [hermes-desktop, write-path, stale, notice, pytest]
status: complete

requires:
  - phase: 04-pane
    provides: plan 04-01 pane first slice, plan 04-02 harness steps and rig helpers, plan 04-03 class guards
provides:
  - one pane write path (sendOp) with optimistic display, one write at a time and base_rev on every write
  - the D-34 stale rule: take the returned board, retry a check once, never retry another op
  - the notice line with its four fixed strings, priority order and 4000 ms timers
  - reload guards that stop a reload reply from undoing a write or rolling the board back
affects: [04-05, 04-06, 04-07, 04-08]

actuals:
  tokens: 14000
  tasks: 3
  commits: 6
plan_head_before: 604041a74d196aa1e66c6ee1ca803fffa08b0474
plan_head_after: 1ef28e8796c95e65858527f09b49d3aa2a256c46
commits: 6

tech-stack:
  added: []
  patterns:
    - every write goes through sendOp(op, onOutcome); later plans add ops, never a second write path
    - the pane keeps the newest accepted rev per session in a ref map (revs), read at send time
    - the notice state holds one kind at a time; noticeText applies the priority order

key-files:
  created:
    - tests/test_pane_writes.py
  modified:
    - plugin/desktop/plugin.js

key-decisions:
  - "The newest accepted rev lives in a per-session map (current.revs), not one ref value. A write queued for a session that lost focus still sends that session's own base_rev."
  - "Focus change deletes the new session's entry in revs, so the first load of a session always passes the lower-rev guard."
  - "A stale reply without a board object counts as failed, so the pane never takes a board it does not have."

requirements-completed: [PANE-03, PANE-08]

duration: 20 min
completed: 2026-11-02
---

# Phase 4 Plan 04: Pane write path Summary

The pane write path: a check shows at once, writes run one at a time on the newest accepted rev, a stale check takes the returned board and retries once, and a four-string notice line reports stale, failed write and failed load.

## Accomplishments

- `sendOp(op, onOutcome)` adds a pending entry at once, chains the write on a promise queue and calls `onOutcome` once with `'ok'`, `'stale'` or `'failed'`. `onCheck` uses it.
- `writeOutcome(reply, op, retried)` returns `'retry'` only for a stale `set_checked` reply whose board still holds the item and only when `retried` is false. Any other stale reply returns `'stale'`.
- `viewBoard(board, pendingOps)` puts every queued or in-flight op on top of the newest board, so a pending check stays shown until its own reply.
- `reload()` drops a reply while a write is in flight and when its rev is lower than the newest accepted rev.
- `noticeText` returns the version mismatch, write failed, stale and load failed lines in that order, else null. `Notice` renders one truncating 12px line under the header, and nothing when empty.
- A failed write (thrown error or any non-stale `ok: false` reply) shows the write failed notice and reloads the board. A failed board load shows the load failed notice until the next taken reload.
- Stale and write failed notices clear with `ctx.setTimeout(clear, NOTICE_MS)`; the clear callback checks the notice `seq`.

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 (red) | failing end to end test for a stale check | 73f1d66 |
| 1 (green) | pane write path with the stale retry and the notice line | c3b1019 |
| 2 (red) | optimistic, retry limit, queue and reload guard tests | 98f26c3 |
| 2 (green) | one write at a time and reload guards in the pane | f6dc19e |
| 3 (red) | failure path and notice priority tests | 7b23cd3 |
| 3 (green) | failure notices with priority and timers in the pane | 1ef28e8 |

Red lines: Task 1 gave `1 failed` (one POST, not two). Task 2 gave `2 failed, 5 passed`: the two reload guard tests fail; the optimistic, retry limit, missing item and queue tests already passed because the Task 1 write path holds the pending entry, the single retry and the queue. Task 3 gave `4 failed, 10 passed`: the write failed, invalid reply, load failed and replace-stale tests fail.

## Verification

- `uv run pytest tests/test_pane_writes.py tests/test_desktop_plugin.py tests/test_pane_harness.py -q -rs`: 69 passed, 0 skipped (14 in tests/test_pane_writes.py).
- ruff check, ruff format --check and pyright on tests/test_pane_writes.py: clean. `node --check plugin/desktop/plugin.js`: clean.
- Acceptance greps: `Board changed, showing the latest` 1, `const NOTICE_MS = 4000` 1, `function writeOutcome` 1, `function viewBoard` 1, `inFlight` 4, `Could not save that change. Try again.` 1, `Could not load the board. Retrying.` 1, `function noticeText` 1.
- The oldest 04-04 commit is `test(04-04)`.
- plugin.js is 317 lines (ceiling 800).
- Em dash and en dash scan over plugin.js and tests/test_pane_writes.py: none found.
- `./scripts/check.sh` last lines:
  - `check: python 3.11 ok` (681 passed, coverage 97.49 percent, gate 80)
  - `check: python 3.14 ok` (681 passed)
  - `check: all ok`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Per-session rev map instead of one rev ref**
- **Found during:** Task 1
- **Issue:** The plan reads `base_rev` from one `current.current.rev` that follows the focused session. A write queued for session A that runs after the focus moved to session B would send B's rev, which can pass the stale check on A's board and lose an update (T-04-11).
- **Fix:** `current.revs` maps each session id to its newest accepted rev. `take` updates it for every accepted reply, and a write reads `revs[asked]`. A focus change deletes the new session's entry, which is the plan's "reset on focus change".
- **Files modified:** plugin/desktop/plugin.js
- **Commit:** c3b1019

**2. [Rule 2 - Missing critical] A stale reply without a board counts as failed**
- **Found during:** Task 1
- **Issue:** `take` reads `reply.board`. A stale reply that carries no board would store an undefined board.
- **Fix:** `writeOutcome` returns `'failed'` for a stale reply with no board.
- **Files modified:** plugin/desktop/plugin.js
- **Commit:** c3b1019

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical). **Impact:** no plan contract changed; both change plugin.js internals only.

## Notes

- `test_reload_reply_during_a_write_is_ignored` serves a higher-rev board with an injected item text for the reload during the write. `viewBoard` puts the pending check on top of any board, so the check alone would hide a missing guard; the injected text shows it in the capture taken at write time.
- The plan says "seed ... (rev 2)" for two items. `seed_two` in the new test file makes two writes so the board reaches rev 2.
- The lower-rev guard still ignores a board whose rev goes down until the focus changes (the flagged assumption in the plan). Phase 5 owns board deletion.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- plugin/desktop/plugin.js: FOUND
- tests/test_pane_writes.py: FOUND
- Commits 73f1d66, c3b1019, 98f26c3, f6dc19e, 7b23cd3, 1ef28e8: FOUND on main
