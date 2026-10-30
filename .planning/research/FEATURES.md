# Feature Landscape

**Domain:** Per-session "things to remember" board for Hermes Desktop. The agent writes items. One human (Theo) edits them in a side pane.
**Researched:** 2026-10-30
**Overall confidence:** HIGH for the todo_list boundary and the Hermes plugin surface (read from source). MEDIUM for agent behaviour rules (design judgment, no in-repo precedent).

## Scope Check Against PROJECT.md

PROJECT.md already fixes most of v1. This file confirms it and makes five sharpenings:

1. Cut the agent tools from eight to four. Every tool schema rides in every request, and one `ops` tool covers add, update, check and remove.
2. Defer reorder, both in the pane and in the agent tools. Keep the `position` column so v2 needs no migration.
3. Show agent items with short numeric ids (`#3`). Plain `- [ ]` markdown has no handle the agent can address.
4. Put the "when to use the board" rules in the tool descriptions, not only in the skill. Plugin skills are not listed in the system prompt, so the agent never loads them by itself.
5. Show other sessions' boards read-only, with a copy action. Edits happen only on the focused session's board.

## The todo_list Boundary

Source: `/home/theo/.hermes/hermes-agent/tools/todo_tool.py` (`TODO_SCHEMA`, line 229; registration, line 333).

| Aspect | Built-in `todo_list` | This board |
|--------|----------------------|------------|
| Purpose, from its description | "Track a task list for multi-step work (3+ steps)", plus "when the user provides multiple tasks" | Items Theo must do, decide or remember |
| Owner | The agent. It writes, the agent verifies. | Theo. The agent writes on his behalf and asks before risky edits. |
| State | In memory on `AIAgent`, one per session (module docstring) | Persistent in plugin storage, survives restarts |
| Item shape | `{id, content, status, parent}`. Status is `pending`, `in_progress`, `completed` or `cancelled`. | `{id, text, checked, parent_id, position, timestamps, updated_by}` |
| Write model | Replace the whole list, or `merge: true` by id | Item-level operations only. No replace-all. |
| Human edit | None. The Desktop only renders it. | Add, edit, check, delete in the pane |
| Compression | Re-injected after compression (`format_for_injection`, active items only) | Keyed by lineage root, so it survives without injection |
| Limits | 256 items, 4000 chars per item (`MAX_TODO_ITEMS`, `MAX_TODO_CONTENT_CHARS`) | Copy the same caps, or lower the item cap to 100 |
| Rule | "Only ONE item in_progress at a time", "Mark completed only after the work is verified" | No in-progress state. Checked or not. |

**Overlap risk.** The `todo_list` description says "or when the user provides multiple tasks". That sentence also fits this board. Our tool descriptions must say: "Theo's own remember list. Never use it for your own plan. Use `todo_list` for your plan." The model picks tools from descriptions, so the boundary lives there.

**Verbs the agent must never use on `todo_list`:** read, write, wrap, replace. PROJECT.md already forbids it. This file adds one reuse: copy the `format_for_injection` idea (inject only active items, as a short block) for the "Theo edited the board" injection.

## Table Stakes

Missing any of these and the core value fails: items the agent lists for Theo stay visible and editable for the whole session.

### Pieces to build (PROJECT.md list, confirmed)

