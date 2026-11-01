---
phase: 03-rest-router-and-client-install-spike
plan: 05
subsystem: api
tags: [hermes, plugin-events, board-updated, fastapi, sqlite]

requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: "03-01 hook wiring and register(), 03-02 BoardApi and build(), 03-04 meta route"
provides:
  - "events.py: PLUGIN_ID, EVENT, Publisher, WriteListener, publish, listener"
  - "board.updated broadcast after every changed write from the agent tool (actor agent) and from POST /board/edit (actor user)"
  - "One WriteListener type (root_id, session_id, rev) shared by BoardTools.after_write and BoardApi.after_write"
affects: [03-06 test pane, 03-08 Mac install, 03-09, 03-10 Windows install, 03-11]

actuals:
  tokens: 4100
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Publish after commit through a bound listener; a publish fault logs one warning and returns"
    - "Lazy Hermes import inside the single adapter function (events.publish)"

key-files:
  created:
    - plugin/session_tasks/events.py
    - tests/test_events.py
  modified:
    - plugin/session_tasks/board_tools.py
    - plugin/session_tasks/board_api.py
    - plugin/session_tasks/wiring.py
    - tests/test_board_tools.py
    - tests/test_register.py
    - tests/hermes_dispatch_snippet.py
    - tests/test_hermes_dispatch.py

key-decisions:
  - "Payload is exactly session_id, root_id, rev, actor. It never holds item text."
  - "Listener is bound per actor with events.listener(actor, publisher), so tool and route share one type."
  - "The dispatch test stubs tui_gateway.server only, so the real broadcast_plugin_event and its name check stay in the path."

requirements-completed: [API-02]

coverage:
  - id: D1
    description: "A board_edit call through the registered handler and a POST /board/edit through a host-style load each reach broadcast_plugin_event once with session_id, root_id, rev and actor, using the default wiring"
    requirement: API-02
    verification:
      - kind: integration
        ref: "tests/test_events.py#test_tool_write_reaches_the_broadcast"
        status: pass
      - kind: integration
        ref: "tests/test_events.py#test_route_write_reaches_the_broadcast"
        status: pass
      - kind: integration
        ref: "tests/test_events.py#test_an_alias_session_publishes_its_own_id_and_the_root"
        status: pass
      - kind: integration
        ref: "tests/test_hermes_dispatch.py#test_hermes_dispatch_of_a_write_broadcasts_board_updated"
        status: pass
    human_judgment: false
  - id: D2
    description: "No event for an empty write, a repeat, a stale write, a rule error, a blank session or a delegate session; two changed writes give rising revs; the listener sees the committed rev"
    requirement: API-02
    verification:
      - kind: unit
        ref: "tests/test_events.py#test_no_event_without_a_change"
        status: pass
      - kind: unit
        ref: "tests/test_events.py#test_two_changed_writes_give_rising_revs"
        status: pass
      - kind: unit
        ref: "tests/test_events.py#test_the_listener_sees_the_committed_rev"
        status: pass
    human_judgment: false
  - id: D3
    description: "A publish fault or a missing hermes_cli never fails a write and logs one warning; the payload holds no board text"
    requirement: API-02
    verification:
      - kind: unit
        ref: "tests/test_events.py#test_publish_fault_keeps_the_tool_result"
        status: pass
      - kind: unit
        ref: "tests/test_events.py#test_publish_fault_keeps_the_route_reply"
        status: pass
      - kind: unit
        ref: "tests/test_events.py#test_missing_hermes_logs_and_returns"
        status: pass
      - kind: unit
        ref: "tests/test_events.py#test_payload_holds_no_text"
        status: pass
    human_judgment: false
  - id: D4
    description: "The wire name is plugin.hermes-session-tasks.board.updated, proven by the Hermes plugin_event_name function in the gateway venv"
    requirement: API-02
    verification:
      - kind: integration
        ref: "uv run pytest -m hermes tests/test_events.py -q -rs"
        status: pass
    human_judgment: false
  - id: D5
    description: "A Desktop client receives the event on each machine (server side only is proven here)"
    verification: []
    human_judgment: true
    rationale: "Delivery to a Desktop client on an SSH remote needs a live Desktop; plans 03-09 and 03-11 prove it (RESEARCH A2)."

plan_head_before: cc40dc7c721c842a889cefbb6384031fb00ec180
plan_head_after: 60d110572065b79f40f351ca1225641a9ac63506
duration: 27min
completed: 2026-11-01
status: complete
---

# Phase 3 Plan 05: board.updated Event Summary

**Every changed write, from the agent tool or from POST /board/edit, now calls Hermes `broadcast_plugin_event("hermes-session-tasks", "board.updated", {session_id, root_id, rev, actor})` after the commit, and a publish fault never fails a write.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-11-01T04:29:00Z (approximate, no timer was recorded at start)
- **Completed:** 2026-11-01T04:56:37Z
- **Tasks:** 2
- **Files modified:** 9 (2 created, 7 modified)

## Accomplishments

