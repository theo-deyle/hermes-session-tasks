---
phase: 01-core-storage-and-session-identity
plan: 01
subsystem: testing
tags: [uv, pytest, ruff, pyright, pin-gate, ast-guards, pytester]

requires: []
provides:
  - uv project with dev-group pins equal to the gateway venv and the Hermes pins
  - scripts/check_pins.py pin gate that runs before install and in every matrix run
  - scripts/check.sh matrix (ruff, format, pyright, pytest) on Python 3.11 and 3.14
  - tests harness with tmp HERMES_HOME, no-network guard, FakeClock and the hermes skip hook
  - real-home session guard that fails a run which gains entries in the real plugin data dir
  - FakeSessionReader and FakeReaderFactory for the lineage tests
  - seven AST layout guards over plugin/ with one self-test each
affects: [01-02, 01-03, 01-04, 01-05, phase-2, phase-3]

plan_head_before: 6a6dbde568495811ee236250161833e5e7aa1d74
plan_head_after: df66f9a582385b46b56158f48848c3f365a90a2c

actuals:
  tokens: 7200
  tasks: 2
  commits: 4

tech-stack:
  added: [uv lock with 26 packages, pytest 9.1.1, pytest-cov 7.1.0, ruff 0.15.10, pyright 1.1.414]
  patterns:
    - "One uv environment per interpreter through UV_PROJECT_ENVIRONMENT"
    - "AST guards return findings from a helper that takes a directory, so each guard can be self-tested on tmp_path"
    - "Session hooks in a pytest plugin module fail the run itself, proven by a pytester subprocess"

key-files:
  created:
    - pyproject.toml
    - .python-version
    - uv.lock
    - scripts/check_pins.py
    - scripts/check.sh
    - plugin/session_tasks/__init__.py
    - tests/conftest.py
    - tests/home_guard.py
    - tests/fakes.py
    - tests/test_layout.py
  modified:
    - .gitignore

key-decisions:
  - "Absolute self-imports (from session_tasks import x) in core modules fail the module-level import guard. Core uses relative imports only."
  - "The manifest guard also names requirements*.txt, setup.py, package.json and lock files, not only pyproject.toml."
  - "The lazy-import guard flags any non-stdlib import outside the public Hermes allowlist, not only private Hermes modules."

requirements-completed: [DEV-01, DEV-02]

coverage:
  - id: D1
    description: "Pin gate: dev pins equal uv.lock, the gateway venv and the Hermes pins, and every locked package comes from pypi.org"
    requirement: DEV-01
    verification:
      - kind: other
        ref: "uv run --no-project --python 3.11 -- python -I scripts/check_pins.py (prints pins ok)"
        status: pass
    human_judgment: false
  - id: D2
    description: "One command runs ruff, format check, pyright and pytest on Python 3.11 and 3.14"
    requirement: DEV-01
    verification:
      - kind: other
        ref: "./scripts/check.sh (ends with check: all ok)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Layout and import guards each report a bad module and pass on plugin/"
    requirement: DEV-02
    verification:
      - kind: unit
        ref: "tests/test_layout.py (7 guards, 7 self-tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Real-home session guard fails a passing run that writes the real plugin data dir, and tests need no gateway and no network"
    requirement: DEV-02
    verification:
      - kind: integration
        ref: "tests/test_layout.py#test_session_guard_fails_a_passing_run_that_writes_the_real_plugin_dir"
        status: pass
      - kind: unit
        ref: "tests/test_layout.py#test_home_guard_ignores_sqlite_sidecars_and_other_paths"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-10-30
status: complete
---

# Phase 1 Plan 01: Toolchain, pin gate and test harness Summary

**uv project with a pin gate that checks uv.lock against the gateway venv before install, a 3.11 and 3.14 check matrix, and a test harness whose real-home guard fails the pytest run itself**

## Performance

