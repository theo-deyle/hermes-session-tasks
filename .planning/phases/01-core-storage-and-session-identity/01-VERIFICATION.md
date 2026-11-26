---
phase: 01-core-storage-and-session-identity
verified: 2026-10-30T20:30:00Z
status: passed
score: 6/6 must-haves verified
covered_files:
  - ".planning/phases/01-core-storage-and-session-identity/01-01-PLAN.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-01-SUMMARY.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-02-PLAN.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-02-SUMMARY.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-03-PLAN.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-03-SUMMARY.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-04-PLAN.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-04-SUMMARY.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-05-PLAN.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-05-SUMMARY.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-06-PLAN.md"
  - ".planning/phases/01-core-storage-and-session-identity/01-06-SUMMARY.md"
  - ".python-version"
  - "plugin/session_tasks/__init__.py"
  - "plugin/session_tasks/aliases.py"
  - "plugin/session_tasks/db.py"
  - "plugin/session_tasks/fork.py"
  - "plugin/session_tasks/lineage.py"
  - "plugin/session_tasks/markdown.py"
  - "plugin/session_tasks/model.py"
  - "plugin/session_tasks/paths.py"
  - "plugin/session_tasks/revision.py"
  - "plugin/session_tasks/rows.py"
  - "plugin/session_tasks/schema.py"
  - "plugin/session_tasks/session_reader.py"
  - "plugin/session_tasks/store.py"
  - "pyproject.toml"
  - "scripts/check.sh"
  - "scripts/check_pins.py"
  - "tests/conftest.py"
  - "tests/fakes.py"
  - "tests/fork_race_worker.py"
  - "tests/hermes_contract_snippet.py"
  - "tests/home_guard.py"
  - "tests/race_worker.py"
  - "tests/test_adapters.py"
  - "tests/test_fork.py"
  - "tests/test_hermes_contract.py"
  - "tests/test_layout.py"
  - "tests/test_lineage.py"
  - "tests/test_markdown.py"
  - "tests/test_markdown_roundtrip.py"
  - "tests/test_phase_flow.py"
  - "tests/test_race.py"
  - "tests/test_store_items.py"
  - "tests/test_store_revision.py"
  - "tests/test_store_subtasks.py"
  - "tests/test_tracer.py"
  - "uv.lock"
covered_digest: "v4:sha256:7c226f5a48f18bb4ab9b7d588f3bbf926498124cef53505b6bf1fd0573004b52"
behavior_unverified: 0
overrides_applied: 0
flagged_prohibitions: 16
---

# Phase 1: Core, storage and session identity - Verification Report

