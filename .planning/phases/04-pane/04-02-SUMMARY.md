---
phase: 04-pane
plan: 02
subsystem: desktop-pane-test-support
tags: [node-vm-harness, plugin-sdk-stubs, pytest, probe-plugin]
status: complete

requires:
  - phase: 04-pane
    provides: plan 04-01 harness with the Button and Checkbox stubs, pane_rig.py and the hooks guard
provides:
  - a node harness with a stub for every SDK name the pane uses
  - render-walk records for inputs, buttons, checkboxes, confirm, copy, tips and nodes
  - the steps click, clickText, check, type, key, blur, confirm, cancel, focus, event, outside and timers
  - the config keys restSequences and duringWrite, and the output keys atWrite, timeouts and outsideCalls
  - a test-only probe plugin and 18 harness self-tests that run through the real routes
affects: [04-03, 04-04, 04-05, 04-06, 04-07, 04-08]

actuals:
  tokens: 10774
  tasks: 3
  commits: 6
plan_head_before: 5c6806d99fb0ed02ab0752e1f3df8e2122c79826
plan_head_after: 918f35496a9d70abcd79788c46ac5fdad62e582a
commits: 6

tech-stack:
  added: []
  patterns:
    - the walk takes an output object and a context object {row, scroll, guard}
    - every stub type has its own walk case and is never called as a component
    - a peek render reads the pane at write time and runs no effects
    - one runStep function serves both the step list and duringWrite

key-files:
  created:
    - tests/fixtures/harness_probe.js
    - tests/test_pane_harness.py
  modified:
    - tests/desktop_pane_harness.mjs
    - tests/pane_rig.py

key-decisions:
  - "The probe plugin lives under tests/fixtures. The install script copies only plugin/desktop/plugin.js, so the probe never reaches a Desktop machine."
  - "Rig.error runs a harness call that must fail and returns stderr. It sits next to harness_error so a failing step test needs no manual relay."
  - "The outside step omits base_rev when the config gives none. The router treats a missing base_rev as zero for an add."
  - "A peek capture is taken for every POST, including a POST answered from restSequences or restOverrides."

requirements-completed: [PANE-04, PANE-05, PANE-07, PANE-11, PANE-12]

duration: 24 min
completed: 2026-11-01
---

# Phase 4 Plan 02: Pane harness stubs, records and steps Summary

The node harness now stubs every SDK component the pane uses, records what each render shows, and runs every step the pane plans 04-04 to 04-07 need. A small probe plugin proves each part through the real routes. `plugin/` is unchanged.

## Accomplishments

- The probe types `Buy milk` into the `Probe add` Input, presses Enter, and posts `{op: 'add', text}` with `base_rev` 0. The store holds the item with updated_by `user`, and the Input value is empty again.
- The harness stubs `Button`, `Checkbox`, `ConfirmDialog`, `CopyButton`, `EmptyState`, `Input`, `ScrollArea`, `Tip`, `icons` (`Trash2`, `Plus`, `ChevronRight`, `ChevronDown`), `host`, `useValue` and `cn`.
- The walk records `inputs`, `buttons` (label, row, disabled, className), `checkboxes` (with `guarded`), `confirm`, `copy`, `tips` and `nodes` (text, className, style, row, scroll). EmptyState title and description appear in `lines` and `nodes`.
- Steps: `click` (label, or label plus row), `clickText`, `check`, `type`, `key` (with optional `blur`), `blur`, `confirm`, `cancel`, `focus`, `event`, `outside` and `timers`. An unknown step, a selector with zero or two matches, a click on a disabled button and a confirm with no open dialog each fail the run with a message.
- Config: `restSequences` (a body, `__error__` or `__relay__` per call, then the override, then the relay) and `duringWrite` (steps run once inside the first POST). Each POST adds one `atWrite` capture taken by a render that runs no effects.
- `timeouts` lists every `ctx.setTimeout` ms. The `timers` step runs each pending callback whose cleanup was not called.
- The usage comment at the top of the harness lists every config key, step kind and output key.
- Rig helpers: `PROBE_JS`, `harness_error`, `inputs`, `the_input`, `button`, `stale_body`, and `Rig.error`.