| Piece | v1 verdict | Minimum shape | Complexity | Depends on |
|-------|-----------|---------------|------------|------------|
| Board model | Table stakes | Item: id, text, checked, parent_id, position, created_at, updated_at, updated_by (`agent` or `user`). Board: revision integer, bumped on every write. Integer ids per board, never reused. Cap items and text length. | Medium | Storage |
| Storage | Table stakes | SQLite at `plugin_db("hermes-session-tasks")`. It lives under `$HERMES_HOME/plugin-data/`, survives `hermes plugins update` and `remove` (`plugins/index.md` "Store durable state", source `plugins/plugin_storage.py`). One row per item, one row per board. Never `state.db`. | Low | None |
| Session key and lineage | Table stakes | Key every board by the durable lineage root id. The pane already gets this id as `host.state.focusedStoredSessionId`. The tool handler gets a live `session_id` and must map it to the root. | Medium to High | Storage. No documented plugin API gives the root: see Gaps |
| Agent tools | Table stakes | Four tools (see "Agent tool surface" below). Each write returns the board. | Medium | Board model, session key |
| Bundled skill | Table stakes, but secondary | Short `SKILL.md` carrying the seven rules below. Register with `ctx.register_skill`. The tool descriptions carry the core rules. | Low | Agent tools |
| Pane | Table stakes | Right-side pane, checkbox list, inline add, inline edit, add subtask, delete, collapse, session picker, copy as markdown, live update. | High | REST routes, board model |
| Live update | Table stakes | `broadcast_plugin_event("hermes-session-tasks", "board.updated", {session_id, revision})` from tool handlers and REST writes. Pane listens with `host.onEvent` and also polls with `useQuery`. | Medium | Pane, REST routes |
| Agent sees Theo's edits | Table stakes | `pre_llm_call` hook injects one short block, only when Theo changed the board since the agent last saw it. See "Agent sees Theo's edits". | Medium | Board model, change log |
| Safe concurrent writes | Table stakes | Item-level operations plus a board revision. Stale write on an item that moved returns an error with the current board. | Medium | Board model |
| Session delete | Table stakes | `on_session_delete` hook removes the board. Hook exists (`plugins/index.md` line 1524). Decide archive vs delete in discuss: recommend delete, because the board has no value without its session. | Low | Storage |

### Subtask depth: one level

**Recommendation: one level.** An item may have subtasks. A subtask may not have subtasks.

Reasons:
- The pane sits at about 260 - 320 px wide on the right. Two indents already cost a quarter of the width. Three do not fit.
- A remember list for one human rarely needs a tree. `todo_list` allows unlimited nesting through `parent`, and that fits an agent plan, not a reminder list.
- The agent tool stays simple: `parent_id` is valid only when the target is a top-level item. The tool rejects anything else with a plain message.
- Markdown stays unambiguous: `- [ ]` at column 0, `  - [ ]` at two spaces.

UI implications:
- Chevron on every item that has subtasks. Collapse state lives in `ctx.storage`, per session, per item.
- "Add subtask" shows only on top-level items.
- The parent shows a count, for example `2/3`. Checking a parent does not auto-check its subtasks. Checking all subtasks does not auto-check the parent. Auto-cascade surprises Theo and the agent.
- Delete on an item with subtasks asks for confirmation (`ConfirmDialog`) and says how many subtasks go with it.

Markdown implications:
- Export writes two-space indent, one level.
- Import clamps deeper indent to level 2 and reports how many lines it flattened.
- The data model keeps `parent_id`, so v2 can lift the cap with no migration.

### Agent tool surface

Four tools. Names are decided in discuss. Use one shared prefix and avoid the word "todo". Suggested: `session_board_read`, `session_board_edit`, `session_board_sessions`, `session_board_copy`.

| Tool | Purpose | Notes |
|------|---------|-------|
| read | Read this board, or another session's board with `session_id` | Covers cross-session read. Returns agent-view markdown plus revision. |
| edit | Apply a list of operations: add, rename, check, uncheck, remove | One call, many operations. Item-level. No replace-all. |
| sessions | List sessions that have a board | Returns id, label, open count, total count, last update. |
| copy | Copy chosen items (or all open items) from another session's board into this one | Items never pass through the model, so copy is exact and cheap. |

Why four, not eight: Hermes sends every tool schema on every request. todo_list sets the pattern: one tool, read by omission, always returns the full list. A merged `edit` tool is the same shape.

The tool must take the current session from the `session_id` keyword Hermes passes. It must never take it from model arguments (PROJECT.md rule).

### Agent-facing output: confirm the full-board contract, with three additions

**Confirmed: each write returns the full board as markdown.** Reasons: boards are small (cap about 100 items, about 600 tokens at 50 items). The agent never has to hold state or replay a diff. `todo_list` does the same ("Always returns the full current list").

Three additions make it work:

1. **Ids in the agent view.** Plain `- [ ] text` gives the agent no way to name an item. Render the agent view as `- [ ] #3 Call the vendor`. Export for humans (copy button, import) stays plain. Same renderer, one flag.
2. **Revision and change line.** Return a header `Board rev 12` and one line such as `Added #7. Checked #2.` The change line is a summary, not a diff the agent must apply.
3. **Errors return the board.** A rejected stale write returns the error and the current board, so the agent retries without an extra read.

