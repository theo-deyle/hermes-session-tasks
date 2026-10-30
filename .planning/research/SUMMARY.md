# Project Research Summary

**Project:** hermes-session-tasks
**Domain:** Hermes Agent plus Hermes Desktop unified plugin - a per-session task board (Python agent tools, hooks and FastAPI router; plain ESM side pane)
**Researched:** 2026-10-30
**Confidence:** MEDIUM-HIGH (HIGH for the Python half, read from source and run on devpc; MEDIUM for live Desktop behaviour and the remote install path, which no researcher ran)

## Executive Summary

This product is a small plugin with two halves in one folder. The Python half runs inside the Hermes gateway on devpc. It holds the board storage, four agent tools, three hooks and a REST router. The Desktop half is one plain ESM file that draws a right-side pane on Theo's Macs and Windows PCs. Experts build this kind of plugin with a thin edge on each side and one shared core in the middle. Tools, REST routes and hooks all call one service. One SQLite file holds the state. The pane renders JSON and holds no logic.

The recommended approach is stdlib-only core code, stored through Hermes's own `plugin_db` helper, with item-level writes guarded by a board revision number. The agent sees Theo's edits through a small `pre_llm_call` delta, never through the whole board on each turn. Polling is the guaranteed way to update the pane. The live event is only a speed-up. The board is keyed by a session lineage root, resolved through an alias table, so it survives compression and branches.

The top risk is deployment, not code. The devpc symlink delivers only the Python half. `desktop/plugin.js` must be installed on each Mac and each Windows PC by hand or by script. All four research files found this. The second risk is token cost: injected text and tool results stay in the prompt for the rest of the session. The third risk is that the agent may never call the board tools, because Hermes can defer plugin tools behind a search step. Prove all three early, in the first phases, not at the end.

## Key Findings

### Recommended Stack

Source: STACK.md. One correction applies: the live gateway runs Python 3.14.9, so plugin code runs and is tested on both 3.11 and 3.14 (see "Resolved Conflicts Between Research Files").

The plugin declares no runtime dependency. It uses the standard library plus what the gateway already ships. Dev tooling lives in a repo-root `pyproject.toml` that Hermes cannot see. The symlink target is a `plugin/` subfolder. The shared core package is named `session_tasks`, never `core`, `tools` or `utils`, because those names shadow Hermes modules in tests.

**Core technologies:**
- Python, stdlib only in core: models, markdown parser, board store - no dependency means no version clash in the gateway venv
- `sqlite3` through `plugins.plugin_storage.plugin_db("hermes-session-tasks")`: board storage - WAL, foreign keys and a 5 s busy timeout come for free, and it works across processes
- fastapi 0.133.1 and pydantic 2.13.4 (gateway-owned): the REST router in `dashboard/plugin_api.py` - validate bodies at the boundary only, plain `def` routes, never `async def` with SQLite
- `hermes_cli.plugin_events.broadcast_plugin_event`: the `board.updated` push - fire and forget, never allowed to fail a write
- Hooks `pre_llm_call`, `post_compaction`, `on_session_delete`: inject Theo's edits, follow lineage, clean up
- One plain ESM `desktop/plugin.js` with `jsx()` and `jsxs()`, SDK UI kit, `useQuery` polling: the pane - no build step, no JSX syntax, theme variables only
- uv (managed Python), pytest 9.1.1, ruff 0.15.10, pyright, `hermes plugins validate` and `hermes plugins doctor . --ci`: dev gate
- `node --check` plus the VM smoke harness copied from hermes-memory-ui: the only pane tests, no npm install

Pin the dev group to the gateway's versions (fastapi 0.133.1, starlette 1.3.1, pydantic 2.13.4, httpx 0.28.1). Use a uv-managed interpreter, because the system `python3` links SQLite 3.40.1 and Hermes then drops WAL.

### Expected Features

Source: FEATURES.md, with PROJECT.md as the baseline.

