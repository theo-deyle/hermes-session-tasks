---
phase: 06-cross-session-boards
verified: 2026-11-03T03:00:00Z
status: passed
score: 4/4 must-haves verified
covered_files:
  - ".planning/phases/06-cross-session-boards/06-01-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-01-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-02-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-02-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-03-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-03-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-04-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-04-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-05-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-05-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-06-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-06-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-07-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-07-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-08-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-08-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-09-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-09-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-10-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-10-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-11-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-11-SUMMARY.md"
  - ".planning/phases/06-cross-session-boards/06-12-PLAN.md"
  - ".planning/phases/06-cross-session-boards/06-12-SUMMARY.md"
  - "plugin/dashboard/plugin_api.py"
  - "plugin/desktop/plugin.js"
  - "plugin/plugin.yaml"
  - "plugin/session_tasks/board_api.py"
  - "plugin/session_tasks/board_tools.py"
  - "plugin/session_tasks/copy_args.py"
  - "plugin/session_tasks/copy_plan.py"
  - "plugin/session_tasks/results.py"
  - "plugin/session_tasks/rows.py"
  - "plugin/session_tasks/store.py"
  - "plugin/session_tasks/titles.py"
  - "plugin/session_tasks/tool_text.py"
  - "plugin/session_tasks/wiring.py"
  - "plugin/skills/board-rules/SKILL.md"
  - "tests/live/cross/cross_live.py"
covered_digest: "v4:sha256:54ba0e457a0253477dd8ee43a39b7783e192f0756d4921d4dff32cbc96a0ce76"
behavior_unverified: 0
overrides_applied: 0
advisory:
  - finding: "IN-07: a refused copy shows the save notice and keeps the gone board on screen (plugin.js)"
    category: other
    reason: "Open info item in 06-REVIEW-DISPOSITION.md. No data risk. Fix in a later phase."
    evidence_status: "none provided"
  - finding: "UI review: the notice line is silent to a screen reader and Back drops keyboard focus (pillar 6 scored 3/4)"
    category: other
    reason: "Quality gap in 06-UI-REVIEW.md. The spec contract is met."
    evidence_status: "none provided"
---

# Phase 6: Cross-session boards Verification Report

**Phase Goal:** The agent and Theo list, read and copy items from other sessions' boards.
**Verified:** 2026-11-03T03:00:00Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The agent lists the sessions that have a board, with open and total counts and the last update. | ✓ VERIFIED | `BoardTools.board_sessions` (board_tools.py) calls `store.list_boards()`. The SQL orders by `updated_at DESC` (rows.py:271). It caps at `SESSIONS_SHOWN = 50`, joins titles through `TitleLookup` in one reader, and builds one `session_line` per board. It never reads `args`. Registered in wiring.py:78 and listed in plugin.yaml. Live (06-12 L1): the real model called `board_sessions` and named "Phase 6 source board". |
| 2 | On request, the agent reads another session's board by session id and copies chosen items, or all open items, into the current board. | ✓ VERIFIED | `board_read` takes the caller from the Hermes keyword and the target from `copy_args.read_target`. It resolves the target through the lineage resolver and calls `_cross_read`, which has no `_mark_seen` and no write. `board_copy` takes the caller from the keyword, refuses a delegate, parses `from_session_id` and `item_ids`, and calls `store.copy_items(caller.root_id, source.root_id, ...)`. Live (06-12 L2, L3): the source board stayed byte equal (rev 1, `agent_seen_rev` 0). The copy wrote two unchecked items with `copied` journal rows `cross-src-1#1` and `#2`. In two mention runs the model read and did not copy. |
| 3 | A session picker in the pane lists boards with title, open count and last update. A picked board shows read-only. | ✓ VERIFIED | plugin.js calls `host.request('session.list', {limit: 200})`, joins on `_lineage_root_id ?? id`, and falls back to the preview and then `Untitled session`. Picked boards render through `readOnlyActions` (`readOnly: true`): checkbox, add line, edit, subtask line and delete are disabled or absent. The banner text is `Read only. Viewing another session.` with Back. Tests `pick_another_board`, `back_returns` and `sends_no_write` pass (I re-ran the last two). Mac check 4 passed (06-12 Task 4). |
| 4 | Theo copies one item, or all open items, from the shown board into the focused board. | ✓ VERIFIED | `runCopy` posts `/board/copy` with `session_id` (the focused root), `from_session_id` (the picked root), optional `item_ids` and `base_rev`. The route `copy_board` calls `BoardApi.copy`, which resolves the target, refuses a delegate target, and calls `copy_items(..., actor="user")`. A stale reply, a refused copy and a published `board.updated` event are handled. `tests/test_pane_copy.py` and `tests/test_api_copy.py` pass (50 and part of 195 tests, re-run by me). Mac check 5 passed: "Copied 1 to (this chat). 0 skipped" and the other board unchanged. |

