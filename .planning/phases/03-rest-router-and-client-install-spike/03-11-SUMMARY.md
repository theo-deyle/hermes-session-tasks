---
phase: 03-rest-router-and-client-install-spike
plan: 11
subsystem: live-test
tags: [hermes-plugin, live-test, desktop-pane, windows, events, stale-write, readme, API-01, API-02, DEV-05]

# Dependency graph
requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: the Windows PC install with the frozen test pane (plan 03-10); the Mac live proof (plan 03-09); the REST routes, the stale reply and the board.updated event (plans 03-01 to 03-06)
provides:
  - Live proof on the Windows PC for success criteria 2 and 3: agent event at rev 1, pane write and stale reply at rev 2, every rev matched against data.db read only
  - RESEARCH A2 on Windows settled: event delivery over the SSH tunnel works for the tool write and for the route write
  - README install steps confirmed by both machines, with the SSH alias of each machine, the Update reload step and the 404 explanation
  - Board ids for the plan 03-12 cleanup
affects: [03-12, phase-07-DEV-04]

# Actuals (#2632)
actuals:
  tokens: 4500
  tasks: 3
  commits: 1
plan_head_before: 8ac1644fac55463ab9563f200c704d71e8e248a6
plan_head_after: dd16d72

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "README install steps name the real SSH alias of each machine: devbox on the Mac, devpc-ts on the Windows PC"
    - "A Desktop half update is the install script again plus Reload desktop plugins; no backend restart"

key-files:
  created:
    - .planning/phases/03-rest-router-and-client-install-spike/03-11-SUMMARY.md
  modified:
    - README.md

key-decisions:
  - "The README names the live SSH alias of each machine in its commands instead of a placeholder, because both runs needed a substitution."
  - "The test pane label race (`other chat` on a brand-new chat) is recorded, not fixed: the frozen test pane is a Phase 3 tool and the Phase 4 board pane has no such label."

patterns-established:
  - "Live test evidence: every rev Theo reports is compared with live_check.py output before the task passes"

requirements-completed: [DEV-05, API-01, API-02]

coverage:
  - id: D1
    description: "An agent write in a new chat on the Windows PC shows as agent event rev 1 and data.db holds the item by agent at rev 1"
    requirement: API-01
    verification:
      kind: human
      status: pass
  - id: D2
    description: "Run write test on the Windows PC shows pane event rev 2 (this chat), add ok at rev 2, stale write answered stale at rev 2; data.db holds the pane item by user at rev 2 and no rev 3"
    requirement: API-02
    verification:
      kind: human
      status: pass
  - id: D3
    description: "README install steps match the live facts from both machines and the README tests pass"
    requirement: DEV-05
    verification:
      kind: test
      ref: "uv run pytest tests/test_install_script.py -q -rs -k readme: 7 passed; dash check exit 0"
      status: pass

# Metrics
duration: about 20 min of executor time after the two live requests
completed: 2026-11-02
status: complete
---

# Phase 3 Plan 11: Windows PC live test and README facts Summary

**The Windows PC test pane passed both live steps: the agent write showed as rev 1 and the pane write plus the stale reply showed as rev 2, each matched against data.db.** The README now names the SSH alias of each machine, the reload step after an update, and the 404 explanation.

Local time is UTC-5. The orchestrator ran Tasks 1 and 2 with Theo on 2026-11-02 and checked every number against `~/.hermes/plugin-data/hermes-session-tasks/data.db` with a read-only `live_check.py`. Test board: `20261102_130511_60c13f` (chat "Add check the test pane on the Windows PC to my board").

## Round record

