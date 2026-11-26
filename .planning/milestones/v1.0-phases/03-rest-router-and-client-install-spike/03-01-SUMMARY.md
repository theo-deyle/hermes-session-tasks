---
phase: 03-rest-router-and-client-install-spike
plan: 01
subsystem: agent-hooks
tags: [hermes-plugin, pre_llm_call, nudge, board-block, own-job-harness, pytest]
status: complete

requires:
  - phase: 01-core-storage-and-session-identity
    provides: BoardStore, SessionResolver, markdown.render, model.Board
  - phase: 02-agent-tools-and-skill
    provides: hooks factory style, wiring.register, FakeCtx, Hermes dispatch snippet
provides:
  - tool_text.NUDGE_LINE (round 1 wording)
  - nudge.py with board_block and turn_context (fenced, escaped, capped)
  - hooks.make_pre_llm_call, registered in wiring.py and listed in plugin.yaml
  - pre_llm_call proven through the real Hermes plugin manager in the gateway venv
  - tests/live/own_job with the six-step prompt, a runner and an analyzer with a tested pass rule
affects: [03-07, 03-12, phase-05]

actuals:
  tokens: 8960
  tasks: 3
  commits: 6
plan_head_before: 58b44d8b09eb63bd0d9173271563498ed8d547d1
plan_head_after: 7c8dc98a829ce4a0a67bae8de5b1024e08d91ac4

tech-stack:
  added: []
  patterns:
    - "Turn text = static nudge line, then a fenced data block that says it holds notes, not instructions"
    - "Item lines escape every < as &lt; so no item can close the fence"
    - "Cap keeps a prefix of whole lines and ends with 'N more items, call board_read'"
    - "The hook checks a blank session id before any resolve, then wraps the rest in try/except and logs a warning"

key-files:
  created:
    - plugin/session_tasks/nudge.py
    - tests/test_pre_llm_hook.py
    - tests/test_own_job_analyze.py
    - tests/live/own_job/job.txt
    - tests/live/own_job/run.sh
    - tests/live/own_job/analyze.py
  modified:
    - plugin/session_tasks/tool_text.py
    - plugin/session_tasks/hooks.py
    - plugin/session_tasks/wiring.py
    - plugin/plugin.yaml
    - tests/test_register.py
    - tests/hermes_dispatch_snippet.py
    - tests/test_hermes_dispatch.py
    - tests/test_tool_text.py

key-decisions:
  - "The nudge line is static text with the single digit 3, so the prompt cache stays stable"
  - "Escape only item lines, never the fence lines; the cap counts item lines only, the notice line is extra"
  - "tests/test_pre_llm_hook.py defines its own broken_store and broken_resolver fixtures instead of importing from test_hooks.py"
  - "analyze.py counts a check only after the first board_edit call that carries 2 or more add ops"

requirements-completed: [AGNT-01]

coverage:
  - id: D1
    description: "Hermes loads plugin/ and pre_llm_call returns the nudge line plus the board with ids for a seeded session, and nothing for a blank session"
    requirement: "AGNT-01"
    verification:
      - kind: integration
        ref: "tests/test_hermes_dispatch.py#test_hermes_runs_pre_llm_call_and_gets_the_nudge_and_the_board"
        status: pass
      - kind: unit
        ref: "tests/test_register.py#test_registered_pre_llm_call_returns_the_nudge_and_the_board"
        status: pass
    human_judgment: false
  - id: D2
    description: "Board block edge rules: empty board, equal texts, display order, fence escape, 2000 character cap, blank and delegate sessions, store and resolver faults"
    requirement: "AGNT-01"
    verification:
      - kind: unit
        ref: "tests/test_pre_llm_hook.py (13 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The own-job harness is tracked and its pass rule is unit tested"
    requirement: "AGNT-01"
    verification:
      - kind: unit
        ref: "tests/test_own_job_analyze.py (16 tests)"
        status: pass
      - kind: other
        ref: ".venv-py3.14/bin/python -I tests/live/own_job/analyze.py --out <phase 2 live-gap-ownjob2> own-1 (0 board_edit calls, pass false)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The nudge wording makes the agent put its own steps on the board in 3 of 3 live runs"
    requirement: "AGNT-01"
    verification: []
    human_judgment: true
    rationale: "This plan only builds the hook and the harness. The live runs and the measured wording belong to plan 03-07."

duration: 9min
completed: 2026-11-01
---

# Phase 3 Plan 01: pre_llm_call nudge and own-job harness Summary

**A `pre_llm_call` hook that adds a static nudge line and a fenced, escaped, capped board block to each non-delegate turn, proven through the real Hermes plugin manager, plus a tracked own-job runner and analyzer with a unit-tested three-part pass rule.**

## Performance

- **Duration:** about 9 min (04:05Z to 04:14Z)
- **Tasks:** 3 of 3
- **Files:** 6 created, 8 modified (14 touched, as the plan stated)
- **Commits:** 6 (3 test commits, 3 feature commits)