A pure diff plus revision is the wrong contract here. A diff forces the agent to keep a copy and apply patches. One missed diff and the agent works from a wrong list. Full board plus a change line costs a few hundred tokens and removes that failure.

If a board ever grows past the cap threshold for readability (say 40 items), render checked items as a count line, not in full. Defer this until a real board needs it.

### Agent sees Theo's edits

- Hook: `pre_llm_call` returns `{"context": "..."}`. This text joins the current user message, not the system prompt, so prompt caching holds.
- Send nothing when the agent already saw the latest revision. Track `agent_seen_revision` per board. Reads and writes by the agent update it.
- When Theo changed the board: inject up to 10 lines, for example `Theo changed your board (rev 9 to 12): checked #2; added #7 "Renew cert"; removed #4.` If more than 10 changes, send `Theo changed the board a lot. Call session_board_read.`
- This needs a small change log (last N user operations per board). That log is the cost of the feature.

### Agent behaviour: rules for the bundled skill

Seven rules. Each one sentence. Put rules 1 and 2 also in the tool descriptions.

1. Add an item to the board when you list something Theo must do, decide or remember, one short line per item.
2. Keep your own working plan in `todo_list`, never on the board.
3. When Theo asks you to add, change, check or remove an item, do it at once and confirm in one line.
4. When your work finishes an item, check it and say so in one line.
5. Ask Theo one plain question before you delete an item, reword an item Theo wrote or edited, uncheck an item, or change more than five items at once.
6. When you are unsure which item Theo means, or whether he wants a change, ask and do not guess.
7. Read another session's board or copy its items only when Theo asks, and name that session in your reply.

Confirmation wording:
- Past tense, one line, verb first, item text in quotes for up to three items. Example: `Added to your board: "Renew cert", "Call vendor", and 2 more.`
- Do not paste the board into chat. The pane shows it.
- An ask names the item and the effect. Example: `Remove #4 "Call vendor" from your board? It is not checked.`

Ask first, always: delete, reword a Theo item, uncheck, bulk change over five, ambiguous match.
Never ask first: add, check an item your work just finished, answer a direct request from Theo.

### Pane interactions

| Interaction | v1 | Complexity | Notes |
|-------------|----|-----------|-------|
| Check and uncheck | Yes | Low | SDK `Checkbox`. Optimistic update, then reconcile on revision. |
| Add item (inline) | Yes | Low | Input at the bottom. Enter adds. Stays focused for the next item. |
| Inline edit | Yes | Low | Click text. Enter saves. Esc cancels. |
| Add subtask | Yes | Low | Context menu and hover button on top-level items only. |
| Delete | Yes | Low | `ContextMenu` and hover icon. Confirm only when subtasks go with it. |
| Collapse subtasks | Yes | Low | State in `ctx.storage`. |
| Empty state | Yes | Low | SDK `EmptyState`. One line that says the agent adds items here. |
| Session picker | Yes | Medium | See "Cross-session". |
| Copy as markdown | Yes | Low | `ctx.os.writeClipboard`. Plain export, no ids. |
| Live update | Yes | Medium | Event plus polling fallback. `ctx.socket` is a no-op on OAuth remotes. |
| Reorder (drag or move up/down) | Slip to v2 | Medium (drag), Low (menu) | The SDK has no drag helper. Order is append order in v1. The `position` column is already there. |
| Import markdown | Slip to v2 | Medium | Needs a parser, a paste dialog and the depth clamp. Theo can paste a list into chat and the agent adds it. |
| Show open count in header | Cheap, include | Low | Part of the picker label. |

## Differentiators

Valued, not required. Each can slip without hurting the core value.

| Feature | Value | Complexity | Notes |
|---------|-------|-----------|-------|
| Agent-changed marker on items | Theo sees at a glance what the agent added or checked. Uses `updated_by`. | Low | Small dot or "agent" label. Data already exists. |
| Import markdown | Round-trip with the copy button | Medium | First v2 candidate. |
| Reorder in pane | Priority by position | Medium | v2. Add agent reorder only with it. |
| Edit another session's board in place | Tick off old items without switching | Low | Same REST. Risk: confusion about which board the agent writes to. |
| Open the other session from the picker | Jump to the conversation that produced the item | Low | `host.openSession(id)`. |
| Palette command and keybind | Add an item without the mouse | Low | `PALETTE_AREA`. |
| Status-bar chip with open count | Visible when the pane is closed or stacked behind another tab | Low | `STATUSBAR_AREAS.right`. Likely wanted soon, because the pane stacks as a tab with other right-side panes. |
| Undo toast on delete | Safer than a confirm dialog | Medium | Needs soft delete. |
| Per-item note or link | Context for a reminder | Medium | Not needed while items are one line. |

