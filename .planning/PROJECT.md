# hermes-session-tasks

## What This Is

A Hermes Desktop plugin that gives each Hermes session a task board in a Desktop side pane. The agent writes items to the board when it lists things to do or remember. Theo adds, edits, checks off and deletes items in the pane. The board is the shared plan of the session: Theo's reminders and the agent's own steps.

## Core Value

Items the agent lists for Theo and the agent's own steps stay visible and editable in the pane for the whole session, so Theo never scrolls up, never asks the agent to repeat itself, and sees what comes next.

## Requirements

### Validated

- ✓ A board follows its session through context compression and branches. - Phase 1
- ✓ Writes are safe when the agent and the pane write at the same time (revision number, reject stale writes). - Phase 1
- ✓ Board data lives on devpc under `$HERMES_HOME` in plugin-owned storage, never in `state.db`. - Phase 1
- ✓ The pane updates live when the agent writes to the board. - Phase 3 (REST routes, `board.updated` event, stub pane proved on the Mac and the Windows PC)
- ✓ The agent writes items to the board when it lists things to do or remember for Theo. - v1.0
- ✓ Theo can add, edit, check off and delete items in the pane. - v1.0
- ✓ Items are checkboxes. An item can have subtasks (depth decided in discuss). - v1.0
- ✓ The agent changes the board when Theo asks, or when the work makes an item done or wrong. - v1.0
- ✓ When the agent is not sure a change is wanted, it asks Theo first and does not guess. - v1.0
- ✓ Each session has its own board. - v1.0
- ✓ Theo can view another session's board from a session picker in the pane. - v1.0
- ✓ On request, the agent can read or copy items from another session's board. - v1.0
- ✓ Markdown checklists (`- [ ]`, `- [x]`, indented subtasks) are the text format for import, export and what the agent sees. - v1.0
- ✓ The pane renders the list as an interactive board, not as raw markdown. - v1.0
- ✓ The agent sees Theo's own edits to the board on its next turn, with small injected context. - v1.0
- ✓ Every Hermes host and every Desktop installs from the public repo `theo-deyle/hermes-session-tasks`; an update goes through `hermes plugins update` on each machine. - v1.0
- ✓ The plugin reads sessions through the Hermes storage interface on Hermes v0.24 and later, and through `SessionDB` on an older Hermes. - v1.0 (version 0.2.1)

### Active

None yet. The next milestone defines them. Two ideas wait in `.planning/todos/pending/`: a master list with tasks shared across sessions, and configurable checkbox states.

### Out of Scope

- A global or project board shared by all sessions - parked as a backlog idea for v2.
- Due dates, priorities, assignees - not needed for a remember list.
- Sync to Super Productivity or GitHub - not needed in v1.
- Changes to the Hermes Agent source tree - everything ships as a plugin.
- Reading, writing, wrapping or replacing the built-in `todo_list` tool - the board holds the agent's plan, and the plugin never uses `todo_list`.

## Context

**Who and where.** Theo runs Hermes Desktop on his Mac and Windows PCs. Each Desktop connects to the Hermes gateway on devpc (DM-TheoDevPC, Debian 12) over an SSH remote. The gateway, the agent and all data live on devpc. Desktop never runs on devpc.

**Problem.** In long Desktop sessions the agent lists what needs doing. Those items scroll away. Theo then scrolls up or asks the agent to repeat itself.

**Hermes plugin model.** One "unified package" folder carries both halves. Reference docs (verified on devpc, Hermes Agent source at `~/.hermes/hermes-agent`):

- `~/.hermes/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md` (sections "A backend for your plugin", "One package, both SDKs", "Pushing events to your desktop half", "Pitfalls")
- `~/.hermes/hermes-agent/website/docs/developer-guide/plugins/index.md` (tools, hooks, slash commands, bundled skills)

Package layout:

