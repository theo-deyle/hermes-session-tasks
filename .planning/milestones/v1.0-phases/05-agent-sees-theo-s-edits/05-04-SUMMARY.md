---
phase: 05-agent-sees-theo-s-edits
plan: 04
subsystem: storage-hooks
tags: [on_session_delete, board cleanup, SessionDB, aliases, hooks, pytest]
status: complete

requires:
  - phase: 05-agent-sees-theo-s-edits
    provides: the post_compaction hook shape, BoardStore write pattern (plan 05-01), tests/hermes_snippet_setup.py (plan 05-03)
provides:
  - BoardStore.delete_boards, rows.delete_boards and aliases.delete_aliases
  - hooks.make_on_session_delete, registered as on_session_delete and declared in plugin.yaml
  - a real SessionDB contract test of delete, bulk delete, chain delete and archive in a temporary home
affects: [05-05, 05-06, 05-07]

actuals:
  tokens: 31000
  tasks: 3
  commits: 5
plan_head_before: b63beff4bccb7a4171b700ea5034ea279161d886
plan_head_after: 1b0c3a50beacbc87024eacba77631e10667204bc
commits: 5

tech-stack:
  added: []
  patterns:
    - a hook callback checks the type of every payload value, then does one short write transaction, and logs one warning on a fault
    - ids go to SQL in chunks of 500 inside one write transaction
    - a board goes only on an exact root id match; an alias match removes the alias row only

key-files:
  created:
    - tests/test_session_delete.py
    - tests/hermes_session_delete_snippet.py
    - tests/test_hermes_session_delete.py
  modified:
    - plugin/session_tasks/aliases.py
    - plugin/session_tasks/rows.py
    - plugin/session_tasks/store.py
    - plugin/session_tasks/hooks.py
    - plugin/session_tasks/wiring.py
    - plugin/plugin.yaml
    - tests/test_register.py

key-decisions:
  - "The alias delete also removes alias rows whose root id is in the list (RESEARCH addition). It never removes a board by an alias match."
  - "A missing or non-string reason removes nothing. An unreadable payload is not a reason, so the safe action is none."
  - "The contract snippet deletes the chain with include_compression_chain=True, the argument the dashboard and Desktop delete paths pass. Plain delete_session deletes only the tip row of a parent_session_id chain."

requirements-completed: [STOR-07]

coverage:
  - id: D1
    description: "When Hermes deletes a session, the plugin removes that session's board with its items, journal rows and alias rows, and leaves every other board unchanged."
    requirement: STOR-07
    verification:
      - kind: unit
        ref: "tests/test_session_delete.py#test_a_deleted_session_takes_its_board"
        status: pass
      - kind: unit
        ref: "tests/test_session_delete.py#test_bulk_delete_removes_every_listed_board"
        status: pass
      - kind: unit
        ref: "tests/test_register.py#test_registered_on_session_delete_removes_a_board"
        status: pass
    human_judgment: false
  - id: D2
    description: "An archive removes nothing, an alias-only match keeps the board, and a branch board survives the delete of its parent."
    requirement: STOR-07
    verification:
      - kind: unit
        ref: "tests/test_session_delete.py#test_archive_keeps_the_board"
        status: pass
      - kind: unit
        ref: "tests/test_session_delete.py#test_alias_only_match_keeps_the_board"
        status: pass
      - kind: unit
        ref: "tests/test_session_delete.py#test_a_branch_board_survives_its_parent"
        status: pass
    human_judgment: false
  - id: D3
    description: "A bad payload removes nothing and raises nothing, a store fault logs one warning, and 1200 ids are deleted in chunks."
    requirement: STOR-07
    verification:
      - kind: unit
        ref: "tests/test_session_delete.py#test_bad_payloads_remove_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_session_delete.py#test_store_fault_logs_a_warning_and_raises_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_session_delete.py#test_twelve_hundred_ids_are_deleted_in_chunks"
        status: pass
      - kind: unit
        ref: "tests/test_session_delete.py#test_a_delegate_id_in_the_list_removes_nothing_of_its_own"
        status: pass
    human_judgment: false
  - id: D4
    description: "Hermes loads the hook: the manifest declares it and the plugin gate passes."
    requirement: STOR-07
    verification:
      - kind: command
        ref: "hermes plugins validate plugin/"
        status: pass
      - kind: unit
        ref: "tests/test_register.py#test_manifest_provides_exactly_the_registered_tools_and_hooks"
        status: pass
    human_judgment: false
  - id: D5
    description: "Through a real Hermes SessionDB, delete, bulk delete and a chain delete remove their boards, an archive keeps both boards of a chain, and an unrelated board stays."
    requirement: STOR-07
    verification:
      - kind: integration
        ref: "tests/test_hermes_session_delete.py#test_hermes_delete_paths_reach_the_plugin"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-11-02