| Step | Request to Theo | Theo reported | data.db (live_check.py) | Result |
|------|-----------------|---------------|-------------------------|--------|
| 1 | In a new chat on the Windows PC, send "Add check the test pane on the Windows PC to my board." Report the pane lines (W2 `2026-11-02T17:56:19Z`) | `session 20261102_130511_60c13f, board rev 1`, `agent event: rev 1 at 1:05:22 PM (other chat)`, `pane event: none yet`, `write test: not run`, `[ ] #1 Check the test pane on the Windows PC` | board rev 1, `updated_at 2026-11-02T18:05:22.684216Z`, item 1 by agent at rev 1; alias `20261102_130511_60c13f` to itself; changes seq 193 (agent add item 1) | pass |
| 2 | Click Run write test. Report the pane lines (W3 `2026-11-02T18:05:23Z`) | `board rev 2`, `pane event: rev 2 at 1:06:25 PM (this chat)`, `write test: add ok at rev 2, stale write answered stale (stale) at rev 2`, items `[ ] #1 Check the test pane on the Windows PC`, `[ ] #2 test item added by the pane` | board rev 2, `updated_at 2026-11-02T18:06:26.029326Z`, item 2 by user at rev 2; changes seq 195 (user add item 2); no rev 3 | pass |

Full pane lines after step 1:

```
backend 0.1.0, api 1
pane 0.1.0, api 1
session 20261102_130511_60c13f, board rev 1
agent event: rev 1 at 1:05:22 PM (other chat)
pane event: none yet
write test: not run
[ ] #1 Check the test pane on the Windows PC
```

Full pane lines after step 2:

```
backend 0.1.0, api 1
pane 0.1.0, api 1
session 20261102_130511_60c13f, board rev 2
agent event: rev 1 at 1:05:22 PM (other chat)
pane event: rev 2 at 1:06:25 PM (this chat)
write test: add ok at rev 2, stale write answered stale (stale) at rev 2
[ ] #1 Check the test pane on the Windows PC
[ ] #2 test item added by the pane
```

The stale write wrote nothing: data.db holds no rev 3 and no change row after seq 195. Success criteria 2 and 3 hold on the Windows PC. RESEARCH A2 holds on Windows: both events reached the pane over the SSH tunnel.

## The `(other chat)` label on step 1

The agent event line read `(other chat)` on the Windows PC. On the Mac (plan 03-09) it read `(this chat)`. Cause: the frozen test pane sets `here` by comparing `payload.root_id` with the root of its last board reply. In a brand-new chat the event arrived before the pane's first board load for the new session id finished, so that root was null and the label fell to `other chat`. The event itself reached the pane (actor agent, rev 1) and the reload showed the item. This is a label race in the test pane only, not an event path fault. The Phase 4 board pane has no such label. The plan's cross-chat pass condition allows `(other chat)` for an event on the same machine, and the item line proves delivery, so step 1 passes.

## Task 3: README facts from both machines

Live facts and where the README stood before this plan:

| Live fact | Source | README before | README now |
|-----------|--------|---------------|------------|
| Mac SSH alias for devpc is `devbox` | 03-08 Task 2 | Commands used `devpc` with no note | Mac steps name `devbox` and use it in both commands |
| Windows SSH alias for devpc is `devpc-ts` | 03-10 Task 1 | "Replace `devpc` with the name from the SSH config" | Windows steps name `devpc-ts` and use it in both commands |
| `scp -O` worked on the first try on both machines; the plain fallback did not run | 03-08, 03-10 | Order stated, outcome not stated | One sentence records the outcome |
| Mac home `/Users/theodeyle/.hermes`, Windows home `C:\Users\TheoDeyle\AppData\Local\hermes` | 03-08, 03-10 | Held: `~/.hermes/...` and `%LOCALAPPDATA%\hermes\...` | Unchanged |
| The pane appears on the right with the title "Session tasks" | 03-09, 03-10, this plan | Held: "open the Session tasks pane on the right" | Unchanged |
| After a second install, Reload desktop plugins loaded the new pane file with no backend restart | 03-10 Task 3 | Update section had no reload step | Update section: run Reload desktop plugins, no backend restart |
| `404 Plugin not found` means Desktop is attached to a backend on another host | 03-09 step 1 | Not covered | One line under Known behavior |
| The first Windows install used the default RemotePath and installed the Phase 4 board pane; the test pane needed `-RemotePath` | 03-10 Task 3 | `-RemotePath` is described for "a frozen test build" | Unchanged: the README documents the real install |