## Cross-session

Minimum v1: view, copy. No edit of other boards.

| Capability | Shape |
|------------|-------|
| Pane picker | A `Select` at the top. Default is the focused session. Lists sessions that have a board, plus the focused session even when its board is empty. |
| Other board view | Read-only. A banner says "Viewing <title>". Per item: "Copy to this board". Header: "Copy all open items". |
| Agent read | `session_board_read(session_id)`. |
| Agent copy | `session_board_copy(from_session_id, item_ids?)`. Default is all open items. |
| Agent list | `session_board_sessions()`. |

What the picker shows per session: **title, open count over total, last activity.**

- **Last activity:** use the board's own `updated_at`. Reason: `session.list` rows do not carry a last-active field. They are ordered by last activity, but the row has only `started_at`.
- **Counts:** from the board.
- **Title:** from Hermes. Source of truth is the `sessions.title` column, written by `hermes_state_titles.py` (`set_session_title`, `get_session_title`). Titles come from the user (`/title`) or from auto-titling, and can be empty. A compressed lineage uses numbered titles (`my session #2`).
- **How the pane gets it:** call `host.request('session.list', {limit: 200})`. Each row has `id`, `title`, `preview`, `started_at`, `message_count` and `_lineage_root_id` (`tui_gateway/methods_session.py`, `_session_row_summary`). Join on `_lineage_root_id ?? id`. Show `title`, fall back to `preview` (first user message), fall back to "Untitled session". This uses only the documented host door. Do not import `hermes_state` from the plugin: internal import paths are not part of the plugin contract (`plugins/index.md`, "Sep 2026 module decomposition").
- **Agent side has no documented title lookup.** See Gaps. Interim: the `sessions` tool returns id, open count, total, last update and the first open item as a hint.

## Anti-Features

| Anti-Feature | Why avoid | What to do instead |
|--------------|-----------|--------------------|
| Global or project board shared by all sessions | Doubles the model: scope picker, merge rules, ownership. Parked in PROJECT.md for v2. | Cross-session copy covers the need for now. |
| Due dates, reminders, notifications | Theo said "remember list", not a scheduler. Adds time zones and a notifier. | Put the date in the item text. |
| Priorities, assignees, labels, tags | Single human, short list. Position carries order if reorder ships. | None. |
| In-progress or cancelled states | These belong to the agent's plan. A checkbox has two states. | Delete or leave unchecked. |
| Sync to Super Productivity or GitHub | Out of scope in PROJECT.md. Adds auth and conflict handling. | Copy as markdown. |
| Reading, writing, wrapping or replacing `todo_list` | Breaks the boundary and the Hermes "no core override" rule. | Separate tools, separate storage. |
| Agent using the board as scratch plan | Floods Theo's list with agent steps. It defeats the core value. | Rule 2 in the skill and the tool descriptions. |
| Replace-all write in the agent tools | One bad call wipes Theo's edits. `todo_list` has this and it suits an agent plan, not a human list. | Item-level operations only. |
| Auto-check parent from subtasks, or the reverse | Surprise state changes for both writers. | Show a count. |
| Unlimited nesting | Does not fit the pane width. | One level. |
| Storing board data in `state.db` or injecting the whole board every turn | Touches core data. Breaks prompt caching and wastes tokens. | Plugin storage. Inject only Theo's changes. |
| A settings page in v1 | No setting is needed yet. | Add one when a real setting appears. |
| Robot-readable rich markdown (tables, links, HTML) in item text | Parsing, rendering and security cost. Items are one line of plain text. | Plain text. Render it as text, never as HTML. |

## Feature Dependencies

