# Pitfalls Research

**Domain:** Hermes Agent + Hermes Desktop unified plugin (Python tools, hooks, FastAPI router, plain ESM pane) that gives each session a task board
**Researched:** 2026-10-30
**Confidence:** HIGH for facts read from local source or observed on devpc. MEDIUM for agent-behaviour risks (not measured yet).

Evidence tags: **[V]** read in local source or observed on devpc today. **[D]** stated in docs only. **[I]** inferred, verify in the named phase.
Paths starting `hermes-agent/` mean `~/.hermes/hermes-agent/`.

## Fact check of PROJECT.md (read this first)

Two facts in PROJECT.md (and in STACK.md) are wrong or stale. Fix them before planning.

| PROJECT.md says | Finding | Effect on the plan |
|-----------------|---------|--------------------|
| "The gateway runs Python 3.11 (`~/.hermes/hermes-agent/venv`)" | **Wrong for the live process.** The two running `hermes serve --isolated` processes (pids 342192 and 342636) have `/proc/<pid>/exe` pointing at `~/.hermes/tools/python-3.14.9+20261021-linux-x64/bin/python3.14`. Their site-packages sit under `~/.hermes/installs/33051a290b175956/environments/.../venv/lib/python3.14`. Plugin `__pycache__` dirs hold 23 `cpython-314` files against 5 `cpython-311` files. The 3.11 venv still exists. fastapi 0.133.1 and pydantic 2.13.4 are the same in both. [V] | Code must run on 3.11 and 3.14. Test on both. See P8. |
| "Backend routes mount only when `hermes serve` starts. A Desktop reconnect reuses the old gateway, so new routes need a gateway restart." | **Half true.** `hermes_cli/web_server_dashboard.py:1032-1120` hot-mounts a newly enabled plugin on its first request. It never re-imports a plugin that is already mounted. So the first mount is free, but every later edit to `plugin_api.py` needs a restart. [V] | See P12 and M1. |
| "`broadcast_plugin_event` pushes to every connected Desktop window" | True only for the one serve process that made the call. Each Desktop SSH connection owns its own `hermes serve --isolated` process (`--ssh-session-token-file`, `--ssh-owner-nonce`). [V] | Live push never crosses processes. Polling is the real sync path. See P6 and M9. |
| "Deploy on devpc by symlink into `~/.hermes/plugins/`" | Delivers the Python half only. Desktop never runs on devpc (`~/.hermes/desktop-plugins/` does not exist on devpc). The Mac and Windows clients need their own copy of `desktop/plugin.js`. [V] [D] | See P7. |
| "Tool handlers can declare `session_id`" | True. The value is `Optional[str]` and can be `None` or empty. [V] | See P5. |
| "Plugin skill ... not listed in the system prompt" (plugin guide, `plugins/index.md` "Bundle skills") | **Docs are stale.** `agent/prompt_builder.py:1200-1230` puts every enabled plugin skill (name plus description) into `<available_skills>`. The body still loads only through `skill_view`. [V] | See P10. |

## Critical Pitfalls

### P1: Injecting the board into every turn (cache cost and stale copies)

**What goes wrong:**
`pre_llm_call` context is appended to the current user message, then saved in the row's `api_content` sidecar and replayed byte for byte on every later request while that row stays in context. A 1.5 KB board injected on turn 40 means 40 copies in the prompt, and 39 are stale. The model then sees an old board next to the new one and acts on the wrong one. Write tools have the same flaw: each write returns the full board, and every result stays in history.

**Why it happens:**
The docs say "injection is ephemeral". That is true for the stored message content, but the sidecar replays the injected text. The core comment says it plainly: a composed block is "replayed verbatim on every later request for as long as that row is in context, so each duplicate is paid once per turn, forever" (`hermes-agent/agent/memory_context.py:126-131`). `compose_user_api_content` says "what turn N sends is what turn N+1 replays" (`agent/turn_context.py:122-130`). [V]

**How to avoid:**
1. Inject a **delta only**: a one-line fenced note when Theo changed the board since the agent last saw it. Cap it at about 600 characters or 10 items. Above the cap, send a pointer ("Theo edited the board, revision 14, call X to read it").
2. Store `agent_seen_revision` per board in SQLite, not in memory. Advance it when the hook delivers a note and when the agent reads the board with a tool. This also covers resumed sessions and the first turn after compaction, where `is_first_turn` is false (`is_first_turn = not bool(conversation_history)`, `turn_context.py:818`).
3. Return nothing when the revision is unchanged. Return nothing when the board is empty and the agent never touched it.
4. Make write tools return a compact result: new revision, item count, and the changed items only. Give the full markdown only on an explicit read call. This overrides the PROJECT.md line "Each write returns the full board as markdown".
5. Keep every tool description and schema static. Never put session ids, item counts or board text into a schema or enum. Core rule: "Mutating past context, swapping toolsets ... mid-conversation breaks the cached prefix" (`hermes-agent/AGENTS.md:20-23`). [V]
6. The hook output cap is 10,000 characters. Above it, Hermes spills the text to `$HERMES_HOME/hook_outputs/<session_id>/<uuid>.txt` and shows a head and tail preview. A big board would reach the model cut in half. The delta rule avoids this.

**Warning signs:**
`approx_input_tokens` in `pre_api_request` grows faster than the transcript. The same checklist text appears in many user rows. Files appear in `$HERMES_HOME/hook_outputs/`.

**Phase to address:** hooks (rule 1 to 3, 6), tools (rule 4, 5).

---

### P2: The board loses its session when compression rotates the session id

**What goes wrong:**
Compression ends the session and starts a child with a new id. The tool `session_id`, the hook `session_id` and the Desktop `focusedStoredSessionId` can each hold a different member of the same lineage. A board keyed by the raw id vanishes after compression, or the pane and the agent write to two different boards.

**Why it happens:**
`pre_llm_call` fires after compression, so its `session_id` is already the child (`hooks.md` "Fires"). The Desktop itself had to solve this: colours and pins are keyed on the durable lineage root "so a color survives auto-compression's session-id rotation" (`apps/desktop/src/store/session-color.ts:9-12`), and it keeps a `lineageAliases` index (`src/store/session.ts:461-530`). `$focusedStoredSessionId` is only "the stored id of the session the user is working in" (`src/store/session-focus.ts`). It may be a tip or a root. [V]

