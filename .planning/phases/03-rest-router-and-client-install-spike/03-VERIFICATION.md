---
phase: 03-rest-router-and-client-install-spike
verified: 2026-11-02T19:30:00Z
status: passed
score: 6/6 roadmap success criteria verified (plus all plan truths checked)
covered_files:
  - .planning/phases/03-rest-router-and-client-install-spike/03-01-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-01-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-02-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-02-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-03-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-03-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-04-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-04-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-05-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-05-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-06-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-06-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-07-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-07-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-08-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-08-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-09-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-09-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-10-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-10-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-11-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-11-SUMMARY.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-12-PLAN.md
  - .planning/phases/03-rest-router-and-client-install-spike/03-12-SUMMARY.md
  - README.md
  - plugin/dashboard/manifest.json
  - plugin/dashboard/plugin_api.py
  - plugin/desktop/plugin.js
  - plugin/plugin.yaml
  - plugin/session_tasks/board_api.py
  - plugin/session_tasks/board_tools.py
  - plugin/session_tasks/events.py
  - plugin/session_tasks/hooks.py
  - plugin/session_tasks/tool_text.py
  - plugin/session_tasks/version.py
  - plugin/session_tasks/wiring.py
  - scripts/install-desktop.ps1
  - tests/live/own_job/analyze.py
  - tests/live/own_job/run.sh
  - tests/test_api.py
  - tests/test_api_load.py
  - tests/test_desktop_plugin.py
  - tests/test_events.py
  - tests/test_install_script.py
  - tests/test_own_job_analyze.py
  - tests/test_pre_llm_hook.py
  - tests/test_version.py
covered_digest: "v4:sha256:c02bb6ef555e501054bca0241569f8595b0f58d1f943c36cc45407d4ab5c06a7"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: REST router and client install spike - Verification Report

**Phase Goal:** The pane's backend routes work. A stub pane installs and runs on the Mac and on the Windows PC. This proves the install path before the real pane exists.
**Verified:** 2026-11-02T19:30:00Z
**Status:** passed
**Re-verification:** No - initial verification