## Task Commits

| Task | Name | Commit |
|------|------|--------|
| 1 (red) | failing probe test for Input typing and Enter | d4f1098 |
| 1 (green) | Input stub with type and key steps | ad159ca |
| 2 (red) | stub, record and step tests through the probe | b89c2bd |
| 2 (green) | component stubs, records and steps | 3220dfe |
| 3 (red) | focus, outside, timer, sequence and write-time tests | cda639d |
| 3 (green) | focus, outside, timers, sequences and write-time capture | 918f354 |

Red lines: Task 1 gave `2 failed` (the probe imported `Input`, which the harness did not stub). Task 2 gave `10 failed` (the probe imported `ConfirmDialog`, which the harness did not stub). Task 3 gave `6 failed, 12 passed` (the six new behavior tests; the stale body test and the unknown step test already passed).

## Verification

- `uv run pytest tests/test_pane_harness.py tests/test_desktop_plugin.py -q -rs`: 44 passed, 0 skipped (18 in test_pane_harness.py). `tests/test_desktop_plugin.py` needed no edit.
- `ruff check`, `ruff format --check` and `pyright` on `tests/pane_rig.py` and `tests/test_pane_harness.py`: clean.
- Acceptance greps: `duringWrite` 4, `restSequences` 2, `ConfirmDialog` 3, `Trash2|ChevronDown` 1 line, `def stale_body` 1, `Probe add` 1, `PROBE_JS` 1.
- No 04-02 commit touches a file under `plugin/`. The oldest 04-02 commit is `test(04-02)`.
- Em dash and en dash scan over every changed file: none found.
- `./scripts/check.sh` last lines:
  - `check: python 3.11 ok` (656 passed, coverage 97.49 percent)
  - `check: python 3.14 ok` (656 passed)
  - `check: all ok`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `Rig.error`**
- **Found during:** Task 1
- **Issue:** `harness_error(config, tmp_path, plugin)` needs a full config with a relay `baseUrl`. Every failing step test would build a relay by hand.
- **Fix:** Added `Rig.error(tmp_path, plugin, **config)` that wraps `harness_error` the same way `Rig.run` wraps `run_harness`. `run_harness` and `harness_error` share a private `_run_node`.
- **Files modified:** tests/pane_rig.py
- **Commit:** d4f1098

**2. [Rule 2 - Missing critical] Two extra tests**
- **Found during:** Tasks 2 and 3
- **Issue:** The plan lists no test for a `confirm` step with no open dialog, and none for an unknown step. Both are stated truths of the plan.
- **Fix:** Added `test_confirm_without_a_dialog_fails` and `test_unknown_step_fails`.
- **Files modified:** tests/test_pane_harness.py
- **Commits:** b89c2bd, cda639d

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing coverage). **Impact:** test support only. No plan contract changed.

## Auth Gates

None.

## Known Stubs

None. The probe `Probe copy all` Button and the probe checkbox handler do nothing by design: they exist so the harness can record disabled state and the guard.

## Threat Flags

None. The plan register covers the new surface (T-04-05 to T-04-07). The outside step posts only to `config.baseUrl`, the loopback relay over the tmp store. The probe lives under `tests/fixtures`.

## Next Phase Readiness

Ready for 04-03 and 04-04. The harness has every stub, record, step and config key the later pane plans name.

## Self-Check: PASSED

- FOUND: tests/desktop_pane_harness.mjs, tests/fixtures/harness_probe.js, tests/pane_rig.py, tests/test_pane_harness.py
- FOUND commits: d4f1098, ad159ca, b89c2bd, 3220dfe, cda639d, 918f354