---

# Phase 5 Plan 04: Board cleanup when a chat is deleted Summary

**Hermes's `on_session_delete` hook now removes a deleted session's board, items, journal and alias rows in one chunked write transaction, keeps every board on an archive, and was proven against a real SessionDB in a temporary home.**

## Performance

- **Duration:** about 15 min
- **Completed:** 2026-11-02T14:20Z
- **Tasks:** 3
- **Files modified:** 10 (3 created, 7 modified)

## Accomplishments

- `aliases.delete_aliases`, `rows.delete_boards` and `BoardStore.delete_boards` (`SQL_IN_CHUNK = 500`). The foreign key cascade removes items and changes.
- `hooks.make_on_session_delete`, `_delete_ids` and `ARCHIVE_REASON`. The callback checks the type of `reason`, `session_id` and `deleted_ids`, returns on `archive`, and logs one WARNING from `session_tasks.hooks` on a store fault.
- `wiring.register` registers `on_session_delete`; `plugin.yaml` lists it under `provides_hooks`.
- 17 unit tests in `tests/test_session_delete.py` (the tracer, eight edge tests, nine bad payload cases), one more in `tests/test_register.py`, and the real SessionDB contract test.

## Planner choices (recorded as the plan asks)

1. The alias delete removes alias rows whose session id or root id is in the list. A board goes only on an exact root id match.
2. A missing or non-string `reason` removes nothing.

## RED evidence

- Task 1 RED: `tests/test_session_delete.py` failed on `ImportError: cannot import name 'make_on_session_delete'`. Commit `884c378` is the first 05-04 commit.
- Task 3 RED: the eight edge tests (17 cases) passed on the Task 1 code. The contract test failed because `tests/hermes_session_delete_snippet.py` did not exist (`No such file or directory`, exit 2).

## Task Commits

1. Task 1 RED: `884c378` test(05-04): add failing test that a deleted session takes its board
2. Task 1 GREEN: `776c1cc` feat(05-04): remove a board when Hermes deletes its session
3. Task 2: `511ce6c` feat(05-04): register the session delete hook
4. Task 3 RED: `e6313f6` test(05-04): add delete edge tests and the SessionDB contract test
5. Task 3 GREEN: `1b0c3a5` test(05-04): pin delete edges and the real SessionDB delete paths

## TDD Gate Compliance

The first 05-04 commit is a test commit (order check on `git log` passed). The tracer test was re-run after GREEN and passed before Task 2 began.

## Files Created/Modified

- `plugin/session_tasks/aliases.py` - `delete_aliases`
- `plugin/session_tasks/rows.py` - `delete_boards`
- `plugin/session_tasks/store.py` - `SQL_IN_CHUNK`, `BoardStore.delete_boards`
- `plugin/session_tasks/hooks.py` - `ARCHIVE_REASON`, `_delete_ids`, `make_on_session_delete`
- `plugin/session_tasks/wiring.py` - the `on_session_delete` registration
- `plugin/plugin.yaml` - `provides_hooks` entry
- `tests/test_session_delete.py`, `tests/test_register.py` - unit tests
- `tests/hermes_session_delete_snippet.py`, `tests/test_hermes_session_delete.py` - the SessionDB contract

