---
phase: "01"
slug: "core-storage-and-session-identity"
# status lifecycle: draft (seeded by plan-phase) -> validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-30"
---

# Phase 01 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 plus pytest-cov 7.1.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` - Wave 0 creates it |
| **Quick run command** | `uv run pytest tests/test_<module>.py -q` |
| **Full suite command** | `./scripts/check.sh` (ruff, format check, pyright, pytest on 3.11 then 3.14) |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_<changed module>.py -q` plus `uv run ruff check . && uv run pyright`
- **After every plan wave:** Run `./scripts/check.sh`
- **Before `/gsd-verify-work`:** Full suite must be green, coverage at or above 80 percent
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01-01 | 1 | STOR-01, STOR-02, STOR-06, STOR-08, DEV-02 | T-01-01, T-01-02, T-01-03, T-01-04, T-01-05 | blank session id rejected, unknown root creates no row, migrate idempotent, newer schema refused | end to end | `uv run pytest tests/test_tracer.py -q` | ❌ W0 | ⬜ pending |
| 01-01-01 | 01-01 | 1 | DEV-01 | T-01-SC | lock pins equal the gateway and Hermes pins before the first install | gate | `uv run --no-project --python 3.11 -- python -I scripts/check_pins.py` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01-01 | 1 | DEV-01 | T-01-SC | N/A | matrix | `./scripts/check.sh` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01-01 | 1 | DEV-02 | T-01-06 | core imports stdlib only, no `pyproject.toml` in `plugin/`, no raw connect outside `paths.py`, `SessionDB` read only | guard | `uv run pytest tests/test_layout.py -q` | ❌ W0 | ⬜ pending |
| 01-02-01 | 01-02 | 2 | STOR-02 | T-01-09 | caps enforced, text sanitised | unit | `uv run pytest tests/test_store_items.py -q` | ❌ W0 | ⬜ pending |
| 01-02-01 | 01-02 | 2 | STOR-03 | T-01-09 | depth 2 rejected, ids never reused | unit | `uv run pytest tests/test_store_subtasks.py -q` | ❌ W0 | ⬜ pending |
| 01-02-02 | 01-02 | 2 | STOR-04 | T-01-08, T-01-10 | stale write rejected, descendant clause, no partial batch | unit | `uv run pytest tests/test_store_revision.py -q` | ❌ W0 | ⬜ pending |
| 01-02-03 | 01-02 | 2 | STOR-05, DEV-02 | T-01-07 | no lost write across processes | integration (processes) | `timeout 240 uv run pytest tests/test_race.py -q` | ❌ W0 | ⬜ pending |
| 01-03-01 | 01-03 | 2 | STOR-08 | T-01-11, T-01-12, T-01-20 | `#12` escape, depth clamp, too_long counted | unit | `uv run pytest tests/test_markdown.py -q` | ❌ W0 | ⬜ pending |
| 01-03-02 | 01-03 | 2 | STOR-08 | T-01-11 | import stops at the cap and reports overflow | unit | `uv run pytest tests/test_markdown_roundtrip.py -q` | ❌ W0 | ⬜ pending |
| 01-04-01 | 01-04 | 2 | STOR-06 | T-01-14, T-01-15, T-01-21 | missing session writes no alias, delegate stores nothing | unit with `FakeSessionReader` | `uv run pytest tests/test_lineage.py -q` | ❌ W0 | ⬜ pending |
| 01-04-02 | 01-04 | 2 | STOR-06 | T-01-16 | branch copied once, edits stay apart | unit and processes | `timeout 240 uv run pytest tests/test_fork.py -q` | ❌ W0 | ⬜ pending |
| 01-04-03 | 01-04 | 2 | STOR-01 | T-01-13 | reader built with `read_only=True`, file opened through `plugin_db` | unit | `uv run pytest tests/test_adapters.py -q` | ❌ W0 | ⬜ pending |
| 01-04-03 | 01-04 | 2 | STOR-01, STOR-06 | T-01-13, T-01-17 | fake equals real `SessionDB`, state.db bytes unchanged | contract (`hermes`) | `uv run pytest -m hermes tests/test_hermes_contract.py -q -rs` | ❌ W0 | ⬜ pending |
| 01-05-01 | 01-05 | 3 | STOR-01, STOR-04, STOR-06, STOR-08 | - | ROADMAP criteria 1 to 4 end to end | integration | `uv run pytest tests/test_phase_flow.py -q` | ❌ W0 | ⬜ pending |
| 01-05-02 | 01-05 | 3 | DEV-01, DEV-02 | T-01-18 | coverage at or above 80 percent on 3.11 | matrix | `./scripts/check.sh` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Task ID format: `<phase>-<plan>-<task>`. Each test file is created by the task that owns it (tests first). Plan 01-01 is Wave 0: it creates the harness, the fakes and the toolchain.

---

## Wave 0 Requirements

- [ ] `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore` (`.venv*/`), `scripts/check.sh`
- [ ] `tests/conftest.py` - autouse `HERMES_HOME` on `tmp_path`, autouse no-network guard, `hermes` marker skip, injected clock, `connect_path` factory fixture
- [ ] `tests/fakes.py` (plan 01-01); `tests/race_worker.py` (plan 01-02); `tests/fork_race_worker.py` (plan 01-04)
- [ ] Every test file named in the map above
- [ ] `plugin/session_tasks/__init__.py` and module skeletons so pyright has a target
- [ ] `scripts/check_pins.py`, the pin-versus-gateway check (plan 01-01, runs before the first `uv sync`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tool `session_id` equals `focusedStoredSessionId` after `/compress` on a live Desktop | STOR-06 | Needs a tool and a pane, which do not exist in Phase 1 | Moved to Phase 2 per RESEARCH.md. The resolver makes both ids map to one board either way. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
