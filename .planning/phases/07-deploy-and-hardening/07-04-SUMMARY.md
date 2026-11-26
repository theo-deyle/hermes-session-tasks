---
phase: 07-deploy-and-hardening
plan: 04
subsystem: api
tags: [dashboard, session-id-limit, layout-guard, ui-spec]

requires:
  - phase: 06-cross-session-boards
    provides: "copy_args.SESSION_ID_MAX, the copy route, review note IN-05, 06-UI-SPEC.md"
provides:
  - "plugin_api.py reads SESSION_ID_MAX from core_module('copy_args') at import"
  - "tests/test_layout.py guard: a second module-level literal of SESSION_ID_MAX under plugin/ fails the suite"
  - "06-UI-SPEC.md line 94 lists the read-only row in the order ItemRow draws it"
affects: [07-05, 07-06]

actuals:
  tokens: 1958
  tasks: 2
  commits: 2
plan_head_before: 3b26c6b7b7152a3de3d053d38e456efd4374bb70
plan_head_after: cca491c370eb77f098b9eb94979ca45dcb9d3338
commits: 2
status: complete

tech-stack:
  added: []
  patterns:
    - "A path-loaded dashboard file calls core_module at import for a shared constant; a function call is not an import, so the dashboard import rule holds"
    - "One AST guard per single-home constant, with a tmp_path self-test"

key-files:
  created: []
  modified:
    - plugin/dashboard/plugin_api.py
    - tests/test_api_copy.py
    - tests/test_layout.py
    - .planning/phases/06-cross-session-boards/06-UI-SPEC.md

key-decisions:
  - "The import-time core load broke no load or version test, so the plan fallback (keep the literal, add an equality test) was not needed."
  - "The layout guard looks only at module-level Assign and AnnAssign nodes with a constant value, so a read such as SESSION_ID_MAX: int = core_module(...).SESSION_ID_MAX is not a finding."

requirements-completed: [DEV-06]

coverage:
  - id: D1
    description: "SESSION_ID_MAX has one literal home in copy_args.py; the route reads it from core and still refuses 257 characters and accepts 256"
    requirement: "DEV-06"
    verification:
      - kind: unit
        ref: "tests/test_api_copy.py#test_long_session_ids_are_refused"
        status: pass
      - kind: unit
        ref: "tests/test_api_load.py, tests/test_version.py, tests/test_copy_args.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "A layout test fails when a second literal assignment of SESSION_ID_MAX appears under plugin/"
    requirement: "DEV-06"
    verification:
      - kind: unit
        ref: "tests/test_layout.py#test_session_id_max_has_one_literal_home"
        status: pass
      - kind: unit
        ref: "tests/test_layout.py#test_session_id_max_guard_reports_each_literal_and_skips_reads"
        status: pass
    human_judgment: false
  - id: D3
    description: "Line 94 of 06-UI-SPEC.md describes the read-only row as built"
    requirement: "DEV-06"
    verification:
      - kind: other
        ref: "sed -n 94p 06-UI-SPEC.md | grep -c checkbox (prints 1)"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-11-03
---

# Phase 7 Plan 04: One home for the session id limit Summary

**The copy and edit routes now read the session id limit from the core parser, a layout test fails on a second literal, and the stale read-only row line in the Phase 6 UI spec matches the pane.**

## Performance

- **Duration:** about 30 min, most of it two full gate runs of 5 minutes per Python version
- **Tasks:** 2 of 2
- **Files modified:** 4

## Accomplishments

- `plugin/dashboard/plugin_api.py`: `load_core()` and `core_module()` moved above the pydantic models. `SESSION_ID_MAX: int = core_module("copy_args").SESSION_ID_MAX` replaces the literal. The model fields and the `Query` parameter keep their uses. The module docstring gains one sentence about the shared limit.
- `tests/test_api_copy.py`: imports the limit from `session_tasks.copy_args` instead of holding a third copy.
- `tests/test_layout.py`: `session_id_max_findings(plugin_dir)` walks every Python file under `plugin/` and reports each module-level literal assignment of `SESSION_ID_MAX`. `test_session_id_max_has_one_literal_home` expects exactly `session_tasks/copy_args.py`. A `tmp_path` self-test proves two literal files are reported and a read of the name is not.
- `06-UI-SPEC.md` line 94 now reads: checkbox first, then the text, then the chevron and the subtask count only when subtasks exist, then the Copy button. This is the order `ItemRow` draws (plugin.js lines 600-640). Phase 04-08 moved the chevron after the text.

## Task Commits

1. Task 1 (tracer): `32414c7` - fix(07-04): read the session id limit from the core parser
2. Task 2: `cca491c` - test(07-04): guard the one home of the session id limit

The tracer gate: the `<verify>` of Task 1 ran green end to end (88 tests across the five named files, ruff, format, pyright, `hermes plugins validate plugin` ends with `Validation passed.`), so expansion went ahead.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_api_copy.py tests/test_api.py tests/test_api_load.py tests/test_version.py tests/test_copy_args.py -q -rs` | 88 passed |
| `pytest tests/test_api_copy.py -q -k long` | 2 passed (257 refused, 256 accepted, both fields) |
| `pytest tests/test_layout.py -q -rs` | 32 passed |
| `hermes plugins validate plugin` | Validation passed. |
| Task files: ruff check, ruff format --check, pyright | clean, 0 errors |
| `./scripts/check.sh` (full house gate, 3.11 and 3.14) | `check: all ok`, exit 0 |
| Gate detail, Python 3.11 | ruff clean, format clean, pyright 0 errors, 1154 passed, coverage 97.16 percent (floor 80) |
| Gate detail, Python 3.14 | ruff clean, format clean, pyright 0 errors, 1154 passed |

The first gate run used `timeout 590` and the kill came just before the final echo. A second run without the bound ended with `check: all ok`. Only the second run counts.

## Deviations from Plan

None - plan executed exactly as written. The fallback of Task 1 step 5 was not needed: the import-time load broke no test in `tests/test_api_load.py` or `tests/test_version.py`.

## Known Stubs

None.

## Threat Flags

None. T-07-08 is mitigated by the single literal home and the guard test, and the 257 and 256 character route tests stay green. T-07-09 is mitigated: the import-time core load is stdlib only, `tests/test_api_load.py` and `hermes plugins validate` pass.

## Issues Encountered

None.

## Next Phase Readiness

IN-05 and the stale spec line are closed (D-56). IN-01, IN-02, IN-03, IN-04, IN-06 and IN-07 stay deferred as decided.

## Self-Check: PASSED

- plugin/dashboard/plugin_api.py, tests/test_api_copy.py, tests/test_layout.py and 06-UI-SPEC.md exist and hold the changes.
- Commits 32414c7 and cca491c are ancestors of HEAD.