**How to avoid:**
1. Do not key by session id. Use `board(id uuid, revision)` plus `board_alias(session_id PRIMARY KEY, board_id)`.
2. Resolve any session id to a board in one function. Order: alias lookup, then a lineage lookup through one adapter module (`SessionDB.get_compression_lineage`, `hermes-agent/hermes_state_compression.py:914`), then "no board".
3. Learn new aliases from the documented `post_compaction(session_id, old_session_id)` hook, and also lazily on any access. The hook is process-local and misses compaction in other processes (`hooks.md` "Fires"). `old_session_id` is `""` when compaction happens in place.
4. Create a board on the first **write**, never on a read. Reads of unknown sessions return an empty board without a row.
5. The REST API accepts any session id and returns the canonical `board_id`. The pane never assumes its focused id equals the agent's id. The broadcast payload carries `board_id` and `revision`. The pane invalidates all board queries on any event. It never filters by id equality.
6. `SessionDB` is a core internal. The Sep 2026 decomposition removed old import paths and "internal import paths were never part of the plugin contract" (`plugins/index.md` "Sep 2026 module decomposition"). Keep the import in one `lineage.py` with a try/except fallback, and add a test that runs against the live hermes-agent checkout. [D]

**Warning signs:**
The board is empty after a long session. Two boards exist for one conversation. Rows in `board_alias` grow with one row per session you never wrote to.

**Phase to address:** store (schema and resolver), hooks (`post_compaction`), api (canonical id in responses), pane (never compare ids).

---

### P3: Branches and resets are not compression lineage

**What goes wrong:**
A naive parent walk puts a `/branch` copy on the same board as its parent. Edits in the branch then change the parent's board. Or a lineage-only lookup gives the branch an empty board and Theo thinks the items are gone.

**Why it happens:**
Core separates the cases. `_resume_lineage_ids` follows only verified compression hops and returns the session alone for "an explicit /branch copy, an API fork, a reset child, or a plain session". The raw walker `_session_lineage_root_to_tip` "crosses fork/reset boundaries and misclassifies API forks" (`hermes-agent/hermes_state_messages.py:1667-1690`). A branch "owns a copied transcript" (`_is_explicit_branch_session`, line 1692). A reset fork of a compression-ended parent "is its own conversation" (`hermes_state_compression.py:904-908`). [V]

**How to avoid:**
1. Use `get_compression_lineage` semantics (compression only) for aliasing. Never walk `parent_session_id` yourself.
2. Decide in discuss: a branch gets a **copy** of the parent board on its first touch, with `forked_from` recorded. Do not share the board. Do not start it empty.
3. A `/new` or reset session starts empty.
4. Delegated subagents carry `parent_session_id` in hook kwargs. Decide whether a subagent write goes to the parent board or is refused. Do not let it create a board under the child id. [I]

**Warning signs:**
A write in a branch shows up in the parent pane. A branch pane is empty although the parent has items.

**Phase to address:** store (fork copy), hooks (first-touch copy).

---

### P4: Trusting a model-supplied session id

**What goes wrong:**
The model passes `session_id` in tool arguments, or a handler falls back to `""` when the kwarg is missing. Items land on the wrong board, or on a board keyed `""`.

**Why it happens:**
`_CallIds.session_id` is `Optional[str]`. `_execute_tool` passes it raw: `{"task_id": ids.task_id, "session_id": ids.session_id}` (`hermes-agent/model_tools.py:640-650, 827`). Hermes forwards only the keywords a handler names, so a handler written `def h(args)` or wrapped by a decorator never sees it (`tools/registry.py:954-962, 1086-1096`). Calls that arrive through `ctx.dispatch_tool`, MCP or `execute_code` may carry no session. [V]

**How to avoid:**
1. Declare `session_id` in every handler signature, plus `**kwargs`.
2. If it is `None` or empty, return an error JSON and write nothing.
3. **No write tool takes a target-session argument.** Only the cross-session read and copy tools take one, and they name it `source_session` so it never reads like the current session. Copy always writes into the current board.
4. Resolve a model-supplied source session by exact id or unique prefix (`SessionDB.resolve_session_id`). Return a clear error on no match or an ambiguous match.

**Warning signs:**
A board with key `""` or `None`. A test that calls the handler without `session_id` does not fail.

**Phase to address:** tools.

---

### P5: Lost updates between the agent, the pane, and several processes

**What goes wrong:**
The agent and the pane write at the same moment. One write overwrites the other. Or two processes each hold a "safe" in-process lock and both write.

**Why it happens:**
Process reality on devpc today [V]:
- Each Desktop SSH connection starts its own `hermes serve --isolated` process. Two run now.
- `hermes chat`, cron and the TUI are more processes. `broadcast_plugin_event` from them reaches nobody (`desktop-plugin-sdk.md` caller table).
- `plugin_api.py` loads as module `hermes_dashboard_plugin_<name>` through `spec_from_file_location` (`web_server_dashboard.py:1169-1175`). `__init__.py` loads as `hermes_plugins.<slug>` (`plugins_loader.py:701-740`). A shared helper module is imported **twice** as two objects, so a `threading.Lock` in it is not shared even inside one process.

**How to avoid:**
1. Keep no state in memory: no cache, no lock, no module-level connection. SQLite in WAL mode is the only shared state. Use `plugins.plugin_storage.plugin_db` (WAL, 5000 ms busy timeout, "a dashboard reader and a tool writer coexist").
2. Open one connection per operation and close it. `plugin_db` sets `check_same_thread=False` and says "caller owns transactions". One shared connection used by two threads mixes their transactions.
3. Write with `BEGIN IMMEDIATE`, or one atomic statement: `UPDATE ... SET revision = revision + 1 WHERE board_id = ? AND revision = ?`. Check `rowcount`.
4. Use **id-addressed operations** for both the agent and the pane (add item, set checked, rename item id, delete item id, move). They rarely conflict, and the revision bump stays inside the same transaction. A whole-board replace (markdown import) requires `expected_revision`.
5. **Never offer the agent a "replace the whole list" operation.** The built-in `todo_list` has `merge=false` by default, "replace the entire list" (`hermes-agent/tools/todo_tool.py` schema). That is how an agent erases Theo's items.
6. Return a stale or conflict result as an HTTP 200 body such as `{"ok": false, "conflict": true, "board": {...}}`. Do not use a 4xx. The Desktop surfaces a REST failure as a plain `Error` whose message is `"<status>: <body>"` plus a `statusCode` field (`apps/desktop/electron/api-transport.test.ts:357-374`). Parsing a body out of that string is fragile. [V for source, I for the exact string]
7. Use JSON files? Do not. `fcntl.flock` would work on one Linux host, but a whole-file rewrite loses data without a CAS and adds nothing over SQLite.

