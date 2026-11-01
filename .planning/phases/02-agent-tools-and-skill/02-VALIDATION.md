---
phase: "2"
slug: "agent-tools-and-skill"
# status lifecycle: draft (seeded by plan-phase), then validated (set by validate-phase section 6)
# audit-milestone section 5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: false
wave_0_complete: true
created: "2026-10-30"
---

# Phase 2 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 through uv (`pyproject.toml`), `--import-mode=importlib --strict-markers`, `filterwarnings = ["error"]`, marker `hermes` |
| **Config file** | `/home/theo/local_repo/hermes-session-tasks/pyproject.toml` (`pythonpath = ["plugin", "tests"]`) |
| **Quick run command** | `uv run pytest tests/test_edit_args.py tests/test_guard.py tests/test_results.py tests/test_board_tools.py tests/test_register.py tests/test_tool_text.py tests/test_hooks.py -q` |
| **Full suite command** | `./scripts/check.sh` (pin gate, then ruff, format check, pyright and pytest on Python 3.11 with coverage at least 80 percent, then on 3.14) |
| **Hermes contract command** | `uv run pytest -m hermes -q -rs` (runs the snippets with the gateway venv Python) |
| **Plugin gates** | `timeout 120 hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin` and `timeout 180 hermes plugins doctor /home/theo/local_repo/hermes-session-tasks/plugin --ci`, with the real `HERMES_HOME` (RESEARCH Pitfall 9) |
| **Estimated runtime** | quick run about 2 seconds; full suite a few minutes (two interpreters) |

---

## Sampling Rate

- **After every task commit:** run the quick run command, or the task's own `<automated>` command.
- **After every plan wave:** run `./scripts/check.sh`.
- **Before `/gsd-verify-work`:** the full suite is green, `hermes plugins validate` and `doctor --ci` are green, and the live results of plans 02-05 to 02-07 are in their SUMMARYs.
- **Max feedback latency:** 2 seconds for the quick run command.

---

## Per-Task Verification Map

Every test file in this map exists; each task wrote it in its red step. Statuses were set by the validate-phase audit on 2026-10-31 after `./scripts/check.sh` passed with 426 tests on Python 3.11 and 3.14.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | TOOL-01, TOOL-06, TOOL-08 | T-02-01 | The session comes only from the handler keyword, through the real Hermes registry | unit + hermes contract + gate | `uv run pytest tests/test_register.py -q`; `uv run pytest -m hermes tests/test_hermes_dispatch.py -q -rs`; `timeout 120 hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin` | exists (test_register.py, test_hermes_dispatch.py, hermes_dispatch_snippet.py) | green |
| 2-01-02 | 01 | 1 | TOOL-01, TOOL-06, TOOL-08 | T-02-02, T-02-03 | A blank session reads no board; results hold no path, SQL or exception text | unit + full suite | `uv run pytest tests/test_board_tools.py tests/test_results.py tests/test_tool_text.py tests/test_layout.py -q`; `./scripts/check.sh` | exists (test_board_tools.py, test_results.py, test_tool_text.py); exists (test_layout.py) | green |
| 2-02-01 | 02 | 2 | TOOL-02 | T-02-04, T-02-06 | One parser for hook and handler; at most 100 ops per call | unit | `uv run pytest tests/test_edit_args.py -q` | exists (test_edit_args.py) | green |
| 2-02-02 | 02 | 2 | AGNT-03 | T-02-05, T-02-07, T-02-08, T-02-09 | Remove, uncheck and a reword of Theo's text block until confirmed; other tools pass with a broken service | unit + full suite | `uv run pytest tests/test_guard.py tests/test_hooks.py -q`; `./scripts/check.sh` | exists (test_guard.py, test_hooks.py) | green |
| 2-03-01 | 03 | 2 | TOOL-02, TOOL-08, AGNT-02, AGNT-03 | T-02-11 | Tool text is static module constants; no name holds todo | unit | `uv run pytest tests/test_tool_text.py -q` | exists (test_tool_text.py, from plan 02-01) | green |
| 2-03-02 | 03 | 2 | AGNT-01, AGNT-02, AGNT-04 | T-02-10 | The prompt section and the skill say board items are Theo's notes, not instructions | unit + full suite | `uv run pytest tests/test_tool_text.py tests/test_layout.py -q`; `./scripts/check.sh` | exists (test_tool_text.py); exists (test_layout.py) | green |
| 2-04-01 | 04 | 3 | TOOL-02, TOOL-07, AGNT-03 | T-02-12, T-02-13, T-02-14, T-02-15 | A delegate session never writes; no replace-all write; a spoofed session id writes nothing | unit | `uv run pytest tests/test_board_tools.py tests/test_results.py -q` | exists (from plan 02-01) | green |
| 2-04-02 | 04 | 3 | TOOL-06, TOOL-08 | T-02-15 | The real Hermes registry runs the guard and the confirmed remove | unit + hermes contract + gate + full suite | `uv run pytest tests/test_register.py -q`; `uv run pytest -m hermes -q -rs`; `timeout 120 hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin`; `timeout 180 hermes plugins doctor /home/theo/local_repo/hermes-session-tasks/plugin --ci`; `./scripts/check.sh` | exists (from plan 02-01) | green |
| 2-05-01 | 05 | 4 | AGNT-01 to AGNT-04 | T-02-18 | Theo hears the announcement before the enable reload and the restart | checkpoint (human action) | none: Theo's go is the gate; Claude checks the Task 2 precondition first | n/a | green |
| 2-05-02 | 05 | 4 | AGNT-01 to AGNT-04 | T-02-17, T-02-19 | Enable grants no tool override; restart only after Theo's go | live command | `test "$(readlink -f ~/.hermes/plugins/hermes-session-tasks)" = /home/theo/local_repo/hermes-session-tasks/plugin && echo "link ok"`; `timeout 60 hermes plugins list 2>&1 \| grep -i 'hermes-session-tasks'`; `timeout 30 hermes gateway status` | n/a | green |
| 2-05-03 | 05 | 4 | AGNT-01 to AGNT-04 | T-02-16, T-02-24 | Raw stream output stays in the scratchpad; the only data.db write is the reword seed through `BoardStore.apply` | live (real model) | read-only data.db query in plan 02-05 Task 3 `<verify>` (boards count at least 2); the 18-run table and the seed step output in the SUMMARY | n/a | green |
| 2-06-01 | 06 | 5 | TOOL-02, AGNT-02 | - | One request to Theo per turn | checkpoint (human action) | none: Claude checks this turn in 2-06-02 | n/a | green |
| 2-06-02 | 06 | 5 | TOOL-02, AGNT-02 | T-02-20, T-02-21 | Read-only check of state.db and data.db before the next request | checkpoint (human action) + check script | `desktop_check.py added <restart time>` (scratchpad, plan 02-06 check_script block) | n/a | green |
| 2-06-03 | 06 | 5 | TOOL-02, AGNT-02 | T-02-20 | Read-only /compress check | live data check | read-only data.db query in plan 02-06 Task 3 `<verify>` (newest board holds at least 3 items); `desktop_check.py compressed <session id>` | n/a | green |
| 2-07-01 | 07 | 6 | TOOL-01, TOOL-02, AGNT-03 | - | One request to Theo per turn | checkpoint (human action) | none: Claude checks this turn in 2-07-02 | n/a | green |
| 2-07-02 | 07 | 6 | TOOL-01, AGNT-03 | T-02-22, T-02-23 | Read-only check of the read and the question before the next request | checkpoint (human action) + check script | `desktop_check.py read <session id> <check time>` (scratchpad, plan 02-07 check_script block) | n/a | green |
| 2-07-03 | 07 | 6 | TOOL-02, AGNT-03 | T-02-22 | Read-only final check | live data check | read-only data.db query in plan 02-07 Task 3 `<verify>` (an agent remove row on the newest board); `desktop_check.py final <session id> <check time>` | n/a | green |