README changed. Verify results: `uv run pytest tests/test_install_script.py -q -rs -k readme` gave 7 passed; the dash check exited 0.

## Must-haves evidence

| Must-have | Evidence | Result |
|-----------|----------|--------|
| Agent write in a new chat on the Windows PC shows as `agent event: rev N at ...`, matched against data.db read only | Step 1: rev 1 in the pane, rev 1 by agent in data.db | pass, label `(other chat)` explained above |
| Run write test shows `pane event: rev N+1 ... (this chat)` and the stale write line; data.db holds the pane item at rev N+1 with no rev change from the stale write | Step 2: rev 2 by user, no rev 3 | pass |
| Cross-chat pass condition: focused chat shows `(this chat)`; same-machine other chat may show `(other chat)` | Step 2 shows `(this chat)`; step 1 label is a race on a new chat, delivery proven by the item line | pass |
| README matches the two live runs and the README tests pass | Task 3 table; 7 passed | pass |
| Each request holds one action and one thing to report | Two requests, each one action and one report | pass |
| Prohibition: Claude never writes to data.db in this plan | `live_check.py` opens with `mode=ro` | held |
| Prohibition: README keeps no em dash or en dash; every command is PowerShell | Dash check exit 0; commands unchanged in form | held |

## Deviations from Plan

**1. [Rule 1 - Record] The agent event label read `(other chat)` on the Windows PC**
- **Found during:** Task 1
- **Issue:** The plan expected `(this chat)`. The frozen test pane labels an event by comparing its root id with the root of the last board reply, which was still null on a brand-new chat.
- **Fix:** None. The item line and data.db prove delivery, and the plan's cross-chat condition allows `(other chat)` on the same machine. The Phase 4 board pane has no such label.
- **Files modified:** none
- **Verification:** data.db item 1 by agent at rev 1; pane item line `[ ] #1 Check the test pane on the Windows PC`
- **Committed in:** the SUMMARY commit

**2. [Rule 1 - Record] A second test board from an earlier new chat**
- **Found during:** Task 2
- **Issue:** Board `20261102_130449_f33b04` (rev 1, `updated_at 2026-11-02T18:06:22.400538Z`, item 1 "test item added by the pane" by user) exists. Theo's first click ran while an earlier new chat, opened 22 s before, was focused.
- **Fix:** None. The board goes on the cleanup list below.
- **Files modified:** none
- **Verification:** live_check.py output
- **Committed in:** the SUMMARY commit

**Total deviations:** 2 records, no code change. **Impact:** none on the plan's goals.

## Test boards in data.db (cleanup in 03-12)

| Kind | Ids |
|------|-----|
| Windows test board | `20261102_130511_60c13f` (items #1 agent, #2 pane) |
| Windows pane write from the earlier new chat | `20261102_130449_f33b04` (item #1 by user) |

The Mac boards and the plan 03-07 boards are listed in the 03-09 SUMMARY.

## Prohibitions check

- Every data.db check opened the file read only. Claude wrote nothing to data.db.
- Each request used plain words, one action and one report, no code name, no GSD term, no reply word.

## Carry forward

- Plan 03-12 asks Theo once, then deletes the test boards on his recorded yes: the two Windows boards above plus the 03-09 list.
- After the cleanup, both machines need the real board pane back: the install line with the default `RemotePath`, then Reload desktop plugins. The README now holds that line per machine.

## Task Commits

- `dd16d72` docs(03-11): README facts from the Mac and Windows PC runs

## Known Stubs

None.

## Threat Flags

None. No new surface. T-03-28 accepted: the test items hold no personal data and plan 03-12 asks before it deletes them.

## Next Phase Readiness

Plan 03-12 (cleanup and final gates) can start. No plugin Python file changed, so no backend restart is needed.

---
*Phase: 03-rest-router-and-client-install-spike*
*Completed: 2026-11-02*

## Self-Check: PASSED

- FOUND: `.planning/phases/03-rest-router-and-client-install-spike/03-11-SUMMARY.md`
- FOUND: commit `dd16d72` is an ancestor of HEAD
- FOUND: `README.md` holds "Windows PC"