**Warning signs:**
`database is locked` in `errors.log`. A checked item un-checks itself. A test that runs two writers in two processes is missing.

**Phase to address:** store (schema, CAS, per-op connection), api (conflict shape), tools (id-addressed ops).

---

### P6: Live updates that only reach one process

**What goes wrong:**
The agent writes in the Mac's backend process. The Windows Desktop never hears about it. The board looks frozen until Theo reopens the pane.

**Why it happens:**
`broadcast_plugin_event` goes through `tui_gateway.server._broadcast_global_event` in the calling process only. It is fire-and-forget, and with no gateway in the process it logs a warning and returns (`hermes-agent/hermes_cli/plugin_events.py:66-88`). Each Desktop is attached to a different process (see P5). `ctx.socket` delivered 48 frames over an SSH remote on the MacBook, but the Windows client was not tested (`deploy-dash/docs/hermes-plugin-sdk.md`, "Desktop half"). `host.onEvent('plugin.<id>.<event>')` was not tested over SSH at all. [V] [I]

**How to avoid:**
1. Polling is the contract. Use `useQuery` with `refetchInterval` near 5 s, backing off to 15 s then 30 s after repeated failures, and pause while the pane is hidden (`host.paneVisibility(paneId)`). The SDK says not to poll faster than a few seconds.
2. Make the poll cheap: `GET /boards/{id}/revision` returns one integer. Fetch the body only when the revision moved.
3. The broadcast is a speed-up. Wrap it in try/except so a broadcast error never fails a write. Keep the payload tiny (`board_id`, `revision`). Every connected window gets it, so never put item text in it.
4. In the first spike, prove the event reaches the Mac and the Windows client, from a tool call and from a REST write.

**Warning signs:**
The pane updates on the machine that started the session and not on the other one.

**Phase to address:** api (revision endpoint, safe broadcast), pane (polling and backoff).

---

### P7: The desktop half never leaves devpc

**What goes wrong:**
The symlink makes the Python half work. The pane never appears on the Mac or Windows clients. Later, a client holds an old copy of `plugin.js` that talks to a newer backend.

**Why it happens:**
The SDK doc: "The copy is local to the machine the desktop app runs on. Against a remote backend, the remote box's `~/.hermes/plugins` is not reachable as a filesystem." The package must be installed on the remote host, and the desktop half installed separately on the client (`desktop-plugin-sdk.md` "Developing a unified package", note). `~/.hermes/desktop-plugins` does not exist on devpc. The sibling project `deploy-dash` met this and ships one copy script per client type. It uses `scp -O` because "Tailscale SSH has no SFTP subsystem". It copies the file instead of symlinking because hot reload through a symlink is untested (`deploy-dash/docs/hermes-plugin-sdk.md` "Install targets"). [V] [D]

**How to avoid:**
1. The deploy phase lists three installs: the devpc Python half, the Mac copy, the Windows copy. A feature is not deployed until the pane renders on each client.
2. Folder name on the client equals the plugin `id` (`hermes-session-tasks`).
3. Return `api_version` in every REST response. The pane compares it with its own constant and shows "update the desktop plugin on this machine" on a mismatch.
4. Keep the REST contract additive. Old clients must keep working after a backend upgrade.
5. Two enable switches exist and both can be off: `plugins.enabled` on devpc, and the Capabilities > Plugins toggle on each client. Check both on each machine.

**Warning signs:**
`ctx.rest` calls work from `curl` on devpc but no pane shows on a client. The pane shows old behaviour after a backend change.

**Phase to address:** deploy (three installs, version handshake), pane (version banner).

---

### P8: Testing only on Python 3.11

**What goes wrong:**
Tests pass on 3.11. The live gateway runs 3.14.9 and a 3.14 difference breaks the plugin at load, for example a pydantic model with a string annotation that cannot resolve.

**Why it happens:**
See the fact check. STACK.md and PROJECT.md both name 3.11. The live processes run 3.14.9. Hermes accepts `>=3.11,<3.15` (`hermes-agent/pyproject.toml:15`, quoted in STACK.md). The sibling project hit 3.14 differences: lazy annotations, `asyncio.get_event_loop()` raising without a running loop, forkserver as the multiprocessing default (`deploy-dash/.planning/research/PITFALLS.md` "Moderate 12"). [V]

**How to avoid:**
1. Run the unit tests on both interpreters: `~/.hermes/hermes-agent/venv/bin/python` (3.11.16) and `~/.hermes/tools/python-3.14.9+20261021-linux-x64/bin/python3`.
2. Pin the dev group to the gateway's versions: fastapi 0.133.1, starlette 1.3.1, pydantic 2.13.4, httpx 0.28.1. An unpinned `uv` resolve gave fastapi 0.142 and starlette 1.7 in the sibling project.
3. No syntax newer than 3.11. Define pydantic models at module level. The loader registers the module in `sys.modules` before `exec_module`, so string annotations resolve.
4. Before every release, check the real interpreter: `readlink /proc/<serve pid>/exe`. Do not trust a doc.
5. Run concurrency tests on an interpreter that links SQLite 3.51.3 or newer. System `python3` links 3.40.1, and Hermes then downgrades the journal mode to DELETE (STACK.md; `hermes_cli/sqlite_runtime.py:23`). Both gateway interpreters link 3.53.1. [V]

**Warning signs:**
`errors.log` shows `Failed to load plugin hermes-session-tasks API routes` after a Hermes update.

**Phase to address:** store and api (test matrix), deploy (interpreter check).

---

### P9: The agent barely uses the board because plugin tools are deferred

**What goes wrong:**
The agent lists items in chat and never calls the board tools. The pane stays empty. The core value fails silently.

**Why it happens:**
Tool search is on by default (`tools.tool_search.enabled: auto`). Any tool that is not core and not in a client-surface toolset is **deferrable**, so plugin tools are replaced in the tool array by three bridge tools: `tool_search`, `tool_describe`, `tool_call`. The model sees only a manifest of names and descriptions, limited to `min(4000 tokens, 5% of context)`. It degrades to names only, then to a bare bridge, as more MCP and plugin tools exist (`hermes-agent/tools/tool_search.py:1-6, 150-171`; `hermes_cli/config_defaults.py:2005-2040`). Core measured the cost of deferral: deferring `clarify` dropped structured-clarify use from 18 of 18 to 7 of 18, so "the ask-the-user affordance must be ambient" (`tool_search.py:143-148`). `todo_list` is itself on the default defer list. [V]

