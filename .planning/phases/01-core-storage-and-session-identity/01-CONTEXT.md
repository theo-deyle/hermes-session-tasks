# Phase 1: Core, storage and session identity - Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Each session has its own durable board in a plugin-owned SQLite file. Concurrent writes from two gateway processes stay safe. The board converts to a markdown checklist and back with no loss. The board follows its session through context compression and branches. The repo is a uv project with ruff, pyright and pytest green on Python 3.11 and 3.14 with no gateway running.

Requirements: STOR-01, STOR-02, STOR-03, STOR-04, STOR-05, STOR-06, STOR-08, DEV-01, DEV-02.

Not in this phase: agent tools and skill (Phase 2), REST routes (Phase 3), pane (Phase 4), `pre_llm_call` delta and session delete (Phase 5), cross-session tools (Phase 6), rollout (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Subtask depth
- **D-01:** An item may have subtasks. A subtask may not have subtasks. Two levels total. The schema keeps `parent_id` so the depth can change later (STOR-03). - **Reversibility:** reversible - the schema is depth-agnostic; only the parser, the store check and the pane change.
- **D-02:** A pasted line nested deeper than one subtask level moves up to the subtask level under the nearest top-level item. The import result reports how many lines moved. No line is dropped.

### Item id form
- **D-03:** Each item has a per-board integer id that starts at 1 and is never reused, even after a delete. The store keeps a `next_item_id` counter per board. - **Reversibility:** costly - the agent view and every tool operation address items by this id; a change breaks the Phase 2 tool contract.
- **D-04:** The agent view of the board shows the id first, after the checkbox: `- [ ] #3 Call John`. A subtask is indented two spaces: `  - [x] #4 Book the room`.
- **D-05:** The parser strips a leading `#<digits> ` token after the checkbox and keeps the rest as text. The clipboard export for Theo carries no ids. The renderer has an `include_ids` switch.

### Branch behaviour
- **D-06:** A session that Hermes marks as an explicit branch starts with a copy of its parent's board, taken the first time the branch touches the board. The copy gets new item ids and a journal row that names the parent. After the copy, the two boards do not share edits. - **Reversibility:** reversible - the alternative is an empty board; no stored data changes shape.
- **D-07:** A compression child (when `compression.in_place` is false) is the same board, resolved through the alias table to the root session id. A `/new` or reset session is a separate conversation and gets an empty board.

### Import rules
- **D-08:** A plain bullet with no checkbox (`- text`, `* text`, `+ text`) becomes an unchecked item. Uppercase `[X]` counts as checked. Headings, paragraphs and blank lines are ignored.
- **D-09:** A checkbox line with empty text is skipped and counted in the import result. Item text is one line; newlines collapse to a space on write.
- **D-10:** Caps: 100 items per board and 500 characters per item. The store enforces both. An import that would pass a cap stops at the cap and reports the overflow count. - **Reversibility:** reversible - a constant in `model`; raising it needs no migration.

### Claude's Discretion
- SQLite schema shape, `user_version` migration, `BEGIN IMMEDIATE` write helper, journal size (research says last 100 rows), alias table layout.
- The lineage walker on public `SessionDB` methods, the fake-`SessionDB` tests, and the `hermes`-marked contract tests.
- Repo layout, pyproject pins, test matrix wiring for 3.11 and 3.14, and the two-process write race test (use `spawn`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project research (this repo)
- `.planning/research/SUMMARY.md` - the open choices table and the recommendations this context locks; phase list.
- `.planning/research/ARCHITECTURE.md` - module layout (`model`, `markdown`, `store`, `lineage`, `events`, `paths`), revision rule, alias table, lazy branch copy, compression-only walk, the `SessionDB` public methods to use and the private ones to avoid.
- `.planning/research/PITFALLS.md` - locking across processes, WAL downgrade on old SQLite, id-addressed operations, sanitise on write, markdown parser pitfalls table.
- `.planning/research/STACK.md` - `plugin_db`, `broadcast_plugin_event`, pyproject sketch, test layout, Python and SQLite versions.
- `.planning/PROJECT.md` and `.planning/REQUIREMENTS.md` - scope, constraints, STOR and DEV requirements.

### Hermes source and docs (on devpc, `~/.hermes/hermes-agent`)
- `~/.hermes/hermes-agent/plugins/plugin_storage.py` - `plugin_db(name)` opens the plugin SQLite file with WAL, foreign keys and a busy timeout.
- `~/.hermes/hermes-agent/hermes_cli/plugin_validate_private_imports.py` - the public import allowlist (`hermes_constants`, `hermes_state`, `hermes_cli.plugin_events`, `plugins.plugin_storage`).
- `~/.hermes/hermes-agent/hermes_state_messages.py` - `is_explicit_fork_child` and `get_session`, the public lineage methods.
- `~/.hermes/hermes-agent/website/docs/user-guide/features/hooks.md` - `post_compaction(session_id, old_session_id)`.
- `~/.hermes/hermes-agent/website/docs/developer-guide/plugins/index.md` - plugin layout, dependency resolution, hooks table.

### House rules
- `~/.claude/skills/donmor-coding-practices/SKILL.md` and `python/*.md` - Python structure, pytest, ruff, docs style.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No plugin code exists yet. The repo holds `.planning/` and `.claude/` only.
- Reference plugins on devpc: `~/.hermes/plugins/memory-wiki/conftest.py` (HERMES_HOME on `tmp_path`, path-loaded dashboard modules), `~/.hermes/plugins/homeassistant/tests/conftest.py` (plugin dir loaded as a package, root removed from `sys.path`), `~/.hermes/plugins/agent-importers/pytest.ini` (`--import-mode=importlib`).

### Established Patterns
- One connection per operation through `plugin_db`, never cached. `BEGIN IMMEDIATE` per write. No module-level state, because `__init__.py` and `plugin_api.py` load as separate module objects in separate processes.
- Core package imports only the standard library. Hermes imports are lazy and sit in thin adapters.
- `pyproject.toml` stays at the repo root, outside the symlinked `plugin/` dir, so Hermes does not read the dev group as runtime dependencies.

### Integration Points
- `plugins.plugin_storage.plugin_db("hermes-session-tasks")` for the file under `$HERMES_HOME/plugin-data/hermes-session-tasks/`.
- `hermes_state.SessionDB(read_only=True)` for the lineage walk on an alias miss.
- `post_compaction` hook writes the alias row (hook registration itself lands in Phase 2 with `__init__.py`; the store and lineage functions it calls land here).

</code_context>

<specifics>
## Specific Ideas

- Agent view line: `- [ ] #3 Call John`. Clipboard export line: `- [ ] Call John`.
- Phase 1 includes a live check on devpc: write a board, run `/compress`, read the board again, and record whether the tool `session_id` and `focusedStoredSessionId` stay equal (STATE.md concern).

</specifics>

<deferred>
## Deferred Ideas

- Write result contract (compact versus full board) - Phase 2 discuss.
- Tool names and count - Phase 2 discuss.
- Stale-write transport (HTTP 409 versus structured 200) - Phase 3 discuss.
- Archive keeps the board, delete removes it, orphan sweep - Phase 5.
- Reorder items (BORD-01), import from the pane (BORD-02) - v2.

</deferred>

---

*Phase: 01-core-storage-and-session-identity*
*Context gathered: 2026-10-30*
