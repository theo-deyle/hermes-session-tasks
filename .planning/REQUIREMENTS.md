# Requirements: hermes-session-tasks

**Defined:** 2026-10-30
**Core Value:** Items the agent lists for Theo stay visible and editable in the pane for the whole session, so Theo never scrolls up or asks the agent to repeat itself.

## v1 Requirements

Requirements for the first release. Each maps to a roadmap phase.

### Storage and board model

- [x] **STOR-01**: Each session has its own board, stored in a plugin-owned SQLite file under `$HERMES_HOME/plugin-data/hermes-session-tasks/`, never in `state.db`.
- [x] **STOR-02**: An item has an id, text, checked state, parent id, position, created and updated timestamps, and who made the last change (agent or user).
- [x] **STOR-03**: An item can have subtasks (depth is set in discuss-phase; the model keeps `parent_id` so the depth can change later).
- [x] **STOR-04**: Every board has a revision number. A write that targets an item changed since the caller's base revision is rejected and returns the current board.
- [x] **STOR-05**: Writes are safe when the agent tool and the pane write at the same time from different gateway processes (SQLite transaction, no in-process lock).
- [x] **STOR-06**: A board follows its session through context compression and branches, so Theo does not lose the list mid-session.
- [ ] **STOR-07**: When Hermes deletes a session, the plugin removes that session's board; an archived session keeps its board.
- [x] **STOR-08**: The board round-trips to and from a markdown checklist (`- [ ]`, `- [x]`, indented subtasks) with a stdlib-only renderer and parser.

### Agent tools

- [ ] **TOOL-01**: The agent can read the current session's board as markdown with item ids and the revision.
- [ ] **TOOL-02**: The agent can add, rename, check, uncheck and remove items in one call with a list of item-level operations. No replace-all write.
- [ ] **TOOL-03**: The agent can list the sessions that have a board, with open and total counts and last update.
- [ ] **TOOL-04**: The agent can read another session's board by session id.
- [ ] **TOOL-05**: The agent can copy chosen items, or all open items, from another session's board into the current board.
- [x] **TOOL-06**: The tools take the current session from the `session_id` Hermes passes to the handler, never from the model's arguments.
- [x] **TOOL-07**: Every write returns the new revision, a one-line change summary, and the board content the agent needs; a rejected stale write always returns the current board (full versus compact result is set in discuss-phase).
- [x] **TOOL-08**: Tool names share one prefix, avoid the word "todo", and never read, write, wrap or replace `todo_list`.

### Agent behaviour

- [ ] **AGNT-01**: A bundled skill tells the agent to add an item when it lists something Theo must do, decide or remember, and to keep its own plan in `todo_list`.
- [ ] **AGNT-02**: The tool descriptions carry the trigger and the `todo_list` boundary, so the agent uses the board without loading the skill.
- [ ] **AGNT-03**: The agent asks Theo one plain question before it deletes an item, rewords an item Theo wrote, unchecks an item, changes many items at once, or is unsure which item Theo means.
- [x] **AGNT-04**: When the agent's work finishes an item, the agent checks it and says so in one line.
- [ ] **AGNT-05**: The agent sees Theo's own edits on its next turn through a `pre_llm_call` hook that injects only the changes since the agent last saw the board, and injects nothing when nothing changed.

### Backend routes

- [ ] **API-01**: REST routes under `/api/plugins/hermes-session-tasks/` let the pane read a board, list boards, and apply the same item-level operations as the agent tools.
- [ ] **API-02**: Every write, from a tool or a route, broadcasts a `board.updated` event with the session id and revision.
- [ ] **API-03**: A meta route returns the backend version and API version, so the pane can detect a mismatch with its own copy.

### Pane

- [ ] **PANE-01**: A right-side pane (`placement: 'right'`) shows the board of the focused session and follows the focus change.
- [ ] **PANE-02**: The pane renders items as checkboxes with subtasks indented and collapsible.
- [ ] **PANE-03**: Theo can check and uncheck items; the pane updates at once and reconciles on the returned revision.
- [ ] **PANE-04**: Theo can add an item inline and keep typing the next one.
- [ ] **PANE-05**: Theo can edit an item's text inline.
- [ ] **PANE-06**: Theo can add a subtask to an item.
- [ ] **PANE-07**: Theo can delete an item; the pane confirms when subtasks go with it.
- [ ] **PANE-08**: The pane updates live when the agent writes, through the broadcast event, and polls as a fallback.
- [ ] **PANE-09**: A session picker lists sessions that have a board with title, open count and last update, and shows another session's board read-only.
- [ ] **PANE-10**: Theo can copy one item or all open items from another session's board into the focused board.
- [ ] **PANE-11**: Theo can copy the board to the clipboard as a plain markdown checklist.
- [ ] **PANE-12**: The pane shows an empty state that says the agent adds items here.
- [ ] **PANE-13**: The pane is one plain ESM file that imports only `@hermes/plugin-sdk`, `react` and `react/jsx-runtime`, uses SDK components and `var(--ui-*)` theme vars, and has no hardcoded colours.