**How to avoid:**
1. Put the trigger in the first words of each tool description: "Theo's checklist in the Desktop pane. Use when you list things for Theo to do or remember." The manifest may show only that.
2. Use few tools (3 or 4, for example read, change, cross-session read, copy). Each extra name costs manifest budget. This follows the "narrow waist" rule in `hermes-agent/AGENTS.md:24-26` and the one-tool read/write shape of `todo_list`.
3. Use a distinctive name prefix and plain words the agent would search for ("checklist", "list for Theo").
4. Measure in the tool phase: start a fresh Desktop session, ask for a to-do list, and record whether the agent calls the board tool. Repeat with 5 prompts. If the rate is low, raise it with Theo as a cost question: `tools.tool_search.enabled: off` makes every tool eager for every session.
5. Check that the toolset is on for the Desktop platform. Saving `hermes tools` writes `known_plugin_toolsets`. A toolset not in the saved list is then off (`hermes_cli/tools_config.py:528-535`).
6. A plugin enabled mid-run adds its tools to the **next session** only (`plugins/index.md` "Mid-run plugin loading"). Test in a new session.

**Warning signs:**
The agent writes a markdown checklist in chat. The transcript shows `tool_call` bridge entries or none.

**Phase to address:** tools (descriptions, count, measurement), skill, deploy (toolset check).

---

### P10: Behaviour rules live only in the skill, and the agent uses the board wrongly

**What goes wrong:**
The agent uses the board as its own scratch plan, or confuses it with `todo_list`, `memory` or the `kanban_*` tools. It deletes or rewrites Theo's items without asking. Or it asks about every tick and annoys Theo.

**Why it happens:**
- The skill body loads only after a `skill_view` call. The index shows just name plus description, and it is frozen into the cached system prompt at session start (`agent/prompt_builder.py:1200-1230`). The docs claim plugin skills are not indexed. The code says they are. Use the code. [V]
- Neighbours overlap. `todo_list` says "Use ... when the user provides multiple tasks" (`tools/todo_tool.py` schema). `memory` owns the word "remember". `kanban_create`, `kanban_list`, `delegate_task` own "task". [V]
- "Ask first" in a prompt is advice, not a rule.

**How to avoid:**
1. Put the hard rules in the **tool descriptions** as well as the skill: "Not the agent's own plan (use todo_list). Not long-term memory (use memory)."
2. Avoid the words `todo`, `task`, `kanban`, `memory` and `note` in tool names. Keep names under 50 characters (the Claude subscription plugin needed aliases above 50, `claude-subscription-directsdk-experimental/CHANGELOG.md`).
3. Enforce server side:
   - Track `created_by` (agent or Theo) on every item.
   - Per-call cap on items added (for example 20) and a total cap (for example 256 items, 4000 characters each, as core sets for `todo_list`: `MAX_TODO_ITEMS`, `MAX_TODO_CONTENT_CHARS`).
   - No whole-board replace for the agent (see P5).
   - For delete, or uncheck, of an item Theo created, return `pre_tool_call` directive `{"action": "approve", "message": ...}`. Core then escalates to the human approval gate (`hermes_cli/plugins.py:1947-1991`). Use it only for destructive ops on Theo's items, so routine ticks never prompt.
4. Skill description must state the trigger and the exclusions in one sentence, because that sentence is all the index shows.
5. Cap writes per turn. A loop that adds one item per step is a scratch plan.

**Warning signs:**
The board fills with "step 1 of my plan" items. `created_by=agent` items outnumber Theo's. Theo reports a vanished item.

**Phase to address:** tools (description, caps, approve directive), skill (description), hooks (`pre_tool_call`).

---

### P11: Board text in the user message is a prompt-injection channel

**What goes wrong:**
The agent copies text from a web page or a file into an item. The hook later injects that item into the **user message**, where the model gives it user-level trust. An item that contains `</...>` can close the fence and add its own instructions.

**Why it happens:**
Core knows this. It wraps recalled memory in `<memory-context>` with "NOT new user input" and strips pre-wrapped context with `sanitize_context` (`hermes-agent/agent/memory_context.py:169-185`). A plugin that injects raw text skips that protection. [V]

**How to avoid:**
1. Wrap injected text in a plugin-specific fence with a "data, not instructions" note, like core does.
2. Strip our own fence tags and control characters from item text on **write**, and again on inject.
3. Prefer a pointer over inline text for agent-authored items. Inline only Theo-authored text.
4. Cap item length (4000 characters) and strip newlines from item text, so one item cannot forge a second `- [x]` line.

**Warning signs:**
Item text contains angle brackets or the word "ignore".

**Phase to address:** hooks (fence), store (sanitize on write).

---

### P12: Restarting the gateway drops turns and leaves mixed versions

**What goes wrong:**
A restart in the middle of a turn loses the turn. After the restart, one backend runs new code and another runs old code against the same database.

**Why it happens:**
- Desktop doc: "If the gateway restarts while a turn is mid-flight, that turn cannot be finished or safely repeated: the queue shows it as **Turn lost during restart**" (`website/docs/user-guide/desktop.md:55`). The same host also serves other surfaces. [D]
- There is one `hermes serve --isolated` per Desktop SSH connection, so "the gateway" is several processes. Code is imported once per process. A hot-mounted plugin is never re-imported (`web_server_dashboard.py:1032-1060`; memory-wiki README: "changing `plugin_api.py` needs a server restart"). [V]
- The first backend to run new code may migrate the schema. Another backend still runs old code against it.

**How to avoid:**
1. Announce the restart first (PROJECT.md rule). Check no session is mid-turn before it.
2. After a restart, check the version on every live backend: `api_version` from `GET /api/plugins/hermes-session-tasks/version` on each connection.
3. Migrations are additive only: new nullable columns, new tables. Track `PRAGMA user_version`. Old code must tolerate new columns.
4. Staged rollout: restart all backends, then update the client copies.

**Warning signs:**
The Mac pane shows a field the Windows pane lacks. `no such column` in `errors.log`.

**Phase to address:** deploy, store (migrations).

---

## Moderate Pitfalls

### M1: Docs and source disagree on route mounting

**What goes wrong:** A 404 from `ctx.rest` leads to an unneeded restart, or a code edit is never picked up.
**Evidence:** Hot mount on first request exists (`web_server_dashboard.py:1032-1120`). A route returns 404 before enable and works after the first request once `plugins.enabled` lists the plugin. A mounted plugin is never reloaded. [V]
**Prevention:** On a 404, check `plugins.enabled`, then `~/.hermes/logs/errors.log` for `Failed to load plugin <id> API routes`, then restart only if code changed. The pane maps 404 to "backend not loaded", never to an empty board.
**Phase:** api, deploy.

