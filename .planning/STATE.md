---
gsd_state_version: "1.0"
current_phase: 3
current_phase_name: REST router and client install spike
status: executing
stopped_at: Completed 03-10-PLAN.md
last_updated: "2026-11-02T17:57:53.417Z"
last_activity: 2026-11-02
last_activity_desc: Phase 05 complete, transitioned to Phase 3
state_head: 490016e2c71dea95adf3579b63cacab282fbfd52
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 41
  completed_plans: 39
  percent: 57
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-30)

**Core value:** Items the agent lists for Theo stay visible and editable in the pane for the whole session, so Theo never scrolls up or asks the agent to repeat itself.
**Current focus:** Phase 05 — Agent sees Theo's edits

## Current Position

Phase: 3 — REST router and client install spike
Plan: 11
Status: Ready to execute
Last activity: 2026-11-02 - Completed 03-10-PLAN.md, next is 03-11

Progress: [██████░░░░] 57%

## Performance Metrics

**Velocity:**
- Total plans completed: 29
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 6 | - | - |
| 02 | 7 | - | - |
| 04 | 9 | - | - |
| 05 | 7 | - | - |

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
| Phase 03 P02 | 4 min | 2 tasks | 12 files |
| Phase 03 P03-03 | 8 min | 3 tasks | 3 files |
| Phase 03 P03-04 | 5 min | 2 tasks | 4 files |
| Phase 03 P03-05 | 27 min | 2 tasks | 9 files |
| Phase 03 P03-06 | 22 min | 3 tasks | 5 files |
| Phase 03 P07 | 12min | 2 tasks | 0 files |
| Phase 03 P08 | 1h 36m | 3 tasks | 0 files |
| Phase 04 P01 | 6 min | 2 tasks | 5 files |
| Phase 04 P09 | 6 min | 2 tasks | 3 files |
| Phase 04 P02 | 24 min | 3 tasks | 4 files |
| Phase 04 P03 | 12 min | 2 tasks | 1 files |
| Phase 04 P04-04 | 20 min | 3 tasks | 2 files |
| Phase 04 P05 | 15 min | 3 tasks | 2 files |
| Phase 04 P06 | 14 min | 3 tasks | 4 files |
| Phase 04 P07 | 45 min | 3 tasks | 2 files |
| Phase 05 P01 | 40 min | 3 tasks | 12 files |
| Phase 05 P02 | 55 min | 3 tasks | 6 files |
| Phase 05 P03 | 25 min | 3 tasks | 6 files |
| Phase 05 P04 | 15 min | 3 tasks | 10 files |
| Phase 05 P05 | 20min | 3 tasks | 0 files |
| Phase 05 P06 | 8min | 3 tasks | 2 files |
| Phase 05 P07 | 23 min | 3 tasks | 2 files |
| Phase 03 P10 | 60 min | 3 tasks | 0 files |

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
- [Phase 03]: 03-02: GET /board, GET /boards and POST /board/edit ship in plugin_api.py; every edit outcome is HTTP 200 with ok true or false, transport faults keep 4xx; EditBody forbids extra fields so confirmed returns 422 (D-24)
- [Phase 03]: 03-02: plugin_api.py loads core under key hermes_session_tasks_core; a new-batch subtask needs parent_ref, not parent_id
- [Phase 03]: 03-03: install script returns an exit code from Invoke-Main and calls exit only when not dot-sourced; relative -HermesHome and a directory at plugin.js are refused
- [Phase 03]: 03-03: Windows branch of the Desktop home rule is tested through Resolve-HermesHome parameters on Linux only; real runs are plans 03-08 and 03-10
- [Phase 03]: 03-04: read_backend_version catches UnicodeDecodeError as well as OSError, so GET /meta never answers 5xx on a bad manifest
- [Phase 03]: 03-04: dashboard layout guard allows only stdlib, fastapi and pydantic at module level, never relative
- [Phase 03]: 03-05: board.updated payload is session_id, root_id, rev, actor only; listener bound per actor via events.listener; publish runs after commit and a fault never fails a write
- [Phase 03]: 03-05: the dispatch test stubs tui_gateway.server so the bare Hermes process does not import the gateway stack; the real broadcast_plugin_event stays in the path
- [Phase 03]: 03-06: the pane harness runs under node --experimental-vm-modules; RestRelay.base_url is bare and the test adds PREFIX
- [Phase 03]: 03-06: the pane drops a board reply for a session that is no longer focused; events read other chat until a board reply sets the root
- [Phase 03]: Round 1 passed 3 of 3 with the plan 03-01 NUDGE_LINE; no wording round, tool_text.py unchanged
- [Phase 03]: 03-08: no messaging gateway restart in the rest of Phase 3; the one Phase 3 restart was for 03-07 with Theo's go; DEV-04 in Phase 7 owns the next announced restart
- [Phase 03]: 03-08: a Desktop quit and reopen reattaches to the backend in backend.lock.json and starts no new process; only a backend restart refreshes the plugin Python half; every Mac command uses the SSH alias devbox
- [Phase 04]: Pane keeps every React hook in Pane; Header and ItemRow are stateless and the harness enforces it
- [Phase 04]: 04-09: -RemotePath defaults to the old literal; Test-RemotePath allows only absolute paths of [A-Za-z0-9._/-] because scp -O hands the path to a shell on devpc
- [Phase 04]: The probe plugin lives in tests/fixtures and never reaches a Desktop machine; the install script copies only plugin/desktop/plugin.js.
- [Phase 04]: The harness takes a peek capture for every POST, so later pane tests read the pane at write time through atWrite.
- [Phase 04]: Guards read class names only from className string literals and *_CLASS constants; a class in a template literal needs a *_CLASS constant to be scanned
- [Phase 04]: Pane keeps the newest accepted rev per session (revs map), so a queued write for an unfocused session sends its own base_rev
- [Phase 04]: 04-05: the empty state shows only after the focused board has loaded, so a loading board never flashes it
- [Phase 04]: 04-05: an orphan subtask renders as a top-level entry so no item ever disappears
- [Phase 04]: 04-06: the add write guard is a ref flag as well as state, because a stale render closure still reads busy false
- [Phase 04]: 04-06: the hidden plus button keeps its space with opacity-0 and stays in the tab order, since Desktop ships no group-hover:visible class
- [Phase 04]: 04-07: saveEdit reads the edit from a ref and clears it first, so Enter then blur sends one write; a stale or failed edit reopens with the typed text
- [Phase 04]: 04-07: the SDK ConfirmDialog has no Cancel focus option, so Enter confirms a parent delete (UI-SPEC Delete rule 4)
- [Phase 05]: 05-01: agent_seen_rev advances on an agent batch only when the agent was up to date before the batch
- [Phase 05]: 05-01: journal gap rule is count < JOURNAL_KEEP or oldest_rev <= agent_seen_rev
- [Phase 05]: 05-01: nudge.py deleted; NUDGE_LINE and its tests stay until the own-plan gate result is known
- [Phase 05]: 05-01: an uncovered journal gap gives the pointer line even with no visible Theo row
- [Phase 05]: 05-02: three arms run in twin test homes built from one allowlisted config, so quiet minus bare is the plugin alone; no secret file is used — The model provider reads the Claude Code store outside HERMES_HOME. The MCP servers, memory prefetch, skills and SOUL.md of the real home would otherwise add to the difference.
- [Phase 05]: 05-02: the optional reminder split is built now in delta_live.py — D-36 names the one reminder line as its fallback and the own-plan gate in 05-05 may need it. Plan 05-07 then needs no tool change in a live plan.
- [Phase 05]: Plan 05-03: board_read and a stale or not-found reply mark the board seen (they carry the whole board); an applied board_edit marks seen only through the plan 05-01 conditional advance; a delegate never marks seen.
- [Phase 05]: 05-04: a missing or non-string reason on on_session_delete removes nothing; alias rows go by session id or root id, a board only by exact root id
- [Phase 05]: 05-04: the contract snippet deletes a chain with include_compression_chain=True (the dashboard and Desktop path); plain delete_session removes only the tip row
- [Phase 05]: Own-plan gate passed 3 of 3 with the prompt section alone (RESEARCH A1 predicted a fail); plan 05-06 decides on NUDGE_LINE
- [Phase 05]: 05-06: own-plan test passed 3 of 3 without the one-line reminder; reminder text and its two tests removed, hooks.py unchanged, no second restart needed
- [Phase 05]: Token test judges input tokens per turn (difference between runs); session totals stay in the report. Measured: plugin 516 tokens per turn, notes 291 at turn 30 for 790 characters.
- [Phase 03]: 03-10: the Windows live test installs the frozen Phase 3 test pane with -RemotePath, because plugin.js at HEAD holds the Phase 4 board pane

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

Last session: 2026-11-02T17:57:52.942Z
Stopped at: Completed 03-10-PLAN.md
Resume file: None
