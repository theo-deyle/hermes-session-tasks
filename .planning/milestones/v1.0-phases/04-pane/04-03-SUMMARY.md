---
phase: 04-pane
plan: 03
subsystem: desktop-pane
tags: [hermes-desktop, tailwind, pytest, guards]
status: complete

requires:
  - phase: 04-pane
    provides: plan 04-01 pane first slice and the plugin_source fixture
provides:
  - a guard that fails when plugin.js uses a class name that the Desktop source never holds
  - guards for palette colour classes, named colours in a style, template literal class values and the 800 line ceiling
  - a self-test for every guard
affects: [04-04, 04-05, 04-06, 04-07, 04-08]

actuals:
  tokens: 3300
  tasks: 2
  commits: 3
plan_head_before: 8702406873a9d84cdcb85a3a24f2abd7999c57be
plan_head_after: 32dec66937339f7907ae9eb2ec822cc41f445363
commits: 3

tech-stack:
  added: []
  patterns:
    - class names are read from className string literals and *_CLASS constants, then checked as text against the Desktop source
    - every scan guard ships with a self-test that feeds it a bad sample

key-files:
  created: []
  modified:
    - tests/test_desktop_plugin.py

key-decisions:
  - "The shipped-class guard checks each token as plain text in the Desktop .ts, .tsx and .css files read once. It is a substring test, as the plan specifies."
  - "The line ceiling and the template literal guard got their own self-tests, so every new guard has one."

requirements-completed: [PANE-13]

duration: 12 min
completed: 2026-11-02
---

# Phase 4 Plan 03: Pane class and colour guards Summary

Test guards that fail the suite when plugin.js uses a class Desktop does not compile, a Tailwind palette colour, a named colour in a style, a template literal class value, or grows past 800 lines.

## Accomplishments

- `class_tokens` reads every `className: '...'` literal and every `const NAME_CLASS = '...'` literal, in order, without duplicates.
- `unshipped_classes` reads every `.ts`, `.tsx` and `.css` file under `apps/desktop/src` once and lists the tokens that appear nowhere.
- `test_every_plugin_class_ships_in_desktop` (marker `hermes`) runs this against the plan 04-01 plugin.js. It passed with no class replaced.
- Palette, style colour, plain literal and line ceiling guards, each with a self-test (`PALETTE_RE`, `STYLE_COLOUR_RE`, `TEMPLATE_CLASS_RE`, `over_line_ceiling`).

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 (red) | failing shipped-class guard | 428902a |
| 1 (green) | every pane class name ships in the Desktop source | 04d1bc4 |
| 2 | palette, style colour, literal form and line ceiling guards | 32dec66 |

Red line for Task 1: `3 failed, 26 deselected` (stubs raised `NotImplementedError`). Task 2 tests passed at once against the plan 04-01 file, as the plan expects.

## Verification

- `uv run pytest tests/test_desktop_plugin.py -q -rs -m hermes -k every_plugin_class_ships`: 1 passed, 0 skipped.
- `uv run pytest tests/test_desktop_plugin.py -q -rs -k "class_tokens_reads or unshipped_classes_reports"`: 2 passed.
- `uv run pytest tests/test_desktop_plugin.py -q -rs`: 37 passed, 0 skipped.
- ruff check, ruff format --check and pyright on tests/test_desktop_plugin.py: clean.
- plugin.js is 203 lines.
- check.sh output lines:
  - `check: python 3.11 ok` (667 passed, coverage 97.49 percent, gate 80)
  - `check: python 3.14 ok` (667 passed)
  - `check: all ok`

## Deviations from Plan

**1. [Rule 2 - Missing critical] Extra self-tests for two guards**
- **Found during:** Task 2
- **Issue:** The plan's truth "Each new guard has a self-test" holds for the palette and style colour guards in the behavior list, but not for the template literal guard or the line ceiling guard.
- **Fix:** Added `test_literal_scan_catches_a_template_class` and `test_line_ceiling_catches_a_long_file`, with a small `over_line_ceiling` helper and `TEMPLATE_CLASS_RE` and `MAX_PLUGIN_LINES` constants.
- **Files modified:** tests/test_desktop_plugin.py
- **Effect on verify:** the Task 2 `-k "palette or style or plain_literals or line_ceiling"` command reports 7 passed, not the 6 the plan lists, because `line_ceiling` matches both the guard and its self-test.
- **Commit:** 32dec66

**Total deviations:** 1 auto-fixed (1 missing critical). **Impact:** none on scope; plugin.js unchanged.

## Notes

- `class_tokens` follows the plan's two literal forms. A class inside a template literal such as the `pl-6` in ``${ROW_CLASS} pl-6`` is not scanned. `pl-6` has 13 hits in the Desktop source (plan evidence), so it ships. A later plan that adds a class in that form should put it in a `*_CLASS` constant so the guard sees it.
- The shipped-class test skips in a checkout without hermes-agent. It runs on devpc in every `./scripts/check.sh`.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- tests/test_desktop_plugin.py: FOUND
- Commits 428902a, 04d1bc4, 32dec66: FOUND on main