### M2: `plugin_api.py` cannot use relative imports

**What goes wrong:** `from . import store` raises `ImportError`, or the module loads twice (see P5).
**Evidence:** It is loaded by `spec_from_file_location` with no package context. Both installed backends are one file: `hermes-memory-ui/dashboard/plugin_api.py` (2742 lines) and `gsd-status-api/dashboard/plugin_api.py`. `memory-wiki` loads its core by path (`conftest.py` `_load_by_path`). [V]
**Prevention:** Put the domain code in one stdlib-only package. Both halves load it through one helper that checks `sys.modules` first and registers one module name. Hold no state in it, so a second copy would still be safe.
**Phase:** store.

### M3: Symlinks, `__pycache__` and the API file

**What goes wrong:** A symlinked `plugin_api.py` is refused. A repo gets dirty with pyc files.
**Evidence:** A symlinked plugin **directory** mounts. A symlinked **api file** is refused with `refusing unsafe api path` (spike in `deploy-dash/docs/hermes-plugin-sdk.md`; check at `web_server_dashboard.py:1155-1167`). `~/.hermes/plugins/gsd-status-api` is a symlink into a repo and holds `cpython-314` pyc files in that repo. Orca-status holds both 311 and 314 pyc files. [V]
**Prevention:** Symlink only the package directory. Add `__pycache__/` to `.gitignore`. Never symlink a file inside `dashboard/`.
**Phase:** deploy.

### M4: Enabling by hand, name mismatch, and scratch homes

**What goes wrong:** The plugin loads nowhere, or a "safe" test rebuilds the live install.
**Evidence:** `hermes plugins enable` nudges the running gateway (`reload-plugins`) and asks for capability consent. A hand edit skips both. Names must match across `plugin.yaml` `name`, `dashboard/manifest.json` `name`, the folder, the desktop `id` and the `broadcast_plugin_event` id (`[a-z0-9_-]{1,64}`, `plugin_events.py`). The sibling project found that running the `hermes` launcher with a scratch `HERMES_HOME` "starts a source-update repair that rebuilds the live Hermes install and rewrites its launchers". [V] [D]
**Prevention:** Use `hermes plugins enable hermes-session-tasks`. Validate with `hermes plugins doctor . --ci` (temporary home, network blocked, checks `**kwargs` and declared against registered tools and hooks). Never run `hermes` with a scratch home.
**Phase:** deploy.

### M5: Tool handler contract slips

**What goes wrong:** A dict return, an uncaught exception, or a missing keyword makes the call fail with an unhelpful error.
**Evidence:** `plugins/index.md` "Common mistakes": return a JSON string, accept `**kwargs`, catch exceptions. `registry.dispatch` wraps exceptions as `Tool execution failed: ...` (`tools/registry.py:942-975`). [V] [D]
**Prevention:** Return `json.dumps(...)` always. Return errors as `{"error": ..., "hint": ...}` with the current revision, so the model can recover. List every tool in `provides_tools`. Keep the hook `pre_llm_call(session_id, user_message, **kwargs)` and swallow all exceptions (return `None`), because the hook runs on the turn's critical path.
**Phase:** tools, hooks.

### M6: Desktop pane code rules

**What goes wrong:** The pane fails to load, renders nothing, or looks wrong after a theme switch.
**Evidence and prevention:**
- No JSX syntax. Use `jsx()` and `jsxs()` from `react/jsx-runtime`. `node --check` does not catch an unimported identifier, which is a render-time `ReferenceError`. Add a smoke test that renders the pane in a VM (the harness in `hermes-memory-ui/tests/desktop_plugin_smoke.mjs`). [D]
- Only three import specifiers. A named import of a missing SDK export stops the whole module (`desktop-plugin-sdk.md`, `WorkspacePageHeaderControl` note). [D]
- No hardcoded colours. Use `var(--ui-*)`. Leave the background alone. A test should reject `#`, `rgb(` and colour names. [D]
- **Verify every SDK name against `hermes-agent/apps/desktop/src/sdk/index.ts`, not against the SKILL.md.** `hermes-desktop-plugins/SKILL.md` lacks `jsxs` and `focusedStoredSessionId`. The sibling project logged every such gap in `docs/hermes-plugin-sdk.md`. Local check done today: `Checkbox`, `ScrollArea`, `EmptyState`, `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue`, `ContextMenu*`, `DropdownMenu*`, `useQuery`, `useMutation`, `queryClient` all exist. There is no `SelectGroup` or `SelectLabel` export. [V]
- `Checkbox` is a Radix button. It cannot sit inside another button (`components/ui/checkbox.tsx` comment on `CheckboxMark`). Make the row a div. [V]
- Tailwind v4 builds CSS from the app source (`src/styles.css`). A utility class that the app never uses may produce no style. Use common utilities, or an inline `style` object with `var(--ui-*)`, and check the look on the Mac build. [I]
- Subscribe with `ctx.onEvent` inside `register()`. A `host.onEvent` call made later (inside an effect or a timer) is not retired on hot reload (`sdk/index.ts:1366-1375`). Use `ctx.setInterval` and `ctx.setTimeout`. Keep no module-scope state: "ES modules can't be unloaded; a hot-edit loop stacks live copies". [V]
- Module evaluation has a 10 s deadline. No top-level `await`. [D]
**Phase:** pane.

### M7: The pane does not follow the focused chat, or writes to the wrong one

**What goes wrong:** Theo starts an inline edit, clicks another chat, and the edit saves into the new board. A slow reply for chat A repaints chat B.
**Evidence:** `focusedStoredSessionId` is tile-aware and falls back to the primary selection. It stays on the last chat while chrome (such as our pane) has keyboard focus (`src/store/session-focus.ts`). It is `null` for a new draft chat. The SDK says to read state imperatively in handlers, not from a render closure. The memory-ui project fixed the same class of bug: test `dashboard_forwards_profile_and_suppresses_stale_responses`. [V]
**Prevention:**
1. Include the board id in every query key. React Query then drops stale replies.
2. When an editor opens, capture `board_id` and `revision` in its local state. Send both with the write. The backend refuses a mismatch.
3. For `null`, show "Start the chat to use the board". Do not call the API.
4. Show the session picker's board read-only, with a clear banner and a "back to this chat" button. Writes go only to the focused chat's board.
**Phase:** pane, api.

