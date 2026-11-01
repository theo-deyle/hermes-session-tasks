---
phase: "3"
slug: "rest-router-and-client-install-spike"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-31"
---

# Phase 3 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`--import-mode=importlib --strict-markers`, `filterwarnings = ["error"]` plus two narrow TestClient ignores), node 24.19.0 VM harness, pwsh 7.6.4 |
| **Config file** | `pyproject.toml` (repo root) |
| **Quick run command** | `uv run pytest -q tests/test_api.py tests/test_api_load.py tests/test_events.py tests/test_pre_llm_hook.py tests/test_version.py tests/test_desktop_plugin.py tests/test_install_script.py` |
| **Full suite command** | `./scripts/check.sh` (pins, ruff, format, pyright, pytest on 3.11 and 3.14, coverage gate 80 on 3.11) |
| **Plugin gates** | `timeout 120 hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin`; `timeout 180 hermes plugins doctor /home/theo/local_repo/hermes-session-tasks/plugin --ci` |
| **Estimated runtime** | quick run about 20 s; full suite about 3 min |

---

## Sampling Rate

- **After every task commit:** run the task's own `<automated>` command (the quick run of the touched test files).
- **After every plan wave:** run `./scripts/check.sh`.
- **Before `/gsd-verify-work`:** full suite green, both plugin gates green, 3 of 3 own-job runs on record (03-07), live reports from the Mac and the Windows PC on record (03-08 to 03-11).
- **Max feedback latency:** about 20 s for a task quick run; the live own-job runs take up to 300 s each and run only in 03-07.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | AGNT-01 | T-03-02 | Hook returns str or None, never raises | unit + hermes contract | `uv run pytest tests/test_register.py -q` and `uv run pytest -m hermes tests/test_hermes_dispatch.py -q -rs` | partly (extend) | pending |
| 3-01-02 | 01 | 1 | AGNT-01 | T-03-01, T-03-03 | Board block fenced, `<` escaped, capped; delegate and blank get None | unit | `uv run pytest tests/test_pre_llm_hook.py tests/test_tool_text.py tests/test_hooks.py tests/test_layout.py -q` | W0 (new file) | pending |
| 3-01-03 | 01 | 1 | AGNT-01 | T-03-04 | Analyzer opens data.db read only | unit | `uv run pytest tests/test_own_job_analyze.py -q` | W0 (new file) | pending |
| 3-02-01 | 02 | 1 | API-01 | T-03-07 | Host-style load, no relative import, core under its own key | unit (TestClient) | `uv run pytest tests/test_api_load.py -q` | W0 (new file) | pending |
| 3-02-02 | 02 | 1 | API-01 | T-03-05, T-03-06, T-03-08 | extra fields refused (no confirmed); parameterised SQL; structured 200 for stale and invalid; plain def handlers | unit (TestClient) + full suite | `uv run pytest tests/test_api.py tests/test_store_list.py tests/test_api_load.py tests/test_board_tools.py tests/test_results.py -q` and `./scripts/check.sh` | W0 (new files) | pending |
| 3-03-01 | 03 | 1 | DEV-05 | T-03-10 | Atomic copy with `export default` check and SHA-256 | unit (pwsh -File, fake scp) | `uv run pytest tests/test_install_script.py -q -rs` | W0 (new file) | pending |
| 3-03-02 | 03 | 1 | DEV-05 | T-03-09, T-03-11, T-03-12 | Host regex, full-path home, no Invoke-Expression, old file kept on failure | unit (pwsh -File, dot-source) | `uv run pytest tests/test_install_script.py -q -rs` | W0 (new file) | pending |
| 3-03-03 | 03 | 1 | DEV-05 | - | N/A (docs) | text check | `uv run pytest tests/test_install_script.py -q -rs -k readme` | W0 (new file) | pending |
| 3-04-01 | 04 | 2 | API-03 | T-03-30 | Meta reply holds ids and versions only; version read never raises | unit (TestClient) | `uv run pytest tests/test_version.py tests/test_api_load.py -q` | W0 (new file) | pending |
| 3-04-02 | 04 | 2 | API-03 | T-03-31 | No async def and no third-party or relative import in the dashboard | unit + full suite | `uv run pytest tests/test_layout.py -q` and `./scripts/check.sh` | yes (extend) | pending |
| 3-05-01 | 05 | 2 | API-02 | T-03-15 | Actor agent on the tool path, user on the route path; signature change and its tests in one commit | unit + hermes contract | `uv run pytest tests/test_events.py tests/test_board_tools.py tests/test_register.py tests/test_api.py -q` and `uv run pytest -m hermes tests/test_events.py -q -rs` | W0 (new file) | pending |
| 3-05-02 | 05 | 2 | API-02 | T-03-13, T-03-14 | Payload holds no text; publish after commit; fault never fails a write | unit + full suite | `uv run pytest tests/test_events.py -q` and `./scripts/check.sh` | W0 (new file) | pending |
| 3-06-01 | 06 | 3 | DEV-05, API-03 | T-03-19 | Relay on loopback only, for one test | node VM via pytest | `uv run pytest tests/test_desktop_plugin.py -q -rs` | W0 (new files) | pending |
| 3-06-02 | 06 | 3 | API-03, DEV-05 | T-03-16, T-03-18 | Item text as plain text; stale write changes no data | node VM via pytest | `uv run pytest tests/test_desktop_plugin.py -q -rs` | W0 (new file) | pending |
| 3-06-03 | 06 | 3 | DEV-03 | T-03-17 | Three allowed imports only; no colour literal, raw HTML or socket | unit + full suite | `uv run pytest tests/test_desktop_plugin.py tests/test_version.py -q -rs` and `./scripts/check.sh` | yes (extend) | pending |
| 3-07-01 | 07 | 3 | AGNT-01 | T-03-20, T-03-21 | Run output outside the repo; data.db read only | live headless | `tests/live/own_job/run.sh r1-1` (2, 3) with `OWN_JOB_OUT="$HOME/.cache/hermes-session-tasks/own-job"`, then the analyzer loop in the task verify | yes (03-01) | pending |
| 3-07-02 | 07 | 3 | AGNT-01 | T-03-22 | Wording change passes the tool text tests before any run | live headless + unit | analyzer loop over the last round, and `uv run pytest tests/test_tool_text.py tests/test_pre_llm_hook.py -q` | yes (03-01) | pending |
| 3-08-01 | 08 | 4 | DEV-05, API-01, API-02, API-03 | T-03-32 | Gateway decision recorded with evidence; live_check.py read only | gates + script | `./scripts/check.sh` and `timeout 120 hermes plugins validate /home/theo/local_repo/hermes-session-tasks/plugin` | yes | pending |
| 3-08-02 | 08 | 4 | DEV-05 | T-03-24 | Hash compared with devpc | manual (Theo at the Mac) | none: physical device | n/a | pending |
| 3-08-03 | 08 | 4 | DEV-05 | T-03-23 | Restart named before it happens; Claude stops no process; ps check | manual (Theo at the Mac) + ps check | none: physical device | n/a | pending |
| 3-09-01 | 09 | 5 | DEV-05, API-03 | - | Version lines, no banner | manual (Theo at the Mac) | none: visual check on a device | n/a | pending |
| 3-09-02 | 09 | 5 | API-02 | T-03-25 | Reported rev checked against data.db read only | manual (Theo at the Mac) + live_check.py | none: visual check on a device | n/a | pending |
| 3-09-03 | 09 | 5 | API-01, API-02 | T-03-25 | Reported revs checked against data.db read only; stale write changes nothing | manual (Theo at the Mac) + live_check.py | none: visual check on a device | n/a | pending |
| 3-10-01 | 10 | 6 | DEV-05 | T-03-27 | Hash compared with devpc; home line recorded | manual (Theo at the Windows PC) | none: physical device | n/a | pending |
| 3-10-02 | 10 | 6 | DEV-05 | T-03-26 | Restart named before it happens; ps check | manual (Theo at the Windows PC) + ps check | none: physical device | n/a | pending |
| 3-10-03 | 10 | 6 | DEV-05, API-03 | - | Version lines, no banner | manual (Theo at the Windows PC) | none: visual check on a device | n/a | pending |
| 3-11-01 | 11 | 7 | API-02 | T-03-28 | Reported rev checked against data.db read only | manual (Theo at the Windows PC) + live_check.py | none: visual check on a device | n/a | pending |
| 3-11-02 | 11 | 7 | API-01, API-02 | T-03-28 | Reported revs checked against data.db read only | manual (Theo at the Windows PC) + live_check.py | none: visual check on a device | n/a | pending |
| 3-11-03 | 11 | 7 | DEV-05 | - | N/A (docs) | text check | `uv run pytest tests/test_install_script.py -q -rs -k readme` | yes (03-03) | pending |
| 3-12-01 | 12 | 8 | AGNT-01, DEV-05 | T-03-29 | No deletion without Theo's recorded answer | decision (Theo) | none: production data decision | n/a | pending |
| 3-12-02 | 12 | 8 | AGNT-01, DEV-05 | T-03-29 | Recorded-yes gate, dry run, one transaction, recount | script + full suite | `grep -Eq "^Theo's answer: (yes|no)" .planning/phases/03-rest-router-and-client-install-spike/03-12-SUMMARY.md`, `./scripts/check.sh` and validate | yes | pending |

