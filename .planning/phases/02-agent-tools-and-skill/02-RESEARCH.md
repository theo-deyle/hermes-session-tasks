# Phase 2: Agent tools and skill - Research

**Researched:** 2026-10-30
**Domain:** Hermes Agent v0.22.5 plugin surface (tools, hooks, skills, prompt sections) on devpc
**Confidence:** HIGH on the Hermes contract (read and probed this session), MEDIUM on agent behaviour (live test only)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-11:** Two tools in this phase: `board_read` and `board_edit`. Prefix `board_`. Phase 6 adds `board_sessions` and `board_copy` under the same prefix. - **Reversibility:** costly - the skill, the tool descriptions, the guard and the live test all name the tools; a rename after Phase 2 touches every one.
- **D-12:** No tool name or description contains the word "todo". Each description names `todo_list`, `memory` and `kanban_*` only to say the board is not them.
- **D-13:** A successful `board_edit` returns the new `rev`, a one-line summary, and one markdown line per changed item with its id, in the agent view form from D-04. No full board on success.
- **D-14:** A stale write returns the current `rev`, the stale reason with the op index, and the full board as markdown with ids. The agent merges and retries.
- **D-15:** `board_read` returns the full board as markdown with ids plus the `rev`. An empty board returns the `rev` and an "empty board" line.
- **D-16:** A `BoardError` (empty text, too long, board full, depth, bad parent ref) returns an error that names the op index and the rule. Nothing is written.
- **D-17:** The tool descriptions and the skill carry the ask rule: ask Theo one plain question before a remove, an uncheck, a reword of an item Theo wrote, or a bulk change, and when unsure which item Theo means.
- **D-18:** A `pre_tool_call` hook on `board_edit` is the hard guard. A call that holds a guarded op is blocked unless the arguments carry `confirmed: true`. Guarded ops: `remove` of any item, `uncheck` of any item, and `set_text` of an item whose `updated_by` is `user`. The block message tells the agent to ask Theo in chat first and then retry with `confirmed: true`. No Desktop approval dialog (no `approve` directive). - **Reversibility:** reversible - the hook is one function; switching to `approve` changes one return value.
- **D-19:** Adds and checks in any count pass without a guard. A bulk add is the normal case when the agent lists things for Theo.
- **D-20:** A delegate session (`delegate_task` subagent) resolves to its delegator's root board (Phase 1). In a delegate session `board_read` works and `board_edit` returns an error that tells the subagent to report the items to its delegator. Only the session Theo talks to writes the board. - **Reversibility:** reversible - one check on `Resolution.kind == "delegate"` in the edit tool.

Phase 1 decisions that Phase 2 builds on: D-01 (two levels), D-03 (integer ids never reused), D-04 (agent view `- [ ] #3 Call John`, subtask indent two spaces), D-10 (100 items, 500 characters).

### Claude's Discretion

- Exact description text for both tools: the trigger sentence first ("Add an item when you list something Theo must do, decide or remember"), then the `todo_list` boundary, then the ask rule.
- The operation schema for `board_edit` (an `ops` list mapping one to one to `AddItem`, `SetText`, `SetChecked`, `RemoveItem` from `session_tasks.model`), `base_rev`, and `confirmed`.
- Skill content, `plugin.yaml` fields, `__init__.py` registration, `post_compaction` hook calling `SessionResolver.record_compaction`.
- The live test on devpc: enable the plugin, open a fresh Desktop session, send 5 prompts that list things for Theo, record the call rate. Also the forced `/compress` check from Phase 1 specifics.
- How the planner reads the tool deferral facts: the default `tools.tool_search.defer` list in `hermes_cli/config_defaults.py` names built-ins only, so plugin tools load eagerly unless `~/.hermes/config.yaml` sets an explicit list. Verify on devpc before the live test. **(This reading is wrong. See "Finding 1".)**

### Deferred Ideas (OUT OF SCOPE)

- Stale-write transport over HTTP (409 versus structured 200) - Phase 3.
- `pre_llm_call` injection of Theo's edits - Phase 5.
- `board_sessions`, `board_copy` - Phase 6.
- Reorder (BORD-01), pane import (BORD-02) - v2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TOOL-01 | The agent can read the current session's board as markdown with item ids and the revision | `markdown.render(board, include_ids=True)`; handler returns a JSON string; empty board gives rev 0 with no row |
| TOOL-02 | Add, rename, check, uncheck and remove items in one call with a list of item-level operations; no replace-all | Flat `ops` schema with a 4-value `op` enum; maps to the four op dataclasses; no whole-board property exists |
| TOOL-06 | The tools take the session from the `session_id` Hermes passes to the handler | Dispatcher injects `session_id` only when the handler signature names it; value can be `None` |
| TOOL-07 | Every write returns the new rev, a one-line summary and the needed board content; a stale write returns the current board | `Applied`/`Stale` shapes; result must be a `str`; failure shape needs a top-level `error` key |
| TOOL-08 | Names share one prefix, avoid "todo", never touch `todo_list` | `board_*` has no collision with built-ins (probe); the guard must return at once for every other tool name |
| AGNT-01 | A bundled skill tells the agent the trigger and the `todo_list` boundary | `ctx.register_skill(name, path, description=...)`; plugin skills DO appear in `<available_skills>` (code) |
| AGNT-02 | Tool descriptions carry the trigger and boundary so the board works without the skill | Deferral hides descriptions. Only the first sentence (60 characters) shows. Needs a system prompt section |
| AGNT-03 | One plain question before delete, uncheck, reword of Theo's text, bulk change, or doubt | `pre_tool_call` guard with `confirmed`; hook sees raw uncoerced args in the real agent path |
| AGNT-04 | When the agent's work finishes an item, it checks the item and says so in one line | Rule text in the prompt section and the skill; verified only by the live test |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Source: `/home/theo/local_repo/hermes-session-tasks/.claude/CLAUDE.md` and `~/.claude/CLAUDE.md`.