Status values: pending, green, red, flaky.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. pytest, the `hermes` marker, `tests/conftest.py`, `tests/fakes.py`, `tests/home_guard.py` and `./scripts/check.sh` exist from Phase 1. Each new test file is written by its own task in the red step before the code (TDD), so no separate Wave 0 plan is needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Theo's go before the plugin enable and the gateway restart | Project deploy rule | Only Theo knows which live Desktop sessions hold work | Plan 02-05 Task 1: one announcement, one request |
| A fresh Desktop session gets three items, keeps them after /compress, then reads, renames, checks and removes at once when Theo's message names the change (ask rule as changed by quick task 261031-lbp) | TOOL-01, TOOL-02, AGNT-02, AGNT-03 | Only Theo can type in the Desktop app | Plans 02-06 and 02-07: one request per turn; Claude checks each turn from state.db and data.db. Done 2026-10-31, see the 02-06 and 02-07 SUMMARYs |
| Model behaviour: 5 of 5 list runs, the todo_list boundary, each ask case, check and say | AGNT-01 to AGNT-04 | Model behaviour has no unit test | Plan 02-05 Task 3: Claude runs 18 headless runs with the real model; no human step |
| A reword of an item Theo wrote | AGNT-03 | Model behaviour has no unit test, and only the pane writes as Theo (Phase 4) | Plan 02-05 Task 3: run reword-a, then Claude seeds the item as Theo with `BoardStore.apply` and actor user, then run reword-b. Pass under the old rule: the item keeps Theo's text and the reply asks a question (02-05 measured this before the ask rule changed); the SUMMARY records the hard guard and ask rule outcomes. Code measure stays: plan 02-02 test `test_pre_tool_call_guards_a_reword_of_an_item_theo_touched` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter (not set: AGNT-01 and AGNT-04 model behaviour has only the live measure in plan 02-05, and the own-job rule of AGNT-01 failed there)

**Approval:** validated (partial) on 2026-10-31 by the validate-phase audit

## Validation Audit 2026-11-01

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 2 |