*Status: pending, green, red, flaky*

---

## Wave 0 Requirements

Each new test file is created red in the first step of its own task (TDD), so no separate Wave 0 plan is needed.

- [ ] `pyproject.toml` - two `filterwarnings` ignores for `fastapi.testclient` (03-02 Task 1)
- [ ] `tests/api_client.py` - host-style loader, client builder, fake Hermes modules (03-02 Task 1)
- [ ] `tests/test_api_load.py`, `tests/test_api.py`, `tests/test_store_list.py` - API-01 (03-02)
- [ ] `tests/test_version.py` - API-03 (03-04)
- [ ] `tests/test_pre_llm_hook.py`, `tests/test_own_job_analyze.py` - AGNT-01 (03-01)
- [ ] `tests/live/own_job/` - job.txt, run.sh, analyze.py copied from the Phase 2 scratchpad (03-01 Task 3)
- [ ] `tests/test_install_script.py` with a fake scp - DEV-05 (03-03)
- [ ] `tests/test_events.py` - API-02 (03-05)
- [ ] `tests/desktop_pane_harness.mjs`, `tests/rest_relay.py`, `tests/test_desktop_plugin.py` - DEV-03, banner, events in the pane (03-06)
- [ ] No framework install: pytest, node and pwsh already exist on devpc.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The test pane installs by script and shows in Desktop on the Mac, with the right version lines and no banner | DEV-05, API-03 | Physical device and visual check; Claude cannot open Desktop on the Mac | 03-08 Tasks 2 and 3, 03-09 Task 1, one request each; Claude checks the hash and a new serve process in `ps` |
| A tool write and a route write show as events on the Mac; the stale write shows its answer | API-01, API-02 | Visual check on the device | 03-09 Tasks 2 and 3, one request each; Claude matches each reported rev with live_check.py |
| The same checks on the Windows PC | DEV-05, API-01, API-02, API-03 | Physical device and visual check | 03-10 Tasks 1 to 3 and 03-11 Tasks 1 and 2, one request each |
| Deletion of the test boards in the real data.db | AGNT-01, DEV-05 | Production data decision | 03-12 Task 1 question; recorded-yes gate, dry run and recount in Task 2 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or a manual-only reason
- [ ] Sampling continuity: no 3 consecutive auto tasks without automated verify (the checkpoint tasks in 03-08 to 03-11 are manual by design, one request each, and each runs a Claude-side data or process check)
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency under 20 s for task quick runs
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
