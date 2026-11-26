# Phase 3: REST router and client install spike - Research

**Researched:** 2026-10-31
**Domain:** Hermes v0.22.5 dashboard plugin routes (FastAPI), Desktop plugin SDK disk door, plugin event bridge, `pre_llm_call` hook
**Confidence:** HIGH on backend, hook and file-install facts (read from source and run on devpc). MEDIUM on event delivery to the Mac and the Windows PC (code read, never run on those machines).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)
- `pre_llm_call` delta of Theo's edits with `agent_seen_rev` - Phase 5.
- Session titles in the board list - Phase 6 (`board_sessions`).
- Git install dialog for the Desktop half - Phase 7, if the copy script proves awkward.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | REST routes under `/api/plugins/hermes-session-tasks/` read a board, list boards, apply item operations | Answer 1 (mount, auth, load), Pattern 1 (router), Pattern 2 (`load_core`), Code Example 1 |
| API-02 | Every write, tool or route, broadcasts `board.updated` with session id and revision | Answer 3 (wire frame run on devpc), Pattern 3 (events adapter, `after_write` signature change) |
| API-03 | Meta route returns backend version and API version | Answer 7 (version read), Code Example 4 |
| DEV-03 | Pane file passes `node --check` and an import allowlist test | Pitfall 1 (`node --check` returns 0 on a broken typeless `.js`), Code Example 6 |
| DEV-05 | Desktop half installed on Mac and Windows PC by copy script, banner on mismatch, README per machine | Answer 5 (disk door, home path per OS), Code Example 5, Pitfalls 4 and 5 |
| AGNT-01 (own-plan half) | The agent puts its own multi-step plan on the board and checks steps off | Answer 4 (hook contract), Answer 6 (harness), Pitfalls 6 to 8 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Source: `/home/theo/local_repo/hermes-session-tasks/.claude/CLAUDE.md` and `~/.claude/CLAUDE.md`.

- Plugin code runs and passes tests on Python 3.11 and 3.14. Import only the standard library, fastapi and pydantic. No 3.12 syntax.
- `desktop/plugin.js` is plain ESM, no build step, imports only SDK specifiers, theme vars only (`var(--ui-*)`), no hex or `rgb()` colours.
- Small modules with one job. The layout guard in `tests/test_layout.py` limits each module in `plugin/session_tasks` to 500 lines and allows only stdlib at module level.
- `pyproject.toml` stays outside `plugin/`. The layout guard fails on any manifest file name (including `package.json`) under `plugin/`.
- Never read, write, wrap or replace `todo_list`.
- Docs in plain language. No em dash or en dash anywhere. Use a spaced hyphen.
- Announce a gateway restart before it happens. A restart drops live Desktop connections.
- Every script for Theo is PowerShell 7 (`pwsh`). Any `az` command is PowerShell. This box has pwsh 7.6.4.
- Secrets: none needed in this phase. Any future secret comes from Infisical.
- Theo verifies on the Mac and the Windows PC himself. Claude runs every check it can run on devpc first. Ask Theo for one thing at a time.
- Commit identity: Theo Deyle <theo.deyle@donmor.ca>.
- Use the GSD workflow for repo edits.

## Summary

The router, the hook and the stub all fit the Hermes v0.22.5 contracts that Phase 1 and 2 already use. No new Python package is needed. The dev group already pins fastapi 0.133.1, starlette 1.3.1, pydantic 2.13.4 and httpx 0.28.1, and the running Desktop backend on devpc loads exactly those versions on Python 3.14.9 [VERIFIED: the `serve` process maps `~/.hermes/installs/33051a290b175956/environments/f19caafe225c4f28bbfba8fa22ceed88/venv`, `importlib.metadata` run there on 2026-10-31].

Four findings change the plan. (1) `broadcast_plugin_event` reaches only the Desktop clients of the process that makes the call. Devpc runs one `hermes serve --isolated` process for each Desktop SSH client (two exist now, different owner nonces). A write in the Mac's process never reaches the Windows window. Polling is the cross-machine path, not a fallback. (2) `node --check plugin.js` returns exit code 0 on a truncated ESM file when no `package.json` says `"type":"module"`. The DEV-03 test must pipe the file with `--input-type=module` or copy it to a `.mjs` file. (3) The project pytest setting `filterwarnings = ["error"]` makes `from fastapi.testclient import TestClient` fail on import. Two targeted ignore lines fix it. (4) The Windows Desktop home is `%LOCALAPPDATA%\hermes`, not `~\.hermes`. The sibling script in `deploy-dash` assumes `$HOME\.hermes` and was never run on Windows. The install script must resolve the home the way Desktop does.

D-22 (structured 200) holds. A 4xx from `ctx.rest` reaches the pane as one string, `Error invoking remote method 'hermes:api': Error: 409: <body>`. The body text survives inside that string. The status code does not arrive as a property.

**Primary recommendation:** Build in this order: core additions (JSON serializer, board list, event adapter, version module, `pre_llm_call` factory), then `plugin_api.py` with `load_core`, then the stub plus the copy script plus the node tests, then the live checks (own-job 3 of 3 headless first, then the Mac and the Windows PC after one announced restart of the two `serve` processes).

## Answers to the seven research questions

### Answer 1 - How `plugin_api.py` loads, mounts and authenticates

| Fact | Evidence |
|------|----------|
| The dashboard scans `<plugins root>/*/dashboard/manifest.json`. The plugin name is `data.get("name", child.name)`. | [VERIFIED: hermes_cli/web_server_dashboard.py:580, 585] `manifest_file = child / "dashboard" / "manifest.json"` and `name = data.get("name", child.name)` |
| `tab.hidden` is read from the manifest and kept as `tab_info["hidden"] = True`. | [VERIFIED: web_server_dashboard.py:532-533] `if bool(raw_tab.get("hidden")):` |
| The `api` field must be a relative path that stays inside `dashboard/`. | [VERIFIED: web_server_dashboard.py:456-475] |
| A user plugin mounts only when it is in `plugins.enabled`. | [VERIFIED: web_server_dashboard.py:809-810] `if source == "user" and plugin_name not in enabled_set:` returns `"not in plugins.enabled"`. `~/.hermes/config.yaml` lists `hermes-session-tasks` under `plugins.enabled` [VERIFIED: read 2026-10-31]. |
| The file loads with `spec_from_file_location`, module name `hermes_dashboard_plugin_<name>`, and goes into `sys.modules` before `exec_module`. No package. | [VERIFIED: web_server_dashboard.py:1168, 1175] `module_name = f"hermes_dashboard_plugin_{plugin['name']}"` and `sys.modules[module_name] = mod` |
| The module must export `router`. The mount prefix is `/api/plugins/<name>`. The dependency `_plugin_route_secret_scope` runs on every route. | [VERIFIED: web_server_dashboard.py:1187] `prefix=f"/api/plugins/{plugin['name']}",` |
| First request to a plugin that is enabled but not yet mounted hot-mounts the router. Once mounted, an edit to `plugin_api.py` needs a restart of that `serve` process. | [VERIFIED: web_server_dashboard.py:1032-1073, 1087-1118]. The mounted check at line 1055 returns False early for a mounted plugin. |
| Auth: every `/api/` path needs the session token header unless the request is already token or native authenticated. A plugin route adds no auth code. | [VERIFIED: web_server.py:226, 444-461] `_SESSION_HEADER_NAME = "X-Hermes-Session-Token"` and `and not _has_valid_session_token(request)` |
| Isolation mode. The config has no `isolation` key, so the mode is `in_process`. In `host` mode the process forwards each request to a plugin host and buffers the response. JSON routes work the same. | [VERIFIED: plugin_isolation.py:28-30, 94-103; web_server_dashboard.py:959-963]; `grep isolation ~/.hermes/config.yaml` printed nothing. |

Manifest to ship (same shape as the sibling plugin):

```json
{"name": "hermes-session-tasks", "api": "plugin_api.py", "tab": {"hidden": true}}
```
[VERIFIED: `~/.hermes/plugins/gsd-status-api/dashboard/manifest.json`, read 2026-10-31]

`hermes plugins validate` passes on a copy of `plugin/` with `dashboard/manifest.json`, `dashboard/plugin_api.py` and `desktop/plugin.js` added. It prints `✓ desktop surface - stays inside the plugin SDK surface` and `dashboard backend API is served through the plugin host (buffered responses)` [VERIFIED: run on a scratch copy 2026-10-31]. The validate command always reports host mode for its own probe. It does not change the live mode.

