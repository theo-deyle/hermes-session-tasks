# hermes-session-tasks: a per-session task board in Hermes Desktop

Brief for Claude Code. Plan this project with GSD before you write code.

## Goal

Theo works with the Hermes agent in long Desktop sessions. When the agent lists
what needs to be done, those items scroll away. Theo then has to scroll up or ask
the agent to repeat itself.

This plugin gives each session a task board in a Desktop side pane:

1. The agent writes items to the board when it lists things to do or remember.
2. Theo can also add, edit, check off, and delete items in the pane.
3. Items are checkboxes. An item can have subtasks.
4. The agent changes the board when Theo asks, or when the work makes an item
   done or wrong. When the agent is not sure whether a change is wanted, it must
   ask Theo first and not guess.
5. Each session has its own board. Theo can view another session's board from a
   picker in the pane. On request, the agent can read or copy items from another
   session's board.

Markdown checklists (`- [ ]`, `- [x]`, indented subtasks) are the text format
for import, export, and what the agent sees. The pane renders the list as an
interactive board, not as raw markdown.

## Decisions already made by Theo

- Separate from the built-in Hermes `todo_list` tool. `todo_list` stays the
  agent's own working plan for multi-step work. This board is Theo's list of
  things to remember. Do not read, write, wrap, or replace `todo_list`.
- Version 1 sharing model: one board per session, a session picker in the pane,
  and agent tools that can read or copy from another session's board. No global
  board in v1 (park it as a backlog idea).
- Default pane position: the right side, stacked with the other right-side
  panes (`placement: 'right'`). Theo can drag it later.
- The project is a GSD project in this repo and is pushed to GitHub
  `Don-Mor-Software-Group/hermes-session-tasks` (private).

## Context (verified on devpc, Hermes Agent source at ~/.hermes/hermes-agent)

- Theo runs Hermes Desktop on his Mac and Windows PCs. Each Desktop connects to
  the Hermes gateway on devpc (DM-TheoDevPC, Debian 12) over an SSH remote. The
  gateway, the agent, and all data live on devpc. Desktop never runs on devpc.
- Hermes plugin model: one "unified package" folder carries both halves.
  Reference: `~/.hermes/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md`
  (sections "A backend for your plugin", "One package, both SDKs", "Pushing
  events to your desktop half", "Pitfalls") and
  `~/.hermes/hermes-agent/website/docs/developer-guide/plugins/index.md`
  (tools, hooks, slash commands, bundled skills).

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

- Python half facts:
  - Loads only when the id is in `plugins.enabled` in `~/.hermes/config.yaml`.
    Set it with `hermes config set` or `hermes plugins enable`, never by hand edit.
  - Tool handlers can declare `session_id` as a keyword and Hermes passes the
    calling session. Use that to key the board. Never trust a session id from
    the model's arguments for the current session.
  - The gateway runs Python 3.11 (`~/.hermes/hermes-agent/venv`). Plugin code
    that runs in the gateway must work on 3.11 and import only the standard
    library plus what the gateway already ships (fastapi, pydantic).
  - Backend routes mount only when `hermes serve` starts. A Desktop reconnect
    reuses the old gateway, so new routes need a gateway restart.
  - `hermes_cli.plugin_events.broadcast_plugin_event("hermes-session-tasks",
    "board.updated", {...})` pushes `plugin.hermes-session-tasks.board.updated`
    to every connected Desktop window. Call it from the tool handler and from
    REST writes so the pane updates live when the agent changes the board.
  - `pre_llm_call` hooks can return `{"context": "..."}` to add text to the
    current turn. Use this (or an equivalent the research finds) so the agent
    sees Theo's own edits to the board. Keep the injected text small and only
    send it when it is needed, so token cost and prompt caching stay sane.
  - Context compression starts a child session with a parent session id. A
    board must follow its session through compression and branches, so Theo does
    not lose the list mid-session. Research how the session lineage is exposed
    (`hermes_state` session parent ids) and decide in discuss-phase.
  - Hermes core keeps a hard rule: never change past context or the system
    prompt mid-conversation (prompt caching).
- Desktop half facts:
  - Plain ESM, no build, no JSX syntax: use `jsx()`/`jsxs()` from
    `react/jsx-runtime`. Import only `@hermes/plugin-sdk`, `react`,
    `react/jsx-runtime`. Verify every SDK name against the SDK doc before use.
  - Use SDK UI components (`Checkbox`, `Input`, `Button`, `ScrollArea`,
    `EmptyState`, `Select*`, `DropdownMenu*`, `ContextMenu*`) and theme vars
    (`var(--ui-*)`), never hardcoded colours. Dark theme only matters.
  - Follow the focused chat with `host.state.focusedStoredSessionId` (durable
    id). Use `ctx.rest` for reads and writes. Use `host.onEvent` for the
    broadcast event and a React Query `useQuery` polling fallback.
    `ctx.socket` is a no-op on OAuth remotes, so do not depend on it.
  - Use `ctx.setInterval`/`ctx.onDispose`, not bare globals (hot reload).
  - The desktop half of a package installed on a remote gateway is not copied
    to the clients. Each client installs it with Install from Git (Desktop
    target) from the GitHub repo. Document this install path for Mac and
    Windows in the README.
- Working example of a package on this host:
  `~/.hermes/plugins/hermes-memory-ui/` (has `desktop/plugin.js`, `dashboard/`,
  `plugin.yaml`). A sibling project that already shipped a Desktop pane with a
  backend: `~/local_repo/deploy-dash/hermes/` (gsd-status-api). Read both for
  patterns. Do not modify either.

## Scope for v1

- Board per session: items with id, text, checked state, parent id (one or
  more subtask levels, decide depth in discuss), order, timestamps, and who made
  the last change (agent or Theo).
- Agent tools (names to decide in discuss; must not collide with `todo_list`):
  read the current board, add items, update/check/uncheck/rename items, remove
  items, reorder, read another session's board, copy items from another session,
  list sessions that have a board. Each write returns the full board as markdown.
- A bundled skill that tells the agent when to use the board: when it lists
  things to do or remember for Theo, keep the board in sync, ask before an
  ambiguous change, never use it as its own scratch plan.
- Pane: shows the focused session's board, checkboxes, inline add and edit,
  add subtask, delete, collapse subtasks, a session picker to view other
  boards, import and copy as markdown. Live update when the agent writes.
- Storage on devpc under `$HERMES_HOME` (resolve with `get_hermes_home()`), in
  a plugin-owned SQLite file or JSON files. Never write into `state.db`. Writes
  must be safe when the agent and the pane write at the same time (revision
  number, reject stale writes).
- Data lifecycle: what happens when a session is deleted (`on_session_delete`
  hook exists). Decide in discuss.

## Out of scope for v1

- A global or project board shared by all sessions (backlog idea).
- Due dates, priorities, assignees, sync to Super Productivity or GitHub.
- Changes to the Hermes Agent source tree. Everything ships as a plugin.

## Constraints

- uv for the dev environment, ruff, pyright, pytest. Gateway runtime is Python
  3.11, so test on 3.11 too.
- Small modules with one responsibility each. Plan the structure first.
- No secrets are needed. If one ever is, it comes from Infisical.
- Repo docs: plain language, no em dash or en dash anywhere, use a spaced hyphen.
- Commit identity: Theo Deyle <theo.deyle@donmor.ca>.
- Deploy on devpc = symlink the package dir into `~/.hermes/plugins/`, enable
  it, restart the gateway. Announce the gateway restart before it happens: it
  drops live Desktop connections.
