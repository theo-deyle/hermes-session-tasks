---
phase: 03-rest-router-and-client-install-spike
plan: 02
subsystem: rest-api
tags: [hermes-plugin, dashboard-api, fastapi, plugin_api, board-routes, pytest]
status: complete

requires:
  - phase: 01-core-storage-and-session-identity
    provides: BoardStore, SessionResolver, model.display_order
  - phase: 02-agent-tools-and-skill
    provides: edit_args.parse, results helpers, BoardTools
provides:
  - plugin/dashboard/manifest.json with a hidden tab
  - plugin/dashboard/plugin_api.py with load_core, core_module, get_api, EditBody and three routes
  - board_json.py (item_dict, board_dict) and board_api.py (ApiReply, BoardApi, build)
  - BoardStore.list_boards and rows.BoardSummary
  - results.stale_text (public)
  - tests/api_client.py host-style load helpers
affects: [03-03, 03-04, 03-06, 03-08, 03-10, phase-04]

actuals:
  tokens: 12300
  tasks: 2
  commits: 4
plan_head_before: 323a6eb0342c6a759ceb4163a648f2b22b8ae6bb
plan_head_after: ad64f9a0148ce65dce167837ecab7927d79cee7f

tech-stack:
  added: []
  patterns:
    - "plugin_api.py is path-loaded with no package; it loads the core package under the fixed key hermes_session_tasks_core and reaches modules with importlib"
    - "Handlers are plain def and only map an ApiReply to a JSONResponse; core never raises for a request fault"
    - "Edit outcomes (applied, stale, rule error, delegate) are all HTTP 200 with ok true or false; only transport faults keep 4xx"
    - "The Annotated Depends alias (ApiDep) keeps ruff B008 quiet and lets tests override get_api"

key-files:
  created:
    - plugin/dashboard/manifest.json
    - plugin/dashboard/plugin_api.py
    - plugin/session_tasks/board_json.py
    - plugin/session_tasks/board_api.py
    - tests/api_client.py
    - tests/test_api_load.py
    - tests/test_api.py
    - tests/test_store_list.py
  modified:
    - plugin/session_tasks/store.py
    - plugin/session_tasks/rows.py
    - plugin/session_tasks/results.py
    - pyproject.toml

key-decisions:
  - "Routes GET /board, GET /boards and POST /board/edit ship here; GET /meta is left to plan 03-04"
  - "EditBody uses extra=forbid, so a confirmed field returns 422 (D-24); base_rev is StrictInt, so a string returns 422"
  - "A subtask in a new batch needs parent_ref, not parent_id, because parent_id must name an item that exists before the batch"
  - "results._stale_text became stale_text so the tool and the route give one message"

requirements-completed: [API-01]

coverage:
  - id: D1
    description: "A Hermes-style load of plugin_api.py serves GET /board with the item a board_edit tool call wrote to the same SQLite file"
    requirement: "API-01"
    verification:
      - kind: integration
        ref: "tests/test_api_load.py#test_host_load_serves_the_board_the_tool_wrote"
        status: pass
      - kind: integration
        ref: "tests/test_api_load.py#test_host_load_keeps_core_under_its_own_key"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /board/edit applies ops as actor user and answers applied, stale, rule error and delegate with the D-22 shapes; transport faults keep 4xx; no confirmed field"
    requirement: "API-01"
    verification:
      - kind: integration
        ref: "tests/test_api.py (26 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /boards lists roots newest first with stable ties, open and total counts, and an empty list for a new file"
    requirement: "API-01"
    verification:
      - kind: unit
        ref: "tests/test_store_list.py (5 tests)"
        status: pass
      - kind: integration
        ref: "tests/test_api.py#test_boards_lists_roots_newest_first"
        status: pass
    human_judgment: false
  - id: D4
    description: "A route writer and a tool writer on one board lose no write (40 adds, rev raised by 40, no 5xx)"
    requirement: "API-01"
    verification:
      - kind: integration
        ref: "tests/test_api.py#test_route_and_tool_writers_lose_no_write"
        status: pass
    human_judgment: false
  - id: D5
    description: "The real Hermes dashboard host mounts these routes and the Desktop pane can call them"
    requirement: "API-01"
    verification: []
    human_judgment: true
    rationale: "No gateway restarted in this plan. Plans 03-08 (Mac) and 03-10 (Windows PC) load the final code at announced restarts and prove the mount."

duration: 4min
completed: 2026-11-01
---

# Phase 3 Plan 02: Board routes Summary

**Three board routes (`GET /board`, `GET /boards`, `POST /board/edit`) in a path-loaded `plugin_api.py` that reaches the core package under a fixed key, with every edit outcome answered as HTTP 200 in the D-22 shape and transport faults kept as 4xx.**

## Performance

- **Duration:** about 4 min (04:16:52Z to 04:21:06Z)
- **Tasks:** 2 of 2
- **Files:** 8 created, 4 modified (12 touched, as the plan stated)
- **Commits:** 4 (2 test commits, 2 feature commits)

## Accomplishments

