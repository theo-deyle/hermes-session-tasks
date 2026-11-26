---
phase: 01-core-storage-and-session-identity
plan: 05
subsystem: storage
tags: [lineage, compression, branch, fork-copy, delegate, session-db, contract-test, sqlite]

requires:
  - phase: 01-02
    provides: schema v1, rows.py, aliases.py, db.write_txn, SessionResolver skeleton, fakes
  - phase: 01-03
    provides: BoardStore.apply with RemoveItem, subtask AddItem, SetText, SetChecked
provides:
  - SessionResolver.resolve for plain, compression, branch, delegate and reset sessions
  - SessionResolver.record_compaction for the Phase 2 post_compaction hook
  - fork.fork_copy, the one write a read may trigger, safe across two processes
  - session_reader.open_session_reader, SessionDB(read_only=True) behind a lazy import
  - SEVEN_ROW_FIXTURE, RaisingReaderFactory and a raising-method option in the fakes
  - hermes-marked contract tests that pin the fake reader and the resolver to the real SessionDB
affects: [01-06, phase-2, phase-3, phase-5]

plan_head_before: df28fb569a2218cce8e8693b0c06c47820510654
plan_head_after: 68304aea2fa652cef1200b3c51f91f71ae90f242

actuals:
  tokens: 12300
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "One _Walk object per top-level resolve holds the lazy reader and the visited set; the reader opens once and closes in finally"
    - "Alias lookup, compression alias write and fork copy each open their own short connection, so no transaction nests"
    - "The fork copy runs after every recursive resolve of the parent ends"
    - "A gateway venv script prints JSON and the pytest side compares it with the fake, one assert per id and per kind"

key-files:
  created:
    - plugin/session_tasks/fork.py
    - plugin/session_tasks/session_reader.py
    - tests/test_lineage.py
    - tests/test_fork.py
    - tests/fork_race_worker.py
    - tests/test_adapters.py
    - tests/test_hermes_contract.py
    - tests/hermes_contract_snippet.py
  modified:
    - plugin/session_tasks/lineage.py
    - tests/fakes.py

key-decisions:
  - "A delegate resolves to its delegator's root with kind delegate and gets no row of its own. The resolve of the delegator may still write the delegator's own alias or branch copy, because that is the delegator's first touch."
  - "Later resolves of a copied branch hit the alias and report kind plain. The branch origin stays in Board.forked_from."
  - "record_compaction skips the write when the old root equals the new id, so an alias never maps a session to itself by that path."
  - "The state.db digest ignores an empty state.db-wal file. A read only open makes SQLite create that empty file."

requirements-completed: [STOR-01, STOR-06]

coverage:
  - id: D1
    description: "Compression tip, middle and root resolve to one board key; reset child reads an empty board; delegate resolves to the delegator root and writes nothing of its own; missing row and missing state.db resolve plain with no alias"
    requirement: STOR-06
    verification:
      - kind: unit
        ref: "tests/test_lineage.py (34 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "record_compaction aliases the new id to the root of the old id by alias, then lineage, then the old id, and raises InvalidSession on a blank id"
    requirement: STOR-06
    verification:
      - kind: unit
        ref: "tests/test_lineage.py#test_record_compaction_finds_the_old_root_by_alias_then_lineage_then_the_old_id"
        status: pass
    human_judgment: false
  - id: D3
    description: "A branch starts with a copy of its parent board with new ids 1 to n, forked_from, one forked journal row, display order kept; a parent with no board writes nothing; branch of a branch, cycle and over-long chain are covered; four racing processes copy once"
    requirement: STOR-06
    verification:
      - kind: unit
        ref: "tests/test_fork.py (12 tests, spawn race included)"
        status: pass
    human_judgment: false
  - id: D4
    description: "plugin_db puts the board file under HERMES_HOME/plugin-data/hermes-session-tasks/data.db with wal, foreign_keys 1, busy_timeout 5000, and no state.db appears; the real SessionDB agrees with FakeSessionReader on all seven rows and missing; resolver kinds match; state.db bytes unchanged"
    requirement: STOR-01
    verification:
      - kind: integration
        ref: "uv run pytest -m hermes tests/test_hermes_contract.py -q -rs (3 passed, 0 skipped)"
        status: pass
      - kind: unit
        ref: "tests/test_adapters.py (3 tests)"
        status: pass
    human_judgment: false

duration: about 25min
completed: 2026-10-30
status: complete
---

# Phase 1 Plan 05: Lineage, branch copy and Hermes contract Summary

**Board follows its session through compression, a branch gets a one-time copy of its parent board, and the real Hermes SessionDB is pinned to the fake reader by a gateway-venv contract test**

## Performance

- **Duration:** about 25 min (the start time was not recorded)
- **Completed:** 2026-10-30T23:45:00Z
- **Tasks:** 3
- **Files modified:** 10 (2 modified, 8 created)

## Accomplishments