The Phase 3 test pane was replaced by the Phase 4 board pane after this phase. I did not count that as a gap. I judged each truth by the Phase 3 live evidence in the SUMMARY files, which I cross-checked against the frozen test pane at `/home/theo/share/hermes-todo/phase3-test-pane.plugin.js` and against the HEAD code that still carries the same behavior.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 0 | The agent puts its own multi-step plan on the board and checks each step off; the own-job headless run passes 3 of 3 (AGNT-01 own-plan half, routed from Phase 2). | VERIFIED | Live (03-07): round 1 passed 3 of 3 with the real model. Every run added 7 steps in one `board_edit` call, checked all 7, made 0 `todo_list` calls (sessions `local-f3aa9e18...`, `local-fe709b83...`, `local-aa471eef...`). The analyzer pass rule is unit tested (`tests/test_own_job_analyze.py`). At HEAD the Phase 3 per-turn nudge line and board block are gone by Phase 5 decision (D-35, D-36). The own-plan rule now rides in `PROMPT_SECTION_TEXT` in `plugin/session_tasks/tool_text.py` ("When a job takes 3 or more steps, add your steps to the board first"), registered in `wiring.py`. Phase 5 plan 05-05 re-ran the gate and it passed 3 of 3 with the prompt section alone (05-06 SUMMARY, branch none). The outcome of the criterion holds at HEAD. The literal "inject the live board and a nudge into every turn" no longer holds, and that is a recorded later-phase design change, not a gap. |
| 1 | A stub pane copied by script shows in Desktop on the Mac and on the Windows PC. The README gives install steps for each machine. | VERIFIED | `scripts/install-desktop.ps1` exists (199 lines), has no `Invoke-Expression`, writes no `.hermes-package.json`, and has no em or en dash. `tests/test_install_script.py` runs it under `pwsh` with a fake `scp` (dry run, atomic replace, empty and no-`export default` refusal, host regex, home rule per OS). Live Mac (03-08): the reported sha256 `4e42968a...2c63b7` equaled the devpc hash, then `5dda4c37...deacfa` after the dock fix; pane showed in Desktop. Live Windows (03-10): sha256 `91b46447...daf0e2` equaled `sha256sum plugin/desktop/plugin.js` at the plan HEAD, home `C:\Users\TheoDeyle\AppData\Local\hermes`, then the frozen test pane (`d7fcfcb7...`, hash matches the file I hashed now) via `-RemotePath`. Pane lines were reported by Theo on both machines. `README.md` has numbered steps for "Install the pane on the Mac" and "Install the pane on the Windows PC" with the real aliases `devbox` and `devpc-ts`, `-DryRun`, `Reload desktop plugins`, and the update step. |
| 2 | The stub reads a board through `ctx.rest` from the routes. A write through a route returns the new revision. A stale write returns the current board. | VERIFIED | HEAD: `plugin/dashboard/plugin_api.py` defines `GET /board`, `GET /boards`, `POST /board/edit`, `GET /meta`, all plain `def`, host-style path load with no relative import (`tests/test_api_load.py`). `board_api.py` returns `_applied_reply` with `rev` and `board`, and `_stale_reply` as HTTP 200 with `ok false`, `error stale`, `rev` and the current `board`; a rule error is HTTP 200 `invalid`; a blank session is 400 `no_session`. Tests: `test_stale_write_returns_200_with_the_current_board` and the rest of `tests/test_api.py`. Live Mac (03-09) and Windows (03-11): "write test: add ok at rev 2, stale write answered stale (stale) at rev 2"; `live_check.py` on `data.db` showed item 2 by user at rev 2 and no rev 3. The frozen pane calls `ctx.rest('/board/edit', ...)`. |
| 3 | A write from an agent tool and a write from a route both broadcast `board.updated` with the session id and revision. The stub on each machine shows whether the event arrived. | VERIFIED | HEAD: `events.publish` is the only caller of `broadcast_plugin_event`; payload is `session_id`, `root_id`, `rev`, `actor`. `wiring.py` binds `events.listener("agent", publish)` to `BoardTools`; `board_api.build` binds `events.listener("user", publish)` to `BoardApi`. The route fires only when `changed_ids` is non-empty, after the commit, and a listener fault is caught and logged. Tests in `tests/test_events.py` include the real Hermes wire name check and no event on an empty or stale write. Live: Mac `agent event: rev 1 ... (this chat)` then `pane event: rev 2 ... (this chat)`; Windows `agent event: rev 1 ... (other chat)` (label race on a brand-new chat, recorded in 03-11) then `pane event: rev 2 ... (this chat)`. Each rev matched `data.db`. |
| 4 | `/meta` returns the backend version and the API version. The stub shows a banner when its version differs from the backend. | VERIFIED | `version.meta()` returns `backend_version` (read from the `plugin.yaml` version line, `0.1.0`) and `api_version` 1; unreadable manifest gives `unknown` and never raises; the route opens no data file (`tests/test_version.py`). The pane (frozen and HEAD) holds `PLUGIN_VERSION = '0.1.0'`, `API_VERSION = 1` and calls `ctx.rest('/meta')`. The mismatch banner is covered by `test_banner_on_backend_mismatch` and `test_meta_failure_shows_no_banner_and_loads_the_board` in the node VM harness. Live on both machines the pane showed `backend 0.1.0, api 1` and `pane 0.1.0, api 1` with no mismatch line. |
| 5 | The stub file passes `node --check` and an import allowlist test (`@hermes/plugin-sdk`, `react`, `react/jsx-runtime`). | VERIFIED | I ran `node --check` on `plugin/desktop/plugin.js` and on the frozen test pane: both pass. Both files import only the three allowed specifiers. `tests/test_desktop_plugin.py` holds `ALLOWED_IMPORTS`, `test_imports_are_on_the_allowlist`, `test_allowlist_rejects_other_imports`, `test_plugin_passes_the_stdin_module_check` and the negative cases (truncated file, JSX). |