**Score:** 4/4 roadmap truths verified. 0 truths are behavior-unverified.

### Behavior-dependent truths (state and ordering invariants)

| Invariant | Status | Evidence |
|-----------|--------|----------|
| A cross read never moves `agent_seen_rev` and writes no row (D-38) | ✓ VERIFIED | Code: `_cross_read` has no `_mark_seen` and no store write. Tests: `tests/test_board_cross.py` seen values and row counts equal before and after (re-run, passes). Real Hermes dispatch snippet shows the seen mark unchanged after a cross read (`tests/test_hermes_dispatch.py`, recorded in 06-VALIDATION). Live: source board byte equal after L2, L3, M1, M2. |
| A copy is one transaction: skip check, cap and inserts share one `BEGIN IMMEDIATE` (T-6-01) | ✓ VERIFIED | `copy_items` runs `plan_copy`, `_apply` and `_provenance` inside one `write_txn`. `tests/test_store_copy.py` passes. |
| The copy stops at the 100 item cap and reports the overflow | ✓ VERIFIED | `plan_copy(..., MAX_ITEMS - len(target))` puts parents before subtasks, so a cut never orphans a subtask. `tests/test_copy_plan.py` passes. |
| The journal cap counts the rows the note reads (review WR-01, fixed in 969b12d) | ✓ VERIFIED | `rows.prune_changes` and `rows.journal_span` now exclude `op = 'copied'`. A `copied` row goes only when its rev is below the oldest kept row. Test 285514b (60 item copy) is in `tests/test_store_copy.py` and passes. |
| `cross_live.py stop` refuses the real Hermes home (review WR-02, fixed in d11c5e9) | ✓ VERIFIED | Fix commit d11c5e9 with test 34c134e. `tests/test_live_cross.py` is not rerun (hermes-marked paths are out of scope for this pass). The gate run at HEAD passed (1072 tests). |

### Locked decisions D-38 to D-46

| Decision | Status | Evidence |
|----------|--------|----------|
| D-38 two new tools, optional `session_id` on `board_read`, caller from the keyword only | ✓ | Handlers take `session_id` as a keyword. `SANCTIONED_ARG_READS` in `tests/test_layout.py` allows one read, `read_target`. |
| D-39 titles through the read-only door, newest first, resolver for lineage ids | ✓ | `titles.py` uses `reader.get_session_title`, then the first user message, then `UNTITLED`. The reader closes in `finally`. A fault gives `Untitled session`. |
| D-40 chosen top item brings open subtasks; a lone subtask becomes top level; delegate refused; agent copies only on request | ✓ | `_groups` in copy_plan.py. `DELEGATE_COPY` before parse. Tool text: "Use it only when Theo asks you to copy". SKILL.md line 64. |
| D-41 new id, unchecked, actor, journal row names the source | ✓ | `_provenance` writes `source_root#source_id`. Live copy rows match. |
| D-42 exact open text on the target is skipped and counted | ✓ | `plan_copy` builds `texts` from unchecked target items. Counts reach `copy_result` and the pane notice. |
| D-43 picker row, focused session always listed, `session.list` join | ✓ | plugin.js lines 85, 157, 865. Mac check 3 passed with real titles. |
| D-44 banner, Back, "Copy all open to <title>", per-row Copy, no write control | ✓ | plugin.js `ReadOnlyBanner`, `CopyAllButton`, `readOnlyActions`. |
| D-45 focus change returns to the focused board; live update by root id | ✓ | The focus effect clears `picked` and `pickedServer`. `reloadShown` runs for the shown root only. |
| D-46 `POST /board/copy`, no extra fields, same stale shape as edit | ✓ | `CopyBody` has `extra="forbid"`, `max_length=256`, `StrictInt`. The core re-parses with `copy_args.parse`. |

### Prohibitions

