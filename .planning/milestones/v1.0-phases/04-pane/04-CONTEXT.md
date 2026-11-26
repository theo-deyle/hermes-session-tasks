# Phase 4: Pane - Context

**Gathered:** 2026-11-01
**Status:** Ready for planning

<domain>
## Phase Boundary

The real Desktop pane: the focused session's board on the right side, with checkboxes, two-level subtasks, inline add, inline edit, subtask add, delete with a confirm when subtasks go too, live update through the board.updated event with a poll fallback, copy as markdown, and an empty state. Requirements PANE-01 to PANE-08 and PANE-11 to PANE-13. The session picker and cross-session copy (PANE-09, PANE-10) are Phase 6. The agent's view of Theo's edits is Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Add an item
- **D-30:** One empty "Add an item" line always sits at the bottom of the list. Enter saves the text and keeps the cursor in a fresh empty line. Escape clears the line. A "+" shows on hover of a top-level item and opens the same kind of line under it for a subtask (two levels, D-01).

### Edit the text
- **D-31:** Click the item text to edit it in place. Enter saves, Escape cancels, a click elsewhere saves. The checkbox stays clickable while the text is in edit mode.

### Delete
- **D-32:** A trash icon shows on row hover. An item with no subtasks is deleted at once. An item with subtasks opens the SDK ConfirmDialog that names the count ("Delete this item and its 3 subtasks?"). No undo toast in this phase (PANE-16 is v2).

### Checked items
- **D-33:** A checked item stays in place with struck-through text and a muted colour. It does not move and does not hide. The pane header shows "N of M open".

### Stale write
- **D-34:** The pane shows a change at once (optimistic) and sends the write with `base_rev`. On a stale reply (D-22 shape) the pane takes the returned board. A check or uncheck is retried once on the new revision with the same op. An add or a text edit is not retried: the pane shows the new board and keeps the typed text in the input so Theo can press Enter again. A one-line notice "Board changed, showing the latest" shows for a few seconds. - **Reversibility:** reversible - pane-local behaviour.

### Claude's Discretion
- Collapse state of subtasks lives in the pane only (default expanded, not stored).
- Poll interval 5 to 10 s; `host.onEvent('plugin.hermes-session-tasks.board.updated', ...)` is the primary signal.
- Copy-to-clipboard button in the header; the markdown carries no ids (D-05).
- Empty state wording: "The agent adds items here. Add one below."
- Pane registration keeps the Phase 3 dock gesture (`placement: 'right'`, `dock: { pane: 'workspace', pos: 'right' }`, `width: '320px'`).
- The node VM pane tests from Phase 3 (`tests/desktop_pane_harness.mjs`, `tests/test_desktop_plugin.py`) extend to the real pane: import allowlist, no hardcoded colour, every edit path through the real routes.
- No separate UI design contract: PANE-13 fixes the SDK components and the `var(--ui-*)` theme variables, and `~/.hermes/plugins/hermes-memory-ui/desktop/plugin.js` is the working reference.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and prior decisions
- `.planning/REQUIREMENTS.md` - PANE-01 to PANE-13 wording
- `.planning/phases/01-core-storage-and-session-identity/01-CONTEXT.md` - D-01 two-level depth, D-03 item ids, D-05 export without ids, D-10 caps
- `.planning/phases/03-rest-router-and-client-install-spike/03-CONTEXT.md` - D-22 stale reply shape, D-23 route shape, D-26 install, D-29 version banner
- `.planning/phases/03-rest-router-and-client-install-spike/03-09-SUMMARY.md` - the dock placement fix and the live Mac result

### Desktop SDK
- `~/.hermes/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md` - pane registration, UI kit exports, `ctx.rest`, `host.onEvent`, hot reload
- `~/.hermes/hermes-agent/apps/desktop/src/sdk/index.ts` - the export list (Checkbox, Input, ScrollArea, ConfirmDialog, CopyButton, EmptyState, icons, cn)
- `~/.hermes/plugins/hermes-memory-ui/desktop/plugin.js` - working reference for jsx() without a build step

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `plugin/desktop/plugin.js` (test pane, 196 lines): `ctx.rest` calls to `/meta`, `/board`, `/board/edit`, the `useValue(host.state.focusedStoredSessionId)` focus read, the event listener and poll loop, the version mismatch banner. The real pane replaces its body and keeps these pieces.
- `plugin/dashboard/plugin_api.py`: `GET /board?session_id=`, `POST /board/edit` (ops list, `base_rev`, 200 with `ok: false, error: stale` and the board), `GET /meta`.
- `tests/desktop_pane_harness.mjs` and `tests/test_desktop_plugin.py`: node VM harness that loads plugin.js with a fake SDK and real routes through `tests/rest_relay.py`.

### Established Patterns
- One plain ESM file, three imports, `jsx()`/`jsxs()`, `var(--ui-*)` only, `ctx.setTimeout`/`ctx.onDispose` for anything that outlives a render.
- Every write goes through one ops route; the pane never addresses an item by anything but its integer id.

### Integration Points
- `host.onEvent('plugin.hermes-session-tasks.board.updated')` payload: `session_id`, `rev`, `actor`.
- Focus change: `host.state.focusedStoredSessionId` is the gateway session key the routes accept.

</code_context>

<specifics>
## Specific Ideas

Theo accepted the five recommendations as stated ("sounds good"). No reference app named.

</specifics>

<deferred>
## Deferred Ideas

- Clear all done items in one action - new capability, backlog.
- Undo toast on delete - PANE-16, v2.

</deferred>

---

*Phase: 04-Pane*
*Context gathered: 2026-11-01*
