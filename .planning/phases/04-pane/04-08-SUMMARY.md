---
phase: 04-pane
plan: 08
subsystem: live-test
tags: [hermes-plugin, live-test, desktop-pane, mac, PANE-01, PANE-02, PANE-03, PANE-04, PANE-05, PANE-06, PANE-07, PANE-08, PANE-11, PANE-12, PANE-13]

# Dependency graph
requires:
  - phase: 04-pane
    provides: the real pane (plans 04-01 to 04-07), the install script -RemotePath (plan 04-09)
provides:
  - Live proof on the Mac for every Phase 4 success criterion, each step checked in data.db
  - Two pane fixes found at step 1 of the round (visible checkbox border, rows flush left)
  - The Mac test board deleted on Theo's recorded yes
affects: [phase-05, phase-06, phase-07, 03-10, 03-11, 03-12]

# Actuals (#2632)
actuals:
  tokens: 1500
  tasks: 13
  commits: 2
plan_head_before: 45ba6fb
plan_head_after: 2f3b6ca

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The SDK Checkbox border (`border-input`) fades into the dark theme; the pane sets `border-(--ui-text-tertiary)` on it"
    - "No empty layout column on the left of a row: the collapse chevron sits after the text, so every row starts at its checkbox"

key-files:
  created:
    - .planning/phases/04-pane/04-08-SUMMARY.md
  modified:
    - plugin/desktop/plugin.js
    - tests/test_desktop_plugin.py

key-decisions:
  - "The collapse chevron sits after the item text, not in a left column, so items and the add line share one left edge."

patterns-established:
  - "Live round evidence: every step Theo reports is compared with a read-only data.db query before the next step"

requirements-completed: [PANE-01, PANE-02, PANE-03, PANE-04, PANE-05, PANE-06, PANE-07, PANE-08, PANE-11, PANE-12, PANE-13]
---

# Phase 4 Plan 08: Mac live check Summary

**The real pane passed every step on the Mac: live update from the agent, check, add, edit, subtask add, delete with confirm, copy as markdown.** Two defects surfaced at step 1 and were fixed in the same turn.

Theo's answer: yes ("delete it", 2026-11-02)

## Task 1: devpc checks

| Check | Result |
|-------|--------|
| `./scripts/check.sh` | `check: all ok` (732 passed on 3.11 and 3.14) |
| `hermes plugins validate` | `Validation passed.` |
| plugin.js SHA-256 before the round | `e4b184c88c2b6dbd80278ad5d09e5c7cdc423d6d69d394a2d7539c34d84c11c9` |
| No restart needed | `git diff --name-only 9625801^ HEAD -- plugin ':(exclude)plugin/desktop'` printed nothing |
| T0 | `2026-11-02T02:42:19Z`, live_check.py printed no board after T0 |

## Round record

Local time is UTC-5. Test board: `20261101_220401_f74be5` (chat "Add trip, call John, email").

| Step | Request | Theo reported | data.db | Result |
|------|---------|---------------|---------|--------|
| 1 install | Run the install line, paste the sha256 line | Screenshot: unchecked boxes invisible, rows indented past the add line | - | two defects, fixed (below); Theo reported the pane updated on its own after the fix commit, no second install line run |
| 2 new chat | Start a new chat, report the pane | `Open a chat to see its items.` | - | pass (no stored id before the first message) |
| 3 agent write | Send the five-item message, screenshot | Screenshot 10.04.28 PM: five items, chevron and `0/2`, subtasks indented, header `5 of 5 open`, long text wraps, copy icon in header | rev 1, five items by agent at `03:04:21Z` | pass |
| 4 check | Tick Call John | strikethrough, box checked, line stayed | item 4 checked by user | pass |
| 5 add | buy milk, Enter, buy bread, Enter | no second click needed, count rose each time | items 9, 10 by user (Theo also added 11 buy turkey) | pass |
| 6 edit | Change the Email Ann text | "It says what I typed" | item 5 text `Email An. about the budget` by user | pass |
| 7 subtask | Hover Call John, plus, find his number | plus and trash on hover, new line indented under the row | item 12 parent 4 by user | pass |
| 8 dialog | Trash on Plan the trip | "delete this item and 2 subtasks? Keep Item / Delete item and subtasks" | - | pass |
| 9 delete | Click Delete item and subtasks | "Everything except that item and its subtasks" | items 1, 2, 3 gone, rev 16 | pass |
| 10 copy | Copy icon, save as board-copy.md | file saved | paste equals the board line for line, subtask indented two spaces, no ids | pass |
| 11 question | Delete the Mac test board? | "delete it" | - | recorded |

Screenshots: `~/share/hermes-todo/Screenshot 2026-11-01 at 9.43.50 PM.png` (defects), `Screenshot 2026-11-01 at 10.04.28 PM.png` (step 3). Paste: `~/share/hermes-todo/board-copy.md`.

## Defects found at step 1 and fixed in the same turn (rule 33)

| Defect | Cause | Fix | Commits |
|--------|-------|-----|---------|
| Unchecked box invisible on the dark theme | SDK Checkbox border `border-input` has no contrast there | `CHECK_CLASS = 'border-(--ui-text-tertiary)'` on the Checkbox | `2f3b6ca` |
| Items indented past the add line | Every row carried an empty 24px chevron column | Chevron renders only for rows with subtasks and sits after the text; rows start at the checkbox | same |

Test commit first: `test(04-08): add failing tests for a visible checkbox and left-aligned rows`, then `fix(04-08): visible checkbox border and rows that start at the left edge` (`2f3b6ca`). 122 pane tests pass. plugin.js is 789 lines. SHA-256 after the fix: `04adc10fda44b3cb` (prefix).

## Task 13: deletion

Dry run before: `{'boards': 1, 'items': 6, 'changes': 22, 'aliases': 1}`. Apply ran behind the `grep -q "^Theo's answer: yes"` check. Dry run after: all zero. Boards in data.db: 19 before, 18 after. Script: `cleanup_boards.py` in the session scratchpad (the plan 03-12 Task 2 contract: dry run by default, `--apply` deletes aliases then boards in one `BEGIN IMMEDIATE` transaction, items and changes cascade).

## Observations for later plans

- Theo emptied the Phase 3 Mac board `20261101_162121_506689` himself through the pane (rev 6, no items). Plan 03-12 still lists it for deletion.
- Desktop on the Mac picked up the fixed plugin.js without a second install run (Theo: "it updated"). The install script copies into the fs-watched disk slot; how the Mac got the new file is not recorded. Phase 7 (DEV-04) should settle the update path.
- No gateway and no backend restart in this phase.

## Deviations

1. Two pane fixes with two commits in a plan that planned no file change (rule 33).
2. Step 1's hash line was not reported; Theo chose to continue with the pane that had updated (rule 24).

## Next Phase Readiness

Phase 4 is complete on the Mac. Phase 3 plans 03-10 to 03-12 (Windows PC) remain, with the frozen Phase 3 pane and `-RemotePath`. Phase 5 can start.
