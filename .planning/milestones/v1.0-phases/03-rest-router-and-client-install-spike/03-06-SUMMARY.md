---
phase: 03-rest-router-and-client-install-spike
plan: 06
subsystem: ui
tags: [hermes-desktop, plugin-sdk, esm, node-vm, fastapi, loopback-relay]

requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: "03-02 routes (GET /board, POST /board/edit), 03-04 GET /meta, 03-05 board.updated event payload"
provides:
  - "plugin/desktop/plugin.js: the test pane (one plain ESM file, three imports, theme classes only)"
  - "tests/desktop_pane_harness.mjs: node VM harness with a small hook runtime and a ctx.rest bridge"
  - "tests/rest_relay.py: RestRelay, a loopback HTTP relay from the harness to a TestClient"
  - "DEV-03 checks: stdin module check, truncated-file check, loader-regex import allowlist, colour and text bans"
  - "Version drift tests: PLUGIN_VERSION against plugin.yaml, API_VERSION against version.API_VERSION"
affects: [03-07, 03-08 Mac install, 03-09, 03-10 Windows install, 03-11, 04 pane]

actuals:
  tokens: 7300
  tasks: 3
  commits: 5

plan_head_before: 8f42a55674354f33fb95f18ff07618ab74f2f7e2
plan_head_after: 248bb28c62007d1456dc0fa73232ca2aa8fc9231

tech-stack:
  added: []
  patterns:
    - "Pane tests run the real plugin.js in a node VM and reach the real router over a loopback relay"
    - "Pane reads live values (focused session, board root) through one useRef so listeners and intervals never read a stale closure"
    - "Stale-write probe: base_rev 0 is behind every existing item, so the write is always answered stale and changes no data"

key-files:
  created:
    - plugin/desktop/plugin.js
    - tests/desktop_pane_harness.mjs
    - tests/rest_relay.py
    - tests/test_desktop_plugin.py
  modified:
    - tests/test_version.py

key-decisions:
  - "The harness runs under node --experimental-vm-modules, because vm.SourceTextModule and SyntheticModule need that flag (same as the hermes-memory-ui smoke harness)."
  - "RestRelay.base_url is the bare host and port. The test adds PREFIX, so the harness forwards the exact path the Desktop sends."
  - "A reply for a session that is no longer focused is dropped before it reaches the pane state."
  - "this chat or other chat compares payload.root_id with the root_id of the last board reply. With no board reply yet, every event reads other chat."

patterns-established:
  - "One line per host element: the harness collects the direct string children of each element, so the tests assert on plain text lines"
  - "Import allowlist helper scans text and comments too, so it is stricter than the Desktop loader"

requirements-completed: [DEV-03, API-03, DEV-05]

coverage:
  - id: D1
    description: "The test pane, run in a node VM, reads the backend versions and the focused session board through ctx.rest from the real router and renders them as text lines"
    requirement: API-03
    verification:
      - kind: integration
        ref: "tests/test_desktop_plugin.py#test_pane_shows_the_board_from_the_real_routes"
        status: pass
      - kind: integration
        ref: "tests/test_desktop_plugin.py#test_pane_with_no_focused_session_makes_no_board_call"
        status: pass
    human_judgment: false
  - id: D2
    description: "The pane shows the last agent event and the last pane event with rev, time and this chat or other chat, and polls every 6000 ms while a session is focused"
    verification:
      - kind: integration
        ref: "tests/test_desktop_plugin.py#test_agent_event_line"
        status: pass
      - kind: integration
        ref: "tests/test_desktop_plugin.py#test_pane_event_line_and_other_chat"
        status: pass
      - kind: integration
        ref: "tests/test_desktop_plugin.py#test_poll_interval"
        status: pass
    human_judgment: true
    rationale: "The harness proves the pane handles the event frame. Delivery of board.updated to a real Desktop over SSH is proved on each machine in plans 03-09 and 03-11 (RESEARCH A2)."
  - id: D3
    description: "Run write test adds one labelled item and sends one stale write through the real routes; the stale write changes no data"
    verification:
      - kind: integration
        ref: "tests/test_desktop_plugin.py#test_write_test_through_the_real_routes"
        status: pass
      - kind: integration
        ref: "tests/test_desktop_plugin.py#test_write_test_on_an_empty_board_still_goes_stale"
        status: pass
    human_judgment: false
  - id: D4
    description: "The version banner shows on a backend or API version mismatch and not on a match; a failed /meta shows backend not reached with no banner"
    requirement: DEV-05
    verification:
      - kind: integration
        ref: "tests/test_desktop_plugin.py#test_banner_on_backend_mismatch"
        status: pass
      - kind: integration
        ref: "tests/test_desktop_plugin.py#test_meta_failure_shows_backend_not_reached"
        status: pass
      - kind: unit
        ref: "tests/test_version.py#test_pane_plugin_version_matches_the_manifest"
        status: pass
      - kind: unit
        ref: "tests/test_version.py#test_pane_api_version_matches_the_backend"
        status: pass
    human_judgment: false
  - id: D5
    description: "plugin.js passes the stdin module check, a truncated copy and JSX fail it, imports are limited to the three SDK specifiers, and the file holds no colour literal, raw HTML, ctx.socket or todo mention"
    requirement: DEV-03
    verification:
      - kind: unit
        ref: "tests/test_desktop_plugin.py#test_plugin_passes_the_stdin_module_check"
        status: pass
      - kind: unit
        ref: "tests/test_desktop_plugin.py#test_truncated_plugin_fails_the_check"
        status: pass
      - kind: unit
        ref: "tests/test_desktop_plugin.py#test_imports_are_on_the_allowlist"
        status: pass
      - kind: unit
        ref: "tests/test_desktop_plugin.py#test_plugin_has_no_colour_literal"
        status: pass
      - kind: other
        ref: "hermes plugins validate plugin (desktop surface line, Validation passed.)"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-11-01