- Core package is stdlib only. Hermes imports are lazy and live in thin adapters (`paths.connect`, `session_reader.open_session_reader`). The layout guards in `tests/test_layout.py` enforce this on `plugin/session_tasks/`.
- Code runs and tests pass on Python 3.11 and 3.14. No 3.12+ syntax (no `type X = ...` statement, no PEP 695 generics).
- Handlers and hooks are plain `def`. The layout guard fails any `async def` in `plugin/session_tasks/`.
- Tools never read, write, wrap or replace `todo_list`.
- Session id comes from the handler keyword, never from the model's arguments.
- `pyproject.toml` stays outside `plugin/`. `plugin/plugin.yaml` and `plugin/skills/` are allowed by the manifest guard.
- Gateway restart is announced before it happens. It drops live Desktop connections.
- Module budget 300 lines soft, 500 hard (`MAX_MODULE_LINES = 500` in `tests/test_layout.py`). One responsibility per module. Plan the module map first.
- No em dash or en dash in any file. Use a spaced hyphen.
- House gate: `./scripts/check.sh` (ruff check, ruff format --check, pyright, pytest on 3.11 and 3.14, coverage at least 80 percent).
- Output style: ASD-STE100, no option menus, no dev code names in replies to Theo.

## Summary

The Hermes contract for this phase is small and stable: `ctx.register_tool`, `ctx.register_hook`, `ctx.register_skill` and `ctx.register_system_prompt_section` are public, and `hermes plugins validate` checks the manifest against them. A throwaway plugin in a temporary Hermes home confirmed the dispatch path end to end (session id injection, block message, string results, bridge calls, skill index, prompt section).

**Finding 1 (changes the plan).** The CONTEXT note that plugin tools load eagerly is wrong. On Hermes v0.22.5 a plugin tool is deferred by default, and `tools.tool_search.defer: []` does not change that. Both board tools are replaced in the tool array by `tool_search`, `tool_describe` and `tool_call`. The model sees only a catalog line per tool: the name and the first sentence of the description, cut to 60 characters. The ask rule and the `todo_list` boundary in the description body are invisible until the agent calls `tool_describe`. Success criterion 4 (the descriptions carry the rule, no skill load) cannot hold as written. The plugin-only fix is `ctx.register_system_prompt_section`: a bounded, cache-safe block in the system prompt that carries the trigger, the boundary and the ask rule. Keep the descriptions as well (AGNT-02 text) and put the trigger in the first sentence.

**Finding 2.** In the real agent loop, `pre_tool_call` fires before argument coercion. The guard sees the raw model arguments: `ops` can be a JSON string and `confirmed` can be the string `"true"`. Only direct `handle_function_call` coerces first. One shared parser must serve the hook and the handler.

**Finding 3.** A `pre_tool_call` callback that raises blocks that tool call. The hook fires for every tool in the session, so an unguarded exception would block `terminal`, `read_file` and the rest.

**Primary recommendation:** Build `board_read` and `board_edit` as plain-`def` handlers over a small service (resolver + store) built in `register(ctx)`. Return JSON strings. Add a prompt section for the ambient rule. Guard with one pure function shared by the hook and the handler. Run the 5-prompt live test headlessly with `hermes chat --oneshot` first, then once on Desktop.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tool schemas and descriptions | Agent half (`plugin/__init__.py` wiring, `session_tasks` data module) | - | Static text, never changes per session (prompt cache) |
| Session to board resolution | Core (`SessionResolver`) | Hermes `state.db` read-only adapter | Phase 1 owns it; handlers call `resolve(session_id)` |
| Board write and stale rule | Core (`BoardStore.apply`) | SQLite via `plugin_db` | Phase 1 owns it; Phase 2 only maps arguments to ops |
| Ask-before-destroy guard | Hermes hook layer (`pre_tool_call`) | Pure function in core | Hook is the hard gate (D-18); logic stays testable without Hermes |
| Ambient trigger and boundary text | Hermes system prompt section | Skill index line, tool first sentence | Deferral hides tool bodies; the prompt section is always in view |
| Compression alias | Hermes hook layer (`post_compaction`) | Core `record_compaction` | Hook only forwards two ids |
| Live pane refresh after a write | Phase 3 (event broadcast) | - | Not in this phase; leave a seam |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`json`, `inspect`-free closures, `dataclasses`) | 3.11 and 3.14 | Handlers, parser, guard, result text | House rule: core is stdlib only |
| Hermes plugin API | v0.22.5 | `register_tool`, `register_hook`, `register_skill`, `register_system_prompt_section` | Public contract in `website/docs/developer-guide/plugins/index.md` and `website/docs/user-guide/features/hooks.md` |
| Phase 1 core (`BoardStore`, `SessionResolver`, `markdown.render`, `paths`, `session_reader`) | in repo | Storage, identity, agent view | Already built and tested |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 (pinned in `pyproject.toml`) | Tests | All handler, hook and parser tests |
| pytest-cov | 7.1.0 | Coverage gate | `scripts/check.sh` on 3.11 |
| `hermes plugins validate` | v0.22.5 | Manifest and registration gate | Once per plan, with the default `HERMES_HOME` |
| `hermes plugins doctor <path> --ci` | v0.22.5 | Real runtime contract check in a temporary home | Once at phase end |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Prompt section for the ambient rule | `tools.tool_search.enabled: off` in `~/.hermes/config.yaml` | Works, but it changes every tool in every session (more schema tokens). That is Theo's cost call, not a plugin change. Keep as the fallback if the live test shows a low call rate. |
| JSON string results | Plain text results | Plain text is judged by a text heuristic (`has_failure_marker`). An item text with a quoted "error" can flag a good call as failed. A JSON object is judged by its top-level shape only. |
| `approve` directive | `block` plus `confirmed` | Locked by D-18. `approve` uses the human approval gate and its `[a]lways` choice can bypass the guard forever. |

**Installation:** none. No external package. `plugin.yaml` has no `python_dependencies`.

**Version verification:** `hermes --version` printed `Hermes Agent v0.22.5 (2026.9.24)`. `pyproject.toml` pins were read this session.