```
Storage -> Board model -> Session key (lineage root)
Board model -> Agent tools (read, edit, sessions, copy)
Board model -> REST routes -> Pane (list, check, add, edit, delete, collapse)
REST routes + Agent tools -> board.updated event -> Pane live update
Board model + change log -> pre_llm_call injection (agent sees Theo's edits)
Agent tools -> Bundled skill (tool descriptions come first, skill second)
Session picker -> session.list join (title) + sessions endpoint (boards with counts)
Session picker -> Other board view -> Copy items (pane) and session_board_copy (agent)
Copy as markdown -> markdown renderer (shared with the agent view)
Import markdown (v2) -> markdown parser + paste dialog
Reorder (v2) -> position column (already in model) -> pane move controls -> agent reorder op
Session delete hook -> Storage
```

## MVP Recommendation

Build in this order:

1. Storage, board model, session key with lineage. Test lineage first: it is the riskiest piece.
2. REST routes and the pane for the focused session: list, check, add, inline edit, subtask, delete, collapse, empty state, copy markdown.
3. Agent tools (read, edit) with the full-board return, plus tool descriptions that carry the boundary. Then the bundled skill.
4. Live update (event plus polling fallback), then `pre_llm_call` injection of Theo's edits.
5. Cross-session: sessions list, picker, read-only view, copy (pane and agent).
6. Session delete hook and revision-conflict handling polish.

Defer to v2: reorder, import markdown, edit other boards in place, status-bar chip, undo toast, global board.

## Gaps and Open Questions

- **Lineage mapping.** No documented plugin API turns a live `session_id` into the lineage root. `hermes_state_sessions.py` has `_session_lineage_root_to_tip` (private) and rows carry `_lineage_root_id`. The ARCHITECTURE pass must pick a supported route or accept a private-API risk. A board that splits after compression breaks the core value.
- **Session title on the agent side.** The plugin has no documented title lookup. The pane can join through `session.list`. The `sessions` tool cannot, without a private import. Options for later: store a label on the board at first write, or accept ids only.
- **Skills are opt-in.** Plugin skills are not in the system prompt's `<available_skills>` (`plugins/index.md`, "Bundle skills"). The agent only loads one if told. Tool descriptions must therefore carry the boundary and rules 1 and 2.
- **Tool Search.** If Theo ever enables `tools.tool_search`, non-core plugin tools can be deferred behind a search step (`user-guide/features/tool-search.md`). The current `~/.hermes/config.yaml` has no entry, so tools load eagerly. Verify at deploy.
- **Desktop half on a remote backend.** Theo runs Desktop on Mac and Windows against devpc. The docs say the unified-package copy is local to the Desktop machine, and a remote backend shows the Desktop half as "unavailable (remote backend)" until it is installed on each Desktop (`desktop-plugin-sdk.md`, "Developing a unified package"). PROJECT.md deploys by symlink on devpc only. Check this before the pane phase. Not a feature, but it blocks the pane.
- **Agent reorder tool.** PROJECT.md lists it. This file defers it. Confirm in discuss.
- **Item cap.** 100 versus the `todo_list` cap of 256. Pick in discuss. Lower is better for the full-board return.

## Sources

- `/home/theo/.hermes/hermes-agent/tools/todo_tool.py` - `TODO_SCHEMA`, `TodoStore`, `format_for_injection`, registration (HIGH)
- `/home/theo/.hermes/hermes-agent/apps/desktop/src/lib/todos.ts` - Desktop todo item shape (HIGH)
- `/home/theo/.hermes/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md` - panes, host state, UI kit, `broadcast_plugin_event`, unified package, pitfalls (HIGH)
- `/home/theo/.hermes/hermes-agent/website/docs/developer-guide/plugins/index.md` - tools, hooks (`pre_llm_call`, `on_session_delete`), durable state, bundled skills (HIGH)
- `/home/theo/.hermes/hermes-agent/website/docs/user-guide/features/tool-search.md` - tool deferral (HIGH)
- `/home/theo/.hermes/hermes-agent/tui_gateway/methods_session.py` - `session.list` row shape (HIGH)
- `/home/theo/.hermes/hermes-agent/hermes_state_titles.py` - session title storage and provenance (HIGH)
- `/home/theo/.hermes/plugins/hermes-memory-ui/desktop/plugin.js` - existing plugin as a full page, not a pane; shows `EmptyState`, `useQuery`, `useMutation` usage (MEDIUM, different surface)
- Agent behaviour rules and the tool-count recommendation: design judgment from the sources above (MEDIUM)