status: complete
---

# Phase 3 Plan 06: Test pane and DEV-03 checks Summary

**One plain ESM test pane (`plugin/desktop/plugin.js`) that reads a board through `ctx.rest`, shows `board.updated` events, runs a stale-write probe and shows a version banner, proved end to end in a node VM against the real router over a loopback relay.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-11-01T04:46:00Z (approximate; the start time was not captured)
- **Completed:** 2026-11-01T05:10:00Z
- **Tasks:** 3
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments

- The test pane renders the plan's layout in order: backend and pane versions, the mismatch banner, the session line, the agent and pane event lines, the write test line, one line per item, and a `Run write test` button. It registers as `pane` in area `panes`, placement `right`, width `320px`.
- `tests/desktop_pane_harness.mjs` loads `plugin.js` with stub SDK, react and jsx-runtime modules and a small hook runtime. `ctx.rest` forwards over loopback to `RestRelay`, which calls the real router of plans 03-02 and 03-04 through a `TestClient`. A mismatch between the pane's request shapes and the router now fails a test.
- The write test posts an add, then a `set_checked` with `base_rev` 0. The reply is `stale`, the store keeps item 1 unchecked, and the pane shows `write test: add ok at rev 2, stale write answered stale (stale) at rev 2`.
- DEV-03 holds: `node --input-type=module --check` on stdin passes the file and fails a truncated copy and JSX. The loader-regex allowlist finds only `@hermes/plugin-sdk`, `react` and `react/jsx-runtime`, and fails on `lodash` and `import('x')`.
- Version drift tests tie `PLUGIN_VERSION` to `plugin.yaml` and `API_VERSION` to `version.API_VERSION`.

## Task Commits

1. **Task 1: End to end test pane (tracer)**
   - Red: `72f0fe3` (test) - `uv run pytest tests/test_desktop_plugin.py -q -rs` gave `2 failed in 2.72s`; the harness failed with `ENOENT ... plugin/desktop/plugin.js`.
   - Green: `8625983` (feat) - 2 passed; `hermes plugins validate` printed `desktop surface - stays inside the plugin SDK surface` and `Validation passed.`
2. **Task 2: Events, poll, write test, banner**
   - Red: `95572fc` (test) - `9 failed, 6 passed`.
   - Green: `5c3e03d` (feat) - 15 passed.
3. **Task 3: Syntax, allowlist, bans, drift** - `248bb28` (test) - the new tests passed at once against the Task 2 file, as the plan expects. `./scripts/check.sh` ended `check: all ok` (631 passed on 3.11 and on 3.14, coverage 97.49 percent).

**Plan metadata:** the docs commit that holds this SUMMARY, STATE.md and ROADMAP.md.

## Files Created/Modified