## Package Legitimacy Audit

No external package is installed or recommended in this phase. The audit is empty by design.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| none | - | - | - | - | - | - |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Desktop session (model: claude-sonnet-5-5 through the directsdk provider)
  |
  | system prompt (frozen at session start)
  |   - plugin prompt section "hermes-session-tasks.board-rules"  <- ambient trigger, boundary, ask rule
  |   - <available_skills> line "hermes-session-tasks:board-rules" <- skill description
  |   - tool_search catalog: "task-board tools (2): board_edit, board_read" (first sentence only)
  v
model emits board_edit (direct, or wrapped in tool_call)
  |
  v
Hermes agent loop (agent/tool_executor.py)
  |-- pre_tool_call hooks (EVERY tool, raw args, session_id kw)
  |      our guard: tool_name != board_edit -> return None at once
  |      board_edit -> parse raw args -> guarded ops? -> block {"error": msg} unless confirmed
  v
model_tools.handle_function_call -> coerce_tool_args -> registry.dispatch
  |-- handler(args, session_id=<agent.session_id or None>)
  v
board tools (plain def)
  1. session_id blank -> error
  2. resolver.resolve(session_id) -> Resolution(root_id, kind)
  3. board_read -> store.get_board(root_id) -> render ids -> JSON string
  4. board_edit -> kind == "delegate" -> error
                -> parse ops -> store.apply(root_id, ops, actor="agent", base_rev=...)
                -> Applied -> {rev, summary, changed lines}
                -> Stale   -> {error, rev, reason, op_index, board}
                -> BoardError -> {error: "op N: rule"}
  v
SQLite plugin file (plugin_db)           post_compaction(session_id, old_session_id) -> record_compaction
```

### Recommended Project Structure

New files only (Phase 1 modules stay as they are). Each module has one job and stays under 300 lines.

```
plugin/
  plugin.yaml                     # manifest: name, version, description, requires_hermes, provides_tools, provides_hooks
  __init__.py                     # register(ctx) only: build service, wire tools, hooks, skill, prompt section
  skills/board-rules/SKILL.md     # AGNT-01 skill body
  session_tasks/
    tool_text.py                  # static strings: descriptions, schemas, prompt section text, skill description
    edit_args.py                  # parse raw or coerced board_edit args -> ParsedEdit (ops, base_rev, confirmed); pure
    guard.py                      # guarded_reasons(parsed, board) and block_message(reasons); pure
    results.py                    # success, stale and error JSON strings; pure
    board_tools.py                # BoardTools: board_read and board_edit handler closures over resolver + store
    hooks.py                      # pre_tool_call guard and post_compaction callbacks, built from the service
tests/
  test_edit_args.py  test_guard.py  test_results.py  test_board_tools.py
  test_register.py   test_tool_text.py  test_hooks.py  test_hermes_dispatch.py (marker hermes)
```

`plugin/__init__.py` sits outside `CORE_DIR`, so the stdlib-only guards do not scan it. It imports no Hermes module either (`ctx` is passed in). Hermes is reached only through `paths.connect` and `session_reader.open_session_reader`, both already lazy.

### Pattern 1: Service built in `register(ctx)`, handlers as closures

**What:** `register(ctx)` builds `BoardStore(paths.connect)` and `SessionResolver(paths.connect, session_reader.open_session_reader)`. It passes them to `BoardTools`. The handlers are bound methods or closures with a fixed signature. No module-level state (Phase 1 rule).
**When to use:** always. Tests call `BoardTools(store, resolver)` with `tmp_path` factories and the fakes in `tests/fakes.py`.

```python
# Source: signatures read in plugin/session_tasks/store.py, lineage.py, paths.py this session
def register(ctx) -> None:
    from .session_tasks import board_tools, hooks, paths, session_reader, tool_text
    from .session_tasks.lineage import SessionResolver
    from .session_tasks.store import BoardStore

    store = BoardStore(paths.connect)
    resolver = SessionResolver(paths.connect, session_reader.open_session_reader)
    tools = board_tools.BoardTools(store, resolver)
    ctx.register_tool(
        name="board_read", toolset=tool_text.TOOLSET, schema=tool_text.BOARD_READ_SCHEMA,
        handler=tools.board_read, emoji="\U0001F4CB",
    )
    ctx.register_tool(
        name="board_edit", toolset=tool_text.TOOLSET, schema=tool_text.BOARD_EDIT_SCHEMA,
        handler=tools.board_edit, emoji="\U0001F4CB",
    )
    ctx.register_hook("pre_tool_call", hooks.make_pre_tool_call(store, resolver))
    ctx.register_hook("post_compaction", hooks.make_post_compaction(resolver))
    ctx.register_system_prompt_section(
        tool_text.PROMPT_SECTION_ID, tool_text.PROMPT_SECTION_TEXT, max_chars=tool_text.PROMPT_SECTION_MAX
    )
    ctx.register_skill(
        "board-rules", Path(__file__).resolve().parent / "skills" / "board-rules" / "SKILL.md",
        description=tool_text.SKILL_DESCRIPTION,
    )
