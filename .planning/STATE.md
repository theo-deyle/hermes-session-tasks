---
gsd_state_version: "1.0"
current_phase: 03
current_phase_name: REST router and client install spike
status: executing
stopped_at: Completed 03-01-PLAN.md
last_updated: "2026-11-01T04:15:17.952Z"
last_activity: 2026-10-31
last_activity_desc: Phase 02 complete, transitioned to Phase 3
state_head: 6381146b709d1734ac4dbf8e9b9ed6faccfc24b5
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 25
  completed_plans: 14
  percent: 29
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-30)

**Core value:** Items the agent lists for Theo stay visible and editable in the pane for the whole session, so Theo never scrolls up or asks the agent to repeat itself.
**Current focus:** Phase 03 — REST router and client install spike

## Current Position

Phase: 03 (REST router and client install spike) — EXECUTING
Plan: 1 of 12 complete (03-01 done)
Status: Executing Phase 3
Last activity: 2026-11-01 — Completed 03-01 (pre_llm_call nudge, own-job harness)

Progress: [███░░░░░░░] 29%

## Performance Metrics

**Velocity:**
- Total plans completed: 13
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 6 | - | - |
| 02 | 7 | - | - |

**Recent Trend:**
- Last 5 plans: none yet
- Trend: none yet

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 3 min | 2 tasks | 11 files |
| Phase 01 P02 | 4 min | 2 tasks | 11 files |
| Phase 01 P03 | 9 min | 3 tasks | 9 files |
| Phase 01 P04 | 8 min | 2 tasks | 3 files |
| Phase 01 P05 | 25 min | 3 tasks | 10 files |
| Phase 01 P06 | 10 min | 2 tasks | 3 files |
| Phase 02 P01 | 25 min | 2 tasks | 14 files |
| Phase 02 P02 | 20 min | 2 tasks | 6 files |
| Phase 02 P03 | 6 min | 2 tasks | 3 files |
| Phase 02 P04 | 25 min | 2 tasks | 9 files |
| Phase 02 P05 | 10 min | 3 tasks | 0 files |
| Phase 02 P06 | 60 min | 3 tasks | 0 files |
| Phase 02 P07 | 10 min | 3 tasks | 1 files |
| Phase 03 P01 | 9 min | 3 tasks | 14 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Research phases 1 and 2 merged into Phase 1, because research phase 2 held one requirement (STOR-06). Research phases 3 to 8 are Phases 2 to 7.
- [Roadmap]: TOOL-03, TOOL-04 and TOOL-05 (cross-session tools) moved to Phase 6. Phase 2 ships the read and edit tools only.
- [Roadmap]: DEV-04 (formal rollout) sits in Phase 7. Earlier live checks on devpc use the same Hermes CLI steps.
- [Roadmap]: Phases 2 and 3 need no strict order, but Phase 3 follows Phase 2 so the event check can use a real tool write.
- [Phase 01]: Core modules use relative imports only; the layout guards fail an absolute session_tasks import
- [Phase 01]: Lazy-import guard flags every non-stdlib import outside the public Hermes allowlist
- [Phase 01]: clean_text measures the 500 char cap on the sanitised text - The sanitised text is what the store keeps.
- [Phase 01]: An empty op batch writes nothing and returns Applied at the current rev - No board row appears from a no-op write.
- [Phase 01]: Journal writes one row per changed item per operation; changed_ids lists each id once
- [Phase 01]: Stale check runs before the no-op check, so a stale write of the current value returns Stale
- [Phase 01]: connect_path retries the WAL switch on database is locked, like hermes_cli.sqlite_util.open_db
- [Phase 01]: moved counts only lines that import; a skipped line counts once in skipped_empty or too_long - No line counts twice, so the import counts add up
- [Phase 01]: A line under a skipped or too-long top-level entry becomes top-level - No child attaches to the wrong parent
- [Phase 01]: hint_id is an int only for an id run of 18 digits or fewer, else None; the token strips at any length - int() on a pasted digit run never raises
- [Phase 01]: A delegate session resolves to its delegator root with kind delegate and gets no row of its own - Orchestrator decision 1. The delegator resolve may write the delegator's own alias or branch copy. The Phase 2 write policy for delegates stays open.
- [Phase 01]: A copied branch reports kind plain on later resolves; Board.forked_from keeps the origin - The alias branch to branch answers before any reader opens.
- [Phase 01]: The state.db digest in the contract test ignores an empty state.db-wal file - A read only SessionDB open makes SQLite create an empty WAL file. Real writes land as WAL frames, so the check still fails on a write.
- [Phase 01]: Coverage gate runs in the Python 3.11 leg only; fail_under stays 80 with 97 percent measured - The plan keeps the 3.14 leg without coverage; 197 tests pass on both
- [Phase 02]: Dispatch snippet links and enables the plugin before importing model_tools (import runs plugin discovery once)
- [Phase 02]: register lives in core wiring.py; plugin/__init__.py only re-exports it
- [Phase 02]: Hook blocks a board_edit call whose arguments do not parse, with the handler's rule text
- [Phase 02]: A reword with no board available is guarded (unknown author errs toward asking)
- [Phase 02]: Hook returns None for delegate and blank sessions because the handler refuses those writes
- [Phase 02]: Prompt section is one static 736 character str; skill description holds no colon
- [Phase 02]: board_edit sends base_rev 0 when absent: the parser requires base_rev for ops on existing items and adds are never stale
- [Phase 02]: after_write runs once after a changed write; a listener fault is logged and the applied result still returns (Phase 3 broadcast seam)
- [Phase 02]: 02-05: list call rate is 5 of 5 with the real model; own-job run made 0 todo_list calls, so success criterion 4 fails its second rule. No Hermes setting changed; one cost question about tools.tool_search.enabled off is in the 02-05 SUMMARY. — Plan rule: a miss on either half of criterion 4 is a measurement, recorded with one cost question for Theo.
- [Phase 02]: 02-05: success criterion 5 live half is met (remove, uncheck, unclear, bulk, reword of Theo's text, finish all pass). Ten test boards remain in the real data.db. — The plan allows no data.db write beyond the reword seed.
- [Phase 02]: A Desktop backend started before a plugin enable keeps the old plugin set until Desktop is reopened; a session created before the plugin loaded keeps its old system prompt, so the prompt section reaches only sessions created after the backend has the plugin (Phase 7 rollout).
- [Phase 03]: 03-01: nudge line is static text with the single digit 3; the board block escapes < in item lines and caps item lines at 2000 characters

### Pending Todos

- Edit PROJECT.md after discuss-phase: the Python line (3.11 and 3.14), the write result contract, and the "routes need a restart" wording (the first mount is hot, later code edits need a restart of every `serve` process).
- Reorder in the pane and in the agent tools is v2 (BORD-01). PROJECT.md still lists a reorder tool under "Pieces to build".

### Blockers/Concerns

- The devpc symlink delivers the Python half only. `desktop/plugin.js` must reach the Mac and the Windows PC by script. Phase 3 proves this path.
- The agent may never call the board tools if Hermes defers plugin tools behind a search step. Phase 2 measures the call rate.
- Event delivery over SSH to the Windows client was never tested. Polling covers it. Phase 3 proves it.
- The tool `session_id` and `focusedStoredSessionId` may differ after a context rotation. Phase 1 tests a forced `/compress`.
- A gateway restart drops live Desktop connections. The restart is announced before it happens (Phase 7).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261031-lbp | Ask rule: the agent asks only on its own initiative; Theo's explicit instruction is the permission | 2026-10-31 | aff0e66 | [261031-lbp-ask-rule-the-agent-asks-only-on-its-own-](./quick/261031-lbp-ask-rule-the-agent-asks-only-on-its-own-/) |
| 261031-uzq | Board holds the agent's own plan too: the agent writes its steps to the board and checks them off | 2026-10-31 | fbb003e | [261031-uzq-board-holds-the-agent-s-own-plan-too-the](./quick/261031-uzq-board-holds-the-agent-s-own-plan-too-the/) |

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-11-01T04:15:17.723Z
Stopped at: Completed 03-01-PLAN.md
Resume file: None