**Score:** 6/6 roadmap truths verified. No truth is behavior-unverified: the transition and ordering truths (publish after commit, stale writes nothing, seen rules) each have a passing test or a recorded live check against `data.db`.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `plugin/dashboard/plugin_api.py` | Router with board, boards, edit, meta | VERIFIED | Substantive (95 lines), loaded by path, calls core `board_api.build()` and `version.meta()`. |
| `plugin/session_tasks/board_api.py` | Route logic with structured replies | VERIFIED | Real store calls; no static returns. |
| `plugin/session_tasks/events.py` | `board.updated` publisher | VERIFIED | Wired from `wiring.py` and `board_api.build`. |
| `plugin/session_tasks/version.py` | Version handshake | VERIFIED | Reads `plugin.yaml`; `API_VERSION = 1`. |
| `plugin/session_tasks/hooks.py` | Hooks | VERIFIED | `pre_llm_call` now carries the Phase 5 delta note; see truth 0. |
| `scripts/install-desktop.ps1` | Copy script | VERIFIED | Tested with a fake `scp`; used live on both machines. |
| `README.md` | Install steps per machine | VERIFIED | Mac and Windows PC sections, no dash characters. |
| `tests/live/own_job/` | Own-job harness | VERIFIED | `analyze.py` and `run.sh` tracked; analyzer unit tested. |
| Frozen test pane | Phase 3 stub | VERIFIED | `/home/theo/share/hermes-todo/phase3-test-pane.plugin.js`, `node --check` passes, hash `d7fcfcb7...` as recorded. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `plugin_api.py` | `board_api.build` | `core_module("board_api").build()` as a FastAPI dependency | WIRED | Each request builds a new API over the production adapters. |
| `board_api.BoardApi.edit` | `events.publish` | `events.listener("user", publish)` | WIRED | Called after commit when `changed_ids` is non-empty. |
| `BoardTools` | `events.publish` | `events.listener("agent", publish)` in `wiring.py` | WIRED | Same listener type for both writers. |
| `events.publish` | Hermes `broadcast_plugin_event` | lazy import inside `publish` | WIRED | Wire name proven by the Hermes contract test. |
| `plugin.js` | the routes | `ctx.rest('/meta')`, `ctx.rest('/board/edit')`, `ctx.onEvent(EVENT_TYPE, ...)` | WIRED | Proven live on both machines. |
| `install-desktop.ps1` | Desktop home slot | `scp -O` then `scp`, temp file then move | WIRED | Proven live on both machines with hash checks. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `GET /board` | `board` | `BoardStore.get_board` over `data.db` | Yes | FLOWING |
| `POST /board/edit` | `applied.board` | `BoardStore.apply` in one write transaction | Yes (live: rev 2 in `data.db`) | FLOWING |
| `GET /meta` | `backend_version` | `plugin.yaml` version line | Yes | FLOWING |
| Pane event line | `payload.rev` | `broadcast_plugin_event` payload | Yes (live: matched `data.db` revs) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `uv run pytest -q -p no:cacheprovider` | 832 passed in 200 s | PASS |
| Pane syntax | `node --check plugin/desktop/plugin.js` and the frozen pane | both pass | PASS |
| Test boards deleted | read-only count in `~/.hermes/plugin-data/hermes-session-tasks/data.db` | 17 boards; the 6 listed roots have 0 rows | PASS |
| Frozen pane hash | `sha256sum` | `d7fcfcb7...` matches 03-10 | PASS |
| Install script safety | grep `Invoke-Expression`, `hermes-package`, em or en dash | none found | PASS |

### Probe Execution

