# Phase 3: REST router and client install spike - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-10-31
**Phase:** 3-REST router and client install spike
**Areas discussed:** Stale write over HTTP, Route shape, Desktop half install, Own-plan nudge, Version banner

---

## Stale write over HTTP

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP 200 structured | `ok: false, error: stale, board` in a 200 body | ✓ |
| HTTP 409 | Status code carries the stale signal; Desktop drops the body | |

**User's choice:** HTTP 200 structured (recommended).

## Route shape

| Option | Description | Selected |
|--------|-------------|----------|
| One ops route | `POST /board/edit` with the tool's `ops` and `base_rev` | ✓ |
| Per-item routes | `PATCH /board/items/<id>` and friends | |

**User's choice:** One ops route (recommended).

## Desktop half install

| Option | Description | Selected |
|--------|-------------|----------|
| pwsh copy script | One `install-desktop.ps1` copies the file over SSH to the disk slot | ✓ |
| Install from Git | Desktop dialog clones the private repo; needs a credential per machine | |

**User's choice:** pwsh copy script (recommended).

## Own-plan nudge

| Option | Description | Selected |
|--------|-------------|----------|
| Nudge every turn, board when not empty | Phase 5 narrows to a delta | ✓ |
| Full board every turn | More injected text | |

**User's choice:** Nudge every turn, board when not empty (recommended).

## Version banner

| Option | Description | Selected |
|--------|-------------|----------|
| plugin.yaml version plus integer API version | Stub constant compared to `/meta` | ✓ |
| Git hash | Needs a build step to embed | |

**User's choice:** plugin.yaml version plus integer API version (recommended).

Theo accepted all five recommendations in one reply ("sounds good").

## Claude's Discretion

See CONTEXT.md "Claude's Discretion".

## Deferred Ideas

See CONTEXT.md "Deferred Ideas".