```
~/.hermes/plugins/hermes-session-tasks/   # symlink to this repo's package dir
├── plugin.yaml          # agent half: tools, hooks, skill
├── __init__.py          # register(ctx): ctx.register_tool, ctx.register_hook, ctx.register_skill
├── dashboard/
│   ├── manifest.json    # { "name": "hermes-session-tasks", "api": "plugin_api.py" }
│   └── plugin_api.py    # FastAPI APIRouter, mounted at /api/plugins/hermes-session-tasks/
└── desktop/
    └── plugin.js        # Desktop pane, one plain ESM file
```

**Python half facts.**

- Loads only when the id is in `plugins.enabled` in `~/.hermes/config.yaml`. Set it with `hermes config set` or `hermes plugins enable`, never by hand edit.
- Tool handlers can declare `session_id` as a keyword and Hermes passes the calling session. Use that to key the board. Never trust a session id from the model's arguments for the current session.
- The brief said the gateway runs Python 3.11 (`~/.hermes/hermes-agent/venv`). Research found the live Desktop SSH gateways run Python 3.14.9 from `~/.hermes/tools/`. Plugin code must work on 3.11 and 3.14 and import only the standard library plus what the gateway already ships (fastapi, pydantic).
- Backend routes mount only when `hermes serve` starts. A Desktop reconnect reuses the old gateway, so new routes need a gateway restart.
- `hermes_cli.plugin_events.broadcast_plugin_event("hermes-session-tasks", "board.updated", {...})` pushes `plugin.hermes-session-tasks.board.updated` to every connected Desktop window. Call it from the tool handler and from REST writes so the pane updates live.
- `pre_llm_call` hooks can return `{"context": "..."}` to add text to the current turn. Use this (or an equivalent the research finds) so the agent sees Theo's own edits. Keep the injected text small and only send it when needed, so token cost and prompt caching stay sane.
- Context compression starts a child session with a parent session id. A board must follow its session through compression and branches. Research how the session lineage is exposed (`hermes_state` session parent ids) and decide in discuss-phase.
- Hermes core keeps a hard rule: never change past context or the system prompt mid-conversation (prompt caching).
- `on_session_delete` hook exists. Data lifecycle on session delete is decided in discuss.

**Desktop half facts.**

- Plain ESM, no build, no JSX syntax: use `jsx()`/`jsxs()` from `react/jsx-runtime`. Import only `@hermes/plugin-sdk`, `react`, `react/jsx-runtime`. Verify every SDK name against the SDK doc before use.
- Use SDK UI components (`Checkbox`, `Input`, `Button`, `ScrollArea`, `EmptyState`, `Select*`, `DropdownMenu*`, `ContextMenu*`) and theme vars (`var(--ui-*)`), never hardcoded colours. Dark theme only matters.
- Follow the focused chat with `host.state.focusedStoredSessionId` (durable id). Use `ctx.rest` for reads and writes. Use `host.onEvent` for the broadcast event and a React Query `useQuery` polling fallback. `ctx.socket` is a no-op on OAuth remotes, so do not depend on it.
- Default pane position: the right side, stacked with the other right-side panes (`placement: 'right'`). Theo can drag it later.

**Pieces to build.**

- Board per session: items with id, text, checked state, parent id (one or more subtask levels, decide depth in discuss), order, timestamps, and who made the last change (agent or Theo).
- Agent tools (names decided in discuss; must not collide with `todo_list`): read the current board, add items, update/check/uncheck/rename items, remove items, reorder, read another session's board, copy items from another session, list sessions that have a board. Each write returns the full board as markdown.
- A bundled skill that tells the agent when to use the board: when it lists things to do or remember for Theo, keep the board in sync, ask before an ambiguous change, put its own multi-step plan on the board and check items off.
- Pane: shows the focused session's board, checkboxes, inline add and edit, add subtask, delete, collapse subtasks, a session picker to view other boards, import and copy as markdown. Live update when the agent writes.
- Storage on devpc under `$HERMES_HOME` (resolve with `get_hermes_home()`), in a plugin-owned SQLite file or JSON files. Never write into `state.db`.

## Constraints

