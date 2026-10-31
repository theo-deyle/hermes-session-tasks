---
phase: 02-agent-tools-and-skill
plan: 06
subsystem: live-test
tags: [hermes-plugin, live-test, desktop, serve-process, compress, session-lineage]
status: complete

requires:
  - phase: 02-agent-tools-and-skill
    provides: plugin enabled and gateway restarted at 2026-10-31T18:03:30Z (plan 02-05)
provides:
  - Desktop session 20261031_145115_8eca46 (UI id 53e82110) holds a board with three agent items
  - The /compress carry-over for that session, confirmed from state.db and data.db
  - Time of the Task 3 check for plan 02-07 - 2026-10-31T19:13:57Z
  - The finding that a Desktop backend and a session keep the plugin set they started with
affects: [02-07, 03-desktop-pane, 07-rollout]

actuals:
  tokens: 6000
  tasks: 3
  commits: 1
plan_head_before: 290d7ca9782c7ffcf500068d10b8246cf3b3d6ed
plan_head_after: ebb3340b655176993371f9f40d95bf827cf358f7

key-files:
  created: []
  modified: []

key-decisions:
  - "A Desktop backend that started before a plugin enable keeps the old plugin set until Desktop is reopened. A session created before the plugin loaded keeps its old system prompt, so the prompt section reaches only sessions created after the backend has the plugin."
  - "Theo reopened Hermes Desktop to start a new backend. Nothing else was restarted or changed during the pass."

requirements-completed: [TOOL-02, AGNT-02]

coverage:
  - id: D1
    description: "A Desktop session that lists three things puts three items on its board (add half of success criterion 1)"
    requirement: "TOOL-02"
    verification:
      - kind: other
        ref: "data.db read-only at 2026-10-31T19:11:10Z: root 20261031_145115_8eca46, rev 1, items 1 to 3, updated_by agent"
        status: pass
    human_judgment: false
  - id: D2
    description: "The agent reached the board tools in the Desktop session through the board-rules skill and tool search"
    requirement: "AGNT-02"
    verification:
      - kind: other
        ref: "Desktop session after the backend reload: skill hermes-session-tasks:board-rules loaded, board_read and board_edit found through tool search"
        status: pass
    human_judgment: true
    rationale: "The stored system prompt of this session still lacks the board rules section (session created before the plugin loaded). The prompt section on a session created after the reload is not proven by this plan. The Desktop path for a new session needs one more look in Phase 7."
  - id: D3
    description: "After /compress, the newest session id resolves to the same board root and the board holds the same three items"
    requirement: "TOOL-02"
    verification:
      - kind: other
        ref: "desktop_check.py mode compressed at 2026-10-31T19:13:57Z, exit 0"
        status: pass
    human_judgment: false
---

# Phase 2 Plan 06: Desktop Pass Part 1 Summary

The Desktop agent put three items on the board, and the board survived /compress with the same session id and the same items. The first attempt failed because the Desktop backend was an old process. It passed after Theo reopened Hermes Desktop.

## Session

- Desktop session id: `20261031_145115_8eca46` (source desktop, started 2026-10-31T18:51:19Z).
- Desktop UI session id: `53e82110`.
- Check script (not committed): `/tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/fc36b518-e447-44ef-9607-152d96268ad2/scratchpad/live-02-06/desktop_check.py`. It opens state.db through `SessionDB(read_only=True)` and data.db with `mode=ro`, and prints no prompt text.

## Task 1: Theo starts a fresh Desktop session (done, with deviation)

Precondition held: the 02-05 SUMMARY records Theo's go, the restart at 2026-10-31T18:03:30Z and a running gateway (PID 592964). The request went to Theo at about 2026-10-31T18:15Z.

Theo's words, by turn:

1. `The agent has answered.`
2. After the first check failed and Theo reopened Hermes Desktop: `It is connected.`
3. After Claude read the board from data.db: `But I am telling you that that session took the message and made the tasks in the box just above the input box. The session id is 20261031_145115_8eca46. The desktop UI session id is 53e82110.`

## First check, mode added (failed)

Run at 2026-10-31T18:55:39Z, restart time `2026-10-31T18:03:30Z`. Exit code 1.

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

In that session the agent asked tool search for `todo_list` only and ran `todo_list` with the three items. It never asked for `board_edit` or `board_read`. data.db had no board and no alias for the session.

Process list at that time (local time is UTC minus 4 hours):

| PID | Start (local) | Process | Started before the plugin enable |
|-----|---------------|---------|----------------------------------|
| 544077 | Sat Oct 31 13:26 | `hermes serve --isolated` (Desktop backend) | yes |
| 578259 | Sat Oct 31 13:53 | `hermes serve --isolated` (Desktop backend) | yes |
| 592964 | Sat Oct 31 14:03 | `hermes gateway run --quiet` | no |