```

The relative import inside `register` works because the agent half loads as package `hermes_plugins.<slug>` (`.claude/CLAUDE.md` fact, `hermes_cli/plugins_loader.py:701-740`). A top-level relative import is also fine; the lazy form keeps `import` side-effect free.

### Pattern 2: One parser for the hook and the handler

**What:** `edit_args.parse(args)` accepts the raw form (`ops` as a JSON string, `confirmed` as `"true"`) and the coerced form (`ops` as a list, `confirmed` as a bool). It returns a frozen `ParsedEdit` or raises a `BoardError` subclass that carries the op index. The handler and the guard both call it. A drift between the two is then impossible.
**Why:** see Finding 2. `coerce_tool_args` runs at `model_tools.py:889`, inside `handle_function_call`. The agent loop fires `pre_tool_call` first with `skip_pre_tool_call_hook=True` on the later call (`agent/tool_executor.py:671-686`, `1730`).

### Pattern 3: Flat op schema with a discriminator

**What:** `ops` is an array of flat objects. Each object has `op` (enum) and optional fields. No `oneOf` and no top-level combinator (the sanitizer forbids top-level `allOf/anyOf/oneOf/enum/not`, `tools/schema_sanitizer.py:175`). Do not use `type: ["integer", "null"]` (the sanitizer rewrites type arrays).
**Fields:** `op` in `add | set_text | set_checked | remove`; `text` (string); `item_id` (integer, an existing item); `checked` (boolean); `parent_id` (integer, an existing top-level item); `parent_ref` (integer, 0-based index of an earlier `add` in the same `ops` list). Top-level properties: `ops` (required), `base_rev` (integer), `confirmed` (boolean). No `session_id` property.
**Reliability aids:** put one worked example in the `ops` description; state per op which fields are required; reject unknown keys with an error that names the op index. Hermes already repairs a JSON-string `ops` and a bare object where a list is expected (`tools/arg_coercion.py:40-87`), but only after the hook ran.
**`base_rev` rule (recommended):** required when any op targets an existing item (`set_text`, `set_checked`, `remove`, `add` with `parent_id`). Optional when every op is a top-level `add` or uses `parent_ref`. Reason: `revision.is_stale` returns False for a top-level add (`revision.py:29-31`), and a guessed base rev would hide Theo's edits. Error text: "base_rev is required when an op targets an existing item. Call board_read first."

### Pattern 4: Guard as a pure function

```python
# Source: model.py and revision.py (read this session); hook contract from hooks.md:548-594
def guarded_reasons(parsed: ParsedEdit, board: Board | None) -> list[str]:
    reasons: list[str] = []
    for index, op in enumerate(parsed.ops):
        if isinstance(op, RemoveItem):
            reasons.append(f"remove of #{op.item_id}")
        elif isinstance(op, SetChecked) and not op.checked:
            reasons.append(f"uncheck of #{op.item_id}")
        elif isinstance(op, SetText) and board is not None:
            item = board.item(op.item_id)
            if item is not None and item.updated_by == "user":
                reasons.append(f"reword of #{op.item_id}")
    return reasons
```

The hook reads the board only when a `SetText` op is present (one `resolve` plus one `get_board`). `remove` and `uncheck` need no read.

```python
def make_pre_tool_call(store, resolver):
    def pre_tool_call(tool_name, args, session_id="", **kwargs):
        if tool_name != "board_edit":
            return None                      # never raise, never read, for any other tool
        try:
            parsed = edit_args.parse(args)
            ...                              # resolve only when a SetText op exists
        except BoardError:
            return None                      # the handler returns the precise error
        except Exception:
            log.exception("board guard failed")
            return {"action": "block", "message": "board_edit: the guard could not check this call. Try again."}
        ...
    return pre_tool_call
```

Block text example (from CONTEXT specifics): `board_edit: remove of #3 needs Theo's answer. Ask him in chat, then retry with confirmed true.` Hermes returns it to the model as `{"error": "<message>"}` (probe output, `tools/registry.py:1075-1078` `tool_error`).

### Anti-Patterns to Avoid

- **A guard that can raise for other tools.** It blocks every tool (Finding 3).
- **Reading `args["session_id"]`.** TOOL-06. The model can send it; the schema must not declare it; the handler must ignore it.
- **Returning a dict from a handler.** `_normalize_handler_result` turns a plain dict into an error (`tools/registry.py:929-944`). Return `json.dumps(...)`.
- **Putting the rule only in the tool description body.** Deferral hides it (Finding 1).
- **Dynamic text in a schema or description.** Item counts or session ids break prompt caching (`.planning/research/PITFALLS.md` P-list item 5).
- **Wrapping or importing `todo_list`.** Out of scope and forbidden.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| String and JSON repair of model arguments | A second coercion layer for the handler | Hermes `coerce_tool_args` (runs before the handler) plus one tolerant `edit_args.parse` for the hook | Hermes already parses JSON-string arrays and `"true"` booleans |
| Session identity | Any session lookup from tool arguments | `SessionResolver.resolve(session_id)` | Phase 1, tested |
| Concurrency and stale rule | A lock or revision logic in the tool | `BoardStore.apply(..., base_rev=...)` | Phase 1, tested with two processes |
| Markdown agent view | A new renderer | `markdown.render(board, include_ids=True)` | Phase 1; it escapes text that looks like `#id` |
| Text cleaning | A second sanitiser | `model.clean_text` inside the store | The store already cleans on write |
| Tool-result size limit | A truncation routine | Hermes default (100,000 characters per result) | A full board is at most about 52,000 characters (100 items x 500 plus ids) |
| Human approval dialog | A confirm UI | `block` plus `confirmed` (D-18) | Locked |

**Key insight:** this phase is argument mapping, result text and two hooks. Every hard problem (identity, concurrency, rendering) is already solved in Phase 1.

## Common Pitfalls

### Pitfall 1: The board tools are invisible to the model
**What goes wrong:** the agent lists items in chat and never calls the board.
**Why it happens:** plugin tools are deferrable. `is_deferrable_tool_name` returns True for any tool that is not in `_HERMES_CORE_TOOLS` and whose toolset is not in `_DIRECT_SURFACE_TOOLSETS` (`tools/tool_search.py:150-162`, set at line 140). The probe confirmed it for toolset `probe-board` with the default list and with `defer: []`. Only `enabled: off` keeps them eager. `todo_list` is deferred too (it is in the default `defer` list, `hermes_cli/config_defaults.py:2032-2039`).
**How to avoid:** (1) register a prompt section; (2) keep the first sentence of each description at or under 60 characters and put the trigger in it; (3) keep the skill description as the third layer; (4) measure with the live test.
**Warning signs:** the transcript shows markdown checklists in chat, or `tool_call` bridge entries with no `board_edit`.

