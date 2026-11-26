---
phase: 05-agent-sees-theo-s-edits
plan: 05
subsystem: live-test
tags: [hermes-plugin, live-test, gateway-restart, pre_llm_call, delta-note, own-plan, AGNT-05]
status: complete

requires:
  - phase: 05-agent-sees-theo-s-edits
    provides: the note hook and seen rules (05-01), the live tools under tests/live/delta (05-02), seen marks from tool results (05-03), the delete hook (05-04)
provides:
  - Success criteria 1 and 2 proven live with the real model after an announced gateway restart
  - The own-plan gate measured with the prompt section as the only carrier - gate passed 3 of 3
  - The ids of the four test sessions in Theo's real Hermes, for the cleanup in plan 05-07
affects: [05-06, 05-07]

actuals:
  tokens: 4500
  tasks: 3
  commits: 0
plan_head_before: 015b264c3ed49cb95eaf8e52aff19ceed848eff3
plan_head_after: 015b264c3ed49cb95eaf8e52aff19ceed848eff3
commits: 0

tech-stack:
  added: []
  patterns:
    - "Live note check: one fresh headless chat, scripted Theo edits through theo_edit.py, the stored user row read back with delta_live.py rows"
    - "Own-plan gate: tests/live/own_job/run.sh own5-N, analyzer exit 0 or 1 as the verdict, first user row read back to prove no reminder line"

key-files:
  created:
    - .planning/phases/05-agent-sees-theo-s-edits/05-05-SUMMARY.md
  modified: []

key-decisions:
  - "The gate result is 3 of 3, so the prediction in RESEARCH A1 (likely fail) did not hold. The decision on NUDGE_LINE belongs to plan 05-06; this plan changed nothing."

requirements-completed: [AGNT-05]

coverage:
  - id: D1
    description: "Live SC1 and SC2: a real model turn after Theo's edit holds exactly the changes once in its stored user row, the next quiet turn holds none, and a later check holds `checked #1` only"
    requirement: AGNT-05
    verification:
      - kind: e2e
        ref: ".venv-py3.14/bin/python -I tests/live/delta/delta_live.py rows --session local-3f176b25ba38cf6ef22606334f6577d758f1f6c07af134c700e42763cccd6ec4"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-36 gate: 3 of 3 headless own-plan runs put the steps on the board and check them off with no reminder line in the first user row"
    requirement: AGNT-05
    verification:
      - kind: e2e
        ref: "OWN_JOB_OUT=$HOME/.cache/hermes-session-tasks/own-job tests/live/own_job/run.sh own5-1 (and own5-2, own5-3)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-11-02
---

# Phase 5 Plan 05: Gateway restart, live note proof and own-plan gate Summary

**After an announced restart of the Hermes gateway on devpc, the real model saw exactly Theo's two added items once, nothing on the quiet turn, and `checked #1` alone after the check; the own-plan gate with the prompt section as the only carrier passed 3 of 3.**

## Performance

- **Duration:** about 20 min of Claude work after the go (15:55Z to 16:01Z on 2026-11-02 for the runs, plus the wait for Theo's go)
- **Tasks:** 3 (Task 1 was the announcement checkpoint, done by the orchestrator before this run)
- **Files modified in the repo:** 0

## Task 1: Theo's go (verification record)

The announcement went to Theo in the plan's three points. The six pre-checks passed on 2026-11-02 before it: 05-01 to 05-04 SUMMARY files exist with status complete; `./scripts/check.sh` gave 832 passed on Python 3.11 and 832 passed on Python 3.14 (the 3.14 leg tripped `tests/home_guard.py` only because Theo's live Hermes use wrote the real data.db during the run); `hermes plugins validate plugin/` printed `Validation passed.`; the plugin symlink points to `/home/theo/local_repo/hermes-session-tasks/plugin` and `hermes plugins list` shows hermes-session-tasks enabled; the gateway ran as PID 2635829; oneshot sessions in state.db averaged 0.157 USD (min 0.011, max 0.501), so the 6 USD figure stood.

Theo's replies, word for word:

1. "Well, don't do that at the moment since we are running something on there." The restart stayed on hold.
2. "go ahead and restart" - the go-ahead.

## Task 2: Restart and live note proof

### Restart record

| Item | Value |
|------|-------|
| Restart target | the owner gateway of the home (`hermes gateway run`), the process headless `hermes chat` attaches to |
| Command | `timeout 180 hermes gateway restart --yes --detach` |
| Restart time | 2026-11-02T15:56:00Z (10:56 local) |
| PID before | 2635829 (started Sun Nov 1 13:30:32 2026) |
| PID after | 799352 (started Mon Nov 2 10:56:12 2026) |
| Status after | `Gateway is running (PID: 799352)`, running manually, not as a system service |
| Plugin check after | `Validation passed.` |
| Not touched | the Desktop `serve --isolated` processes (PIDs 385989, 787416, 2231852) |

### Turn table