### M8: Errors look like an empty board

**What goes wrong:** The backend is down or the plugin is not loaded. The pane shows "No items". Theo concludes the list was lost, or a later import replaces the real board.
**Evidence:** `ctx.rest` rejects with a string error. The SDK says the desktop half "degrades gracefully when the backend half is off". An older client copy and a missing mount both fail this way. [D]
**Prevention:** Keep the last good data on screen with a "stale" badge. Use `ErrorState` for a first-load failure. Disable import and bulk actions while the last fetch failed. Treat the board as unknown, not empty, until one fetch succeeds.
**Phase:** pane.

### M9: Closing the pane disables the plugin

**What goes wrong:** Theo closes the board tab. The plugin switches itself off, including any chip or command, and the board seems gone.
**Evidence:** "Closing the only pane contributed by a plugin disables that plugin" (`desktop-plugin-sdk.md` "Panes"). [D]
**Prevention:** Say so in the README. Name the fix: Capabilities > Plugins, or Reset layout. Optionally add a palette command and a status-bar chip with the open count, and check that they survive.
**Phase:** pane.

### M10: Data lifecycle: archive is not delete, hooks are not guaranteed

**What goes wrong:** Archiving a chat deletes its board, and un-archive finds nothing. Or a CLI prune in another process leaves orphan boards forever.
**Evidence:** `on_session_delete` also fires for `reason="archive"`, which keeps the transcript and can be undone. It fires post-commit, "process-local ... no exactly-once guarantee". `deleted_ids` includes "compression-chain links" (`hooks.md:1086-1112`). [D]
**Prevention:**
1. On `archive`, do nothing.
2. On `delete`, `prune` and the other delete reasons, remove the aliases for the ids in `deleted_ids` (or `session_id`). Delete the board only when no alias remains.
3. Add a sweep in the API (on pane open, at most once per hour): boards whose aliases all point to sessions missing from `state.db` for more than 7 days are removed. This covers missed hooks.
4. Caps: 256 items, 4000 characters per item, and a "clear completed" action. Core caps `todo_list` for the same reason, so a list does not "defeat the compression it rides through" (`tools/todo_tool.py:11-14`).
5. Create boards on first write only (P2), so cron and subagent sessions leave no rows.
**Phase:** store, hooks.

### M11: Markdown round trip loses ids and structure

**What goes wrong:** An import drops item ids, so agent references and CAS break. The agent addresses "item 3" and Theo has moved it. Tabs, CRLF, `[X]`, `*` bullets or a multi-line item break the parse.
**Prevention:**
1. Show short stable ids in the agent view, for example `- [ ] (a3) text`. Agent operations use ids only. Unknown ids return an error that lists the valid ones.
2. Import is a diff against the current board (match by id when present, else by text), not a wipe.
3. Accept `[x]`, `[X]`, `-`, `*`, tabs, 2 and 4 space indents and CRLF. Reject depth beyond the decided limit with a clear error.
4. Strip newlines inside an item on write (see P11). Test round trips with generated boards.
**Phase:** store (parser), tools (ids).

### M12: Profile scope and cached paths

**What goes wrong:** A path computed at import time points to the wrong profile. A background thread loses the profile and writes to the launch home.
**Evidence:** `plugin_data_dir` "resolves `get_hermes_home()` on every call so it follows the active profile - don't cache across profile switches". `plugins/AGENTS.md` says a provider "never caches `hermes_home` from `initialize()`". Memory-ui has regression tests `test_worker_thread_copies_request_context` and `test_profile_dependency_unwinds_context_on_cancellation`. Only the default profile exists on devpc today (no `~/.hermes/profiles/`). [V]
**Prevention:** Resolve the DB path per call. Use `asyncio.to_thread` (it copies the context), never a bare `threading.Thread`. Add one test that switches the home between two calls.
**Phase:** store, api.

### M13: Tests that cannot run outside the gateway

**What goes wrong:** Tests import `hermes_cli` at top level and fail under plain pytest, or they mock the wrong name and the real broadcast runs.
**Evidence:** `broadcast_plugin_event` raises `ValueError` for a bad event name and `TypeError` for a non-dict payload. With no gateway it logs a warning and returns. `plugin_storage` needs `hermes_constants` and `hermes_cli.sqlite_util`. The memory-ui tests inject a fake `hermes_constants` module and load `plugin_api` with `spec_from_file_location`. The memory-wiki `conftest.py` puts the hermes-agent checkout on `sys.path`. [V]
**Prevention:**
1. Keep one thin `storage.py` seam that takes a path. Tests pass `tmp_path`. Only the default resolver calls `plugin_data_dir`.
2. Import `hermes_cli.plugin_events` lazily inside the notify function. Patch `hermes_cli.plugin_events.broadcast_plugin_event` (the attribute your code reads at call time). Test three cases: the call receives `("hermes-session-tasks", "board.updated", {"board_id", "revision"})`, a raising broadcast does not fail the write, and no broadcast happens on a rejected stale write.
3. Use `fastapi.testclient.TestClient` (needs `httpx`) with the pinned versions from P8.
4. Add a gate that loads the real package through the live hermes-agent checkout: `hermes plugins doctor . --ci`.
5. Add a two-process write test (`multiprocessing` with `spawn`, since 3.14 defaults to forkserver) that checks no lost update.
**Phase:** store (harness first), api.

## Minor Pitfalls

### m1: Time stamps
**What goes wrong:** Naive local times sort wrongly across the Mac, the PC and devpc.
**Prevention:** Store UTC ISO 8601 with `Z`. Format in the pane with `fmtDateTime` or `relativeTime` from the SDK.

### m2: Codicon names
**What goes wrong:** A glyph name with no CSS rule renders blank (`deploy-dash/docs/hermes-plugin-sdk.md` "Codicon glyphs"). Use the SDK `icons` set, or check each name against `codicon.css`.

### m3: Skill name and index text are frozen per session
**What goes wrong:** An edit to the skill description or tool text appears only in new sessions. Skill names must match `[a-zA-Z0-9_-]+` and must not contain `:` (`plugins_content.py:23-36`).

### m4: Copy scripts
**What goes wrong:** `scp` fails on devpc because Tailscale SSH has no SFTP. Use `scp -O` (sibling finding).

### m5: Idle gateway kept awake by sockets
**What goes wrong:** Every plugin socket dial is gateway traffic (`apps/desktop/src/api/plugins.ts`, `MAX_REFUSED_PLUGIN_DIALS` comment). Not a problem for a few clients. Another reason to keep polling slow while the pane is hidden.