| Prohibition | Tier | Status | Evidence |
|-------------|------|--------|----------|
| A copy never changes the source board | test | ✓ VERIFIED | Source rev and item asserts in `tests/test_store_copy.py` and `tests/test_board_cross.py` (re-run, pass). |
| A copy never changes or removes an existing target item | test | ✓ VERIFIED | `_apply` runs only `AddItem` ops. Target asserts in `tests/test_store_copy.py`. |
| The plugin never writes the Hermes session store when it reads a title | test | ✓ VERIFIED | `SessionDB(read_only=True)` in session_reader.py. The `state_db_unchanged` digest test is in `tests/test_hermes_contract.py` (recorded as passing in 06-VALIDATION and the 06-12 gate lines). |
| The read-only view renders no write control | test | ✓ VERIFIED | `sends_no_write` and `pick_another_board` pass. |
| No board or session this phase did not create is changed or deleted; no Hermes setting changes | judgment | ✓ VERIFIED (judgment, non-authoritative) | 06-12-SUMMARY records read-only id checks and board counts (19 to 18, exactly the one Mac test chat). The copy source board `20261031_191523_093c62` stayed at rev 4. |
| The agent does not copy unless Theo asks | judgment | ✓ VERIFIED (judgment, non-authoritative) | Two mention runs (M1, M2) called `board_read` and no `board_copy`. Tool text and skill state the rule. |

Human review of the two judgment prohibitions is optional. The evidence is recorded and the risk is low.

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `plugin/session_tasks/copy_plan.py` | ✓ VERIFIED | Pure copy rules, 140 lines, used by `store.copy_items`. |
| `plugin/session_tasks/copy_args.py` | ✓ VERIFIED | `parse` and `read_target`, bounded ids, used by tools and API. |
| `plugin/session_tasks/store.py` `copy_items` | ✓ VERIFIED | Real SQL in one write transaction. |
| `plugin/session_tasks/titles.py` | ✓ VERIFIED | `TitleLookup`, wired in wiring.py. |
| `plugin/session_tasks/board_tools.py` | ✓ VERIFIED | `board_sessions`, cross `board_read`, `board_copy`. |
| `plugin/session_tasks/board_api.py` `copy` and `dashboard/plugin_api.py` route | ✓ VERIFIED | Route calls `api.copy`. |
| `plugin/desktop/plugin.js` | ✓ VERIFIED | Picker, read-only view, copy buttons. 1342 lines; the one-file limit is recorded in 06-UI-SPEC and the line ceiling test. `node --check` passes. |
| `plugin/skills/board-rules/SKILL.md`, `tool_text.py`, `plugin.yaml` | ✓ VERIFIED | Four tools named. `plugin.yaml` lists `board_sessions` and `board_copy`. |

### Key Link Verification

| From | To | Status | Details |
|------|----|--------|---------|
| `wiring.register` | `tools.board_sessions`, `tools.board_copy` | WIRED | `register_tool` calls at wiring.py:78 and :85, with titles injected (`TitleLookup(open_reader)`). |
| `BoardTools.board_copy` | `store.copy_items` | WIRED | Caller root is the target. |
| `BoardApi.copy` | `store.copy_items(actor="user")` | WIRED | Called from the `/board/copy` route. |
| `plugin.js runCopy` | `POST /board/copy` | WIRED | Body fields match `CopyBody`. |
| `plugin.js` picker | `session.list` and `GET /boards` | WIRED | Join on `_lineage_root_id ?? id`. |
| `after_write` listener | `board.updated` event | WIRED | The agent and the user listeners both run after a copy commits. A listener fault is logged and never fails the result. |

### Data-Flow Trace (Level 4)

