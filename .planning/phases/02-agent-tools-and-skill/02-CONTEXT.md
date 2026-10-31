# Phase 2: Agent tools and skill - Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

The agent half of the plugin: `plugin.yaml`, `__init__.py`, two tools (`board_read`, `board_edit`), the `post_compaction` hook, a `pre_tool_call` guard, and the bundled skill. The agent reads the current session's board as markdown with ids and the revision, and edits it with a list of item-level operations. The agent writes things Theo must do, decide or remember to the board, and keeps its own plan in `todo_list`. Requirements: TOOL-01, TOOL-02, TOOL-06, TOOL-07, TOOL-08, AGNT-01, AGNT-02, AGNT-03, AGNT-04.

Not in this phase: REST routes and the pane (Phases 3 and 4), the `pre_llm_call` edit injection and session delete (Phase 5), cross-session tools `board_sessions` and `board_copy` (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Tool names
- **D-11:** Two tools in this phase: `board_read` and `board_edit`. Prefix `board_`. Phase 6 adds `board_sessions` and `board_copy` under the same prefix. - **Reversibility:** costly - the skill, the tool descriptions, the guard and the live test all name the tools; a rename after Phase 2 touches every one.
- **D-12:** No tool name or description contains the word "todo". Each description names `todo_list`, `memory` and `kanban_*` only to say the board is not them.

### Write result shape
- **D-13:** A successful `board_edit` returns the new `rev`, a one-line summary, and one markdown line per changed item with its id, in the agent view form from D-04. No full board on success.
- **D-14:** A stale write returns the current `rev`, the stale reason with the op index, and the full board as markdown with ids. The agent merges and retries.
- **D-15:** `board_read` returns the full board as markdown with ids plus the `rev`. An empty board returns the `rev` and an "empty board" line.
- **D-16:** A `BoardError` (empty text, too long, board full, depth, bad parent ref) returns an error that names the op index and the rule. Nothing is written.

### Guard before delete, uncheck or reword
- **D-17:** The tool descriptions and the skill carry the ask rule. When Theo's own message names a remove, an uncheck, a reword or a bulk change, that message is his answer: the agent does it at once with `confirmed: true`. The agent asks Theo one plain question first only when it decides on its own to remove an item, uncheck an item or reword an item Theo wrote, or when it is not sure which item Theo means. Changed 2026-10-31 (quick task 261031-lbp) after the phase 2 Desktop pass, where the agent asked before a remove that Theo named in his own message. The 02-05 live runs ask-b, uncheck-b, bulk and reword-b measured the old rule; with an explicit instruction the agent now acts at once.
- **D-18:** A `pre_tool_call` hook on `board_edit` is the hard guard. A call that holds a guarded op is blocked unless the arguments carry `confirmed: true`. Guarded ops: `remove` of any item, `uncheck` of any item, and `set_text` of an item whose `updated_by` is `user`. The block message tells the agent: when Theo's own message named the change, send the same call again with `confirmed: true`; otherwise ask Theo one plain question in chat first, then send the call again with `confirmed: true`. An explicit instruction from Theo in his own message counts as his answer. The guard cannot check intent, so the rule text defines `confirmed: true` as a change that Theo's own message named or that Theo answered in chat. No Desktop approval dialog (no `approve` directive). - **Reversibility:** reversible - the hook is one function; switching to `approve` changes one return value.
- **D-19:** Adds and checks in any count pass without a guard. A bulk add is the normal case when the agent lists things for Theo.

### Subagents
- **D-20:** A delegate session (`delegate_task` subagent) resolves to its delegator's root board (Phase 1). In a delegate session `board_read` works and `board_edit` returns an error that tells the subagent to report the items to its delegator. Only the session Theo talks to writes the board. - **Reversibility:** reversible - one check on `Resolution.kind == "delegate"` in the edit tool.

### Claude's Discretion
- Exact description text for both tools: the trigger sentence first ("Add an item when you list something Theo must do, decide or remember"), then the `todo_list` boundary, then the ask rule.
- The operation schema for `board_edit` (an `ops` list mapping one to one to `AddItem`, `SetText`, `SetChecked`, `RemoveItem` from `session_tasks.model`), `base_rev`, and `confirmed`.
- Skill content, `plugin.yaml` fields, `__init__.py` registration, `post_compaction` hook calling `SessionResolver.record_compaction`.
- The live test on devpc: enable the plugin, open a fresh Desktop session, send 5 prompts that list things for Theo, record the call rate. Also the forced `/compress` check from Phase 1 specifics.
- How the planner reads the tool deferral facts: the default `tools.tool_search.defer` list in `hermes_cli/config_defaults.py` names built-ins only, so plugin tools load eagerly unless `~/.hermes/config.yaml` sets an explicit list. Verify on devpc before the live test.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project (this repo)
- `.planning/phases/01-core-storage-and-session-identity/01-CONTEXT.md` - D-01 to D-10: depth, item ids, agent view line form, caps, branch and compression rules.
- `.planning/phases/01-core-storage-and-session-identity/01-05-SUMMARY.md` - delegate resolution, the `post_compaction` registration note for Phase 2.
- `.planning/research/SUMMARY.md` - open choices table, tool count recommendation, the deferral risk.
- `.planning/research/PITFALLS.md` - tool description rules, prompt cost of tool results, id-addressed operations.
- `.planning/REQUIREMENTS.md` - TOOL and AGNT requirements.
- `.planning/ROADMAP.md` - Phase 2 success criteria.

### Hermes source and docs (on devpc, `~/.hermes/hermes-agent`)
- `website/docs/developer-guide/plugins/index.md` - `ctx.register_tool`, `ctx.register_hook`, `ctx.register_skill`, `plugin.yaml`, hook table with `pre_tool_call` directives.
- `website/docs/user-guide/features/hooks.md` - `pre_tool_call` return shapes (`block`, `approve`, `modify`), fail-closed timeout rule, `post_compaction` arguments.
- `tools/registry.py` - handlers get `session_id` only when the signature names it.
- `hermes_cli/config_defaults.py` - `tools.tool_search` defaults and the `defer` list.
- `hermes_cli/plugin_validate_private_imports.py` - public import allowlist.
- `~/.hermes/skills/hermes-desktop-plugins/templates/` - plugin templates.

### House rules
- `~/.claude/skills/donmor-coding-practices/SKILL.md` and `python/*.md` - Python structure, pytest, ruff, docs style.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `plugin/session_tasks/store.py` `BoardStore.get_board` and `BoardStore.apply(root_id, ops, actor=, base_rev=)` returning `Applied` or `Stale`.
- `plugin/session_tasks/model.py` ops `AddItem`, `SetText`, `SetChecked`, `RemoveItem`; results `Applied(board, rev, changed_ids)`, `Stale(board, reason, op_index, item_id)`; `BoardError` family; `Item.updated_by` for the guard.
- `plugin/session_tasks/markdown.py` `render(board, include_ids=True)` for the agent view.
- `plugin/session_tasks/lineage.py` `SessionResolver.resolve` returning `Resolution.kind` (plain, compression, branch, delegate, reset) and `record_compaction`.

### Established Patterns
- Core package is stdlib only; Hermes imports are lazy and live in thin adapters. The agent half (`__init__.py`) loads as package `hermes_plugins.<slug>`, so relative imports work there.
- One connection per operation through `plugin_db`; no module-level state.
- Tool handlers are plain `def`; `session_id` comes from the handler keyword, never from model arguments (TOOL-06).

### Integration Points
- `__init__.py` `register(ctx)`: two tools, `post_compaction` hook, `pre_tool_call` guard, skill.
- `plugin.yaml` declares the tools and hooks; `hermes plugins validate plugin/` must pass.
- Tests run without a gateway (DEV-02): call the tool handlers directly with a `session_id` keyword and a `tmp_path` HERMES_HOME.

</code_context>

<specifics>
## Specific Ideas

- Success line after an add: `rev 7: added 3 items` then `- [ ] #5 Call John` per changed item.
- When the agent's work finishes an item it checks the item and says so in one line (AGNT-04).
- Block message example: "board_edit: remove of #3 needs Theo's answer. Ask him in chat, then retry with confirmed true."

</specifics>

<deferred>
## Deferred Ideas

- Stale-write transport over HTTP (409 versus structured 200) - Phase 3.
- `pre_llm_call` injection of Theo's edits - Phase 5.
- `board_sessions`, `board_copy` - Phase 6.
- Reorder (BORD-01), pane import (BORD-02) - v2.

</deferred>

---

*Phase: 02-agent-tools-and-skill*
*Context gathered: 2026-10-30*
