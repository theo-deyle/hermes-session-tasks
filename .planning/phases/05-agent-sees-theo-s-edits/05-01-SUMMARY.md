---
phase: 05-agent-sees-theo-s-edits
plan: 01
subsystem: agent-hooks
tags: [pre_llm_call, delta-note, sqlite, agent_seen_rev, pytest]
status: complete

requires:
  - phase: 02-board-store-and-agent-tools
    provides: the changes journal, agent_seen_rev column, BoardStore and the pre_llm_call hook shell
provides:
  - delta.py, the pure builder of the fenced note of Theo's board changes
  - BoardStore.unseen_changes and BoardStore.mark_seen, plus the conditional seen advance of an agent batch
  - a pre_llm_call hook that returns the note, the pointer line or None
affects: [05-02, 05-03, 05-04, 05-05, 05-06, 05-07]

actuals:
  tokens: 8470
  tasks: 3
  commits: 5
plan_head_before: 74507649698b386f344209eaf13ac38d9a40f77d
plan_head_after: 7b73c786bd34bb46832e86fd9b667a4ba2f4b8cd
commits: 5

tech-stack:
  added: []
  patterns:
    - one read snapshot for the unseen read, one short write for the seen mark
    - monotonic seen mark and conditional seen advance in the same write transaction as the batch
    - the mark runs after the note is built, so a format fault loses no change

key-files:
  created:
    - plugin/session_tasks/delta.py
    - tests/test_delta.py
    - tests/test_store_seen.py
  modified:
    - plugin/session_tasks/rows.py
    - plugin/session_tasks/store.py
    - plugin/session_tasks/hooks.py
    - tests/test_pre_llm_hook.py
    - tests/test_register.py
    - tests/test_hermes_dispatch.py
    - tests/hermes_dispatch_snippet.py
  deleted:
    - plugin/session_tasks/nudge.py

key-decisions:
  - "Seen advance on board_edit: an applied agent batch advances agent_seen_rev only when the agent was up to date before the batch (RESEARCH correction of the CONTEXT line)."
  - "Journal gap rule: covered when count < JOURNAL_KEEP or oldest_rev <= agent_seen_rev (RESEARCH correction of the CONTEXT line)."
  - "nudge.py is deleted in this plan. tool_text.NUDGE_LINE and its tests stay until the own-plan gate result is known."
  - "When the journal does not cover the gap, the hook sends the pointer line even when no Theo row is visible."

requirements-completed: [AGNT-05]

coverage:
  - id: D1
    description: "A Theo change in the pane reaches the agent's next turn as one fenced note line, and the turn after it is quiet."
    requirement: AGNT-05
    verification:
      - kind: integration
        ref: "tests/test_pre_llm_hook.py#test_a_theo_edit_in_the_pane_reaches_the_next_turn_once"
        status: pass
      - kind: integration
        ref: "tests/test_hermes_dispatch.py#test_hermes_runs_pre_llm_call_and_gets_only_theo_changes"
        status: pass
    human_judgment: false
  - id: D2
    description: "The note holds at most 1000 characters; over the cap or over a journal gap it is one pointer line."
    requirement: AGNT-05
    verification:
      - kind: unit
        ref: "tests/test_delta.py#test_a_block_of_exactly_1000_characters_is_kept"
        status: pass
      - kind: unit
        ref: "tests/test_store_seen.py#test_exactly_100_rows_with_the_oldest_rev_one_above_seen_is_not_covered"
        status: pass
    human_judgment: false
  - id: D3
    description: "No seen mark hides a Theo change the agent was not shown, and agent text never returns as user-level content."
    requirement: AGNT-05
    verification:
      - kind: unit
        ref: "tests/test_store_seen.py#test_agent_edit_after_a_theo_edit_keeps_the_theo_change"
        status: pass
      - kind: unit
        ref: "tests/test_store_seen.py#test_agent_rows_are_left_out"
        status: pass
    human_judgment: false
  - id: D4
    description: "Item text cannot close the fence of the note."
    requirement: AGNT-05
    verification:
      - kind: unit
        ref: "tests/test_delta.py#test_text_cannot_close_the_fence"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-11-02
---

# Phase 5 Plan 01: Note of Theo's board changes Summary

**The pre_llm_call hook now sends only Theo's changes since the agent last saw the board, as a fenced note of at most 1000 characters or one pointer line, and a quiet turn gets nothing.**

## Performance

- **Duration:** about 40 min (the start time was not recorded)
- **Completed:** 2026-11-02T13:05Z
- **Tasks:** 3
- **Files modified:** 11 plus 1 deleted