### Pitfall 2: The first sentence is cut
**What goes wrong:** the catalog shows `Add an item when you list something Theo must…`.
**Why:** `_short_desc` takes the first sentence (ends at `.`, `!` or `?` followed by a space) and clips it to 60 characters on a word boundary (`tools/tool_search_catalog.py:215-227`).
**How to avoid:** a test that takes the first sentence of each description and asserts `len <= 60` and no early period. Candidates measured this session: `Add to Theo's board what he must do, decide or remember.` (56) and `Read Theo's task board with item ids and the revision.` (54). The CONTEXT trigger sentence is 68 characters and would be cut.

### Pitfall 3: Raw arguments in the hook
**What goes wrong:** the guard checks `isinstance(args["ops"], list)`, sees a string, finds no `remove`, and lets a delete through.
**Why:** coercion happens after the hook in the agent loop (Finding 2).
**How to avoid:** `edit_args.parse` accepts both forms. Test with `ops` as a JSON string, and with `confirmed` as `"true"` and `"True"`.

### Pitfall 4: Guard exception blocks everything
**What goes wrong:** a bug in the guard blocks `terminal` and every other tool until restart.
**Why:** a raising `pre_tool_call` callback is turned into a block directive for that call (`hermes_cli/plugins_dispatch.py:290-293`).
**How to avoid:** return `None` on the first line for any other tool name; wrap the board path in `try/except`; test that a non-board tool name returns `None` with a broken service.

### Pitfall 5: `session_id` can be `None`
**What goes wrong:** `check_session_id(None)` raises `InvalidSession` inside the handler.
**Why:** `handle_function_call` passes `session_id=None` when the caller gave none. The probe showed `"session_id": null` for a direct call with no id. The agent loop passes `agent.session_id or ""`.
**How to avoid:** declare `session_id: str | None = None`; treat `None` and blank as an error result: `{"error": "no session id; the board is not available here"}`.

### Pitfall 6: `changed_ids` includes removed items
**What goes wrong:** the summary or the changed-lines code looks up a removed id on the new board and crashes or prints nothing.
**Why:** `_remove` journals the removed item and its subtasks, and `journal` appends each id to `changed` (`store.py:164-172`, `65-69`).
**How to avoid:** for each id in `Applied.changed_ids`, `board.item(id)` returning `None` means removed: print `- removed #4`. Count the summary from the submitted ops. When `changed_ids` is empty print `rev N: no change` (`store.py:236-237` returns the old rev).

### Pitfall 7: `updated_by` is conservative
**What goes wrong:** the agent adds an item, Theo checks it in the pane, and the agent must now confirm a reword.
**Why:** `_touch` sets `updated_by` to the actor of the last change (`store.py:131-142`). Any touch by Theo makes the item "Theo's".
**How to avoid:** accept it. It errs toward asking, which is the safe side. Say so in the skill.

### Pitfall 8: The rest of the world uses the name "todo"
**What goes wrong:** D-12 says no description contains "todo" and also says each description names `todo_list`. Both cannot hold.
**How to avoid:** read D-12 as "no tool NAME contains todo; a description may name `todo_list` once, in the boundary sentence". Test both halves. See Open Question 2.

### Pitfall 9: A temporary `HERMES_HOME` with the `hermes` CLI builds a runtime
**What goes wrong:** `hermes plugins validate` with `HERMES_HOME` set to an empty directory printed "Installing Python dependencies" and left an 876 MB runtime in that directory (observed, then deleted).
**How to avoid:** run `hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin` and `hermes plugins doctor ... --ci` with the real `HERMES_HOME`. Both use their own temporary home for the probe. Use a temporary `HERMES_HOME` only with the gateway venv Python (no `hermes` CLI), as the probe did.

### Pitfall 10: Compressed delegate session loses its delegate kind
**What goes wrong:** a compression child of a delegate session resolves as `compression`, not `delegate`, so `board_edit` would write the delegator's board.
**Why:** `_compression` returns kind `"compression"` even when the chain root is a delegate (`lineage.py:177-193`), and the alias then answers `"compression"` (`lineage.py:156-159`).
**Impact:** LOW. `compression.in_place` defaults to True (`hermes_cli/config_defaults.py:700`) and `~/.hermes/config.yaml` has no override, so session ids do not rotate on devpc. Record it; do not fix it in Phase 2.

## Code Examples

### plugin.yaml (validated shape)

```yaml
# Source: manifest of the throwaway probe passed `hermes plugins validate` (all checks green);
# requires_hermes format as used in ~/.hermes/plugins/agent-importers/plugin.yaml
name: hermes-session-tasks
version: 0.2.0
description: A per-session task board for Theo. The agent adds things Theo must do, decide or remember; Theo edits them in a Desktop pane.
requires_hermes: ">=0.22.5"
provides_tools:
  - board_read
  - board_edit
provides_hooks:
  - pre_tool_call
  - post_compaction
```

`hermes plugins validate` compares `provides_tools` and `provides_hooks` with what `register()` records, and fails on an undeclared tool or hook (`hermes_cli/plugin_validate.py:430-447`). The prompt section and the skill are not checked.

### Handler signature and result strings

```python
# Source: plugins/index.md:876-882 and tools/registry.py:1086-1096 (_kwargs_accepted_by); probe output
def board_edit(self, args: dict, session_id: str | None = None, **kwargs) -> str:
    ...
    return json.dumps(result, ensure_ascii=False)   # always a str
```

Result shapes (recommended; JSON keys match D-13 to D-16):

```json
{"ok": true, "rev": 7, "summary": "rev 7: added 3 items",
 "changed": ["- [ ] #5 Call John", "- [ ] #6 Book the van", "  - [ ] #7 Ask about the quote"]}
```
```json
{"error": "stale: #3 changed after rev 4 (op 1)", "stale": true, "reason": "stale", "op_index": 1,
 "rev": 6, "board": "- [ ] #3 Call John\n- [x] #4 Book the van\n"}
```
```json
{"error": "op 2: item text is empty"}
```

Failure results carry a top-level `error` key so Hermes records the call as failed (`agent/display.py:1065-1072`). A success object has no `error` key. `board_read` returns `{"ok": true, "rev": N, "board": "<markdown>"}` and, for an empty board, `{"ok": true, "rev": N, "board": "", "note": "empty board"}`.

