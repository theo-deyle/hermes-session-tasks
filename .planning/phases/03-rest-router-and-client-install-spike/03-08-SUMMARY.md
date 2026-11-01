---
phase: 03-rest-router-and-client-install-spike
plan: 08
subsystem: live-test
tags: [hermes-plugin, live-test, desktop-install, mac, sha256, gateway-decision, DEV-05]

# Dependency graph
requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: scripts/install-desktop.ps1 and the README install steps (plan 03-03); the test pane plugin/desktop/plugin.js with PLUGIN_VERSION and API_VERSION (plan 03-06); the 3 of 3 own-job result and the gateway restart record (plan 03-07)
provides:
  - Devpc gates green on HEAD 8502874 before Theo touches the Mac
  - T0, the plugin.js SHA-256 and the version values the Mac install must match
  - The process list before the Mac restart, and the gateway decision with the 03-07 restart recorded as a deviation
  - live_check.py, a read-only board check by time, for plans 03-09 and 03-10
affects: [03-09, 03-10, 03-12, phase-07-DEV-04]

# Actuals (#2632)
actuals:
  tokens: 2600
  tasks: 1
  commits: 0
plan_head_before: 85028740e8afbd12e647445e6830e04da18dfb25
plan_head_after: 85028740e8afbd12e647445e6830e04da18dfb25

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live board check: a stdlib script opens data.db with file:...?mode=ro as a URI and prints one JSON line per board updated after a given UTC time; it writes nothing"
    - "Expected values first: T0, SHA-256 and versions go on record before any request to Theo, so his reply is compared, never trusted"

key-files:
  created:
    - .planning/phases/03-rest-router-and-client-install-spike/03-08-SUMMARY.md
  modified: []

key-decisions:
  - "No messaging gateway restart in plan 03-08 or later in Phase 3. The one Phase 3 restart happened for plan 03-07 at 13:30 local on 2026-11-01 with Theo's go (pid 1270415 to pid 2635829); DEV-04 in Phase 7 owns the next announced restart."
  - "Task 1 writes no repo file; the SUMMARY carries the evidence and the scratchpad holds live_check.py."

patterns-established:
  - "Times in data.db are UTC with a Z suffix; ps lstart prints local time (UTC-5 on 2026-11-01). Compare a board time with a UTC T0 only."

requirements-completed: []

coverage:
  - id: D1
    description: "Devpc gates: check.sh ends with check: all ok, hermes plugins validate passes, hermes plugins doctor --ci passes, 03-07 records 3 of 3"
    requirement: DEV-05
    verification:
      - kind: integration
        ref: "./scripts/check.sh (ran twice on HEAD 8502874: task verify and tracer gate re-run)"
        status: pass
      - kind: integration
        ref: "timeout 120 hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin"
        status: pass
      - kind: integration
        ref: "timeout 180 hermes plugins doctor /home/theo/local_repo/hermes-session-tasks/plugin --ci"
        status: pass
    human_judgment: false
  - id: D2
    description: "Versions agree across plugin.yaml, plugin.js and version.py, and the plugin.js SHA-256 is on record with T0"
    requirement: DEV-05
    verification:
      - kind: other
        ref: "sha256sum plugin/desktop/plugin.js; grep version: plugin/plugin.yaml; grep PLUGIN_VERSION, API_VERSION plugin/desktop/plugin.js; grep API_VERSION plugin/session_tasks/version.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Mac install half of success criterion 1: the sha256: line Theo reports equals the devpc hash (Task 2)"
    requirement: DEV-05
    verification: []
    human_judgment: true
    rationale: "Only Theo can run the install line on the Mac; Claude compares the reported hash after his reply"
  - id: D4
    description: "Announced Desktop restart on the Mac and a fresh serve --isolated process on devpc after R1 (Task 3)"
    requirement: DEV-05
    verification: []
    human_judgment: true
    rationale: "Only Theo can quit and reopen Hermes Desktop on the Mac; Claude checks the process list after his reply"

