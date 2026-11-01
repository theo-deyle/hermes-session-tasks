---
phase: 03-rest-router-and-client-install-spike
plan: 04
subsystem: rest-api
tags: [hermes-plugin, dashboard-api, version-handshake, layout-guards, pytest]
status: complete

requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: plugin_api.py router, core_module, tests/api_client.py (plan 03-02)
provides:
  - plugin/session_tasks/version.py with API_VERSION, plugin_dir, read_backend_version, meta
  - GET /meta route in plugin_api.py (the fourth and last D-23 route)
  - tests/test_version.py with manifest_value and the meta tests
  - dashboard_import_findings and the dashboard async guard in tests/test_layout.py
affects: [03-06, 03-08, 03-10]

actuals:
  tokens: 9000
  tasks: 2
  commits: 4
plan_head_before: cb8d9bca59ab0cfbaaf7624f42dbe12bed87ef31
plan_head_after: a5c996487b70ca90fd68cf1f2f63190a20d4f5c0

tech-stack:
  added: []
  patterns:
    - "GET /meta is a plain def that returns core_module('version').meta(); it does not use get_api, so it opens no data file"
    - "read_backend_version never raises: OSError, UnicodeDecodeError and a missing line give 'unknown' and one WARNING"
    - "Layout guards walk plugin/dashboard: no async def, and module-level imports are stdlib, fastapi or pydantic only"

key-files:
  created:
    - plugin/session_tasks/version.py
    - tests/test_version.py
  modified:
    - plugin/dashboard/plugin_api.py
    - tests/test_layout.py

key-decisions:
  - "version.py imports PLUGIN_NAME from .paths, so plugin_id has one source"
  - "read_backend_version also catches UnicodeDecodeError, so a binary manifest cannot make /meta fail"
  - "dashboard_import_findings allows only fastapi and pydantic besides the stdlib; a function-level import is not checked"

requirements-completed: [API-03]

coverage:
  - id: D1
    description: "A Hermes-style load of plugin_api.py serves GET /meta with ok, plugin_id, backend_version equal to the plugin.yaml version and api_version 1"
    requirement: "API-03"
    verification:
      - kind: integration
        ref: "tests/test_version.py#test_meta_route_returns_both_versions"
        status: pass
      - kind: unit
        ref: "tests/test_version.py#test_backend_version_matches_the_manifest"
        status: pass
    human_judgment: false
  - id: D2
    description: "The pyproject version equals the plugin.yaml version"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "tests/test_version.py#test_pyproject_version_matches_the_manifest"
        status: pass
    human_judgment: false
  - id: D3
    description: "A missing, unreadable or version-less manifest gives unknown, one warning and HTTP 200 data; meta holds no state and creates no plugin-data folder"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "tests/test_version.py (missing manifest, unreadable manifest, no-state, unknown meta tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The layout guards fail any async def and any relative or third-party module-level import in plugin/dashboard"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "tests/test_layout.py#test_dashboard_defines_no_async_def"
        status: pass
      - kind: unit
        ref: "tests/test_layout.py#test_dashboard_module_level_imports_are_stdlib_fastapi_or_pydantic"
        status: pass
      - kind: unit
        ref: "tests/test_layout.py#test_dashboard_import_guard_reports_relative_and_third_party_imports"
        status: pass
    human_judgment: false
  - id: D5
    description: "The real Hermes dashboard host mounts GET /meta and the Desktop pane reads it"
    requirement: "API-03"
    verification: []
    human_judgment: true
    rationale: "No gateway restarted in this plan. Plans 03-08 (Mac) and 03-10 (Windows PC) load the final code at announced restarts and prove the mount."

duration: 5min
completed: 2026-11-01
---

# Phase 3 Plan 04: Version handshake Summary

**`GET /meta` in the path-loaded `plugin_api.py` returns the `plugin.yaml` version and `API_VERSION` 1 from a stdlib `version.py` that never raises, and the layout guards now cover `plugin/dashboard`.**

## Performance

- **Duration:** about 5 min (start about 04:33Z, end 04:38Z)
- **Tasks:** 2 of 2
- **Files:** 2 created, 2 modified
- **Commits:** 4 (2 test commits, 2 feature commits)

