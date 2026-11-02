---
phase: 06-cross-session-boards
plan: 09
subsystem: rest-api
tags: [board_copy, rest-route, copy, pane, stale-shape]
status: complete

requires:
  - phase: 06-cross-session-boards
    provides: BoardStore.copy_items (06-01), copy_args.parse (06-02), results.DELEGATE_COPY and source_missing_text (06-05)
provides:
  - POST /board/copy route with CopyBody (PANE-10 backend, D-46)
  - BoardApi.copy, _copied_reply, optional message of _stale_reply
affects: [06-11 pane copy action, 06-12 live test]

actuals:
  tokens: 5300
  tasks: 2
  commits: 3

plan_head_before: 81acf02578155b033665c505868aed8d8f740934
plan_head_after: 843b5eb4b278d4946ea31eeb498c636908e1c2a5
commits: 3

tech-stack:
  added: []
  patterns:
    - "route handler is a plain def that only maps ApiReply to JSONResponse; BoardApi.copy holds every check"
    - "check order as board_copy: resolve target, delegate, parse, resolve source, same root, store call, listener guard"

key-files:
  created:
    - tests/test_api_copy.py
  modified:
    - plugin/session_tasks/board_api.py
    - plugin/dashboard/plugin_api.py

key-decisions:
  - "The Task 1 code already held every guard of the plan's Task 2 list, so the Task 2 tests passed on first run and Task 2 needed no code commit (same as 06-05)"

requirements-completed: [PANE-10]
---

# Phase 6 Plan 09: Copy route Summary

`POST /board/copy` copies chosen or all open items from another session's board into the focused board as actor user, with the `/board/edit` rule that an unknown body field gives 422 and the `/board/edit` stale reply shape.

## Accomplishments

- `CopyBody` takes exactly `session_id`, `from_session_id`, optional `item_ids` and optional strict-integer `base_rev`. `extra="forbid"` refuses any other field; both ids are 1 to 256 characters.
- `BoardApi.copy` replies `ok` true with the `_applied_reply` keys plus `copied`, `skipped` and `overflow`. A blank target gives 400 `no_session`. A delegate target, a same-root source, a source with no board and bad `item_ids` give 200 `invalid` with a fixed `message`. A missing source item gives the stale shape with `reason` `not_found`, the source-missing message and the target board.
- The listener fires once with the target root, only when the copy changed the target. A listener fault logs one WARNING from `session_tasks.board_api` and the reply stays ok.
- The source board is never written. A delegate target writes nothing.
- 17 tests in `tests/test_api_copy.py` (14 test functions, parametrized). They pass on Python 3.11 (uv project env) and on Python 3.14 (`.venv-py3.14`: test_api_copy, test_layout).

## Task Commits

| Task | Commit | Type |
|------|--------|------|
| 1 RED | 2f0bc31 | test(06-09): add failing end to end test for the copy route |
| 1 GREEN | bf31780 | feat(06-09): POST /board/copy for the pane |
| 2 RED | 843b5eb | test(06-09): add copy route rule tests |

Task 2 GREEN: no code commit. The route and `BoardApi.copy` from Task 1 already passed every rule test.

## TDD evidence

- Task 1 red line: `assert 404 == 200` (route missing).
- Task 2: all 17 tests passed on first run; the rules are in the Task 1 code because it follows the full `board_copy` check order.

## Verification

- `uv run pytest tests/test_api_copy.py tests/test_api.py tests/test_events.py tests/test_layout.py -q -rs`: 98 passed, 0 skipped.
- `ruff check`, `ruff format --check` and `pyright` on the three files: clean.
- `grep -c "^def test_" tests/test_api_copy.py` prints 14; `grep -c 'extra="forbid"' plugin/dashboard/plugin_api.py` prints 2.
- `./scripts/check.sh` was not run here: the orchestrator runs the wave gate.
- The first 06-09 commit is a test commit.

## Deviations from Plan

None - plan executed as written. One note: the Task 1 GREEN step already contained the full Task 2 logic, so Task 2 has a test commit only.

## Known Stubs

None.

## Threat Flags

None. T-6-27 (extra field, long id and bad id tests), T-6-28 (delegate test) and T-6-29 (stale shape message test) are covered by the tests named in the plan.

## Self-Check: PASSED

tests/test_api_copy.py, board_api.py and plugin_api.py exist; commits 2f0bc31, bf31780 and 843b5eb are ancestors of HEAD.