- `plugin/desktop/plugin.js` - the test pane: constants, `boardLines`, `Pane`, default export `{ id, name, register }`
- `tests/desktop_pane_harness.mjs` - node VM harness (`lines`, `restCalls`, `contribution`, `intervals`, `eventTypes`, plus a `buttons` key)
- `tests/rest_relay.py` - `RestRelay`, a `ThreadingHTTPServer` on `127.0.0.1` port 0 that forwards to a `TestClient` under one lock
- `tests/test_desktop_plugin.py` - 26 tests: pane behavior, syntax checks, allowlist, colour and text bans
- `tests/test_version.py` - two drift tests

## Decisions Made

- The harness needs `node --experimental-vm-modules`. The plan's CLI line omitted the flag.
- `RestRelay.base_url` carries no prefix. The test appends `PREFIX`, so the harness sees the same paths as the Desktop (`/meta`, `/board?session_id=s1`).
- The pane drops a board reply when the focused session changed while the call ran.
- While `/meta` is still loading the pane shows `backend checking`; `backend not reached` appears only after a failure.
- With no focused session the write button shows `write test: no session focused` and makes no call.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Harness needs `--experimental-vm-modules`**
- **Found during:** Task 1 (harness design)
- **Issue:** `vm.SourceTextModule` and `vm.SyntheticModule` exist only with that flag. The plan's CLI shows `node tests/desktop_pane_harness.mjs <plugin.js> <config.json>`.
- **Fix:** `run_harness` calls `node --experimental-vm-modules tests/desktop_pane_harness.mjs ...`, as the hermes-memory-ui smoke test does. The harness header documents it.
- **Files modified:** `tests/test_desktop_plugin.py`, `tests/desktop_pane_harness.mjs`
- **Committed in:** `72f0fe3`

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** None on scope. The extra flag changes only how the test calls node.

Extra tests beyond the plan list (all in `tests/test_desktop_plugin.py`): no poll without a focused session, events start as `none yet`, an event with no focused session reads `other chat` and makes no board call, a write test on an empty board still goes stale, and a self-test for the colour scan. The plan's test name `test_plugin_never_names_todo` is kept.

## Issues Encountered

None. `ExperimentalWarning` lines from node go to stderr and do not affect the tests.

## User Setup Required

None - no external service configuration required. No gateway restart happened and the pane is not installed on the Mac or the Windows PC. Plans 03-08 to 03-11 own that with Theo.

## Known Stubs

None. The pane is a deliberate test pane (name `Session tasks (test)`). Phase 4 replaces it with the real pane.

## Threat Flags

None. The relay (T-03-19) binds `127.0.0.1` on a random port for one test run only. Item text renders only as a string child (T-03-16), proved by `test_item_text_stays_plain_text` and the raw HTML scan. The import allowlist (T-03-17) and the stale-write probe (T-03-18) are tested. No package was installed (T-03-SC).

## Next Phase Readiness

- `plugin/desktop/plugin.js` is the file that plans 03-08 and 03-10 install on the Mac and the Windows PC.
- Whether `ctx.onEvent` receives `board.updated` over the SSH remote on each machine stays open until plans 03-09 and 03-11 (RESEARCH A2). The pane also polls every 6 s, so a missed event does not leave a stale board.
- DEV-05 is only half done here (the banner). The copy script and the README steps belong to later plans of this phase.

## Self-Check: PASSED

- Created files exist: `plugin/desktop/plugin.js`, `tests/desktop_pane_harness.mjs`, `tests/rest_relay.py`, `tests/test_desktop_plugin.py`, this SUMMARY.
- Commits `72f0fe3`, `8625983`, `95572fc`, `5c3e03d`, `248bb28` are ancestors of HEAD (5 commits since `8f42a55`).
- Acceptance criteria: the task greps exit 0; `uv run pytest tests/test_desktop_plugin.py tests/test_version.py -q -rs` gives 36 passed, 0 skipped; `node --input-type=module --check < plugin/desktop/plugin.js` exits 0; `head -c 200 plugin/desktop/plugin.js | node --input-type=module --check` exits 1; `hermes plugins validate` prints the desktop surface line and `Validation passed.`; `./scripts/check.sh` ends `check: all ok`.

---
*Phase: 03-rest-router-and-client-install-spike*
*Completed: 2026-11-01*
