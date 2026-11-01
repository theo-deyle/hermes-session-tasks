---
phase: 03-rest-router-and-client-install-spike
plan: 09
subsystem: live-test
tags: [hermes-plugin, live-test, desktop-pane, mac, events, stale-write, API-01, API-02, API-03, DEV-05]

# Dependency graph
requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: the Mac install with the verified plugin.js hash and live_check.py (plan 03-08); the REST routes, the stale reply and the board.updated event (plans 03-01 to 03-06)
provides:
  - Live proof on the Mac for success criteria 1 to 4: version lines, agent event, pane event, structured stale reply
  - Two pane fixes found by the live test: the backend error text in the pane, and the pane docked to the right edge
  - The "other gateway" explanation for the 404 Plugin not found reply
  - Board ids for the plan 03-12 cleanup
affects: [03-10, 03-11, 03-12, phase-04-pane]

# Actuals (#2632)
actuals:
  tokens: 1800
  tasks: 3
  commits: 2
plan_head_before: 5fa091a
plan_head_after: 17d7082

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pane placement: `placement: 'right'` alone stacks the pane as a tab of the right role; with no right pane open it lands in the main area and covers the chat composer. `dock: { pane: 'workspace', pos: 'right' }` plus `width` puts it on the right edge."
    - "Pane error lines carry the error text: `backend not reached: <status>: <body>` so a 404 from a wrong gateway is readable in the pane"

key-files:
  created:
    - .planning/phases/03-rest-router-and-client-install-spike/03-09-SUMMARY.md
  modified:
    - plugin/desktop/plugin.js
    - tests/test_desktop_plugin.py

key-decisions:
  - "A defect Theo flags during a live test is fixed in the same turn (standing rule 33, set during this plan)."
  - "The pane docks to the right edge with a fixed width; the stack-as-tab placement is not used."

patterns-established:
  - "Live test evidence: every rev Theo reports is compared with live_check.py output before the task passes"

requirements-completed: [DEV-05, API-01, API-02, API-03]

coverage:
  - id: D1
    description: "Test pane on the Mac shows backend 0.1.0, api 1 and pane 0.1.0, api 1 with no mismatch line"
    requirement: DEV-05
    verification:
      kind: human
      status: pass
  - id: D2
    description: "An agent write shows as agent event rev 1 (this chat) and data.db holds the item by agent at rev 1"
    requirement: API-01
    verification:
      kind: human
      status: pass
  - id: D3
    description: "Run write test shows pane event rev 2 (this chat), add ok at rev 2, stale write answered stale at rev 2; data.db holds the pane item by user at rev 2"
    requirement: API-02
    verification:
      kind: human
      status: pass
  - id: D4
    description: "The stale write answers with the structured stale reply and changes no rev"
    requirement: API-03
    verification:
      kind: human
      status: pass
---

# Phase 3 Plan 09: Mac live test Summary

**The Mac test pane passed 3 of 3: version lines, agent event at rev 1, pane write and stale reply at rev 2.** Two pane defects surfaced and were fixed during the round.

## Round record

Local time is UTC-5. Test board: `20261101_162121_506689` (chat "Add Mac test pane check").

| Step | Request to Theo | Theo reported | data.db (live_check.py) | Result |
|------|-----------------|---------------|-------------------------|--------|
| 1 | Open Desktop on the Mac, report the pane lines | First tries: `backend not reached` with no detail, then `404 Plugin not found`; after switching Desktop to devbox and Reload desktop plugins: `backend 0.1.0, api 1`, `pane 0.1.0, api 1`, no mismatch line | no board change | pass after fixes |
| 2 | Ask the agent in a new chat to add "Check the test pane on the Mac" to the board (M2 `2026-11-01T21:21:14Z`) | "It added the check task"; pane: `agent event: rev 1 at 4:21:41 PM (this chat)` | rev 1, item #1 by agent at `21:21:41Z` | pass |
| 3 | Click Run write test, report the pane lines (M3 `2026-11-01T21:22:14Z`) | `pane event: rev 2 at 5:26:37 PM (this chat)`, `write test: add ok at rev 2, stale write answered stale (stale) at rev 2`, items `[ ] #1 Check the test pane on the Mac`, `[ ] #2 test item added by the pane` | rev 2, item #2 by user at `22:26:37Z`, no further rev | pass |

Screenshot of step 3: `~/share/hermes-todo/Screenshot 2026-11-01 at 5.26.43 PM.png`. The chat composer and the pane are both visible.

## Defects found and fixed in the round

| Defect | Cause | Fix | Commit |
|--------|-------|-----|--------|
| Pane said `backend not reached` with no reason | `metaFailed` dropped the error message | Pane prints `backend not reached: <message>`; test asserts `500: forced failure` in the lines | `7eef6b3` |
| Pane filled the main area and covered the chat composer; a resize snapped back; Theo could not type a message | `placement: 'right'` alone stacks the pane as a tab of the right role; with no right pane open the pane landed in the main area | Registration adds `dock: { pane: 'workspace', pos: 'right' }` with `width: '320px'`; test asserts the dock value; Theo ran Reset layout on the Mac | `17d7082` |

plugin.js SHA-256 after `17d7082`: `5dda4c37a622e5ef88d8d1fb0c6dfc9fa854999d4fd48a350d4169d135deacfa`. The Mac disk slot holds this version after Theo re-ran the install script. The Windows install (plan 03-10) must copy this version.

`tests/test_desktop_plugin.py`: 26 passed after both fixes.

## The 404 "Plugin not found" explanation

Desktop on the Mac was attached to a different gateway, not devbox. That gateway has no hermes-session-tasks plugin, so `/meta` answered `404 {"detail":"Plugin not found"}` (the `_plugin_api_request_refused` reply). Throwaway `hermes serve` backends on devpc answered `200 {"ok":true,...}` the whole time, so the backend code was never at fault. After Theo switched Desktop to devbox, the write test worked and the version lines showed.

## Deviations from the plan

1. Two pane fixes with two commits in a plan that planned no file change (rule 33: a flagged defect is fixed in the same turn).
2. The defect fix was first deferred ("noted as a bug for the real pane"). That deferral blocked step 2 because the pane covered the chat composer. Rule 33 in `~/.claude/CLAUDE.md` records the lesson.
3. M1 for step 1 was not retained through the fix round; steps 2 and 3 carry their request times.

## Cleanup list for plan 03-12

| Kind | Ids |
|------|-----|
| Mac test board | `20261101_162121_506689` (items #1 agent, #2 pane) |
| Pane write-test boards from step 1 tries | `20261031_191523_093c62` (items #2, #3 by user at `21:03:47Z`), `20261029_124236_4ecdeb` (one pane item at `21:03:39Z`) |
| Plan 03-07 boards | `local-f3aa9e18…`, `local-fe709b83…`, `local-aa471eef…` (7 items each); nudge-check session `local-8b8faa25…` |

## Task Commits

- `7eef6b3` fix(03-09): show the meta error text in the test pane backend line
- `17d7082` fix(03-09): dock the test pane to the right of the chat

## Next Phase Readiness

Plan 03-10 (Windows PC install) can start. The install copies plugin.js at hash `5dda4c37…acfa`. No gateway restart is needed: no plugin Python file changed.