- `SessionResolver.resolve` handles every session kind from D-07 and orchestrator decision 1. It opens one reader per top-level call, closes it in `finally`, and stops a looping or over-long parent chain at `MAX_LINEAGE_HOPS = 20` with one warning and no write.
- `fork_copy` copies the parent board inside one `BEGIN IMMEDIATE` transaction: new ids 1 to n in display order, parent links remapped, every item rev 1, one `forked` journal row by actor `agent`, and the alias. A parent with no board writes nothing. Four spawned processes resolving one branch produce one board, one journal row and ids 1 to 4.
- `record_compaction` is ready for the Phase 2 hook. It finds the old root by alias, then one lineage call, then the old id.
- `open_session_reader` builds `SessionDB(read_only=True)` and nothing else. The contract test runs the real `SessionDB` in the gateway venv Python 3.11.16 against a temporary home: `is_explicit_fork_child`, `get_compression_lineage` and the projected session row equal the fake for all seven fixture ids and `missing`. The `state.db` bytes are the same after every resolve, and no `real Hermes home gained` line appears.

## Task Commits

1. **Task 1: resolver rules** - `c4516b6` (test, red: 19 failed, 15 passed), `d3c7bd1` (feat)
2. **Task 2: branch copy** - `8039798` (test, red: 8 failed, 4 passed), `dc5af6f` (feat)
3. **Task 3: adapters and contract** - `68304ae` (feat; the contract tests ran green on first use after one fix, see Deviations)

**Plan metadata:** the docs commit that holds this file.

## Files Created/Modified

- `plugin/session_tasks/lineage.py` - resolver for all kinds, `record_compaction`, marker helpers, `_Walk` (198 lines)
- `plugin/session_tasks/fork.py` - `fork_copy`
- `plugin/session_tasks/session_reader.py` - `open_session_reader`, the only `hermes_state` import
- `tests/fakes.py` - `SEVEN_ROW_FIXTURE`, `ReaderBoom`, `RaisingReaderFactory`, `raise_in` option
- `tests/test_lineage.py`, `tests/test_fork.py`, `tests/fork_race_worker.py` - resolver, copy and race tests
- `tests/test_adapters.py` - adapter tests with fake Hermes modules
- `tests/test_hermes_contract.py`, `tests/hermes_contract_snippet.py` - contract tests and the gateway-venv script

## Decisions Made

- A delegate takes the delegator's root and gets no row of its own. The recursive resolve of the delegator can still write the delegator's own compression alias or branch copy. That write is the delegator's first touch, not a delegate board. The Phase 2 write policy for delegates stays open.
- A copied branch reports kind `plain` on later resolves, because the alias `branch -> branch` answers first. `Board.forked_from` keeps the origin.
- A cycle test and a 25-link chain test both prove that a loop returns `plain` and writes nothing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The state.db digest counted an empty WAL file as a change**
- **Found during:** Task 3 (first contract run, `state_db_unchanged` was false)
- **Issue:** The plan says to hash `state.db` and any `state.db-wal`. A read only `SessionDB` open makes SQLite create an empty `state.db-wal` file, so the digest changed with no write. A debug script showed the `state.db` size and hash were identical and the WAL file had 0 bytes.
- **Fix:** The digest hashes `state.db` always and `state.db-wal` only when it holds data. Real writes land as WAL frames, so a write still changes the digest.
- **Files modified:** `tests/hermes_contract_snippet.py`
- **Verification:** `uv run pytest -m hermes tests/test_hermes_contract.py -q -rs` gives 3 passed, 0 skipped.
- **Committed in:** `68304ae`

---

**Total deviations:** 1 auto-fixed (1 bug in the plan's test design)
**Impact on plan:** None on scope. The check is as strong as the plan intended: it still fails on any write to the state.db main file or WAL frames.

## Issues Encountered

- A zsh quoting slip passed one string of paths to ruff. I used an array and the check ran.
- `uv run --isolated --locked --python 3.14` printed `Installed 24 packages` and left `.venv` as it was.

## Verification Results

- `uv run pytest tests/test_lineage.py tests/test_fork.py tests/test_adapters.py -q`: pass (49 tests).
- `uv run pytest -m hermes tests/test_hermes_contract.py -q -rs`: 3 passed, 0 skipped.
- `timeout 300 uv run --isolated --locked --python 3.14 pytest tests/test_lineage.py tests/test_fork.py tests/test_adapters.py tests/test_hermes_contract.py -q -rs`: 52 passed.
- `ruff check`, `ruff format --check` and `pyright` on all plan files: clean.
- `./scripts/check.sh`: `check: all ok`, 190 passed on Python 3.11 and on 3.14.
- `~/.hermes/plugin-data/hermes-session-tasks` does not exist after the runs.

## Known Stubs

None.

## Threat Flags

None. The new surface is the read only `state.db` open (T-01-13), covered by the threat model.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 01-06 can run the full matrix and close phase 1.
- Phase 2 registers the `post_compaction` hook with `on_post_compaction(session_id="", old_session_id="", **kwargs)` and calls `record_compaction`. It also decides the delegate write policy and runs the live `/compress` check on Desktop.

## Self-Check: PASSED

- Created files exist: fork.py, session_reader.py, test_lineage.py, test_fork.py, fork_race_worker.py, test_adapters.py, test_hermes_contract.py, hermes_contract_snippet.py.
- Commits found in HEAD history: c4516b6, d3c7bd1, 8039798, dc5af6f, 68304ae.
- Acceptance greps exit 0. `./scripts/check.sh` ended with `check: all ok`.

---
*Phase: 01-core-storage-and-session-identity*
*Completed: 2026-10-30*
