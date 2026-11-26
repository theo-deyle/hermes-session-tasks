---
phase: 06-cross-session-boards
plan: 01
subsystem: storage
tags: [sqlite, copy, board-store, journal]
status: complete

requires:
  - phase: 05-agent-sees-theo-s-edits
    provides: agent_seen_rev advance rule in _apply, delta note over the journal
provides:
  - BoardStore.copy_items, one write transaction copy between two boards
  - copy_plan.plan_copy, the pure rules of D-40 to D-42
  - ChangeOp copied, CopyApplied, NoSourceBoard, SameBoard
affects: [06-05 board_copy tool, 06-09 POST /board/copy route]

actuals:
  tokens: 6300
  tasks: 2
  commits: 4

plan_head_before: 995b4414213c9df049e2b7fd8a369998d156a390
plan_head_after: 1961435c9d9ea6d2f3d02fbc316012695a68aaf4
commits: 4

tech-stack:
  added: []
  patterns:
    - "after_ops hook on _apply: extra journal rows share the batch rev and the prune"
    - "pure plan module (plan_copy) like plan_import: groups, skip set, capacity cut"

key-files:
  created:
    - plugin/session_tasks/copy_plan.py
    - tests/test_copy_plan.py
    - tests/test_store_copy.py
  modified:
    - plugin/session_tasks/model.py
    - plugin/session_tasks/store.py

key-decisions:
  - "A1: a skipped parent skips its subtasks and counts each one"
  - "A2: a text planned earlier in the batch counts as open"
  - "A3: in all open, an open subtask of a checked parent copies as a top-level item"
  - "A4: an unknown id in item_ids returns Stale not_found and writes nothing"
  - "A10: one copied journal row per copied item, add rows stay"
  - "SameBoard is raised in the store as well as in callers"

requirements-completed: [TOOL-05, PANE-10]
---

# Phase 6 Plan 01: Board copy in the store Summary

One `BoardStore.copy_items` call copies chosen or all open items from another board into the caller's board in a single BEGIN IMMEDIATE transaction, with pure rules in `copy_plan.py` and a `copied` journal row that names the source.

## Accomplishments

- `copy_items(target_root, source_root, item_ids, *, actor)` returns `CopyApplied` (copied, skipped, overflow) or `Stale`. The source is only read.
- `plan_copy` selects items, skips texts already open on the target, and cuts at the capacity (100 minus every target item) without orphaning a subtask.
- `_apply` gained `after_ops`; `_provenance` writes one `copied` row per op (text `<source_root>#<source_item_id>`) at the batch rev, so `summary_line` counts adds only and `change_line` returns None for the row.
- An empty plan writes no row and keeps the target rev.

## Task Commits

| Task | Commit | Type |
|------|--------|------|
| 1 RED | 0c5278c | test(06-01): add failing end to end test for a board copy |
| 1 GREEN | 34ac90e | feat(06-01): copy items from another board in one write transaction |
| 2 RED | 8a3b100 | test(06-01): add copy rule, cap and guard tests |
| 2 GREEN | 1961435 | feat(06-01): copy rules for subtasks, chosen ids, skips and the cap |

## TDD evidence

- Task 1 red line: `ImportError: cannot import name 'CopyApplied' from 'session_tasks.model'` (1 error during collection).
- Task 2 red line: `15 failed, 16 passed` for the two new modules against the one-path `plan_copy` from task 1.
- Green: `31 passed` for the two new modules on Python 3.11 (uv project env) and on Python 3.14 (isolated uv env).

## Verification

- `uv run pytest` over copy_plan, store_copy, store_seen, delta, store_items, store_subtasks, markdown and layout tests: 152 passed.
- `ruff check`, `ruff format --check` and `pyright` on the five files: clean.
- `store.py` is 373 lines; `SCHEMA_VERSION` unchanged; `copy_plan.py` imports only `collections.abc`, `dataclasses` and `.model`.
- `./scripts/check.sh` was not run here: the plan assigns it to the executor that finishes wave 1 last.

## Assumptions (planner decisions, built as stated; Theo can change each)

A1 skipped parent skips and counts its subtasks. A2 same-batch duplicate text counts as open. A3 open subtask of a checked parent copies top-level. A4 unknown id rolls back and names the id. A10 one `copied` row per item (a 100 item copy writes 200 journal rows, the prune keeps 100, the Phase 5 pointer line covers the gap).

## Deviations from Plan

None - plan executed as written. Notes:

- Task 2 RED was reached by restoring the task 1 one-path `copy_plan.py` before the test commit, then restoring the full rules for the GREEN commit, so the test commit landed with real failures.
- Extra tests beyond the list: an agent copy while the agent is behind leaves `agent_seen_rev` alone, and a parent that does not fit takes its subtasks into overflow.
- A kid of a parent that is cut by the cap counts as skipped when its own text is already open, else as overflow (a plan detail the text left open).

## Known Stubs

None.

## Threat Flags

None. T-6-01 to T-6-03 are covered by the tests named in the plan.

## Self-Check: PASSED

All five files exist; commits 0c5278c, 34ac90e, 8a3b100 and 1961435 are ancestors of HEAD.
