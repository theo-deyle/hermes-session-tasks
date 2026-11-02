---
phase: 06-cross-session-boards
plan: 07
subsystem: live-test-tools
tags: [live-check, seed, board-read, tool-calls, gateway-stop, prompts]
status: complete

requires:
  - phase: 06-cross-session-boards
    provides: BoardStore.copy_items and the `copied` journal rows (plan 06-01), the contract-snippet approach to seeding a scratch home (plan 06-03)
provides:
  - tests/live/cross/cross_live.py with seed, board, calls and stop subcommands
  - refuse_real_home, read_board, tool_calls, main
  - four live prompt files (list, read, copy, mention) that name the seeded session cross-src-1
affects: [06-12 live check with the real model]

actuals:
  tokens: 4540
  tasks: 3
  commits: 6

plan_head_before: 44aa62895d698604a93abd11236c10f90302c3fe
plan_head_after: 19f7e29b497a7c126e55c6428ada7265408c2e8e
commits: 6

tech-stack:
  added: []
  patterns:
    - "live script loads sibling live scripts by file path (importlib spec_from_file_location), never copies them"
    - "refusal of the real Hermes home runs before any Hermes import"

key-files:
  created:
    - tests/live/cross/cross_live.py
    - tests/live/cross/list.txt
    - tests/live/cross/read.txt
    - tests/live/cross/copy.txt
    - tests/live/cross/mention.txt
    - tests/test_live_cross.py
  modified: []

key-decisions:
  - "seed makes the session row with SessionDB.create_session and set_session_title only. It adds no message rows, so it never calls append_message and never triggers the Hermes dependency sync that plan 06-03 hit."
  - "Seeded items carry updated_by `user`, because seed uses the pane write path (BoardApi.edit) as theo_edit.py does."
  - "calls prints one JSON list on one line; stop prints {home, result} and exits 1 on a refusal."

requirements-completed: [TOOL-03, TOOL-04, TOOL-05]

duration: 25 min
completed: 2026-11-02
---

# Phase 6 Plan 7: Cross-session live check tools Summary

Four tested subcommands (seed, board, calls, stop) and four prompt files let plan 06-12 seed a titled source board in a test Hermes home, read it and its copy journal read only, list the tool calls of a headless run, and stop the test gateway.

## What changed

- `seed` refuses (exit 2, no write) when HERMES_HOME is unset, blank or the real `~/.hermes`. It then creates the session `cross-src-1`, sets its title and applies the ops through `board_api.build(publish=<no-op>).edit(session, ops, 0)`. It prints `{session, title, ok, rev, changed_ids}`.
- `board` opens the data file with a `mode=ro` URI, maps a session id through the aliases table and prints `{rev, agent_seen_rev, items, copied}`. A missing file or board gives exit 2.
- `calls` loads `tests/live/own_job/analyze.py` by file path and prints `{name, args}` for each `tool_use`, naming the real tool inside a `tool_call` bridge use.
- `stop` loads `tests/live/delta/delta_live.py` by file path and calls `stop_test_gateway`. Exit 0 for `stopped` or `not running`, 1 for `refused`.
- Prompt files: `read.txt` and `mention.txt` ask for no change, only `copy.txt` asks for a copy, `list.txt` names no session. No file holds an em dash or an en dash.

## Verification

- `uv run pytest tests/test_live_cross.py -q -rs` gives 11 passed, 0 skipped. The hermes-marked tracer test runs the real gateway venv Python against a temporary HERMES_HOME.
- `ruff check`, `ruff format --check` and `pyright` are clean on both files.
- The first 06-07 commit is a test commit.
- `./scripts/check.sh` was not run, as ordered. The orchestrator runs the wave gate. Tests ran on Python 3.11 only here.

## Deviations from Plan

None - plan executed as written. In Task 2 the refusal and missing-board tests passed on first run, because Task 1 already built those paths (the plan names `refuse_real_home` and the missing-board path in Task 1). The RED run of Task 2 failed on the `calls` and two `stop` tests.

## Known Stubs

None.

## Threat Flags

None. T-6-20 is covered by test_seed_refuses_the_real_home and test_seed_refuses_an_unset_home. T-6-21 is covered by the digest check in test_board_reads_items_and_copied_rows_read_only. T-6-22 is covered by test_stop_refuses_a_pid_file_that_names_another_home.

## Commits

1. `1d62c87` test(06-07): add failing test for the cross-session live tools
2. `43615ba` feat(06-07): seed and read boards for the cross-session live check
3. `74f3033` test(06-07): add refusal, journal, calls and stop tests
4. `1fc4f6e` feat(06-07): calls, stop and the refusal paths of the live tools
5. `cc01b05` test(06-07): prompt files for the cross-session live run
6. `19f7e29` test(06-07): build the dash characters in the prompt test without literals

## Self-Check: PASSED

All six created files exist and all six commits are ancestors of HEAD.