**Must have (table stakes):**
- Board model with item-level writes and a board revision - the base of safe concurrent writes
- Session key that survives compression and branches - a board that splits breaks the core value
- Agent tools: read, edit (a list of operations), list sessions, copy from another session - four tools, not eight
- Bundled skill plus rules in the tool descriptions - the board is Theo's list, never the agent's plan
- Right-side pane: checkboxes, inline add and edit, subtasks, delete, collapse, empty and error states, copy as markdown
- Live update (event plus polling) and the agent seeing Theo's edits through a small delta
- Session picker with a read-only view of other boards and a copy action
- Delete the board when its session is deleted (keep it on archive)

**Should have (competitive):**
- Agent-changed marker on items (the `updated_by` data already exists)
- Status-bar chip with the open count, useful because the pane stacks as a tab
- Open the source session from the picker (`host.openSession`)

**Defer (v2+):**
- Reorder in the pane and in agent tools (keep the `position` column so no migration is needed)
- Edit another session's board in place, undo toast, global board, due dates, priorities, sync
- Markdown import is a borderline case: FEATURES.md defers it, PROJECT.md lists it. Recommendation: build the parser in phase 1 (the agent view needs it), and ship the import dialog last in phase 7 so it can drop without harm.

### Architecture Approach

Source: ARCHITECTURE.md. One write path serves everything. Tools, REST routes and hooks call `service`, which owns the actor, the `base_rev` rule, the change journal and the event. `store` is the only module that writes. Edge files stay thin. Hermes imports stay lazy and inside the adapter modules, so tests run with no Hermes on the path. Both entry files (`__init__.py` as a package, `plugin_api.py` with no package context) load the shared core through one `load_core()` helper under a fixed module name.

**Major components:**
1. `session_tasks/model` and `markdown` - dataclasses, limits, checklist parser and renderer (with and without item ids)
2. `session_tasks/store` - SQLite schema, `user_version` migrations, `BEGIN IMMEDIATE` writes, revision rule, journal (last 100 rows), alias table
3. `session_tasks/service` and `delta` - use cases, stale-write rule, and the text the agent receives
4. `session_tasks/lineage`, `events`, `paths` - adapters to Hermes (alias lookup first, compression-only walk on a miss, safe broadcast, per-call path)
5. `tools.py`, `hooks.py`, `__init__.py` - agent half; `session_id` comes only from the handler keyword
6. `dashboard/plugin_api.py` with a hidden-tab `manifest.json` - REST router, `/meta` with an `api_version`
7. `desktop/plugin.js` - pane that follows `host.state.focusedStoredSessionId`, polls, and sends raw markdown on import

Revision rule: add never conflicts. Update, rename, check and remove of item X fail when `X.rev > base_rev`. A stale reject returns the current board. The pane reads the revision first and fetches the body only when it moved.

### Critical Pitfalls

1. **The Desktop half is not deployed by the devpc symlink (TOP RISK, found in all four files).** The symlink delivers the Python half only. `plugin.js` must be installed on each Mac and each Windows PC, in a folder named exactly `hermes-session-tasks`, with no second package copy on the same machine (two folders with one id load first-wins). A remote Desktop shows the half as "unavailable (remote backend)" until it is installed. Two enable switches exist (`plugins.enabled` on devpc, the Plugins toggle on each client). Prevent it: prove the install path in phase 4 with a stub pane on both clients, ship one copy script per client type (`scp -O`, because Tailscale SSH has no SFTP), return `api_version` from `/meta`, and show a banner on mismatch. Not tested: how the repo (private on GitHub) reaches each machine.
2. **Token cost from injected text and tool results.** `pre_llm_call` text is saved and replayed on every later turn. Inject a delta only, capped near 600 to 1200 characters, driven by `agent_seen_rev` stored in SQLite. Reset `agent_seen_rev` on `post_compaction` so the full board returns once. Keep tool schemas static.
3. **Session identity.** Compression, branches, resets and a model-supplied id can all split or misroute a board. Key by lineage root with an alias table. Walk compression edges only. Copy the parent board lazily on a branch's first touch. Start a `/new` session empty. Take `session_id` only from the handler keyword, return an error when it is empty, and give no write tool a target-session argument.
4. **Lost updates and live reach across processes.** Several `hermes serve` processes run at once, one per Desktop SSH connection. A broadcast reaches only the Desktop windows of the sending process. Use SQLite as the only shared state. Use one connection per operation. Use polling as the contract and the event as the accelerator.
5. **The agent never calls the board, or misuses it.** Tool search can defer plugin tools behind a bridge, so the model sees only short names and descriptions. Few tools, a trigger in the first words of each description, and a measured 5 of 5 prompt test. Put the `todo_list`, `memory` and `kanban_*` exclusions in the tool descriptions. Enforce caps on the server. Use a `pre_tool_call` approve directive for delete or uncheck of Theo's items.

