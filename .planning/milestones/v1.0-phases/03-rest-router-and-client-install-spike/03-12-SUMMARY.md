---
phase: 03-rest-router-and-client-install-spike
plan: 12
subsystem: cleanup
tags: [hermes-plugin, cleanup, data-db, sqlite, gates, AGNT-01, DEV-05]

# Dependency graph
requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: the test board root lists from plans 03-07, 03-09 and 03-11; the REST routes, the stale reply and the board.updated event (plans 03-01 to 03-06)
provides:
  - The 6 test boards deleted from the real data.db on Theo's recorded yes, with the row counts before and after on record
  - The final gates green on HEAD: check.sh, hermes plugins validate, hermes plugins doctor --ci
affects: [phase-04, phase-07-DEV-04]

# Actuals (#2632)
actuals:
  tokens: 2500
  tasks: 2
  commits: 0
plan_head_before: c6e70f1ef9c408745125a7f049a02839f33e4cad
plan_head_after: c6e70f1ef9c408745125a7f049a02839f33e4cad

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A production-data deletion runs behind a grep of the recorded yes line, in one BEGIN IMMEDIATE transaction with parameterised statements, between two dry runs"

key-files:
  created:
    - .planning/phases/03-rest-router-and-client-install-spike/03-12-SUMMARY.md
  modified: []

key-decisions:
  - "The cleanup script lives in the session scratchpad, not in the repo: it is a one-time act on one data file."
  - "Items and journal rows were not deleted by name: PRAGMA foreign_keys = ON made them cascade from the boards rows, and an orphan check after the apply found zero stray rows."

patterns-established:
  - "Production-data step: ask once, record the answer, dry run, apply behind the recorded yes, dry run again"

requirements-completed: [AGNT-01, DEV-05]

coverage:
  - id: D1
    description: "Theo answered the one plain question and the SUMMARY recorded it before Task 2 ran"
    requirement: AGNT-01
    verification:
      kind: human
      ref: "Theo's answer: yes, recorded 2026-11-02 before the first dry run"
      status: pass
  - id: D2
    description: "The 6 listed roots are gone, no other board changed: 23 boards before, 17 after, zero orphan rows"
    requirement: AGNT-01
    verification:
      kind: test
      ref: "cleanup_boards.py --dry-run before and after; orphan check 0 0 0"
      status: pass
  - id: D3
    description: "check.sh, validate and doctor --ci pass on HEAD after the cleanup"
    requirement: DEV-05
    verification:
      kind: test
      ref: "check: all ok; Validation passed.; doctor exit 0"
      status: pass

# Metrics
duration: about 15 min of executor time after Theo's answer
completed: 2026-11-02
status: complete
---

# Phase 3 Plan 12: Test board cleanup and final gates Summary

**The 6 test boards are gone from the real data.db on Theo's recorded yes: 23 boards before, 17 after, zero rows left for every listed root, and the three final gates pass on HEAD.**

Local time is UTC-5. The orchestrator ran Task 1 with Theo on 2026-11-02. The executor ran Task 2 at 18:35 UTC with `.venv-py3.14/bin/python -I` (SQLite 3.53.1) against `~/.hermes/plugin-data/hermes-session-tasks/data.db`. No other file was touched.

## Task 1: the delete question

Theo's answer: yes ("yes", 2026-11-02, after he asked "You sure they hold only test data and not actual data?" and saw every item of the 6 boards)

## Root list (6 boards)

| Root id | Source |
|---------|--------|
| `local-f3aa9e18981c55542e65bd9f63736a04d0010a85186e746064256bcb29bcc4c2` | plan 03-07 agent test chat r1-1 |
| `local-fe709b83895ec2ca3ad1ff17ea958c65ba470b05af5ea11bede3e64323870fdf` | plan 03-07 agent test chat r1-2 |
| `local-aa471eefa70ab9fb2b8b158bddbdf1c86f67af25b37c16704186812c071b2bf7` | plan 03-07 agent test chat r1-3 |
| `20261101_162121_506689` | plan 03-09 Mac test chat (emptied by Theo, rev 6) |
| `20261102_130511_60c13f` | plan 03-11 Windows test chat |
| `20261102_130449_f33b04` | plan 03-11 Windows first chat (one pane write) |

## Task 2: dry run, delete, recount, gates

The script `cleanup_boards.py` sits in the session scratchpad (not tracked). It opens the data file with `timeout=5.0`, `PRAGMA busy_timeout = 5000` and `PRAGMA foreign_keys = ON`. `--dry-run` counts rows per root with parameterised `SELECT COUNT(*)` statements. `--apply` runs one `BEGIN IMMEDIATE` transaction: `DELETE FROM aliases WHERE root_id = ?` per root, then `DELETE FROM boards WHERE root_id = ?` per root, then `COMMIT`; any error rolls back.

### First dry run (before the delete)

