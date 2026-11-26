# Phase 2: Agent tools and skill - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-10-30
**Phase:** 02-agent-tools-and-skill
**Areas discussed:** Tool names, Write result shape, Guard before delete or uncheck, Subagents

Advisor mode was active. The research subagents were not spawned. The standing rule against option matrices applies, and the facts came from `.planning/research/` and the Hermes source on devpc.

---

## Tool names

| Option | Description | Selected |
|--------|-------------|----------|
| board_read, board_edit | Short and plain; Phase 6 adds board_sessions and board_copy | ✓ |
| session_board_read, session_board_edit | Names the board kind; longer in every call | |
| remember_read, remember_edit | Names the purpose; less obvious in the tool list | |

**User's choice:** board_read, board_edit

---

## Write result shape

| Option | Description | Selected |
|--------|-------------|----------|
| Changed items only | Rev, summary, one line per changed item; stale returns the full board | ✓ |
| Full board every time | Whole board on every call | |
| Rev and summary only | Agent must call board_read for new ids | |

**User's choice:** Changed items only

---

## Guard before delete or uncheck

| Option | Description | Selected |
|--------|-------------|----------|
| Block until confirmed | pre_tool_call blocks unless confirmed true; no dialog | ✓ |
| Desktop approval dialog | approve directive; Theo answers twice | |
| Rule in the descriptions only | No hook | |

**User's choice:** Block until confirmed

---

## Subagents

| Option | Description | Selected |
|--------|-------------|----------|
| Read only | board_read works; board_edit errors with a report-to-delegator message | ✓ |
| Read and write | Subagent writes straight to the board | |
| No access | Both tools error | |

**User's choice:** Read only

## Claude's Discretion

Tool description text, operation schema, skill content, plugin.yaml, registration, the post_compaction hook, the live 5-prompt test, the deferral check on devpc.

## Deferred Ideas

Stale-write HTTP transport (Phase 3), edit injection (Phase 5), cross-session tools (Phase 6), reorder and pane import (v2).
