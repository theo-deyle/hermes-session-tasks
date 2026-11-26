---
phase: 05-agent-sees-theo-s-edits
plan: 03
subsystem: agent-tools
tags: [board_read, board_edit, agent_seen_rev, pre_llm_call, compose_user_api_content, pytest]
status: complete

requires:
  - phase: 05-agent-sees-theo-s-edits
    provides: BoardStore.mark_seen, BoardStore.unseen_changes, delta.py and the pre_llm_call hook (plan 05-01)
provides:
  - seen marks in board_read and in the stale or not-found reply of board_edit, with a fault guard
  - tests/hermes_snippet_setup.py, the shared setup of the gateway venv snippets
  - the 30-turn token test without the model, run through Hermes's own hook dispatch and message composer
affects: [05-04, 05-05, 05-06, 05-07]

actuals:
  tokens: 4409
  tasks: 3
  commits: 5
plan_head_before: 4a3e0d3a6f0d06f75891c9f0e74f8f66fc250c0e
plan_head_after: 502e11f6ff39e1b4e15723316e7746dcbe94adfa
commits: 5

tech-stack:
  added: []
  patterns:
    - a result that carries the whole board marks the board seen at the rev of that result
    - a seen mark fault logs one warning and never changes the tool result
    - a gateway venv snippet puts its own directory on sys.path and shares setup helpers

key-files:
  created:
    - tests/hermes_snippet_setup.py
    - tests/hermes_thirty_turn_snippet.py
    - tests/test_hermes_thirty_turn.py
  modified:
    - plugin/session_tasks/board_tools.py
    - tests/test_pre_llm_hook.py
    - tests/test_board_tools.py

key-decisions:
  - "RESEARCH correction of the CONTEXT line on seen: board_read and a stale or not-found reply mark seen, because they carry the whole board. An applied board_edit result carries only the agent's own items, so it marks seen only through the conditional advance of plan 05-01. A delegate never marks seen."
  - "The new snippet imports shared setup from tests/hermes_snippet_setup.py. tests/hermes_dispatch_snippet.py stays unchanged, as the plan says."

requirements-completed: [AGNT-05]

coverage:
  - id: D1
    description: "After the agent reads the board, the next turn carries no note about changes that read showed."
    requirement: AGNT-05
    verification:
      - kind: integration
        ref: "tests/test_pre_llm_hook.py#test_board_read_by_the_agent_clears_the_note"
        status: pass
      - kind: unit
        ref: "tests/test_board_tools.py#test_read_marks_the_board_seen_at_its_rev"
        status: pass
    human_judgment: false
  - id: D2
    description: "A delegate read marks nothing, a stale or not-found reply marks the board rev, an applied edit after a Theo change keeps seen, and a failing mark still returns the board."
    requirement: AGNT-05
    verification:
      - kind: unit
        ref: "tests/test_board_tools.py#test_delegate_read_does_not_mark_seen"
        status: pass
      - kind: unit
        ref: "tests/test_board_tools.py#test_stale_reply_marks_seen_at_the_board_rev"
        status: pass
      - kind: unit
        ref: "tests/test_board_tools.py#test_not_found_reply_marks_seen"
        status: pass
      - kind: unit
        ref: "tests/test_board_tools.py#test_applied_edit_after_a_theo_change_keeps_seen"
        status: pass
      - kind: unit
        ref: "tests/test_board_tools.py#test_a_failing_seen_mark_still_returns_the_board"
        status: pass
    human_judgment: false
  - id: D3
    description: "Through Hermes's own hook dispatch and composer, 30 turns add exactly the notes (turns 5, 12, 20 and the pointer line on turn 25) and nothing on a quiet turn."
    requirement: AGNT-05
    verification:
      - kind: integration
        ref: "tests/test_hermes_thirty_turn.py#test_thirty_turns_add_exactly_the_notes"
        status: pass
      - kind: integration
        ref: "tests/test_hermes_thirty_turn.py#test_notes_only_follow_theo_edits"
        status: pass
      - kind: integration
        ref: "tests/test_hermes_thirty_turn.py#test_quiet_arm_adds_nothing_on_every_turn"
        status: pass
      - kind: integration
        ref: "tests/test_hermes_thirty_turn.py#test_every_note_is_within_the_cap"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-02
---

# Phase 5 Plan 03: Seen marks and the 30-turn token test Summary

**The agent's own board read and its stale or not-found reply now count as seen, and a 30-turn session through Hermes's real hook dispatch and message composer adds exactly the size of Theo's notes and nothing on quiet turns.**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-11-02T13:56Z
- **Tasks:** 3
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments

- `board_tools.py`: `_mark_seen` calls `BoardStore.mark_seen` inside a guard that logs one WARNING from `session_tasks.board_tools`. `board_read` marks at the rev of the board it returns, except for a delegate. The stale and not-found branch of `board_edit` marks at `result.board.rev`.
- Seen edges are tested: delegate read, stale reply, not-found reply, applied edit after a Theo change, failing mark.
- `tests/hermes_snippet_setup.py` holds `link_and_enable(home, plugin_dir)` and `stub_gateway_server(record)`.
- The 30-turn token test without the model runs two boards (edits and quiet) through `invoke_hook("pre_llm_call")` and `compose_user_api_content`. Notes land on turns 5, 12 and 20, and a pointer line lands on turn 25 after a forced journal gap. Every note is at most 1000 characters. The characters added in the edits arm minus the quiet arm equal the sum of (note length + 2).

## RED evidence

- Task 1 RED: `test_board_read_by_the_agent_clears_the_note` failed on its assertion. The next hook call returned the fenced note with `checked #1` instead of None. Commit `9f70f0c` is the first 05-03 commit.
- Task 2 RED: `test_stale_reply_marks_seen_at_the_board_rev` and `test_not_found_reply_marks_seen` failed on their assertions (seen stayed 1, board rev was 2). The other four tests passed already, because Task 1 built the read mark and the guard.
- Task 3 has no RED: the plan marks it `type="auto"` without TDD, and the five tests passed on the first run.

## Task Commits

1. Task 1 RED: `9f70f0c` test(05-03): add failing test that a board read clears the note
2. Task 1 GREEN: `a01b880` feat(05-03): mark the board seen when the agent reads it
3. Task 2 RED: `5094d6d` test(05-03): add seen edge tests for the tool handlers
4. Task 2 GREEN: `b4d2d75` feat(05-03): mark seen on a stale or not-found reply
5. Task 3: `502e11f` test(05-03): add the 30-turn character contract through Hermes

## TDD Gate Compliance

The first 05-03 commit is a test commit. Each GREEN commit follows its RED commit. The tracer feedback gate (Task 1) re-ran its verify in auto mode and passed before Task 2 began.

## Files Created/Modified

- `plugin/session_tasks/board_tools.py` - `_mark_seen`, the mark in `board_read` and in the stale branch
- `tests/test_pre_llm_hook.py` - the end to end read test
- `tests/test_board_tools.py` - `seen` helper and six edge tests
- `tests/hermes_snippet_setup.py` - shared setup for gateway venv snippets
- `tests/hermes_thirty_turn_snippet.py` - the 30-turn script, one JSON line
- `tests/test_hermes_thirty_turn.py` - five hermes-marked tests

## Decisions Made

RESEARCH correction of the CONTEXT line, as the plan records: CONTEXT says every `board_read` and `board_edit` by the agent marks the board seen. This plan marks seen on `board_read` and on a stale or not-found reply, because those results carry the whole board. An applied `board_edit` result carries only the agent's own items, so it marks seen only through the conditional advance of plan 05-01. A delegate never marks seen.

## Deviations from Plan

None - plan executed exactly as written. The item ids matched the plan (#3 Call John, #4 Book the van), so the tests assert the ids from the plan and no id-by-text fallback was needed. The snippet still reads ids by text from the board for the Theo edits.

## Issues Encountered

None. `./scripts/check.sh` ended with `check: all ok`: 813 passed on Python 3.11 with 97.61 percent coverage, and 813 passed on Python 3.14. No `home_guard` failure occurred.

## Verification

- `uv run pytest tests/test_hermes_thirty_turn.py -q -rs -m hermes`: 5 passed, 0 skipped.
- `uv run pytest tests/test_board_tools.py tests/test_pre_llm_hook.py tests/test_store_seen.py -q -rs`: 68 passed.
- `grep -n "_mark_seen" plugin/session_tasks/board_tools.py`: 2 lines. `grep -n "result.board.rev" plugin/session_tasks/board_tools.py`: 1 line. `grep -n "compose_user_api_content" tests/hermes_thirty_turn_snippet.py`: matches (the real composer).
- Order check on `git log`: the first 05-03 commit is a `test(05-03)` commit.

## Known Stubs

None.

## Threat Flags

None. T-05-09, T-05-10 and T-05-11 are mitigated: delegate guard with its test, `try/except` with one warning and its test, and the mark uses the rev of the board the tool returned with a monotonic store mark.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plans 05-04 and later can reuse `tests/hermes_snippet_setup.py` for new gateway venv snippets.

## Self-Check: PASSED

All six files exist. Commits `9f70f0c`, `a01b880`, `5094d6d`, `b4d2d75` and `502e11f` are ancestors of HEAD.

---
*Phase: 05-agent-sees-theo-s-edits*
*Completed: 2026-11-02*
