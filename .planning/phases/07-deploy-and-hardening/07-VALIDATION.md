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
| 7-01-01 | 01 | 1 | DEV-06 | T-07-01, T-07-02 | The note of the user's changes names no person | unit | `uv run pytest tests/test_neutral_wording.py -q -rs -k "self_test or scan_finds or delta or hooks or rows"` | no, created in this task | pending |
| 7-01-02 | 01 | 1 | DEV-06 | T-07-01 | Rule sentences keep their words apart from the name | unit | `uv run pytest tests/test_tool_text.py tests/test_register.py tests/test_board_tools.py -q -rs` | yes | pending |
| 7-01-03 | 01 | 1 | DEV-06 | T-07-02 | No person or host name in public strings | unit | `uv run pytest tests/test_neutral_wording.py tests/test_guard.py tests/test_hooks.py tests/test_delta.py tests/test_tool_text.py -q -rs` | yes after 7-01-01 | pending |
| 7-02-01 | 02 | 1 | DEV-04, DEV-06 | T-07-03, T-07-04 | No host name in the user pages; the full Desktop URL form | unit | `uv run pytest tests/test_docs.py tests/test_install_script.py -q -rs` | no, created in this task | pending |
| 7-02-02 | 02 | 1 | DEV-06 | T-07-03 | CONTRIBUTING names no person | unit | `uv run pytest tests/test_docs.py tests/test_install_script.py -q -rs` | yes after 7-02-01 | pending |
| 7-03-01 | 03 | 1 | DEV-06 | T-07-07 | Quoted placeholder sha, entry passes the Hermes loader | unit and hermes | `uv run pytest tests/test_catalog_entry.py -q -rs` | no, created in this task | pending |
| 7-03-02 | 03 | 1 | DEV-06 | T-07-05, T-07-SC | Read-only CI rights, pinned actions, no secrets | unit | `uv run pytest tests/test_ci_file.py -q -rs` | no, created in this task | pending |
| 7-03-03 | 03 | 1 | DEV-06 | T-07-06 | Counts only, never a matched value | unit and script | `uv run pytest tests/test_history_scan.py -q -rs` | no, created in this task | pending |
| 7-04-01 | 04 | 1 | DEV-06 | T-07-08, T-07-09 | One session id limit for the route and the parser | unit | `uv run pytest tests/test_api_copy.py tests/test_api.py tests/test_api_load.py tests/test_version.py tests/test_copy_args.py -q -rs` | yes | pending |
| 7-04-02 | 04 | 1 | DEV-06 | T-07-08 | One literal home of the limit | unit | `uv run pytest tests/test_layout.py -q -rs` | yes | pending |
| 7-05-01 | 05 | 2 | DEV-06 | T-07-11 | Focus moves only after Back | pane harness | `uv run pytest tests/test_pane_readonly.py -q -rs -k "focus or back"` | yes | pending |
| 7-05-02 | 05 | 2 | DEV-06 | T-07-02 | Notices reach a screen reader; the whole package scan | pane harness | `uv run pytest tests/test_pane_copy.py tests/test_pane_picker.py tests/test_neutral_wording.py -q -rs` | yes | pending |
| 7-05-03 | 05 | 2 | DEV-04 | T-07-10, T-07-SC | A stale pane copy shows the version line | unit | `uv lock --check && uv run pytest tests/test_version.py tests/test_desktop_plugin.py tests/test_catalog_entry.py -q -rs` | yes | pending |
| 7-06-01 | 06 | 3 | DEV-06 | T-07-12 | History holds no token, key or customer data | script | `python3 -I scripts/history_scan.py . --word customer` | yes after 7-03-03 | pending |
| 7-06-02 | 06 | 3 | DEV-06 | T-07-12, T-07-15 | Theo decides what goes public | decision checkpoint | manual only | n/a | pending |
| 7-06-03 | 06 | 3 | DEV-06 | T-07-13, T-07-14 | Public head equals main; first CI run passes | integration | `gh run list --repo theo-deyle/hermes-session-tasks --branch main --limit 1 --json conclusion --jq '.[0].conclusion'` | n/a | pending |
| 7-07-01 | 07 | 4 | DEV-04 | T-07-16, T-07-17, T-07-26 | Scratch home only; the real home is unchanged; the host probe is read only and records no IP address | integration | `HERMES_HOME=<scratch> hermes plugins install 'theo-deyle/hermes-session-tasks#plugin' --enable` | n/a | pending |
| 7-07-02 | 07 | 4 | DEV-04 | T-07-25 | Theo names the second host or keeps the devpc result before any other host changes | decision checkpoint | manual only | n/a | pending |
| 7-07-03 | 07 | 4 | DEV-04, DEV-06 | T-07-17, T-07-25 | Install on the named host only, stop on a taken slot; the pushed head passes the plugin checks | integration and tool | `grep -q "Proof host: devpc fresh home" 07-07-SUMMARY.md \|\| grep -q "Host update: .*already up to date" 07-07-SUMMARY.md` and `timeout 120 hermes plugins validate plugin --install-deps` | yes | pending |
| 7-08-01 | 08 | 5 | DEV-04 | T-07-21 | The test home touches no real data | live headless | `grep -cE` for the `ask rule` verdict line in 07-08-SUMMARY.md | n/a | pending |
| 7-08-02 | 08 | 5 | DEV-04 | T-07-18 | Theo's go before the restart | go checkpoint | manual only | n/a | pending |
| 7-08-03 | 08 | 5 | DEV-04 | T-07-18, T-07-19, T-07-20 | Owner-checked SIGTERM, no token printed, cleanup of own chats only | live | `grep -cE` for the `own-plan` verdict line in 07-08-SUMMARY.md | n/a | pending |
| 7-09-01 | 09 | 6 | DEV-04 | T-07-22 | The devpc dev link is unchanged | integration | `test "$(readlink -f ~/.hermes/plugins/hermes-session-tasks)" = "$(pwd)/plugin"` | n/a | pending |
| 7-09-02 | 09 | 6 | DEV-04 | T-07-22, T-07-23 | Delete of the Mac test chat after Theo's answer only | manual | manual only (Mac) | n/a | pending |
| 7-09-03 | 09 | 6 | DEV-04 | T-07-22, T-07-23, T-07-27 | Delete of the Windows test chat after Theo's answer only; the final public push after the scan and Theo's go only | manual | manual only (Windows PC, then the go question) | n/a | pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