## Accomplishments

- `delta.py`: pure builder. Five ops give five line shapes, a forked row gives no line, every `<` becomes `&lt;`, and the block is capped at 1000 characters.
- `rows.py` and `store.py`: `Unseen`, `read_seen`, `read_user_changes_after`, `journal_span`, monotonic `mark_seen`, conditional `advance_seen`, `BoardStore.unseen_changes` and `BoardStore.mark_seen`.
- `hooks.py`: the hook reads the unseen changes, builds the note, then marks the board seen. It still returns None for a blank id and a delegate, and logs one warning on a fault.
- The Phase 3 board block is gone: `nudge.py` is deleted. The register test and the real Hermes dispatch test pin the new contract.

## RED evidence

- Task 1 RED line: `ImportError: cannot import name 'delta' from 'session_tasks'` while collecting `tests/test_pre_llm_hook.py`. The plan names this import failure as the red state (module not yet written). Strictly this is a load failure, not an assertion failure. The semantic assessment: the target test `test_a_theo_edit_in_the_pane_reaches_the_next_turn_once` could not run, so the red proves only that the module was missing. The green run then passed the same test on its assertions.
- Task 2 RED: 8 tests failed on assertions (4 in `tests/test_delta.py` for the pointer line and the cap, 4 in `tests/test_store_seen.py` for the seen advance), 15 passed. Each failure was the planned behavior missing.

## Task Commits

1. Task 1 RED: `9613472` test(05-01): add failing end to end test for the note of Theo's changes
2. Task 1 GREEN: `bcfd63d` feat(05-01): inject only Theo's changes since the agent last saw the board
3. Task 2 RED: `ac0d321` test(05-01): add note cap, gap and seen rules tests
4. Task 2 GREEN: `c2e2f52` feat(05-01): cap the note and keep unseen Theo changes after an agent edit
5. Task 3: `7b73c78` refactor(05-01): retire the Phase 3 board block and update the turn contracts

## TDD Gate Compliance

The first 05-01 commit is a test commit. Each GREEN commit follows its RED commit.

## Decisions Made

1. RESEARCH correction 1, built as planned: an applied agent batch advances `agent_seen_rev` only when it equalled the rev before the batch. Test: `test_agent_edit_after_a_theo_edit_keeps_the_theo_change`.
2. RESEARCH correction 2, built as planned: the gap rule is `count < JOURNAL_KEEP or oldest_rev <= agent_seen_rev`. Tests: the two `100_rows` tests pin the boundary.
3. Planner decision: `nudge.py` is deleted here. `tool_text.NUDGE_LINE` and `tests/test_tool_text.py` stay until the own-plan gate result is known.
4. Planner decision on D-35 wording: an uncovered gap gives the pointer line even when no Theo row is visible, because the pruned rows can hold Theo's changes.

## Known effect after deploy

Boards written before this phase have `agent_seen_rev` 0. The first turn on such a board sends Theo's journaled changes once, or the pointer line, then marks the board seen.

## Deviations from Plan

None - plan executed exactly as written.

In `tests/test_pre_llm_hook.py`, `test_quiet_turn_returns_none_and_marks_nothing` makes one hook call before it installs the mark recorder. In Task 1 an agent-only board is still unseen on the first call, because the seen advance in `_apply` arrives in Task 2, so the first call marks it seen. The behavior text allows this ("after the agent add and one hook call, a second hook call ...").

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The new reads and writes stay inside the existing plugin data file, and the threat register mitigations T-05-01 to T-05-05 are covered by `test_text_cannot_close_the_fence`, `test_agent_rows_are_left_out`, the fault tests, `test_delegate_session_returns_none` and the seen tests.

## Verification

- `./scripts/check.sh` ended with `check: all ok` (Python 3.11: 763 passed, coverage 97.59 percent; Python 3.14: 763 passed).
- `uv run pytest tests/test_pre_llm_hook.py tests/test_delta.py tests/test_store_seen.py tests/test_register.py tests/test_hermes_dispatch.py tests/test_tool_text.py -q -rs`: 115 passed, 0 skipped.
- `grep -n "NUDGE_LINE =" plugin/session_tasks/tool_text.py` still prints one line.

## Next Phase Readiness

Ready for 05-02.

## Self-Check: PASSED

- Files found: `plugin/session_tasks/delta.py`, `tests/test_delta.py`, `tests/test_store_seen.py`. `plugin/session_tasks/nudge.py` is deleted.
- Commits found in HEAD: 9613472, bcfd63d, ac0d321, c2e2f52, 7b73c78.
