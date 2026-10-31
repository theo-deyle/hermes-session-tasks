---
phase: 02-agent-tools-and-skill
plan: 02
subsystem: agent-tools
tags: [hermes-plugin, pre_tool_call, post_compaction, board_edit, argument-parser, guard, pytest]
status: complete

requires:
  - phase: 02-agent-tools-and-skill
    provides: results.describe, tool_text.BOARD_EDIT, tests/fakes.py, BoardTools shape (plan 02-01)
  - phase: 01-core-storage-and-session-identity
    provides: BoardStore, SessionResolver.record_compaction, model ops and BoardError, revision.target_id
provides:
  - edit_args.parse, one parser for raw hook arguments and coerced handler arguments
  - guard rule (has_candidates, needs_board, guarded_reasons, block_message)
  - make_pre_tool_call and make_post_compaction hook callbacks
affects: [02-03, 02-04, 02-05]

actuals:
  tokens: 8600
  tasks: 2
  commits: 4
plan_head_before: d1adb072bfcb0317630bd941669b7c93c9157847
plan_head_after: afc05a60525d09612c308171265abb74773a2cb2

tech-stack:
  added: []
  patterns:
    - "One parser (edit_args.parse) serves the hook and the handler"
    - "Hook first statement returns None for every other tool; board_edit fails closed"
    - "Hook session comes from the session_id keyword, never from args"
    - "Guard rule is pure functions over the parsed ops and a Board or None"

key-files:
  created:
    - plugin/session_tasks/edit_args.py
    - plugin/session_tasks/guard.py
    - plugin/session_tasks/hooks.py
    - tests/test_edit_args.py
    - tests/test_guard.py
    - tests/test_hooks.py
  modified: []

key-decisions:
  - "The hook blocks a board_edit call whose arguments do not parse, with the same rule text the handler returns (closes the gap where Hermes coerces after the hook runs)"
  - "A reword with no board available is guarded: an unknown author errs toward asking"
  - "A delegate session and a blank session return None from the hook, because the handler refuses those writes"
  - "post_compaction passes a non-string new id as blank so the resolver rejects it and the hook logs, never raises"

patterns-established:
  - "OP_FIELDS is a MappingProxyType, so the field table cannot change at run time"
  - "Per-op errors raise inside a builder with no index; _parse_op adds the op index once"

requirements-completed: [TOOL-02, AGNT-03]

coverage:
  - id: D1
    description: "edit_args.parse maps add, set_text, set_checked and remove to the op dataclasses and gives equal results for raw and coerced forms"
    requirement: "TOOL-02"
    verification:
      - kind: unit
        ref: "tests/test_edit_args.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "parse rejects unknown ops, unknown fields, wrong types, bool ids, more than 100 ops, and a missing base_rev, with the op index"
    requirement: "TOOL-02"
    verification:
      - kind: unit
        ref: "tests/test_edit_args.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "The pre_tool_call hook blocks an unconfirmed remove, uncheck and reword of an item Theo touched, and passes adds and checks"
    requirement: "AGNT-03"
    verification:
      - kind: unit
        ref: "tests/test_hooks.py#test_pre_tool_call_blocks_an_unconfirmed_remove"
        status: pass
      - kind: unit
        ref: "tests/test_hooks.py#test_pre_tool_call_passes_adds_and_checks_in_any_count"
        status: pass
      - kind: unit
        ref: "tests/test_guard.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "The hook never breaks another tool, fails closed only for board_edit, and returns only a block directive or None"
    requirement: "AGNT-03"
    verification:
      - kind: unit
        ref: "tests/test_hooks.py#test_pre_tool_call_returns_none_for_other_tools_with_a_broken_service"
        status: pass
      - kind: unit
        ref: "tests/test_hooks.py#test_hook_returns_only_block_or_none"
        status: pass
    human_judgment: false
  - id: D5
    description: "post_compaction forwards both ids to the resolver, does no I/O for a blank old id, and never raises"
    requirement: "AGNT-03"
    verification:
      - kind: unit
        ref: "tests/test_hooks.py#test_post_compaction_forwards_both_ids"
        status: pass
    human_judgment: false
  - id: D6
    description: "Whether a real model asks Theo in chat after a block, then retries with confirmed true"
    requirement: "AGNT-03"
    verification: []
    human_judgment: true
    rationale: "Needs a real model in the real agent loop. The live test in plan 02-05 measures it (T-02-07 accepts the flag as a forcing function)."
