---
phase: 01-core-storage-and-session-identity
plan: 03
subsystem: storage
tags: [sqlite, revision-rule, subtasks, caps, journal, spawn-race, multiprocessing]

requires:
  - phase: 01-02
    provides: schema v1, BoardStore.get_board and top-level apply, rows.py, db.write_txn, resolver, fixtures
provides:
  - BoardStore.apply for AddItem, SetText, SetChecked and RemoveItem with subtasks, caps and the stale rule
  - revision.py with check_base_rev and the pure is_stale rule over the pre-batch board
  - rows.py read_item, update_item, delete_item, count_items, read_changes, prune_changes
  - spawn race tests that prove no lost write and no lost update across processes
affects: [01-04, 01-05, 01-06, phase-2, phase-3]

plan_head_before: 732036350f69fb97e72a2111a5594714a277b6cc
plan_head_after: b6f60f4961d3447cff011cb08cc00ef49aae2110

actuals:
  tokens: 30000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Existence reads the live transaction state. Staleness reads the pre-batch snapshot. Two ops on one item never make each other stale."
    - "A rejected write travels out of the transaction as a private exception, so write_txn rolls back, then the store reads the current board and returns Stale."
    - "Spawn workers live in tests/race_worker.py. Each worker puts exactly one result on the queue, an error included."

key-files:
  created:
    - plugin/session_tasks/revision.py
    - tests/test_store_items.py
    - tests/test_store_subtasks.py
    - tests/test_store_revision.py
    - tests/race_worker.py
    - tests/test_race.py
  modified:
    - plugin/session_tasks/store.py
    - plugin/session_tasks/rows.py
    - plugin/session_tasks/paths.py

key-decisions:
  - "The journal writes one row per changed item per operation (RESEARCH rule 10). Two ops on one item in one batch write two rows. changed_ids lists each id once, in first-change order."
  - "A check or uncheck journal row carries the item text, so a reader of the journal sees what the item was."
  - "A SetText or SetChecked that equals the current value is a no-op only after the stale check. A stale no-op reads as Stale."
  - "Subtasks for a cascade remove come from rows.read_items filtered by parent id, so rows.py needs no read_children function."

requirements-completed: [STOR-01, STOR-02, STOR-03, STOR-04, STOR-05, DEV-02]

coverage:
  - id: D1
    description: "All four item operations store every field, stamp the new rev and the actor, never reuse an id and journal each change"
    requirement: STOR-02
    verification:
      - kind: unit
        ref: "tests/test_store_items.py (23 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Subtasks hang under a top-level item, cascade on remove, never get a third level and never change a parent or child check state"
    requirement: STOR-03
    verification:
      - kind: unit
        ref: "tests/test_store_subtasks.py (14 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A write against a stale view, including a parent delete over a fresh subtask, returns Stale with the current board and changes nothing; the journal keeps 100 rows per board"
    requirement: STOR-04
    verification:
      - kind: unit
        ref: "tests/test_store_revision.py (26 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Four spawned processes write one file with no lost write, a one-item race ends with one Applied and one Stale, and the cap holds under concurrency, on Python 3.11 and 3.14"
    requirement: STOR-05
    verification:
      - kind: integration
        ref: "tests/test_race.py (4 tests); isolated Python 3.14 run of the four store test files, 67 passed"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-10-30
status: complete
---

# Phase 1 Plan 03: Item operations, revision rule and cross-process proof Summary

**BoardStore.apply now handles add, rename, check and remove with one-level subtasks, 100 item and 500 character caps and a per-item stale rule that makes a parent delete stale over a fresh subtask, proven across four spawned processes on Python 3.11 and 3.14.**

## Performance

- **Duration:** 9 min
- **Completed:** 2026-10-30T23:31Z
- **Tasks:** 3
- **Files modified:** 9 (6 created, 3 modified)

## Accomplishments

- `store.py` runs each batch in one `BEGIN IMMEDIATE` transaction. Ops apply in list order. The first failing op decides the outcome and its `op_index`. The item cap is checked after the last op, so a batch that removes and adds is judged by its end state.
- `revision.py` holds `check_base_rev` and `is_stale`. A parent remove is stale when any subtask in the pre-batch board has `rev > base_rev`. A `base_rev` above the board rev makes every targeting op stale and leaves plain adds alone.
- `rows.py` gained six functions and no existing line changed. The journal prunes to 100 rows per board inside the same transaction.
- The race tests ran 8 times in a row on Python 3.11 with 4 passed each time, and once on Python 3.14.

## Task Commits

