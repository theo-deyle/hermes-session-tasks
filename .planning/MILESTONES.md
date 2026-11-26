# Milestones

## v1.0 Session task board (Shipped: 2026-11-26)

**Phases completed:** 7 phases, 62 plans, 106 tasks

**Key accomplishments:**
- uv project with a pin gate that checks uv.lock against the gateway venv before install, a 3.11 and 3.14 check matrix, and a test harness whose real-home guard fails the pytest run itself
- A session id now reaches a SQLite board through the resolver and store, and comes back as markdown in the agent view (`- [ ] #1 Call John`) and the clipboard view (`- [ ] Call John`), with known sessions routed through an alias table that opens no reader.
- BoardStore.apply now handles add, rename, check and remove with one-level subtasks, 100 item and 500 character caps and a per-item stale rule that makes a parent delete stale over a fresh subtask, proven across four spawned processes on Python 3.11 and 3.14.
- The board now converts to a markdown checklist and back with no loss: render escapes text that starts with `#<digits>`, parse reads checklists and plain bullets with every moved, empty or over-long line counted, and plan_import stops at the free item capacity.
- Board follows its session through compression, a branch gets a one-time copy of its parent board, and the real Hermes SessionDB is pinned to the fake reader by a gateway-venv contract test
- Seven integration tests run every ROADMAP criterion through store, markdown and lineage, and check.sh now enforces 80 percent branch coverage on Python 3.11 (97.09 percent measured)
- A `pre_llm_call` hook that adds a static nudge line and a fenced, escaped, capped board block to each non-delegate turn, proven through the real Hermes plugin manager, plus a tracked own-job runner and analyzer with a unit-tested three-part pass rule.
- Three board routes (`GET /board`, `GET /boards`, `POST /board/edit`) in a path-loaded `plugin_api.py` that reaches the core package under a fixed key, with every edit outcome answered as HTTP 200 in the D-22 shape and transport faults kept as 4xx.
- PowerShell 7 script that copies the Desktop pane file from devpc over scp into the slot Desktop scans, with Desktop's own home rule per OS, host and home guards, a dry run and an atomic replace, plus per-machine README steps.
- `GET /meta` in the path-loaded `plugin_api.py` returns the `plugin.yaml` version and `API_VERSION` 1 from a stdlib `version.py` that never raises, and the layout guards now cover `plugin/dashboard`.
- Every changed write, from the agent tool or from POST /board/edit, now calls Hermes `broadcast_plugin_event("hermes-session-tasks", "board.updated", {session_id, root_id, rev, actor})` after the commit, and a publish fault never fails a write.
- One plain ESM test pane (`plugin/desktop/plugin.js`) that reads a board through `ctx.rest`, shows `board.updated` events, runs a stale-write probe and shows a version banner, proved end to end in a node VM against the real router over a loopback relay.
- The plan 03-01 nudge line, injected by the pre_llm_call hook, lifts the own-job rate from 0 of 3 (Phase 2, rule text alone) to 3 of 3: every run added its 7 steps in one board_edit call before work, checked all 7 off, and made zero todo_list calls.
- The test pane is installed on the Mac with the devpc hash `4e42968a...2c63b7` (success criterion 1, install half), devpc is green on HEAD 8502874 with versions 0.1.0 / API 1 on record, and the announced Desktop restart showed that Desktop reattaches to its detached backend (pid 2231852), which already holds the current plugin Python half.
- The Mac test pane passed 3 of 3: version lines, agent event at rev 1, pane write and stale reply at rev 2.
- The test pane runs on the Windows PC: the install hash matched devpc, a fresh backend started after the announced restart, and the pane shows `backend 0.1.0, api 1` and `pane 0.1.0, api 1` with no mismatch line.
- The Windows PC test pane passed both live steps: the agent write showed as rev 1 and the pane write plus the stale reply showed as rev 2, each matched against data.db.
- The 6 test boards are gone from the real data.db on Theo's recorded yes: 23 boards before, 17 after, zero rows left for every listed root, and the three final gates pass on HEAD.
- The real pane passed every step on the Mac: live update from the agent, check, add, edit, subtask add, delete with confirm, copy as markdown.
- The pre_llm_call hook now sends only Theo's changes since the agent last saw the board, as a fenced note of at most 1000 characters or one pointer line, and a quiet turn gets nothing.
- Four small tools for the live checks of plans 05-05 to 05-07: a scripted Theo edit through the pane write path, a run and session reader with a three-arm token comparison, and a builder of twin test Hermes homes (plugin on and off) with no secret file, every listener off and a safe gateway stop.
- The agent's own board read and its stale or not-found reply now count as seen, and a 30-turn session through Hermes's real hook dispatch and message composer adds exactly the size of Theo's notes and nothing on quiet turns.
- Hermes's `on_session_delete` hook now removes a deleted session's board, items, journal and alias rows in one chunked write transaction, keeps every board on an archive, and was proven against a real SessionDB in a temporary home.
- After an announced restart of the Hermes gateway on devpc, the real model saw exactly Theo's two added items once, nothing on the quiet turn, and `checked #1` alone after the check; the own-plan gate with the prompt section as the only carrier passed 3 of 3.
- The own-plan test passed 3 of 3 without the one-line reminder, so the reminder text and its two tests were removed and the prompt section stays the only carrier.
- The token test with the real model shows the plugin costs 516 input tokens per turn and Theo's notes add 291 more at turn 30 (5 notes, 780 characters), and on Theo's real Hermes an archived chat keeps its board while a deleted chat loses it.
- TitleLookup labels each board root with its Hermes title, else its first user message (first 5 messages, 60 characters), else `Untitled session`, through one read-only SessionDB reader, and never raises.
- Picker row with Hermes titles, a menu of every board, and a read-only view of another session's board, in the one plain pane file.
- The plugin package names "the user" in every model-visible string, the manifest description and the docstrings, and a name guard test keeps it that way.
- The README becomes the catalog page with the one-line host install and the full-URL Desktop identifier, and the devpc setup plus the fallback script steps move to CONTRIBUTING.md, guarded by tests/test_docs.py.
- The copy and edit routes now read the session id limit from the core parser, a layout test fails on a second literal, and the stale read-only row line in the Phase 6 UI spec matches the pane.
- Back returns keyboard focus to the picker trigger through a ref flag set only by Back, both notices speak as live regions, the banner is rounded, the name scan covers the whole package, and every version holder reads 0.2.0.

---
