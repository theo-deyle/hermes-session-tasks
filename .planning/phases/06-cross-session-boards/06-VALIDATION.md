---
phase: "6"
slug: "cross-session-boards"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-02"
---

# Phase 6 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`--import-mode=importlib --strict-markers`, marker `hermes`); pane tests run `node --experimental-vm-modules tests/desktop_pane_harness.mjs` through `tests/pane_rig.py` |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]`, `fail_under = 80`) |
| **Quick run command** | `uv run pytest -q -rs <the test files of the task>` (each task's `<automated>` line names them) |
| **Full suite command** | `./scripts/check.sh` (pin gate, ruff check, ruff format --check, pyright, pytest on 3.11 and 3.14, coverage 80 percent; last line `check: all ok`) |
| **Estimated runtime** | quick run about 10 seconds (two test files measured at 9.5 s on 2026-11-02); full suite a few minutes |

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` lines (its own test files, plus `node --check plugin/desktop/plugin.js` for pane tasks)
- **After every plan wave:** Run `./scripts/check.sh`; the executor that finishes the wave last runs it and records `check: all ok`
- **Before `/gsd-verify-work`:** Full suite green, `uv run pytest -q -rs -m hermes` green with 0 skipped on devpc, `timeout 120 hermes plugins validate plugin/` prints `Validation passed.`
- **Max feedback latency:** about 30 seconds per task (targeted files only)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | TOOL-05, PANE-10 | T-6-01, T-6-03 | One write transaction; the source board is only read | unit | `uv run pytest tests/test_store_copy.py -q -rs -k one_open_item` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 1 | TOOL-05, PANE-10 | T-6-01, T-6-02 | A missing id or an empty plan writes nothing; the cap holds at 100 | unit | `uv run pytest tests/test_copy_plan.py tests/test_store_copy.py tests/test_store_seen.py tests/test_delta.py tests/test_store_items.py tests/test_store_subtasks.py tests/test_markdown.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | TOOL-04, TOOL-05 | T-6-04 | Only `copy_args.read_target` may read `session_id` from the arguments | unit | `uv run pytest tests/test_copy_args.py tests/test_edit_args.py tests/test_layout.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 | 1 | TOOL-04, TOOL-05 | T-6-05, T-6-06 | Bounded ids (1 to 100, no bool), ids of at most 256 characters | unit | `uv run pytest tests/test_copy_args.py tests/test_edit_args.py tests/test_layout.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 1 | TOOL-03 | T-6-07 | Read-only session store door, reader closed | unit | `uv run pytest tests/test_titles.py tests/test_lineage.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-03-02 | 03 | 1 | TOOL-03 | T-6-08, T-6-09 | Sanitised labels; a reader fault never fails a tool | unit | `uv run pytest tests/test_titles.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-03-03 | 03 | 1 | TOOL-03 | T-6-07 | state.db digest unchanged after the title reads | contract (hermes) | `uv run pytest tests/test_hermes_contract.py -q -rs -m hermes` | ✅ (extend) | ⬜ pending |
| 6-04-01 | 04 | 1 | PANE-09 | T-6-10, T-6-12 | Text children only; read-only rows render no write control | pane harness | `uv run pytest tests/test_pane_picker.py -q -rs -k pick_another_board` | ❌ W0 | ⬜ pending |
| 6-04-02 | 04 | 1 | PANE-09 | T-6-11 | `session.list` only on mount, focus change and menu open | pane harness | `uv run pytest tests/test_pane_picker.py tests/test_pane_view.py tests/test_pane_writes.py tests/test_pane_add.py tests/test_pane_edit_delete.py tests/test_pane_harness.py tests/test_desktop_plugin.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-05-01 | 05 | 2 | TOOL-05 | T-6-13 | The copy target is the Hermes keyword session | unit | `uv run pytest tests/test_board_cross.py -q -rs -k copies_one_open_item` | ❌ W0 | ⬜ pending |
| 6-05-02 | 05 | 2 | TOOL-05 | T-6-13, T-6-14, T-6-15 | Delegate refused; argument `session_id` ignored for the target | unit | `uv run pytest tests/test_board_cross.py tests/test_board_tools.py tests/test_results.py tests/test_store_copy.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-06-01 | 06 | 2 | PANE-09 | T-6-18 | Back restores the focused board and its lines | pane harness | `uv run pytest tests/test_pane_readonly.py -q -rs -k back_returns` | ❌ W0 | ⬜ pending |
| 6-06-02 | 06 | 2 | PANE-09 | T-6-18, T-6-19 | Focus change clears the picked board; event reload only for the shown root | pane harness | `uv run pytest tests/test_pane_readonly.py tests/test_pane_picker.py tests/test_desktop_plugin.py tests/test_pane_view.py tests/test_pane_writes.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-06-03 | 06 | 2 | PANE-09 | T-6-17 | No POST from any read-only control | pane harness | `uv run pytest tests/test_pane_readonly.py -q -rs -k sends_no_write` | ❌ W0 | ⬜ pending |
| 6-07-01 | 07 | 2 | TOOL-03, TOOL-04, TOOL-05 | T-6-20, T-6-21 | Seed only in a test home; board read with `mode=ro` | unit (hermes) | `uv run pytest tests/test_live_cross.py -q -rs -m hermes` | ❌ W0 | ⬜ pending |
| 6-07-02 | 07 | 2 | TOOL-03, TOOL-04, TOOL-05 | T-6-20, T-6-22 | Real home refused; stop refuses another home's gateway | unit | `uv run pytest tests/test_live_cross.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-07-03 | 07 | 2 | TOOL-05 | - | N/A | unit | `uv run pytest tests/test_live_cross.py -q -rs -k prompt_files` | ❌ W0 | ⬜ pending |
| 6-08-01 | 08 | 3 | TOOL-04 | T-6-23, T-6-24 | Cross read marks nothing seen; caller from the keyword | unit | `uv run pytest tests/test_board_cross.py -q -rs -k names_another_board` | ❌ W0 | ⬜ pending |
| 6-08-02 | 08 | 3 | TOOL-04 | T-6-23, T-6-24 | Unknown id creates no row; delegate reads, never marks | unit | `uv run pytest tests/test_board_cross.py tests/test_board_tools.py tests/test_lineage.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-08-03 | 08 | 3 | TOOL-03 | T-6-25, T-6-26 | At most 50 lines; no write | unit | `uv run pytest tests/test_board_cross.py tests/test_board_tools.py tests/test_results.py tests/test_store_list.py tests/test_layout.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-09-01 | 09 | 3 | PANE-10 | T-6-27 | Route holds no logic; plain `def` | unit (router) | `uv run pytest tests/test_api_copy.py -q -rs -k copies_one_item` | ❌ W0 | ⬜ pending |
| 6-09-02 | 09 | 3 | PANE-10 | T-6-27, T-6-28, T-6-29, T-6-30 | Extra fields 422; delegate target refused; fixed error texts | unit (router) | `uv run pytest tests/test_api_copy.py tests/test_api.py tests/test_events.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-10-01 | 10 | 4 | TOOL-03, TOOL-05 | T-6-32 | Manifest equals the registered tools | unit | `uv run pytest tests/test_register.py -q -rs` | ✅ (extend) | ⬜ pending |
| 6-10-02 | 10 | 4 | TOOL-03, TOOL-04, TOOL-05 | T-6-31, T-6-33, T-6-34 | Copy-on-request rule; todo_list named once; prompt section unchanged | unit | `uv run pytest tests/test_tool_text.py tests/test_register.py tests/test_layout.py -q -rs` | ✅ (extend) | ⬜ pending |
| 6-10-03 | 10 | 4 | TOOL-03, TOOL-04, TOOL-05 | T-6-32 | Real registry keeps the caller from the keyword | contract (hermes) | `uv run pytest tests/test_hermes_dispatch.py -q -rs -m hermes` | ✅ (extend) | ⬜ pending |
| 6-11-01 | 11 | 4 | PANE-10 | T-6-35 | Copy body built at click time with the four D-46 fields | pane harness | `uv run pytest tests/test_pane_copy.py -q -rs -k row_copy_copies_one_item` | ❌ W0 | ⬜ pending |
| 6-11-02 | 11 | 4 | PANE-10 | T-6-35, T-6-36, T-6-37 | One request per click, no retry, queue order | pane harness | `uv run pytest tests/test_pane_copy.py tests/test_pane_readonly.py tests/test_pane_writes.py tests/test_pane_view.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-11-03 | 11 | 4 | PANE-10 | - | N/A | pane harness | `uv run pytest tests/test_pane_copy.py -q -rs` | ❌ W0 | ⬜ pending |
| 6-12-01 | 12 | 5 | TOOL-03, TOOL-04, TOOL-05 | T-6-39, T-6-41 | Test home only; real gateway untouched | live headless | `test ! -e "$HOME/.cache/hermes-session-tasks/cross-live/home"` plus the run table in 06-12-SUMMARY.md | n/a (measurement) | ⬜ pending |
| 6-12-02 | 12 | 5 | PANE-09, PANE-10 | T-6-38 | Restart only after Theo's recorded go | checkpoint (human action) | n/a | n/a | ⬜ pending |
| 6-12-03 | 12 | 5 | TOOL-03, PANE-09, PANE-10 | T-6-38, T-6-40 | Backend stop matched to its lock; deletes only checked test sessions | live headless + end-of-phase human check | `timeout 120 hermes plugins validate plugin/` plus the own-plan line in 06-12-SUMMARY.md | n/a (measurement) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No framework install: pytest, the node VM harness and the `hermes` marker exist. Each new test file is created by the RED step of the task that first needs it (tracer-first TDD), so no separate stub wave runs.

- [ ] `tests/test_copy_plan.py`, `tests/test_store_copy.py` - TOOL-05 and PANE-10 copy rules (plan 06-01)
- [ ] `tests/test_copy_args.py` and the narrowed TOOL-06 guard in `tests/test_layout.py` - TOOL-04, TOOL-05 arguments (plan 06-02)
- [ ] `tests/test_titles.py`, title and message support in `tests/fakes.py`, parity keys in `tests/hermes_contract_snippet.py` - TOOL-03 (plan 06-03)
- [ ] `tests/desktop_pane_harness.mjs`: `DropdownMenu*` stubs, `host.request` stub, `openMenu` and `pick` steps, `calls` config, outputs `menuItems`, `menuContent`, `requestCalls`, `callResults`; `tests/pane_rig.py` `TZ=UTC`; `tests/test_pane_picker.py` - PANE-09 (plan 06-04)
- [ ] `tests/test_board_cross.py` - TOOL-03, TOOL-04, TOOL-05 handlers (plans 06-05 and 06-08)
- [ ] `tests/test_pane_readonly.py` and `board_gets` matching `/board?` only - PANE-09 (plan 06-06)
- [ ] `tests/live/cross/` and `tests/test_live_cross.py` - live check tools (plan 06-07)
- [ ] `tests/test_api_copy.py` - PANE-10 route (plan 06-09)
- [ ] `tests/test_pane_copy.py` - PANE-10 pane (plan 06-11)
- [ ] Tests that assert the opposite of D-38, changed in the plan that changes the code: `test_read_ignores_a_session_id_in_the_arguments` and the dispatch `spoofed` case (plan 06-08), `test_board_read_schema_declares_no_session_id_property` (plan 06-10), the TOOL-06 layout guard (plan 06-02), `MAX_PLUGIN_LINES` and the header test (plan 06-04)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Go for the restart of the Hermes gateway on devpc and of the Mac's Desktop backend | PANE-09, PANE-10 | The restart drops live Desktop connections; only Theo knows which chats hold work in progress | Plan 06-12 Task 2: one announcement, Theo's reply recorded word for word |
| Picker look in the real 320 px pane, with real titles from `session.list` | PANE-09 | Visual check, and the first call of `session.list` from a plugin pane (RESEARCH Q2); Claude cannot see the Mac window | Plan 06-12 Task 3 human check 1: install the pane on the Mac, reopen Desktop, open a new chat, open the picker |
| Read-only view of another chat's board | PANE-09 | Visual check of the banner, the greyed boxes and the hover controls | Plan 06-12 Task 3 human check 2: pick another chat that has items |
| One row copy through the Mac's restarted backend, with its notice | PANE-10 | The real route on the Mac backend and the one-line notice in the real pane | Plan 06-12 Task 3 human check 3: Copy on one row, then Back; Claude then asks one question before it deletes the test chat |

Claude runs every other check: the test-home runs with the real model (list, read, copy, unasked copy count), the own-plan re-check, the restart, the backend stop and the cleanup.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 6s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** {pending / approved YYYY-MM-DD}