### Answer 2 - How `ctx.rest` calls a route, and the error mapping (D-22 confirmed)

- `ctx.rest(path, opts)` calls `pluginRest(pluginId, path, opts)` [VERIFIED: apps/desktop/src/contrib/plugin.ts:366].
- `pluginRest` adds a leading `/`, rejects any `..` segment, then calls `hermesApi({ path: \`/api/plugins/${pluginId}${suffix}\`, method, body, ... })` [VERIFIED: apps/desktop/src/api/plugins.ts:79]. A query string stays in the path. `PluginRestOptions` is `method`, `body`, `upload`, `timeoutMs` [CITED: desktop-plugin-sdk.md:1896-1898].
- A POST passes a JS object as `body`: `ctx.rest('/action', { method: 'POST', body: { go: true } })` [CITED: desktop-plugin-sdk.md:1887].
- The renderer calls IPC `hermes:api`. `hermesApi` returns the parsed JSON of a 2xx answer [VERIFIED: electron/preload.ts:339].
- For an HTTP status of 400 or more, the main process throws `new Error(\`${status}: ${detail}\`)` and sets `error.statusCode` [VERIFIED: electron/api-transport.ts:183-189].
- The renderer then holds the wrapped string. The app's own code matches it as `Error invoking remote method 'hermes:api': Error: 409: <body>` and tests the pattern `/(?:^\s*|error:\s*)409:/i` [VERIFIED: apps/desktop/src/lib/gateway-rpc.ts:62-70].
- Conclusion: a 409 body is not dropped. It arrives as text inside the message. The status code is not a reliable property. A pane that must branch on "stale" needs string parsing under 409. A 200 with `ok: false` needs none. D-22 stands. A FastAPI validation failure returns 422 and reaches the pane the same string way. That fits D-22: only transport faults keep a 4xx.
- A 2xx answer that is HTML gives the error "Expected JSON from ... but got HTML" [VERIFIED: api-transport.ts, `htmlResponseError`]. A missing or unmounted route returns JSON 404 from the fallback, not HTML.
- A POST is retried only when the body was not yet sent [VERIFIED: api-transport.ts, `shouldRetryRequest` and `withRetry`]. A double write is not possible through retry. `base_rev` also guards it.

### Answer 3 - Event delivery over SSH, wire name, fallback floor

- Wire name is `plugin.<plugin_id>.<event>`. The plugin id must match `[a-z0-9_-]{1,64}`. The event is a dotted name of `[A-Za-z0-9_-]` segments [VERIFIED: hermes_cli/plugin_events.py, `_PLUGIN_ID_RE`, `_EVENT_RE`, `plugin_event_name`]. `hermes-session-tasks` and `board.updated` are valid. I ran `plugin_event_name('hermes-session-tasks','board.updated')` in the project's 3.11 and 3.14 venvs and it printed `plugin.hermes-session-tasks.board.updated`.
- Frame on the wire. I registered a fake transport in `tui_gateway.server._live_transports`, called `broadcast_plugin_event`, and captured this frame under the Hermes bootstrap on Python 3.14.9:

```json
{"jsonrpc": "2.0", "method": "event", "params": {"type": "plugin.hermes-session-tasks.board.updated", "session_id": "", "payload": {"session_id": "abc", "rev": 3}}}
```
[VERIFIED: run 2026-10-31, script `scratchpad/bcast.py`]. The frame's own `session_id` is always an empty string. The session id and the revision must sit inside `payload`.
- Delivery is per process. `_broadcast_global_event` writes to `_live_transports` of the calling process only [VERIFIED: tui_gateway/server.py:762-778]. A WebSocket transport registers itself on connect [VERIFIED: tui_gateway/ws.py:563].
- Devpc runs one `hermes serve --isolated --host 127.0.0.1 --port 0 --ssh-session-token-file ... --ssh-owner-nonce <nonce>` process for each Desktop SSH client. On 2026-10-31 two such processes ran (PIDs 544077 and 1013517, started 13:26 and 19:05, different nonces) [VERIFIED: `ps` and `/proc/<pid>/cmdline`]. `hermes_cli/process_identity.py:157` says `serve --isolated` is "Desktop's SSH backend". That the two processes belong to the Mac and the Windows PC is [ASSUMED]. The messaging gateway (`gateway run`, PID 1270415) is a third process. It holds no Desktop client.
- Result. An agent tool write in the Mac's process reaches the Mac window only. A route write from the Mac stub reaches the Mac window only. The Windows window learns of both only through polling. Poll is the cross-machine path.
- Desktop side. The gateway JSON-RPC socket feeds `emitGatewayEvent(event)` before the app dispatches [VERIFIED: apps/desktop/src/app/contrib/wiring.tsx:807]. `host.onEvent(type, fn)` and `ctx.onEvent(type, fn)` subscribe by `event.type` [VERIFIED: apps/desktop/src/contrib/events.ts]. The listener gets the whole event: `{ type, session_id, payload }`.
- Whether `host.onEvent` receives a plugin event on an SSH remote was never run. The sibling project saw 48 `ctx.socket` frames on a MacBook over SSH. It did not test `host.onEvent`, and it did not test Windows [CITED: /home/theo/local_repo/deploy-dash/docs/hermes-plugin-sdk.md "Desktop half"]. The stub in this phase exists to prove it.
- WebSocket write is thread safe from a worker thread and blocks up to `_WS_WRITE_TIMEOUT_S = 10.0` seconds if the event loop stalls [VERIFIED: tui_gateway/ws.py:85, 132-134, 166]. A plain `def` route runs in the thread pool, so it is safe. Publish after the commit, never inside the transaction.
- With no gateway in the process, `broadcast_plugin_event` logs a warning and returns. It does not raise. I ran it in a clean 3.11 and 3.14 venv with the Hermes repo on `sys.path`: it printed `no raise` [VERIFIED: run 2026-10-31].
- Polling floor. The SDK says do not poll faster than a few seconds [CITED: desktop-plugin-sdk.md "Pitfalls"]. Use 5 to 8 seconds in the stub. Use `ctx.setInterval`, which the host clears on unload.

### Answer 4 - `pre_llm_call` contract in v0.22.5

- Registered with `ctx.register_hook("pre_llm_call", callback)`. The name is a member of `VALID_HOOKS` [VERIFIED: hermes_cli/plugins.py:111] `"transform_llm_output", "pre_llm_call", "post_llm_call",`.
- Call site: `agent/turn_context.py:799-850`, function `_collect_pre_llm_call_context`. It calls `invoke_hook("pre_llm_call", ...)` with these keyword arguments: `session_id`, `task_id`, `turn_id`, `user_message`, `conversation_history`, `is_first_turn`, `model`, `platform`, `parent_session_id`, `sender_id` [VERIFIED: turn_context.py:811-823]. Declare `session_id` and `**kwargs`.
- Return contract. A dict with a non-empty `"context"` key, or a non-empty `str`. Anything else is skipped. Pieces join with a blank line [VERIFIED: turn_context.py:830-850].
- Where the text lands: appended to the current turn's user message, never to the system prompt [CITED: website/docs/user-guide/features/hooks.md "Where context is injected"]. Hermes may persist the exact API-bound message in an `api_content` sidecar, so each injected block replays on later turns [CITED: same page; `.planning/research/PITFALLS.md` P1 quotes `memory_context.py:126-131`].
- The function returns an empty string when `agent._persist_disabled` is true [VERIFIED: turn_context.py:806]. Only the background review agent sets that flag [VERIFIED: agent/background_review.py:1002]. A headless `hermes chat --oneshot` run fires the hook.
- Any exception inside the hook is caught and logged by Hermes (`pre_llm_call hook failed`). A callback that runs longer than `plugins.hook_callback_timeout` (default 30 s) is skipped, not blocked [CITED: hooks.md line 396]. D-28 still applies: never raise, return `None`.
- Output over `hooks.output_spill.max_chars` (default 10,000) is written to disk and replaced by a head and tail preview [VERIFIED: tools/hook_output_spill.py:24]. Keep the injected text far below that.
- Delegate and subagent turns: a delegate child runs through `child.run_conversation` [VERIFIED: tools/delegate_tool_child_run.py:913], the same path, so the hook fires with the child's `session_id` and `parent_session_id` set. That the hook fires for a child was read, not run [ASSUMED]. The hook must return `None` when `SessionResolver.resolve(session_id).kind == "delegate"`, exactly as `make_pre_tool_call` does.
- Manifest: add `pre_llm_call` under `provides_hooks` in `plugin/plugin.yaml`. `tests/test_register.py::test_manifest_provides_exactly_the_registered_tools_and_hooks` compares the manifest list with `ctx.hooks`, and `hermes plugins validate` prints `✓ declared hooks - matches registrations`. Both must change in one commit.
- Plugin tools are deferred behind `tool_search`. `is_deferrable_tool_name` returns true for a plugin tool that is not core [VERIFIED: tools/tool_search.py:150-165]. `~/.hermes/config.yaml` has no `tools.tool_search` key [VERIFIED: Phase 2 SUMMARY line 138]. The model reaches `board_edit` through `tool_describe` and `tool_call` [VERIFIED: Phase 2 SUMMARY line 138, 205]. The nudge text must say how to reach `board_edit`. The prompt section already says "If board_edit is not in your tool list, find it with tool_search" [VERIFIED: plugin/session_tasks/tool_text.py:112-113].