Also plan for: Python 3.11 and 3.14 test matrix (P8), prompt-injection fence and sanitising on write (P11), gateway restart drops live turns and leaves mixed versions (P12), a closed pane disables the plugin (M9), an error must never look like an empty board (M8), and the pane must capture the board id at edit start (M7).

### Resolved Conflicts Between Research Files

| # | Topic | Resolution | File followed |
|---|-------|-----------|---------------|
| 1 | Python version | Plugin code runs and is tested on both 3.11 and 3.14. The two live `hermes serve --isolated` processes run 3.14.9 (confirmed from `/proc` on devpc). The checkout venv is 3.11.16. Change the `pyproject.toml` sketch to `requires-python = ">=3.11,<3.15"`, pyright 3.11 as the floor, and run pytest on both interpreters. No syntax newer than 3.11. Use `spawn` in multiprocessing tests, because 3.14 defaults to forkserver. Both interpreters link SQLite 3.53.1. | ARCHITECTURE.md and PITFALLS.md. STACK.md ("3.11 only") is overridden. |
| 2 | Subtask depth | Open. FEATURES.md recommends one level of subtasks: a top-level item may have subtasks, a subtask may not. Reason: the pane is 260 to 320 px wide and deeper indents do not fit. ARCHITECTURE.md recommends two levels: item and subtask. Reason: the schema keeps `parent_id` either way, and a deeper tree needs a deeper parser and UI. Read closely, both describe the same shape (an item plus one subtask level). The real open question is whether to allow a third level. Recommendation: cap at item plus subtask, clamp deeper import lines to that level and report the count. **Mark as a discuss-phase decision.** | Both, unresolved by design. |
| 3 | Plugin skills in the system prompt | They are listed. `agent/prompt_builder.py:1200-1226` and `plugins_content.py:27-30` put every enabled plugin skill (name plus description) into `<available_skills>`. The body still loads only through `skill_view`. The `plugins/index.md:1201` claim is stale. Consequence: write the `register_skill` description as a trigger sentence with the exclusions, because that sentence is all the index shows. Still put the core rules in the tool descriptions, which are always in view. | ARCHITECTURE.md and PITFALLS.md (source). STACK.md and FEATURES.md (docs) are overridden. |
| 4 | Write result contract | See the trade-off below. | New recommendation, partly overrides PROJECT.md. |
| 5 | Locking | **Settled.** Several gateway processes run at once, and `plugin_api.py` and `__init__.py` load as two separate module objects. A Python lock cannot guard a shared file. Use SQLite `BEGIN IMMEDIATE`, one connection per operation, the `boards.rev` compare, and no module-level state. Add a two-process write test. | STACK.md and ARCHITECTURE.md (PITFALLS.md agrees). |

**Write result contract trade-off.** PROJECT.md says each write returns the full board as markdown. FEATURES.md and ARCHITECTURE.md agree: a small board costs about 600 tokens at 50 items, and the agent never holds a diff. PITFALLS.md objects: every tool result stays in history, so each write adds another full copy, and the old copies go stale beside the new one.

Recommended contract:
- A write returns a compact result: new `rev`, open and total counts, the changed items with their ids, and one summary line such as `Added #7. Checked #2.`
- A write returns the full board when the board has about 10 items or fewer, and whenever Theo changed the board since the agent last saw it (so the agent catches up in the same call).
- A stale reject always returns the error plus the current board.
- `read` always returns the full board with `rev`.
- A write moves `agent_seen_rev` forward only when the agent really received the content. A compact result that hides Theo's unseen edits must not skip the delta hook.

This keeps the agent safe from drift (it always gets a full view after a conflict or a user edit) and caps the growth of history. Confirm in discuss-phase, because it changes a PROJECT.md line.