```
root_id                                                                board items changes aliases
local-f3aa9e18981c55542e65bd9f63736a04d0010a85186e746064256bcb29bcc4c2 yes       7      14       1
local-fe709b83895ec2ca3ad1ff17ea958c65ba470b05af5ea11bede3e64323870fdf yes       7      14       1
local-aa471eefa70ab9fb2b8b158bddbdf1c86f67af25b37c16704186812c071b2bf7 yes       7      14       1
20261101_162121_506689                                                 yes       0       6       1
20261102_130511_60c13f                                                 yes       2       2       1
20261102_130449_f33b04                                                 yes       1       1       1
total boards: 23
```

### Apply

Command: `grep -q "^Theo's answer: yes" .planning/phases/03-rest-router-and-client-install-spike/03-12-SUMMARY.md && .venv-py3.14/bin/python -I <scratchpad>/cleanup_boards.py --apply <6 root ids>`

Output: `deleted: 6 alias rows, 6 boards rows (items and changes cascaded)`, exit 0. Run once.

### Second dry run (after the delete)

```
root_id                                                                board items changes aliases
local-f3aa9e18981c55542e65bd9f63736a04d0010a85186e746064256bcb29bcc4c2 no        0       0       0
local-fe709b83895ec2ca3ad1ff17ea958c65ba470b05af5ea11bede3e64323870fdf no        0       0       0
local-aa471eefa70ab9fb2b8b158bddbdf1c86f67af25b37c16704186812c071b2bf7 no        0       0       0
20261101_162121_506689                                                 no        0       0       0
20261102_130511_60c13f                                                 no        0       0       0
20261102_130449_f33b04                                                 no        0       0       0
total boards: 17
```

Orphan check after the delete (read only): items, changes and aliases with no boards row: `0 0 0`. The total dropped by exactly 6, the number of listed roots that had a boards row. The 17 boards left are the ten Phase 2 test boards and Theo's real sessions.

### Final gates on HEAD `c6e70f1`

| Gate | Command | Result |
|------|---------|--------|
| check.sh | `./scripts/check.sh` | `check: python 3.11 ok`, `832 passed in 195.72s`, `check: python 3.14 ok`, `check: all ok`, exit 0 |
| validate | `timeout 120 hermes plugins validate .../plugin` | `Validation passed.`, exit 0 |
| doctor | `timeout 180 hermes plugins doctor .../plugin --ci` | `OK: runtime discovery, manifest parsing, import, and registration passed`, `registrations: 2 tool(s), 4 hook(s)`, exit 0 |

## Must-haves evidence

| Must-have | Evidence | Result |
|-----------|----------|--------|
| One plain question with one recommendation before any deletion | Task 1 ran with the real count (6); Theo asked one follow-up and answered yes | pass |
| `Theo's answer:` line on record before Task 2 | The line above, written by the orchestrator before the executor started; the apply command ran behind `grep -q "^Theo's answer: yes"` | pass |
| Dry run, one write transaction, second dry run with zero rows | The two dry-run outputs above; apply output `6 alias rows, 6 boards rows` | pass |
| No other board touched: count drops by the number of listed roots with a boards row | 23 before, 17 after, 6 roots had a boards row; orphan check 0 0 0 | pass |
| check.sh, validate and doctor --ci pass on HEAD | Gate table above | pass |

## Prohibitions

| Statement | Evidence |
|-----------|----------|
| No board deleted without Theo's recorded yes | The apply command is chained after the grep; the grep matched |
| The cleanup never touches state.db or any Hermes file outside data.db | The script opens one path: `~/.hermes/plugin-data/hermes-session-tasks/data.db`; the script makes no other file call |

## Observations

- The Windows PC still has the frozen Phase 3 test pane installed. The install line with the default `RemotePath` puts the real board pane back: `Set-Location $HOME; pwsh -NoProfile -File .\install-desktop.ps1 -DevpcHost devpc-ts`, then Reload desktop plugins. Carried forward to the orchestrator.
- The first dry-run call passed the 6 ids through one zsh variable; zsh did not split it, so the script saw one long id. The run was repeated with explicit arguments. No data changed on the first call: a dry run only reads.
- A Desktop backend that polls one of the deleted test chats now gets an empty board. No write follows unless Theo acts in that chat.

## Deviations from Plan

None - plan executed exactly as written.

## Task Commits

No code commit: the plan changed no repo file. The docs commit for this SUMMARY, ROADMAP.md and STATE.md follows.

## Known Stubs

None.

## Threat Flags

None. T-03-29 mitigated as planned: recorded yes, grep guard, parameterised SQL, one BEGIN IMMEDIATE transaction, two dry runs, project Python with SQLite 3.53.1.

## Next Phase Readiness

Phase 3 is complete on this plan. Phase 4 (the board pane) can start. The Windows PC pane swap above is the one open hand-off.

---
*Phase: 03-rest-router-and-client-install-spike*
*Completed: 2026-11-02*

## Self-Check: PASSED

- FOUND: `.planning/phases/03-rest-router-and-client-install-spike/03-12-SUMMARY.md`
- FOUND: HEAD c6e70f1 equals plan_head_before (no code commit, docs only)
- FOUND: the `Theo's answer: yes` line
