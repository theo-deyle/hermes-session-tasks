# Architecture Research

**Domain:** Hermes Agent + Hermes Desktop unified plugin (Python tools, hooks, FastAPI router, plain ESM pane) that gives each session a task board
**Researched:** 2026-10-30
**Confidence:** HIGH for the Python half and the REST and event path (read in source). MEDIUM for live Desktop behaviour (not run). LOW only where marked "verify".

Path shorthand used in every citation below:

- `HA/` = `~/.hermes/hermes-agent/` (checkout at commit `bf0203a794`, 2026-10-22)
- `HP/` = `~/.hermes/plugins/`
- `sdk-doc` = `HA/website/docs/developer-guide/desktop-plugin-sdk.md`
- `plug-doc` = `HA/website/docs/developer-guide/plugins/index.md`
- `hooks-doc` = `HA/website/docs/user-guide/features/hooks.md`

## Findings that change PROJECT.md or STACK.md

Read these first. Each one changes a plan.

1. **The live gateway runs Python 3.14.9, not 3.11.** Process 342192 (`hermes serve --isolated ...`) has `/proc/342192/exe -> ~/.hermes/tools/python-3.14.9+20261021-linux-x64/bin/python3.14`. Its site-packages come from `~/.hermes/installs/33051a290b175956/environments/f19caafe225c4f28bbfba8fa22ceed88/venv/lib/python3.14`. That env has fastapi 0.133.1, pydantic 2.13.4, SQLite 3.53.1. The checkout venv (`HA/venv`) is 3.11.16. `HA/pyproject.toml:15` allows `>=3.11,<3.15`. The installed analog `HP/gsd-status-api` has a `cpython-314` pyc. **Plugin code must run on 3.11 to 3.14. Test on both.** STACK.md says "3.11 only"; that is wrong for the live process.
2. **Several gateway processes run at once.** `ps` shows two `hermes serve --isolated --host 127.0.0.1 --port 0 --ssh-session-token-file ...` processes (PIDs 342192 and 342636, each with its own token file under `~/.hermes/desktop-ssh/`). Desktop starts one per SSH connection. The messaging gateway is another process. Tools, hooks and routes share a process only inside one `serve`. So the store must be safe across processes (SQLite, not a Python lock), and a broadcast reaches only the Desktop windows of the process that sent it (`HA/tui_gateway/server.py:762-778`, `_live_transports` is process-local). **Polling is the real cross-process path. The event is an accelerator.**
3. **The Desktop half does not deploy by the devpc symlink.** The unified-package copy is local to the machine that runs Desktop. For a remote backend the remote `~/.hermes/plugins` is not reachable, so `plugin.js` must be installed on the Mac and on the Windows PC separately (`sdk-doc:1766-1775`). PROJECT.md "Deploy on devpc by symlink" covers the Python half only. It needs a second deploy step and a version handshake (see "Deployment seams").
4. **Compression keeps the session id by default.** `compression.in_place` defaults to `true` (`HA/hermes_cli/config_defaults.py:695-700`, `HA/agent/agent_init.py:1582-1584`). `~/.hermes/config.yaml` does not override it. With in-place compaction there is no `parent_session_id` chain (`HA/website/docs/developer-guide/context-compression-and-caching.md:329-336`). The lineage code is a safety net for `in_place: false`, plus branches. It is not the main path. Key the board by root id anyway, so a later config change needs no migration.
5. **Plugin skills do appear in `<available_skills>`.** `plug-doc:1201` says they do not. The source says they do (`HA/agent/prompt_builder.py:1200-1226`, `HA/hermes_cli/plugins_content.py:27-30`). Trust the source. The `description` argument of `register_skill` becomes the index row, so write it as a trigger sentence.
6. **`plugin_api.py` loads with no package context.** It is imported as a top-level module named `hermes_dashboard_plugin_<name>` from the file path (`HA/hermes_cli/web_server_dashboard.py:1168-1180`). A relative import (`from ..core import x`) fails. The agent half is different: it loads as the package `hermes_plugins.<slug>` with `__path__` set, so relative imports work there (`HA/hermes_cli/plugins_loader.py:719-754`). Both halves need one loader snippet for the shared `core` package (see "Shared code").

## Standard Architecture

### System Overview

```
 Mac / Windows (Hermes Desktop, renderer)               devpc (hermes serve process, Python 3.14)
+----------------------------------------+            +------------------------------------------------+
| desktop/plugin.js (pane, placement     |  ctx.rest  | gateway auth middleware (token or native grant) |
|  'right')                              |----------->|   -> /api/plugins/hermes-session-tasks/*        |
|  - reads host.state.focusedStoredSessionId           |   dashboard/plugin_api.py  (thin FastAPI router) |
|  - useQuery poll (4 s) + invalidate    |<-----------|                  |                              |
|  - ctx.onEvent(plugin.<id>.board.updated)  events   |                  v                              |
+----------------------------------------+            |   core/service.py  <-------------+             |
                                                      |     ^        |  (one write path)  |             |
   Agent turn (same process)                          |     |        v                    |             |
+--------------------------------+   tool call        |   tools.py  core/store.py     hooks.py          |
| model -> registry.dispatch     |------------------->|  (session_id kwarg)  |   (pre_llm_call,         |
|   session_id=agent.session_id  |                    |                      v    post_compaction,      |
+--------------------------------+                    |               SQLite data.db  on_session_delete)|
                                                      |      core/lineage.py (id -> root id)            |
                                                      |      core/events.py -> broadcast_plugin_event   |
                                                      +------------------------------------------------+
                                                         ^ other serve processes and the messaging
                                                           gateway open the same SQLite file
```

### Component Boundaries

