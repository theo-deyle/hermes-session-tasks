# Phase 3: REST router and client install spike - Context

**Gathered:** 2026-10-31
**Status:** Ready for planning

<domain>
## Phase Boundary

The pane's backend: a FastAPI router in `plugin/dashboard/plugin_api.py` under `/api/plugins/hermes-session-tasks/` with read, list, edit and meta routes. Every write, from a tool or a route, broadcasts `board.updated`. A stub pane in `plugin/desktop/plugin.js` installs on the Mac and on the Windows PC by a copy script, reads a board through `ctx.rest`, shows whether the event arrived, and shows a version banner. A `pre_llm_call` hook injects the live board and one nudge line each turn, so the agent puts its own steps on the board (routed from Phase 2, D-21). Requirements: API-01, API-02, API-03, DEV-03, DEV-05, AGNT-01 (own-plan half).

Not in this phase: the real pane (Phase 4), the `pre_llm_call` delta of Theo's edits and session delete (Phase 5), cross-session tools (Phase 6), formal rollout DEV-04 and DEV-06 (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Stale write over HTTP
- **D-22:** A stale write returns HTTP 200 with `{"ok": false, "error": "stale", "reason": ..., "op_index": ..., "rev": ..., "board": ...}`. The body carries the same content as the tool's stale result (D-14). Reason: Desktop turns any 4xx into a string error and may drop the body on the IPC hop (`apps/desktop/electron/api-transport.ts:183-190`). A `BoardError` (D-16) also returns 200 with `ok: false` and `error: "invalid"`, the op index and the rule. Transport faults (no session, bad JSON) keep their 4xx. - **Reversibility:** costly - the pane (Phase 4) reads this shape; a later switch to 409 changes every pane write.

### Route shape
- **D-23:** Four routes: `GET /board?session_id=`, `GET /boards`, `POST /board/edit`, `GET /meta`. `POST /board/edit` takes the same `ops` list and `base_rev` as `board_edit`, with `session_id` in the body, and returns `ok`, `rev` and the board as JSON. One write path through `BoardStore.apply` with `actor="user"`. No per-item routes.
- **D-24:** The D-18 guard does not apply to route writes. A route write is Theo's own edit, so no `confirmed` field exists on the route.
- **D-25:** The route takes `session_id` from the request, because the pane names the focused session. The resolver maps it to the board root the same way the tools do. The tool rule TOOL-06 (never from model arguments) is unchanged for tools.

### Desktop half install
- **D-26:** One PowerShell script `scripts/install-desktop.ps1`, run with pwsh 7 on the Mac and on the Windows PC. It copies `plugin/desktop/plugin.js` from devpc over the SSH link the Desktop already uses, to `$HERMES_HOME/desktop-plugins/hermes-session-tasks/plugin.js` on that machine. Desktop loads the disk copy within seconds; no install dialog, no Git credential on the Mac or the PC (`desktop-plugin-sdk.md:20, 68, 1766-1773`). The README gives the steps for each machine. - **Reversibility:** reversible - the file lands in the documented disk slot; a later Git install replaces the script, not the file.

### Own-plan nudge each turn
- **D-27:** A `pre_llm_call` hook adds one nudge line every turn ("Your steps go on the board: add them with board_edit before you start, check each one off when done"). When the board is not empty it also adds the current board with ids (D-04 form). Phase 5 narrows the board part to a delta of Theo's edits. Pass rule: 3 of 3 headless own-job runs, the agent writes its steps to the board and checks them off. The exact nudge wording is Claude's discretion; the planner records the measured wording.
- **D-28:** The hook never raises. On a store error it returns nothing and logs a warning.

### Version banner
- **D-29:** `plugin.yaml` `version` is the backend version. `desktop/plugin.js` carries the same string as a constant. `API_VERSION` is an integer that starts at 1 and bumps on any route or body change. `GET /meta` returns both. The stub shows a banner when its constant differs from either value. The two version strings move together on a release; a test fails when they drift.

