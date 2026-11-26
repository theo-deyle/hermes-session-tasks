---
phase: 06-cross-session-boards
plan: 02
subsystem: tool-arguments
tags: [validation, copy, board-read, layout-guard]
status: complete

requires:
  - phase: 05-agent-sees-theo-s-edits
    provides: edit_args parser pattern (ops, base_rev)
provides:
  - copy_args.parse for board_copy (from_session_id, item_ids, base_rev)
  - copy_args.read_target for the session_id of board_read
  - public edit_args.whole_number and edit_args.base_rev_arg
  - TOOL-06 layout guard with one sanctioned read
affects: [06-05 board_copy tool, 06-08 cross read handler, 06-09 POST /board/copy route]

actuals:
  tokens: 7500
  tasks: 2
  commits: 4

plan_head_before: 88fe914fc6e3ab71f4ac8ddb97c221206c8ef8b9
plan_head_after: 397dce8fe67c923075d20b0a2fe6bed59dba8a86
commits: 4

tech-stack:
  added: []
  patterns:
    - "one pure parser serves the tool and the route (as edit_args does)"
    - "layout guard allow-list of (file name, function name) pairs"

key-files:
  created:
    - plugin/session_tasks/copy_args.py
    - tests/test_copy_args.py
  modified:
    - plugin/session_tasks/edit_args.py
    - tests/test_layout.py

key-decisions:
  - "A non-digit string for item_ids (for example \"x\") is ITEM_IDS_BAD, not an index error"
  - "A raw item_ids list over 1000 entries is refused before the loop with the 100 id error"
  - "The guard skips only top-level functions of the named file; the same read elsewhere is still reported"

requirements-completed: [TOOL-04, TOOL-05, PANE-10]
---

# Phase 6 Plan 02: Copy and cross-read arguments Summary

`copy_args.parse` turns a `board_copy` call into `CopyArgs(from_session_id, item_ids, base_rev)` with plain errors for every bad value, `copy_args.read_target` names the board `board_read` should read, and the TOOL-06 guard allows that one read and no other.

## Accomplishments

- `parse` accepts `item_ids` as a list, a JSON string of a list or one whole number; ids are 1 or more, de-duplicated in first-seen order, at most 100 distinct. An empty list is an error. A bad id names its index (`item_ids[1]`).
- `from_session_id` is required, non-blank, at most 256 characters. `base_rev` goes through `edit_args.base_rev_arg` and gives the board_edit error text.
- `read_target` returns None for an absent or blank `session_id`, the stripped text otherwise, and raises for a non-string or a value over 256 characters.
- `edit_args._whole` and `_base_rev` are now public `whole_number` and `base_rev_arg`; `tests/test_edit_args.py` is unchanged and green.
- `tests/test_layout.py`: `SANCTIONED_ARG_READS = {("copy_args.py", "read_target")}`; `session_id_arg_findings` skips the body of that one function. Every other read is still reported.

## Planner finding (TOOL-06 guard)

`test_core_never_reads_session_id_from_the_tool_arguments` reported any `args.get("session_id")` in core, which D-38 needs once. The guard now has a one-pair allow-list and stays strict elsewhere. `test_session_id_guard_allows_only_the_sanctioned_function` proves a second function in `copy_args.py`, and a `read_target` in another file, are still reported. RESEARCH listed three tests that contradict D-38; this guard is a fourth, and the `spoofed` case of `tests/test_hermes_dispatch.py` is a fifth (plan 06-08 changes it).

## Task Commits

| Task | Commit | Type |
|------|--------|------|
| 1 RED | 65707be | test(06-02): add failing tests for the copy arguments |
| 1 GREEN | c3111bb | feat(06-02): parse the copy arguments and the board_read target |
| 2 RED | 80affdd | test(06-02): add copy argument limit and guard edge tests |
| 2 GREEN | 397dce8 | feat(06-02): limits for the copy arguments and the board_read target |

## TDD evidence

- Task 1 red line: `ModuleNotFoundError: No module named 'session_tasks.copy_args'` (1 error during collection).
- Task 2 red line: 22 failures for `tests/test_copy_args.py` and `tests/test_layout.py` against the one-path parser from task 1. The new guard edge test already passed at task 1 because the task 1 guard change was the narrowed one.
- Green: `127 passed` for test_copy_args, test_edit_args and test_layout on Python 3.11 (uv project env) and on Python 3.14 (`.venv-py3.14`).

## Verification

- `ruff check`, `ruff format --check` and `pyright` on the four files: clean.
- `copy_args.py` is 112 lines, every function is under 50 lines, imports only `json`, `collections.abc`, `dataclasses`, `.edit_args`, `.model`.
- The first 06-02 commit is a test commit.
- `./scripts/check.sh` was not run here: the plan assigns it to the executor that finishes wave 1 last.

## Deviations from Plan

None - plan executed as written. Notes:

- The task 1 RED test file failed `ruff format` and import order; the fix landed in the task 1 GREEN commit.
- Task 2 RED was reached by keeping the task 1 one-path `copy_args.py` in place during the test commit and restoring the full parser for GREEN.
- One fix inside GREEN: a non-digit string such as `"x"` returns ITEM_IDS_BAD as the behavior list says, not an index error.

## Known Stubs

None.

## Threat Flags

None. T-6-04 (guard test), T-6-05 (limit tests) and T-6-06 (session id tests) are covered by the tests named in the plan.

## Self-Check: PASSED

copy_args.py, test_copy_args.py, edit_args.py and test_layout.py exist; commits 65707be, c3111bb, 80affdd and 397dce8 are ancestors of HEAD.
