---
phase: 06-cross-session-boards
plan: 05
subsystem: agent-tools
tags: [board_copy, tool-handler, copy, delegate-guard]
status: complete

requires:
  - phase: 06-cross-session-boards
    provides: BoardStore.copy_items (06-01), copy_args.parse (06-02), TitleLookup (06-03)
provides:
  - BoardTools.board_copy handler (TOOL-05)
  - BoardTools.titles field
  - results.DELEGATE_COPY, copy_summary, copy_result, source_missing_text
affects: [06-10 tool registration and text, 06-12 live test]

actuals:
  tokens: 9000
  tasks: 2
  commits: 3

plan_head_before: 91eb93705c0bb9ae88776af563dce901d5eec2c7
plan_head_after: f6a56f2f833c3d9fc3f283dd2e39d5a728bd4962
commits: 3

tech-stack:
  added: []
  patterns:
    - "handler order: keyword, resolve caller, delegate, parse, resolve source, same-root check, store call"
    - "listener guard after a committed write, only when changed_ids is non-empty"

key-files:
  created:
    - tests/test_board_cross.py
  modified:
    - plugin/session_tasks/board_tools.py
    - plugin/session_tasks/results.py

key-decisions:
  - "The Task 1 handler already held every guard in the plan's step 3 order, so the Task 2 tests passed on first run and Task 2 needed no code commit"

requirements-completed: [TOOL-05]
---

# Phase 6 Plan 05: board_copy tool handler Summary

`BoardTools.board_copy` copies chosen or all open items from another session's board into the caller's board, with the target taken only from the Hermes `session_id` keyword and the D-42 sentence `Copied N to <title>. M skipped, already on the board.` in the result.

## Accomplishments

- `board_copy(args, session_id=None, **kwargs)` returns `{ok, rev, summary, changed}`. The `changed` lines use the D-13 agent view with ids, in source display order, parent before subtask.
- Refusals write nothing: blank keyword (NO_SESSION, no reader opened), delegate caller (DELEGATE_COPY), same root (SAME_BOARD), unknown source (NO_SOURCE_BOARD), bad arguments (parser message through `describe`), unknown item id (names the id, "Nothing was copied.").
- The cap clause ` K not copied, the board holds 100 items.` follows the sentence only when the cap cut items.
- A copy that adds nothing returns ok with the current rev and calls no listener. A listener fault logs one WARNING from `session_tasks.board_tools` and the result stays ok.
- `BoardTools.titles` defaults to `no_titles()`, so a tool built without a lookup says `Untitled session`.
- 20 tests in `tests/test_board_cross.py`. They pass on Python 3.11 and 3.14 (3.14 run: test_board_cross, test_board_tools, test_layout).

## Task Commits

1. Task 1 RED: `3e9033d` test(06-05): add failing end to end test for board_copy
2. Task 1 GREEN: `34924e7` feat(06-05): board_copy handler copies items into the caller's board
3. Task 2 tests: `f6a56f2` test(06-05): add board_copy guard and sentence tests

## Deviations from Plan

### Auto-fixed Issues

None - plan executed as written, with one ordering note.

**Task 2 has no feat commit.** The plan's Task 1 step 3 already specifies the full handler order (keyword, delegate, parse, source resolve, same root, store call, Stale, listener guard). Task 1 implemented all of it, so the Task 2 tests passed on their first run and no handler change remained. The planned commit `feat(06-05): board_copy guards and result sentences` was skipped because it would be empty. Every test in the Task 2 behavior list exists and passes.

## Verification

- `uv run pytest tests/test_board_cross.py tests/test_board_tools.py tests/test_results.py tests/test_store_copy.py tests/test_layout.py -q -rs`: 123 passed, 0 skipped.
- ruff check, ruff format --check and pyright on the three files: clean.
- `board_tools.py` is 142 lines; `results.py` has no em dash or en dash.
- The first 06-05 commit is a test commit.
- `./scripts/check.sh` not run here; the orchestrator runs the wave gate.

## Known Stubs

None.

## Threat Flags

None. T-6-13 and T-6-14 are covered by `test_an_argument_session_id_never_changes_the_target` and `test_delegate_cannot_copy`.

## Self-Check: PASSED

- plugin/session_tasks/board_tools.py, plugin/session_tasks/results.py and tests/test_board_cross.py exist.
- Commits 3e9033d, 34924e7 and f6a56f2 are on main.
