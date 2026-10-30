# Phase 1: Core, storage and session identity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-10-30
**Phase:** 1-Core, storage and session identity
**Areas discussed:** Subtask depth, Item id form, Branch behaviour, Import rules

---

## Subtask depth

| Option | Description | Selected |
|--------|-------------|----------|
| Item plus one subtask level | Deeper pasted lines move up to the subtask level, count reported | ✓ |
| Three or more levels | Deeper parser and pane; indents do not fit a 260 to 320 px pane | |

**User's choice:** Recommendation accepted.
**Notes:** None.

---

## Item id form

| Option | Description | Selected |
|--------|-------------|----------|
| `#3` first, per-board integer never reused | `- [ ] #3 Call John`; export carries no ids | ✓ |
| `{#a3}` or `(a3)` | Alternatives from ARCHITECTURE.md and PITFALLS.md | |

**User's choice:** Recommendation accepted.
**Notes:** None.

---

## Branch behaviour

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy copy of the parent board on first use | New item ids, journal row names the parent, edits then separate | ✓ |
| Branch starts empty | Simpler; loses the list on a branch | |

**User's choice:** Recommendation accepted.
**Notes:** None.

---

## Import rules

| Option | Description | Selected |
|--------|-------------|----------|
| Plain bullet is an unchecked item; headings ignored; cap 100 items and 500 chars; empty text skipped | | ✓ |
| Skip plain bullets | Their checkbox children would attach to the wrong parent | |

**User's choice:** Recommendation accepted.
**Notes:** User said "all recommended" and asked to continue with `/gsd-plan-phase 1` after the commit.

## Claude's Discretion

Schema, migrations, write helper, journal size, alias table layout, lineage walker, test matrix wiring, two-process race test.

## Deferred Ideas

Write result contract (Phase 2), tool names (Phase 2), stale-write transport (Phase 3), archive versus delete (Phase 5), reorder and pane import (v2).