- Task 1 (tracer): `tests/api_client.py` loads `plugin_api.py` with `spec_from_file_location` under `hermes_dashboard_plugin_hermes-session-tasks`, inserted in `sys.modules` before `exec_module`. `GET /board` returns the item a `board_edit` tool call wrote to the same file. The core store module loads from `plugin/session_tasks` under `hermes_session_tasks_core.store`.
- Task 2: `POST /board/edit` mirrors `board_edit` with actor `user`. An applied write returns `ok`, `root_id`, `rev`, `summary`, `changed_ids` and `board`. A stale write returns `error` `stale` with `reason`, `op_index`, `item_id`, the same message text the tool gives, `rev` and the current board. A rule error or a delegate session returns `error` `invalid` with `op_index`, `rule` and `message`.
- `GET /boards` lists roots by `updated_at` descending, then `root_id` ascending. A board with every item removed shows total 0.
- All five API-01 edge rows have a test: empty, adjacency, ordering, idempotency, concurrency.

## Verification Evidence

- Red summary line for Task 1 (commit 19ca900): `4 failed in 0.58s` from `uv run pytest tests/test_api_load.py -q`.
- Task 1 green: `4 passed in 0.93s`. After the format fix and again at the tracer gate: `4 passed`.
- `hermes plugins validate <plugin>` printed `Validation passed.` Dashboard lines: `Isolation - runs in the plugin host (plugins.isolation: host)` and `dashboard backend API is served through the plugin host (buffered responses)`. All other lines passed (manifest, loadable, declared tools, declared hooks, security scan).
- `hermes plugins doctor <plugin> --ci` exited 0: `2 tool(s), 3 hook(s)`.
- Tracer gate (auto mode): the three Task 1 verify commands ran again after the commit and passed (`4 passed`, `Validation passed.`, commit order exit 0). Log: tracer verified end to end, expanding.
- Commit order check exited 0: the oldest 03-02 commit is `test(03-02)`.
- Red summary for Task 2 (commit 0ed3c63): `tests/test_api.py` gave `23 failed, 3 passed`; `tests/test_store_list.py` failed at collection with `ImportError: cannot import name 'BoardSummary'`.
- Task 2 green: `uv run pytest tests/test_api.py tests/test_store_list.py tests/test_api_load.py tests/test_board_tools.py tests/test_results.py -q` gave `88 passed` after one test fix; `tests/test_api.py` alone gave `26 passed` (plan minimum 22).
- Lint on the seven touched files: `ruff check` passed, `ruff format --check` gave `7 files already formatted`, `pyright` gave `0 errors, 0 warnings`.
- `./scripts/check.sh` ended with `check: python 3.11 ok`, `check: python 3.14 ok`, `check: all ok` (529 passed on each interpreter). Coverage TOTAL 97.52 percent. The output holds no "real Hermes home" line.
- Acceptance greps all passed: manifest equality, `CORE_KEY`, `def board_dict`, `class BoardApi`, `StarletteDeprecationWarning`, `"/board/edit"`, `"/boards"`, `extra="forbid"`, `def stale_text`, `def list_boards`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Display-order test used parent_id inside the same batch**
- **Found during:** Task 2 green run
- **Issue:** The red test added item "c" with `parent_id=1` in the same batch that creates item 1. The store requires `parent_id` to name an item that exists before the batch, so it returned a stale reply and the body had no `board` key. The test was wrong, not the route.
- **Fix:** The test uses `parent_ref=0`, the in-batch reference the core already supports.
- **Files modified:** tests/test_api.py
- **Commit:** ad64f9a

**2. [Rule 3 - Blocking] zsh did not split `$F` in the lint command**
- **Found during:** Task 1
- **Issue:** The plan's `F="..."; ruff check $F` form fails in zsh because zsh does not split a variable on spaces.
- **Fix:** Ran the same commands inside `bash -c`. No file changed.

**3. [Plan text drift] Extra tests beyond the behavior block**
- **Found during:** Task 2
- **Issue:** The plan asks for at least 22 tests in tests/test_api.py. The file holds 26. Four tests are extra to the behavior block: the 101st item case (own test, because it needs 100 seeded items), a blank session on GET, a GET for a session with no board, and an empty GET /boards.
- **Fix:** None needed. The minimum holds.

**Total deviations:** 1 auto-fixed bug (test), 1 shell note, 1 plan text drift. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. The new surface (three routes under `/api/plugins/hermes-session-tasks`) is in the plan threat model as T-03-05 to T-03-08. Replies carry fixed strings, rule text and board data only.

## Notes for Later Plans

- Editing `plugin_api.py` needs an announced restart of every `hermes serve` process. This plan restarted nothing.
- Plan 03-04 adds `GET /meta`, `after_write` on `BoardApi` and `async_def_findings` over `plugin/dashboard`. `BoardApi` is a frozen dataclass with two fields now; add the new field with a default.
- Plan 03-04 should note that `get_api()` builds new core objects on each request, so no module-level state exists besides the cached core module and the router.
- The test client override replaces `get_api`, so route tests use the test-tree `session_tasks` while the host-load tests use the `hermes_session_tasks_core` tree. Both trees share the same SQLite file.
- `GET /board` may write once: resolving a compression tip writes an alias, and a branch copies its parent board on first touch. Accepted in the plan.

## Self-Check: PASSED

- Created files exist: manifest.json, plugin_api.py, board_json.py, board_api.py, api_client.py, test_api_load.py, test_api.py, test_store_list.py.
- Commits exist: 19ca900, e9ceef6, 0ed3c63, ad64f9a.