| Component | Responsibility | Talks to | Must not |
|-----------|----------------|----------|----------|
| `core/model.py` | Item and Board dataclasses, limits, error types, id generation | nothing | import Hermes, touch disk |
| `core/markdown.py` | Parse `- [ ]` and `- [x]` lists to a tree. Render a board to markdown with or without item ids | `model` | touch disk |
| `core/store.py` | SQLite schema, `user_version` migrations, one `BEGIN IMMEDIATE` transaction per write, revision rule, change journal, alias table | `model`, a connection factory passed in | know about tools, REST, events |
| `core/service.py` | Use cases (read, add, update, remove, move, import, copy, list). Applies the actor and `base_rev` rule. Calls the publisher after commit | `store`, `markdown`, `lineage`, publisher callback | import FastAPI or Hermes at module level |
| `core/delta.py` | Builds the text the agent gets: delta since `agent_seen_rev`, or the full board. Owns the size caps | `service`, `markdown` | change the board |
| `core/lineage.py` | Session id -> root board id. Branch detection. Alias writes | `store`, `hermes_state.SessionDB` (lazy import) | write to state.db |
| `core/events.py` | `publish(root_id, rev, actor)` -> `broadcast_plugin_event`. Swallows errors | `hermes_cli.plugin_events` (lazy import) | block or raise |
| `core/paths.py` | Connection factory: `plugins.plugin_storage.plugin_db` (lazy import) | Hermes storage helper | cache a connection |
| `tools.py` + `schemas.py` | Tool schemas and handlers. Take `session_id` from the injected kwarg | `service` (injected) | accept the current session id from model arguments |
| `hooks.py` | `pre_llm_call`, `post_compaction`, `on_session_delete` callbacks | `delta`, `service` (injected) | raise, block, or run long |
| `skills/hermes-session-tasks/SKILL.md` | Rules for the agent | none | |
| `dashboard/plugin_api.py` | Pydantic request models, routes, HTTP status mapping | `core` via the loader snippet | hold business rules |
| `desktop/plugin.js` | Pane, picker, markdown import and copy, live update | `ctx.rest`, `ctx.onEvent`, `host.state` | import anything except `@hermes/plugin-sdk`, `react`, `react/jsx-runtime` |

## Verified API reference

### 1. Registration contract

`register(ctx)` lives in the package `__init__.py` and runs once at load. A crash disables the plugin but not Hermes (`plug-doc:921-923`). The plugin loads only when its id is in `plugins.enabled` (`HA/hermes_cli/web_server_dashboard.py:798-811`, `sdk-doc:1826-1833`).

| Call | Exact signature | Source |
|------|-----------------|--------|
| `ctx.register_tool` | `register_tool(self, name: str, toolset: str, schema: dict, handler: Callable, check_fn: Callable \| None = None, requires_env: list \| None = None, is_async: bool = False, description: str = "", emoji: str = "", override: bool = False) -> Optional[PluginRegistration]` | `HA/hermes_cli/plugins.py:461-466` |
| `ctx.register_hook` | `register_hook(self, hook_name: str, callback: Callable) -> PluginRegistration`. An unknown name only warns (`plugins.py:959-961`) | `HA/hermes_cli/plugins.py:943-945` |
| `ctx.register_skill` | `register_skill(self, name: str, path: Path, description: str = "", frontmatter: Optional[Mapping] = None) -> PluginRegistration`. Name matches `[a-zA-Z0-9_-]+`, no `:`. The agent loads it as `hermes-session-tasks:<name>`. Raises `FileNotFoundError` if the file is missing | `HA/hermes_cli/plugins_content.py:22-52` |
| `ctx.register_system_prompt_section` | `register_system_prompt_section(self, id, content: str \| Callable, *, position="after_memory", max_chars=...)`. Frozen into each new session prompt. Static text only | `HA/hermes_cli/plugins.py:967-989` |

Schema shape is the OpenAI function form: `{"name", "description", "parameters": {...}}` (`plug-doc:732-787`). Handler shape: `def handler(args: dict, **kwargs) -> str`, always return a JSON string, never raise (`plug-doc:877-881`). Result type errors become a tool error (`HA/tools/registry.py:940-944`).

**How the handler gets `session_id`.**

1. The agent calls `model_tools.handle_function_call(..., session_id=agent.session_id or "", ...)` (`HA/agent/tool_executor.py:1721-1727`; same value in `HA/agent/agent_runtime_helpers.py:2568`).
2. `_execute_tool` builds `dispatch_kwargs = {"task_id": ids.task_id, "session_id": ids.session_id}` and calls `registry.dispatch(function_name, next_args, **dispatch_kwargs)` (`HA/model_tools.py:827-839`).
3. `registry.dispatch` narrows the kwargs to what the handler signature names, via `_kwargs_accepted_by` (`HA/tools/registry.py:954-957`, `1086-1096`). A handler with `**kwargs` gets everything. A handler with a `session_id` parameter gets only that.
4. The value is `agent.session_id`. That is the **live** id. Under rotating compression it is the tip, not the root. Under the default in-place mode it is the one durable id. It can be `""` (handle it: return a tool error).

**Hooks that matter (all in `VALID_HOOKS`, `HA/hermes_cli/plugins.py:108-203`).**

| Hook | Kwargs we use | Return | Notes |
|------|---------------|--------|-------|
| `pre_llm_call` | `session_id`, `is_first_turn`, `parent_session_id`, `task_id`, `turn_id`, `platform`, `model`, `user_message`, `conversation_history` (`HA/agent/turn_context.py:809-822`) | `{"context": str}` or a plain non-empty `str`. `None` means no injection (`turn_context.py:834-838`) | Once per user turn, after compression, before the tool loop (`hooks-doc:698`). Bounded by the hook timeout, default 30 s, on a worker thread with the context copied (`HA/hermes_cli/plugins_dispatch.py:41-55,164,358`). Per-hook context over 10,000 chars is spilled to disk (`plug-doc:1560`). |
| `post_compaction` | `session_id`, `old_session_id` (`""` when in place), `kind`, `reason` | ignored | Fires once per committed compaction on every path (`hooks-doc:1118-1135`, `plugins.py:202`). Timeout-bounded. |
| `on_session_delete` | `session_id`, `reason`, `profile`, optional `deleted_ids`, `sessions_dir` | ignored | `reason` is one of `delete`, `archive`, `empty_sweep`, `prune`, `ghost_prune`, `profile_repair`. Fires after commit, in the committing process only, no exactly-once guarantee (`hooks-doc:1086-1112`). |

Callbacks should take `**kwargs`. Narrow signatures get only the fields they name (`plugins_dispatch.py:259-263`).

Imports from Hermes must stay on the public list: `hermes_constants`, `hermes_state`, `hermes_cli.plugin_events`, `hermes_cli.config`, `plugins.plugin_storage`, `tools.registry` (`HA/hermes_cli/plugin_validate_private_imports.py:38`). Run `hermes plugins validate` in CI.