### Claude's Discretion
- The `load_core` snippet in `plugin_api.py` (path-loaded, no relative imports), Pydantic request models, the `dashboard/manifest.json` with `tab.hidden`.
- Event payload fields beyond `session_id` and `rev` (for example `actor`), the stub's event indicator layout, and the poll interval fallback (5 to 10 s).
- The import allowlist test for `plugin.js` (regex over `import` lines, allows only `@hermes/plugin-sdk`, `react`, `react/jsx-runtime`), and the `node --check` test.
- The headless own-job harness, reused from the Phase 2 scratchpad run `live-gap-ownjob2`.
- How `GET /boards` lists sessions (root ids, revs, item counts) without reading `state.db` for titles; titles belong to Phase 6.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project (this repo)
- `.planning/phases/01-core-storage-and-session-identity/01-CONTEXT.md` - D-01 to D-10: ids, agent view line, caps, lineage.
- `.planning/phases/02-agent-tools-and-skill/02-CONTEXT.md` - D-11 to D-21: tool names, result shapes, guard, delegate rule, own plan on the board.
- `.planning/phases/02-agent-tools-and-skill/02-VERIFICATION.md` - the own-plan override and the 0 of 3 result that this phase fixes.
- `.planning/research/ARCHITECTURE.md` - `plugin_api.py` load rules, mount and auth, hot-mount and restart rules, event flow A and B.
- `.planning/research/STACK.md` - structured 200 rationale, `broadcast_plugin_event`, Desktop SDK exports, pane registration, `ctx.rest`.
- `.planning/research/PITFALLS.md` - Desktop event delivery, polling floor, import allowlist.
- `.planning/REQUIREMENTS.md` - API-01 to API-03, DEV-03, DEV-05, AGNT-01.
- `.planning/ROADMAP.md` - Phase 3 success criteria 0 to 5.

### Hermes source and docs (on devpc, `~/.hermes/hermes-agent`)
- `website/docs/developer-guide/desktop-plugin-sdk.md` - disk plugin path, `ctx.rest`, `ctx.onEvent`, pane registration, remote backend note (lines 1766-1773).
- `hermes_cli/web_server_dashboard.py` - manifest scan, router mount with prefix, auth dependency, hot-mount on first request.
- `hermes_cli/plugin_events.py` - `broadcast_plugin_event(name, event, payload)`.
- `website/docs/user-guide/features/hooks.md` - `pre_llm_call` return shape (`{"context": ...}`).
- `apps/desktop/electron/api-transport.ts` lines 183-190 - 4xx to string error.
- `~/.hermes/plugins/gsd-status-api/dashboard/manifest.json` - hidden tab manifest example.
- `~/.hermes/skills/hermes-desktop-plugins/templates/plugin.js` - pane template.

### House rules
- `~/.claude/skills/donmor-coding-practices/SKILL.md` and `python/*.md`.
- `~/.claude/CLAUDE.md` rule 14: every script for Theo is PowerShell 7.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `plugin/session_tasks/store.py` `BoardStore.get_board`, `BoardStore.apply(root_id, ops, actor=, base_rev=)` returning `Applied` or `Stale`.
- `plugin/session_tasks/edit_args.py` parses the `ops` list for `board_edit`; the route reuses it.
- `plugin/session_tasks/results.py` builds the tool result shapes; the route maps the same objects to JSON.
- `plugin/session_tasks/lineage.py` `SessionResolver.resolve` for the route's session id.
- `plugin/session_tasks/hooks.py` factory style (`make_pre_tool_call`, `make_post_compaction`); add `make_pre_llm_call` the same way.
- `plugin/session_tasks/wiring.py` `register` with a typed `ctx` protocol; add the new hook there.

### Established Patterns
- Core is stdlib only; Hermes imports lazy in thin adapters. `plugin_api.py` loads by path with no package, so it needs a `load_core` snippet (ARCHITECTURE.md "Shared code").
- One connection per operation, `BEGIN IMMEDIATE` per write, no module-level state.
- Plain `def` route handlers; `async def` with sqlite blocks the gateway.
- Tests run without a gateway: `FastAPI()` plus `include_router(router, prefix=...)` and `TestClient`.

### Integration Points
- `plugin/dashboard/manifest.json` and `plugin/dashboard/plugin_api.py` export `router`.
- An `events` adapter calls `broadcast_plugin_event` after commit from both the tool path and the route path; a publish failure never fails a write.
- `plugin.yaml` adds `pre_llm_call` to `provides_hooks`; `hermes plugins validate plugin/` must pass.
- Any edit to `plugin_api.py` needs a restart of every `hermes serve` process; announce it first.

</code_context>

<specifics>
## Specific Ideas

- Stale body example: `{"ok": false, "error": "stale", "reason": "item changed", "op_index": 1, "rev": 14, "board": {...}}`.
- Stub pane shows four lines: backend version and API version, own version with the banner on mismatch, last event `rev N at HH:MM:SS`, and the board as plain text.
- Live check on each machine: run the install script, open Desktop, focus a session with a board, make a tool write and a route write, see the event line change on both.

</specifics>

<deferred>
## Deferred Ideas

- `pre_llm_call` delta of Theo's edits with `agent_seen_rev` - Phase 5.
- Session titles in the board list - Phase 6 (`board_sessions`).
- Git install dialog for the Desktop half - Phase 7, if the copy script proves awkward.

</deferred>

---

*Phase: 03-rest-router-and-client-install-spike*
*Context gathered: 2026-10-31*