**Phase Goal:** Each session has its own durable board. Concurrent writes stay safe. The board follows its session through compression and branches.
**Verified:** 2026-10-30T20:30:00Z
**Status:** passed (16 judgment-tier prohibitions flagged, see below)
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ROADMAP 1: Items sit in a plugin-owned SQLite file, `state.db` stays untouched, each item holds id, text, checked, parent, position, timestamps and last writer, a subtask hangs under its parent | VERIFIED | `schema.py` SCHEMA_V1 defines `items` with all fields and `updated_by CHECK IN ('agent','user')`, plus a composite parent foreign key. `paths.connect()` opens the file only through `plugins.plugin_storage.plugin_db`. `session_reader.py` builds `SessionDB(read_only=True)`. Tests `test_open_session_reader_builds_session_db_read_only`, `test_session_db_is_always_built_read_only` and the `state.db` hash check in the hermes contract test pass. `test_every_item_field_is_set_and_a_subtask_hangs_under_its_parent` passes. |
| 2 | ROADMAP 2: Two separate processes write one board with no lost write. A write to an item changed since its base revision is rejected and returns the current board | VERIFIED | `db.write_txn` uses `BEGIN IMMEDIATE`. `store.apply` returns `Stale(board, ...)` on `_StaleSignal` after rollback. `revision.is_stale` compares item rev and board rev to `base_rev`, and checks subtasks on a parent delete. `tests/test_race.py` spawns real processes: four-process fill to the cap, four-process own-item edits, two-process race on one item (one applied, one stale), two-process add at 99 items (one add, one BoardFull). All pass in both Python legs. |
| 3 | ROADMAP 3: A board written before a compression shows the same items after it. A branch shows its parent's items | VERIFIED | `lineage.py` resolves through the alias table, `record_compaction`, and a lazy `get_compression_lineage` walk. `fork.py` copies the parent board once, inside one write transaction. `test_board_survives_rotating_compression_through_the_hook_and_without_it` and `test_branch_shows_parent_items_and_edits_stay_apart` pass. The two-process branch copy test (`test_two_processes_resolving_one_branch_copy_it_once`) passes. |
| 4 | ROADMAP 4: A board converts to a markdown checklist and back with no loss, including subtasks | VERIFIED | `tests/test_markdown_roundtrip.py` runs 500 seeded random boards with ids on and with ids off. `test_pasted_checklist_round_trips_through_the_store_with_subtasks` passes through `plan_import` and `BoardStore.apply`. `markdown.py` has 100 percent line and branch coverage. |
| 5 | ROADMAP 5: `uv sync` builds the project. ruff, pyright and pytest pass on Python 3.11 and 3.14 with no gateway. Store tests include the two-process write test | VERIFIED | I ran `./scripts/check.sh`. It ended with `check: all ok`. Python 3.11 leg: ruff clean, 36 files formatted, pyright 0 errors, 210 passed, coverage 97.09 percent (gate 80). Python 3.14 leg: same checks, 210 passed. `uv run pytest -m hermes -q -rs`: 3 passed, 207 deselected, 0 skipped. |
| 6 | Review fixes CR-01, WR-01, WR-02, WR-03 hold | VERIFIED | See "Review fix check" below. I ran the new lineage and fork tests against the pre-fix `lineage.py` (commit `5414833^`): 4 failed, 47 passed. All 4 failures are the new CR-01 and WR-01 tests. Against current code all pass. |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Review fix check

| Finding | Fix commit | Evidence in current code | Status |
|---------|-----------|--------------------------|--------|
| CR-01 (blocker) compressed branch never copies its parent | 5414833 | `lineage._compression` calls `_resolve(chain_root)` when the chain root is an explicit fork child. Tests `test_branch_compressed_before_its_first_touch_still_gets_the_parent_copy` and `test_compaction_hook_for_a_branch_not_yet_touched_copies_the_parent_board` fail on old code, pass on new. | HOLDS |
| WR-01 compressed delegate writes to a wrong board | 03546aa | `_root_of_old` returns `_resolve(old_id).root_id`. `record_compaction` catches `_LineageLoop`. Tests `test_compressed_delegate_tip_resolves_to_the_delegator_root` and `test_compaction_hook_for_a_delegate_aliases_the_new_id_to_the_delegator_root` fail on old code, pass on new. | HOLDS |
| WR-02 blank session key accepted by `BoardStore` | 0550837 | `model.check_session_id` rejects a non-string or blank id. `BoardStore.get_board` and `apply` call it first. The resolver uses the same function. | HOLDS |
| WR-03 real-home guard blind to a rewrite | efeec9a | `home_guard.snapshot` maps each path to `(size, mtime_ns)`. `new_entries` reports a changed stamp. The real `~/.hermes/plugin-data/hermes-session-tasks` does not exist after my runs. | HOLDS |

### Deferred Items

