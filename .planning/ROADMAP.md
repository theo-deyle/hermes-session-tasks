# Roadmap: hermes-session-tasks

## Overview

The plugin gives each Hermes session a task board that Theo sees in a Desktop pane. The build starts with the board store and the session key. The agent tools come next. Then come the REST routes, with a proof that the pane installs on the Mac and the Windows PC. The pane follows. After the pane, the agent learns to see Theo's edits. Cross-session reading and copying come next. The last phase rolls the plugin out and finishes the README.

The phases start from the eight in `.planning/research/SUMMARY.md`. Research phases 1 and 2 merge into Phase 1, because research phase 2 held one requirement (STOR-06). Research phases 3 to 8 are roadmap Phases 2 to 7, in the same order.

**Rules for every phase:**
- Each phase adds tests for its own code to the harness from Phase 1. The tests run without a gateway (DEV-02).
- Each phase keeps ruff, pyright and pytest green on Python 3.11 and 3.14 (DEV-01).
- Open design choices (subtask depth, write result contract, tool names, item cap, item id form) are listed in `research/SUMMARY.md`. Each phase settles its own in its discuss step.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core, storage and session identity** - A safe SQLite board per session that follows its session through compression and branches. (completed 2026-10-30)
- [x] **Phase 2: Agent tools and skill** - The agent reads and edits the board, and puts its own multi-step plan on the board. (completed 2026-10-31)
- [x] **Phase 3: REST router and client install spike** - The backend routes work, and a stub pane runs on the Mac and the Windows PC. (completed 2026-11-02)
- [x] **Phase 4: Pane** - Theo sees and edits the focused session's board in a right-side pane that updates live. (completed 2026-11-01)
- [x] **Phase 5: Agent sees Theo's edits** - The agent learns of Theo's changes on its next turn, and a deleted session loses its board. (completed 2026-11-02)
- [x] **Phase 6: Cross-session boards** - The agent and Theo list, read and copy items from other sessions' boards. (completed 2026-11-02)
- [ ] **Phase 7: Deploy and hardening** - The plugin installs on any Hermes host and any Desktop machine from a public, catalog-ready GitHub repo.

## Phase Details

### Phase 1: Core, storage and session identity
**Goal**: Each session has its own durable board. Concurrent writes stay safe. The board follows its session through compression and branches.
**Depends on**: Nothing (first phase)
**Requirements**: STOR-01, STOR-02, STOR-03, STOR-04, STOR-05, STOR-06, STOR-08, DEV-01, DEV-02
**Success Criteria** (what must be TRUE):
  1. A session's items sit in a plugin-owned SQLite file under `$HERMES_HOME/plugin-data/hermes-session-tasks/`, and `state.db` stays untouched. Each item holds an id, text, checked state, parent, position, timestamps and the last writer (agent or user). A subtask hangs under its parent.
  2. Two separate processes write the same board at the same time, and no write is lost. The store rejects a write to an item changed since its base revision, and returns the current board.
  3. A board written before a context compression shows the same items after it. A branch of a session shows its parent's items.
  4. A board converts to a markdown checklist and back with no loss, including subtasks.
  5. `uv sync` builds the project. ruff, pyright and pytest pass on Python 3.11 and 3.14 with no gateway running. The store tests include the two-process write test.