**Other disagreements, with a recommendation each:**
- Tool count: FEATURES.md says 4, ARCHITECTURE.md says 6, PITFALLS.md says 3 to 4. Recommend 4 (read, edit with an operation list, sessions, copy). Every schema rides on every request and fills the deferral manifest.
- Tool names: avoid `todo`, `task`, `kanban`, `memory` and `note`. Recommend the prefix `session_board_` (FEATURES.md, PITFALLS.md) over `tasks_board_` (ARCHITECTURE.md). Keep names under 50 characters.
- Item cap: 100 (FEATURES.md), 200 (ARCHITECTURE.md), 256 (PITFALLS.md). Recommend 100 with 500 characters per item, because the lower cap fits full-board returns.
- Agent-visible item id: `#3` (FEATURES.md), `{#a3}` (ARCHITECTURE.md), `(a3)` (PITFALLS.md). Recommend a short per-board integer that is never reused, in one fixed form. Pick the exact form in discuss. Export for humans carries no ids.
- Stale-write transport: 409 (ARCHITECTURE.md) against HTTP 200 with `{"ok": false, ...}` (STACK.md, PITFALLS.md). Recommend the structured 200, because Desktop turns a 4xx into a string error. Confirm in the REST phase.
- Archive: keep the board on `archive`, delete on `delete`, `prune`, `empty_sweep` and `ghost_prune` (ARCHITECTURE.md, PITFALLS.md). FEATURES.md said delete without this distinction. Follow the first two. Add an orphan sweep for missed hooks.
- Poll interval: 4 s (ARCHITECTURE.md), 5 to 10 s (STACK.md), 5 s with backoff (PITFALLS.md). Recommend 5 s, revision-only request, paused when the pane is hidden.
- Tool search: FEATURES.md says the live config has no entry, so tools load eagerly. PITFALLS.md says the default is `auto`, so plugin tools are deferrable. These two cannot both be right. Measure it in phase 3.

## Implications for Roadmap

Suggested structure: 8 phases. Phases 3 and 4 can run in parallel after phase 2. The order follows the dependency chain in ARCHITECTURE.md and moves the two riskiest unknowns (agent tool use, client install) to the front.

### Phase 1: Core, storage and test harness
**Rationale:** Everything else calls this. The test harness must exist before the first feature test.
**Delivers:** `model`, `markdown` (parser, renderer, round-trip tests), `store` (schema, `user_version`, revision rule, journal, alias table, caps, sanitise on write), repo layout with the `plugin/` symlink target, pyproject and CI, test matrix on 3.11 and 3.14, a two-process write race test, `hermes`-marked contract tests.
**Addresses:** board model, storage, safe concurrent writes, markdown format.
**Uses:** stdlib `sqlite3`, `plugin_db`, uv, pytest, ruff, pyright.
**Avoids:** P5, P8, M2, M11, M12, M13, P11 (sanitise on write).

### Phase 2: Service, session identity and lineage
**Rationale:** The board key is the riskiest design piece. Test it before any surface depends on it.
**Delivers:** `service`, `delta`, `lineage` (alias table, compression-only walk, lazy branch copy, reset starts empty), `events`, `paths` adapters, fake-`SessionDB` contract tests, and one test against the live checkout.
**Addresses:** session key and lineage, board follows its session through compression and branches.
**Implements:** the one write path and the actor and `base_rev` rule.
**Avoids:** P2, P3, P4.

### Phase 3: Agent half - tools, skill, registration
**Rationale:** The core value fails silently if the agent does not use the board. Measure it now.
**Delivers:** four tools with static schemas, `session_id` from the keyword only, caps and per-call limits, the `pre_tool_call` approve directive for delete or uncheck of Theo's items, the skill with a trigger-sentence description, `plugin.yaml`, `__init__.py`, and `hermes plugins validate` clean. Live check: enable on devpc, open a fresh Desktop session, run 5 "list things for me" prompts, and record the tool call rate.
**Addresses:** agent tools, bundled skill, the `todo_list` boundary, the write result contract.
**Avoids:** P4, P9, P10, M5.

