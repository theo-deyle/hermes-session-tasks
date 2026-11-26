---
phase: 02-agent-tools-and-skill
plan: 04
subsystem: agent-tools
tags: [hermes-plugin, board-edit, hooks, prompt-section, skill, dispatch-contract, pytest]
status: complete

requires:
  - phase: 02-agent-tools-and-skill
    provides: BoardTools.board_read, results.describe/read_result/error_result, wiring.register and skill_path (plan 02-01)
  - phase: 02-agent-tools-and-skill
    provides: edit_args.parse and OP_FIELDS, hooks.make_pre_tool_call and make_post_compaction, guard (plan 02-02)
  - phase: 02-agent-tools-and-skill
    provides: tool_text schema, prompt section and skill constants (plan 02-03)
provides:
  - BoardTools.board_edit (item-level ops, actor agent, D-13 success shape, D-14 stale shape, D-16 rule errors, D-20 delegate refusal)
  - BoardTools.after_write callback (no-op default, the Phase 3 broadcast seam)
  - results.DELEGATE_EDIT, summary_line, applied_result, stale_result
  - wiring.register with board_edit, both hooks, the prompt section and the skill
  - plugin.yaml provides_tools and provides_hooks equal to the registrations
  - Hermes dispatch contract test for the whole agent half
affects: [02-05, 02-06, 02-07, 03-desktop-pane]

actuals:
  tokens: 8526
  tasks: 2
  commits: 4
plan_head_before: 9fb9312479379bdbda1fa4aeca5a55f23dd1547b
plan_head_after: c78871ae3e2b2a9df0861516f482f5752361f1c1

tech-stack:
  added: []
  patterns:
    - "The handler and the hook share one parser (edit_args.parse); the handler never reads confirmed"
    - "A listener fault after a committed write is logged as a warning and never changes the result"
    - "The dispatch snippet runs under the gateway venv Python and prints one JSON line; the pytest module asserts on it"

key-files:
  created: []
  modified:
    - plugin/session_tasks/results.py
    - plugin/session_tasks/board_tools.py
    - plugin/session_tasks/wiring.py
    - plugin/plugin.yaml
    - tests/test_board_tools.py
    - tests/test_results.py
    - tests/test_register.py
    - tests/hermes_dispatch_snippet.py
    - tests/test_hermes_dispatch.py

key-decisions:
  - "board_edit sends base_rev 0 when the call has none: the parser requires base_rev for every op on an existing item, and a top-level or parent_ref add is never stale"
  - "after_write runs inside board_edit with the literal self.after_write(resolution.root_id), wrapped in try and except Exception with a logged warning"
  - "The manifest test compares sorted lists, so the manifest order is board_read then board_edit and pre_tool_call then post_compaction"
  - "A changed subtask line comes from render() on a one-item board, so the escape rule and the two-space indent stay the Phase 1 rules"

patterns-established:
  - "Result shapes: success has ok and no error; every failure has a top-level error; a stale failure also carries stale, reason, op_index, item_id, rev and the full board"
  - "RED stubs return empty values so the new tests fail on assertions, not on import errors"

requirements-completed: [TOOL-02, TOOL-06, TOOL-07, TOOL-08, AGNT-03]