**Plans**: 6/6 plans complete in 5 waves
Plans:
**Wave 1**
- [x] 01-01-PLAN.md - uv toolchain, pin gate, 3.11 and 3.14 matrix, test harness, layout and real-home guards (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md - First end to end test (session id to SQLite board to markdown), then the alias table and shared store fixtures (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-03-PLAN.md - Store: all item ops, subtasks, caps, revision rule, journal, two- and four-process race tests (wave 3)
- [x] 01-04-PLAN.md - Markdown: escape rule, parser, import planning at the cap, seeded round trip (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 01-05-PLAN.md - Lineage: compression alias, branch fork copy, delegate and reset, Hermes adapters and contract tests (wave 4, after 01-03)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 01-06-PLAN.md - Phase gate: integration test per ROADMAP criterion, 80 percent coverage gate (wave 5)
**Research**: Needed for the lineage part only. Topics: `post_compaction` on a live Desktop, whether the tool `session_id` and `focusedStoredSessionId` stay equal after `/compress`, how a branch looks in `state.db`. The store and markdown code need none.

### Phase 2: Agent tools and skill
**Goal**: The agent writes the things Theo must do, decide or remember to the board. The agent also puts its own multi-step plan on the board and checks each step off as it finishes it.
**Depends on**: Phase 1
**Requirements**: TOOL-01, TOOL-02, TOOL-06, TOOL-07, TOOL-08, AGNT-01, AGNT-02, AGNT-03, AGNT-04
**Success Criteria** (what must be TRUE):
  1. In a fresh Desktop session on devpc, the agent reads the board as markdown with item ids and the revision. The agent adds, renames, checks, unchecks and removes items in one call with a list of item-level operations.
  2. No replace-all write exists. Every write returns the new revision and a one-line summary. A stale write returns the current board.
  3. The tools take the session from the id Hermes passes to the handler, so a session id in the model's arguments changes nothing. The tool names share one prefix and avoid the word "todo". `todo_list` stays untouched.
  4. A live test sends 5 prompts that list things for Theo. In all 5, the agent adds the items to the board. When the agent gets a job of 3 or more steps, it writes its steps to the board first and checks them off as it finishes; the own-job headless run measures this. The tool descriptions carry this rule, so the agent needs no skill load.
  5. The agent asks Theo one plain question before a delete, an uncheck, a reword of Theo's text or a bulk change. It asks the same question when it is unsure which item Theo means. When its work finishes an item, the agent checks the item and says so in one line.
**Plans**: 7/7 plans complete in 6 waves
Plans:
**Wave 1**
- [x] 02-01-PLAN.md - First end to end test: Hermes loads the plugin and board_read returns the board with ids; board_read contract and the session and todo_list guards (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-02-PLAN.md - board_edit argument parser, the ask-before-destroy guard, pre_tool_call and post_compaction callbacks (wave 2)
- [x] 02-03-PLAN.md - Tool text: board_edit schema and descriptions, system prompt section, bundled skill (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 02-04-PLAN.md - board_edit handler and results, full registration, real Hermes dispatch, validate and doctor gates (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 02-05-PLAN.md - Announcement to Theo, then plugin enable and gateway restart on devpc, then the headless live test with the real model (5 of 5 rule, todo_list boundary, each ask case) (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 02-06-PLAN.md - Desktop pass part 1, one request per turn: list message and /compress, each checked read only from the data (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 02-07-PLAN.md - Desktop pass part 2, one request per turn: read and edit after /compress, the question before the remove, the confirmed remove, each checked read only from the data (wave 6)
**Research**: Needed. Topics: tool deferral and the toolset default for the Desktop platform, the `pre_tool_call` approve directive, the final tool names.

### Phase 3: REST router and client install spike
**Goal**: The pane's backend routes work. A stub pane installs and runs on the Mac and on the Windows PC. This proves the install path before the real pane exists.
**Depends on**: Phase 2
**Requirements**: API-01, API-02, API-03, DEV-03, DEV-05, AGNT-01 (own-plan half, routed from Phase 2)
**Success Criteria** (what must be TRUE):
  0. A `pre_llm_call` hook injects the live board and one nudge line ("your steps go on the board") into every turn, pulled forward from Phase 5. The own-job headless run passes in at least 3 of 3: the agent writes its steps to the board and checks them off. Routed from Phase 2 on 2026-10-31 (D-21): rule text alone gave 0 of 3.
  1. A stub pane copied by script shows in Desktop on the Mac and on the Windows PC. The README gives the install steps for each machine.
  2. The stub reads a board through `ctx.rest` from the routes under `/api/plugins/hermes-session-tasks/`. A write through a route returns the new revision. A stale write returns the current board.
  3. A write from an agent tool and a write from a route both broadcast `board.updated` with the session id and revision. The stub on each machine shows whether the event arrived.
  4. The `/meta` route returns the backend version and the API version. The stub shows a banner when its own version differs from the backend.
  5. The stub file passes `node --check` and an import allowlist test that permits only `@hermes/plugin-sdk`, `react` and `react/jsx-runtime`.
**Plans**: 12/12 plans complete in 8 waves
Plans:
**Wave 1**
- [x] 03-01-PLAN.md - Own-plan nudge: pre_llm_call hook end to end through Hermes, board block escape and cap, own-job harness tracked with its pass rule (wave 1)
- [x] 03-02-PLAN.md - Board routes: host-style load of plugin_api.py, GET /board, POST /board/edit with structured 200 replies, GET /boards (wave 1)
- [x] 03-03-PLAN.md - Copy script install-desktop.ps1 (home rule per OS, guards, dry run) and the README steps for the Mac and the Windows PC (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 03-04-PLAN.md - GET /meta with the backend and API versions, layout guards over the dashboard (wave 2)
- [x] 03-05-PLAN.md - board.updated from tool and route writes, publish after commit, never fails a write (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 03-06-PLAN.md - Test pane plugin.js through the real routes in a node VM: board, events, poll, write test, banner, syntax and import checks, version drift (wave 3)
- [x] 03-07-PLAN.md - Own-job headless runs with the real model, 3 of 3, up to three wording rounds (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 03-08-PLAN.md - Mac part 1: devpc gates and gateway decision, install command, announced Desktop restart (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 03-09-PLAN.md - Mac part 2: test pane lines, agent write event, write test and stale reply, each checked against data.db (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 03-10-PLAN.md - Windows PC part 1: install command, announced Desktop restart, test pane lines (wave 6)

**Wave 7** *(blocked on Wave 6 completion)*
- [x] 03-11-PLAN.md - Windows PC part 2: agent write event, write test, then README facts from both machines (wave 7)

**Wave 8** *(blocked on Wave 7 completion)*
- [x] 03-12-PLAN.md - One plain question, then delete the test boards on Theo's recorded yes, final gates (wave 8)
**Research**: Needed. Topics: stale-write transport (HTTP 409 or a structured 200) in a live Desktop, event delivery over SSH to the Mac and the Windows PC, how `plugin.js` reaches each machine from a private repo.
**UI hint**: yes

### Phase 4: Pane
**Goal**: Theo sees and edits the focused session's board in a right-side pane. The pane updates live when the agent writes.
**Depends on**: Phase 3
**Requirements**: PANE-01, PANE-02, PANE-03, PANE-04, PANE-05, PANE-06, PANE-07, PANE-08, PANE-11, PANE-12, PANE-13
**Success Criteria** (what must be TRUE):
  1. A right-side pane shows the board of the focused session and switches when the focus changes. An empty board shows a message that the agent adds items here.
  2. Items show as checkboxes with indented, collapsible subtasks. Theo checks and unchecks an item and sees the change at once. The pane then reconciles on the returned revision.
  3. Theo adds an item inline and keeps typing the next one. Theo edits an item's text inline and adds a subtask. Theo deletes an item, and the pane confirms when subtasks go with it.
  4. When the agent writes to the board, the pane updates with no reload, through the event. Polling covers the case where no event arrives.
  5. Theo copies the board to the clipboard as a plain markdown checklist. The pane is one plain ESM file with three allowed imports, SDK components, `var(--ui-*)` theme vars and no hardcoded colour.
**Plans**: 9/9 plans complete in 7 waves
Plans:
**Wave 1**
- [x] 04-01-PLAN.md - First end to end test: a check in the real pane reaches the store; checkbox rows, header count, Phase 3 contracts kept, hooks guard (wave 1)
- [x] 04-09-PLAN.md - Install script takes an optional -RemotePath, so the Phase 3 Windows steps install the frozen Phase 3 pane (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 04-02-PLAN.md - Test pane harness: every SDK stub, step kind, reply sequence and write-time capture, proven with a probe plugin (wave 2)
- [x] 04-03-PLAN.md - Guards: every class ships in Desktop, no palette or named colour, plain class literals, 800 line ceiling (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 04-04-PLAN.md - Write path: optimistic display, one write at a time, stale retry for a check, failure and notice line (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 04-05-PLAN.md - View: subtask groups, collapse, done style, header copy as markdown, empty states, focus switch (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 04-06-PLAN.md - Add line and subtask add line with the plus button (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 04-07-PLAN.md - Inline text edit, delete with the confirm dialog, reload and focus rules for typing (wave 6)

**Wave 7** *(blocked on Wave 6 completion)*
- [x] 04-08-PLAN.md - Mac live check, one request per turn, each step checked in data.db, then the cleanup question (wave 7)
**Research**: Not needed. The SDK exports are verified, and `hermes-memory-ui` is a working reference.
**UI hint**: yes

### Phase 5: Agent sees Theo's edits
**Goal**: The agent knows what Theo changed on its next turn, at a small token cost. A board lives and dies with its session.
**Depends on**: Phase 4
**Requirements**: AGNT-05, STOR-07
**Success Criteria** (what must be TRUE):
  1. After Theo edits the board in the pane, the agent's next turn carries a short note that lists only those changes.
  2. A turn with no change since the agent last saw the board gets no injected text.
  3. The injected note stays near 600 to 1200 characters at most. A token count at turn 30 is compared with a session that has no plugin. The difference equals the size of the notes.
  4. When Hermes deletes a session, the plugin removes that session's board. A session that Hermes archives keeps its board.
**Plans**: 7/7 plans complete in 6 waves
Plans:
**Wave 1**
- [x] 05-01-PLAN.md - First end to end test (Theo's pane edit to the agent's next turn), note rules, seen rules, old turn-text contracts (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 05-02-PLAN.md - Live test tools: scripted Theo edit, session rows, the two 30-run token arms (wave 2)
- [x] 05-03-PLAN.md - Agent tool results mark the board seen; 30-turn character contract through Hermes (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 05-04-PLAN.md - Board cleanup when Hermes deletes a session, archive keeps it; real SessionDB contract (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 05-05-PLAN.md - Announced gateway restart, live note check with the real model, own-plan test without the reminder (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 05-06-PLAN.md - Act on the own-plan result: remove the reminder, or ask Theo and bring it back in the form he picks (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 05-07-PLAN.md - Token test over 30 turns, live archive and delete, cleanup of every test chat (wave 6)
**Research**: Needed. Topics: the `platform` value Desktop reports, delegate and subagent turn behaviour, hot mount versus restart for new code.

### Phase 6: Cross-session boards
**Goal**: The agent and Theo list, read and copy items from other sessions' boards.
**Depends on**: Phase 4
**Requirements**: TOOL-03, TOOL-04, TOOL-05, PANE-09, PANE-10
**Success Criteria** (what must be TRUE):
  1. The agent lists the sessions that have a board, with open and total counts and the last update.
  2. On request, the agent reads another session's board by session id. The agent copies chosen items, or all open items, into the current board.
  3. A session picker in the pane lists boards with title, open count and last update. A picked board shows read-only.
  4. Theo copies one item, or all open items, from the shown board into the focused board.
**Plans**: 12/12 plans complete in 5 waves
Plans:
**Wave 1**
- [x] 06-01-PLAN.md - Copy in the board store: one transaction, the copy rules, the journal of where each copy came from (wave 1)
- [x] 06-02-PLAN.md - Arguments of board_copy and of the board_read target; the caller check keeps one sanctioned read (wave 1)
- [x] 06-03-PLAN.md - Session titles for the agent through the read-only session store, pinned to the real store (wave 1)
- [x] 06-04-PLAN.md - Chat picker in the pane with titles, and the first read-only view of another board (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 06-05-PLAN.md - board_copy handler: copy into the caller's board, guards and the copy sentence (wave 2)
- [x] 06-06-PLAN.md - Read-only view: Back, focus change, live update by board, empty and failure states, no writes (wave 2)
- [x] 06-07-PLAN.md - Tools for the live check: seed a source board in a test home, read boards, list tool calls (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 06-08-PLAN.md - board_sessions and board_read of another session's board, with no seen change (wave 3)
- [x] 06-09-PLAN.md - Copy route for the pane, with the edit route's reply shapes (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 06-10-PLAN.md - Register the two new tools, the tool text, the skill section, the real Hermes dispatch test (wave 4)
- [x] 06-11-PLAN.md - Copy one item or all open items from the pane, with the one-line copy notice (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 06-12-PLAN.md - Live check with the real model in a test home, announced restart, own-plan re-check, Mac checks (wave 5)
**Research**: Not needed. The REST and pane patterns repeat, and the title join uses the documented `session.list`.
**UI hint**: yes

### Phase 7: Deploy and hardening
**Goal**: The plugin installs on any Hermes host with one `hermes plugins install` line and its pane installs on any Hermes Desktop machine from the Plugins page. The public GitHub repo holds everything the Hermes plugin catalog asks of a submission. Changed 2026-11-03 by Theo; see 07-CONTEXT.md.
**Depends on**: Phase 5, Phase 6
**Requirements**: DEV-04, DEV-06
**Success Criteria** (what must be TRUE):
  1. `hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable` installs and enables the plugin on a Hermes host other than devpc, never by a hand edit of `config.yaml`. The gateway restart is announced before it happens. devpc keeps the symlink as the dev mode.
  2. After a restart on devpc, every running `hermes serve` process runs the new code and reports the same version from `/meta`. The Desktop backends are stopped only after a lock file and command line match, after Theo's go.
  3. A live pass on the Mac and on a Windows PC installs the pane from the Plugins page (Install from Git, Desktop target) and runs the whole loop in four steps. The agent lists items. The pane shows them live. Theo edits one. The agent sees the edit on its next turn.
  4. The public GitHub repo `theo-deyle/hermes-session-tasks` holds the full history, a plain-language README with no personal or host names, a CONTRIBUTING file with the devpc dev setup, a ready catalog entry file, and a CI run of the test suite. `hermes plugins validate plugin --install-deps` passes. The README states that closing the only pane disables the plugin.
  5. The three Phase 6 pane review warnings, the stale UI-SPEC line and review note IN-05 are fixed. The user-facing strings name no person and no host.
**Plans**: 7/9 plans executed in 6 waves
Plans:
**Wave 1**
- [x] 07-01-PLAN.md - Board text with no personal or host name: the delta note, the tool text, the skill, the guard text, the manifest description, and the name scan of the package (wave 1)
- [x] 07-02-PLAN.md - README as the catalog page, plugin/README.md, CONTRIBUTING.md with the devpc dev setup and the fallback script (wave 1)
- [x] 07-03-PLAN.md - Catalog entry file, CI workflow that runs check.sh, the counts-only history scan (wave 1)
- [x] 07-04-PLAN.md - One home for SESSION_ID_MAX (IN-05) and the stale UI-SPEC line (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 07-05-PLAN.md - Pane fixes (focus after Back, notice role status, rounded banner), the whole-package name scan, version 0.2.0 (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 07-06-PLAN.md - Pre-push checks, Theo's decision on what goes public and the license, the public push and the first CI run (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 07-07-PLAN.md - Install, enable, doctor and update from the public repo in a fresh Hermes home, then Theo's choice of a second host and the same install there; catalog readiness outputs (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 07-08-PLAN.md - Ask rule check in a test home, announced restart on devpc, owner-checked backend stop, new-code proof, own-plan check (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [ ] 07-09-PLAN.md - Install from the Plugins page and the four-step loop on the Mac and on the Windows PC, then Theo's go before the final public push (wave 6)
**Research**: Needed. Topics: the catalog entry schema (`plugin-catalog/README.md`), how the Desktop app installs a plugin from Git against a remote backend, the GitHub history scan before the public push, and the restart procedure for every `serve` process.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core, storage and session identity | 6/6 | Complete    | 2026-10-30 |
| 2. Agent tools and skill | 7/7 | Complete    | 2026-10-31 |
| 3. REST router and client install spike | 12/12 | Complete    | 2026-11-02 |
| 4. Pane | 9/9 | Complete    | 2026-11-01 |
| 5. Agent sees Theo's edits | 7/7 | Complete    | 2026-11-02 |
| 6. Cross-session boards | 12/12 | Complete    | 2026-11-02 |
| 7. Deploy and hardening | 7/9 | In Progress | - |