## Deviations from Plan

**1. [Rule 3 - Blocking] The snippet does not call `append_message`**
- **Found during:** Task 3
- **Issue:** The plan says to call `create_session` and `append_message` for each session. In a new data root, the first `append_message` imports `agent.conversation_loop`, which relaunches the gateway Python through the Hermes dependency sync. The relaunch runs the script a second time, and `link_and_enable` fails with `FileExistsError` (and the run takes 30 seconds).
- **Fix:** The snippet calls `create_session` only. Delete and archive need no message rows, and the run takes about 1.5 seconds.
- **Files modified:** `tests/hermes_session_delete_snippet.py`
- **Commit:** `1b0c3a5`

**2. [Rule 1 - Bug in the plan's premise] Chain delete needs `include_compression_chain=True`**
- **Found during:** Task 3
- **Issue:** Plain `SessionDB.delete_session("chain")` deleted only the tip row (`deleted_ids` was None), so the board held by `chain-root` stayed. The plan and RESEARCH say a chain delete from any segment removes the whole lineage. In the Hermes tree this holds for local reset lineages with a policy receipt, and for `include_compression_chain=True`, the argument the dashboard and Desktop delete paths pass (`hermes_state_sessions.py:1719-1745`).
- **Fix:** The snippet passes `include_compression_chain=True`. The event then carries `deleted_ids == ["chain", "chain-root"]`, and the test asserts it. The hook code needed no change.
- **Files modified:** `tests/hermes_session_delete_snippet.py`, `tests/test_hermes_session_delete.py`
- **Commit:** `1b0c3a5`

**Total deviations:** 2 auto-fixed (1 blocking, 1 plan premise). **Impact:** test setup only. No plugin code changed from the plan. A plain `delete_session` on a bare `parent_session_id` chain still leaves the chain root board, which the plan already treats as an inert board (T-05-16, no orphan sweep).

## Issues Encountered

None open. `./scripts/check.sh` ended with `check: all ok`: 832 passed on Python 3.11 with 97.34 percent coverage (gate 80), 832 passed on Python 3.14. No `home_guard` failure occurred.

## Verification

- `uv run pytest tests/test_session_delete.py tests/test_register.py tests/test_hermes_session_delete.py -q -rs`: 30 passed, 0 skipped.
- `timeout 120 hermes plugins validate plugin/` output (key lines): `✓ declared tools - matches registrations`, `✓ declared hooks - matches registrations`, `✓ security scan - safe`, `✓ desktop surface - stays inside the plugin SDK surface`, `Validation passed.`
- Real SessionDB snippet printed: boards left `["keep", "arch-root", "arch"]`; payloads `cli` / `delete` / None, `bulk1` / `delete` / `["bulk1", "bulk2"]`, `chain` / `delete` / `["chain", "chain-root"]`, `arch` / `archive` / `["arch", "arch-root"]`.
- Acceptance greps: `def make_on_session_delete` (hooks.py), `def delete_boards` (store.py, rows.py), `def delete_aliases` (aliases.py), `SQL_IN_CHUNK = 500` (store.py), `on_session_delete` once in `plugin.yaml` and once in `wiring.py`: all print.

## Known Stubs

None.

## Threat Flags

None. T-05-12 to T-05-15 are mitigated and tested (archive returns first; type checks and exact root match; chunks of 500; try/except with one warning). T-05-16 is accepted: no orphan sweep, per D-37.

## User Setup Required

None. The real gateway was not restarted and no real session was deleted. The plugin code reaches a running Desktop backend after its next restart (phase 7).

## Next Phase Readiness

Plan 05-05 can build on the four-hook registration. The snippet note about `append_message` helps any later snippet that needs message rows.

## Self-Check: PASSED

All ten plan files exist. Commits `884c378`, `776c1cc`, `511ce6c`, `e6313f6` and `1b0c3a5` are ancestors of HEAD.

---
*Phase: 05-agent-sees-theo-s-edits*
*Completed: 2026-11-02*