No probe scripts declared. Skipped.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| API-01 | 03-02, 03-08, 03-09, 03-11 | Routes to read a board, list boards and apply item-level ops | SATISFIED | Truth 2; `GET /board`, `GET /boards`, `POST /board/edit` at HEAD and live. |
| API-02 | 03-05, 03-08, 03-09, 03-11 | Every write broadcasts `board.updated` with session id and revision | SATISFIED | Truth 3. |
| API-03 | 03-04, 03-06, 03-08, 03-09, 03-10 | Meta route with backend and API version | SATISFIED | Truth 4. |
| DEV-03 | 03-06 | `node --check` and an import allowlist test | SATISFIED | Truth 5. |
| DEV-05 | 03-03, 03-06, 03-08, 03-09, 03-10, 03-11, 03-12 | Copy script install, version banner, README steps per machine | SATISFIED | Truths 1 and 4. |
| AGNT-01 | 03-01, 03-07, 03-12 (own-plan half, routed from Phase 2) | The agent puts its own multi-step plan on the board | SATISFIED | Truth 0. Phase 2 left this half failed; Phase 3 live runs plus the Phase 5 re-gate close it. |

No orphaned requirement: REQUIREMENTS.md maps API-01, API-02, API-03, DEV-03 and DEV-05 to Phase 3, and AGNT-01 to Phase 2 with its own-plan half routed here. All six appear in plan frontmatter, and all are marked Complete.

### Anti-Patterns Found

None blocking. No TBD, FIXME or XXX in the covered code. No em or en dash in `README.md` or the install script.

### Advisory Findings (from 03-REVIEW.md, not must-have failures)

03-REVIEW.md has 0 critical, 3 warnings and 8 info items. The disposition file still lists them as open. None blocks a roadmap criterion, so they do not lower the status.

| Finding | Check I made | Impact |
|---------|--------------|--------|
| WR-01: a deeply nested `ops` string makes `POST /board/edit` answer 500 | I reproduced `RecursionError` from `edit_args.parse({"ops": ["[" * 100000], "base_rev": 0})` at HEAD; no `RecursionError` catch exists in `edit_args.py`. | Hostile or malformed input only, on a loopback route. Valid and stale writes are unaffected. Worth a one-line fix in a later phase. |
| WR-02: resolver and store faults other than `InvalidSession` escape as a bare 500 | Read `board_api.py`; confirmed. | A fault path only. |
| WR-03: the pane drops reloads when a board returns with a lower rev after a delete and recreate | Reported against `plugin.js` kept by Phase 4. | Affects the Phase 4 pane, not the Phase 3 stub criteria. |

### Notes (not gaps)

1. The Phase 3 criterion 0 wording (inject the board and a nudge every turn) was changed on purpose in Phase 5. The behavior it protected (3 of 3 own-plan runs) is re-measured at HEAD in Phase 5.
2. After plan 03-12 Theo ran the install line with the default `RemotePath` on the Windows PC, then `Reload desktop plugins`, so the Windows PC holds the real board pane again (the 03-12 summary carries the line). The Mac got the real pane during Phase 4.
3. On the Windows PC the first agent event line read `(other chat)` in a brand-new chat, because the frozen pane had not loaded the new session yet. The event itself arrived. 03-11 records it.
4. Two older test boards (`20261031_191523_093c62`, `20261029_124236_4ecdeb`) remain in `data.db` by design: Theo's recorded yes in 03-12 covered 6 listed roots only.
5. Regression check: Phase 01, 02, 04 and 05 VERIFICATION files all report `passed`. Phase 02 passed with one override and a recorded own-plan gap, which this phase closes. The full suite of 832 tests still passes at HEAD.

### Human Verification Required

None. The device checks (Mac and Windows PC) were done live with Theo during plans 03-08 to 03-11, and every reported number was matched against `data.db` or `ps` by the executor. The SUMMARY files hold the pasted pane lines, hashes and times.

### Gaps Summary

No gaps. The routes work and are tested through FastAPI and the real Hermes contract. The stub pane installed by script and ran on the Mac and on the Windows PC, with hash-matched installs, event lines and a stale reply checked against `data.db`. The install path is proven.

---

_Verified: 2026-11-02T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
