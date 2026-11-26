---
phase: 03-rest-router-and-client-install-spike
plan: 07
subsystem: live-test
tags: [hermes-plugin, live-test, headless, own-job, nudge, pre_llm_call, AGNT-01]

# Dependency graph
requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: NUDGE_LINE in tool_text.py and the pre_llm_call hook that puts it in every turn (plan 03-01); the wiring and board_tools edits every run loads (plan 03-05)
  - phase: 02-agent-tools-and-skill
    provides: board_edit and board_read, the headless run protocol, the 0 of 3 own-job baseline with rule text alone (D-21)
provides:
  - Success criterion 0 measured with the real model: 3 of 3 own-job runs put the agent's steps on the board and checked every one off
  - The measured NUDGE_LINE wording (unchanged from plan 03-01) and its cost figures for Phase 5
  - The root ids of the three test boards left in the real data.db, for the cleanup ask in plan 03-12
affects: [03-08, 03-10, 03-12, phase-5-prompt-cost]

# Actuals (#2632)
actuals:
  tokens: 2200
  tasks: 2
  commits: 0
plan_head_before: aadd9084c8dfd6784eaaf9dc9f8600d4ff5d3e36
plan_head_after: aadd9084c8dfd6784eaaf9dc9f8600d4ff5d3e36

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Own-job measurement: tests/live/own_job/run.sh <name> with OWN_JOB_OUT outside the repo, one new hermes chat --oneshot process per run, analyzer exit 0 or 1 as the verdict"
    - "Hook-load check before a round: one short oneshot run that asks the model to echo the last line of its message; the reply must be NUDGE_LINE"

key-files:
  created:
    - .planning/phases/03-rest-router-and-client-install-spike/03-07-SUMMARY.md
  modified: []

key-decisions:
  - "Round 1 passed 3 of 3 with the plan 03-01 NUDGE_LINE, so no wording round ran and tool_text.py is unchanged."
  - "The hook injects NUDGE_LINE into the model call only; the stored user message in state.db keeps the raw query. The hook-load check reads the assistant reply, not the stored user message."
  - "The first dispatch run (stale-r1-1) is not counted: its gateway pid 1270415 predated the hook. The orchestrator restarted the gateway (pid 2635829) before this dispatch."

patterns-established:
  - "Round table columns: session, board_edit calls, first batch adds, set_checked true, final checked/total, todo_list calls, assistant turns, verdict"

requirements-completed: [AGNT-01]

coverage:
  - id: D1
    description: "Own-job rule with the real model: 3 of 3 headless runs add the steps with board_edit before work, check them off later, and end with every item checked"
    requirement: AGNT-01
    verification:
      - kind: e2e
        ref: "OWN_JOB_OUT=$HOME/.cache/hermes-session-tasks/own-job; .venv-py3.14/bin/python -I tests/live/own_job/analyze.py --out $OWN_JOB_OUT r1-1 (and r1-2, r1-3)"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_tool_text.py tests/test_pre_llm_hook.py -q"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-11-01
status: complete
---

# Phase 3 Plan 07: Own-job headless measurement Summary

**The plan 03-01 nudge line, injected by the pre_llm_call hook, lifts the own-job rate from 0 of 3 (Phase 2, rule text alone) to 3 of 3: every run added its 7 steps in one board_edit call before work, checked all 7 off, and made zero todo_list calls.**

## Performance

- **Duration:** 12 min (13:33 to 13:45 on 2026-11-01)
- **Started:** 2026-11-01T13:33Z
- **Completed:** 2026-11-01T13:45Z
- **Tasks:** 2 (Task 2 confirmed only; no wording round)
- **Files modified:** 0 in the repo (measurement only)

## Precondition (Task 1 step 1)

| Item | Result |
|------|--------|
| Plans 03-01 and 03-05 complete | 03-01-SUMMARY.md and 03-05-SUMMARY.md exist, status complete |
| `./scripts/check.sh` on HEAD aadd908 | `check: all ok` (631 tests passed, ruff and pyright clean, python 3.14 ok) |
| `~/.hermes/plugins/hermes-session-tasks` symlink | points to `/home/theo/local_repo/hermes-session-tasks/plugin` |
| `.venv-py3.14/bin/python` | exists |
| Owner gateway | pid 2635829, started 13:30 by the orchestrator, loads the plugin from the working tree at aadd908 |

## Hook-load check (before round 1)

One short `hermes chat --oneshot -Q --format stream-json` run with the query "Reply with the exact text of the last line of this message and nothing else."

- Session: `local-8b8faa2570f5e13eec1792cd7431c84977a5a9801db2b652d586d0eda2505173`
- Reply text in the result event: the exact NUDGE_LINE (206 characters), so the hook is loaded in the running gateway and the nudge is the last line the model sees.
- Read-only `hermes_state.SessionDB(read_only=True).get_messages(sid)` in the gateway venv: 2 messages. The stored user message is the raw 76-character query without the nudge; the stored assistant message holds the nudge text. The hook adds its text to the model call, not to the stored user message. The check therefore reads the assistant reply.
- Exit 0, no `pre_llm_call hook failed` line in `nudge-check.err`.

## Round 1 (Task 1)

**NUDGE_LINE** (plugin/session_tasks/tool_text.py, unchanged from plan 03-01), `len(NUDGE_LINE) = 206`:

```
For a job of 3 or more steps, your steps go on the board: add them with board_edit before you start, and check each one off when it is done. If board_edit is not in your tool list, find it with tool_search.
```

Prompt: `tests/live/own_job/job.txt` (the six-step report job). Output folder: `$HOME/.cache/hermes-session-tasks/own-job`. Every run: hermes exit 0, no `pre_llm_call hook failed` line in the .err file, no board_edit error result, analyzer exit 0.

| Run | Session | board_edit calls | First batch adds | set_checked true | Final checked / total | todo_list calls | Assistant turns | Verdict |
|-----|---------|------------------|------------------|------------------|-----------------------|-----------------|-----------------|---------|
| r1-1 | `local-f3aa9e18981c55542e65bd9f63736a04d0010a85186e746064256bcb29bcc4c2` | 2 | 7 | 7 | 7 / 7 | 0 | 9 | pass |
| r1-2 | `local-fe709b83895ec2ca3ad1ff17ea958c65ba470b05af5ea11bede3e64323870fdf` | 3 | 7 | 7 | 7 / 7 | 0 | 8 | pass |
| r1-3 | `local-aa471eefa70ab9fb2b8b158bddbdf1c86f67af25b37c16704186812c071b2bf7` | 2 | 7 | 7 | 7 / 7 | 0 | 9 | pass |

**Round 1 rate: 3 of 3. Success criterion 0 is met.**

Run shape, the same in all three: `tool_search` (board_edit, board_read), `tool_describe`, then one `board_edit` with 7 add ops (one parent item for the report plus six child steps with `parent_ref: 0`), then the work with `terminal`, `execute_code` and `read_file`, then `board_edit` with `set_checked` ops. r1-2 checked in two batches (rev 3); r1-1 and r1-3 checked all 7 in one call (rev 2). Assistant turns are the assistant messages stored in state.db for the session, read only.

## Task 2: wording rounds

Round 1 passed 3 of 3; no wording round. `plugin/session_tasks/tool_text.py` is unchanged (`git status --porcelain plugin/` prints nothing). `uv run pytest tests/test_tool_text.py tests/test_pre_llm_hook.py -q`: 81 passed.

## Injected text cost (for Phase 5, RESEARCH Pitfall 6)

| Figure | Value |
|--------|-------|
| NUDGE_LINE length | 206 characters, one line |
| Final board item count | 7 per run (1 parent + 6 steps) in r1-1, r1-2, r1-3 |
| Assistant turns per run | 9, 8, 9 |
| Wall time per run (result event `duration_ms`) | 52.9 s, 45.8 s, 47.6 s |
| Model tokens per run (result event, input / output) | r1-1: 924302 / 3628 (cache read 906921); r1-2: 812723 / 3372 (cache read 795984); r1-3: 895541 / 2759 (cache read 887476) |
| Hook-load check | 96089 input / 227 output, 9.9 s |

The input totals are the sum over all turns of the full context, almost all of it a cache read. The nudge adds 206 characters plus the board block (7 items with ids, about 350 characters) to every turn after the first board_edit.

## Test boards in data.db (cleanup in 03-12)

Board root ids left in `~/.hermes/plugin-data/hermes-session-tasks/data.db` by this plan. Nothing was deleted.

| Root id | Items | Note |
|---------|-------|------|
| `local-f3aa9e18981c55542e65bd9f63736a04d0010a85186e746064256bcb29bcc4c2` | 7 | r1-1 |
| `local-fe709b83895ec2ca3ad1ff17ea958c65ba470b05af5ea11bede3e64323870fdf` | 7 | r1-2 |
| `local-aa471eefa70ab9fb2b8b158bddbdf1c86f67af25b37c16704186812c071b2bf7` | 7 | r1-3 |
| `local-8b8faa2570f5e13eec1792cd7431c84977a5a9801db2b652d586d0eda2505173` | 0 | nudge check, no board expected |
| `local-09790dd311c9f37adc5c1a8e614ad165ff45c2407c31004a56351d8e0c0c985f` | 0 | stale first-dispatch run on the old gateway, no board, not counted |

Sessions in state.db for the same ids are also left in place. Run streams: `$HOME/.cache/hermes-session-tasks/own-job/{r1-1,r1-2,r1-3,nudge-check}.{jsonl,err}` and `stale-r1-1.{jsonl,err}`.

## Deviations from Plan

None - plan executed exactly as written. The rerun context (move the stale r1-1 pair aside, run the hook-load check first) was followed before round 1.

## Prohibitions check

- No board in data.db was deleted or changed by the executor; only the agent's own board_edit calls wrote.
- No Hermes setting changed; no gateway process was started, stopped or restarted by this executor.
- No wording change, so `tests/test_tool_text.py` properties hold as before.

## Threat Flags

None. No new surface; run output stays in `$HOME/.cache`, outside the repo.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: `.planning/phases/03-rest-router-and-client-install-spike/03-07-SUMMARY.md`
- FOUND: `$HOME/.cache/hermes-session-tasks/own-job/r1-1.jsonl`, `r1-2.jsonl`, `r1-3.jsonl` (non-empty)
- No task commit expected: round 1 changed no repo file; the docs commit carries this summary.