### Fake ctx test (no gateway)

```python
# Source: validate probe RecordingContext, hermes_cli/plugin_validate.py:227-268
class FakeCtx:
    def __init__(self) -> None:
        self.tools: dict[str, dict] = {}
        self.hooks: dict[str, list] = {}
        self.skills: list[tuple] = []
        self.sections: list[tuple] = []

    def register_tool(self, name, toolset, schema, handler, **kw):
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler, **kw}

    def register_hook(self, hook_name, callback):
        self.hooks.setdefault(hook_name, []).append(callback)

    def register_skill(self, name, path, description="", frontmatter=None):
        self.skills.append((name, path, description))

    def register_system_prompt_section(self, id, content, *, position="after_memory", max_chars=4000):
        self.sections.append((id, content, max_chars))
```

Handler tests build `BoardTools(store, resolver)` from the existing `store` and `resolver_for` fixtures and call `tools.board_edit({...}, session_id="s1")`. `HERMES_HOME` is already a tmp dir through the autouse `hermes_home` fixture in `tests/conftest.py`.

### Hermes dispatch contract test (marker `hermes`)

Follow the Phase 1 pattern (`tests/test_hermes_contract.py` plus a snippet run by `~/.hermes/hermes-agent/venv/bin/python`, which has no pytest). The snippet creates a temporary `HERMES_HOME`, symlinks `plugin/` as `plugins/hermes-session-tasks`, writes `config.yaml` with `plugins.enabled`, then runs `discover_plugins()`, `get_tool_definitions(...)`, `handle_function_call(...)` and prints one JSON object. The probe in this session did exactly that in a few seconds.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Docs say plugin skills are not in the system prompt | Code lists them in `<available_skills>` (`agent/prompt_builder.py:1200-1229`) | stale doc at `plugins/index.md:1206` | Skill description is a real third layer |
| Tool schemas always in the request | Tool search defers plugin tools by default | v0.22.x | Descriptions are not ambient |
| `pre_llm_call` injection for always-on rules | `register_system_prompt_section` (cache-safe, frozen per session) | v0.22.x, `hooks.md:403-447` | Right place for the ambient rule |

**Deprecated/outdated:** the `shutil.copy2` skill copy pattern. Use `ctx.register_skill`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `requires_hermes: ">=0.22.5"` is the right floor (only 0.22.5 was tested) | plugin.yaml | A too-high floor blocks older installs; Theo runs 0.22.5, so none |
| A2 | Toolset name `task-board` reads better in the catalog than `hermes-session-tasks` | Pattern 1 | Cosmetic. The catalog group label is the toolset name (probe) |
| A3 | A cap of 100 ops per call (equal to `MAX_ITEMS`) is a safe input bound | Pattern 3 | A model that needs more ops splits the call; no data risk |
| A4 | JSON string results are better for the model than plain text | Code Examples | Slightly more tokens; failure marking is safer (verified code) |
| A5 | The prompt section lifts the call rate enough without `enabled: off` | Summary | Live test shows a low rate; then Theo decides on `enabled: off` |
| A6 | `hermes chat --oneshot` uses the same toolsets and deferral as Desktop | Validation | The headless rate differs from Desktop; run one Desktop pass to confirm |
| A7 | The first-sentence wording `Add to Theo's board what he must do, decide or remember.` triggers calls | Pitfall 2 | Low rate; reword and retest |

## Open Questions

1. **Does the prompt section replace the need to turn tool search off?**
   - What we know: deferral is verified; the section is documented and probed; the earlier research (P9) measured `clarify` falling from 18 of 18 to 7 of 18 when deferred.
   - What is unclear: the call rate of this model with the section and a deferred tool.
   - Recommendation: build the section now; run the 5 prompts; if fewer than 5 of 5 call the board, ask Theo one cost question about `tools.tool_search.enabled: off`.
2. **D-12 wording conflict.** D-12 forbids "todo" in descriptions and also requires each description to name `todo_list`. Recommendation: names carry no "todo"; one `todo_list` mention per description inside the boundary sentence.
3. **Phase 3 event seam.** API-02 (broadcast on every write) belongs to Phase 3. Recommendation: keep one `after_write` callable parameter on `BoardTools` (default no-op) so Phase 3 adds the broadcast without editing the handler.
4. **Live test route.** The criterion says a fresh Desktop session. Recommendation: Claude runs the 5 prompts with `hermes chat --query-file <file> --oneshot -Q --format stream-json` (one process per prompt, real model, real plugin), reads `data.db`, then Theo does one Desktop check. The Desktop gateway restart must be announced first.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Hermes Agent | tools, hooks, validate | yes | v0.22.5 (2026.9.24) | - |
| Gateway venv Python | contract snippet, probe | yes | 3.11.16 | - |
| `hermes plugins validate` and `doctor` | manifest gate | yes | v0.22.5 | - |
| `hermes chat --oneshot --format stream-json` | headless live test | yes (flags listed in `--help`) | v0.22.5 | Desktop-only test |
| uv, pytest, ruff, pyright | house gate | yes (Phase 1 ran `check.sh`) | per `pyproject.toml` | - |
| `~/.hermes/config.yaml` | toolset and deferral facts | yes | read only | - |

Facts read from `~/.hermes/config.yaml` on devpc: no `tools.tool_search` key (defaults apply); `platform_toolsets.cli` is an explicit list without any board toolset; `known_plugin_toolsets.cli` is `[a2a, spotify]`; `plugins.enabled` does not yet list `hermes-session-tasks`; `agent.disabled_toolsets` holds `bfl, desktop_ui, discord, discord_admin, feishu_doc, feishu_drive, project, search, spotify, stt, video, video_gen, x_search, yuanbao`; no `compression.in_place` key (default True); model `claude-sonnet-5-5[1m]` through provider `claude-subscription-directsdk-experimental`.