---

# Phase 2 Plan 02: board_edit argument parser and guard hooks Summary

One stdlib parser reads both the raw arguments the `pre_tool_call` hook sees and the coerced arguments the handler sees. A pure guard rule and two hook callbacks block a remove, an uncheck or a reword of Theo's item until `confirmed` is true, and never touch another tool.

## Performance

- Duration: about 20 min
- Completed: 2026-10-31
- Tasks: 2 of 2
- Files: 6 created, 0 modified
- Commits: 4 (two test, two feat)

## Accomplishments

- Task 1: `edit_args.parse` with `MAX_OPS`, `OP_FIELDS`, `EditArgsError` and `ParsedEdit`. It accepts JSON-string ops, a bare op object, JSON-string op elements, digit strings, and true or false strings in any letter case. It names the op index in each per-op error. It requires `base_rev` when an op targets an existing item.
- Task 2: `guard.py` (D-18, D-19) and `hooks.py`. The hook parses raw args with the same parser, blocks unreadable arguments, skips all I/O when the call is confirmed or holds no candidate op, and reads the board only for a `set_text` op. The `post_compaction` hook forwards both ids to `SessionResolver.record_compaction`.
- Plan 02-04 can register both hooks and call `edit_args.parse` from the handler with no change to these modules.

## TDD record

### Task 1

- RED: `uv run pytest tests/test_edit_args.py -q` gave `1 error in 0.20s`: `ModuleNotFoundError: No module named 'session_tasks.edit_args'`. Commit 83e43b2.
- Semantic assessment of RED: the plan names a failure at import as the expected RED, because the module did not exist. No test body ran. `gsd_run check tdd-red-evidence` does not read pytest text reports, so I recorded the real command output and did not run the classifier.
- GREEN: `uv run pytest tests/test_edit_args.py -q` gave 55 passed. Commit 9c5585d.
- REFACTOR: none. A pyright fix (`Sequence[object]` return type) and a format fix landed before the GREEN commit.

### Task 2

- RED: `uv run pytest tests/test_guard.py tests/test_hooks.py -q` gave `2 errors`: `ModuleNotFoundError: No module named 'session_tasks.guard'`. Commit a4be304. Same semantic assessment as Task 1.
- GREEN: 46 tests pass in the two files (101 across the three new files). Commit afc05a6.
- REFACTOR: none.

## Verification

- `uv run pytest tests/test_edit_args.py tests/test_guard.py tests/test_hooks.py tests/test_layout.py -q`: pass (101 tests in the three new files; the guard, hook and layout files together give 72).
- `./scripts/check.sh`: `check: python 3.11 ok`, `check: python 3.14 ok`, `check: all ok`. 339 tests pass on each Python. Coverage TOTAL 97.48 percent on 3.11. No "real Hermes home gained" output.
- Acceptance greps: `MAX_OPS = 100`, `class EditArgsError(BoardError)`, `MappingProxyType`, `def guarded_reasons`, `def make_pre_tool_call`, `record_compaction(`, `Theo must answer first for: ` all present.
- Commit order check: the oldest 02-02 commit is `test(02-02)`.

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0.

## Known Stubs

None.

## Threat Flags

None. The plan threat model covers the hook trust boundary (T-02-04, T-02-05, T-02-06, T-02-08, T-02-09). T-02-07 stays accepted: the `confirmed` flag is a forcing function, not a security boundary.

## Next Phase Readiness

Plan 02-04 registers `make_pre_tool_call(store, resolver)` and `make_post_compaction(resolver)` and calls `edit_args.parse` from the `board_edit` handler. Plan 02-03 has no file in common with this plan.

## Self-Check: PASSED

- Files found: edit_args.py, guard.py, hooks.py, test_edit_args.py, test_guard.py, test_hooks.py.
- Commits found in HEAD ancestry: 83e43b2, 9c5585d, a4be304, afc05a6.
