---
phase: "07"
slug: "deploy-and-hardening"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-03"
---

# Phase 07 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 with pytest-cov 7.1.0, ruff 0.15.10, pyright 1.1.414, node VM harness |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, marker `hermes`) |
| **Quick run command** | `uv run pytest -q tests/test_<module>.py` |
| **Full suite command** | `./scripts/check.sh` |
| **Estimated runtime** | ~240 seconds per Python version |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q tests/test_<module>.py` for the touched module plus `uv run ruff check . && uv run ruff format --check .`
- **After every plan wave:** Run `./scripts/check.sh`
- **Before `/gsd-verify-work`:** Full suite must be green, `hermes plugins validate plugin --install-deps` passes, `node --check plugin/desktop/plugin.js` exits 0, history scan reports zero token hits
- **Max feedback latency:** 240 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | DEV-04 | — | N/A | unit | `uv run pytest -q tests/test_version.py tests/test_desktop_plugin.py` | ✅ | ⬜ pending |
| TBD | TBD | TBD | DEV-04 | — | N/A | unit | `uv run pytest -q tests/test_docs.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DEV-04 | — | N/A | integration | `HERMES_HOME=<scratch> hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DEV-06 | — | No secret value printed | unit | `uv run pytest -q tests/test_catalog_entry.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DEV-06 | — | N/A | tool | `timeout 120 hermes plugins validate plugin --install-deps` | ✅ | ⬜ pending |
| TBD | TBD | TBD | DEV-06 | — | No person or host name in public strings | unit | `uv run pytest -q tests/test_neutral_wording.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DEV-06 | — | N/A | unit | `uv run pytest -q tests/test_ci_file.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DEV-06 | — | History holds no token, key or customer data | script | `python3 -I scripts/history_scan.py .` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DEV-06 | — | N/A | pane harness | `uv run pytest -q tests/test_pane_picker.py tests/test_pane_view.py` | ✅ | ⬜ pending |
| TBD | TBD | TBD | DEV-06 | — | N/A | unit | `uv run pytest -q tests/test_copy_args.py tests/test_api_copy.py tests/test_layout.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

The planner fills Task ID, Plan and Wave from the PLAN.md files.

---

## Wave 0 Requirements

- [ ] `tests/test_catalog_entry.py` - the catalog entry matches `plugin.yaml` and passes the Hermes validator
- [ ] `tests/test_docs.py` - identifier forms, the "closing the only pane disables the plugin" line, no personal or host names
- [ ] `tests/test_neutral_wording.py` - no `Theo` or `devpc` under `plugin/`, `README.md`, `CONTRIBUTING.md`
- [ ] `tests/test_ci_file.py` - the workflow calls `./scripts/check.sh` and pins action versions
- [ ] `scripts/history_scan.py` - counts only, never a value

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full loop on the Mac and on a Windows PC through Install from Git | DEV-04 | Needs the physical machines and the Desktop dialog | Four steps per machine, one request per turn, result recorded word for word (D-57) |
| Desktop backends stopped on devpc | DEV-04 | Stops live Desktop connections; needs Theo's go | List lock files, match pid and command line, stop matched pids after the go (D-55) |
| Public push of the full history | DEV-06 | One-way action | `checkpoint:decision` before the push task (D-50) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 240s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
