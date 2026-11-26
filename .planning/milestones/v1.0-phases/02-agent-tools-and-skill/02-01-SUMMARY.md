---
phase: 02-agent-tools-and-skill
plan: 01
subsystem: agent-tools
tags: [hermes-plugin, tool-registration, board_read, session-identity, pytest, layout-guards]
status: complete

requires:
  - phase: 01-core-storage-and-session-identity
    provides: BoardStore, SessionResolver, markdown.render, model errors, paths.connect, session_reader
provides:
  - plugin/plugin.yaml manifest and plugin/__init__.py entry point
  - wiring.register(ctx, connect, open_reader) with PluginContext Protocol
  - board_read tool in toolset task-board, proven through the real Hermes registry
  - tool_text, results and board_tools modules with the contracts later plans extend
  - FakeCtx test double and the Hermes dispatch contract test
  - layout guards for the TOOL-06 session line and the todo_list boundary
affects: [02-02, 02-03, 02-04, 02-05]

actuals:
  tokens: 6800
  tasks: 2
  commits: 4
plan_head_before: d7723b89a626957fa27f697d39870a85b64e5128
plan_head_after: 5db09f80839ee702056eabf9629759405369f5c7

tech-stack:
  added: []
  patterns:
    - "register(ctx) lives in core wiring.py; plugin/__init__.py only re-exports it"
    - "Handlers read the session only from the session_id keyword, never from args"
    - "Result strings: failure has a top-level error key, success never does"
    - "Hermes dispatch contract test runs the gateway venv Python on a tmp HERMES_HOME"

key-files:
  created:
    - plugin/plugin.yaml
    - plugin/__init__.py
    - plugin/session_tasks/wiring.py
    - plugin/session_tasks/tool_text.py
    - plugin/session_tasks/results.py
    - plugin/session_tasks/board_tools.py
    - tests/test_register.py
    - tests/hermes_dispatch_snippet.py
    - tests/test_hermes_dispatch.py
    - tests/test_board_tools.py
    - tests/test_results.py
    - tests/test_tool_text.py
  modified:
    - tests/fakes.py
    - tests/test_layout.py

key-decisions:
  - "Link and enable the plugin in the tmp HERMES_HOME before importing model_tools in the dispatch snippet, because the import runs plugin discovery once"
  - "plugin.yaml version 0.1.0 equals pyproject.toml; provides_tools lists only board_read until plan 02-04"
  - "register lives in wiring.py (core) so tests import it directly and the layout guards scan it"

patterns-established:
  - "FakeCtx records register_tool, register_hook, register_skill and register_system_prompt_section for no-gateway tests"
  - "Layout guard helpers return findings; each has a tree test and one self-test on a bad module"

requirements-completed: [TOOL-01, TOOL-06, TOOL-08]

coverage:
  - id: D1
    description: "Hermes loads plugin/ as hermes-session-tasks and handle_function_call(board_read) returns the board as markdown with ids and the rev"
    requirement: "TOOL-01"
    verification:
      - kind: integration
        ref: "tests/test_hermes_dispatch.py#test_hermes_dispatches_board_read_with_the_handler_session"
        status: pass
      - kind: unit
        ref: "tests/test_register.py#test_register_wires_board_read_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "board_read handles an empty board, a blank session, a delegate session, equal texts and display order"
    requirement: "TOOL-01"
    verification:
      - kind: unit
        ref: "tests/test_board_tools.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "The session comes only from the session_id keyword; a spoofed argument changes nothing"
    requirement: "TOOL-06"
    verification:
      - kind: integration
        ref: "tests/test_hermes_dispatch.py#test_hermes_dispatches_board_read_with_the_handler_session"
        status: pass
      - kind: unit
        ref: "tests/test_board_tools.py#test_read_ignores_a_session_id_in_the_arguments"
        status: pass
      - kind: unit
        ref: "tests/test_layout.py#test_core_never_reads_session_id_from_the_tool_arguments"
        status: pass
    human_judgment: false
  - id: D4
    description: "Tool name board_read, no todo in the name, first description sentence at most 60 characters, todo_list named once, boundary guard over plugin Python files"
    requirement: "TOOL-08"
    verification:
      - kind: unit
        ref: "tests/test_tool_text.py"
        status: pass
      - kind: unit
        ref: "tests/test_layout.py#test_plugin_python_files_never_mention_todo_outside_tool_text"
        status: pass
    human_judgment: false
  - id: D5
    description: "Whether the model calls board_read in real sessions (tool deferral, description pull)"
    requirement: "TOOL-01"
    verification: []
    human_judgment: true
    rationale: "Needs the real agent loop and a real model. The live test in plan 02-05 measures it."
---

# Phase 2 Plan 01: board_read end to end through Hermes Summary

Hermes in the gateway venv loads `plugin/` as the enabled plugin `hermes-session-tasks`, registers `board_read` in toolset `task-board`, injects the session id, and returns the board as a JSON string with markdown ids, the rev and an empty-board note.

## Performance