### Phase 4: REST router and the client install spike
**Rationale:** This phase proves the top risk early. A stub pane must render on both clients before the real pane is built.
**Delivers:** `plugin_api.py` with `load_core()`, hidden-tab `manifest.json`, `/meta` with `api_version`, `GET /board?since_rev=`, id-addressed writes with `base_rev`, the structured-200 conflict shape, safe broadcast. A minimal stub `plugin.js` copied by script to the Mac and the Windows PC. Proof that `ctx.rest` works through Desktop auth, and that the event does or does not reach each client.
**Addresses:** REST routes, the foundation of the pane and live update.
**Avoids:** P6, P7, M1, M3, M4.

### Phase 5: Pane
**Rationale:** The visible half of the core value. It depends on the REST contract and the proven install path.
**Delivers:** read-only follow of the focused chat, then writes (check, add, inline edit, subtask, delete with confirm, collapse), empty and error states, stale badge, copy as markdown, polling with `paneVisibility` and backoff, `ctx.onEvent` subscription inside `register()`, version banner, VM smoke test and static tests (no hex, no JSX, three imports).
**Addresses:** pane interactions, live update.
**Avoids:** M6, M7, M8, M9, P6.

### Phase 6: Agent sees Theo's edits (hooks)
**Rationale:** It can start after phase 2 but is only provable once the pane writes exist.
**Delivers:** `pre_llm_call` delta with `agent_seen_rev` in SQLite and a data-not-instructions fence, `post_compaction` alias and seen reset, `on_session_delete` (keep on archive, orphan sweep), skip for subagent turns, a token check at turn 30 against a no-plugin baseline.
**Addresses:** agent sees Theo's edits, session delete.
**Avoids:** P1, P11, M10.

### Phase 7: Cross-session and import
**Rationale:** Layers on a working board. Lowest risk, so it goes late.
**Delivers:** `sessions` and `copy` tools, picker with a read-only banner and a back button, title join through `session.list` (title, then preview, then "Untitled session"), copy to this board, markdown import (droppable to v2).
**Addresses:** session picker, cross-session read and copy.
**Avoids:** M7 (picker is read-only), m6.

### Phase 8: Deploy and hardening
**Rationale:** The final rollout uses the path proven in phase 4. Restarts drop live turns, so announce them.
**Delivers:** devpc symlink and `hermes plugins enable` (never a hand edit of `config.yaml`), announced restart of every `hermes serve` process, `readlink /proc/<pid>/exe` recorded, `/meta` version check on every backend, `plugin.js` on every client, toolset check, the "Looks Done But Isn't" checklist from PITFALLS.md, and a README that explains that closing the only pane disables the plugin.
**Avoids:** P7, P8, P12, M3, M4, M9.

### Phase Ordering Rationale

- Storage, then service, then surfaces. The revision rule, the alias table and the journal sit under tools, REST and hooks, so they come first.
- Agent tools before the pane. The core value starts with the agent writing items, and the tool-use rate is the largest unknown.
- The client install spike sits in phase 4, not phase 8. A failed remote install would block the pane and would surface too late otherwise.
- Hooks come after the pane writes. A delta needs a real user edit to prove.
- Cross-session and import come last, because they add nothing to the core value and carry little risk.

### Research Flags

Phases likely needing deeper research during planning (`/gsd-plan-phase --research-phase <N>`):
- **Phase 2:** live checks of `post_compaction` on Desktop, whether the tool `session_id` and `focusedStoredSessionId` stay equal after `/compress`, and what a branch looks like in `state.db`.
- **Phase 3:** measure tool deferral and the toolset default for the Desktop platform, confirm the `pre_tool_call` approve directive, and settle the tool names.
- **Phase 4:** confirm the 409 versus 200 transport in a live Desktop, event delivery over SSH to the Mac and the Windows PC (the Windows client was never tested), and how `plugin.js` reaches each machine.
- **Phase 6:** the `platform` value Desktop reports, delegate and subagent turn behaviour, hot mount versus restart.
- **Phase 8:** a live procedure with Theo (restart announcement, every process, both clients).