# Metrics
duration: 9min
completed: 2026-11-01
status: in-progress
---

# Phase 3 Plan 08: Mac install and announced Desktop restart Summary

**Task 1 done: devpc is green on HEAD 8502874, the expected plugin.js hash `4e42968a...2c63b7` and the versions 0.1.0 / API 1 are on record with T0, and live_check.py reads any board change after T0 without a write. Tasks 2 and 3 wait for Theo on the Mac.**

## Performance

- **Duration:** 9 min for Task 1 (18:45Z to 18:54Z on 2026-11-01)
- **Started:** 2026-11-01T18:45Z
- **Task 1 completed:** 2026-11-01T18:54Z
- **Tasks:** 1 of 3 (Tasks 2 and 3 are Theo's actions on the Mac)
- **Files modified:** 0 in the repo (evidence only)

## Task 1: end to end on devpc

### Step 1: gates

| Gate | Command | Result |
|------|---------|--------|
| check.sh | `./scripts/check.sh` | exit 0, last line `check: all ok`. Python 3.11: ruff, format, pyright 0 errors, 631 passed, coverage 97 percent. Python 3.14: ruff, format, pyright 0 errors, 631 passed. |
| validate | `timeout 120 hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin` | exit 0, `Validation passed.` All 16 checks pass (manifest, loadable `__init__.py` and `desktop/plugin.js`, capability probe, declared tools and hooks match, no collisions, security scan safe, desktop surface inside the SDK). Note line: `Isolation - runs in the plugin host (plugins.isolation: host)`, dashboard API served through the plugin host. |
| doctor | `timeout 180 hermes plugins doctor /home/theo/local_repo/hermes-session-tasks/plugin --ci` | exit 0, `OK: runtime discovery, manifest parsing, import, and registration passed`, 2 tools, 3 hooks, manifest `hermes-session-tasks 0.1.0 (standalone)`. |

Logs: `/tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/5289d997-ad4c-492a-ae9c-0ddec0033f59/scratchpad/{check,validate,doctor}.log`.

### Step 2: 03-07 result

`03-07-SUMMARY.md` records `Round 1 rate: 3 of 3. Success criterion 0 is met.` with runs r1-1, r1-2 and r1-3 each at 7 of 7 checked. Confirmed.

### Step 3: T0, hash and versions

| Value | Result |
|-------|--------|
| T0 (UTC) | `2026-11-01T18:49:52.631996Z` |
| HEAD | `8502874` on `main`, working tree clean except the orchestrator's `.planning/config.json` and `.planning/state.json` |
| SHA-256 of `plugin/desktop/plugin.js` | `4e42968a329d4d76efdc98898f5b23ffc520952405a830c4bfbdf3b16b2c63b7` |
| `plugin/plugin.yaml` version | `0.1.0` (line 2) |
| `plugin/desktop/plugin.js` PLUGIN_VERSION | `'0.1.0'` (line 12) |
| `plugin/desktop/plugin.js` API_VERSION | `1` (line 13) |
| `plugin/session_tasks/version.py` API_VERSION | `1` (line 16) |

The three version values agree: backend 0.1.0 equals the pane constant, and API 1 equals on both sides.

### Step 4: Hermes serve and gateway processes before the Mac restart

`ps -eo pid,lstart,args`, filtered to Hermes `serve` and `gateway`. Start times are local (UTC-5). The argv of a `serve --isolated` process starts with a long inline Python launcher; the table keeps the tail.

| PID | Started (local) | Args (tail) |
|-----|-----------------|-------------|
| 2231852 | Sun Nov 1 08:01:44 2026 | `serve --isolated --host 127.0.0.1 --port 0 --ssh-session-token-file /home/theo/.hermes/desktop-ssh/dfda277e4fcadaab5b5106d883d97e19/fd26df8d34535a6a.token --ssh-owner-nonce fd26df8d34535a6a` |
| 2514051 | Sun Nov 1 11:50:43 2026 | `serve --isolated --host 127.0.0.1 --port 0 --ssh-session-token-file /home/theo/.hermes/desktop-ssh/f3619ffc6faed70a5b6d5c9de87e0711/0f701d748ac923ba.token --ssh-owner-nonce 0f701d748ac923ba` |
| 2635829 | Sun Nov 1 13:30:32 2026 | `python3 -m hermes_cli.main --profile default gateway run --quiet` |

Three processes: two Desktop backends (`serve --isolated`) and one messaging gateway (`gateway run`). Both Desktop backends started before any plan 03-08 action. Task 3 expects a new `serve --isolated` process with a start time after R1.

### Step 5: gateway decision and evidence

**Decision:** no messaging gateway restart in this plan or in the rest of Phase 3.

**Deviation on the plan's truth "The messaging gateway is not restarted in Phase 3":** that truth is already false. The orchestrator restarted the owner gateway once, at 13:30:32 local on 2026-11-01 (pid 1270415 to pid 2635829), with Theo's go, before plan 03-07. Reason: plan 03-07's `hermes chat --oneshot` runs attach to the owner gateway, and that gateway had loaded the plugin before the `pre_llm_call` hook existed, so the own-job measurement needed the hook in memory. The restart happened once, for 03-07, with Theo's approval. No further restart in this phase.

Evidence for the rest of the decision:

| Reason | Evidence |
|--------|----------|
| The running gateway holds the plugin with the hook loaded | `gateway run` line above: pid 2635829, started 13:30:32 local, after the hook landed (plan 03-01, commit `0d7f38e` and later). 03-07's hook-load check read the exact NUDGE_LINE from this gateway. |
| Desktop sessions run in separate `hermes serve --isolated` processes | The two `serve --isolated` lines above. `hermes_cli/process_identity.py:157-159`: `serve --isolated` opted out of the host singleton, "Desktop's SSH backend for another machine". |
| Headless own-job runs start their own process | 03-07 pattern: one new `hermes chat --oneshot` process per run, attached to the owner gateway. |
| No Phase 3 success criterion uses a messaging platform session | Criteria 0 to 5 use headless runs, the Mac Desktop and the Windows PC Desktop. |
| The board schema has no change in this phase | `git log --format='%h %ad %s' -- plugin/session_tasks/schema.py | head -n 1` prints `72f2930 Fri Oct 30 19:19:51 2026 -0400 feat(01-02): first end to end path from session id to markdown`. Zero commits touch `schema.py` in the range `81916ab..HEAD` (Phase 3). |
| The announced gateway restart belongs to Phase 7 | DEV-04 (Phase 7) owns it. |

Threat T-03-32 stays accepted: the gateway's in-memory plugin copy is consistent and matches the schema on disk.

### Step 6: live_check.py

Path: `/tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/5289d997-ad4c-492a-ae9c-0ddec0033f59/scratchpad/live_check.py` (session scratchpad, not tracked).

Stdlib only. Opens `~/.hermes/plugin-data/hermes-session-tasks/data.db` with `sqlite3.connect("file:<path>?mode=ro", uri=True)`. Prints one JSON line per board whose `updated_at` is later than the given ISO time: `root_id`, `rev`, `updated_at`, and `items` (`id`, `text`, `checked`, `rev`, `updated_by`) ordered by parent then position. Writes nothing. `grep -c "mode=ro"` on the file prints 1.

Run with T0:

```
$ .venv-py3.14/bin/python -I live_check.py 2026-11-01T18:49:52.631996Z
no board updated after 2026-11-01T18:49:52.631996Z   (stderr)
exit 0
```

Proof that it reads boards (run with an earlier time, 2026-11-01T13:00:00Z): three lines, the 03-07 boards `local-f3aa9e18...` rev 2 (updated 18:37:14Z), `local-fe709b83...` rev 3 (18:38:18Z) and `local-aa471eef...` rev 2 (18:39:26Z), each with 7 items. Exit 0. `data.db` mtime stayed `2026-11-01 13:39:26 -0500` after both runs, and `data.db-wal` is 0 bytes.

Note: `updated_at` in data.db is UTC with a Z suffix. ps `lstart` is local time. T0 and every later check time use `date -u`.

### Acceptance criteria

| Criterion | Result |
|-----------|--------|
| SUMMARY holds T0, the plugin.js SHA-256, the equal version values, the process list, the gateway decision with evidence lines, and the first live_check.py output | PASS, sections above |
| live_check.py exists in the scratchpad and holds `mode=ro` | PASS, `grep -c` prints 1 |

### Tracer gate

Auto mode is active (`workflow._auto_chain_active: true`). The Task 1 `<verify>` ran again after the task: `./scripts/check.sh` exit 0 with `check: all ok` (log `check2.log`), `hermes plugins validate` exit 0 with `Validation passed.` (log `validate2.log`). No code changed between the two runs.

## Task Commits

Task 1 changed no repo file, so it has no task commit. `commits: 0` is measured: `git rev-list --count 8502874..HEAD` printed 0 before the SUMMARY commit. The SUMMARY commit follows this file.

## Decisions Made

- No messaging gateway restart in this plan or later in Phase 3 (step 5). The 03-07 restart is recorded as a deviation, not as a Phase 3 practice.
- live_check.py orders items by parent then position, so a parent's children follow the parents block. Plan 03-09 reads item ids, not order, so this is enough.

## Deviations from Plan

**1. [Rule 1 - Record] The gateway restart for plan 03-07**
- **Found during:** Task 1, step 5
- **Issue:** The plan's truth "The messaging gateway is not restarted in Phase 3" was false before this plan started. The orchestrator restarted the owner gateway at 13:30:32 local on 2026-11-01 (pid 1270415 to pid 2635829) with Theo's go, so the 03-07 own-job runs hit a gateway that had the `pre_llm_call` hook in memory.
- **Fix:** Recorded as a one-time, approved restart for 03-07. The decision for this plan and the rest of Phase 3 stays: no further restart. The other evidence (schema.py unchanged, Desktop backends are `serve --isolated`, DEV-04 in Phase 7) holds.
- **Files modified:** none
- **Verification:** the `gateway run` line in step 4 shows pid 2635829 with start time 13:30:32; 03-07-SUMMARY records the same pid and time.
- **Committed in:** the SUMMARY commit

**Total deviations:** 1 (a record, no code change). **Impact:** none on the plan's tasks; the gateway decision text changes from "never in Phase 3" to "once, for 03-07, with approval; no further restart".

## Prohibitions check

- No `hermes serve` process and no gateway was stopped, started or restarted by this executor. No Hermes setting changed.
- data.db was opened read-only (`mode=ro`) only. No board was deleted or changed; mtime unchanged.
- The Task 2 request below uses plain words, no code name, no GSD term, no reply word.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. No new surface; the scratchpad script reads one local file.

## Checkpoint: waiting for Task 2

Task 1 is green and recorded. Task 2 is a human action on the Mac: Theo runs the install line in PowerShell 7 and reports the printed lines. The values to compare with his reply:

| Expected | Value |
|----------|-------|
| `sha256:` line | `4e42968a329d4d76efdc98898f5b23ffc520952405a830c4bfbdf3b16b2c63b7` |
| `installed:` path ends in | `desktop-plugins/hermes-session-tasks/plugin.js` |
| `home:` line | record as reported |
| T0 | `2026-11-01T18:49:52.631996Z` |

Task 3 (announced Desktop restart) follows the hash match. R1 and the post-restart process list go in this file when the next dispatch continues.

## Self-Check: PASSED

- FOUND: `.planning/phases/03-rest-router-and-client-install-spike/03-08-SUMMARY.md`
- FOUND: `/tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/5289d997-ad4c-492a-ae9c-0ddec0033f59/scratchpad/live_check.py` with `mode=ro`
- No task commit expected: Task 1 changed no repo file; the docs commit carries this summary.

---
*Phase: 03-rest-router-and-client-install-spike*
*Task 1 completed: 2026-11-01*
