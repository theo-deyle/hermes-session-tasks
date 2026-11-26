---
phase: "03"
slug: "rest-router-and-client-install-spike"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-02"
---

# Phase 03 - Security

Register authored at plan time: yes (every plan 03-01 to 03-12 carries a STRIDE block, T-03-01 to T-03-32 plus T-03-SC). ASVS level 1, block on high. Classification at grep depth on HEAD 358a834 by the security auditor: every named mitigation test exists in `tests/`, every named code pattern exists in `plugin/`, `scripts/install-desktop.ps1` or the live scripts, the live mitigations are recorded in the 03-07 to 03-12 summaries, and the 12 cited test files pass (314 tests). The full suite passes too (`./scripts/check.sh`, 832 tests on Python 3.11 and 3.14).

Two Phase 3 mitigations now live in later code: plan 05-01 moved the board block from `nudge.py` to `delta.py` (T-03-01), and plan 04-01 replaced the test pane (T-03-18). The register cites the Phase 3 commit and the HEAD code that carries the same mitigation.

## Trust boundaries

| Boundary | Description | Data crossing |
|----------|-------------|---------------|
| Board text to model | Item text written by the agent or by Theo enters the turn's user message through the `pre_llm_call` hook | Item text, item ids, revision number |
| Hermes to hook | The `session_id` keyword comes from the agent loop and is the only session input | Session id |
| Desktop client to route | The pane sends `session_id`, `ops` and `base_rev` to `/board`, `/boards`, `/board/edit` and `/meta`; on the Mac and the Windows PC the calls cross the SSH tunnel; the gateway token middleware authenticates the client, the values stay untrusted | Session id, ops list, base revision |
| Route to SQLite | Route values reach parameterised SQL through BoardStore | Session id, item text, revision |
| Route reply to pane | Reply bodies go back to the pane and item text reaches the render | Board rows, rule text, fixed error strings |
| Serve process to Desktop clients | `board.updated` goes over the authenticated gateway socket to every Desktop of that process | Session id, root id, revision, actor |
| Write path to listener | A listener runs after a committed write in the same thread | Root id, session id, revision |
| Command line to install script | Theo types `-DevpcHost`, `-HermesHome` and `-RemotePath` | Host name, home path, remote path |
| Devpc to client disk (Mac, Windows PC) | The script copies plugin.js over SSH and Desktop runs it as plugin code | plugin.js bytes, SHA-256 |
| plugin.yaml to version read | A file on devpc feeds the `/meta` reply | Version string |
| Harness or Claude to real data.db | The own-job analyzer and live_check.py read the real board file; plan 03-12 deletes test boards in it | Board rows, root ids |
| Run output to repo | Own-job stream files can hold tool output and session ids | Stream text, session ids |
| Test relay | The relay listens on loopback during one test run only | Route calls against a tmp store |
| Theo's restart to live sessions | Quitting Desktop ends any chat turn on that machine | None (a dropped chat turn) |

## Threat register