### Answer 5 - How Desktop loads a disk plugin on the Mac and the Windows PC

- Slot: `<HERMES_HOME>/desktop-plugins/<id>/plugin.js`. The folder name must equal the plugin `id` [CITED: desktop-plugin-sdk.md quick start]. The scan reads one entry file per folder, `plugin.js` [VERIFIED: apps/desktop/src/contrib/runtime-loader.ts:576-579] `entrySegments: ['plugin.js']`.
- No `plugin.json` and no marker is needed. A marker-less folder that holds a `plugin.js` is a standalone plugin and a Rescan never overwrites it [CITED: desktop-plugin-sdk.md "One package, both SDKs"]. A `plugin.json` belongs to the Git install path only [VERIFIED: apps/desktop/electron/desktop-plugin-install.ts:202, 230]. A `.hermes-package.json` marker makes the plugin opt-in (off until switched on). Do not write one.
- The standalone plugin loads on by default (`defaultEnabled` default `true`) [CITED: desktop-plugin-sdk.md "Settings, enable state, and storage"].
- The root is local to the Desktop machine and is NOT taken from the remote backend [VERIFIED: apps/desktop/electron/fs-ipc.ts:93-99, 121-127].
- Where `HERMES_HOME` points on each OS [VERIFIED: apps/desktop/electron/data-paths.mjs:26-62]:
  - If env `HERMES_HOME` is set, use it. A path whose parent folder is named `profiles` maps to the grandparent.
  - Windows without env: the user environment variable `HERMES_HOME` from the registry, else `%LOCALAPPDATA%\hermes`. The legacy `~\.hermes` is used only when `%LOCALAPPDATA%\hermes` does not exist and `~\.hermes` does.
  - macOS and Linux: `~/.hermes`. `HERMES_DATA_DIR_SUFFIX` is appended when set.
- Copy needs only `scp`. The sibling project ships a working pair of scripts: `scp -O` first, plain `scp` as fallback, copy to a temp file in the target folder, check `export default`, then `Move-Item` over `plugin.js`, print the SHA-256 [CITED: /home/theo/local_repo/deploy-dash/scripts/install-desktop.ps1, `Copy-GsdRemoteFile`, `Install-GsdPlugin`]. It reasons that `-O` is needed because "Tailscale SSH has no SFTP subsystem" [CITED: deploy-dash/docs/hermes-plugin-sdk.md:180]. Devpc's own `sshd` is plain OpenSSH [VERIFIED: `ps`]. Whether Tailscale SSH sits in front for the clients is [ASSUMED].
- The sibling script's default home is `Join-Path $HOME '.hermes'`. That is wrong for a Windows Desktop whose home is `%LOCALAPPDATA%\hermes`. The sibling never ran on Windows [CITED: deploy-dash/docs/hermes-plugin-sdk.md "Desktop half": only the MacBook was tested]. Do not copy its home logic.
- The client's ssh alias for devpc is `devpc` on the MacBook [CITED: deploy-dash/docs/hermes-plugin-sdk.md:177-180]. The Windows PC alias is unknown to devpc. Make it a parameter.
- This box has pwsh 7.6.4, `scp` and `ssh` (OpenSSH 9.2) [VERIFIED: run 2026-10-31]. Pester is not installed. Test the script with `pwsh -File` plus a fake `scp` first on `PATH`.
- Closing the only pane of a plugin disables the plugin [CITED: PITFALLS.md M9]. Say so in the README.
- Reload: the app watches `desktop-plugins/`, loads within seconds, and the palette has "Reload desktop plugins" [CITED: desktop-plugin-sdk.md quick start].

### Answer 6 - The Phase 2 own-job harness (reuse for the 3 of 3 rule)

Files, all in `/tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/fc36b518-e447-44ef-9607-152d96268ad2/scratchpad/`:

| File | Role |
|------|------|
| `live-gap-ownjob2/job.txt` | The six-step prompt. It names six steps over the plugin source files and ends "Do not stop until all six steps are done." |
| `live-gap-ownjob2/own-1.jsonl` to `own-3.jsonl` | Raw stream of the three D-21 runs (0 `board_edit` calls) |
| `live-02-05/run.sh` | Runner. `hermes chat --query-file <prompt> --oneshot -Q --format stream-json`, `timeout 300`, output to `<name>.jsonl` and `<name>.err` |
| `live-02-05/analyze.py` | Reads the JSONL, counts `board_edit` and `todo_list` calls (handles the `tool_call` bridge name), and prints the board rows for the run's session id from `~/.hermes/plugin-data/hermes-session-tasks/data.db` (read only) |

[VERIFIED: files read 2026-10-31]. The `ownjob2` folder holds no runner. Its three runs used the `run.sh` command shape with `job.txt` as the query file. The session id sits in the stream's `result` event and in the `.err` file (`session_id: local-...`).

Reuse plan. The scratchpad is session scoped and will be gone. Copy `job.txt`, `run.sh` and `analyze.py` into a tracked folder (for example `tests/live/own_job/`) in the first plan, with `D` made a parameter. Extend `analyze.py` so a run passes when all three hold: at least one `board_edit` call carries 2 or more `add` ops; a later `board_edit` carries a `set_checked` op with `checked` true; the final board has at least 2 items and every item the agent added is checked. Headless runs start a new process each time, so they need no `serve` restart.

Each run writes a board into the real `data.db`. Phase 2 left ten test boards there [CITED: STATE.md decision 02-05]. Clean up the three new roots at the end of the plan with a one-line ask first (production data rule).

### Answer 7 - The version test

