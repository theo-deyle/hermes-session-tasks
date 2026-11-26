# Phase 5: Agent sees Theo's edits - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-11-02
**Phase:** 5-Agent sees Theo's edits
**Areas discussed:** The note the agent sees, Quiet turns, Delete and archive

---

## The note the agent sees

| Option | Description | Selected |
|--------|-------------|----------|
| One line per Theo change from the journal, cap near 1000 chars, pointer line above the cap | Agent edits left out | ✓ |
| Inject the full board when the revision changed | Larger, replayed every later turn (P1) | |

## Quiet turns

| Option | Description | Selected |
|--------|-------------|----------|
| Hook returns the delta or None; own-plan rule in the system prompt section only | Meets criterion 2 | ✓ |
| Keep the static nudge line every turn | Violates criterion 2 | |

## Delete and archive

| Option | Description | Selected |
|--------|-------------|----------|
| Archive keeps; delete reasons remove aliases and the board; no sweep | Hook only | ✓ |
| Hook plus an orphan sweep | More code for a case Hermes does not need yet | |

Theo accepted all three recommendations in one reply ("accepted").

## Claude's Discretion

When seen advances, delegate silence, platform value, journal cap, token measurement method, hot mount versus restart, unit test list.

## Deferred Ideas

Orphan board sweep (later phase); cross-session tools and picker (Phase 6).