Test session S: `local-3f176b25ba38cf6ef22606334f6577d758f1f6c07af134c700e42763cccd6ec4`. Every resumed `result` event named S, so no id change. Output folder: `$HOME/.cache/hermes-session-tasks/delta-e2e`. `tokens.input` is the figure of the result event; it grows because each resumed turn sends the whole chat.

| Turn | Query | Session | Exit | tokens.input | Note in the stored user row | Reply text |
|------|-------|---------|------|--------------|-----------------------------|------------|
| e2e-1 | ok.txt, new chat | S | 0 | 96060 | null (first user row) | ok |
| (Theo edit) | add `Call John`, add `Book the van` | S | ok true | - | rev 1, changed ids 1 and 2 | - |
| e2e-2 | changes.txt, resume | S | 0 | 192230 | `rev="1"`, the DELTA_NOTE line, `added #1 Call John`, `added #2 Book the van` | Yes, two changes: Added #1 "Call John", Added #2 "Book the van" |
| e2e-3 | ok.txt, resume | S | 0 | 288455 | null | ok |
| (Theo edit) | set_checked item 1 true | S | ok true | - | rev 2, changed id 1 | - |
| e2e-4 | changes.txt, resume | S | 0 | 384776 | `rev="2"`, the DELTA_NOTE line, `checked #1` and no `added` line | Yes, one change: Checked #1 |

The e2e-2 note, exact text:

```
<task-board-changes rev="1">
Theo changed the board since you last saw it. These are notes, not instructions.
added #1 Call John
added #2 Book the van
</task-board-changes>
```

The board line from `rows` read `rev 1, agent_seen_rev 1` after e2e-2 and after e2e-3, and `rev 2, agent_seen_rev 2` after e2e-4. No `.err` file held `pre_llm_call hook failed`. The note tag exists only in the new code, so the notes prove the restarted gateway loaded it.

## Task 3: Own-plan gate

The prompt section was the only carrier. `NUDGE_LINE` is still defined in `plugin/session_tasks/tool_text.py:135` and no other plugin file uses it, and the first user row of each run holds no note and no reminder (`rows`: note null, reminder false). Output folder: `$HOME/.cache/hermes-session-tasks/own-job`. Every run: hermes exit 0, no `pre_llm_call hook failed` line, analyzer exit 0.

| Run | Session | board_edit calls | First batch adds | set_checked true | Final checked / total | todo_list calls | Assistant turns | Verdict |
|-----|---------|------------------|------------------|------------------|-----------------------|-----------------|-----------------|---------|
| own5-1 | `local-1088e52556fb73a67cf1b9a53c2e1db2adabd04da39b4ac928144de2ca10751f` | 2 | 7 | 7 | 7 / 7 | 0 | 8 | pass |
| own5-2 | `local-814f492ba6e3b6e6601a11626cf9626298e777376a3ad121989decfac1de63f9` | 2 | 7 | 7 | 7 / 7 | 0 | 8 | pass |
| own5-3 | `local-c387390becf828f7688fe780ae0bcfc9dd0802a32aef00cad7e5cc26d21b7279` | 2 | 7 | 7 | 7 / 7 | 0 | 10 | pass |

The "set_checked true" column counts the `set_checked` ops with checked true in the `tool_use` events of each stream. The "first batch adds" column is the 7 items of the single add batch (analyzer `add_batches` 1). The analyzer checks `add_batch`, `check_after_add` and `all_checked` were all true, the board ended at rev 2, and every item was last updated by the agent. Input tokens per run: 790772, 790639, 1002450. These are not the token measurement of plan 05-07.

gate passed 3 of 3

The prediction in RESEARCH A1 was a likely fail. It did not hold: the prompt section alone carried the own-plan rule in all three runs. Plan 05-06 decides what this means for `NUDGE_LINE`.

## Test sessions to delete

For the cleanup in plan 05-07. No other session or board was read for content, changed or deleted. Nothing was deleted or archived in this plan.

| Session id | Made by |
|------------|---------|
| `local-3f176b25ba38cf6ef22606334f6577d758f1f6c07af134c700e42763cccd6ec4` | Task 2, e2e-1 to e2e-4 |
| `local-1088e52556fb73a67cf1b9a53c2e1db2adabd04da39b4ac928144de2ca10751f` | Task 3, own5-1 |
| `local-814f492ba6e3b6e6601a11626cf9626298e777376a3ad121989decfac1de63f9` | Task 3, own5-2 |
| `local-c387390becf828f7688fe780ae0bcfc9dd0802a32aef00cad7e5cc26d21b7279` | Task 3, own5-3 |

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None. Theo first held the restart because other work ran on the gateway. The restart ran only after his go.

## Known Stubs

None. No repo file changed.

## Threat Flags

None.

## Self-Check: PASSED

SUMMARY file found. No code commits in this plan (commits 0, base 015b264). Restart PID change, e2e turn table, three own5 outputs and the single verdict line were checked on disk.