None. STOR-07 (Phase 5) is a different requirement and is not a Phase 1 gap.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `plugin/session_tasks/` (13 modules, 1313 lines) | Core: model, schema, db, paths, rows, aliases, revision, store, markdown, lineage, fork, session_reader | VERIFIED | All exist, are substantive, and are tracked in git. No module passes 500 lines. |
| `pyproject.toml`, `uv.lock`, `.python-version` | uv project, dev pins, coverage gate `fail_under = 80` | VERIFIED | `check.sh` ran the pin gate and the coverage gate. |
| `scripts/check.sh`, `scripts/check_pins.py` | Matrix runner and pin gate | VERIFIED | Both ran inside my `check.sh` run. |
| `tests/` (19 files) | Harness, guards, race, flow tests | VERIFIED | 210 tests pass on both Pythons. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/check.sh` | `scripts/check_pins.py` | pin gate first in every run | WIRED | Output shows `Resolved 26 packages` and the pin step ran before tests. |
| `tests/conftest.py` | `tests/home_guard.py` | `pytest_plugins = ["home_guard"]` | WIRED | Guard hooks run in the session; no real-home change reported. |
| `tests/test_phase_flow.py` | `markdown.plan_import`, `lineage.record_compaction` | parse, plan, apply, render; compaction then resolve | WIRED | Tests pass. |
| `store.apply` | `lineage` root id | caller passes the resolved root id | WIRED | `test_phase_flow` composes resolver and store. |
| `paths.connect` | Hermes `plugin_db` | lazy import | WIRED | `test_hermes_contract.py` (marker `hermes`) ran: 3 passed. |

### Data-Flow Trace (Level 4)

Not applicable. The phase renders no UI. The store reads and writes real SQLite rows, proven by the process race tests and the on-disk round trip tests.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full gate on Python 3.11 and 3.14 | `./scripts/check.sh` | `check: all ok`, 210 passed twice, coverage 97.09 percent | PASS |
| Hermes contract tests | `uv run pytest -m hermes -q -rs` | 3 passed, 0 skipped | PASS |
| Review-fix tests fail on pre-fix code | `pytest tests/test_fork.py tests/test_lineage.py` against `5414833^` `lineage.py` in a scratchpad copy | 4 failed, 47 passed | PASS |
| Real Hermes home untouched | `ls ~/.hermes/plugin-data/hermes-session-tasks` | does not exist | PASS |
| Git tree clean after the run | `git status --short` | no output | PASS |

### Probe Execution

No probes declared or found (`scripts/*/tests/probe-*.sh` does not exist). Step skipped.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| STOR-01 | 01-02, 01-03, 01-05, 01-06 | Per-session board in plugin SQLite file, not `state.db` | SATISFIED | `paths.py`, read-only `SessionDB`, tests above |
| STOR-02 | 01-02, 01-03 | Item fields incl. last writer | SATISFIED | `schema.py` items table, `test_every_item_field_is_set...` |
| STOR-03 | 01-03 | Subtasks via `parent_id` | SATISFIED | Composite FK, `DepthExceeded` at depth 2, `tests/test_store_subtasks.py` |
| STOR-04 | 01-03, 01-06 | Revision number, stale write returns current board | SATISFIED | `revision.py`, `store.apply`, `tests/test_store_revision.py` |
| STOR-05 | 01-03 | Cross-process safe writes | SATISFIED | `BEGIN IMMEDIATE`, `tests/test_race.py` |
| STOR-06 | 01-02, 01-05, 01-06 | Board follows compression and branches | SATISFIED | `lineage.py`, `fork.py`, tests and review fixes |
| STOR-08 | 01-02, 01-04, 01-06 | Markdown round trip, stdlib only | SATISFIED | `markdown.py`, 500-board round trip |
| DEV-01 | 01-01, 01-06 | uv, ruff, pyright, pytest on 3.11 and 3.14 | SATISFIED | `check.sh` run |
| DEV-02 | 01-01, 01-02, 01-03, 01-06 | Tests without a gateway, two-process write test | SATISFIED | no-network fixture, `tests/test_race.py` |

All 9 phase requirement IDs appear in plan frontmatter and in REQUIREMENTS.md (marked complete, mapped to Phase 1). No orphaned requirement: REQUIREMENTS.md maps exactly these 9 IDs to Phase 1.

### Prohibitions (judgment tier, non-authoritative)

The plans declare 16 prohibitions. All are `verification: judgment` with `status: unresolved`. None is test-tier. Flag: `unverified-prohibition - human review recommended` applies to each, because a judge verdict is non-authoritative. The evidence below is deterministic where a named test exists. I confirmed that all 22 named tests exist and pass.

| # | Prohibition (short) | Judge verdict | Evidence |
|---|---------------------|---------------|----------|
| 1 | Delete never removes a subtask changed after base_rev | not violated | two named stale-delete tests pass; `revision.is_stale` child check |
| 2 | No partial batch, no truncation of text | not violated | `test_rejected_batch_leaves_rev_items_and_journal_unchanged`, `test_500_code_points_pass_and_501_raise_text_too_long` pass |
| 3 | No replace-all or clear-board op | not violated | `Op = AddItem or SetText or SetChecked or RemoveItem` in `model.py`; no clear method on `BoardStore` (code read, no test) |
| 4 | No parent and subtask auto-check | not violated | `test_checking_a_parent_leaves_its_subtasks_unchanged` passes |
| 5 | A read never creates a board row | not violated | `test_unknown_root_reads_empty_board_and_creates_no_rows` passes |
| 6 | Never touch `todo_list` | not violated | `grep todo_list plugin` finds nothing; Hermes import allowlist test passes |
| 7 | No dependency manifest in `plugin/` | not violated | `git ls-files plugin` lists only `.py` files; layout test passes |
| 8 | No private Hermes import | not violated | the two import guard tests pass |
| 9 | No `async def` in core | not violated | `test_core_defines_no_async_def` passes |
| 10 | No test touches the real `~/.hermes` | not violated | guard tests pass; real plugin-data dir absent after my runs |
| 11 | No cached connection, path or SessionDB | not violated | grep: one `sqlite3.connect` (in `paths.py`, per call); no module-level state; `open_db` closes in `finally` (code read, no test) |
| 12 | Never write `state.db` | not violated | read-only `SessionDB`, three named tests pass |
| 13 | A delegate gets no board or copy | not violated | `test_delegate_resolves_to_the_delegator_root_and_writes_nothing` passes |
| 14 | Branch and parent never share edits | not violated | `test_branch_edits_do_not_reach_the_parent_and_the_reverse` passes |
| 15 | Session id only from the caller, never blank | not violated | `check_session_id` used by resolver and store; two named blank-id tests pass |
| 16 | An import never drops a line silently | not violated | three named parser tests pass and the zero-capacity test passes |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| plugin, tests, scripts | - | `TBD`, `FIXME`, `XXX`, `TODO`, `HACK` | none found | No debt markers |
| plugin, tests, scripts, pyproject.toml | - | em dash or en dash | none found | House rule met |
| `tests/home_guard.py` | 79 | Message reads `real Hermes home changed:` while plan 01-01 truth text says `gained:` | Info | Deliberate wording change from the WR-03 fix. The behavior is stronger. No action. |
| `.planning/phases/.../01-REVIEW-DISPOSITION.md` | - | IN-02 to IN-06 left open | Info | Cosmetic or Phase 2 and 3 scope. Not blockers. |

### Human Verification Required

None. Every item has deterministic evidence. The 16 flagged prohibitions are recorded above for the audit trail. Phase 1 has no live Desktop surface, so no visual or device check applies.

Note for the research item in ROADMAP (`post_compaction` on a live Desktop, equality of tool `session_id` and `focusedStoredSessionId` after `/compress`): the code and tests use the Hermes public contract and a fake pinned to the real `SessionDB`. The live-Desktop equality is not provable in Phase 1 and belongs to the Phase 2 live test.

### Gaps Summary

No gaps. All five ROADMAP success criteria hold in the code, the full gate passes on both Python versions, the two-process race tests pass, and the four review fixes hold (the CR-01 and WR-01 tests fail on the old code). ROADMAP.md still shows Phase 1 as "In Progress" with an unchecked box, although 6/6 plans are done. The orchestrator can mark it complete.

---

_Verified: 2026-10-30T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
