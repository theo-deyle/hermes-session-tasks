---
phase: "5"
slug: "agent-sees-theo-s-edits"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-02"
---

# Phase 5 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`--import-mode=importlib --strict-markers`, `filterwarnings = ["error"]`), marker `hermes` for tests that need the Hermes checkout and its gateway venv |
| **Config file** | `pyproject.toml` (repo root) |
| **Quick run command** | `uv run pytest -q tests/test_pre_llm_hook.py tests/test_delta.py tests/test_store_seen.py tests/test_board_tools.py tests/test_session_delete.py tests/test_register.py` |
| **Full suite command** | `./scripts/check.sh` (pins, ruff, format, pyright, pytest on 3.11 and 3.14, coverage gate 80 on 3.11) |
| **Hermes contracts** | `uv run pytest -q -rs -m hermes tests/test_hermes_dispatch.py tests/test_hermes_thirty_turn.py tests/test_hermes_session_delete.py tests/test_live_delta.py` |
| **Plugin gate** | `timeout 120 hermes plugins validate plugin/` |
| **Estimated runtime** | quick run about 15 s; full suite about 3 min; live checks up to 300 s per headless turn, the token arms about 12 min in the background |

---

## Sampling Rate

- **After every task commit:** run the task's own `<automated>` command (the touched test files).
- **After every plan wave:** run `./scripts/check.sh`.
- **Before `/gsd-verify-work`:** full suite green, plugin gate green, the 05-05 live note table and gate verdict on record, the 05-07 arms report with `pass` true, and the 05-07 delete table on record.
- **Max feedback latency:** about 15 s for a task quick run; live runs only in plans 05-05 and 05-07.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | AGNT-05 | T-05-03, T-05-04 | Hook returns the note or None, never raises; delegate gets None | unit (end to end in process) | `uv run pytest tests/test_pre_llm_hook.py -q -rs` | yes (rewrite) | pending |
| 5-01-02 | 01 | 1 | AGNT-05 | T-05-01, T-05-02, T-05-05 | `<` escaped; agent rows left out; seen never hides a Theo change; cap and gap give the pointer line | unit | `uv run pytest tests/test_delta.py tests/test_store_seen.py tests/test_pre_llm_hook.py -q -rs` | W0 (new files) | pending |
| 5-01-03 | 01 | 1 | AGNT-05 | T-05-03 | Real Hermes dispatch returns only Theo's changes | unit + hermes contract + full suite | `uv run pytest tests/test_register.py tests/test_hermes_dispatch.py -q -rs` and `./scripts/check.sh` | yes (extend) | pending |
| 5-02-01 | 02 | 2 | AGNT-05 | T-05-06 | Scripted Theo edit writes only its own session | hermes contract | `uv run pytest tests/test_live_delta.py -q -rs -m hermes` | W0 (new files) | pending |
| 5-02-02 | 02 | 2 | AGNT-05, STOR-07 | T-05-07, T-05-08 | Read-only opens; stop at the first broken run | unit | `uv run pytest tests/test_live_delta.py -q -rs` | W0 (new files) | pending |
| 5-03-01 | 03 | 2 | AGNT-05 | T-05-11 | A board read clears the note | unit (end to end in process) | `uv run pytest tests/test_pre_llm_hook.py -q -rs -k board_read_by_the_agent` | yes (extend) | pending |
| 5-03-02 | 03 | 2 | AGNT-05 | T-05-09, T-05-10 | Delegate read marks nothing; mark fault keeps the tool result | unit | `uv run pytest tests/test_board_tools.py tests/test_pre_llm_hook.py tests/test_store_seen.py -q -rs` | yes (extend) | pending |
| 5-03-03 | 03 | 2 | AGNT-05 | - | 30 turns add exactly the notes through Hermes's composer | hermes contract + full suite | `uv run pytest tests/test_hermes_thirty_turn.py -q -rs -m hermes` and `./scripts/check.sh` | W0 (new files) | pending |
| 5-04-01 | 04 | 3 | STOR-07 | T-05-13 | Delete removes only the listed root's board and aliases | unit (end to end in process) | `uv run pytest tests/test_session_delete.py -q -rs -k deleted_session_takes_its_board` | W0 (new file) | pending |
| 5-04-02 | 04 | 3 | STOR-07 | - | Hook declared and registered | unit + plugin gate | `uv run pytest tests/test_register.py -q -rs` and `timeout 120 hermes plugins validate plugin/` | yes (extend) | pending |
| 5-04-03 | 04 | 3 | STOR-07 | T-05-12, T-05-13, T-05-14, T-05-15 | Archive keeps; bad payloads remove nothing; chunks of 500; never raises | unit + hermes contract + full suite | `uv run pytest tests/test_session_delete.py -q -rs`, `uv run pytest tests/test_hermes_session_delete.py -q -rs -m hermes` and `./scripts/check.sh` | W0 (new files) | pending |
| 5-05-01 | 05 | 4 | AGNT-05 | T-05-17 | Restart named before it happens; Claude checks all gates first | checkpoint (Theo's go) | none: Theo's go for a restart that drops live Desktop connections | n/a | pending |
| 5-05-02 | 05 | 4 | AGNT-05 | T-05-18 | Edits only to sessions the run created | live headless | `timeout 30 hermes gateway status` and `delta_live.py rows` on the e2e session | yes (05-02 tools) | pending |
| 5-05-03 | 05 | 4 | AGNT-05 | T-05-18 | Run output outside the repo; data files read only | live headless | `tests/live/own_job/run.sh own5-1` (2, 3), then the verdict line grep | yes | pending |
| 5-06-01 | 06 | 5 | AGNT-05 | - | One plain question only when the gate failed | checkpoint (Theo's decision) | none: Theo's choice of the reminder form | n/a | pending |
| 5-06-02 | 06 | 5 | AGNT-05 | T-05-20 | Delta part, store and SQL unchanged | unit + hermes contract + full suite | `uv run pytest tests/test_tool_text.py tests/test_pre_llm_hook.py tests/test_register.py tests/test_hermes_dispatch.py tests/test_hermes_thirty_turn.py -q -rs` and `./scripts/check.sh` | yes (extend) | pending |
| 5-06-03 | 06 | 5 | AGNT-05 | T-05-21 | Second restart named before it happens | checkpoint (Theo's go, only when hooks.py changed) | none: Theo's go | n/a | pending |
| 5-07-01 | 07 | 6 | AGNT-05 | T-05-21 | Restart only after the recorded go | live headless | outcome line grep in 05-07-SUMMARY.md | yes | pending |
| 5-07-02 | 07 | 6 | AGNT-05 | T-05-24 | Timeouts per turn and per run; stop at the first broken run | live headless | `delta_live.py arms`, then the `arms-report.json` pass check | yes (05-02 tools) | pending |
| 5-07-03 | 07 | 6 | STOR-07 | T-05-22, T-05-23 | Archive only after a dry run that lists one test session; delete only checked test ids | live CLI + full suite | `hermes sessions delete <id> --yes` with `delta_live.py rows`, `./scripts/check.sh`, `timeout 120 hermes plugins validate plugin/` | yes | pending |

*Status: pending, green, red, flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_delta.py` - SC1 line map and SC3 cap (plan 05-01)
- [ ] `tests/test_store_seen.py` - seen rules and the gap boundary (plan 05-01)
- [ ] `tests/test_live_delta.py` with `tests/live/delta/` - live tools (plan 05-02)
- [ ] `tests/hermes_snippet_setup.py`, `tests/hermes_thirty_turn_snippet.py`, `tests/test_hermes_thirty_turn.py` - SC3 character contract (plan 05-03)
- [ ] `tests/test_session_delete.py`, `tests/hermes_session_delete_snippet.py`, `tests/test_hermes_session_delete.py` - SC4 (plan 05-04)

Each file is created by the task that first needs it, test first.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Go for the gateway restart | AGNT-05 | The restart drops Theo's live Desktop connections; only he knows which chats hold work | Plan 05-05 Task 1 and, when the hook changes again, plan 05-06 Task 3 |
| Choice of the reminder form after a failed own-plan test | AGNT-05 | A decision with a cost to Theo, not a check | Plan 05-06 Task 1, only when the gate failed |

Every acceptance check is automated or run by Claude. The pane write is replaced by `tests/live/delta/theo_edit.py`, which calls the same `BoardApi.edit` as the route. The full loop on the Mac and the Windows PC is Phase 7 criterion 3.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or a checkpoint that needs Theo
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [ ] Feedback latency < 5s (quick runs take about 15 s; live checks are long by nature)
- [ ] `nyquist_compliant: true` set in frontmatter (set by validate-phase after execution)

**Approval:** pending