## Deviation and cause

**Deviation:** the first pass failed the `added` check and the round stopped for diagnosis, as the plan requires. No Claude-run restart and no setting change followed.

**Cause:** the two Desktop backend processes (PIDs 544077 and 578259) started before the plugin enable at 18:03Z. They never reloaded the plugin set. The enable step sends its reload nudge to the gateway control socket only (`hermes_cli/plugins_activation.py`, `reload_running_gateway`), so a `hermes serve` backend does not receive it.

**Fix:** Theo quit and reopened Hermes Desktop. Desktop started a new `hermes serve` backend, PID 678209, at 15:00:30 local (19:00:30Z). Desktop reopened the same session `20261031_145115_8eca46`.

**Result of the fix:** on Theo's next turn in that session (19:08Z, a question about the session id), the agent loaded the skill `hermes-session-tasks:board-rules`, found `board_read` and `board_edit` through tool search, read an empty board and added the three items. The stored system prompt of this session still lacks the board rules section, because the session was created before the plugin loaded. The agent reached the tools through the skill and tool search instead.

## Task 2: Data check, then /compress (done)

Read-only data.db read at 2026-10-31T19:11:10Z:

| Field | Value |
|-------|-------|
| root | `20261031_145115_8eca46` |
| rev | 1 |
| item 1 | "Call John about the quote", unchecked, updated_by agent |
| item 2 | "Book the van for Friday (Nov 6)", unchecked, updated_by agent |
| item 3 | "Decide on the paint supplier", unchecked, updated_by agent |

The board holds three items, so the add half of the check passes on the data. The `section_present` half stays false for this session, as explained above.

Claude showed the /compress request. Theo sent `/compress` at about 19:12Z and pasted the Desktop compression notice. The notice listed the three tasks as preserved. It also told the agent to reload the board-rules skill, so the Desktop compression notice names the skill as part of the carry-over.

## Task 3: /compress carry-over (done)

**Time of this check, for plan 02-07: 2026-10-31T19:13:57Z.**

`desktop_check.py compressed 20261031_145115_8eca46`, exit 0. Reduced form of the result, built from the fields the run reported (the raw output was not saved to a file):

```json
{
  "lineage": ["20261031_145115_8eca46"],
  "newest_id": "20261031_145115_8eca46",
  "old_root": "20261031_145115_8eca46",
  "newest_root": "20261031_145115_8eca46",
  "rev": 1,
  "items": [
    {"id": 1, "text": "Call John about the quote", "checked": false, "updated_by": "agent"},
    {"id": 2, "text": "Book the van for Friday (Nov 6)", "checked": false, "updated_by": "agent"},
    {"id": 3, "text": "Decide on the paint supplier", "checked": false, "updated_by": "agent"}
  ]
}
```

- The session id did not change after /compress. Compression ran in place.
- The newest id resolves to the same root: `old_root` equals `newest_root`.
- The board holds the same three items, `rev` 1, all unchecked.

The plan verify command printed `items on the newest board 3 20261031_145115_8eca46` and exited 0.

## Finding for the roadmap (Phase 7 rollout)

A Desktop backend started before a plugin enable keeps the old plugin set until Desktop is reopened. A session created before the plugin loaded keeps its old system prompt. The prompt section therefore reaches only sessions created after the backend has the plugin. For the rollout, Theo reopens Hermes Desktop after the enable, then starts a new session to get the prompt section. An old session still works through the skill and tool search once the backend has reloaded.

## Deviations from Plan

**1. [Rule 3 - Blocking] Desktop backend predated the plugin enable**
- **Found during:** Task 2 data check
- **Issue:** `added` check exited 1, no board, no prompt section, agent used `todo_list`.
- **Fix:** Theo reopened Hermes Desktop so a new `hermes serve` backend loaded the plugin. Claude restarted nothing and changed no setting.
- **Files modified:** none
- **Commit:** none for the fix. The blocked state was recorded in `ebb3340`.

**Total deviations:** 1 (blocking, fixed by Theo reopening Desktop). **Impact:** the `section_present` proof for a session created after the reload is open. The tools, the edit path and the /compress carry-over are proven on the Desktop path.

## Known Stubs

None. No repo file changed.

## Threat Flags

None.

## Self-Check

- `desktop_check.py` and `added_result.json` exist in the scratchpad dir and not in the repo.
- `git status --porcelain` shows only `.planning/config.json` and `.planning/state.json`, modified before this plan started.
- The JSON, times and Theo's words above come from the checks run in this plan.

## Self-Check: PASSED