- **Duration:** 3 min
- **Started:** 2026-10-30T23:12:29Z
- **Completed:** 2026-10-30T23:15:54Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- `scripts/check_pins.py` printed `pins ok` before the first `uv sync`. It compares the dev pins with `uv.lock`, the gateway venv `pip list`, and the Hermes pytest and ruff pins. It also rejects any locked package that is not from pypi.org.
- `./scripts/check.sh` ends with `check: all ok` and prints `check: python 3.11 ok` and `check: python 3.14 ok`. It uses one environment per interpreter, so `.venv` is never replaced.
- `tests/test_layout.py` holds seven AST guards (no manifest in `plugin/`, stdlib-only module imports, public Hermes allowlist for lazy imports, no `async def`, 500 line limit, `sqlite3.connect` only in `paths.py`, `SessionDB` only with `read_only=True`). Each guard has a self-test on a bad module in `tmp_path`.
- `tests/home_guard.py` watches only `plugin-data/hermes-session-tasks` under the real home. A pytester subprocess test proves exit code 1 and the line `real Hermes home gained: ...` for a passing run that writes there. A second test proves a clean run exits 0.
- `tests/conftest.py` sets `HERMES_HOME` to a tmp directory for every test and raises on AF_INET and AF_INET6 connects. `tests/fakes.py` mirrors the four public `SessionDB` lineage methods.

## Task Commits

1. **Orchestrator state before the plan** - `a75f42a` (docs)
2. **Task 1: uv project, pin gate, package marker** - `31d9d7b` (chore)
3. **Task 2 RED: layout guards, self-tests, home guard tests** - `3e8872e` (test)
4. **Task 2 GREEN: check.sh, conftest, home_guard, fakes** - `df66f9a` (feat)

**Plan metadata:** the docs commit that holds this file, STATE.md and ROADMAP.md.

## Files Created/Modified

- `pyproject.toml` - uv project, dev-group pins, pytest, ruff and pyright config
- `.python-version` - `3.11`
- `uv.lock` - 26 packages, all from pypi.org
- `.gitignore` - adds `.venv*/`, `.coverage`, `htmlcov/`
- `scripts/check_pins.py` - pin gate, stdlib only
- `scripts/check.sh` - lint, format, type and test matrix
- `plugin/session_tasks/__init__.py` - package docstring only
- `tests/conftest.py` - autouse tmp home and no-network fixtures, `FakeClock`, `clock`, `db_path`, hermes skip hook
- `tests/home_guard.py` - snapshot helpers and the two session hooks
- `tests/fakes.py` - `SessionSpec`, `FakeSessionReader`, `FakeReaderFactory`
- `tests/test_layout.py` - guards, self-tests, home guard tests, pytester session guard tests (19 tests)

## Decisions Made

- Core modules use relative imports only. An absolute `session_tasks` import fails the module-level import guard, as the guard name says.
- The manifest guard covers more names than `pyproject.toml` (requirements files, `setup.py`, `package.json`, lock files), because any of them can make Hermes install packages.
- The lazy-import guard flags every non-stdlib import outside the public allowlist, so a lazy `fastapi` import in core also fails.

## Deviations from Plan

None - plan executed exactly as written.

The commit trailer uses `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, the attribution line from the harness. The dispatch prompt named `Claude Fable 5.1`. This is a message trailer only and changes no file.

## Issues Encountered

- `ruff format --check` failed on the first run for three long lines. `ruff format` fixed them before the first commit that held the files.

## Known Stubs

None. `plugin/session_tasks/__init__.py` is a package marker by design. Plan 01-02 adds the core modules.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 01-02 starts on a working toolchain. It adds the `connect`, `store` and `resolver_for` fixtures to `tests/conftest.py`, and the core modules the guards already cover.
- DEV-01 flagged assumption (interpreter differences between 3.11 and 3.14): the full suite ran green on both with `filterwarnings = ["error"]`. No core module exists yet, so the multiprocessing, `ResourceWarning` and sqlite3 adapter edges get real coverage in plans 01-02 to 01-05.

## Self-Check: PASSED

- Created files exist: pyproject.toml, .python-version, uv.lock, scripts/check_pins.py, scripts/check.sh, plugin/session_tasks/__init__.py, tests/conftest.py, tests/home_guard.py, tests/fakes.py, tests/test_layout.py.
- Commits found in HEAD history: a75f42a, 31d9d7b, 3e8872e, df66f9a.
- `./scripts/check.sh` ended with `check: all ok`. `uv run pytest tests/test_layout.py -q` printed `19 passed`. No run printed `real Hermes home gained`.

---
*Phase: 01-core-storage-and-session-identity*
*Completed: 2026-10-30*