Desktop uses `platform_toolsets.cli` (`tui_gateway/agent_factory.py:424`). A plugin toolset is on for that platform unless it is in `known_plugin_toolsets.cli` and absent from the saved list (`hermes_cli/tools_config.py:527-534`). A new `task-board` toolset is not in that list, so it is on. Saving `hermes tools` later writes `known_plugin_toolsets`; if the new toolset is not in the saved list at that moment, it turns off. Check after any `hermes tools` save.

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 through uv (`pyproject.toml`), `--import-mode=importlib --strict-markers`, `filterwarnings = ["error"]` |
| Config file | `/home/theo/local_repo/hermes-session-tasks/pyproject.toml` (`pythonpath = ["plugin", "tests"]`, marker `hermes`) |
| Quick run command | `uv run pytest tests/test_edit_args.py tests/test_guard.py tests/test_results.py tests/test_board_tools.py tests/test_register.py tests/test_tool_text.py tests/test_hooks.py -q` |
| Full suite command | `./scripts/check.sh` (3.11 with coverage at least 80 percent, then 3.14) |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-01 | `board_read` returns ids, rev, and an empty-board note; works in a delegate session | unit | `uv run pytest tests/test_board_tools.py -k read -q` | Wave 0 |
| TOOL-02 | Each op and a mixed batch apply; `parent_ref` works; the `op` enum has exactly four values; no whole-board property exists in the schema | unit | `uv run pytest tests/test_board_tools.py tests/test_tool_text.py -k "ops or schema" -q` | Wave 0 |
| TOOL-06 | Handler uses the keyword session; `args={"session_id": "evil"}` changes nothing; schema has no `session_id`; no source file reads `args["session_id"]` (AST test); Hermes passes the id | unit + hermes contract | `uv run pytest tests/test_board_tools.py tests/test_tool_text.py -k session -q`; `uv run pytest -m hermes tests/test_hermes_dispatch.py -q` | Wave 0 |
| TOOL-07 | Success, stale (full board, op index), `BoardError` and blank-session shapes; failures carry `error`; successes do not | unit | `uv run pytest tests/test_results.py tests/test_board_tools.py -q` | Wave 0 |
| TOOL-08 | Names start with `board_` and hold no "todo"; one `todo_list` mention per description; `hermes plugins validate` passes (no collision); no module imports or calls the todo tool | unit + gate | `uv run pytest tests/test_tool_text.py tests/test_register.py -q`; `hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin` | Wave 0 |
| AGNT-01 | `SKILL.md` exists with frontmatter; `register_skill` gets name, path and description; text holds the trigger, the `todo_list` boundary, the ask rule and the check-and-say rule | unit | `uv run pytest tests/test_register.py tests/test_tool_text.py -k skill -q` | Wave 0 |
| AGNT-02 | Each description's first sentence is at most 60 characters and holds the trigger; the prompt section is registered, non-empty and at most 4,000 characters (target under 1,000); live: 5 of 5 prompts add items | unit + live | `uv run pytest tests/test_tool_text.py -q`; live protocol below | Wave 0 |
| AGNT-03 | Guard blocks `remove`, uncheck, and `set_text` on a user item; `confirmed` as `true`, `"true"` and `"True"` passes; `ops` as a JSON string is parsed; adds and checks pass in any count; a non-board tool returns `None` with a broken service; a malformed call does not raise; live: the agent asks one plain question first | unit + live | `uv run pytest tests/test_guard.py tests/test_hooks.py -q`; live protocol below | Wave 0 |
| AGNT-04 | Rule text present (unit); live: after work that finishes an item, the board shows it checked and the reply has one line saying so | unit + live | `uv run pytest tests/test_tool_text.py -k finish -q`; live protocol below | Wave 0 |
| (hook) | `post_compaction` forwards ids to `record_compaction`; empty `old_session_id` does no I/O; the hook never raises | unit | `uv run pytest tests/test_hooks.py -k compaction -q` | Wave 0 |
| (gate) | Manifest, loadable, declared tools and hooks match, no collisions | gate | `hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin` and `hermes plugins doctor /home/theo/local_repo/hermes-session-tasks/plugin --ci` | n/a |

### Live test protocol (needs the real Hermes and the real model)

Preconditions, in this order: announce the gateway restart; symlink `plugin/` into `~/.hermes/plugins/hermes-session-tasks`; `hermes plugins enable hermes-session-tasks`; restart the gateway; check the toolset is on with `_get_platform_tools(load_config(), "cli")` through the gateway venv Python.

1. Run 5 prompts that list things for Theo, one fresh session each. Headless form: `hermes chat --query-file <prompt file> --oneshot -Q --format stream-json`. Claude runs this and reads the stream and `data.db`. Pass: the 5 runs hold 5 `board_edit` adds (bridge or direct) and no item landed only in `todo_list`.
2. Run one prompt that gives the agent its own multi-step job. Pass: it uses `todo_list`, not the board.
3. Seed an item, then ask the agent to remove it. Pass: the first `board_edit` is blocked or never sent, and the final reply is one plain question.
4. Seed an item, then give work that finishes it. Pass: the item is checked and the reply says so in one line.
5. Run `/compress` in one Desktop session and read the board after it (Phase 1 carry-over). With `compression.in_place` True the id should not change.
6. One Desktop pass by Theo: a fresh session, one list prompt, then ask Claude to read the board row. This is the only step that needs Theo (it needs his Desktop session).

Record the call rate in the SUMMARY. A rate under 5 of 5 raises Open Question 1.

### Sampling Rate