coverage:
  - id: D1
    description: "board_edit applies add, set_text, set_checked and remove in one call as actor agent and returns the rev, a one-line summary and one agent-view line per changed item"
    requirement: "TOOL-02"
    verification:
      - kind: unit
        ref: "tests/test_board_tools.py#test_edit_adds_items_and_returns_the_changed_lines"
        status: pass
      - kind: unit
        ref: "tests/test_board_tools.py#test_edit_renames_checks_unchecks_and_removes_in_one_call"
        status: pass
    human_judgment: false
  - id: D2
    description: "A stale write returns the current board and writes nothing; a rule error names the op index and writes nothing"
    requirement: "TOOL-07"
    verification:
      - kind: unit
        ref: "tests/test_board_tools.py#test_stale_write_returns_the_current_board"
        status: pass
      - kind: unit
        ref: "tests/test_board_tools.py#test_rule_errors_name_the_op_index_and_write_nothing"
        status: pass
    human_judgment: false
  - id: D3
    description: "The session comes from the Hermes keyword only, and a delegate session cannot write"
    requirement: "TOOL-06"
    verification:
      - kind: unit
        ref: "tests/test_board_tools.py#test_edit_ignores_a_session_id_in_the_arguments"
        status: pass
      - kind: unit
        ref: "tests/test_board_tools.py#test_delegate_session_cannot_edit"
        status: pass
    human_judgment: false
  - id: D4
    description: "register records two tools in one toolset, two hooks, the prompt section and the skill, and the manifest declares exactly those tools and hooks"
    requirement: "TOOL-08"
    verification:
      - kind: unit
        ref: "tests/test_register.py#test_manifest_provides_exactly_the_registered_tools_and_hooks"
        status: pass
      - kind: integration
        ref: "hermes plugins validate and hermes plugins doctor --ci on plugin/"
        status: pass
    human_judgment: false
  - id: D5
    description: "The real Hermes registry adds, blocks an unconfirmed remove (raw and coerced), applies a confirmed remove, follows a compaction, renders the section, lists the skill and shows each first sentence whole in the tool search catalog"
    requirement: "AGNT-03"
    verification:
      - kind: integration
        ref: "tests/test_hermes_dispatch.py#test_hermes_dispatches_board_edit_guard_hooks_prompt_and_skill"
        status: pass
    human_judgment: false
---

# Phase 2 Plan 04: board_edit and full wiring Summary

`board_edit` now writes item-level ops through `BoardStore.apply` as actor agent, and `register(ctx)` connects both tools, both hooks, the prompt section and the skill. The real Hermes registry runs the whole agent half.

## Accomplishments

- `board_edit` returns the D-13 success shape (`ok`, `rev`, `summary`, `changed`), the D-14 stale shape (current rev and full board), and the D-16 rule error (`op N: <rule>`). Nothing is written on any rejection.
- A delegate session gets `DELEGATE_EDIT` before parse and apply (D-20). A `session_id` inside the arguments is ignored.
- `BoardTools.after_write` runs once with the root id after a write that changes items. A no-change batch, a stale write, a rule error, a blank session and a delegate session never call it. A listener that raises is logged and the applied result still returns.
- `wiring.register` adds `board_edit`, `pre_tool_call`, `post_compaction`, the prompt section (max_chars `PROMPT_SECTION_MAX`) and the skill (`SKILL_DESCRIPTION`). `plugin.yaml` lists the same tools and hooks.
- The cross-check that 02-03 asked for exists: `test_schema_matches_the_parser` compares the schema op enum and item properties with `edit_args.OP_FIELDS`.
- The dispatch snippet drives the real registry in the gateway venv: add, unconfirmed remove blocked, raw-JSON remove blocked by `get_pre_tool_call_directive`, confirmed remove applied, compaction alias, a `read_file` check with no directive, the rendered prompt section, the skill key `hermes-session-tasks:board-rules`, and the tool search catalog line of each tool.

## TDD Gate Compliance

Task 1
- RED: `a6748da` `test(02-04): add failing board_edit handler tests`. The commit also holds stubs (`board_edit` returns an empty error, the result functions return empty strings) so the tests fail on assertions and not on import errors. `uv run pytest tests/test_board_tools.py tests/test_results.py` gave 30 failed, 21 passed. `gsd check tdd-red-evidence` on the JUnit report returned `RED_EVIDENCE_OK` for target `test_edit_adds_items_and_returns_the_changed_lines`. Semantic assessment: the target ran and failed on the planned assertion (the stub returned `{"error": ""}` where the D-13 shape was expected).
- GREEN: `40cbd67` `feat(02-04): board_edit handler and write results`. 51 passed.