### m6: Cross-session reads
**What goes wrong:** The agent reads a board from a session in another platform (Telegram, cron). Allow only boards that exist. Return titles, not transcripts. Cap the number of boards listed.

## Technical Debt Patterns

| Shortcut | Immediate benefit | Long-term cost | When acceptable |
|----------|-------------------|----------------|-----------------|
| Key boards by the raw `session_id` | No alias table | Boards vanish at compression (P2) | Never |
| Inject the whole board each turn | Agent always "sees" it | Cache and token growth, stale copies (P1) | Never |
| Full board in every write result | Easy for the model | Same growth through tool results (P1) | Only for boards under about 10 items, if measured |
| JSON file per board | No schema | Lost updates, no atomic CAS (P5) | Never |
| Module-level lock or cache | Looks safe | Useless across processes and module copies (P5) | Never |
| Copy the SQLite connection to a global | Faster | Mixed transactions across threads (P5) | Never |
| Skip the Windows client check | Faster release | Pane may never load there (P7) | Only for a release that Theo confirms is Mac only |
| Hand-edit `config.yaml` to enable | Quick | Skips consent and the reload nudge (M4) | Never |
| Rely on the skill for rules | Less code | Rules not loaded (P10) | Never for destructive rules |

## Integration Gotchas

| Integration | Common mistake | Correct approach |
|-------------|----------------|------------------|
| `pre_llm_call` | Return board text each turn | Return a small fenced delta only when the revision changed (P1) |
| `post_compaction` | Trust it as the only alias source | Use it plus lazy lineage lookup (P2) |
| `on_session_delete` | Delete on `archive` | Ignore `archive`, sweep for orphans (M10) |
| `broadcast_plugin_event` | Put item text in the payload, let errors raise | Tiny payload, try/except, never required (P6) |
| `ctx.rest` | Expect headers, ETag or typed errors | Revision in the body, conflicts as 200 payloads (P5, P6) |
| `ctx.socket` / `host.onEvent` | Depend on them | Treat as a speed-up over polling (P6) |
| `plugin_db` | Share one connection | One connection per operation (P5) |
| `register_skill` | Assume the body is always in context | The index shows name and description only (P10) |
| Desktop SDK | Trust SKILL.md for names | Check `sdk/index.ts` (M6) |
| `pre_tool_call` | Use only prompt text to ask first | Return the `approve` directive for destructive ops (P10) |

## Performance Traps

| Trap | Symptoms | Prevention | When it breaks |
|------|----------|------------|----------------|
| Full board per turn | Rising input tokens | Delta injection (P1) | About 15 turns with a 1 KB board |
| Polling full bodies | Idle load on devpc | Poll the revision integer, pause when hidden (P6) | 3 clients polling every 5 s |
| Hook does slow I/O | Turn start lags | One indexed SELECT, no network, swallow errors (M5) | Any slow disk |
| `SessionDB` lineage walk on every call | Slow tool calls | Alias table first, walk only on a miss (P2) | Deep compression chains |
| Unbounded boards | Slow pane, big results | 256 items and 4000 characters (M10) | A few hundred items |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Raw item text in the user message | Prompt injection with user-level trust | Fence, sanitize, pointer for agent text (P11) |
| Model picks the target session | Writes to another board | No target argument on writes (P4) |
| Agent deletes Theo's items silently | Data loss | `approve` directive on destructive ops (P10) |
| Item text in broadcast payloads | Text reaches every connected window | Payload holds ids and revision only (P6) |
| REST accepts unbounded text or ids | Large rows, odd keys | Pydantic limits on length and count at the boundary, parameterised SQL only |
| Cross-session read with no limit | Reads boards of unrelated sessions | Existing boards only, capped list (m6) |

## UX Pitfalls

| Pitfall | User impact | Better approach |
|---------|-------------|-----------------|
| Empty state on error | Theo thinks items are lost | Stale badge and `ErrorState` (M8) |
| Edit lands in the wrong chat | Silent wrong data | Capture board id at edit start (M7) |
| Picker board is editable | Edits on a board Theo is not working in | Read-only banner with a back button (M7) |
| Closing the tab turns the plugin off | Pane gone, no obvious way back | README note, palette command (M9) |
| Agent ticks items Theo did not finish | Trust loss | Agent may check only items it can show evidence for. Ask when unsure |
| Agent asks about every change | Annoyance | Ask only for destructive ops on Theo's items (P10) |
| Pane shows a conflict as an error toast | Confusing | Merge silently when ops do not clash, show a small "updated by agent" mark |

## "Looks Done But Isn't" Checklist

- [ ] **Compression:** Works after `/compress` and an automatic compaction. Verify the board survives and the pane still shows it.
- [ ] **Branch:** A `/branch` session shows a copy, and edits do not touch the parent.
- [ ] **Resume:** An old session reopened days later: the agent learns about the board on its first turn (not only when `is_first_turn`).
- [ ] **Two clients:** Mac and Windows both show an agent write within one poll interval.
- [ ] **Two processes:** An agent write in process A and a pane write in process B both persist.
- [ ] **Client copy:** Each client holds the current `plugin.js` and the pane banner shows no version mismatch.
- [ ] **Python versions:** Unit tests pass on 3.11.16 and 3.14.9.
- [ ] **Backend down:** The pane shows a stale or error state, never an empty board.
- [ ] **Tool visibility:** In a fresh Desktop session the agent calls the board tool for 5 of 5 "list things for me" prompts.
- [ ] **todo_list boundary:** A multi-step coding task does not write to the board.
- [ ] **Token check:** Input tokens on turn 30 show no growth from board text.
- [ ] **Archive and delete:** Archive keeps the board. Delete removes it. An orphan sweep removes the rest.
- [ ] **Restart:** `plugins.enabled`, `hermes plugins doctor . --ci`, and the version endpoint pass on every live backend after the restart.

## Recovery Strategies