- **Tech stack**: uv for the dev environment, ruff, pyright, pytest - house Python tooling.
- **Runtime**: the Desktop SSH gateways on devpc run Python 3.14.9 (verified 2026-10-30, `~/.hermes/tools/python-3.14.9+20261021-linux-x64`); the `~/.hermes/hermes-agent/venv` is Python 3.11.16. Plugin code must run and be tested on both 3.11 and 3.14, and import only the standard library plus fastapi and pydantic.
- **Desktop**: plain ESM, no build step, SDK imports only - Hermes Desktop loads one plain file.
- **Structure**: small modules with one responsibility each, structure planned first - house coding rule.
- **Secrets**: none needed; if one is ever needed it comes from Infisical - house rule.
- **Docs**: plain language, no em dash or en dash anywhere, spaced hyphen instead - house rule.
- **Commit identity**: Theo Deyle <theo.deyle@donmor.ca>.
- **Repo**: GSD project in this repo. The public repo `theo-deyle/hermes-session-tasks` (remote `public`, MIT) is the install source for every Hermes host and every Desktop. The org repo `Don-Mor-Software-Group/hermes-session-tasks` (remote `origin`, private) takes changes only through a pull request.
- **Deploy**: every host, devpc too, holds an installed copy from the public repo (`hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable`). An update is: push to `public`, then `hermes plugins update hermes-session-tasks` on each machine that has its own Hermes. Desktop copies the pane from the Hermes on its own machine. A pane-only change needs no gateway restart. Announce a gateway restart before it happens: it drops live Desktop connections.
- **Hermes versions**: Hermes Agent v0.22.5 or later. Hermes removes `hermes_state` no earlier than v0.27.0; the plugin already uses the storage interface when Hermes has it.
- **Boundary**: never read, write, wrap or replace `todo_list`.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate from the built-in `todo_list` tool | The board holds both Theo's reminders and the agent's own steps; `todo_list` is simply not used | - Pending |
| One board per session, session picker, cross-session read and copy tools; no global board in v1 | Keeps v1 small; global board parked as backlog | - Pending |
| Default pane position right, stacked with other right-side panes | Matches the other right-side panes; Theo can drag it later | - Pending |
| Markdown checklist is the text format for import, export and agent view | Readable by agent and human, round-trips cleanly | ✓ Phase 1: hand-written parser, 500 random boards round trip with no loss |
| Plugin-owned storage under `$HERMES_HOME`, never `state.db` | Keeps Hermes core data untouched | ✓ Phase 1: SQLite through `plugin_db`, contract test proves `state.db` bytes unchanged |
| Agent asks before an ambiguous board change | Theo's list; a wrong guess costs trust | - Pending |
| Session lineage through an alias table filled by the compaction hook, with a lazy `SessionDB` read-only walk as fallback | One resolve rule for plain, compression, branch and delegate sessions; a delegate reads its delegator root | ✓ Phase 1: 20-hop loop guard, branch copy once under a race |
| Stale write returns the current board instead of an error | The caller merges and retries; no lost update across processes | ✓ Phase 1: per-item revision rule, 4-process race test |
| The REST routes take `session_id` from the request and refuse any extra body field; a stale route write answers HTTP 200 with `ok: false` and the current board | The pane names the focused session; a `confirmed` flag never crosses REST; Desktop turns 4xx into an opaque error string | ✓ Phase 3: D-24, D-25, live on both machines |
| The Desktop half installs by a PowerShell script over the Desktop's own SSH link, with a host guard, an atomic copy and a SHA-256 line | A disk plugin loads uncompiled; the hash lets Theo compare with devpc in one line | ✓ Phase 3: Mac (`devbox`) and Windows PC (`devpc-ts`, home `%LOCALAPPDATA%\hermes`) |
| No messaging gateway restart inside Phase 3; the Desktop backends restart by Theo quitting and reopening Desktop after an announcement | Claude stops no process; the schema did not change, so the gateway's older code stays safe | ✓ Phase 3: two announced restarts, `ps` checked each time |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? Move to Out of Scope with reason
2. Requirements validated? Move to Validated with phase reference
3. New requirements emerged? Add to Active
4. Decisions to log? Add to Key Decisions
5. "What This Is" still accurate? Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-02 after Phase 3*