| Threat | Component | Severity | Disposition | Status | Evidence |
|--------|-----------|----------|-------------|--------|----------|
| T-03-01 | nudge.board_block (now delta.delta_note) | high | mitigate | CLOSED | Phase 3 nudge.py:14-40 held the `task-board` fence, the note line, `&lt;` escape and the 2000 cap (commit 7b73c78^); plan 05-01 moved it to delta.py:14-22, 60 with a 1000 cap; `test_text_cannot_close_the_fence`, `test_one_character_more_gives_the_pointer_line` |
| T-03-02 | hooks.make_pre_llm_call | medium | mitigate | CLOSED | hooks.py:114-116 `except Exception` logs one warning and returns None; `test_store_fault_returns_none_and_logs_a_warning`, `test_resolver_fault_returns_none_and_logs_a_warning` |
| T-03-03 | hooks.make_pre_llm_call | low | mitigate | CLOSED | hooks.py:102-107 blank and delegate sessions return None before any read; `test_blank_session_returns_none`, `test_delegate_session_returns_none` |
| T-03-04 | tests/live/own_job/analyze.py | medium | mitigate | CLOSED | analyze.py:158 `mode=ro` URI; no DELETE in analyze.py or run.sh; `test_read_board_follows_the_alias_and_opens_read_only` |
| T-03-05 | GET /board, POST /board/edit | low | accept | CLOSED | accepted risk AR-03-01 (D-25); README.md:69 states any signed-in Desktop reads and writes any board and devpc serves one user |
| T-03-06 | board_api.edit | high | mitigate | CLOSED | plugin_api.py:30 `extra="forbid"`; board_api.py:124 `edit_args.parse`; edit_args.py:18 MAX_OPS 100; model.py:16-17 MAX_ITEMS 100, MAX_TEXT_CHARS 500; rows.py uses `?` placeholders only; `test_confirmed_field_is_refused`, `test_a_101st_item_is_an_invalid_reply_and_writes_nothing` |
| T-03-07 | route replies | medium | mitigate | CLOSED | board_api.py:128-129 reply holds `str(exc)` and `describe(exc)` of a BoardError only; plugin_api.py:71-90 return `reply.body` only; `test_rule_error_returns_200_invalid`, `test_transport_faults_keep_4xx` |
| T-03-08 | plugin_api handlers | high | mitigate | CLOSED | plugin_api.py:72, 81, 87, 93 plain `def`; store.py:199-271 one `open_db` per operation; `test_dashboard_defines_no_async_def` (test_layout.py:271) |
| T-03-09 | install-desktop.ps1 host argument | high | mitigate | CLOSED | install-desktop.ps1:118-123 `Test-DevpcHost` rejects a leading `-` and matches `^[A-Za-z0-9._@-]+\z`, called at :186 before any scp; :138-140 scp gets separate arguments; `test_bad_host_is_refused` (3 hosts), `test_empty_host_name_is_refused` |
| T-03-10 | downloaded plugin.js | medium | mitigate | CLOSED | install-desktop.ps1:46 `.plugin.js.new`, :170 `export default` check, :174 `Move-Item`, :175 SHA-256 line; `test_file_without_export_default_is_refused`, `test_script_installs_the_file_and_prints_path_and_hash` |
| T-03-11 | install-desktop.ps1 home argument | medium | mitigate | CLOSED | install-desktop.ps1:94-95 `IsPathRooted` check; :146-148 writes only the plugin slot file and its temp file; `test_relative_hermes_home_is_refused` |
| T-03-12 | install-desktop.ps1 | medium | mitigate | CLOSED | `test_script_source_has_no_expression_runner_and_no_marker_file` (test_install_script.py:387-390); the test rig runs `pwsh -File` (test_install_script.py:85) |
| T-03-13 | events.publish payload | medium | mitigate | CLOSED | events.py:32 payload holds session_id, root_id, rev, actor only; `test_payload_holds_no_text` |
| T-03-14 | after_write listeners | medium | mitigate | CLOSED | store.py:271-272 the transaction closes before `apply` returns; board_api.py:133-137 and board_tools.py:94-96 call `after_write` after that inside `except Exception`; events.py:39-40 catches the publish fault; `test_the_listener_sees_the_committed_rev`, `test_publish_fault_keeps_the_route_reply`, `test_publish_fault_keeps_the_tool_result` |
| T-03-15 | actor field | low | mitigate | CLOSED | wiring.py:53 `events.listener("agent", ...)`; board_api.py:150 `events.listener("user", ...)`; `test_tool_write_reaches_the_broadcast` (actor agent), `test_route_write_reaches_the_broadcast` (actor user) |
| T-03-16 | plugin.js item render | high | mitigate | CLOSED | plugin.js holds no `dangerouslySetInnerHTML` or `innerHTML`; `test_plugin_sets_no_raw_html_and_uses_no_socket` (test_desktop_plugin.py:304), `test_item_text_stays_plain_text` (:146) |
| T-03-17 | plugin.js imports | medium | mitigate | CLOSED | plugin.js:8-22 imports only the three SDK specifiers; `ALLOWED_IMPORTS` (test_desktop_plugin.py:224), `test_imports_are_on_the_allowlist`, `test_allowlist_rejects_other_imports` |
| T-03-18 | Run write test | low | mitigate | CLOSED | test pane at commit 5c3e03d plugin.js:148 `base_rev: 0`; `test_write_test_through_the_real_routes` asserted item 1 stays unchecked (retired with the test pane in 04-01); frozen copy ~/share/hermes-todo/phase3-test-pane.plugin.js:148; 03-09 summary:88 and 03-11 summary:86 record `stale write answered stale` and no rev 3 |
| T-03-19 | tests/rest_relay.py | low | accept | CLOSED | accepted risk AR-03-02; rest_relay.py:17 `LOOPBACK = "127.0.0.1"`, :21 random port for one TestClient |
| T-03-20 | real data.db (own-job runs) | medium | mitigate | CLOSED | analyze.py:158 `mode=ro`; 03-07 summary:138-148 lists the three root ids and says nothing was deleted |
| T-03-21 | run stream files | low | mitigate | CLOSED | run.sh:4-31 writes to `$OWN_JOB_OUT` only; 03-07 summary:107 output folder `$HOME/.cache/hermes-session-tasks/own-job`; the summary holds counts and ids |
| T-03-22 | NUDGE_LINE wording rounds | low | mitigate | CLOSED | no wording round ran; 03-07 summary:121 tool_text.py unchanged, `pytest tests/test_tool_text.py tests/test_pre_llm_hook.py` 81 passed |
| T-03-23 | Mac Desktop backend restart | medium | mitigate | CLOSED | 03-08 summary:223 the request named the restart and its effect before Theo quit; :225-240 process list shows Claude stopped no process |
| T-03-24 | plugin.js on the Mac | medium | mitigate | CLOSED | 03-08 summary:209-214 Theo's `sha256:` line equals the devpc hash byte for byte; install-desktop.ps1:170 `export default` check |
| T-03-25 | real data.db (Mac live test) | medium | mitigate | CLOSED | live_check.py:11 `mode=ro` URI (session scratchpad); 03-09 summary:15, 171 read-only check; 03-11 summary:145 |
| T-03-26 | Windows Desktop backend restart | medium | mitigate | CLOSED | 03-10 summary:109 the request named the restart and its effect before Theo quit; :124 the Desktop quit ended the process, not Claude |
| T-03-27 | install path on Windows | medium | mitigate | CLOSED | 03-10 summary:87-91 `home:` and `slot:` lines, write into the plugin slot only; :98 hash equals a devpc hash; host guard tests from plan 03-03 |
| T-03-28 | test items in real boards | low | accept | CLOSED | accepted risk AR-03-03; 03-11 summary:197; 03-12 summary deleted the 6 test boards on the recorded yes |
| T-03-29 | cleanup_boards.py | high | mitigate | CLOSED | cleanup_boards.py:49 `BEGIN IMMEDIATE`, :54-59 parameterised DELETE, COMMIT, ROLLBACK (session scratchpad); 03-12 summary:81 recorded yes, :113 apply behind `grep -q "^Theo's answer: yes"`, :98-117 two dry runs, :77 project Python SQLite 3.53.1 |
| T-03-30 | GET /meta | low | accept | CLOSED | accepted risk AR-03-04; version.py:46-51 body holds ok, plugin_id, backend_version, api_version only; `test_meta_holds_no_state_and_opens_no_data_file` |
| T-03-31 | plugin_api.py load | medium | mitigate | CLOSED | version.py:29-41 `read_backend_version` catches OSError and UnicodeDecodeError and returns `unknown`; `test_unreadable_manifest_gives_unknown`, `test_meta_with_no_manifest_answers_unknown`; `dashboard_import_findings` (test_layout.py:127, 275) |
| T-03-32 | messaging gateway on older code | low | accept | CLOSED | accepted risk AR-03-05; 03-08 summary:152-167 no further gateway restart in Phase 3; one restart ran before 03-07 with Theo's go, on record as a deviation |
| T-03-SC | npm/pip/cargo installs | high | mitigate | CLOSED | check.sh:7 runs `scripts/check_pins.py` first; uv.lock unchanged in the Phase 3 commits (0d7f38e..HEAD); the one pyproject.toml change (19ca900) adds two pytest warning filters, no dependency |