- **Per task commit:** the quick run command above.
- **Per wave merge:** `./scripts/check.sh`.
- **Phase gate:** full suite green, `hermes plugins validate` and `doctor --ci` green, live protocol recorded, before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_edit_args.py` - raw and coerced forms, unknown keys, bool-as-int, op cap (TOOL-02)
- [ ] `tests/test_guard.py` - guard matrix (AGNT-03)
- [ ] `tests/test_results.py` - result shapes (TOOL-07)
- [ ] `tests/test_board_tools.py` - handlers with the `store` and `resolver_for` fixtures, delegate case (TOOL-01, TOOL-02, TOOL-06, D-20)
- [ ] `tests/test_tool_text.py` - first sentence length, names, boundary text, prompt section size (TOOL-08, AGNT-01, AGNT-02, AGNT-04)
- [ ] `tests/test_register.py` and `tests/test_hooks.py` - `FakeCtx` (add to `tests/fakes.py`), registrations, hook safety
- [ ] `tests/test_hermes_dispatch.py` plus a snippet script - real registry dispatch, marker `hermes`
- [ ] Update the layout guard test so new `session_tasks` modules are scanned (automatic: `CORE_DIR` is the whole directory)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Hermes owns the session; no credential in this phase |
| V3 Session Management | yes | Session id from the handler keyword only (TOOL-06); blank id is an error |
| V4 Access Control | yes | One board per session root; delegate sessions cannot write (D-20); other tools untouched by the guard |
| V5 Input Validation | yes | Strict `edit_args.parse`: op enum, integer types without bool, unknown keys rejected, ops cap, store `clean_text` and caps |
| V6 Cryptography | no | None |
| V7 Error Handling and Logging | yes | Errors name the op and the rule; no path or SQL in a result; log without item text |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Model passes a foreign `session_id` in args | Spoofing / Elevation | Handler ignores `args["session_id"]`; schema omits it; AST test |
| Model passes `confirmed: true` with no question to Theo | Tampering | The flag is a forcing function, not a security boundary. Say so in the skill. The first blocked call returns the instruction to ask. The live test checks the question happens |
| Item text with a fake `#id` or a second checklist line | Tampering | Phase 1 `sanitize_text` and the render escape |
| Stored item text read back by the model as instructions | Tampering / Injection | Phase 1 sanitises on write; Phase 5 adds delta injection. In `board_read`, label the output as Theo's list, not instructions |
| Guard exception blocks all tools | Denial of service | Early return for other names; try/except around the board path |
| Oversized `ops` list | Denial of service | Ops cap; store caps 100 items; one `BEGIN IMMEDIATE` per call |
| Hook runs on every tool call (latency) | Denial of service | No I/O unless the tool is `board_edit` and an op is `set_text` |

## Sources

### Primary (HIGH confidence)

All read or run on devpc 2026-10-30, Hermes v0.22.5 at `/home/theo/.hermes/hermes-agent`.

- `hermes_cli/plugins.py:462-499` (`register_tool`), `943-945` (`register_hook`), `967-990` (`register_system_prompt_section`), `1841-2061` (`pre_tool_call` directive scan, block, approve, modify, timeout)
- `hermes_cli/plugins_dispatch.py:256-294` (`invoke_hook`, fail-closed for `pre_tool_call`), `79-81` (section limits), `583-625` (section rendering)
- `hermes_cli/plugins_content.py:23-56` (`register_skill`)
- `tools/registry.py:709-779` (`register`), `929-966` (`_normalize_handler_result`, `dispatch`), `1075-1096` (`tool_error`, `_kwargs_accepted_by`)
- `model_tools.py:766-801` (`_pre_dispatch_guards`), `823-846` (`_execute_tool`, `session_id` and `task_id` injection), `873-966` (`handle_function_call`, bridge unwrap)
- `tools/arg_coercion.py:21-87`, `tools/schema_sanitizer.py:175`
- `agent/tool_executor.py:671-686`, `1722-1735` (hook before coercion; `session_id=agent.session_id or ""`)
- `tools/tool_search.py:140-162`, `343-378`; `tools/tool_search_catalog.py:215-227`; `hermes_cli/config_defaults.py:2000-2045` (defer list), `695-700` (`in_place`)
- `hermes_cli/tools_config.py:527-534`, `578-653`; `tui_gateway/agent_factory.py:390-440`
- `agent/prompt_builder.py:1200-1229` (plugin skills in `<available_skills>`), `1362-1382` (index wording)
- `agent/display.py:1039-1082`, `agent/tool_result_classification.py:33-57` (failure classification)
- `gateway/session_mutation_compress.py:103-115`, `agent/compaction_events.py:239-262` (`post_compaction` on `/compress`)
- `tools/delegate_tool.py:343` (`_delegate_from` marker), `tools/delegate_tool.py:470` (children inherit the parent toolsets)
- `hermes_cli/plugin_validate.py:227-268`, `395-453`, `497-559` (gate checks)
- `website/docs/user-guide/features/hooks.md:403-447, 548-594, 1118-1141`; `website/docs/developer-guide/plugins/index.md:347-369, 876-882, 1165-1206`; `website/docs/user-guide/features/tool-search.md`
- This repo: `plugin/session_tasks/model.py`, `store.py`, `revision.py`, `lineage.py`, `markdown.py`, `paths.py`, `session_reader.py`; `tests/conftest.py`, `tests/test_layout.py`, `tests/test_hermes_contract.py`; `pyproject.toml`
- `~/.hermes/config.yaml` (read only); `~/.hermes/plugins/agent-importers/` and `homeassistant/` (manifest and registration style)
- Executed probes: a throwaway plugin in a temporary `HERMES_HOME` (deleted) ran `discover_plugins`, `_get_platform_tools`, `get_tool_definitions`, `handle_function_call` (direct and through `tool_call`), `invoke_hook("post_compaction", ...)`, `render_system_prompt_sections`, and `hermes plugins validate`. A second probe ran `classify_tools` and `assemble_tool_defs` with default config, `defer: []`, and `enabled: off`.

### Secondary (MEDIUM confidence)

- `.planning/research/PITFALLS.md` P9 and P10 (deferral risk, plugin skill index): consistent with the code read above.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no external package; Hermes API read and probed.
- Architecture: HIGH - every integration point was run once in a probe.
- Pitfalls: HIGH for the Hermes behaviour, MEDIUM for model behaviour (live test decides).

**Research date:** 2026-10-30
**Valid until:** 2026-11-13 (14 days; re-check after any `hermes update`, because the tool search and plugin hook code moves fast)
