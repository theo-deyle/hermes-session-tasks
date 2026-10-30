---
phase: 01-core-storage-and-session-identity
plan: 06
subsystem: testing
tags: [integration-tests, coverage, check-gate, pytest-cov, phase-close]

requires:
  - phase: 01-03
    provides: BoardStore.apply, revision rule, two process race test
  - phase: 01-04
    provides: markdown parse, render and plan_import
  - phase: 01-05
    provides: SessionResolver, record_compaction, fork copy, Hermes contract tests
provides:
  - tests/test_phase_flow.py, seven integration tests across store, markdown and lineage
  - Coverage config in pyproject.toml with branch coverage and fail_under 80
  - Coverage gate in the Python 3.11 leg of scripts/check.sh
affects: [phase-2, phase-3]

plan_head_before: f095d24f753c4d2bcff566989030d2c2e1b91b05
plan_head_after: 425b2853623ec20f75d02cc8532877abb0231cd1

actuals:
  tokens: 4300
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Integration tests resolve the session id first, then call the store with the root id, the way the Phase 2 service does"
    - "Coverage runs only in the 3.11 leg; the 3.14 leg runs the same tests without it"

key-files:
  created:
    - tests/test_phase_flow.py
  modified:
    - pyproject.toml
    - scripts/check.sh

key-decisions:
  - "The coverage gate lives in the 3.11 leg only, as the plan says. The 3.14 leg proves the same 197 tests pass without coverage."
  - "fail_under stays at 80. Coverage is 97.09 percent, so no extra tests were needed and no warning ignore was added."

requirements-completed: [STOR-01, STOR-04, STOR-06, STOR-08, DEV-01, DEV-02]

coverage:
  - id: D1
    description: "An agent write and a user write share one board, a stale write returns the current board, every item field is set, timestamps end in Z, and state.db does not appear"
    requirement: STOR-04
    verification:
      - kind: integration
        ref: "tests/test_phase_flow.py#test_agent_and_user_share_one_board_and_a_stale_write_gets_the_current_board"
        status: pass
      - kind: integration
        ref: "tests/test_phase_flow.py#test_every_item_field_is_set_and_a_subtask_hangs_under_its_parent"
        status: pass
    human_judgment: false
  - id: D2
    description: "A board survives a rotating compression through the hook and through the lineage walk; a branch shows the parent items and later edits stay apart; reset gets an empty board and a delegate reads the delegator root"
    requirement: STOR-06
    verification:
      - kind: integration
        ref: "tests/test_phase_flow.py (compression, branch, reset and delegate tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A pasted checklist imports and renders back with no loss, hint ids equal stored ids, a line over 500 characters is skipped and counted, and an import into a nearly full board stops at the item cap"
    requirement: STOR-08
    verification:
      - kind: integration
        ref: "tests/test_phase_flow.py#test_pasted_checklist_round_trips_through_the_store_with_subtasks"
        status: pass
      - kind: integration
        ref: "tests/test_phase_flow.py#test_import_into_a_nearly_full_board_stops_at_the_cap"
        status: pass
    human_judgment: false
  - id: D4
    description: "check.sh passes ruff, format, pyright and pytest on Python 3.11 and 3.14 with 80 percent coverage enforced"
    requirement: DEV-01
    verification:
      - kind: command
        ref: "./scripts/check.sh (ends with check: all ok, coverage 97.09 percent)"
        status: pass
      - kind: command
        ref: "uv run pytest --cov --cov-fail-under=100 exits 1, so the gate fails when coverage is below the limit"
        status: pass
    human_judgment: false

duration: about 10min
completed: 2026-10-30
status: complete
---

# Phase 1 Plan 06: Phase flow tests and coverage gate Summary

**Seven integration tests run every ROADMAP criterion through store, markdown and lineage, and check.sh now enforces 80 percent branch coverage on Python 3.11 (97.09 percent measured)**

## Performance

- **Duration:** about 10 min (the start time was not recorded)
- **Completed:** 2026-10-30
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `tests/test_phase_flow.py` holds seven tests on one data file, with a `SessionResolver` and a `BoardStore` wired as the Phase 2 service will wire them. They cover: the stale write that returns the current board, the fields of every item and the subtask link, compression through the hook and through the lineage walk, a branch copy with edits kept apart, reset and delegate, a pasted checklist round trip, and the item cap on import.
- The pasted checklist test shows the D-02, D-09 and D-10 counters together: `moved == 1`, `skipped_empty == 1`, `too_long == 1`, and the short line after the 501 character line is on the board. `render` without ids gives the canonical checklist, and `parse` of `render` with ids gives hint ids equal to the stored ids.
- The nearly full board test fills 98 items, imports five, and adds two with overflow 3 and no `BoardFull`.
- `pyproject.toml` has `[tool.coverage.run]` (source `plugin/session_tasks`, branch true) and `[tool.coverage.report]` (`fail_under = 80`, `show_missing = true`). The 3.11 leg of `scripts/check.sh` runs `pytest -q --cov --cov-report=term-missing`.

## Task Commits

1. **Task 1: phase flow tests** - `6f3b4f6` (test)
2. **Task 2: coverage gate** - `425b285` (chore)

**Plan metadata:** the docs commit that holds this file.

## Files Created/Modified

- `tests/test_phase_flow.py` - seven integration tests, one or more per ROADMAP criterion
- `pyproject.toml` - coverage run and report config
- `scripts/check.sh` - coverage step in the 3.11 leg

## Decisions Made

- The coverage gate sits in the 3.11 leg only, as the plan says.
- No new test and no warning ignore were needed. Coverage is already above the limit.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Verification Results

- `uv run pytest tests/test_phase_flow.py -q`: 7 passed.
- `./scripts/check.sh`: `check: python 3.11 ok`, `check: python 3.14 ok`, `check: all ok`. Wall time 37 s.
- Tests per interpreter: 197 passed on Python 3.11 and 197 passed on Python 3.14.
- Coverage TOTAL on Python 3.11: 97.09 percent (732 statements, 160 branches). Lowest files: `paths.py` 69 percent, `db.py` 77 percent, `fork.py` 88 percent.
- Gate check: `pytest --cov --cov-fail-under=100` on 3.11 exits 1.
- `uv run pytest -m hermes -q -rs`: 3 passed, 0 skipped.
- No run printed `real Hermes home gained`. `~/.hermes/plugin-data/hermes-session-tasks` does not exist.
- `git status --porcelain` showed no `state.db`, `data.db` or `.coverage` file.

## Known Stubs

None.

## Threat Flags

None. T-01-18 is mitigated by `fail_under = 80` with branch coverage. No new package was added.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1 is complete. Phase 2 keeps `./scripts/check.sh` green.
- Phase 2 still owns the live `/compress` check on Desktop and the delegate write policy.
- `paths.py` and `db.py` hold the lowest coverage (the real `plugin_db` path and the connection error branches). Phase 2 adapter tests can raise it.

## Self-Check: PASSED

- Created file exists: `tests/test_phase_flow.py`.
- Commits found in HEAD history: 6f3b4f6, 425b285.
- Acceptance greps exit 0 (`plan_import(`, `record_compaction(`, `fail_under = 80`, `--cov`). `./scripts/check.sh` ended with `check: all ok`.

---
*Phase: 01-core-storage-and-session-identity*
*Completed: 2026-10-30*
