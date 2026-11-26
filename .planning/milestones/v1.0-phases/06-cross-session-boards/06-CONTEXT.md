# Phase 6: Cross-session boards - Context

**Gathered:** 2026-11-02
**Status:** Ready for planning

<domain>
## Phase Boundary

The agent lists the sessions that have a board, reads another session's board by session id, and copies chosen items or all open items into the current board. The pane gets a session picker, a read-only view of a picked board, and copy buttons for one item or all open items. Requirements TOOL-03, TOOL-04, TOOL-05, PANE-09, PANE-10.

Not in this phase: edits to another session's board, a global board, markdown import, reorder, the formal rollout (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Agent tools
- **D-38:** Two new tools, `board_sessions` and `board_copy` (names fixed by D-11). `board_read` takes an optional `session_id` argument that names another session's board. The calling session still comes only from the `session_id` keyword Hermes passes (TOOL-06). A cross read never marks the board as seen and never changes `agent_seen_rev`. - **Reversibility:** costly - the skill, the tool descriptions and the live test name the tools and the argument.
- **D-39:** `board_sessions` returns one line per board: title, session id, open count over total, last board update, sorted newest board update first. The title comes from the Hermes session store through the same read-only door Phase 1 uses for lineage (`session_reader.open_session_reader`, public `get_session_title`), then the first user message, then "Untitled session". A session id passed to `board_read` or `board_copy` resolves through the Phase 1 resolver, so any id in a compressed lineage reaches its root board. - **Reversibility:** reversible - one read on an existing door.
- **D-40:** `board_copy(from_session_id, item_ids?)` copies the named items, or all open items when `item_ids` is absent, into the calling session's board. A chosen top-level item brings its open subtasks. A chosen subtask copied alone becomes a top-level item. A copy is an add: the D-18 guard does not apply, and no new hook guards it. The tool descriptions and the skill say the agent copies only when Theo asks for it. A delegate session cannot copy (same rule as `board_edit`, D-20).

### Copy semantics (precedent D-06 branch copy)
- **D-41:** A copied item gets a new per-board id, starts unchecked, and belongs to the actor who copied it (`agent` for the tool, `user` for the pane). The journal row names the source root id and the source item id. No link back to the source item is kept on the item. The target board keeps its caps (D-10): a copy that would pass 100 items stops at the cap and reports the overflow count.
- **D-42:** An item whose exact text is already open on the target board is skipped. The result names the counts: "Copied N to <title>. M skipped, already on the board." Compared text is the sanitised text, case-sensitive, after trim. Checked items on the target do not block a copy.

### Pane picker and other-board view (sketch approved 2026-11-02)
- **D-43:** A picker row replaces the "N of M open" header line at the top of the pane. It shows the current board's title and its open count, and opens a list of every session that has a board, newest board change first. The focused session is always listed, even with an empty board. Each row shows title, open count over total, and the last update. The pane gets titles from `host.request('session.list', {limit: 200})`, joined on `_lineage_root_id ?? id`; title, then `preview`, then "Untitled session" with the short id. A board whose session is missing from `session.list` stays listed with the fallback label.
- **D-44:** A picked board other than the focused one shows read-only: a banner "Read only. Viewing another session." with a Back link, a header button "Copy all open to <focused title>", and a "Copy" button on each top-level row on hover. No checkbox, add line, edit, subtask add or delete works there. Copy acts on the focused session's board; the result shows as the one-line notice from D-34 with the D-42 counts. The copy as markdown button stays and copies the shown board.
- **D-45:** When the focused session changes, the pane returns to the focused board. Live update applies to the shown board: the `board.updated` event carries `root_id`, so the pane refetches when it matches the shown board, and the poll fallback covers the rest.

### REST
- **D-46:** `GET /boards` adds nothing; titles come from the Desktop side (D-43). A new `POST /board/copy` takes `session_id` (target), `from_session_id`, optional `item_ids`, and `base_rev`, with the same no-extra-fields rule and the same stale reply shape as `/board/edit` (D-22, D-24). `GET /board?session_id=` already serves the read-only view.

### Claude's Discretion
Tool result wording, the `board_copy` result shape (summary line plus the added lines in D-13 form), the skill text, which SDK component builds the picker (`Select` or `DropdownMenu`), the exact banner and button labels within the sketch, the test list, and the hot-mount versus restart check on devpc.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Sketch (approved)
- `.planning/sketches/06-session-picker.html` - the three pane states: picker row, picker open, other board read-only with copy buttons.

### Prior decisions
- `.planning/phases/01-core-storage-and-session-identity/01-CONTEXT.md` - D-03 ids, D-04 agent view line, D-06 branch copy (the copy precedent), D-07 lineage, D-10 caps.
- `.planning/phases/02-agent-tools-and-skill/02-CONTEXT.md` - D-11 tool names, D-13 to D-16 result shapes, D-18 guard, D-20 delegate rule.
- `.planning/phases/03-rest-router-and-client-install-spike/03-CONTEXT.md` - D-22 stale reply, D-24 route rules, `GET /boards`.
- `.planning/phases/04-pane/04-CONTEXT.md` and `04-UI-SPEC.md` - pane layout, D-33 header, D-34 optimistic write and notice line.
- `.planning/phases/05-agent-sees-theo-s-edits/05-CONTEXT.md` - D-35 seen tracking that a cross read must not touch.

### Research
- `.planning/research/FEATURES.md` "Cross-session" - `session.list` row shape, title fallback chain, picker shape.
- `~/.hermes/hermes-agent/tui_gateway/methods_session.py` `_session_row_summary` - the `session.list` row: `id`, `title`, `preview`, `started_at`, `_lineage_root_id`.
- `~/.hermes/hermes-agent/hermes_state_titles.py` `get_session_title` - the public title read.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `plugin/session_tasks/store.py` `BoardStore.list_boards` and `rows.BoardSummary` (root_id, rev, open, total, updated_at): the list for both tool and route.
- `plugin/session_tasks/fork.py`: the branch copy that gives new ids and a journal row; the copy op follows it.
- `plugin/session_tasks/session_reader.py`: the read-only `SessionDB` door for titles.
- `plugin/session_tasks/board_tools.py` and `board_api.py`: resolve, delegate check, result helpers to extend.
- `plugin/desktop/plugin.js`: `Header`, `headerText`, `openCounts`, the notice line, `sendOp` with `base_rev`.

### Established Patterns
- Tools take the calling session from the keyword only; routes take `session_id` from the request and refuse extra fields.
- Every write goes through `BoardStore.apply` under `BEGIN IMMEDIATE` with the rev rule; a copy is one batch of adds plus a journal row.
- Static tool text in `tool_text.py` keeps the prompt cache stable.

### Integration Points
- `wiring.py` registers the two new tools and the route.
- `events.publish` already carries `root_id`; the pane matches it against the shown board.

</code_context>

<specifics>
## Specific Ideas

Theo approved the sketch in the plan canvas without annotations. The picker row replaces the header line; it does not add a row above it.

</specifics>

<deferred>
## Deferred Ideas

- Edit another session's board from the pane - out of scope (research anti-feature M7).
- Global board across sessions - backlog (PROJECT.md).
- Agent-side session title for the agent without the state store, should the public door move - revisit in Phase 7 if `hermes update` changes the import list.

</deferred>

---

*Phase: 06-cross-session-boards*
*Context gathered: 2026-11-02*