The planner fills Task ID, Plan and Wave from the PLAN.md files.

---

## Wave 0 Requirements

- [ ] `tests/test_catalog_entry.py` - the catalog entry matches `plugin.yaml` and passes the Hermes validator (task 7-03-01)
- [ ] `tests/test_docs.py` - identifier forms, the "closing the only pane disables the plugin" line, no personal or host names (task 7-02-01)
- [ ] `tests/test_neutral_wording.py` - no `Theo` or `devpc` under `plugin/` (task 7-01-01; the whole package from task 7-05-02); `README.md` and `CONTRIBUTING.md` are checked by `tests/test_docs.py`
- [ ] `tests/test_ci_file.py` - the workflow calls `./scripts/check.sh` and pins action versions (task 7-03-02)
- [ ] `scripts/history_scan.py` - counts only, never a value, with `tests/test_history_scan.py` (task 7-03-03)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full loop on the Mac and on a Windows PC through Install from Git | DEV-04 | Needs the physical machines and the Desktop dialog | Four steps per machine, one request per turn, result recorded word for word (D-57) |
| Desktop backends stopped on devpc | DEV-04 | Stops live Desktop connections; needs Theo's go | List lock files, match pid and command line, stop matched pids after the go (D-55) |
| Public push of the full history | DEV-06 | One-way action | `checkpoint:decision` before the push task (D-50) |
| Install on a second Hermes host | DEV-04 | Changes another machine of Theo's and restarts its gateway | Plan 07-07 Task 2: Theo names the host or keeps the devpc result; Claude runs the install there only after that answer |
| Final public push of the phase record | DEV-06 | One-way action | Plan 07-09 Task 3, sixth turn: one go question that names what the push publishes, before the push |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 240s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
