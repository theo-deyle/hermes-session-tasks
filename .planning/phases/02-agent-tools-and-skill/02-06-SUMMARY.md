---
phase: 02-agent-tools-and-skill
plan: 06
subsystem: live-test
tags: [hermes-plugin, live-test, desktop, serve-process, blocked]
status: blocked

requires:
  - phase: 02-agent-tools-and-skill
    provides: plugin enabled and gateway restarted at 2026-10-31T18:03:30Z (plan 02-05)
provides:
  - The finding that the Desktop session did not get the board rules section and has no board
affects: [02-07, 03-desktop-pane, 07-rollout]

actuals:
  tokens: 4000
  tasks: 1
  commits: 0
plan_head_before: 290d7ca9782c7ffcf500068d10b8246cf3b3d6ed
plan_head_after: 290d7ca9782c7ffcf500068d10b8246cf3b3d6ed

key-files:
  created: []
  modified: []

key-decisions:
  - "The round stops at the Task 2 data check. Task 2 request and Task 3 do not run. Nothing was restarted or changed."

requirements-completed: []

coverage:
  - id: D1
    description: "A Desktop session that lists three things puts three items on its board"
    requirement: "TOOL-02"
    verification:
      - kind: other
        ref: "desktop_check.py mode added: items [] , exit 1"
        status: fail
    human_judgment: false
  - id: D2
    description: "The stored system prompt of the Desktop session holds hermes-session-tasks.board-rules"
    requirement: "AGNT-02"
    verification:
      - kind: other
        ref: "desktop_check.py mode added: section_present false"
        status: fail
    human_judgment: false
---

# Phase 2 Plan 06: Desktop Pass Summary (blocked)

The Desktop agent did not use the board. The session has no board rules section in its system prompt and no board in data.db. The agent kept the three items in the built-in task list (`todo_list`) instead. The round stops here.

## Task 1: Theo starts a fresh Desktop session (done)

Precondition held: the 02-05 SUMMARY records Theo's go, the restart at 2026-10-31T18:03:30Z and a running gateway (PID 592964). The request was shown to Theo at about 2026-10-31T18:15Z. Theo's reply, word for word: `The agent has answered.`

## Task 2: Data check (failed)

Check script: `/tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/fc36b518-e447-44ef-9607-152d96268ad2/scratchpad/live-02-06/desktop_check.py`. It is not committed. It opens state.db through `SessionDB(read_only=True)` and data.db with `mode=ro`, and prints no prompt text. Run at 2026-10-31T18:55:39Z, mode `added`, restart time `2026-10-31T18:03:30Z`. Exit code 1. Result:

```json
{
  "session_id": "20261031_145115_8eca46",
  "section_present": false,
  "root": "20261031_145115_8eca46",
  "rev": null,
  "items": [],
  "reply_first_line": "I've added all three to the to-do list:",
  "started_at_utc": "2026-10-31T18:51:19.848162+00:00"
}
```

The session has source `desktop`, 6 messages, model `claude-sonnet-5-5[1m]`.

Extra read-only evidence from the same session in state.db:

- The agent made two tool calls. `tool_describe` asked for `["todo_list"]` only. Then `tool_call` ran `todo_list` with the three items (call John about the quote, book the van for Friday, decide on the paint supplier).
- The agent never asked for `board_edit` or `board_read`.
- data.db has no board and no alias for this session. The file last changed at 14:10:32 local, during the 02-05 runs.

## Finding

The board rules section never reached this Desktop session, so the agent had no reason to look for `board_edit`. The likely cause is that the Desktop backend runs in one of the two `hermes serve --isolated` processes that started before the 02-05 restart. The 02-05 SUMMARY recorded that they keep the pre-restart plugin set. This is a hypothesis: Claude did not read which serve process holds the session, and the system prompt text is not printed by design.

Process list now (local time is UTC minus 4 hours), unchanged from 02-05:

| PID | Start (local) | Process | Started before the restart |
|-----|---------------|---------|----------------------------|
| 544077 | Sat Oct 31 13:26:31 2026 | `hermes serve --isolated` (Desktop SSH session) | yes |
| 578259 | Sat Oct 31 13:53:18 2026 | `hermes serve --isolated` (Desktop SSH session) | yes |
| 592964 | Sat Oct 31 14:03:32 2026 | `hermes gateway run --quiet` | no, the new gateway |

The gateway restart of 02-05 does not restart the two serve processes. Phase 7 owns the rollout to every serve process.

## Not run

- The Task 2 request to Theo (`/compress`). A broken system stops the test round, so the request was not shown.
- Task 3 (`compressed` check) and plan 02-07.

## Deviations from Plan

None. The plan says to stop on exit 1 and to report the finding with the 02-05 process list. No restart, no setting change and no data write happened.

## Known Stubs

None. No repo file changed.

## Threat Flags

None.

## Self-Check

- `desktop_check.py` exists in the scratchpad dir and is not in the repo.
- `git status --porcelain` before this SUMMARY showed only `.planning/config.json` and `.planning/state.json`, modified before this plan started.
- Process list and JSON above come from the commands run in this plan.

## Self-Check: PASSED