- Python reads `plugin.yaml` with a line regex. There is no YAML library in the dev group, and `tests/test_register.py` already parses the flat manifest by hand with `manifest_list` [VERIFIED: tests/test_register.py:19-34]. `plugin/plugin.yaml` today holds `version: 0.1.0` [VERIFIED: read]. Add one helper `manifest_value("version")` in the same style.
- Runtime read for `/meta`: a stdlib function in a new core module `version.py`: `Path(__file__).resolve().parent.parent / "plugin.yaml"` from `plugin/session_tasks/version.py` gives `plugin/plugin.yaml`. Match `^version:\s*(\S+)\s*$`. On a miss return the string `"unknown"` and log a warning. Never raise in a route.
- `API_VERSION = 1` is a constant in the same module. The route and the tests import it.
- JS side: one line `const PLUGIN_VERSION = '0.1.0'` and one line `const API_VERSION = 1` near the top of `desktop/plugin.js`.
- Drift test, three asserts: the regex over `plugin.js` finds `PLUGIN_VERSION` equal to the `plugin.yaml` value; `API_VERSION` in `plugin.js` equals `session_tasks.version.API_VERSION`; `pyproject.toml` `version` equals the manifest value (cheap third lock, optional).
- The banner test is a node VM test: feed a fake `/meta` answer with a different `backend_version` and assert the banner text renders (see Validation Architecture).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Board read, list, edit routes | API / Backend (`plugin_api.py` in the `serve` process) | Database / Storage (plugin SQLite) | The router is thin. `BoardStore` owns rules and storage. |
| Stale and rule outcome shape | API / Backend | Browser / Client reads it | One JSON shape, built in core, read by the pane. |
| `board.updated` publish | API / Backend (core `events.py`, after commit) | Browser / Client subscribes | The adapter is the only caller of `broadcast_plugin_event`. |
| Cross-machine freshness | Browser / Client (poll) | API / Backend (cheap read route) | Events are per process. Poll covers every other client. |
| Own-plan nudge and board injection | API / Backend (`pre_llm_call` in the agent turn) | none | Runs in the agent process. Never in the pane. |
| Version handshake | API / Backend (`/meta`) | Browser / Client (banner) | The client compares its constant with two server values. |
| Stub pane, event line, banner | Browser / Client (`desktop/plugin.js`) | none | One plain ESM file. |
| Copy of `plugin.js` to a machine | Client OS (pwsh script run on that machine) | devpc (source file) | Desktop only loads a local disk copy. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.133.1 | `APIRouter` in `dashboard/plugin_api.py` | Gateway-owned, same pin as the running `serve` venv [VERIFIED: `importlib.metadata` in the serve venv] |
| pydantic | 2.13.4 | Request models at the route boundary only | Same pin; core stays on dataclasses [VERIFIED: same] |
| starlette | 1.3.1 | `TestClient` through `fastapi.testclient` | Same pin [VERIFIED: same] |
| httpx | 0.28.1 | Needed by `TestClient` | Same pin [VERIFIED: same] |
| pytest | 9.1.1 | Tests | Existing dev pin [VERIFIED: pyproject.toml] |
| node | 24.19.0 | `node --check`, VM smoke tests | Present on devpc [VERIFIED: `node --version`] |
| pwsh | 7.6.4 | Install script, script tests on Linux | Present on devpc [VERIFIED: `pwsh --version`] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `hermes_cli.plugin_events` | Hermes v0.22.5 | `broadcast_plugin_event`, `plugin_event_name` | Lazy import inside `events.py` only. It is on the public import list in `tests/test_layout.py` (`HERMES_PUBLIC_IMPORTS`). |
| `plugins.plugin_storage` | Hermes v0.22.5 | Connection factory | Already used by `paths.connect`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-machine poll for freshness | A relay WebSocket route between `serve` processes | More machinery for about five users. Theo's rule asks before broadcast machinery. Do not build it. |
| `httpx2` to silence the TestClient warning | Two `filterwarnings` ignore lines | `httpx2` is a new package the gateway does not carry. Use the ignores. |
| PyYAML in the dev group | Line regex | PyYAML adds a pin and a lock change for a flat file. Use the regex. |

**Installation:** none. No new package enters the repo in this phase.

**Version verification:** versions read from the live `serve` venv on 2026-10-31: fastapi 0.133.1, starlette 1.3.1, pydantic 2.13.4, httpx 0.28.1, uvicorn 0.41.0, Python 3.14.9, SQLite 3.53.1. The project dev venvs hold anyio 4.15.1 and the gateway holds 4.14.2. The dev group does not pin anyio and `scripts/check_pins.py` does not compare it [VERIFIED: pyproject.toml, check_pins.py `GATEWAY_PACKAGES`].

## Package Legitimacy Audit

