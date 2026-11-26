---
phase: 06-cross-session-boards
plan: 08
subsystem: board-tools
tags: [board-read, board-sessions, cross-read, tool-handlers]
status: complete

requires:
  - phase: 06-cross-session-boards
    provides: copy_args.read_target (06-02), TitleLookup and BoardTools.titles (06-03, 06-05), NO_SOURCE_BOARD (06-01)
provides:
  - board_read with an optional session_id argument that reads another session's board and marks nothing seen
  - BoardTools.board_sessions, one line per board, newest update first, at most 50 lines
  - results.py helpers OTHER_BOARD_NOTE, NO_SESSIONS_NOTE, SESSIONS_SHOWN, session_line, sessions_result, cross_read_result
affects: [06-09, 06-10 schemas and tool text, 06-11, 06-12 live check]

actuals:
  tokens: 9000
  tasks: 3
  commits: 5

plan_head_before: 9d5445e1421384ab52c73e048ecac6ca907732f7
plan_head_after: 47c777af55473e6af129eb6ae816a3b4567223df
commits: 5

tech-stack:
  added: []
  patterns:
    - "board_read splits into _own_read and _cross_read; the cross path calls no _mark_seen and no store write"
    - "the caller still resolves from the keyword only; the argument goes through copy_args.read_target"

key-files:
  created: []
  modified:
    - plugin/session_tasks/board_tools.py
    - plugin/session_tasks/results.py
    - tests/test_board_cross.py
    - tests/test_board_tools.py
    - tests/test_hermes_dispatch.py

key-decisions:
  - "A cross read of an id with no board (rev 0) gives the NO_SOURCE_BOARD error and creates no row (RESEARCH P2)."
  - "board_sessions never reads its arguments; a fault while it resolves the caller gives no (this session) marker, never an error."
  - "RESEARCH A6 recorded: 50 lines are enough for about five users' sessions; `more` counts the boards not shown."

requirements-completed: [TOOL-03, TOOL-04]
---

# Phase 6 Plan 8: Cross read and board_sessions Summary

The agent can now list every session that has a board (`board_sessions`) and read another session's board by session id (`board_read` with a `session_id` argument), and a cross read moves no seen mark.

## What was built

1. `board_read` keeps its keyword check and resolve. It reads the argument through `copy_args.read_target`. No argument, a blank argument, or an id of the own lineage gives the old own read (marks seen, as before). Another board gives `{ok, rev, session_id, title, note, board}` with the note `OTHER_BOARD_NOTE` (plus `; empty board` for an empty board). A non-string argument gives `TARGET_BAD`. An unknown id or a board at rev 0 gives `NO_SOURCE_BOARD` and creates no row.
2. `board_sessions` returns `- <title> | <session id> | <open> of <total> open | updated <updated_at>` per board, with ` (this session)` on the caller's own board, newest update first and ties by root id. It uses `BoardStore.list_boards` (one read snapshot) and one `TitleLookup.titles` call for all shown roots. No board gives `sessions: []`, `more: 0` and `NO_SESSIONS_NOTE`.
3. The two tests that asserted the old meaning changed as the plan says: `test_read_ignores_a_session_id_in_the_arguments` became `test_own_read_still_comes_from_the_keyword`, and the `spoofed` expectation in `tests/test_hermes_dispatch.py` now equals `{"error": NO_SOURCE_BOARD}`.

## Flagged edge (recorded as the plan asked)

A cross read of a branch session id that never had a board makes the resolver copy its parent's board (Phase 1 fork rule), so that one read can create a board. This is the existing "one write a read may trigger" rule. `test_a_cross_read_of_a_branch_id_copies_its_parent_board_once` tests it: the first read creates the `br` board, the second read writes nothing more. Accepted.

## Counts for the acceptance criteria

- `grep -c "_mark_seen" plugin/session_tasks/board_tools.py` prints 3 before and after this plan (the definition, the own read and the stale branch of `board_edit`). The cross path adds none.
- `grep -c '"session_id"' plugin/session_tasks/board_tools.py` prints 0. `read_target` appears once.
- `board_tools.py` is 199 lines.

## Verification

- `uv run pytest tests/test_board_cross.py tests/test_board_tools.py tests/test_results.py tests/test_store_list.py tests/test_layout.py tests/test_lineage.py -q` passes on Python 3.11.
- `tests/test_board_cross.py tests/test_board_tools.py tests/test_results.py` pass on Python 3.14 (scratch environment).
- `uv run pytest tests/test_hermes_dispatch.py -q -rs -m hermes`: 4 passed, 0 skipped.
- `ruff check`, `ruff format --check` and `pyright` pass on the five files.
- `./scripts/check.sh` was not run (the orchestrator runs the wave gate).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Duplicate `seen` helper in tests/test_board_tools.py**
- **Found during:** Task 1 GREEN lint
- **Issue:** the RED commit added a `seen` helper, but the file already defined one at the end.
- **Fix:** removed my copy in the Task 1 feature commit.
- **Commit:** 78ad149

### Plan step not needed

**2. Task 2 has no separate feature commit.** The Task 1 implementation already covered every Task 2 rule (blank argument, own lineage, bad argument, unknown id, delegate caller, empty board, branch id, untitled fallback). The Task 2 tests all passed on first run, so no GREEN change existed to commit. The test commit `78df4f0` holds the tests; the rules are covered by `78ad149`. The plan's "the cases Task 1 did not cover fail" did not occur.

**3. RED for Task 3 fails at import** (the new names `NO_SESSIONS_NOTE` and `SESSIONS_SHOWN` do not exist yet), which fails the whole module at collection. Task 1 RED fails the same way for `OTHER_BOARD_NOTE`.

## Authentication gates

None.

## Known Stubs

None.

## Threat Flags

None. T-6-23 to T-6-26 are covered by the tests named in the plan (`test_own_read_still_comes_from_the_keyword`, `test_board_read_names_another_board_and_marks_nothing`, `test_more_than_50_boards_lists_50_and_counts_the_rest`).

## Commits

- 3da7127 test(06-08): add failing end to end test for a cross board_read
- 78ad149 feat(06-08): board_read reads another session's board on request
- 78df4f0 test(06-08): add cross read rule tests
- fdbb5ff test(06-08): add board_sessions tests
- 47c777a feat(06-08): board_sessions lists the boards with titles and counts

## Self-Check: PASSED

The five commits are ancestors of HEAD, and the five modified files exist.
