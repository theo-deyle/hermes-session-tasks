---
phase: 03-rest-router-and-client-install-spike
plan: 10
subsystem: live-test
tags: [hermes-plugin, live-test, desktop-install, windows, sha256, restart, DEV-05, API-03]

# Dependency graph
requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: the Mac live proof and the frozen test pane hash (plan 03-09); scripts/install-desktop.ps1 with -RemotePath (plan 03-03, extended by plan 04-09); the REST routes and the /meta version lines (plans 03-01 to 03-06)
provides:
  - Live proof on the Windows PC for success criteria 1 (install half) and 4: the sha256 line, the home line, the ssh name, a fresh backend after the announced restart, and the pane version lines with no mismatch line
  - RESEARCH open items A3 and A5 settled from the Windows PC
  - The install line that puts the frozen Phase 3 test pane on a Desktop machine while plugin.js holds the Phase 4 board pane
affects: [03-11, 03-12, phase-07-DEV-04]

# Actuals (#2632)
actuals:
  tokens: 1600
  tasks: 3
  commits: 0
plan_head_before: 490016e2c71dea95adf3579b63cacab282fbfd52
plan_head_after: 490016e2c71dea95adf3579b63cacab282fbfd52

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Windows install: `scp -O` copies the script over the Windows ssh alias; the plain scp fallback did not run. The script resolves `%LOCALAPPDATA%\\hermes` as the Desktop home."
    - "Frozen test pane install: `-RemotePath /home/theo/share/hermes-todo/phase3-test-pane.plugin.js` plus Reload desktop plugins swaps the Desktop half with no backend restart"

key-files:
  created:
    - .planning/phases/03-rest-router-and-client-install-spike/03-10-SUMMARY.md
  modified: []

key-decisions:
  - "The Windows live test uses the frozen Phase 3 test pane from ~/share/hermes-todo, not plugin.js at HEAD, because plugin.js now holds the Phase 4 board pane."
  - "The frozen test pane root div gets `userSelect: 'text'` so Theo can copy the pane lines; the file is outside the repo and no commit covers it."

patterns-established:
  - "Every hash Theo reports is compared with a devpc sha256sum before the task passes; a hash that differs from the plan's expected value is traced to a commit before any next request."

requirements-completed: [DEV-05, API-03]

coverage:
  - id: D1
    description: "Windows install half of success criterion 1: scp -O fetches the script, the sha256 line equals a devpc hash, installed ends in desktop-plugins\\hermes-session-tasks\\plugin.js, and the home line shows %LOCALAPPDATA%\\hermes"
    requirement: DEV-05
    verification:
      kind: manual_procedural
      ref: "Theo's paste from the Windows PC: sha256 91b46447...daf0e2 equals sha256sum plugin/desktop/plugin.js at HEAD 490016e; home C:\\Users\\TheoDeyle\\AppData\\Local\\hermes"
      status: pass
  - id: D2
    description: "Announced Desktop restart on the Windows PC: a hermes serve --isolated process started after the request time W1, and Claude stopped no process"
    requirement: DEV-05
    verification:
      kind: manual_procedural
      ref: "ps -eo pid,lstart,args at 12:45:56 local: pid 1040717 started Nov 2 12:45:41, after W1 2026-11-02T12:42:56-05:00; pid 385989 gone; pid 2231852 unchanged"
      status: pass
  - id: D3
    description: "The test pane on the Windows PC shows backend 0.1.0, api 1 and pane 0.1.0, api 1 with no mismatch line and write test not run (success criteria 1 and 4)"
    requirement: API-03
    verification:
      kind: human
      status: pass

# Metrics
duration: about 1h (waiting for Theo on the Windows PC)
completed: 2026-11-02
status: complete
---

# Phase 3 Plan 10: Windows PC install, announced restart and pane lines Summary

**The test pane runs on the Windows PC: the install hash matched devpc, a fresh backend started after the announced restart, and the pane shows `backend 0.1.0, api 1` and `pane 0.1.0, api 1` with no mismatch line.** The first install copied the Phase 4 board pane by mistake; a second install with `-RemotePath` put the frozen Phase 3 test pane in place.

Local time is UTC-5. The orchestrator ran the three requests with Theo on 2026-11-02 and recorded the evidence below.

## Task 1: Theo runs the install command on the Windows PC

Theo's ssh name for devpc on the Windows PC is `devpc-ts`. He put it in place of each `devpc` in the plan's line. `scp -O` copied the script (100%, 7256 bytes). The plain `scp` fallback did not run.

Lines the script printed:

```
home: C:\Users\TheoDeyle\AppData\Local\hermes
slot: C:\Users\TheoDeyle\AppData\Local\hermes\desktop-plugins\hermes-session-tasks
copy: devpc-ts:/home/theo/local_repo/hermes-session-tasks/plugin/desktop/plugin.js
installed: C:\Users\TheoDeyle\AppData\Local\hermes\desktop-plugins\hermes-session-tasks\plugin.js
sha256: 91b46447782493a5f08327af0b98c26acb07de1621eb37e9c0f3eb47d9daf0e2
```

Checks:

| Check | Result |
|-------|--------|
| `sha256:` equals a devpc hash | Yes. `sha256sum plugin/desktop/plugin.js` at HEAD `490016e` prints `91b46447...daf0e2`. This is the Phase 4 board pane, not the 03-08 hash `4e42968a...2c63b7` and not the 03-09 hash `5dda4c37...acfa`, because plugin.js changed in plan 03-09 and in Phase 4. |
| `installed:` ends in `desktop-plugins\hermes-session-tasks\plugin.js` | Yes. |
| `home:` line | `C:\Users\TheoDeyle\AppData\Local\hermes`, which is `%LOCALAPPDATA%\hermes`. |

RESEARCH open items settled:

- A3: Desktop on Windows resolves `%LOCALAPPDATA%\hermes` as its home, and the script prints it.
- A5: the Windows ssh name is `devpc-ts`, and `scp -O` works with a relative target in `$HOME`.

## Task 2: announced Desktop restart on the Windows PC

Request time W1: `2026-11-02T12:42:56-05:00`. The request named the restart and its effect before Theo quit Desktop.

Hermes `serve` processes before W1 (`ps -eo pid,lstart,args`, local time):

| PID | Started (local) | Role |
|-----|-----------------|------|
| 385989 | Nov 2 08:27:22 | Windows backend, `hermes serve --isolated --host 127.0.0.1 --port 0 --ssh-session-token-file ...` |
| 2231852 | Nov 1 08:01:44 | Mac backend, same command shape |

After Theo reported Desktop open again, `ps` at 12:45:56 local showed:

| PID | Started (local) | Change |
|-----|-----------------|--------|
| 1040717 | Nov 2 12:45:41 | New. Started after W1. |
| 2231852 | Nov 1 08:01:44 | Unchanged. |
| 385989 | gone | Ended by the Desktop quit. |

A `serve --isolated` process started after W1. Claude stopped no process. The Mac backend was not touched.

## Task 3: Theo opens the test pane on the Windows PC and reports its lines

First attempt: the pane showed the Phase 4 board pane ("open a session to see its items"), not the test pane. Cause: the Task 1 line used the default `RemotePath`, which copies `plugin/desktop/plugin.js` at HEAD, and HEAD holds the Phase 4 board pane. The 04-09 SUMMARY handoff says plans 03-10 and 03-11 install the frozen test pane with `-RemotePath /home/theo/share/hermes-todo/phase3-test-pane.plugin.js`.

Theo asked for the pane text to be selectable. The orchestrator added `style: { userSelect: 'text' }` to the root div of the frozen test pane file `/home/theo/share/hermes-todo/phase3-test-pane.plugin.js`. `node --check` passed.

| File state | SHA-256 |
|------------|---------|
| Before the edit (equals plugin.js at commit `17d7082`) | `5dda4c37a622e5ef88d8d1fb0c6dfc9fa854999d4fd48a350d4169d135deacfa` |
| After the edit | `d7fcfcb7906df87bb02bb93dba7432681b61100258c30d211dbf6c5384392e04` |

The file is outside the repo, so no commit covers it.

Second install line on the Windows PC:

```
Set-Location $HOME; pwsh -NoProfile -File .\install-desktop.ps1 -DevpcHost devpc-ts -RemotePath /home/theo/share/hermes-todo/phase3-test-pane.plugin.js
```

Then "Reload desktop plugins" from the command palette. No second backend restart was needed: the pane file loads on the Windows side. Theo did not paste the second install lines; the pane lines below prove the install.

Pane lines Theo pasted:

```
backend 0.1.0, api 1
pane 0.1.0, api 1
no session focused
agent event: none yet
pane event: none yet
write test: not run
board is empty
```

Match: backend and pane versions equal, no mismatch line, write test not run. Success criteria 1 and 4 hold on the Windows PC.

## Must-haves evidence