| Pitfall | Recovery cost | Recovery steps |
|---------|---------------|----------------|
| Board keyed wrong (P2, P3) | MEDIUM | Add alias rows from a one-off script that walks `state.db` lineage. Merge boards by alias, newest revision wins per item id. |
| Lost update (P5) | LOW | Keep an `item_history` or last 20 op log per board. Replay from it. |
| Items erased by the agent (P10) | LOW | Same op log. Add an "undo last agent change" action. |
| Stale client copy (P7) | LOW | Re-run the client copy script. The pane banner names the machine. |
| Mixed backend versions (P12) | MEDIUM | Restart all backends. Check `PRAGMA user_version`. |
| Orphan boards (M10) | LOW | Run the sweep with a dry run flag first. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention phase | Verification |
|---------|------------------|--------------|
| P1 Injection cost | hooks, tools | Token count on turn 30 equals the no-plugin baseline within 5 percent. Unit test: unchanged revision returns `None`. |
| P2 Compression lineage | store, hooks | Test: write, rotate the session id, read through the new id. |
| P3 Branch and reset | store, hooks | Test: fork copy. Reset starts empty. |
| P4 Session id trust | tools | Test: `None` id returns an error and writes nothing. Schema has no target on writes. |
| P5 Concurrency | store, api, tools | Two-process write test. Conflict returns 200 with the board. |
| P6 Live update reach | api, pane | Mac and Windows both update within one poll. Broadcast error does not fail a write. |
| P7 Desktop copy | deploy, pane | Pane renders on each client. Version banner test. |
| P8 Python versions | store, api, deploy | CI runs 3.11 and 3.14. `readlink /proc/<pid>/exe` recorded in the deploy log. |
| P9 Tool deferral | tools, skill, deploy | 5 of 5 prompt test in a fresh session. Toolset on for the Desktop platform. |
| P10 Behaviour rules | tools, skill, hooks | todo_list boundary test. Delete of a Theo item triggers approval. Caps enforced. |
| P11 Injection channel | hooks, store | Test: item text with a fence tag is stripped. |
| P12 Restart | deploy, store | Version endpoint on every backend. Additive migration test against the previous schema. |
| M1 Mount timing | api, deploy | A 404 maps to a "backend not loaded" state in the pane. |
| M2 Imports | store | `plugin_api.py` imports with no package context in a test. |
| M3 Symlink | deploy | Mounted from a symlinked dir. `.gitignore` has `__pycache__/`. |
| M4 Enable and names | deploy | `hermes plugins doctor . --ci` green. Names match in all five places. |
| M5 Handler contract | tools, hooks | Handlers return JSON strings. Doctor reports no missing `**kwargs`. |
| M6 Pane rules | pane | Static test: no `#`, `rgb(`, JSX, extra imports. VM smoke render. |
| M7 Focus and wrong chat | pane, api | Test: switch focus mid-edit. The write goes to the original board or is refused. |
| M8 Error as empty | pane | Kill the backend. The pane keeps old data and shows a badge. |
| M9 Closing disables | pane | README note. Palette command checked. |
| M10 Lifecycle | store, hooks | Archive keeps. Delete removes. Sweep removes orphans. |
| M11 Markdown | store, tools | Round-trip property test. |
| M12 Profile scope | store, api | Switch-home test. |
| M13 Test harness | store | Harness exists before the first feature test. |

**Research flags for phases:**
- **deploy:** needs a live spike. Confirm interpreter version, process count, three installs, and event delivery to the Windows client.
- **tools:** needs a measured prompt test (P9). The result may change the tool count or raise a `tool_search` question for Theo.
- **hooks:** confirm in a live session that `post_compaction` fires on Desktop and what a branch looks like in `state.db`.
- **store, api, pane:** standard patterns once the points above are fixed.

## Sources

Local source and docs (all under `~/.hermes/hermes-agent/` unless noted):
- `AGENTS.md:15-26` (prompt cache rule, narrow waist)
- `agent/turn_context.py:100-130, 799-835` and `agent/memory_context.py:120-185` (injection, replay, fencing)
- `website/docs/user-guide/features/hooks.md` (`pre_llm_call`, `on_session_delete`, `post_compaction`)
- `website/docs/developer-guide/plugins/index.md` (tool contract, hooks table, durable state, mid-run loading, decomposition notice)
- `website/docs/developer-guide/desktop-plugin-sdk.md` (Pitfalls, unified package, ctx.socket, panes)
- `website/docs/user-guide/desktop.md:55` (turn lost during restart)
- `hermes_cli/web_server_dashboard.py:480-640, 1002-1215` (mount, hot mount, symlink check)
- `hermes_cli/plugins_loader.py:701-740`, `hermes_cli/plugins_content.py:23-50`, `hermes_cli/plugins.py:1947-1991`
- `hermes_cli/plugin_events.py`, `plugins/plugin_storage.py`, `hermes_cli/sqlite_util.py`
- `hermes_state_messages.py:1667-1700`, `hermes_state_compression.py:895-945`, `hermes_state_sessions.py:1543`
- `model_tools.py:640-650, 800-830`, `tools/registry.py:942-975, 1086-1096`, `tools/todo_tool.py`
- `tools/tool_search.py`, `hermes_cli/config_defaults.py:2000-2040`, `hermes_cli/tools_config.py:520-535`
- `apps/desktop/src/sdk/index.ts`, `src/store/session-focus.ts`, `src/store/session-color.ts`, `src/store/session.ts`, `src/api/plugins.ts`, `src/components/ui/checkbox.tsx`

Installed plugins and sibling projects:
- `~/.hermes/plugins/hermes-memory-ui` (README caveats, `tests/test_profile_scope_regressions.py`, `tests/test_plugin_api.py`; git history is one commit, `8f79810 chore: bump plugin version to 0.6.4`)
- `~/.hermes/plugins/memory-wiki` (README line 88-89, `conftest.py`), `~/.hermes/plugins/orca-status`, `~/.hermes/plugins/claude-subscription-directsdk-experimental/CHANGELOG.md`
- `~/.hermes/plugins/gsd-status-api` (symlink to `local_repo/deploy-dash/hermes/plugins/gsd-status-api`) and its history (`git log` in deploy-dash: `fe003ae`, `25742b2`, `4f5b2c2`, `47bc3d6`, `4f6ad20`)
- `local_repo/deploy-dash/docs/hermes-plugin-sdk.md` and `.planning/research/PITFALLS.md` (spike results: symlink refusal, install targets, `ctx.socket` over SSH, scratch-home hazard)

Observed on devpc, 2026-10-30:
- `ps`, `/proc/342192/exe`, `/proc/342636/exe`, `/proc/342636/cmdline` (serve processes, interpreter)
- `~/.hermes/config.yaml` (`plugins.enabled`), `~/.hermes/logs/agent.log` ("Mounted plugin API routes")
- `find ~/.hermes/plugins -name '*.pyc'` (3.11 versus 3.14 counts)

---
*Pitfalls research for: Hermes session task board plugin*
*Researched: 2026-10-30*