- Duration: about 25 min
- Completed: 2026-10-31
- Tasks: 2 of 2
- Files: 14 created or modified (12 created, 2 modified)
- Commits: 4 (two test, two feat)

## Accomplishments

- Task 1 (first end to end task): manifest, entry point, `wiring.register`, `tool_text`, `results`, `board_tools.board_read`, `FakeCtx`, and a hermes-marked test through the real Hermes registry. `hermes plugins validate` prints "Validation passed.".
- Task 2: empty-board note (D-15), blank-session refusal with no I/O, delegate read, equal-text adjacency and display-order tests, plus two layout guards: `session_id_arg_findings` (TOOL-06) and `todo_mention_findings` (`todo_list` boundary).
- The interfaces block of the plan now exists in code with the exact names. Plans 02-02 and 02-03 can build on `FakeCtx`, `tool_text`, `results` and `BoardTools`.

## TDD record

### Task 1

- RED: `uv run pytest tests/test_register.py -q` gave `1 error in 0.16s`: `ModuleNotFoundError: No module named 'session_tasks.wiring'` (the planned reason: the modules did not exist). The hermes test `test_hermes_dispatches_board_read_with_the_handler_session` failed on the planned assertion: `{'error': 'Unknown tool: board_read'} == {'ok': True, ...}`. Commit 85d2e76.
- Semantic assessment of RED: the dispatch snippet ran the real Hermes registry and reached the assertion for the planned behavior, so the hermes target failed for the intended reason. The `test_register.py` target failed at collection on the missing module, which the plan names as the expected RED. `gsd_run check tdd-red-evidence` supports TAP, JUnit, swift-testing, unittest and go reports, not pytest text, so I did not run it. I recorded the real command output instead.
- GREEN: commit e82476f. `test_register.py` 3 passed, dispatch test 1 passed, validate passed, ruff, format and pyright clean.

### Task 2

- RED: `uv run pytest tests/test_board_tools.py tests/test_results.py tests/test_tool_text.py tests/test_layout.py -q` gave `2 failed, 44 passed in 1.68s`. The two failures were `test_read_empty_board_returns_rev_zero_and_the_empty_note` and `test_read_board_with_every_item_removed_keeps_its_rev_and_the_note`, both on the missing `note` key. The other new tests passed at RED because Task 1 already built that behavior (blank session, spoofed argument, delegate, adjacency, order, guards). Commit 7569acf.
- GREEN: commit 5db09f8. `results.read_result` adds `note: "empty board"` for an empty board. 46 passed on the four files. `./scripts/check.sh` ended with `check: all ok`, on 3.11 (238 passed, coverage 96.99 percent) and on 3.14 (238 passed).
- REFACTOR: none needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Dispatch snippet discovered plugins before the plugin link existed**
- **Found during:** Task 1 GREEN
- **Issue:** After the implementation the hermes test still returned `Unknown tool: board_read`. Importing `model_tools` runs plugin discovery once, and `discover_plugins()` is idempotent. The snippet created the symlink and `config.yaml` after that import, so the first discovery never saw the plugin.
- **Fix:** The snippet now links and enables the plugin first, then imports the Hermes modules, then calls `discover_plugins()`. A code comment states why.
- **Files modified:** tests/hermes_dispatch_snippet.py
- **Verification:** `uv run pytest -m hermes tests/test_hermes_dispatch.py -q -rs` gives 1 passed, 0 skipped.
- **Commit:** e82476f

**Total deviations:** 1 auto-fixed (1 bug in a test helper). **Impact:** none on the plugin code. The fix lives in the same commit as the GREEN change.

## Decisions Made

- The hermes dispatch snippet links and enables the plugin before any Hermes import (see deviation 1).
- `plugin.yaml` version `0.1.0` equals `pyproject.toml`; `provides_tools` holds `board_read` only, and `provides_hooks` is empty until plan 02-04 adds the hooks.
- `register` lives in core `wiring.py`, as the plan chose.

## Issues Encountered

None open. `hermes plugins validate` reports `Isolation - runs in the plugin host (plugins.isolation: host)` for the real Hermes home. That is an informational line from Hermes. The dispatch test passes through the in-process loader. Plan 02-05 checks the behavior in the live gateway.

## Known Stubs

None.

## Threat Flags

None. The plan's threat register entries T-02-01 (spoofed session id) and T-02-02 (blank session) are mitigated and tested. T-02-03 holds because results carry only the rev, markdown and fixed error strings.

## Next Phase Readiness

Ready for 02-02 and 02-03. They use `FakeCtx`, `tool_text.BOARD_EDIT`, `results.describe` and `BoardTools`. Plan 02-04 adds the other registrations to `wiring.register`.

## Self-Check: PASSED

- Files exist: all 12 created files and both modified files found on disk.
- Commits exist in HEAD ancestry: 85d2e76, e82476f, 7569acf, 5db09f8.
- Commit order: the oldest 02-01 commit is `test(02-01)`.
- Plan verification: register, board_tools, results, tool_text and layout tests pass; hermes dispatch test passes with no skip; `hermes plugins validate` prints "Validation passed."; `./scripts/check.sh` ends with `check: all ok`.