**Tool names and toolset.** `todo_list` (toolset `todo`) is taken (`HA/tools/todo_tool.py:333`). Use the toolset `session_tasks` and a `tasks_board_` prefix. Plugin toolsets are on by default for a platform unless default-off or already "known" and unsaved (`HA/hermes_cli/tools_config.py:527-534`). Theo's `platform_toolsets` lists are explicit and `known_plugin_toolsets` names only `a2a` and `spotify` (`~/.hermes/config.yaml`), so the new toolset should appear. **Verify in a fresh Desktop session.** Saving the toolset panel later writes `known_plugin_toolsets` and can switch it off.

### 2. Backend mount, auth, imports

- **Mount.** `dashboard/manifest.json` with `"api": "plugin_api.py"` is found by scanning `<plugins root>/*/dashboard/manifest.json` (`HA/hermes_cli/web_server_dashboard.py:565-596`). The module must export `router`. It is mounted with `app.include_router(router, prefix=f"/api/plugins/{name}", dependencies=[Depends(_plugin_route_secret_scope)])` (`web_server_dashboard.py:1185-1189`). `name` comes from the manifest `name` field (`:585`).
- **Hide the dashboard tab.** `manifest.json` without `tab` still gets a default tab with `entry: dist/index.js` (`web_server_dashboard.py:527-556`). Set `"tab": {"hidden": true}` like `HP/gsd-status-api/dashboard/manifest.json`. Final manifest: `{"name": "hermes-session-tasks", "api": "plugin_api.py", "tab": {"hidden": true}}`.
- **First mount needs no restart, later edits do.** A newly enabled plugin hot-mounts on its first request (`web_server_dashboard.py:1032-1110`). Any edit to `plugin_api.py` or `core/` needs a restart of **every** `hermes serve` process (there are two). The loaded module stays in `sys.modules` (`:1175`).
- **Auth.** The routes sit behind the gateway auth. `auth_middleware` returns 401 for any `/api/` path that is not public unless the request carries a session token, a native HTTP principal, or token auth (`HA/hermes_cli/web_server.py:443-463`). The outermost `_token_auth_seam` runs `authenticate_native_http` first (`web_server.py:466-480`). `/api/plugins/*` is not on the public list (`HA/hermes_cli/dashboard_auth/public_paths.py:23` lists only `/api/dashboard/plugins`). A disabled plugin's routes answer 404 only after auth passes (`web_server.py:398-420`). Doc statement: `HA/website/docs/user-guide/features/extending-the-dashboard.md:750`.
- **How Desktop sends credentials.** `ctx.rest(path, opts)` calls `pluginRest`, which calls `hermesApi({ path: '/api/plugins/<id>' + suffix, method, body, timeoutMs, ...profileScoped() })` (`HA/apps/desktop/src/api/plugins.ts:72-87`). Desktop's main process attaches the credential. The plugin never sees it. `..` in a path throws (`plugins.ts:56-64`). Options: `{ method?, body?, upload?, timeoutMs? }` (`plugins.ts:44-50`). The body is a JS object and the response is parsed JSON.
- **Profile scope.** The mount dependency sets the profile scope for each request (`web_server_dashboard.py:937-956`). `get_hermes_home()` honours the context override (`HA/hermes_constants.py:188-195`). So `plugin_data_dir` follows the profile. No `_profile_request_scope` dependency is needed, unlike `HP/hermes-memory-ui/dashboard/plugin_api.py:80`.
- **Event loop.** In-process handlers run on the gateway loop. A plain `def` route runs in a worker thread. An `async def` route that calls SQLite blocks every other request (`extending-the-dashboard.md:752-760`). Use plain `def` routes.
- **Imports of the plugin's own modules from `plugin_api.py`.** Not possible by relative import (finding 6). `HP/hermes-memory-ui` avoids the problem with one 112 KB file. Use the loader snippet below instead.

### 3. Live update

- **Python side.** `from hermes_cli.plugin_events import broadcast_plugin_event`. Signature: `broadcast_plugin_event(plugin_id: str, event: str, payload: Optional[dict[str, Any]] = None) -> None` (`HA/hermes_cli/plugin_events.py:66`). `plugin_id` matches `[a-z0-9_-]{1,64}`. `event` is a bare dotted name of `[A-Za-z0-9_-]` segments, max 128 chars. Bad input raises `ValueError`. A non-dict payload raises `TypeError` (`plugin_events.py:40-80`). Delivery is fire and forget; a wedged peer is skipped (`HA/tui_gateway/server.py:762-778`). With no gateway it logs and returns (`plugin_events.py:84-92`).
- **Wire name.** `plugin.hermes-session-tasks.board.updated`. Frame: `{"jsonrpc":"2.0","method":"event","params":{"type": name, "session_id": "", "payload": {...}}}` (`HA/tui_gateway/server.py:717-720`).
- **Where it works.** Callers in `plugin_api.py` routers, tools and hooks of the agent turn reach every Desktop window connected to that `hermes serve` (`sdk-doc:1862-1870`, `plugin_events.py:19-30`). `hermes chat`, cron, and a gateway with no Desktop client send to nobody.
- **Desktop side.** `ctx.onEvent(type, listener)` is the tracked form (`sdk-doc:191`). `host.onEvent(type, fn)` is the same tap and is retired with the plugin when called during `register` (`sdk-doc:1120-1122`, `HA/apps/desktop/src/contrib/events.ts:31-45`). The listener gets the whole `GatewayEvent`, so read `event.payload`. Events can be replayed after a reconnect (`replayed?: boolean`, `HA/apps/shared/src/gateway-events.ts:57-59`). The handler must be idempotent. Invalidating a query is.
- **`ctx.socket` is a no-op on OAuth remotes.** `sdk-doc:1900-1902` and `2026`. The source says the same: "OAuth remotes resolve null" (`plugins.ts:121-127`). Do not use `ctx.socket` at all.

### 4. Desktop pane