| Must-have | Evidence | Result |
|-----------|----------|--------|
| Install fetches the script with `scp -O` and the `sha256:` line equals a devpc hash; the `home:` line shows the Desktop home | Task 1: `scp -O` copied 7256 bytes; hash `91b46447...daf0e2` equals devpc at HEAD `490016e`; home `C:\Users\TheoDeyle\AppData\Local\hermes` | pass, with the hash traced to Phase 4 (see deviations) |
| The restart request names the restart and its effect first | Task 2 request text named the backend restart and the end of any running chat turn | pass |
| After Theo reports Desktop open, `ps` shows a `serve --isolated` process that started after W1 | pid 1040717 started 12:45:41, W1 12:42:56 | pass |
| The pane shows `backend 0.1.0, api 1`, `pane 0.1.0, api 1` and no mismatch line | Task 3 pane lines | pass |
| Each request holds one action and one report; no run.sh, check.sh or harness named | Three requests, each one action and one report | pass |
| Prohibition: Claude stops, kills or starts no `hermes serve` or gateway process | Process changes came from Theo's Desktop quit and reopen only | held |
| Prohibition: no code name, GSD term or reply word in a request | Requests used plain words | held |

## Deviations from Plan

**1. [Rule 1 - Wrong assumption] The Task 1 line installed the Phase 4 board pane**
- **Found during:** Task 3
- **Issue:** The plan's Task 1 line used the default `RemotePath`, which copies `plugin/desktop/plugin.js` at HEAD. Since plan 04-01, that file is the Phase 4 board pane, not the Phase 3 test pane. The plan's expected hash (the 03-08 value) was also out of date: plugin.js changed in plan 03-09 and in Phase 4.
- **Fix:** A second install with `-RemotePath /home/theo/share/hermes-todo/phase3-test-pane.plugin.js`, then Reload desktop plugins. The pane lines confirm the test pane.
- **Files modified:** none in the repo
- **Verification:** Task 3 pane lines
- **Committed in:** the SUMMARY commit

**2. [Rule 1 - Live-test defect] Pane text not selectable**
- **Found during:** Task 3
- **Issue:** Theo could not select the pane text to copy the lines.
- **Fix:** `style: { userSelect: 'text' }` on the root div of the frozen test pane file (standing rule 33: a defect flagged in a live test is fixed in the same turn). Hash before `5dda4c37...acfa`, after `d7fcfcb7...92e04`.
- **Files modified:** `/home/theo/share/hermes-todo/phase3-test-pane.plugin.js` (outside the repo)
- **Verification:** `node --check` passed; Theo pasted the pane lines.
- **Committed in:** none; the file is outside the repo

**3. [Rule 1 - Record] The Windows ssh name is `devpc-ts`**
- **Found during:** Task 1
- **Issue:** The plan's line names the host `devpc`. On the Windows PC the ssh name is `devpc-ts`. Theo substituted it.
- **Fix:** Recorded: every Windows PC command uses `devpc-ts`.
- **Files modified:** none
- **Verification:** Theo's `copy:` line reads `devpc-ts:/home/theo/...`.
- **Committed in:** the SUMMARY commit

**Total deviations:** 3 (one wrong assumption, one live-test defect, one record; no repo code change). **Impact:** none on the plan's goals.

## Prohibitions check

- No `hermes serve` process and no gateway was stopped, started or restarted by Claude. Theo's Desktop quit ended pid 385989 and his reopen started pid 1040717.
- No repo file changed. The only edit was to the frozen test pane file in `~/share/hermes-todo`.
- Each request used plain words, one action and one report, no code name, no GSD term, no reply word.

## Carry forward

- Plan 03-11 runs the agent write and the write test on the Windows PC with the test pane at hash `d7fcfcb7...92e04`. Every Windows PC command uses `devpc-ts`.
- Plan 03-12 or the phase close: after the Windows live test, the Windows PC needs the real board pane back. One line for Theo: the Task 1 install line with the default `RemotePath` (`Set-Location $HOME; pwsh -NoProfile -File .\install-desktop.ps1 -DevpcHost devpc-ts`), then Reload desktop plugins. The same applies to the Mac if it still holds the test pane.

## Task Commits

None. No task changed a repo file; the docs commit carries this summary.

## Known Stubs

None.

## Threat Flags

None. No new surface. T-03-26 and T-03-27 mitigations held: the restart was announced first, and the script printed the home and wrote only into the plugin slot.

## Next Phase Readiness

Plan 03-11 (Windows PC part 2) can start. The test pane is installed on the Windows PC and attached to backend pid 1040717. No backend restart is needed while no plugin Python file changes.

---
*Phase: 03-rest-router-and-client-install-spike*
*Completed: 2026-11-02*

## Self-Check: PASSED

- FOUND: `.planning/phases/03-rest-router-and-client-install-spike/03-10-SUMMARY.md`
- FOUND: `home:` line in the Task 1 block
- No task commit expected: no task changed a repo file.
