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
| 01-TBD | TBD | TBD | STOR-01 | - | DB under `<HERMES_HOME>/plugin-data/hermes-session-tasks/data.db`, `state.db` never created, reader opened `read_only=True` | contract and unit | `uv run pytest tests/test_paths.py tests/test_hermes_contract.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD | TBD | TBD | STOR-02 | - | N/A | unit | `uv run pytest tests/test_store_items.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD | TBD | TBD | STOR-03 | - | depth 2 rejected, ids never reused | unit | `uv run pytest tests/test_store_subtasks.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD | TBD | TBD | STOR-04 | - | stale write rejected, no partial batch | unit | `uv run pytest tests/test_store_revision.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD | TBD | TBD | STOR-05 | - | no lost write across processes | integration (processes) | `uv run pytest tests/test_race.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD | TBD | TBD | STOR-06 | - | missing session writes no alias | unit with `FakeSessionReader` | `uv run pytest tests/test_lineage.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD | TBD | TBD | STOR-06 | - | fake equals real `SessionDB` | contract (`hermes`) | `uv run pytest -m hermes tests/test_hermes_contract.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD | TBD | TBD | STOR-08 | - | caps enforced, `#12` escape | unit | `uv run pytest tests/test_markdown.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD | TBD | TBD | DEV-01 | - | N/A | matrix | `./scripts/check.sh` | ❌ W0 | ⬜ pending |
| 01-TBD | TBD | TBD | DEV-02 | - | core imports stdlib only, no `pyproject.toml` in `plugin/` | guard | `uv run pytest tests/test_layout.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

The planner fills Task ID, Plan and Wave when it writes the PLAN.md files.

---

## Wave 0 Requirements

- [ ] `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore` (`.venv*/`), `scripts/check.sh`
- [ ] `tests/conftest.py` - autouse `HERMES_HOME` on `tmp_path`, `hermes` marker skip, injected clock, `connect_path` factory fixture
- [ ] `tests/race_worker.py`, `tests/fakes.py`
- [ ] Every test file named in the map above
- [ ] `plugin/session_tasks/__init__.py` and module skeletons so pyright has a target
- [ ] The pin-versus-gateway check script

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