## Accepted risks

| Risk ID | Threat ref | Rationale | Accepted by | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-05 | Any Desktop the gateway authenticates may read or write any board by session id. Devpc serves one user. README.md:69 states it | Theo (D-25, 03-CONTEXT) | 2026-11-02 |
| AR-03-02 | T-03-19 | The test relay binds 127.0.0.1 on a random port for the length of one test and serves a tmp store | plan 03-06 | 2026-11-02 |
| AR-03-03 | T-03-28 | The test items sat in new test chats and held no personal data. Plan 03-12 asked Theo before it deleted them | Theo (03-12 Task 1, yes) | 2026-11-02 |
| AR-03-04 | T-03-30 | The /meta reply holds the plugin id, the version string and an integer only. The gateway token middleware gates the route | plan 03-04 | 2026-11-02 |
| AR-03-05 | T-03-32 | The messaging gateway holds a consistent in-memory copy of its plugin code, and the board schema has no change in Phase 3. Phase 7 (DEV-04) restarts it with an announcement | Theo (03-08 gateway decision) | 2026-11-02 |

## Summary threat flags

Plans 03-01 to 03-08 and 03-10 to 03-12 report `None` and map their new surface to the plan register. 03-09-SUMMARY.md has no `## Threat Flags` section; its body maps the live evidence to T-03-25 and records no new surface.

## Security audit trail

| Audit date | Threats total | Closed | Open | Run by |
|------------|---------------|--------|------|--------|
| 2026-11-02 | 33 | 33 | 0 | gsd-security-auditor, grep depth (ASVS L1) |

## Sign-off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in the accepted risks log
- [x] `threats_open: 0` confirmed

## Security Audit 2026-11-02

| Metric | Count |
|---|---|
| Threats found | 33 |
| Closed | 33 |
| Open | 0 |
