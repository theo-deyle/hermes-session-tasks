---
phase: 07-deploy-and-hardening
plan: 05
subsystem: desktop-pane
tags: [accessibility, focus, live-region, neutral-wording, version]

requires:
  - phase: 06-cross-session-boards
    provides: the read-only view, the picker and the three review warnings in 06-UI-REVIEW.md
  - phase: 07-deploy-and-hardening
    provides: 07-01 neutral wording guard, 07-03 catalog entry
provides:
  - Back in the read-only view returns keyboard focus to the picker trigger
  - Both notice forms are live regions (role status)
  - The read-only banner is rounded like the other controls
  - The name scan covers every text file under plugin/, the pane file and plugin/README.md included
  - Version 0.2.0 in plugin.yaml, pyproject.toml, uv.lock, the pane and the catalog entry
affects: [07-06, 07-08, 07-09]

actuals:
  tokens: 3950
  tasks: 3
  commits: 3
plan_head_before: 30a94a06854cb17ad5bbe0ffb0381254aab1cdcf
plan_head_after: fb9a37de1aafdb8436ddd18c54f029db0b953286
commits: 3

tech-stack:
  added: []
  patterns:
    - "Only Pane holds hooks: the trigger ref and the focus flag live in Pane and reach PickerRow as a prop"
    - "A focus move needs a flag that only the user action sets, so a load, a pick or a focus change never moves focus"

key-files:
  created: []
  modified:
    - plugin/desktop/plugin.js
    - tests/desktop_pane_harness.mjs
    - tests/test_pane_readonly.py
    - tests/test_pane_copy.py
    - tests/test_pane_picker.py
    - tests/test_neutral_wording.py
    - plugin/plugin.yaml
    - pyproject.toml
    - uv.lock
    - tests/test_version.py
    - tests/test_desktop_plugin.py
    - catalog/hermes-session-tasks.yaml

key-decisions:
  - "back() sets the focus flag only when a board is under view (current.current.picked is not null). Picking the focused board from the menu while not viewing calls back() too, and a flag left set there would steal focus on a later focus change."
  - "The harness gives a Button ref a stand-in element whose focus() records the button label in focusCalls."

requirements-completed: [DEV-04, DEV-06]

coverage:
  - id: D1
    description: "Back returns keyboard focus to the picker trigger; load, pick and focus change move no focus"
    requirement: DEV-04
    verification:
      - kind: unit
        ref: "tests/test_pane_readonly.py#test_back_returns_keyboard_focus_to_the_picker_trigger"
        status: pass
      - kind: unit
        ref: "tests/test_pane_readonly.py#test_load_pick_and_focus_change_move_no_focus"
        status: pass
    human_judgment: false
  - id: D2
    description: "Both notice forms carry role status; the banner holds rounded-md and only the two theme tokens"
    requirement: DEV-04
    verification:
      - kind: unit
        ref: "tests/test_pane_copy.py#test_source_item_gone_reloads_and_shows_the_stale_notice, tests/test_pane_copy.py#test_copied_notice_is_three_pieces_on_one_line"
        status: pass
      - kind: unit
        ref: "tests/test_pane_picker.py#test_banner_uses_only_the_yellow_border_token"
        status: pass
    human_judgment: false
  - id: D3
    description: "The whole package names no person and no host"
    requirement: DEV-06
    verification:
      - kind: unit
        ref: "tests/test_neutral_wording.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every version holder reads 0.2.0 and uv.lock changes one line"
    requirement: DEV-04
    verification:
      - kind: unit
        ref: "tests/test_version.py, tests/test_catalog_entry.py, tests/test_desktop_plugin.py"
        status: pass
      - kind: other
        ref: "uv lock --check; git diff uv.lock shows the project version line only"
        status: pass
    human_judgment: false
  - id: D5
    description: "The real Desktop button receives the ref and focus() reaches the DOM node"
    verification: []
    human_judgment: true
    rationale: "The harness proves the pane logic with a stand-in element. The SDK Button spreads ref onto the button element (read in source, not run). The Mac and Windows passes in plan 07-09 use the real pane."

duration: 40min
completed: 2026-11-03
status: complete
---

# Phase 7 Plan 05: Pane Review Fixes and Version 0.2.0 Summary

**Back returns keyboard focus to the picker trigger through a ref flag set only by Back, both notices speak as live regions, the banner is rounded, the name scan covers the whole package, and every version holder reads 0.2.0.**

## Performance

- **Duration:** about 40 min
- **Completed:** 2026-11-03
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments

- A keyboard user who presses Back lands on the picker trigger. A first render, a pick, a live update and a session focus change move no focus (T-07-11).
- Both notice forms (plain text and the three-piece copied notice) carry `role: 'status'`, so a screen reader hears the copy result and the write notices.
- `BANNER_CLASS` holds `rounded-md` and still uses only the yellow border token and the primary text token.
- The pane header comment says "the user's edits". `tests/test_neutral_wording.py` now scans all 35 text files under `plugin/` (floor 30), `desktop/plugin.js` and `README.md` included.
- Version 0.2.0 in `plugin/plugin.yaml`, `pyproject.toml`, `PLUGIN_VERSION`, the catalog entry and `uv.lock`. The `uv.lock` diff is the one project version line (T-07-SC). An older pane copy now shows the version line against this backend (T-07-10).

## Task Commits

1. **Task 1: Back returns keyboard focus to the picker trigger** - `5c89c6a` (feat)
2. **Task 2: Notice live region, rounded banner, neutral comment, whole-package scan** - `dfca433` (feat)
3. **Task 3: Version 0.2.0 everywhere it lives** - `fb9a37d` (chore)

**Plan metadata:** the docs commit that holds this file.

## Files Created/Modified

- `plugin/desktop/plugin.js` - `triggerRef`, `focusAfterBack`, the focus effect, `role: 'status'` in `Notice`, `rounded-md` in `BANNER_CLASS`, neutral header comment, `PLUGIN_VERSION = '0.2.0'`
- `tests/desktop_pane_harness.mjs` - output key `focusCalls`, `role` in `nodes` and `titled`
- `tests/test_pane_readonly.py` - the two focus tests (the no-focus test runs for load, pick and focus change)
- `tests/test_pane_copy.py`, `tests/test_pane_picker.py` - role and rounded assertions
- `tests/test_neutral_wording.py` - whole-package scan; `text_files` takes the package folder only
- `plugin/plugin.yaml`, `pyproject.toml`, `uv.lock`, `catalog/hermes-session-tasks.yaml`, `tests/test_version.py`, `tests/test_desktop_plugin.py` - version 0.2.0

## Decisions Made

- `back()` sets `focusAfterBack` to `current.current.picked !== null`, not to `true`. The menu calls `back()` when the user picks the focused board while not viewing. An unconditional flag would stay set there and steal focus when a later session focus change clears the view.
- The mutation check: with the `trigger.focus()` call removed, `test_back_returns_keyboard_focus_to_the_picker_trigger` fails. The test measures the behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Focus flag could stay set and steal focus later**
- **Found during:** Task 1
- **Issue:** The plan said to set the flag to true in `back()`. `back()` also runs when the user picks the focused board with no other board under view. There `setPicked(null)` changes nothing, the effect does not run, and the flag stays true until a later focus change.
- **Fix:** The flag takes the value `current.current.picked !== null`.
- **Files modified:** `plugin/desktop/plugin.js`
- **Verification:** `test_load_pick_and_focus_change_move_no_focus` and the Back test pass.
- **Committed in:** `5c89c6a`

**2. [Rule 3 - Blocking] Commit trailer names the real model**
- **Issue:** The house rules text asks for `Co-Authored-By: Claude Fable 5.1`. This run is Claude Sonnet 5.5, and the harness attribution reminder names that model.
- **Fix:** All three commits end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

---

**Total deviations:** 2 (1 bug, 1 trailer wording)
**Impact on plan:** None on scope.

## Issues Encountered

None.

## Verification

| Check | Result |
|-------|--------|
| `node --check plugin/desktop/plugin.js` | pass |
| `uv lock --check` | pass |
| `./scripts/check.sh` (pin gate, ruff check, ruff format --check, pyright, pytest on 3.11 and 3.14) | `check: all ok`; 1160 passed on each interpreter; coverage 97.16 percent on 3.11 (floor 80) |
| `timeout 120 hermes plugins validate plugin --install-deps` | `Validation passed.` |

## Threat Flags

None. No new endpoint, auth path or file access.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The pane and the backend both read 0.2.0. Plans 07-06 to 07-09 can build on this version.
- The real-Desktop focus move waits for the Mac and Windows passes in plan 07-09.

## Self-Check: PASSED

- Commits `5c89c6a`, `dfca433`, `fb9a37d` are ancestors of HEAD.
- `plugin/desktop/plugin.js` holds `triggerRef`, `focusAfterBack`, two `role: 'status'` lines, `rounded-md` and `PLUGIN_VERSION = '0.2.0'`.
- `plugin/plugin.yaml` holds `version: 0.2.0`; `catalog/hermes-session-tasks.yaml` holds `version: "0.2.0"`.

---
*Phase: 07-deploy-and-hardening*
*Completed: 2026-11-03*