Phases with standard patterns (skip research-phase):
- **Phase 1:** stdlib, SQLite and pytest patterns, with prototypes already run.
- **Phase 5:** SDK exports verified against `sdk/index.ts`, and hermes-memory-ui is a working reference.
- **Phase 7:** same REST and pane patterns, and the title join uses the documented `session.list`.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Read from local source, and commands ran on devpc (pip list, validate, uv sync, prototypes). One stale item: STACK.md named Python 3.11 only. Corrected here. |
| Features | MEDIUM-HIGH | The `todo_list` boundary and the plugin surface were read from source. Agent behaviour rules and the tool count are design judgment. |
| Architecture | HIGH for Python, REST and event paths; MEDIUM for live Desktop | Source citations are line-level. Nothing ran in a live Desktop session. Process facts are a snapshot of 2026-10-30. |
| Pitfalls | HIGH for source facts; MEDIUM for agent behaviour | Many items are tagged verified. The tool-deferral rate and prompt-injection risk are not yet measured. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- Remote Desktop install: how `plugin.js` reaches the Mac and the Windows PC. The repo is private on GitHub. Recommend a `scp -O` sync script that places one file, plus the `/meta` check. Prove it in phase 4. Needs Theo's choice.
- Tool deferral: FEATURES.md and PITFALLS.md disagree on whether plugin tools load eagerly. Measure in phase 3. If the rate is low, ask Theo a cost question: turning off `tools.tool_search` makes every tool eager for every session.
- Session id equality after compression: the pane id and the tool id may differ after a rotation. In-place compaction is the default, so this is a safety net. Test with a forced `/compress` in phase 2.
- Event delivery over SSH to the Windows client: untested by every source. Polling covers it, but prove it in phase 4.
- Skill and toolset visibility in a fresh Desktop session: `known_plugin_toolsets` can switch the toolset off after a toolset panel save. Check at deploy.
- Agent-side session titles: no documented lookup. The pane joins through `session.list`. The `sessions` tool returns ids, counts, last update and the first open item as a hint. Storing a label at first write is the later option.
- Discuss-phase decisions, each with its recommendation above: subtask depth, write result contract, tool count and names, item cap, item id form, branch copy, archive versus delete, reorder deferred, import timing, picker reset on focus change, no `check_fn` for non-Desktop platforms in v1, profiles ignored in v1.
- PROJECT.md edits to make: the Python line (3.11 and 3.14), the write result contract, the reorder tool, and "routes need a restart" (first mount is hot, later code edits need a restart of every `serve` process).

## Sources

### Primary (HIGH confidence)
- `~/.hermes/hermes-agent/` source at commit `bf0203a794` (Hermes Agent v0.22.5): `hermes_cli/plugins.py`, `plugins_loader.py`, `plugins_content.py`, `plugins_dispatch.py`, `plugin_events.py`, `web_server.py`, `web_server_dashboard.py`, `config_defaults.py`; `plugins/plugin_storage.py`; `tools/registry.py`, `todo_tool.py`, `tool_search.py`; `agent/turn_context.py`, `memory_context.py`, `prompt_builder.py`; `hermes_state_*.py`; `apps/desktop/src/sdk/index.ts`, `api/plugins.ts`
- `~/.hermes/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md`, `plugins/index.md`, `user-guide/features/hooks.md`, `user-guide/desktop.md`
- Installed plugins as analogs: `hermes-memory-ui`, `memory-wiki`, `homeassistant`, `agent-importers`, `gsd-status-api`
- Commands run on devpc on 2026-10-30: gateway `pip list`, `/proc/<pid>/exe` of both `hermes serve` processes, `hermes plugins validate` on a prototype layout, `uv sync`, `node --check`, VM smoke harness, checklist parser and `plugin_db` prototypes

### Secondary (MEDIUM confidence)
- `~/.hermes/skills/hermes-desktop-plugins/templates/plugin.js` and the house skills under `~/.claude/skills/` (coding rules)
- Sibling project `local_repo/deploy-dash` (`docs/hermes-plugin-sdk.md`, research PITFALLS): symlink refusal, `scp -O`, `ctx.socket` over SSH on the Mac, scratch-home hazard

### Tertiary (LOW confidence, needs validation)
- Agent behaviour rules, tool count, and token budgets: design judgment, to be measured in phases 3 and 6
- Stale-write transport (409 string shape) and Tailwind utility availability in the pane: inferred, to be tested in phases 4 and 5

---
*Research completed: 2026-10-30*
*Ready for roadmap: yes*