- `events.py` is the only caller of `broadcast_plugin_event`. The Hermes import is lazy inside `publish`. `listener(actor, publisher)` binds the actor.
- `BoardTools.after_write` and the new `BoardApi.after_write` share the `WriteListener` type `(root_id, session_id, rev)`. `register(..., publish=)` wires actor agent. `build(..., publish=)` wires actor user.
- 25 tests in `tests/test_events.py`: end to end for both writers, an alias session, 12 silent cases, rising revs, committed rev, three fault paths, payload content, and the Hermes wire name in the gateway venv.
- Whole suite: 603 passed on Python 3.11 and on Python 3.14, coverage 97.49 percent, `check: all ok`.

## Task Commits

1. **Task 1 red: failing end to end tests** - `2d5ea5d` (test). Red line: `4 failed in 0.61s` (collection of `session_tasks.events` fails; all four tests fail).
2. **Task 1 green: events.py, new listener signature, wiring** - `64ad6fd` (feat). Holds board_tools.py, wiring.py, tests/test_board_tools.py and tests/test_register.py as the plan requires. The red line for the signature tests before this commit was `2 failed, 49 passed` (test_after_write_runs_once_with_the_root_after_a_change and test_register_wires_the_agent_publisher).
3. **Task 2: prove the edge cases** - `6942cc1` (test). All 21 new tests passed at once, as the plan expected, so no code change was needed.
4. **Deviation fix: dispatch test** - `60d1105` (fix). See below.

**Plan metadata:** the docs commit that holds this SUMMARY, STATE.md and ROADMAP.md.

## Files Created/Modified

- `plugin/session_tasks/events.py` - publish, listener, names and types
- `plugin/session_tasks/board_tools.py` - `after_write: WriteListener`, call with `(root_id, session_id, result.rev)`
- `plugin/session_tasks/board_api.py` - `BoardApi.after_write`, call after an `Applied` with changes, `build(publish=)`
- `plugin/session_tasks/wiring.py` - `register(publish=)` binds the agent listener
- `tests/test_events.py` - new, 25 tests
- `tests/test_board_tools.py`, `tests/test_register.py` - new listener signature and the publisher wiring test
- `tests/hermes_dispatch_snippet.py`, `tests/test_hermes_dispatch.py` - recording stand-in for `tui_gateway.server` and one new test

## Decisions Made

- The Hermes name test runs its script inline with `python -I -c`, so the red commit holds only `tests/test_events.py` as the plan requires.
- The event goes out inside the existing try/except of each writer, after the commit and outside the write transaction (T-03-14).
- No relay between serve processes: events reach only the Desktop clients of the process that wrote. Freshness across machines stays with polling (RESEARCH Pitfall 3).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Dispatch test broke when a tool write began to publish**
- **Found during:** Task 2 (`./scripts/check.sh`)
- **Issue:** `tests/test_hermes_dispatch.py` failed 3 tests with `FileExistsError` on the plugin symlink. The board write in the bare dispatch process now calls the real `broadcast_plugin_event`. That imports `tui_gateway.server`, and the Hermes launcher then prepared a new dependency environment for the temporary home and ran the script a second time. A bisect showed the failure appears only with the full set of feat changes and passes on the parent commits.
- **Fix:** The snippet registers a recording stand-in for `tui_gateway.server` (and its package) before any plugin code runs. The real `broadcast_plugin_event` and its name check stay in the path. A new test asserts the wire name and the payload of both writes (rev 2 add, rev 3 confirmed remove).
- **Files modified:** `tests/hermes_dispatch_snippet.py`, `tests/test_hermes_dispatch.py` (not in the plan file list)
- **Verification:** `uv run pytest tests/test_hermes_dispatch.py -q` gives 4 passed; `./scripts/check.sh` ends `check: all ok`.
- **Committed in:** `60d1105`

---

**Total deviations:** 1 auto-fixed (1 bug).
**Impact on plan:** The fix is test only and adds proof of the wire name through Hermes dispatch. No production code changed.

## Issues Encountered

- In a plain gateway-venv process `tui_gateway.server` raises `ModuleNotFoundError` (dotenv). `broadcast_plugin_event` catches it (it is an `ImportError`), logs, and returns, so a write in such a process still works. A measured `publish` call takes 0.05 s there.

## User Setup Required

None - no external service configuration required. No gateway restart happened in this plan. The announced Desktop restarts in plans 03-08 and 03-10 load the new wiring.

## Known Stubs

None.

## Threat Flags

None. The only new surface is the existing authenticated gateway broadcast, already in the plan threat model (T-03-13 to T-03-15, all mitigated and tested).

## Next Phase Readiness

- Server side of API-02 is done. Plan 03-06 (test pane) can show the arrival of `plugin.hermes-session-tasks.board.updated`.
- Client delivery on each machine stays open until plans 03-09 and 03-11 (RESEARCH A2).

## Self-Check: PASSED

- Created files exist: `plugin/session_tasks/events.py`, `tests/test_events.py`, this SUMMARY.
- Commits `2d5ea5d`, `64ad6fd`, `6942cc1`, `60d1105` are ancestors of HEAD.
- Acceptance criteria: the four greps exit 0; `uv run pytest -m hermes tests/test_events.py -q -rs` gives 1 passed, 0 skipped; `uv run pytest tests/test_events.py -q` gives 25 passed; `./scripts/check.sh` ends `check: all ok`.

---
*Phase: 03-rest-router-and-client-install-spike*
*Completed: 2026-11-01*