- **Register.** `ctx.register({ id: 'pane', area: 'panes', title: 'Tasks', data: { placement: 'right', width: '320px' }, render: () => jsx(Pane, { ctx }) })`. `placement` is `'main' | 'left' | 'right' | 'top' | 'bottom'`. A `right` pane stacks as a tab with other right panes (`sdk-doc:245-262`). The contribution id becomes `hermes-session-tasks:pane` (`sdk-doc:172-175`, `1171-1175`). Closing the only pane a plugin contributes **disables the plugin** until Theo re-enables it in Capabilities, Plugins (`sdk-doc:279-283`). Known behaviour, no fix.
- **Follow the focused chat.** `useValue(host.state.focusedStoredSessionId)`. It is `$focusedStoredSessionId`, the tile id when a tile has focus, else the primary selection (`HA/apps/desktop/src/store/session-focus.ts:90-92`, exposed at `HA/apps/desktop/src/sdk/index.ts:609`). It is `null` for a fresh draft. Do not use `focusedSessionId`: that is the runtime id and is useless on the server (`sdk-doc:1072-1074`). The stored id equals the `session_key` the backend reports as `stored_session_id` (`HA/tui_gateway/server.py:1609`). That key can differ from `agent.session_id` after a rotation (`server.py:1057-1063`). So the server resolves any id to a root.
- **REST.** `ctx.rest('/board?session_id=' + encodeURIComponent(sid))`, `ctx.rest('/board/items', { method: 'POST', body: {...} })`. Base path `/api/plugins/hermes-session-tasks`.
- **Polling and cache.** `useQuery`, `useMutation`, `useQueryClient` and the shared `queryClient` are SDK exports (`HA/apps/desktop/src/sdk/index.ts:1895,2004-2008`). The bundled kanban plugin uses `invalidateQueries` on events plus `refetchInterval` (`HA/apps/desktop/src/plugins/kanban/api.ts:163-185`, `plugin.tsx:50`). `host.paneVisibility('hermes-session-tasks:pane')` is an atom that is true while the pane is on screen (`sdk-doc:1171-1182`). Poll only while true.
- **UI components actually exported** (`HA/apps/desktop/src/sdk/index.ts:1729-1803`): `StatusDot`, `Badge`, `Button`, `Checkbox`, `Codicon`, `ColorSwatches`, `ConfirmDialog`, `ContextMenu`, `ContextMenuCheckboxItem`, `ContextMenuContent`, `ContextMenuItem`, `ContextMenuSeparator`, `ContextMenuSub`, `ContextMenuSubContent`, `ContextMenuSubTrigger`, `ContextMenuTrigger`, `CopyButton`, `DecodeText`, `Dialog`, `DialogContent`, `DialogDescription`, `DialogFooter`, `DialogHeader`, `DialogTitle`, `DialogTrigger`, `DisclosureCaret`, `DropdownMenu`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuSeparator`, `DropdownMenuTrigger`, `EmptyState`, `ErrorState`, `FadeScroll`, `GlyphSpinner`, `Input`, `Kbd`, `KbdGroup`, `Loader`, `LogView`, `Popover`, `PopoverContent`, `PopoverTrigger`, `RowButton`, `SandboxedFrame`, `ScrollArea`, `SearchField`, `SegmentedControl`, `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue`, `Separator`, `Skeleton`, `Switch`, `Tabs`, `TabsList`, `TabsTrigger`, `Textarea`, `Tip`, `Tooltip`, `TooltipContent`, `TooltipProvider`, `TooltipTrigger`. Helpers: `isSubmitEnter` (IME-safe Enter, `sdk/index.ts:1873`), `icons`, `cn`, `haptic`, `useI18n`, `relativeTime`. **Not exported:** `SelectGroup`, `SelectLabel`, `DropdownMenuCheckboxItem`, `DropdownMenuSub*`, `Collapsible`. Use `DisclosureCaret` plus local state for collapse. PROJECT.md already lists names that all exist.
- **Reference code to copy.** `HP/hermes-memory-ui/desktop/plugin.js` (named SDK imports, `ctx` passed into components, `useQuery` with `queryKey: [PLUGIN_ID, ...]`, lines 1-25, 434, 1779). Pane placement reference: `HA/apps/desktop/src/plugins/hermes-bots/roster-pane.tsx:154`. A node `vm` smoke test for a plain-ESM plugin: `HP/hermes-memory-ui/tests/desktop_plugin_smoke.mjs`.

## Session lineage (question 5)

**What Hermes does.**

- Default `in_place: true`: compaction rewrites the message list on the same session id. No parent chain (`context-compression-and-caching.md:329-336`).
- `in_place: false`: each compaction commits a child row. The parent ends with `end_reason = 'compression'` and the child has `parent_session_id = parent.id`. Schema: `parent_session_id TEXT` with an index (`HA/website/docs/developer-guide/session-storage.md:189,215`). Predicate for a compression child: parent exists with `end_reason = 'compression'` (`HA/hermes_state_common.py:174-175`). Python form: `_is_compression_child_row` (`HA/hermes_state_compression.py:906-912`).
- `/branch` makes a child with `model_config._branched_from` set (`HA/hermes_state_common.py:170-173`). Public check: `SessionDB.is_explicit_fork_child(session_id)` (`HA/hermes_state_messages.py:1899`; row form at `:1878-1897`). A branch is **not** a compression continuation (`hermes_state_messages.py:1667-1693`).
- Sidebar rows carry `id` (the tip) and `_lineage_root_id` (the root, only when different) (`HA/hermes_state_sessions.py:1151,1286-1287`). The SDK says stored ids resolve to the durable lineage root (`sdk-doc:598-604`).
- `SessionDB.get_conversation_root` exists (`hermes_state_messages.py:1745-1749`) but it uses a raw parent walker that crosses branch and reset boundaries (`hermes_state_sessions.py:1543-1556`). Do not use it. `_resume_lineage_ids` is private. Write a 15-line walker on the public methods instead.

**Recommendation: key the board by the compression-root session id. Resolve any id to the root once, and cache the answer in our own alias table.**

Rules:

1. `board_key = root_id`. The root is the first ancestor reached by walking `parent_session_id` only across compression edges.
2. `lineage.resolve(session_id)`: alias hit -> root. Miss -> walk with `SessionDB(read_only=True)` (`HA/hermes_state.py:582`) using `get_session` and `is_explicit_fork_child`, write the alias row, return the root. In the default in-place mode the walk is one `get_session` and ends at the id itself.
3. `post_compaction` with a non-empty `old_session_id` writes `alias(new_id -> root_of(old_id))` with no DB read.
4. **Branch = lazy fork.** On the first resolve of a session that `is_explicit_fork_child` and has a `_branched_from` parent that owns a board, copy that board once (new item ids, journal row "forked from") and give the branch its own root. No hook fires on branch creation, so the copy happens on first access. The branch board is "the parent board as of the branch's first use". Accept that small drift.
5. Reset children (`/new`, idle, daily) are separate conversations and get a separate board.

Why not the other two options: copy on compression needs a hook race and doubles data. Following the parent chain on every read costs a DB walk per tool call and per poll.

## Storage and concurrency (question 6)

- **Owner.** `core/store.py` is the only module that writes the board. Tools, REST routes and hooks all call `core/service.py`, which calls the store. One write path.
- **File.** One SQLite file through `plugins.plugin_storage.plugin_db("hermes-session-tasks")` -> `<HERMES_HOME>/plugin-data/hermes-session-tasks/data.db`, WAL, foreign keys, 5000 ms busy timeout (`HA/plugins/plugin_storage.py:27-47`, `HA/hermes_cli/sqlite_util.py:18-67`). This matches STACK.md.
- **Process model.** Inside one `hermes serve`, routes, plugin slash commands, and the tools and hooks of the agent turn run in one process (`plugin_events.py:19-30`; `dashboard.turn_isolation` is `False` by default, `HA/hermes_cli/config_defaults.py:1019`; `plugins.isolation` defaults to `in_process`, `HA/hermes_cli/plugin_isolation.py:1-10`, and `~/.hermes/config.yaml` has neither key). But there are several processes (finding 2). So the lock is the SQLite file lock. Open one connection per operation, close it, never share it across threads. Tool calls in one turn can run on parallel threads.
- **Schema (sketch).**
  - `boards(root_id PK, rev INT, agent_seen_rev INT, created_at, updated_at)`
  - `items(id PK, root_id FK, parent_id NULL, position INT, text, checked INT, rev INT, updated_by TEXT 'agent'|'user', created_at, updated_at)`
  - `aliases(session_id PK, root_id)`
  - `changes(root_id, rev, actor, op, item_id, text, ts)` keeps the last 100 rows per board.
- **Revision rule.**
  1. `boards.rev` rises by exactly 1 per committed write operation. A batch (add 5 items) is one operation.
  2. Every item stores `rev` = the board rev of its last change.
  3. Every write names the actor (`agent` or `user`) and a `base_rev` (the rev the caller last saw). Pane: the rev of its last fetch. Agent: `boards.agent_seen_rev`.
  4. Inside `BEGIN IMMEDIATE`: add never conflicts. Update, check, rename, remove and move of item X are rejected if `X.rev > base_rev` or X is gone. Reorder and import-replace are rejected if `board.rev != base_rev`.
  5. A reject returns 409 (REST) or a tool error with `stale: true`, plus the current board. Nothing is half applied.
  6. Why per item and not whole board: Theo checks item 3 while the agent appends item 7. Those do not conflict. A whole-board rule would reject Theo every time the agent writes.
- **Events.** The service calls the publisher after the commit and outside the transaction. A publish failure never fails the write.

## Agent sees Theo's edits (question 7)

Goal: the agent learns of Theo's edits on its next turn, with the least injected text, without touching past context.

**What the cache rule allows.** AGENTS.md says mutating past context or rebuilding the system prompt mid-conversation breaks the cache (`HA/AGENTS.md:20-21`). `pre_llm_call` text is appended to the **current** user message. Hermes persists the exact API-bound message in an `api_content` sidecar so "what turn N sends is what turn N+1 replays" (`HA/agent/turn_context.py:108-132`, `hooks-doc:715`). So an injection is never rewritten, but it is replayed on every later turn until compaction. **Every injected byte costs tokens for the rest of the session.** Keep each injection small and rare.

**Design.**

1. State: `boards.agent_seen_rev` = the newest rev whose content the agent has in its context.
2. Advance `agent_seen_rev` in the same transaction when (a) a tool returns the board to the agent (every board tool returns the full markdown plus `rev`), or (b) the hook injects text.
3. `pre_llm_call(session_id, **kwargs)`:
   - Resolve the root. No board, or `rev == agent_seen_rev` -> return `None`.
   - Read `changes` after `agent_seen_rev`. If none has `actor = 'user'` -> set seen to `rev`, return `None` (the agent made those changes and already saw the results).
   - If the journal covers the gap: return `{"context": delta_text}`. Delta format, at most 20 lines and about 1200 chars:

     ```
     [task board] The user changed the board since you last looked (rev 11 -> 14):
     - checked "Send quote to Alex" {#a3}
     - added "Call garage" {#c7}
     - renamed {#b1} to "Book dentist Tuesday"
     Open items: 4. Call tasks_board_read for the full list.
     ```
   - If the journal does not cover the gap, or `agent_seen_rev == 0` with a non-empty board: inject the full board, capped at 40 items or 2000 chars (open items first, then "N done items hidden").
4. `post_compaction`: set `agent_seen_rev = 0`. Compaction summarised the earlier injections and tool results, so the next turn re-injects the full board once. Order is safe: preflight compaction runs before `pre_llm_call` in the same turn (`hooks-doc:698`).
5. Never change the system prompt. Do not use `register_system_prompt_section` for live board state: it is frozen per session and its text is static.
6. Every delta and tool result carries `rev`. The skill tells the agent: the highest rev in view is the truth. Old views in history stay stale by design.
7. Limits: edits made during a long running turn show up on the next turn, or earlier as a stale reject if the agent writes the same item. The hook skips `platform` values that have no pane only if discuss decides so.

**Always visible agent rules.** Put the three core rules in the tool descriptions (they sit in the cached tool list): the board is the user's list and not your plan; ask before an ambiguous change; never use `todo_list` for it. The skill carries the detail and its `description` is the index row that makes the model load it (`prompt_builder.py:1225`).

## Data flow

### A. Agent adds an item

1. The model emits `tasks_board_add` with `{"items": [{"text": "Send quote to Alex"}]}`.
2. `agent/tool_executor.py:1721-1727` calls `handle_function_call(..., session_id=agent.session_id or "")`. `model_tools.py:827-839` calls `registry.dispatch`. `registry.py:957` narrows kwargs to the handler signature.
3. `tools.py` handler checks arguments and `session_id != ""`. It calls `service.add(session_id, actor="agent", items=...)`.
4. `service` calls `lineage.resolve(session_id)` -> `root_id` (alias hit, else `SessionDB` walk, then alias write).
5. `store` runs `BEGIN IMMEDIATE`: create the board row if absent, apply the revision rule (add never conflicts), insert items with `rev = board.rev + 1`, bump `boards.rev`, write a `changes` row, set `agent_seen_rev = new rev`, `COMMIT`.
6. After commit, `events.publish(root_id, rev, "agent")` calls `broadcast_plugin_event("hermes-session-tasks", "board.updated", {"root_id", "rev", "actor"})`. It reaches every Desktop window of this `serve` process.
7. The handler returns a JSON string with `ok`, `rev` and the agent-view markdown (with item ids). The turn goes on.
8. In Desktop, `ctx.onEvent("plugin.hermes-session-tasks.board.updated", ...)` calls `queryClient.invalidateQueries({ queryKey: ['hermes-session-tasks'] })`. The pane refetches `GET /board?session_id=<focused>&since_rev=<known>`. If the event never arrives (other process, reconnect), the 4 s poll while the pane is visible does the same.

### B. Theo checks an item

1. Click on `Checkbox`. `useMutation` calls `ctx.rest('/board/items/<id>', { method: 'PATCH', body: { session_id: focusedStoredSessionId, checked: true, base_rev } })`.
2. Desktop main sends it to `/api/plugins/hermes-session-tasks/board/items/<id>` with the credential. Gateway auth admits it (`web_server.py:443-480`).
3. The plain `def` route validates the Pydantic body and calls `service.update(session_id, actor="user", ...)`. Same `lineage.resolve`.
4. `store` runs the rule: reject with 409 + current board if `item.rev > base_rev`. Else set `checked`, `item.rev = board.rev + 1`, `updated_by = 'user'`, write a `changes` row, `COMMIT`. `agent_seen_rev` is not touched.
5. The route publishes the event and returns the new board. The pane writes it into the query cache. The self-echo event is harmless (the pane ignores `rev <= cached rev`).
6. On Theo's next message, `turn_context.py:1179` runs `pre_llm_call`. The hook sees `rev (14) > agent_seen_rev (11)` with user changes in the journal, builds the delta, returns `{"context": ...}`, and sets `agent_seen_rev = 14`. Hermes appends the text to that user message (`turn_context.py:117-131`).
7. The agent's next board write uses `base_rev = 14`. If Theo changed the same item again after that, the agent gets a stale reject with the current board, and `agent_seen_rev` moves up.

### C. Compression happens

**Default (in place).**

1. Compaction rewrites the message list on the same session id (`config_defaults.py:695-700`). The board key does not change.
2. `post_compaction(session_id=<same>, old_session_id="")` fires. `hooks.py` calls `service.reset_seen(session_id)`: `agent_seen_rev = 0`. No event.
3. The pane does nothing: `focusedStoredSessionId` is unchanged.
4. On the next turn, `pre_llm_call` finds `agent_seen_rev (0) < rev` with a non-empty board and injects the full board once.

**Rotating (`in_place: false`).**

1. Compaction commits a child session. The old row ends with `end_reason = 'compression'`. The child has `parent_session_id = old`.
2. `post_compaction(session_id=new, old_session_id=old)` fires. The hook writes `alias(new -> root_of(old))` and resets `agent_seen_rev`.
3. The next tool call has `session_id = new`. `lineage.resolve` hits the alias. Same board.
4. Desktop may send either the root or the tip as `session_id`. The server resolves both to one root (alias hit, or walker). No pane change is needed.

**Branch.** First tool call or first `GET /board` for the branch id: `lineage.resolve` sees an explicit fork, copies the parent board once, stores the branch as its own root. Later edits do not cross.

**Delete.** `on_session_delete(reason in {delete, empty_sweep, prune, ghost_prune})` deletes boards whose root is in `{session_id} + deleted_ids`, and their alias rows. `archive` and `profile_repair` keep the board (an archived session can come back, `hooks-doc:1099`).

## Proposed module layout

```
hermes-session-tasks/                       # package dir, symlinked into ~/.hermes/plugins/
  plugin.yaml                               # name, version, description, provides_tools, provides_hooks
  __init__.py                               # register(ctx) only; load_core(); inject service into tools and hooks
  schemas.py                                # tool schemas (OpenAI function form)
  tools.py                                  # handlers: def h(args, *, session_id="", **kwargs) -> str
  hooks.py                                  # pre_llm_call, post_compaction, on_session_delete
  skills/hermes-session-tasks/SKILL.md      # the skill; register_skill(name, path, description)
  core/                                     # pure Python, stdlib only, no Hermes import at module level
    __init__.py
    model.py     markdown.py    store.py    service.py    delta.py
    lineage.py   events.py      paths.py                  # last three import Hermes lazily inside functions
  dashboard/
    manifest.json                           # {"name", "api": "plugin_api.py", "tab": {"hidden": true}}
    plugin_api.py                           # router, Pydantic models, HTTP mapping; load_core()
  desktop/
    plugin.js                               # one plain ESM file
```

The Python tests, `pyproject.toml` and `.planning/` stay outside the package dir (STACK.md).

### Shared code (`load_core`)

Both entry files call the same 12-line snippet so the two halves share one module object under a fixed key:

```python
def load_core():
    import importlib.util, sys
    from pathlib import Path
    name = "hermes_session_tasks_core"
    if name in sys.modules:
        return sys.modules[name]
    root = Path(__file__).resolve().parent            # use .parent.parent in plugin_api.py
    init = root / "core" / "__init__.py"
    spec = importlib.util.spec_from_file_location(name, init, submodule_search_locations=[str(init.parent)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
```

`tools.py` and `hooks.py` receive `core.service` by argument. They never import `core` themselves. A pytest asserts both halves get the same object. The SQLite file is the real shared state, so a duplicate module would still be safe. The fixed key is not evicted on `reload-plugins` (`plugins_loader.py:738` evicts only `hermes_plugins.<slug>`), so edits need a restart. That restart is needed for the routes anyway.

### Registration skeleton

```python
def register(ctx):
    core = load_core()
    svc = core.service.build()                     # wires paths, lineage, events
    tools.register(ctx, svc)                       # ctx.register_tool(name=..., toolset="session_tasks", schema=..., handler=...)
    ctx.register_hook("pre_llm_call", hooks.make_pre_llm_call(svc))
    ctx.register_hook("post_compaction", hooks.make_post_compaction(svc))
    ctx.register_hook("on_session_delete", hooks.make_on_session_delete(svc))
    ctx.register_skill("hermes-session-tasks", SKILL_PATH,
                       description="Use when you list things to do or remember for the user, or when the user edits the task board.")
```

### Tool surface (names to settle in discuss)

Six tools keep the cached schema small: `tasks_board_read` (optional `other_session_id`), `tasks_board_add` (list of items with optional `parent_id`), `tasks_board_update` (list of `{id, text?, checked?}`), `tasks_board_remove`, `tasks_board_sessions` (boards with title, open and done counts), `tasks_board_copy` (`from_session_id`, optional item ids). Move and reorder fold into `update` (`parent_id`, `after_id`). The current session is never an argument.

### REST surface (all under `/api/plugins/hermes-session-tasks`)

`GET /meta` (api version, plugin version), `GET /boards`, `GET /board?session_id=&since_rev=` (returns `{changed: false, rev}` when nothing moved), `POST /board/items`, `PATCH /board/items/{id}`, `DELETE /board/items/{id}`, `POST /board/move`, `POST /board/import`, `GET /board/markdown`, `POST /board/copy`. Every write body carries `session_id` and `base_rev`. Every response carries `root_id` and `rev`. Titles for the picker come from `SessionDB(read_only=True).get_session(root)["title"]`.

### Suggested build order

| # | Build | Depends on | Done when |
|---|-------|-----------|-----------|
| 1 | `model`, `markdown` | none | round trip tests pass on 3.11 and 3.14 |
| 2 | `store` with the revision rule, journal, alias table | 1 | a two-process write race test passes (`multiprocessing`, same file) |
| 3 | `service`, `delta` | 2 | actor, stale-reject and delta tests pass with a fake publisher |
| 4 | `paths`, `lineage`, `events` adapters | 3 | contract tests against a fake `SessionDB`, plus one test with `HERMES_AGENT_REPO` on `sys.path` |
| 5 | Agent half: `schemas`, `tools`, `__init__`, skill, `plugin.yaml` | 3, 4 | `hermes plugins validate` is clean. In a fresh Desktop session the model calls a tool and the board row exists |
| 6 | Router: `plugin_api.py`, `manifest.json` | 3, 4 | Pydantic and 409 tests pass with `TestClient`. A real `ctx.rest` call works through Desktop auth |
| 7 | Pane, read only: follow focus, poll with `paneVisibility` | 6 | the board of the focused chat shows. A node `vm` smoke test passes |
| 8 | Pane writes and event subscription | 7 | check, add, edit, delete work. The agent write appears in under 1 s |
| 9 | Hooks: `pre_llm_call`, `post_compaction`, `on_session_delete` | 3, 4 (5 to see it live) | Theo's edit shows in the agent's next turn as a delta. Compaction re-injects once |
| 10 | Picker, cross-session read and copy, markdown import and export | 6, 8 | another board opens. `tasks_board_copy` copies |
| 11 | Rotating-compression and branch cases | 4, 9 | fake-lineage tests pass. One manual `in_place: false` run is optional |
| 12 | Deploy: devpc symlink and enable, restart, `plugin.js` on Mac and Windows, `/meta` handshake | all | both Desktops show the pane against the new backend |

Steps 5 and 6 can run in parallel after 4. Step 9 can start after 3 but is only provable once 8 exists.

## Patterns to follow

1. **One write path.** Tool, route and hook call the service. The service owns the actor, `base_rev`, the journal and the event.
2. **Thin edges.** `plugin_api.py` maps HTTP to a service call and the error to a status code. `tools.py` maps arguments to a service call and the result to JSON.
3. **Lazy Hermes imports inside `core`.** Tests run with no Hermes on the path. Contract tests with `@pytest.mark.hermes` run against the real checkout (STACK.md).
4. **Python tests load `plugin_api.py` by file path with a fake `hermes_constants`.** Pattern: `HP/hermes-memory-ui/tests/test_plugin_api.py:11-25`.
5. **Poll as the guarantee, event as the accelerator.** One `useQuery` per board. `invalidateQueries` on the event. `refetchInterval: 4000` only while `paneVisibility` is true.
6. **Every response and every agent-visible text carries `rev`.**

## Anti-patterns to avoid

| Anti-pattern | Why bad | Instead |
|--------------|---------|---------|
| A Python `threading.Lock` as the only guard | Several `serve` processes and the gateway share the file | SQLite `BEGIN IMMEDIATE` |
| Reading `state.db` with raw `sqlite3` | Private schema, guards, writer rules | `SessionDB(read_only=True)` public methods |
| `async def` routes that call SQLite | Blocks the gateway loop for every client | plain `def` routes |
| `ctx.socket` for live update | No-op on OAuth remotes | `ctx.onEvent` plus polling |
| Injecting the full board on every turn | Replayed forever, burns the cache and tokens | Delta only when `rev > agent_seen_rev` |
| A dynamic system prompt section with board text | Frozen per session, breaks the cache rule if rebuilt | `pre_llm_call` delta |
| Model-supplied id for the current board | The model can write to another session | `session_id` kwarg only. Other boards use `other_session_id` |
| Deleting a board on `archive` | An archived session can return | Delete on `delete`, `empty_sweep`, `prune`, `ghost_prune` only |
| `focusedSessionId` in the pane | Runtime id, unknown to the server | `focusedStoredSessionId` |
| Relative import in `plugin_api.py` | No package context | `load_core()` |
| Hardcoded colours | Break themes | `var(--ui-*)` vars (`sdk-doc:1679-1685`) |
| Touching `todo_list` | Out of scope per PROJECT.md | Separate toolset and tool names |

## Scalability

One user, a few dozen boards. The limits exist to protect the prompt and the pane, not the database.

| Concern | Limit |
|---------|-------|
| Items per board | 200 |
| Item text | 500 characters |
| Subtask depth | 1 or 2 levels (discuss) |
| Journal rows per board | 100 |
| Delta injection | 20 lines, about 1200 characters |
| Full board injection | 40 items, 2000 characters |
| Poll | 4 s, pane visible only, `since_rev` makes the reply tiny |
| Tool result | full markdown, same caps as the full board injection |

## Deployment seams (for the last phase)

- Python half: symlink the package dir into `~/.hermes/plugins/hermes-session-tasks`, `hermes plugins enable hermes-session-tasks` (never hand edit `plugins.enabled`), restart every `hermes serve` and announce it first, it drops live Desktop connections. Tools register at load. A mid-run enable shows tools "next session" (`HA/plugins/AGENTS.md:90-96`).
- Desktop half: `$HERMES_HOME/desktop-plugins/hermes-session-tasks/plugin.js` on each Desktop machine. Folder name must equal the plugin `id` (`sdk-doc:87-90`). Do not also install a package copy on the same machine: two folders with one id load first-wins (`sdk-doc:2021-2023`). For a linked checkout, Desktop watches and hot reloads it (`sdk-doc:1732-1755`).
- Version skew: `GET /meta` returns `{api: 1, version}`. The pane shows a one-line notice if its own `API_VERSION` differs.

## Open questions for discuss-phase

Each has a recommendation. They are short on purpose.

1. **Subtask depth.** Recommend two levels (item, subtask). Schema has `parent_id` either way. Deeper needs a deeper markdown parser and UI.
2. **Branch behaviour.** Recommend a lazy copy of the parent board on first use (above). Alternative is an empty board.
3. **Board lifecycle on delete and archive.** Recommend delete on delete and prune, keep on archive.
4. **Desktop half install on Mac and Windows.** Needs Theo's choice: git install from the private GitHub repo (needs auth on each machine) or a file copy. Recommend a `scp` or sync script that places one file, plus the `/meta` check.
5. **Tools on non-Desktop platforms.** The plugin toolset is on for every platform by default (`tools_config.py:527-534`). Recommend no `check_fn` in v1 and a note in the skill. Telegram boards would have no pane.
6. **Picker behaviour.** Recommend the picker view is temporary and resets when chat focus changes.
7. **Item id syntax in agent markdown.** Recommend a trailing `{#a3}`. Export and import for Theo use plain markdown with no ids.
8. **Profiles.** `ctx.rest` uses the active profile, not the focused session's profile (`plugins.ts:79-85`, `sdk-doc:1073`). Only a `default` profile has real chats today (`~/.hermes/profiles/` holds one agent profile). Recommend ignoring this in v1.

## Verify during build (not settled by reading)

- A fresh Desktop session lists the `session_tasks` tools (toolset default, `known_plugin_toolsets`).
- `agent._parent_session_id` meaning for delegate children (`HA/agent/agent_init.py:1205`): the hook should skip subagent turns. Check with a real delegate run.
- `platform` value Desktop sessions report to `pre_llm_call`.
- Hot mount versus restart on the first enable.
- Pane id string for `paneVisibility` on the installed Desktop build.

## Sources

All paths are local and were read on 2026-10-30. HIGH confidence unless marked.

- `HA/hermes_cli/plugins.py:108-203,461-499,943-989` (hooks, `register_tool`, `register_hook`, system prompt section)
- `HA/hermes_cli/plugins_content.py:22-52` (`register_skill`)
- `HA/hermes_cli/plugins_loader.py:700-754` (agent half import, package context)
- `HA/hermes_cli/plugins_dispatch.py:41-55,164,256-294,358` (hook bounds, context copy)
- `HA/tools/registry.py:946-974,1086-1096` (dispatch, kwarg narrowing)
- `HA/model_tools.py:823-839`, `HA/agent/tool_executor.py:1721-1727`, `HA/agent/agent_runtime_helpers.py:2568` (where `session_id` comes from)
- `HA/agent/turn_context.py:108-132,799-853,1179` (`pre_llm_call` collect and inject)
- `HA/agent/prompt_builder.py:1200-1226` (plugin skills in the index)
- `HA/hermes_cli/web_server_dashboard.py:524-596,798-811,937-956,1032-1195` (manifest, gating, hot mount, mount)
- `HA/hermes_cli/web_server.py:398-480` (runtime gate, auth middleware, token seam)
- `HA/hermes_cli/plugin_events.py` and `HA/tui_gateway/server.py:717-778` (broadcast)
- `HA/apps/desktop/src/api/plugins.ts:44-137` (`pluginRest`, `pluginSocket`)
- `HA/apps/desktop/src/sdk/index.ts:609,1729-1803,1873,1895,2004-2008` (exports)
- `HA/apps/desktop/src/store/session-focus.ts:90-92`, `HA/apps/desktop/src/contrib/events.ts:31-45`
- `HA/hermes_state_common.py:170-175`, `HA/hermes_state_compression.py:882-912`, `HA/hermes_state_messages.py:1667-1693,1745-1749,1878-1899`, `HA/hermes_state_sessions.py:1151,1286-1287,1535-1556`, `HA/hermes_state.py:582`
- `HA/hermes_cli/config_defaults.py:695-700,1019`, `HA/agent/agent_init.py:1582-1584`
- `HA/plugins/plugin_storage.py`, `HA/hermes_cli/sqlite_util.py:18-67`, `HA/hermes_cli/plugin_validate_private_imports.py:38`
- `HA/hermes_cli/tools_config.py:527-534`, `HA/plugins/AGENTS.md:80-108`, `HA/AGENTS.md:20-21`
- `sdk-doc` lines 172-262, 279-283, 1061-1182, 1630-1700, 1732-1775, 1820-1930, 2013-2026
- `plug-doc` lines 732-787, 877-881, 1165-1210 (stale line 1201), 1505-1560
- `hooks-doc` lines 474-475, 678-715, 1086-1135
- `HA/website/docs/developer-guide/context-compression-and-caching.md:329-338`, `session-storage.md:162-215`
- Live evidence: `ps` and `/proc/342192/{exe,maps}` on devpc, 2026-10-30 (MEDIUM: a snapshot, the install can change on `hermes update`)
- `HP/hermes-memory-ui/` (`plugin.yaml`, `dashboard/manifest.json`, `__init__.py`, `desktop/plugin.js`, `tests/`) and `HP/gsd-status-api/` (`dashboard/manifest.json`) as the installed analogs