Task 2
- RED: `fe02425` `test(02-04): add failing registration and Hermes dispatch tests`. 6 failed, 5 passed. `RED_EVIDENCE_OK` for target `test_register_records_both_hooks`. Semantic assessment: the target failed on `sorted(ctx.hooks) == ["post_compaction", "pre_tool_call"]` because no hook was registered. The dispatch test failed with a missing `edit_add` key because the snippet did not yet run the new calls.
- GREEN: `c78871a` `feat(02-04): wire board_edit, hooks, prompt section and skill`. All suites pass.

No REFACTOR commit was needed. The RED record files were kept in the scratchpad or removed after the check, so the repo holds none.

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/test_board_tools.py tests/test_results.py -q` | 51 passed (plan floor 35) |
| `uv run pytest tests/test_register.py -q` | 9 passed (plan floor 7) |
| `uv run pytest -m hermes -q -rs` | 5 passed, 0 skipped, no "real Hermes home gained" |
| `hermes plugins validate .../plugin` (real HERMES_HOME) | "Validation passed." |
| `hermes plugins doctor .../plugin --ci` | exit 0, 2 tools, 2 hooks |
| `./scripts/check.sh` | `check: python 3.11 ok`, `check: python 3.14 ok`, `check: all ok`; 416 passed on each; coverage TOTAL 98 percent |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] RED stubs added so the tests fail on assertions**
- **Found during:** Task 1 RED
- **Issue:** With no stubs the new tests failed at import (`DELEGATE_EDIT` and `applied_result` missing). tdd.md calls that INVALID_RED.
- **Fix:** The RED commit adds empty-valued stubs for `DELEGATE_EDIT`, `summary_line`, `applied_result`, `stale_result`, `board_edit` and the `after_write` field. GREEN replaces them.
- **Files modified:** plugin/session_tasks/results.py, plugin/session_tasks/board_tools.py
- **Commit:** a6748da

**2. [Rule 1 - Bug] Manifest test compared an unsorted manifest list with a sorted registry list**
- **Found during:** Task 2 GREEN
- **Issue:** `manifest_list("provides_tools") == sorted(ctx.tools)` failed because the plan lists `board_read` before `board_edit`.
- **Fix:** The test now sorts both sides. It still fails on any extra, missing or duplicate name.
- **Files modified:** tests/test_register.py
- **Commit:** c78871a

**3. [Rule 3 - Blocking] ruff and pyright fixes in the dispatch snippet**
- **Found during:** Task 2 `check.sh`
- **Issue:** One import line was too long, and three dict literals needed an explicit `dict[str, object]` type.
- **Fix:** Wrapped the import and added the annotations.
- **Files modified:** tests/hermes_dispatch_snippet.py
- **Commit:** c78871a

### Acceptance criterion note

`grep -c 'register_hook(' plugin/session_tasks/wiring.py` prints 3, not 2. The third match is the `register_hook` method in the `PluginContext` Protocol, which must stay. `grep -c 'ctx.register_hook(' ...` prints 2, which is the intent of the criterion.

**Total deviations:** 3 auto-fixed (1 Rule 1, 2 Rule 3), 1 criterion note. **Impact:** none on behavior.

## Observations

- `hermes plugins validate` reports `Isolation - runs in the plugin host (plugins.isolation: host)` on this machine. CLAUDE.md lists the default as `in_process` and `~/.hermes/config.yaml` had no isolation key on 2026-10-30. Validation and doctor both pass in host mode, and the SQLite design already works across processes. Plan 02-05 (install) and Phase 3 (broadcast through `after_write`) should read the live setting.
- RESEARCH Pitfall 10 (a compressed delegate resolves as compression) stays recorded and unfixed, as the threat register says.

## Known Stubs

None. The `_no_listener` default does nothing on purpose: Phase 3 passes the real broadcast as `after_write`.

## Threat Flags

None. No new endpoint, auth path or file access beyond the plan's threat model (T-02-12 to T-02-15 are covered by the delegate, schema, result-shape and spoofed-id tests).

## Self-Check: PASSED

All nine files exist, commits `a6748da`, `40cbd67`, `fe02425` and `c78871a` are ancestors of HEAD, and `git rev-list --count` from the recorded base gives 4.