No external package is added in this phase. The legitimacy gate did not run because no install command is planned.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | - | - | - | - | - | - |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Mac or Windows PC (Desktop)                     devpc
+--------------------------------+   SSH tunnel   +---------------------------------------------------------+
| desktop/plugin.js (stub pane)  | -------------> | hermes serve --isolated  (one process per client)       |
|  - useValue(focusedStoredSid)  |  ctx.rest      |  auth middleware (session token)                        |
|  - poll /board every 5-8 s     |                |   -> /api/plugins/hermes-session-tasks/*                |
|  - GET /meta once, banner      |                |      dashboard/plugin_api.py (thin router)              |
|  - ctx.onEvent(board.updated)  | <------------- |         load_core() -> session_tasks (path-loaded copy) |
+--------------------------------+  WS JSON-RPC   |            BoardStore.apply(actor="user")  --commit-->  |
                                     event frame   |                    |                            data.db |
                                                   |                    +--> events.publish --> broadcast_plugin_event
                                                   |                                                         |
 agent turn (same serve process)                   |  pre_llm_call hook (nudge + board, never raises)        |
  model -> board_edit (session_id kwarg)           |  board_edit handler -> BoardStore.apply(actor="agent")  |
                                                   |            --commit--> after_write -> events.publish    |
                                                   +---------------------------------------------------------+
 A second client has its own serve process and the same data.db. It sees changes by poll only.
```

### Recommended Project Structure

```
plugin/
  plugin.yaml                      # add pre_llm_call to provides_hooks; version stays the backend version
  __init__.py                      # unchanged
  dashboard/
    manifest.json                  # new: name, api, tab.hidden
    plugin_api.py                  # new: router, load_core, pydantic models, HTTP mapping
  desktop/
    plugin.js                      # new: stub pane, PLUGIN_VERSION, API_VERSION
  session_tasks/
    board_json.py                  # new: Board and Stale and BoardError to JSON dicts (stdlib)
    events.py                      # new: publish(root_id, session_id, rev, actor), lazy Hermes import
    version.py                     # new: API_VERSION, read_backend_version(plugin_dir)
    nudge.py                       # new: nudge text constant and board block builder
    hooks.py                       # add make_pre_llm_call
    store.py                       # add list_boards()
    board_tools.py                 # change after_write signature (see Pattern 3)
    wiring.py                      # register pre_llm_call, build events publisher
scripts/
  install-desktop.ps1              # new
tests/
  test_api.py  test_api_load.py  test_events.py  test_version.py
  test_pre_llm_hook.py  test_desktop_plugin.py  test_install_script.py
  live/own_job/                    # job.txt, run.sh, analyze.py copied from the scratchpad
README.md                          # new: per-machine install steps (DEV-05); Phase 7 extends it
```

### Pattern 1: Thin router, one write path
**What:** `plugin_api.py` maps HTTP to `BoardStore` and maps core objects to JSON through `board_json.py`. Handlers are plain `def`. Reuse `edit_args.parse` so the route and the tool share one validator.
**When to use:** every route.
**Example:** see Code Example 1.

Route behavior to plan:

| Route | Success body | Failure body |
|-------|--------------|--------------|
| `GET /board?session_id=` | `{"ok": true, "api_version": 1, "session_id", "root_id", "rev", "board": {...}}` | no session: 400 or 422 transport fault |
| `GET /boards` | `{"ok": true, "boards": [{"root_id", "rev", "open", "total", "updated_at"}]}` | none expected |
| `POST /board/edit` | `{"ok": true, "rev", "board": {...}}` | 200 `{"ok": false, "error": "stale", "reason", "op_index", "item_id", "rev", "board"}` or 200 `{"ok": false, "error": "invalid", "op_index", "rule"}` |
| `GET /meta` | `{"ok": true, "plugin_id", "backend_version", "api_version"}` | none |

- `reason` carries `stale.reason` verbatim. Its values are `"stale"` or `"not_found"` [VERIFIED: plugin/session_tasks/model.py:13] `StaleReason: TypeAlias = Literal["stale", "not_found"]`. The CONTEXT example `"reason": "item changed"` is only an example. Do not ship it.
- `error` is a machine code (`"stale"` or `"invalid"`), not the human text the tool puts in `error` [VERIFIED: results.py `stale_result` puts human text in `error`]. Add the human line under `message`.
- The `board` field is JSON (items list), not markdown. The pane renders items. Keep `render(..., include_ids=True)` for the hook only.
- A route write with `SessionResolver` kind `delegate`: return `{"ok": false, "error": "invalid", ...}` with the `DELEGATE_EDIT` rule, to match the tool [VERIFIED: board_tools.py:62-63].
- `GET /board` for an unknown session returns an empty board and creates no row [VERIFIED: store.py:194-198 docstring "An unknown root gives an empty board, no row"].
- Resolving a session id can write: a compression tip gets an alias, and a branch gets a copy of its parent board on first touch [VERIFIED: lineage.py:109-116 docstring]. A GET therefore may write once. A known alias answers with no `state.db` open [same docstring]. A session with no board opens a `state.db` reader on every poll. That is acceptable for about five users.

### Pattern 2: `load_core` for a path-loaded module
**What:** The host imports `plugin_api.py` with no package, so a relative import fails. Load the `session_tasks` package under a fixed key.
**Evidence:** I ran this snippet on Python 3.11 and 3.14. `hermes_session_tasks_core.store` imported, `BoardStore.__module__` was `hermes_session_tasks_core.store`, and no `session_tasks` key leaked into `sys.modules` [VERIFIED: run 2026-10-31, `scratchpad/proto/load_core.py`].
**Consequence:** the route copy and the agent-half copy (`hermes_plugins.hermes_session_tasks.session_tasks`) are two module trees. `isinstance` checks must stay inside one tree. SQLite is the shared state, so two trees are safe.
**Test:** a test loads `plugin_api.py` the way the host does (`spec_from_file_location`, name `hermes_dashboard_plugin_hermes-session-tasks`, put in `sys.modules` before `exec_module`) and calls the routes through `TestClient`.

### Pattern 3: Events adapter and the `after_write` seam
**What:** `events.publish(root_id, session_id, rev, actor)` calls `broadcast_plugin_event("hermes-session-tasks", "board.updated", payload)` inside `try/except Exception`. The payload is `{"session_id", "root_id", "rev", "actor"}`. The Hermes import is lazy, inside the function.
**Change needed:** `BoardTools.after_write` is `Callable[[str], None]` and gets only `root_id` [VERIFIED: board_tools.py:26, 34, 80]. The event needs `rev`, `actor` and the caller's `session_id`. Change the listener to `Callable[[str, str, int], None]` taking `(root_id, session_id, rev)`, with the actor fixed `"agent"` in that path. Update `tests/test_board_tools.py` and `tests/test_register.py` in the same commit. `after_write` runs once after a changed write and a listener fault is logged and swallowed already [VERIFIED: board_tools.py:76-82].
**Route path:** the route calls `events.publish(..., actor="user")` after `BoardStore.apply` returns `Applied` with non-empty `changed_ids`. A no-op write and a stale write publish nothing.
**Why `root_id` in the payload:** the pane holds a focused stored session id that may be an alias of the root. The pane compares `payload.root_id` with the `root_id` its last `GET /board` returned.

### Pattern 4: `pre_llm_call` factory
**What:** `make_pre_llm_call(store, resolver)` in `hooks.py`, same factory style as the two existing hooks. The callback signature is `(session_id: object = "", **kwargs) -> str | None`. Return a string, not a dict, to keep the contract simple. Wrap the whole body in `try/except Exception`, log a warning, return `None` (D-28).
**Body:** blank session returns `None`. `resolver.resolve(session_id)` with kind `delegate` returns `None`. Else build the nudge line, then append the board block when `store.get_board(root_id).items` is not empty.
**Board block rules:** fence it as data, cap it, escape the closing tag (see Pitfall 7).

### Anti-Patterns to Avoid
- **`async def` route that touches SQLite:** blocks the gateway loop. Use plain `def`.
- **Module-level state in `plugin_api.py` beyond the cached core module and the router:** the file is evaluated once per process, so state outlives edits.
- **Publish inside the write transaction:** the WebSocket write can block up to 10 s.
- **A relative import in `plugin_api.py`:** fails at load. Use `load_core`.
- **A second validator for ops:** use `edit_args.parse`.
- **Colour literals or JSX in `plugin.js`:** the loader rejects JSX and the project rule bans colours.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ops validation on the route | A new parser | `edit_args.parse` | One rule set for tool, hook and route |
| Stale and rule outcome text | New wording | `results.describe`, `Stale.reason` | The tool and the route must say the same thing |
| Event name building | String concat | `broadcast_plugin_event(plugin_id, event, payload)` | It validates the id and event and builds `plugin.<id>.<event>` |
| Session to board root | A second lookup | `SessionResolver.resolve` | Alias and branch rules already live there |
| Import allowlist | A new rule list | The Desktop loader's own regex (see Code Example 6) | The test then agrees with the loader |
| Desktop home path | A guess | The `data-paths.mjs` rules (Answer 5) | A wrong guess installs into a folder Desktop never scans |
| Hot reload of the stub | A watcher | Desktop's own file watch | The app reloads within seconds |

**Key insight:** the risky parts are the places where two systems must agree (the loader regex, the home path, the stale shape, the version strings). Copy the other side's rule, then test against it.

## Common Pitfalls

### Pitfall 1: `node --check` passes a broken `plugin.js`
**What goes wrong:** `node --check desktop/plugin.js` returns exit code 0 for `export default { a:` when the nearest `package.json` has no `"type":"module"`.
**Why it happens:** Node tries CommonJS first on a typeless `.js`, then falls back to ESM detection, and the check mode swallows the ESM error.
**Evidence:** run on Node 24.19.0, 2026-10-31. Typeless `.js` with a truncated file: exit 0. The same content as `.mjs`: exit 1. A `"type":"module"` folder: exit 1. `node --input-type=module --check < file`: exit 1 [VERIFIED: run, scratchpad `jsproto/`].
**How to avoid:** the test pipes the file to `node --input-type=module --check` (or copies it to a temp `.mjs`). Do not add a `package.json` to `plugin/`: the layout guard bans it. Add a self-test that a truncated file fails the check.
**Warning signs:** a test named "node check" that never failed once.

### Pitfall 2: `TestClient` import fails under `filterwarnings = ["error"]`
**What goes wrong:** `from fastapi.testclient import TestClient` raises `StarletteDeprecationWarning` ("Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead"), then an anyio `DeprecationWarning` ("The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead").
**Evidence:** run on both venvs with `warnings.simplefilter("error")`. Both ignores together made the routes answer 200 and 422 on 3.11 and 3.14 [VERIFIED: run 2026-10-31, `scratchpad/proto/run.py`].
**How to avoid:** add to `[tool.pytest.ini_options] filterwarnings` after `"error"`:
`"ignore:Using `httpx` with `starlette.testclient`:starlette.exceptions.StarletteDeprecationWarning"` and `"ignore:The anyio.abc.BlockingPortal alias is deprecated:DeprecationWarning"`. Keep both narrow. A new fastapi pin may need a recheck.

### Pitfall 3: Events reach one machine only
**What goes wrong:** the Windows pane shows a stale board after the agent writes in the Mac's session.
**Why it happens:** see Answer 3. The broadcast list is per process.
**How to avoid:** poll every 5 to 8 s while the pane is visible. Treat the event as a speed-up that marks "event arrived" in the stub. The live check on each machine tests the event from that machine's own session and that machine's own route write. Do not expect a cross-machine event, and do not fail the phase when none arrives.

### Pitfall 4: Wrong Desktop home on Windows
**What goes wrong:** the script copies into `~\.hermes\desktop-plugins`, Desktop scans `%LOCALAPPDATA%\hermes\desktop-plugins`, and no pane shows.
**How to avoid:** resolve the home as in Answer 5. Print the resolved path and the SHA-256 on every run. Offer `-HermesHome` to override. A `-DryRun` switch prints the plan and writes nothing.

### Pitfall 5: `scp` on Windows and on Tailscale SSH
**What goes wrong:** OpenSSH 9 `scp` uses SFTP by default and fails where there is no SFTP subsystem ("Connection closed"). A Windows drive path such as `C:\...` can be read as a host.
**How to avoid:** try `scp -O` then plain `scp` (the sibling pattern). Copy into a relative temp file name inside the target folder, then rename. Validate the host parameter with a strict regex and refuse a leading `-` so it cannot become a `scp` option [CITED: deploy-dash `Test-GsdHost`]. The Windows drive-letter behavior is [ASSUMED] until Theo runs it.

### Pitfall 6: The board injected each turn replays on every later turn
**What goes wrong:** with D-27 the live board is injected on every turn. Hermes can store the injected text with the turn and replay it, so a board of N characters costs N characters again on each later request, and old copies go stale [CITED: hooks.md, PITFALLS.md P1].
**Status:** D-27 locks "inject every turn" until Phase 5 narrows it. Honor D-27. Reduce the cost: cap the board block (Pitfall 7), keep the nudge to one constant line, and write the cost in the plan so Phase 5 has it.

### Pitfall 7: Board text in the user message is a prompt-injection channel
**What goes wrong:** an agent-written item holds text that closes the fence and adds instructions [CITED: PITFALLS.md P11].
**How to avoid:** wrap the block in a plugin fence with a "notes, not instructions" line. Replace any `</` of the fence tag inside item text before injection. Cap at about 2,000 characters and end with a pointer line ("N more items, call board_read") [ASSUMED: the cap number]. Item text already has control characters stripped and newlines collapsed on write [VERIFIED: model.py `sanitize_text`]. It does not strip angle brackets.

### Pitfall 8: The model does not call a deferred tool on its own job
**What goes wrong:** Phase 2 measured 0 `board_edit` calls in 3 of 3 six-step runs with the rule text in the prompt section, tool descriptions and skill [VERIFIED: 02-VERIFICATION.md line 68].
**How to avoid:** the nudge arrives in the turn's user message, which the model weighs more than a frozen prompt section. The nudge must also name the path: add steps with `board_edit` before the job starts, reach `board_edit` through `tool_search` when it is not in the tool list. Whether this lifts the rate is unmeasured [ASSUMED]. Plan for two or three wording rounds. Record the measured wording and the rate for each round. Stop the round and diagnose when a run shows a broken system, per Theo's standing rule.

### Pitfall 9: A restart is needed, and it drops live Desktop connections
**What goes wrong:** the hook and the new tool wiring load when a `serve` process starts. The two running `serve` processes started before this change, so they lack the `pre_llm_call` hook. A first request hot-mounts `plugin_api.py`, but a later edit to it needs a restart.
**How to avoid:** announce the restart before it happens. To retire a `serve` process, stop it; the Desktop client's reconnect path respawns it from the new code [CITED: hermes_cli/web_server_skew_exit.py docstring]. That a manual stop respawns cleanly was not run [ASSUMED]. Headless `hermes chat --oneshot` runs start a fresh process each time and need no restart.

### Pitfall 10: Closing the pane disables the plugin
**What goes wrong:** Theo closes the only pane and the plugin switches off [CITED: PITFALLS.md M9]. Put the fix (Capabilities, Plugins, or Reset layout) in the README.

## Code Examples

### 1. `plugin_api.py` skeleton (host-style load, plain `def`)
```python
# Source: patterns verified by prototype 2026-10-31; mount facts web_server_dashboard.py:1168-1187
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

CORE_KEY = "hermes_session_tasks_core"
router = APIRouter()


def load_core() -> Any:
    cached = sys.modules.get(CORE_KEY)
    if cached is not None:
        return cached
    init = Path(__file__).resolve().parent.parent / "session_tasks" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        CORE_KEY, init, submodule_search_locations=[str(init.parent)]
    )
    if spec is None or spec.loader is None:
        raise ImportError("session_tasks package not found")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[CORE_KEY] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(CORE_KEY, None)
        raise
    return mod


class EditBody(BaseModel):
    session_id: str = Field(min_length=1)
    ops: list[Any]
    base_rev: int | None = None


@router.get("/meta")
def meta() -> dict[str, Any]:
    load_core()
    version = importlib.import_module(CORE_KEY + ".version")
    plugin_dir = Path(__file__).resolve().parent.parent
    return {
        "ok": True,
        "plugin_id": "hermes-session-tasks",
        "backend_version": version.read_backend_version(plugin_dir),
        "api_version": version.API_VERSION,
    }
```
Pydantic with `from __future__ import annotations` and a module-level model worked when the module sat in `sys.modules` before exec and when it did not [VERIFIED: prototype]. A body that fails validation (empty `session_id`) returned 422 [VERIFIED: prototype].

### 2. Version read
```python
# plugin/session_tasks/version.py (stdlib only)
import re
from pathlib import Path

API_VERSION = 1
_LINE = re.compile(r"^version:\s*(\S+)\s*$", re.MULTILINE)


def read_backend_version(plugin_dir: Path) -> str:
    try:
        text = (plugin_dir / "plugin.yaml").read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    found = _LINE.search(text)
    return found.group(1) if found else "unknown"
```

### 3. Events adapter
```python
# plugin/session_tasks/events.py
import logging
from typing import Any

PLUGIN_ID = "hermes-session-tasks"
EVENT = "board.updated"
log = logging.getLogger(__name__)


def publish(root_id: str, session_id: str, rev: int, actor: str) -> None:
    payload: dict[str, Any] = {"session_id": session_id, "root_id": root_id, "rev": rev, "actor": actor}
    try:
        from hermes_cli.plugin_events import broadcast_plugin_event  # pyright: ignore[reportMissingImports]
        broadcast_plugin_event(PLUGIN_ID, EVENT, payload)
    except Exception:
        log.warning("board.updated publish failed", exc_info=True)
```
Unit tests inject a fake publisher. One `hermes`-marked test checks `plugin_event_name(PLUGIN_ID, EVENT)` equals `plugin.hermes-session-tasks.board.updated`; that import needs no `dotenv` [VERIFIED: run in clean 3.11 and 3.14 venvs].

### 4. Stub pane skeleton (plain ESM, no JSX)
```javascript
// Source: contract desktop-plugin-sdk.md quick start; imports verified against sdk/runtime.ts:61-70
import { host, useValue } from '@hermes/plugin-sdk'
import { useEffect, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const PLUGIN_VERSION = '0.1.0'
const API_VERSION = 1
const POLL_MS = 6000

function makePane(ctx) {
  return function Pane() {
    const sid = useValue(host.state.focusedStoredSessionId)
    const [meta, setMeta] = useState(null)
    const [board, setBoard] = useState(null)
    const [event, setEvent] = useState(null)
    useEffect(() => { ctx.rest('/meta').then(setMeta).catch(() => setMeta({ error: true })) }, [])
    useEffect(() => {
      if (!sid) return undefined
      const load = () => ctx.rest(`/board?session_id=${encodeURIComponent(sid)}`).then(setBoard).catch(() => {})
      load()
      return ctx.setInterval(load, POLL_MS)
    }, [sid])
    useEffect(() => ctx.onEvent('plugin.hermes-session-tasks.board.updated', e =>
      setEvent({ rev: e.payload && e.payload.rev, at: new Date().toLocaleTimeString() })), [])
    const mismatch = meta && !meta.error && (meta.backend_version !== PLUGIN_VERSION || meta.api_version !== API_VERSION)
    return jsxs('div', { className: 'flex h-full flex-col gap-2 p-3 text-sm', children: [
      mismatch ? jsx('div', { className: 'text-(--ui-accent)', children: 'Update the desktop plugin on this machine' }) : null,
      jsx('div', { children: `last event: ${event ? `rev ${event.rev} at ${event.at}` : 'none yet'}` }),
    ] })
  }
}

export default {
  id: 'hermes-session-tasks',
  name: 'Session tasks (stub)',
  register(ctx) {
    ctx.register({ id: 'pane', area: 'panes', title: 'tasks', data: { placement: 'right', width: '320px' }, render: () => jsx(makePane(ctx), {}) })
  },
}
```
`ctx.setInterval` and `ctx.onEvent` return disposers, which `useEffect` can return. `host.state.focusedStoredSessionId` is the stored id [VERIFIED: sdk/index.ts:609-611 comment "Stored (durable) id of the focused session"]. The pane must not hold a hex colour. `var(--ui-accent)` is a theme variable named in CLAUDE.md. Add a button that posts a stale write (`base_rev: 0`, op `set_checked` on item 1): it always returns a stale or not_found rejection and never changes data (`is_stale` is true when `item.rev > base_rev`, and a missing item gives `not_found`) [VERIFIED: revision.py]. It proves the 200 body path live.

### 5. Install script core (pwsh 7, runs on macOS, Windows, Linux)
```powershell
# scripts/install-desktop.ps1 - skeleton of the home rule (data-paths.mjs:26-62)
function Resolve-HermesHome {
  if ($env:HERMES_HOME) {
    $home1 = $env:HERMES_HOME
    $parent = Split-Path -Parent $home1
    if ((Split-Path -Leaf $parent).ToLower() -eq 'profiles') { return Split-Path -Parent $parent }
    return $home1
  }
  $suffix = $env:HERMES_DATA_DIR_SUFFIX
  if ($IsWindows) {
    $reg = (Get-ItemProperty -Path 'HKCU:\Environment' -Name HERMES_HOME -ErrorAction SilentlyContinue).HERMES_HOME
    if ($reg) { return $reg }
    $base = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $HOME 'AppData\Local' }
    $default = (Join-Path $base 'hermes') + $suffix
    $legacy = Join-Path $HOME '.hermes'
    if (-not (Test-Path $default) -and -not $suffix -and (Test-Path $legacy)) { return $legacy }
    return $default
  }
  return (Join-Path $HOME '.hermes') + $suffix
}
```
Copy as in the sibling: `scp -O -q`, fall back to `scp -q`, temp file `.plugin.js.new`, check `export default`, `Move-Item -Force`, print SHA-256. The sibling script ends each function with `return` and never calls `exit` because it runs through `Invoke-Expression`. Run this script as a file with `pwsh -File`, so `exit` codes work and the usual pwsh parameter binding applies. Keep every `scp` argument a separate array item, never one joined string.

### 6. DEV-03 tests (allowlist and syntax)
```python
# The loader's own regex: apps/desktop/src/contrib/runtime-loader.ts:72
IMPORT_RE = re.compile(r"""(from\s*|import\s*\(\s*|import\s+)(['"])([^'"]+)\2""")
ALLOWED = {"@hermes/plugin-sdk", "react", "react/jsx-runtime"}
```
Run the regex over the file, take group 3, and assert every match is in `ALLOWED`. This is stricter than the loader (the loader ignores matches inside strings and comments). Keep UI strings free of the words `from` and `import` followed by a quote, or the test gives a false hit. Add a self-test with a file that imports `lodash` and one that has `import('x')`; both must fail. Syntax: `subprocess.run(["node", "--input-type=module", "--check"], input=source, ...)` and a self-test with a truncated file that must return non-zero.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Desktop plugin polls a JSONL queue | `broadcast_plugin_event` plus `host.onEvent` | in Hermes v0.22.5 docs (rss-reader migration note) | Event is a speed-up. Per process only. |
| `ctx.socket` as live feed | `host.onEvent` plus poll | SDK doc says socket is a no-op on OAuth remotes | Do not use `ctx.socket` here. |
| Unified package auto-copy of `desktop/plugin.js` | Manual disk copy for a remote backend | SDK doc note on remote backend | The script in this phase is the delivery path. |

**Deprecated or outdated:** `httpx` with `starlette.testclient` (deprecation warning, suggests `httpx2`). Ignore the warning narrowly. Do not add `httpx2` while the gateway lacks it.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The two `serve --isolated` processes on devpc belong to the Mac and the Windows PC | Answer 3 | Low. The per process rule holds for any client count. |
| A2 | `host.onEvent` receives plugin events on an SSH remote | Answer 3 | Medium. The stub exists to prove it. If false, polling still works. |
| A3 | The Windows PC alias for devpc is unknown; the Mac alias is `devpc` | Answer 5 | Low. The script takes the host as a parameter. |
| A4 | `scp -O` is needed because Tailscale SSH is in front of the clients | Answer 5, Pitfall 5 | Low. The script tries `-O` then plain `scp`. |
| A5 | A Windows drive-letter path is safe as a local `scp` target | Pitfall 5 | Medium. The script copies to a relative temp name. |
| A6 | A delegate child fires `pre_llm_call` (code path read, not run) | Answer 4 | Low. The hook returns `None` for delegates either way. |
| A7 | The nudge wording lifts the own-job rate to 3 of 3 | Pitfall 8 | High. This is the measured outcome of the phase. |
| A8 | A 2,000 character cap on the injected board block is right | Pitfall 7 | Low. Tune after the first runs. |
| A9 | Stopping a `serve` process makes the Desktop client respawn it from new code | Pitfall 9 | Medium. Docstring says the reconnect path respawns it. Not run. |
| A10 | The IPC hop drops `statusCode` as a property | Answer 2 | Low. The renderer's own code matches the message text instead. |

## Open Questions (RESOLVED)

1. **Where is each machine's Hermes home?**
   - Known: Desktop resolves it as in Answer 5.
   - Unclear: whether the Windows PC uses `%LOCALAPPDATA%\hermes` or the legacy `~\.hermes`, and which SSH alias it uses.
   - Recommendation: the script prints the resolved path and takes `-HermesHome` and `-DevpcHost`. Theo's first run on each machine settles it.
   - RESOLVED: plans 03-08 (Mac) and 03-10 (Windows PC) settle it. The script prints the resolved home on its `home:` line, and `-DevpcHost` takes the ssh name of each machine.

2. **Cost of D-27 against P1.**
   - Known: the board replays on each later turn. The cap limits it. Phase 5 narrows it.
   - Recommendation: keep D-27, cap the block, record the measured prompt growth in the 3 own-job runs.
   - RESOLVED: plan 03-01 caps the item lines of the board block at 2000 characters; plan 03-07 records the nudge length, item counts and turn counts for Phase 5.

3. **Own-job test boards in `data.db`.**
   - Recommendation: delete the three new roots after the measurement, after a one-line ask (production data).
   - RESOLVED: plan 03-12 Task 1 asks Theo once, for every test board of the phase; Task 2 deletes them only on his yes.

4. **The restart.**
   - Recommendation: one announced stop of both `serve` processes before the live checks. Headless runs come first and need none.
   - RESOLVED: plans 03-08 (Mac) and 03-10 (Windows PC) each hold one announced Desktop restart: Theo quits and reopens Desktop after a request that names the restart and its effect, and Claude confirms a new `serve` process with `ps`. Claude stops no `serve` process (Phase 2 rule: Desktop owns them). The messaging gateway is not restarted in Phase 3 (plan 03-08 Task 1 records why).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Hermes Agent | hook, route, validate, headless runs | yes | v0.22.5 | none |
| Python 3.11 and 3.14 project venvs | tests | yes (`.venv-py3.11`, `.venv-py3.14`) | 3.11 and 3.14 | none |
| node | `node --check`, VM tests | yes | 24.19.0 | none |
| pwsh | install script and its tests | yes | 7.6.4 | none |
| `scp`, `ssh` | install script test with a fake `scp` | yes | OpenSSH 9.2 | none |
| Pester | script tests | no | - | `pwsh -File` plus a fake `scp` run from pytest |
| Mac and Windows PC with Hermes Desktop | DEV-05 live check | not reachable from devpc | - | Theo runs the script and reports what the stub shows |

**Missing dependencies with no fallback:** none for the code work. The live check on each machine needs Theo at that machine.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1, `--import-mode=importlib --strict-markers`, `filterwarnings = ["error"]` [VERIFIED: pyproject.toml] |
| Config file | `/home/theo/local_repo/hermes-session-tasks/pyproject.toml` |
| Quick run command | `uv run --python 3.14 pytest -q tests/test_api.py tests/test_events.py tests/test_pre_llm_hook.py tests/test_version.py tests/test_desktop_plugin.py` (set `UV_PROJECT_ENVIRONMENT=.venv-py3.14`) |
| Full suite command | `./scripts/check.sh` (pins, ruff, format, pyright, pytest on 3.11 and 3.14, coverage gate 80 on 3.11) |
| Plugin gates | `timeout 120 hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin` and `timeout 180 hermes plugins doctor /home/theo/local_repo/hermes-session-tasks/plugin --ci` (both pass today) |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | `GET /board`, `GET /boards`, `POST /board/edit` return the D-22 and D-23 shapes; stale and invalid return 200 with `ok: false`; empty `session_id` returns 422 | unit with `TestClient` | `pytest tests/test_api.py -q` | no, Wave 0 |
| API-01 | `plugin_api.py` loads the way the host loads it and shares one SQLite file with the tool path | unit | `pytest tests/test_api_load.py -q` | no, Wave 0 |
| API-02 | A tool write and a route write each call the publisher once with `session_id`, `root_id`, `rev`, `actor`; a no-op and a stale write publish nothing; a publisher fault never fails the write | unit | `pytest tests/test_events.py tests/test_board_tools.py -q` | partly (`test_board_tools.py` exists) |
| API-02 | Wire name equals `plugin.hermes-session-tasks.board.updated` | hermes contract | `pytest -m hermes tests/test_events.py -q -rs` | no, Wave 0 |
| API-03 | `/meta` returns `backend_version` equal to `plugin.yaml` and `api_version` equal to `API_VERSION` | unit | `pytest tests/test_version.py -q` | no, Wave 0 |
| API-03 | Banner shows when the stub constants differ from a fake `/meta` | node VM harness via pytest | `pytest tests/test_desktop_plugin.py -q -k banner` | no, Wave 0 |
| DEV-03 | `plugin.js` passes `node --input-type=module --check`; self-test with a truncated file fails | unit | `pytest tests/test_desktop_plugin.py -q -k syntax` | no, Wave 0 |
| DEV-03 | Import allowlist permits only the three specifiers; self-tests with `lodash` and `import('x')` fail | unit | `pytest tests/test_desktop_plugin.py -q -k imports` | no, Wave 0 |
| DEV-05 | Script resolves the home per OS, copies with a fake `scp`, refuses a bad host, leaves `plugin.js` intact on `scp` failure, prints SHA-256 | unit via `pwsh -File` | `pytest tests/test_install_script.py -q` | no, Wave 0 |
| DEV-05 | README names the steps for the Mac and for the Windows PC | unit (text check) | `pytest tests/test_install_script.py -q -k readme` | no, Wave 0 |
| DEV-05 | Stub shows in Desktop on the Mac and on the Windows PC, the event line changes, stale body arrives | manual, Theo at each machine | none (visual, physical device) | n/a |
| AGNT-01 | Hook returns the nudge, adds the board block only when the board has items, caps and fences it, returns `None` for blank and delegate sessions, never raises on a store fault | unit | `pytest tests/test_pre_llm_hook.py -q` | no, Wave 0 |
| AGNT-01 | `plugin.yaml` `provides_hooks` equals the registered hooks | unit | `pytest tests/test_register.py -q` | yes (extend) |
| AGNT-01 | Own-job headless run passes 3 of 3 | live headless | `tests/live/own_job/run.sh own-1` (and 2, 3) then `analyze.py` | no, Wave 0 (copy from scratchpad) |
| Version | `plugin.js` constants equal `plugin.yaml` version and `API_VERSION` | unit | `pytest tests/test_version.py -q -k drift` | no, Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command for the touched area, on Python 3.14.
- **Per wave merge:** `./scripts/check.sh`.
- **Phase gate:** `./scripts/check.sh` green, both plugin gates green, 3 of 3 own-job runs passed, then Theo's live check on the Mac and on the Windows PC.

### Wave 0 Gaps
- [ ] `tests/test_api.py`, `tests/test_api_load.py` - API-01
- [ ] `tests/test_events.py` - API-02 (plus the `hermes`-marked contract test)
- [ ] `tests/test_version.py` - API-03 and drift
- [ ] `tests/test_pre_llm_hook.py` - AGNT-01
- [ ] `tests/test_desktop_plugin.py` plus a small `.mjs` VM harness - DEV-03 and the banner
- [ ] `tests/test_install_script.py` with a fake `scp` - DEV-05
- [ ] `pyproject.toml` `filterwarnings`: the two ignore lines (Pitfall 2)
- [ ] `tests/fakes.py`: extend `FakeCtx` only if it lacks `pre_llm_call` capture (it records `ctx.hooks` by name already)
- [ ] `tests/live/own_job/` copied from the scratchpad, with `D` as a parameter and the pass rule added to `analyze.py`
- [ ] The layout test `module_length_findings` limit (500 lines) applies to the new core modules. Keep each small.
- [ ] No framework install is needed.

## Security Domain

`security_enforcement` is on (ASVS level 1, block on high) [VERIFIED: `.planning/config.json`].

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (inherited) | The gateway token middleware gates `/api/plugins/*`. The router adds none [VERIFIED: web_server.py:444-461] |
| V3 Session Management | no | No session of our own |
| V4 Access Control | yes | Any authenticated client may read or write any board by `session_id` (D-25). Accepted for one user. Say so in the README. |
| V5 Input Validation | yes | Pydantic body model, `edit_args.parse`, `check_session_id`, the 100 op cap and 500 character text cap in core |
| V6 Cryptography | no | None used |
| V7 Error Handling | yes | Results carry no path, SQL or exception text. Log detail server side. |
| V12 Files | yes | Install script copies one fixed file name into one fixed folder. It checks the host argument and prints a hash. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection through board text in the user message | Tampering | Fence the block, mark it as notes, escape the closing tag, cap length (Pitfall 7) |
| SQL injection through `session_id` or op text | Tampering | Parameterized SQL only (existing rows and aliases modules) |
| XSS through item text in the pane | Tampering | Render text as React children. Never use `dangerouslySetInnerHTML` or an HTML string. |
| `scp` option injection through the host argument | Tampering | Regex on the host, refuse a leading `-`, pass each argument as a separate item |
| Tampered `plugin.js` on the client | Tampering | Copy from the known source, check `export default`, print SHA-256 for Theo to compare |
| Event spoof or leak | Information disclosure | The payload holds ids and a revision, no board text. The stream is the authenticated gateway socket. |
| Route used to read another user's board | Information disclosure | Single user tool. Note in README. |
| Hook raises and breaks a turn | Denial of service | Catch all, return `None`, log (D-28). Hermes also catches and times out the hook. |

## Sources

### Primary (HIGH confidence)
- `~/.hermes/hermes-agent/hermes_cli/web_server_dashboard.py` (lines 456-475, 532-533, 580-585, 798-810, 959-1000, 1032-1118, 1168-1190) - discovery, mount, hot mount, host mode
- `~/.hermes/hermes-agent/hermes_cli/web_server.py` (lines 226, 292-299, 444-461) - auth middleware
- `~/.hermes/hermes-agent/hermes_cli/plugin_events.py` - event name rules and no-gateway behavior (read and run)
- `~/.hermes/hermes-agent/tui_gateway/server.py` (717-778), `tui_gateway/ws.py` (85, 132-215, 563) - frame shape, per process fan out, thread safety (read and run)
- `~/.hermes/hermes-agent/agent/turn_context.py` (799-850, 1179) - `pre_llm_call` call site
- `~/.hermes/hermes-agent/hermes_cli/plugins.py` (111) - valid hook names
- `~/.hermes/hermes-agent/tools/hook_output_spill.py`, `tools/tool_search.py`, `tools/delegate_tool_child_run.py`
- `~/.hermes/hermes-agent/hermes_cli/web_server_idle_exit.py`, `web_server_skew_exit.py`, `process_identity.py` - SSH backend process model
- `~/.hermes/hermes-agent/apps/desktop/electron/{api-transport.ts,data-paths.mjs,fs-ipc.ts,preload.ts,desktop-plugins-root.ts}` and `src/{api/plugins.ts,contrib/runtime-loader.ts,contrib/events.ts,contrib/plugin.ts,sdk/index.ts,sdk/runtime.ts,lib/gateway-rpc.ts,app/contrib/wiring.tsx}`
- `~/.hermes/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md`, `website/docs/user-guide/features/hooks.md`
- This repo: `plugin/plugin.yaml`, `plugin/session_tasks/*.py`, `tests/*.py`, `pyproject.toml`, `scripts/check.sh`
- Commands run on devpc 2026-10-31: `ps` and `/proc` for `serve` processes, `importlib.metadata` in the serve venv, `hermes plugins validate` on a scratch layout, `hermes plugins doctor`, `node --check` variants, `TestClient` prototype on 3.11 and 3.14, `load_core` prototype, broadcast frame capture, `plugin_event_name` run

### Secondary (MEDIUM confidence)
- `/home/theo/local_repo/deploy-dash/scripts/install-desktop.ps1` and `docs/hermes-plugin-sdk.md` - sibling install precedent, MacBook only
- `/tmp/claude-1002/.../fc36b518-.../scratchpad/live-02-05/` and `live-gap-ownjob2/` - Phase 2 harness (session scoped)
- `.planning/research/PITFALLS.md`, `ARCHITECTURE.md`, `STACK.md`, Phase 1 and 2 CONTEXT, SUMMARY and VERIFICATION files

### Tertiary (LOW confidence)
- None used. Items without a run or a read are tagged `[ASSUMED]` above.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - read from the live `serve` venv.
- Architecture: HIGH for backend, hook and install path. MEDIUM for event delivery on the clients.
- Pitfalls: HIGH for items 1 to 4 (run), MEDIUM for 5 and 9, LOW for 8 (the nudge outcome is unmeasured).

**Research date:** 2026-10-31
**Valid until:** 2026-11-14 (Hermes updates move fast; re-check after each `hermes update`)
