---
phase: 04-pane
plan: 01
subsystem: desktop-pane
tags: [hermes-desktop, plugin-sdk, esm, node-vm-harness, pytest]
status: complete

requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: the dock registration, the loopback relay, the real router and the Phase 3 pane contracts
provides:
  - the Session tasks pane first slice: checkbox rows, an N of M open header and a check write through the real route
  - tests/pane_rig.py, the shared rig for every later pane test
  - a harness that records checkboxes, runs the check step and rejects a hook outside the top-level component
affects: [04-02, 04-03, 04-04, 04-05, 04-06, 04-07, 04-08]

actuals:
  tokens: 8200
  tasks: 2
  commits: 4
plan_head_before: 3074b14347f4326d09cbc7f8b4ef840c76088753
plan_head_after: c7b144d58608861202bbb07e94b26c3c3314c992
commits: 4

tech-stack:
  added: []
  patterns:
    - one hook-owning Pane component with stateless child components
    - long-lived callbacks read a ref, never a render closure
    - optimistic board update with applyOp, then take the reply board

key-files:
  created:
    - tests/pane_rig.py
  modified:
    - plugin/desktop/plugin.js
    - tests/desktop_pane_harness.mjs
    - tests/conftest.py
    - tests/test_desktop_plugin.py

key-decisions:
  - "The pane keeps every React hook in Pane. Header and ItemRow are plain functions of their props. The harness enforces it."
  - "The pane holds one state value, server: the last accepted board reply tagged with its session id. A board for another session never shows."
  - "The optimistic check keeps the server rev. The write sends that rev as base_rev."

requirements-completed: [PANE-01, PANE-03, PANE-13]

duration: 6 min
completed: 2026-11-02
---

# Phase 4 Plan 01: First slice of the Session tasks pane Summary

The Session tasks pane now shows the focused board as checkbox rows under an `N of M open` header, and a check goes through the real route to the store and back, proven in the node VM harness.

## Accomplishments

- A check on item 1 sends `POST /board/edit` with `{session_id: 's1', ops: [{op: 'set_checked', item_id: 1, checked: true}], base_rev: 1}`. The store holds item 1 checked by `user` at rev 2. The pane shows the checked box and `0 of 1 open`.
- Each item is an SDK `Checkbox` with the item text as `aria-label`, inside a row with `data-item-id`. The item text is a plain string child.
- The header shows `{open} of {total} open` and shows nothing for an empty board.
- The Phase 3 contracts hold: right dock registration, focus read through `useValue`, no board call without focus, 6000 ms poll, reload on each `board.updated` event, and the version mismatch line.
- The plugin name is `Session tasks`. The Phase 3 diagnostic lines, the write test button and its routine are gone.
- The harness fails a run when a component other than the top-level pane component calls a hook.

## Task Commits

| Task | Name | Commit |
|------|------|--------|
| 1 (red) | failing end to end test for a pane check | 9625801 |
| 1 (green) | checkbox rows and the check write | 75c784a |
| 2 (red) | plugin name and hooks guard tests | c5c5245 |
| 2 (green) | hooks guard in the harness, final plugin name | c7b144d |

Red line for Task 1 (`uv run pytest tests/test_desktop_plugin.py -q -rs -k check_reaches_the_store`): `Error: no checkbox in row 1` from the harness check step, `1 failed, 22 deselected`.
Red line for Task 2: `2 failed, 1 passed, 23 deselected` (the name test and the hooks guard test failed, the top-level hook test passed before the guard existed).

## Verification

- `uv run pytest tests/test_desktop_plugin.py tests/test_version.py -q -rs`: 33 passed, 0 skipped.
- `node --check plugin/desktop/plugin.js`: exit 0.
- `ruff check`, `ruff format --check` and `pyright` on the three changed Python test files: clean.
- First 04-01 commit is a `test(04-01)` commit.
- Acceptance greps: `data-item-id` 1, `Checkbox` 2, `Run write test` 0, `TEST_ITEM_TEXT` 0, `Session tasks (test)` 0, `PLUGIN_VERSION = '0.1.0'` 1, dock literal 1, `def run_harness` in `tests/pane_rig.py` 1 and in `tests/test_desktop_plugin.py` 0.
- Em dash and en dash scan over every changed file: none found.
- `./scripts/check.sh` last lines:
  - `check: python 3.11 ok` (631 passed, coverage 97.49 percent)
  - `check: python 3.14 ok` (631 passed)
  - `check: all ok`

## Deviations from Plan

None - plan executed exactly as written.

## Auth Gates

None.

## Known Stubs

None. The pane writes only `set_checked` in this plan. `applyOp` returns the board unchanged for other ops by design. Plans 04-02 to 04-07 add the other ops.

## Threat Flags

None. The plan's register covers every new surface (T-04-01 to T-04-04).

## Next Phase Readiness

Ready for 04-02. The shared rig, the `Checkbox` stub, the `check` step, the row tracking and the hooks guard are in place for the later pane plans.

## Self-Check: PASSED

- FOUND: tests/pane_rig.py, plugin/desktop/plugin.js, tests/desktop_pane_harness.mjs, tests/conftest.py, tests/test_desktop_plugin.py
- FOUND commits: 9625801, 75c784a, c5c5245, c7b144d