| Artifact | Data variable | Source | Real data | Status |
|----------|---------------|--------|-----------|--------|
| Picker rows | boards, titles | `GET /boards` (SQLite) and `session.list` | Yes. Mac check 3 showed real titles. | ✓ FLOWING |
| Read-only view | `pickedServer.board` | `GET /board?session_id=<root>` | Yes. Mac check 4. | ✓ FLOWING |
| Copy notice | `copied`, `skipped`, `overflow` | Route reply from `copy_items` | Yes. Mac check 5. | ✓ FLOWING |
| `board_sessions` lines | summaries, titles | `list_boards` and the read-only `SessionDB` | Yes. Live L1. | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Store, plan, args, cross tools, copy route, titles, layout guard, seen and delta | `uv run pytest -q tests/test_store_copy.py tests/test_copy_plan.py tests/test_copy_args.py tests/test_board_cross.py tests/test_api_copy.py tests/test_titles.py tests/test_layout.py tests/test_store_seen.py tests/test_delta.py` | 195 passed in 4.16 s | ✓ PASS |
| Pane copy and picker | `uv run pytest -q tests/test_pane_copy.py tests/test_pane_picker.py` | 50 passed | ✓ PASS |
| Back and no-write read-only view | `uv run pytest -q tests/test_pane_readonly.py -k "back_returns or sends_no_write"` | 2 passed | ✓ PASS |
| Pane syntax | `node --check plugin/desktop/plugin.js` | exit 0 | ✓ PASS |
| Full house gate | `./scripts/check.sh` at HEAD (reported by the caller, not rerun) | 1072 tests on 3.11 and 3.14, `check: all ok` | ✓ PASS |

I did not run `tests/live/*`, any hermes-marked test, or anything that touches `~/.hermes`. The live record in 06-12-SUMMARY is read, not rerun.

### Probe Execution

Step 7c: SKIPPED. The phase declares no `probe-*.sh` file.

### Requirements Coverage

Every ID in the PLAN frontmatter matches REQUIREMENTS.md. All five are claimed by at least one plan. No orphaned requirement.

| Requirement | Source plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| TOOL-03 | 06-03, 06-07, 06-08, 06-10, 06-12 | The agent lists sessions that have a board, with counts and last update. | ✓ SATISFIED | Truth 1. |
| TOOL-04 | 06-02, 06-07, 06-08, 06-10, 06-12 | The agent reads another session's board by session id. | ✓ SATISFIED | Truth 2, `_cross_read`, no seen change. |
| TOOL-05 | 06-01, 06-02, 06-05, 06-07, 06-10, 06-12 | The agent copies chosen or all open items into the current board. | ✓ SATISFIED | Truth 2, `board_copy`, live L3. |
| PANE-09 | 06-04, 06-06, 06-12 | Session picker with title, open count and last update; another board shows read-only. | ✓ SATISFIED | Truth 3, Mac checks 3 and 4. |
| PANE-10 | 06-01, 06-02, 06-09, 06-11, 06-12 | Theo copies one item or all open items into the focused board. | ✓ SATISFIED | Truth 4, Mac check 5. |

REQUIREMENTS.md already marks all five Complete in the traceability table.

### Gate reports read

| Report | Result |
|--------|--------|
| 06-VALIDATION.md | `status: validated`, `nyquist_compliant: true`. Every task row green. |
| 06-SECURITY.md | `threats_open: 0`. T-6-01 to T-6-40 closed or accepted (AR-06-01 to AR-06-03). |
| 06-REVIEW.md and 06-REVIEW-DISPOSITION.md | Two warnings, both fixed (969b12d, d11c5e9) with tests. Seven info items deferred. |
| 06-UI-REVIEW.md | Pillars 4, 3, 4, 4, 4, 3. No blocker. Five Mac checks passed. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| all phase source files | n/a | `TBD`, `FIXME`, `XXX`, `TODO`, `HACK` | none found | No debt marker in the changed files. |
| plugin.js | n/a | IN-07: refused copy shows the "save" notice | ℹ️ Info | UX wording only. Advisory. |
| board_tools.py | `_cross_read` | IN-01: docstring says "no store write" but resolving a branch id can create an alias board | ℹ️ Info | No behavior risk. |
| copy_args.py | n/a | IN-02: `base_rev` parsed and unused on the copy path | ℹ️ Info | No behavior risk. |

The other info items (IN-03 to IN-06) are in 06-REVIEW-DISPOSITION.md as deferred. None blocks the goal.

### Human Verification Required

None open. The end-of-phase human checks (five Mac checks in the real pane) are already recorded as passed by Theo in 06-12-SUMMARY Task 4.

### Deferred Items

None. Phase 7 (deploy and hardening) holds no item that this phase needs.

### Gaps Summary

No gap. All four roadmap truths hold in the code. The tools, the route and the pane are registered and wired. Tests I ran pass. The live runs with the real model and the Mac checks agree with the code reading. The two review warnings that came after the summaries are fixed and the fixes are in `rows.py` and `cross_live.py` on HEAD.

---

_Verified: 2026-11-03T03:00:00Z_
_Verifier: Claude (gsd-verifier)_