## Accomplishments

- Task 1 (tracer): `tool_text.NUDGE_LINE`, `nudge.turn_context`, `hooks.make_pre_llm_call`, the `wiring.py` registration and the `plugin.yaml` line. The Hermes dispatch test fires `pre_llm_call` through `hermes_cli.plugins.invoke_hook` and gets exactly one str that starts with the nudge line and holds `- [ ] #1 Call John`. A blank session gives no str.
- Task 2: item lines escape `<` as `&lt;`. Item lines keep a prefix of whole lines within 2000 characters, then one line `N more items, call board_read`. A full board of 100 items with 450 characters each stays at or below 2600 characters of hook output.
- Task 3: `tests/live/own_job/` holds `job.txt` (byte identical to the Phase 2 copy), `run.sh` (needs `OWN_JOB_OUT`) and `analyze.py` (opens the data file with `mode=ro`).

## Verification Evidence

- Red summary line for Task 1 (commit 0d7f38e): `2 failed, 8 passed in 0.65s` from `uv run pytest tests/test_register.py -q`.
- Task 1 green: `uv run pytest tests/test_register.py -q` gave `10 passed`.
- `uv run pytest -m hermes tests/test_hermes_dispatch.py -q -rs` gave `3 passed`, 0 skipped, no "real Hermes home gained" line.
- `hermes plugins validate <plugin>` printed "declared hooks - matches registrations" and "Validation passed."
- `hermes plugins doctor <plugin> --ci` exited 0: "2 tool(s), 3 hook(s)".
- Commit order check exited 0: the oldest 03-01 commit is `test(03-01)`.
- Task 2: `uv run pytest tests/test_pre_llm_hook.py tests/test_tool_text.py tests/test_hooks.py tests/test_layout.py -q` gave `142 passed`; `tests/test_pre_llm_hook.py` alone gave `13 passed`.
- Task 3: `uv run pytest tests/test_own_job_analyze.py -q` gave `16 passed`. `bash -n run.sh` and the executable bit check passed.
- Own-job analyzer on the Phase 2 recording (`live-gap-ownjob2/own-1`, exit 1): `board_edit_calls` 0, `todo_list_calls` 0, `add_batches` 0, `pass` false, three reasons. This matches 02-VERIFICATION.
- Plan verification: the five test files gave `133 passed`. `./scripts/check.sh` ended with `check: python 3.14 ok` and `check: all ok` (494 passed).
- Tracer gate (auto mode): the tracer verify commands ran again after the Task 1 commit and passed. Log: tracer verified end to end, expanding.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test helper read the wrong field in the cap test**
- **Found during:** Task 2
- **Issue:** The red commit e4a69b8 held a test helper that split a kept item line at the wrong index, so the first-lines check failed for a test reason, not a code reason.
- **Fix:** Changed `split(" ", 3)[3]` to `split(" ", 4)[4]` and committed it with the green change.
- **Files modified:** tests/test_pre_llm_hook.py
- **Commit:** 69b112c

**2. [Plan text drift] Hermes dispatch test count**
- **Found during:** Task 1
- **Issue:** The plan acceptance line says `1 passed` for `uv run pytest -m hermes tests/test_hermes_dispatch.py`. The file already held 2 Hermes tests from Phase 2, so the new count is 3.
- **Fix:** None needed. The fail rule (no failure, no skip) holds.

**3. [Rule 3 - Blocking] zsh did not split `$F` in the lint command**
- **Found during:** Task 1
- **Issue:** The plan's `F="..."; ruff check $F` form fails in zsh because zsh does not split a variable on spaces.
- **Fix:** Ran the same commands inside `bash -c`. No file changed.

**Total deviations:** 1 auto-fixed bug (test helper), 1 plan text drift, 1 shell note. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. The new surface (turn text built from board items, a read-only analyzer) is in the plan's threat model as T-03-01 to T-03-04.

## Notes for Later Plans

- Plan 03-07: the nudge wording is round 1. Keep the properties that `tests/test_tool_text.py` checks (one line, at most 240 characters, names `board_edit` and `tool_search`, no digit but the `3`). Record the measured block sizes and turn counts, because Hermes can replay each injected block on later turns (Pitfall 6).
- Plan 03-12: the analyzer never writes. Deleting the test boards that live runs create waits for Theo's one-line go.
- No gateway restart happened in this plan. A new `hermes chat --oneshot` process loads the hook on its own. The Desktop backends load it at the announced restarts in plans 03-08 and 03-10.

## Self-Check: PASSED

- Created files exist: nudge.py, test_pre_llm_hook.py, test_own_job_analyze.py, job.txt, run.sh, analyze.py.
- Commits exist: 0d7f38e, c3cf1a2, e4a69b8, 69b112c, 78f2faa, 7c8dc98.
