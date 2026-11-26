---
phase: 04-pane
plan: 05
subsystem: desktop-pane
tags: [hermes-desktop, view, subtasks, copy-markdown, empty-state, pytest]
status: complete

requires:
  - phase: 04-pane
    provides: plan 04-04 write path (sendOp, viewBoard, notice line), plan 04-02 harness steps, plan 04-03 class guards
provides:
  - two-level groups in the pane with a collapse chevron and a done count on the parent row
  - the header with the N of M open count, the copy as markdown button and a hairline, outside the ScrollArea
  - boardMarkdown, the copy text in the same form as markdown.render(include_ids=False)
  - the empty board state and the no-chat state
  - collapse state per parent id, reset on a focus change
affects: [04-06, 04-07, 04-08]

requirements-completed: [PANE-01, PANE-02, PANE-11, PANE-12]

actuals:
  tokens: 4500
  tasks: 3
  commits: 6
plan_head_before: d6a3a30101d7934c5218a3413e7a7cb4e13ac661
plan_head_after: 415d65fd13a9cf5acdbf2083eb230381813ef117
commits: 6

tech-stack:
  added: []
  patterns:
    - ItemBlock is the one stateless block per top-level item; plan 04-06 adds the subtask add line inside it
    - every class string sits in a className literal or a *_CLASS constant so the shipped-class guard scans it
    - only Pane holds hooks; the early return for no focus sits after every hook call

key-files:
  created:
    - tests/test_pane_view.py
  modified:
    - plugin/desktop/plugin.js

key-decisions:
  - "The empty state shows only after the focused board has loaded (shown is not null), so a board that is still loading never flashes the empty text."
  - "The subtask row class is its own constant (SUBTASK_ROW_CLASS) instead of a template string, so the shipped-class guard sees pl-6."
  - "An orphan subtask (parent missing from the board) renders as a top-level entry, so no item ever disappears."

duration: 15 min
completed: 2026-11-01
---

# Phase 4 Plan 05: Pane view Summary

The pane now shows the board as two-level groups with a collapse chevron and a done count, checked items struck through in place, a header with the open count, the copy as markdown button and a hairline, both empty states, and a scrolling list that follows the focused session.

## Accomplishments

- `buildTree(items)` groups items by parent in board order. `subtaskCountText(children)` gives `{done}/{total}`.
- `boardMarkdown(items)` writes one line per item: two spaces for a subtask, `- [x] ` or `- [ ] `, the text with one leading backslash when it matches `^\\*#[0-9]+(?:\s|$)`, then a newline. It carries no id. A test compares its output with `render(board, include_ids=False)`.
- `Header` holds the count line (nothing at zero items) and `CopyButton` with `appearance: 'icon'`, label `Copy as markdown`, disabled on an empty board. A `border-b border-(--ui-stroke-secondary)` hairline sits under it. The notice line stays under the header.
- `ItemBlock` renders the parent row and then one row per subtask. The parent row has a 24px chevron column (a ghost `icon-xs` Button with a Tip, `ChevronDown` or `ChevronRight`), the checkbox, the text and the count. A subtask row has `pl-6`, the checkbox and the text.
- `collapsed` state in `Pane` toggles per parent id and resets in the `[sid]` effect. A collapsed parent keeps its count.
- A checked item keeps its place with `line-through` and `text-(--ui-text-secondary)`. A parent and its subtasks send one `set_checked` each.
- An empty loaded board shows `The agent adds items here.` and `Add one below.`. No focused chat shows `Open a chat to see its items.` with no header, no list and no board call.
- The item list sits in a `ScrollArea` with `min-h-0 flex-1`. The header sits above it.

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 (red) | failing end to end test for subtask groups and copy | 6da47f6 |
| 1 (green) | subtask groups, header copy button and scroll area | 570987d |
| 2 (red) | collapse, done style, independent check and focus switch tests | a1b43d2 |
| 2 (green) | collapse, done style and focus switch | 1ac8753 |
| 3 (red) | empty state, copy escape, long text and header position tests | 60dfd2c |
| 3 (green) | empty states and long text layout | 415d65f |

Red lines: Task 1 gave `1 failed` (no `1/2` count). Task 2 gave `2 failed, 5 passed`: the collapse and expand tests fail. The done style, independent check and focus switch tests passed at once because plans 04-01 to 04-04 already built them; the collapse reset test passed until the reset line was removed, and a mutation check (reset removed) made it fail. Task 3 gave `2 failed, 10 passed`: the empty state and no-chat tests fail.

## Verification

- `uv run pytest tests/test_pane_view.py tests/test_pane_writes.py tests/test_desktop_plugin.py -q -rs`: 63 passed, 0 skipped (12 in tests/test_pane_view.py). The hermes shipped-class test passes, so `border-(--ui-stroke-secondary)`, `pl-6`, `min-h-0` and the other new classes ship in Desktop.
- ruff check, ruff format --check and pyright on tests/test_pane_view.py: clean. `node --check plugin/desktop/plugin.js`: clean.
- Acceptance greps: `function boardMarkdown` 1, `Copy as markdown` 1, `pl-6` 1, `border-(--ui-stroke-secondary)` 1, `Expand subtasks` 1, `line-through` 1, `ChevronRight` 1, `The agent adds items here.` 1, `Open a chat to see its items.` 1, `overflowWrap: 'anywhere'` 1.
- The oldest 04-05 commit is `test(04-05)`.
- plugin.js is 454 lines (ceiling 800).
- Em dash and en dash scan over plugin.js and tests/test_pane_view.py: none found.
- `./scripts/check.sh` last lines:
  - `check: python 3.11 ok` (693 passed, coverage 97.49 percent, gate 80)
  - `check: python 3.14 ok` (693 passed)
  - `check: all ok`

## Deviations from Plan

None - plan executed exactly as written.

## Notes

- The harness does not record the row `div` class, so the `pl-6` indent is checked by the acceptance grep and by the shipped-class guard only. Plan 04-08 checks the indent on the Mac (the plan's flagged assumption).
- The chevron click in `ItemBlock` reaches `onToggle(item.id)`; the subtask add line of plan 04-06 goes at the end of the block `div`.
- Task 2's done-style test needed no code change: `DONE_STYLE`, `DONE_CLASS` and the `Pane` text style came from the first plans.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- plugin/desktop/plugin.js: FOUND
- tests/test_pane_view.py: FOUND
- Commits 6da47f6, 570987d, a1b43d2, 1ac8753, 60dfd2c, 415d65f: FOUND on main
