# Phase 4: Pane - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-11-01
**Phase:** 4-Pane
**Areas discussed:** Add an item, Edit the text, Delete, Checked items, Stale write

---

## Add an item

| Option | Description | Selected |
|--------|-------------|----------|
| Always-present bottom line, Enter keeps the cursor | Hover "+" for a subtask | ✓ |
| Add button opens a dialog | One item per dialog | |

## Edit the text

| Option | Description | Selected |
|--------|-------------|----------|
| Click to edit in place, Enter saves, Escape cancels | Blur saves | ✓ |
| Edit through a row menu | Extra click per edit | |

## Delete

| Option | Description | Selected |
|--------|-------------|----------|
| Hover trash, confirm only when subtasks go too | SDK ConfirmDialog with the count | ✓ |
| Confirm every delete | Slower for the common case | |

## Checked items

| Option | Description | Selected |
|--------|-------------|----------|
| Stay in place, struck through, header shows N of M open | No reorder, no hide | ✓ |
| Move done items to the bottom | Items jump on each check | |

## Stale write

| Option | Description | Selected |
|--------|-------------|----------|
| Optimistic, retry a check once, keep typed text for add and edit | Short notice line | ✓ |
| Block the pane until the write returns | Slower feel | |

Theo accepted all five recommendations in one reply ("sounds good").

## Claude's Discretion

Collapse state in the pane only, poll interval, copy button placement, empty state wording, test harness extension, no separate UI design contract.

## Deferred

Clear all done items (backlog); undo toast on delete (PANE-16, v2).