1. **Task 1 and the rule of Task 2 (code)** - `ba0f8f0` (feat): `store.py`, `rows.py`, `revision.py`, item and subtask tests. RED evidence: the 37 new tests gave 25 failed against the plan 01-02 package, run from a `git archive` copy of the previous HEAD.
2. **Task 2 (tests)** - `74aa625` (test): 26 revision tests, all passing at once.
3. **Task 3 fix** - `0ec4204` (fix): WAL lock retry in `paths.connect_path`.
4. **Task 3 (tests)** - `b6f60f4` (test): `race_worker.py` and `test_race.py`.

**Plan metadata:** the docs commit that holds this file, STATE.md, ROADMAP.md and REQUIREMENTS.md.

## Test Results

- `uv run pytest tests/test_store_items.py tests/test_store_subtasks.py -q`: 37 passed (floor 20).
- `uv run pytest tests/test_store_revision.py -q`: 26 passed (floor 15).
- `timeout 240 uv run pytest tests/test_race.py -q`: 4 passed, about 4.4 s, stable over 8 runs.
- `uv run --isolated --locked --python 3.14 pytest` on the four store test files: 67 passed.
- `./scripts/check.sh`: 102 passed on each interpreter, ruff, format and pyright clean, `check: all ok`. No `real Hermes home gained` line.

## Decisions Made

- One journal row per changed item per operation, as RESEARCH rule 10 says. The plan truth reads "one row per batch" for a changed item. When two ops change one item in one batch, this code writes two rows. No test asserts the other reading.
- The stale check runs before the no-op check, so a stale `SetChecked` to the current value returns Stale. The race test needs this.
- `changed_ids` has no duplicates.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Concurrent first open failed with "database is locked"**
- **Found during:** Task 3, `test_four_processes_fill_a_fresh_file_to_the_cap_with_no_lost_write` (3 of 8 runs failed)
- **Issue:** `paths.connect_path` ran `PRAGMA journal_mode=WAL` once. SQLite returns "database is locked" at once, without the busy timeout, when several connections switch a fresh file to WAL together. Production `connect()` does not have this problem, because `hermes_cli.sqlite_util.open_db` retries that one error.
- **Fix:** `_enable_wal` retries the pragma up to 8 times on that one error, with a doubling sleep, like Hermes.
- **Files modified:** `plugin/session_tasks/paths.py` (not in the plan's `files_modified`; a plan 01-02 file)
- **Verification:** a 30 round, 4 process loop gave zero errors after the fix; the race tests passed 8 of 8 runs.
- **Commit:** `0ec4204`

**2. [Process] Revision rule landed with Task 1**
- **Issue:** `store.py` calls `is_stale` and `prune_changes` from the first working version, so `revision.py` and the prune SQL are in the Task 1 commit. The Task 2 commit holds only the revision tests, which passed at once. There is no separate RED run for Task 2.
- **Impact:** none on behavior. The Task 1 RED run (25 failed against the old package) covers the shared code.

**Total deviations:** 1 auto-fixed bug, 1 process note. **Impact:** the bug fix is small, mirrors Hermes, and plan 01-05 does not touch `paths.py`.

The commit trailer uses `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, the attribution line from the harness, as plans 01-01 and 01-02 did. The dispatch prompt named `Claude Fable 5.1`. This is a message trailer only.

## Issues Encountered

- The first Task 2 test run had one wrong expectation in `test_rev_rises_by_exactly_one_per_batch_and_reads_back_as_int` (a fourth item was needed to keep one item at rev 1). I fixed the test, not the code.

## Known Stubs

None.

## Flagged assumption (STOR-05)

The four race shapes in Task 3 are the whole STOR-05 coverage: concurrent first write to a fresh file, concurrent edits of disjoint items, a race on one item and a race at the cap. A writer killed mid-transaction is not tested. This is the plan's own assumption, unchanged.

## Threat Flags

None. No new endpoint, auth path or file access. T-01-07 to T-01-10 are implemented and tested. T-01-SC: no new package.

## Next Phase Readiness

- Plan 01-04 adds the markdown escape rule and parser to `markdown.py`. It does not touch the files here.
- Plan 01-05 can call `rows.read_board`, `read_items`, `create_board`, `save_board`, `insert_item`, `insert_change` and `BoardStore.get_board`. Each signature is unchanged.
- Plan 01-06 runs the full matrix once every wave 3 plan is done.

## Self-Check: PASSED

- Created files exist: revision.py, test_store_items.py, test_store_subtasks.py, test_store_revision.py, race_worker.py, test_race.py.
- Commits found in HEAD history: ba0f8f0, 74aa625, 0ec4204, b6f60f4.
- Acceptance greps exit 0: `def update_item`, `def read_changes`, `def prune_changes`, `def is_stale`, `def check_base_rev`, `is_stale(` in store.py, `DepthExceeded` and `BoardFull` in store.py, `get_context("spawn")`, `timeout=60`, `def add_items`.
- `./scripts/check.sh` ended with `check: all ok`.

---
*Phase: 01-core-storage-and-session-identity*
*Completed: 2026-10-30*
