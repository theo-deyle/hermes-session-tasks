---
phase: "05"
slug: "agent-sees-theo-s-edits"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-02"
---

# Phase 05 - Security

Register authored at plan time: yes (every plan 05-01 to 05-07 carries a STRIDE block, T-05-01 to T-05-31). ASVS level 1, block on high. Classification at grep depth: every named mitigation test exists in `tests/`, every named code pattern exists in `plugin/session_tasks/` or `tests/live/delta/`, the live mitigations are recorded in the 05-05 and 05-07 summaries, and the full suite passes (`./scripts/check.sh`, 832 tests on Python 3.11 and 3.14).

## Trust boundaries

| Boundary | Description | Data crossing |
|----------|-------------|---------------|
| Theo's pane to the agent's context | Board rows Theo wrote enter the model's user message as a fenced note | Item text, item ids, revision numbers |
| Hermes session delete to the plugin store | The `on_session_delete` payload names sessions whose boards go | Session ids, delete reason |
| Live test tools to Theo's real Hermes home | Headless turns, archive and delete of test chats only | Session ids, board rows, test titles |
| Real Hermes home to the twin test homes | An allowlisted config copy, no secret file | Model and agent settings, plugin names |

## Threat register

| Threat | Component | Severity | Disposition | Status | Evidence |
|--------|-----------|----------|-------------|--------|----------|
| T-05-01 | delta.py note text | high | mitigate | CLOSED | `escape` turns `<` into `&lt;` (delta.py:22), own tag `DELTA_TAG`; `test_text_cannot_close_the_fence` |
| T-05-02 | read_user_changes_after | medium | mitigate | CLOSED | `actor = 'user'` filter (rows.py:202); `test_agent_rows_are_left_out` |
| T-05-03 | pre_llm_call | medium | mitigate | CLOSED | `except Exception` returns None with one warning; fault tests in tests/test_pre_llm_hook.py |
| T-05-04 | pre_llm_call | medium | mitigate | CLOSED | delegate check (hooks.py:50, 106); `test_delegate_session_returns_none` |
| T-05-05 | agent_seen_rev updates | medium | mitigate | CLOSED | monotonic and conditional `UPDATE` (rows.py:216, 222); `test_agent_edit_after_a_theo_edit_keeps_the_theo_change`, `test_mark_seen_never_moves_down` |
| T-05-06 | theo_edit.py | high | mitigate | CLOSED | one `--session` through BoardApi.edit; `test_theo_edit_leaves_other_boards_alone` |
| T-05-07 | delta_live.py rows and arms | medium | mitigate | CLOSED | read-only URI opens (delta_live.py:240), queries filter on one session id |
| T-05-08 | arms loop | low | mitigate | CLOSED | `timeout` per run in delta_live.py; stop at the first broken run (05-07 summary) |
| T-05-09 | board_read seen mark | medium | mitigate | CLOSED | delegate check (board_tools.py:74); `test_delegate_read_does_not_mark_seen` |
| T-05-10 | `_mark_seen` | medium | mitigate | CLOSED | `test_a_failing_seen_mark_still_returns_the_board` |
| T-05-11 | seen value from a tool | low | mitigate | CLOSED | mark at the rev of the returned board; monotonic store mark (rows.py:216) |
| T-05-12 | on_session_delete on archive | high | mitigate | CLOSED | `ARCHIVE_REASON` check before any read (hooks.py:29, 140); `test_archive_keeps_the_board`; real SessionDB archive case |
| T-05-13 | delete by an odd or forged id | high | mitigate | CLOSED | type checks and exact root match; `test_alias_only_match_keeps_the_board`, `test_bad_payloads_remove_nothing` |
| T-05-14 | bulk deleted_ids | medium | mitigate | CLOSED | `SQL_IN_CHUNK = 500` (store.py:38); `test_twelve_hundred_ids_are_deleted_in_chunks` |
| T-05-15 | callback inside the Hermes delete thread | medium | mitigate | CLOSED | `test_store_fault_logs_a_warning_and_raises_nothing` |
| T-05-16 | missed delete in another process | low | accept | CLOSED | accepted risk, D-37 defers the orphan sweep |
| T-05-17 | gateway restart | high | mitigate | CLOSED | announced; Theo's go recorded word for word; `--yes --detach` only after it (05-05 summary) |
| T-05-18 | test chats in the real home | high | mitigate | CLOSED | edits only to the four created session ids, all listed and deleted in 05-07 |
| T-05-19 | Desktop backends on older code | low | accept | CLOSED | accepted risk, schema unchanged, Phase 7 rollout |
| T-05-20 | reminder replay cost | low | mitigate | CLOSED | reminder never came back; `NUDGE_LINE` removed in 05-06 |
| T-05-21 | second gateway restart | high | mitigate | CLOSED | `hooks.py changed: no`, no second restart (05-06, 05-07 summaries) |
| T-05-22 | `hermes sessions archive` bulk filter | high | mitigate | CLOSED | unique title; dry run listed exactly one session before the real run (05-07 summary) |
| T-05-23 | `hermes sessions delete` of test chats | high | mitigate | CLOSED | four listed ids, each checked read only; board count 25 to 21 (05-07 summary) |
| T-05-24 | 90-turn token test | low | mitigate | CLOSED | `timeout` per turn and on the run; stop at the first broken run |
| T-05-25 | make_home.py | high | mitigate | CLOSED | `SECRET_NAME` guard (make_home.py:46, 64); `test_make_home_holds_no_secret_file`, `test_make_home_refuses_the_real_home_and_a_secret_looking_kept_key` |
| T-05-26 | test home listeners | high | mitigate | CLOSED | `test_make_home_turns_every_listener_off`, `test_port_clash_names_a_shared_port_and_a_public_listener` |
| T-05-27 | stop of a test gateway | high | mitigate | CLOSED | pid file and `/proc/<pid>/environ` match (delta_live.py:312-344); `test_stop_refuses_a_pid_file_for_another_home` |
| T-05-28 | removal of the test homes | medium | mitigate | CLOSED | links deleted first, paths checked under the cache dir (05-07 summary) |
| T-05-29 | Theo's real gateway during the token test | high | mitigate | CLOSED | PID 799352 unchanged before the probes, after the probes and after the arms (05-07 summary) |
| T-05-30 | test gateway listeners and pollers | high | mitigate | CLOSED | every platform off; `ports` check after the probes, no clash (05-07 summary) |
| T-05-31 | model access for a test home | high | mitigate | CLOSED | no secret file linked, copied or read; credentials stay in the Claude Code store; both probes exited 0 |

## Accepted risks

| Risk ID | Threat ref | Rationale | Accepted by | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-16 | A delete in another process or while Hermes is down leaves an inert board that nothing resolves to; the orphan sweep is deferred in D-37 | Theo (D-37, 05-CONTEXT) | 2026-11-02 |
| AR-05-02 | T-05-19 | The Desktop backends keep the Phase 4 code until each Desktop app restarts; the schema did not change, so both code versions share the data file safely | Theo (Phase 7 rollout) | 2026-11-02 |

## Summary threat flags

Every SUMMARY reports `None`.

## Security audit trail

| Audit date | Threats total | Closed | Open | Run by |
|------------|---------------|--------|------|--------|
| 2026-11-02 | 31 | 31 | 0 | orchestrator, grep depth (ASVS L1 short-circuit) |

## Sign-off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in the accepted risks log
- [x] `threats_open: 0` confirmed