### Dev and deploy

- [x] **DEV-01**: The repo is a uv project with ruff, pyright and pytest, and the tests pass on Python 3.11 and 3.14.
- [x] **DEV-02**: Tool handlers, hooks, store and routes have tests that run without a gateway, including a two-process concurrent write test.
- [ ] **DEV-03**: The pane file passes `node --check` and an import allowlist test.
- [ ] **DEV-04**: The package dir is symlinked into `~/.hermes/plugins/`, enabled with the Hermes CLI, and the gateway restart is announced before it happens.
- [ ] **DEV-05**: The Desktop half (`desktop/plugin.js`) is installed on the Mac and the Windows PC by a copy script, the pane shows a banner when its version does not match the backend, and the README gives the steps for each machine.
- [ ] **DEV-06**: The repo is pushed to GitHub `Don-Mor-Software-Group/hermes-session-tasks` (private) with a plain-language README.

## v2 Requirements

Deferred. Tracked but not in the current roadmap.

### Board

- **BORD-01**: Theo can reorder items in the pane, and the agent can reorder items.
- **BORD-02**: Theo can import a markdown checklist into the board from the pane.
- **BORD-03**: Theo can edit another session's board in place.
- **BORD-04**: A global or project board shared by all sessions.

### Pane

- **PANE-14**: Items show a marker when the agent made the last change.
- **PANE-15**: A status bar chip shows the open count when the pane is hidden.
- **PANE-16**: Delete shows an undo toast instead of a confirm dialog.
- **PANE-17**: The picker can open the other session's conversation.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Reading, writing, wrapping or replacing `todo_list` | `todo_list` is the agent's own working plan; Theo decided the board stays separate |
| Due dates, reminders, priorities, assignees, labels | A remember list, not a scheduler; the date goes in the item text |
| In-progress or cancelled item states | Those belong to the agent's plan; a checkbox has two states |
| Replace-all write in the agent tools | One bad call wipes Theo's edits |
| Auto-check a parent from its subtasks, or the reverse | Surprise state changes for both writers; show a count instead |
| Sync to Super Productivity or GitHub | Not needed in v1; copy as markdown covers export |
| Changes to the Hermes Agent source tree | Everything ships as a plugin |
| Rich markdown or HTML in item text | Items are one line of plain text; render as text, never as HTML |
| Injecting the whole board every turn | Breaks prompt caching and wastes tokens; inject only Theo's changes |
| A settings page | No setting is needed yet |

## Traceability

Each v1 requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STOR-01 | Phase 1 | Complete |
| STOR-02 | Phase 1 | Complete |
| STOR-03 | Phase 1 | Complete |
| STOR-04 | Phase 1 | Complete |
| STOR-05 | Phase 1 | Complete |
| STOR-06 | Phase 1 | Complete |
| STOR-07 | Phase 5 | Pending |
| STOR-08 | Phase 1 | Complete |
| TOOL-01 | Phase 2 | Pending |
| TOOL-02 | Phase 2 | Pending |
| TOOL-03 | Phase 6 | Pending |
| TOOL-04 | Phase 6 | Pending |
| TOOL-05 | Phase 6 | Pending |
| TOOL-06 | Phase 2 | Complete |
| TOOL-07 | Phase 2 | Complete |
| TOOL-08 | Phase 2 | Complete |
| AGNT-01 | Phase 2 | Pending |
| AGNT-02 | Phase 2 | Pending |
| AGNT-03 | Phase 2 | Pending |
| AGNT-04 | Phase 2 | Complete |
| AGNT-05 | Phase 5 | Pending |
| API-01 | Phase 3 | Pending |
| API-02 | Phase 3 | Pending |
| API-03 | Phase 3 | Pending |
| PANE-01 | Phase 4 | Pending |
| PANE-02 | Phase 4 | Pending |
| PANE-03 | Phase 4 | Pending |
| PANE-04 | Phase 4 | Pending |
| PANE-05 | Phase 4 | Pending |
| PANE-06 | Phase 4 | Pending |
| PANE-07 | Phase 4 | Pending |
| PANE-08 | Phase 4 | Pending |
| PANE-09 | Phase 6 | Pending |
| PANE-10 | Phase 6 | Pending |
| PANE-11 | Phase 4 | Pending |
| PANE-12 | Phase 4 | Pending |
| PANE-13 | Phase 4 | Pending |
| DEV-01 | Phase 1 | Complete |
| DEV-02 | Phase 1 | Complete |
| DEV-03 | Phase 3 | Pending |
| DEV-04 | Phase 7 | Pending |
| DEV-05 | Phase 3 | Pending |
| DEV-06 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 43 total
- Mapped to phases: 43
- Unmapped: 0

---
*Requirements defined: 2026-10-30*
*Last updated: 2026-10-30 after roadmap creation*