## Accomplishments

- Task 1 (tracer): `version.py` holds `API_VERSION = 1`, `plugin_dir`, `read_backend_version` and `meta`. The route `GET /meta` is a plain def that returns `core_module("version").meta()`. The router now holds the four D-23 routes: `GET /board`, `GET /boards`, `POST /board/edit`, `GET /meta`.
- `tests/test_version.py` has 8 tests: the route under a host-style load, the manifest match, the pyproject lock, two missing-manifest cases, an unreadable manifest (a folder named `plugin.yaml`), the no-state check and the unknown meta.
- Task 2: `dashboard_import_findings(dashboard_dir)` reports a relative import and any module-level import that is not stdlib, fastapi or pydantic. Three new tests guard the real dashboard folder and the guard itself.

## Verification Evidence

- Red for Task 1 (commit 0ab753e): `uv run pytest tests/test_version.py -q` stopped at collection with `ImportError: cannot import name 'version' from 'session_tasks'` and `1 error in 0.51s`.
- Task 1 green: `uv run pytest tests/test_version.py tests/test_api_load.py -q` gave `12 passed`; `tests/test_version.py` alone gave `8 passed` (plan minimum 7).
- `ruff check`, `ruff format --check` and `pyright` on the three Task 1 files passed (`0 errors, 0 warnings`). Two files needed `ruff format`; the diff held only line wrapping.
- `timeout 120 hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin` printed `Validation passed.`
- Commit order check exited 0: the oldest 03-04 commit is `test(03-04)`.
- Tracer gate (auto mode): the pytest and validate commands ran again after the feat commit and passed (`12 passed`, `Validation passed.`). Log: tracer verified end to end, expanding.
- Red for Task 2 (commit 5ac8369): `uv run pytest tests/test_layout.py -q` gave `2 failed, 27 passed`, both with `NameError` on `dashboard_import_findings`.
- Task 2 green: `29 passed`. Lint, format check and pyright passed.
- `./scripts/check.sh` ended with `check: python 3.11 ok` (576 passed), `check: python 3.14 ok` (576 passed) and `check: all ok`. Coverage TOTAL 97.57 percent; `version.py` is at 100 percent.
- Acceptance greps passed: `API_VERSION = 1`, `"/meta"`, `def dashboard_import_findings`, `PLUGIN_DIR / "dashboard"`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Catch UnicodeDecodeError in read_backend_version**
- **Found during:** Task 1 green
- **Issue:** The plan names `OSError` only. A manifest with bytes that are not UTF-8 raises `UnicodeDecodeError`, which is not an `OSError`, so `/meta` would answer 500. The truth "read_backend_version never raises" needs both.
- **Fix:** The except clause names `(OSError, UnicodeDecodeError)`.
- **Files modified:** plugin/session_tasks/version.py
- **Commit:** ac5e5d1

**2. [Plan text drift] Extra test**
- **Issue:** The behavior block lists 7 tests. The file holds 8: `test_unreadable_manifest_gives_unknown` covers the `OSError` branch that the two missing-manifest cases do not reach.
- **Fix:** None needed. The minimum of 7 holds.

**Total deviations:** 1 auto-fixed (missing handling), 1 plan text drift. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. `GET /meta` is the surface in the plan threat model (T-03-30, T-03-31). The reply holds the plugin id, the version string and an integer only.

## Notes for Later Plans

- Editing `plugin_api.py` needs an announced restart of every `hermes serve` process. This plan restarted nothing. Plans 03-08 and 03-10 load the final code.
- Plan 03-06 (the pane) compares its `PLUGIN_VERSION` and `API_VERSION` constants with the `GET /meta` reply. The drift test for the `plugin.js` constants belongs to that plan; `manifest_value("version")` in `tests/test_version.py` is ready for reuse.
- The plan's `after_write` note on `BoardApi` in the 03-02 summary did not apply to this plan and was not touched.

## Self-Check: PASSED

- Created files exist: plugin/session_tasks/version.py, tests/test_version.py.
- Commits exist: 0ab753e, ac5e5d1, 5ac8369, a5c9964.
