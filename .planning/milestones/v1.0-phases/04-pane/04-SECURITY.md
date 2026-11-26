---
phase: "04"
slug: "pane"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-02"
---

# Phase 04 - Security

Register authored at plan time: yes (every plan 04-01 to 04-09 carries a STRIDE block). ASVS level 1, block on high. Classification at grep depth: every named mitigation test exists in `tests/` and the full suite passes (`./scripts/check.sh`, 744 tests on Python 3.11 and 3.14).

## Threat register

| Threat | Component | Severity | Disposition | Status | Evidence |
|--------|-----------|----------|-------------|--------|----------|
| T-04-01 | item render | high | mitigate | CLOSED | `test_item_text_stays_plain_text`, raw HTML scan in tests/test_desktop_plugin.py |
| T-04-02 | check write | medium | mitigate | CLOSED | `base_rev` on every write; stale reply tests in tests/test_pane_writes.py |
| T-04-03 | imports | medium | mitigate | CLOSED | import allowlist test, three specifiers only |
| T-04-04 | session id in the body | low | accept | CLOSED | D-25, gateway token middleware; accepted risk |
| T-04-05 | harness outside step | low | mitigate | CLOSED | posts only to the loopback relay; conftest home guard |
| T-04-06 | harness probe file | low | mitigate | CLOSED | the install script copies only `$RemotePath`; probe under tests/fixtures |
| T-04-07 | harness duringWrite hang | low | mitigate | CLOSED | `timeout=60` and `MAX_ROUNDS` in tests/pane_rig.py |
| T-04-08 | colours | low | mitigate | CLOSED | `test_plugin_has_no_colour_literal`, palette and style guards |
| T-04-09 | missing Desktop class | medium | mitigate | CLOSED | `test_every_plugin_class_ships_in_desktop` |
| T-04-10 | file size | low | mitigate | CLOSED | 800 line ceiling test; file at 799 lines |
| T-04-11 | lost update in sendOp | high | mitigate | CLOSED | `base_rev` from the newest accepted reply; one retry for a check only; WR-03 fix keeps every rev (commits c5e12df, 7bf8911) |
| T-04-12 | write storm | medium | mitigate | CLOSED | `test_writes_run_one_at_a_time`, `test_second_stale_reply_is_not_retried` |
| T-04-13 | notice line | low | mitigate | CLOSED | `test_invalid_reply_shows_write_failed` |
| T-04-14 | reply for another session | medium | mitigate | CLOSED | visit counter per focus change (WR-02 fix, commits 9ba239c, e9a7e3e); CR-01 fix pins the edit to its session (a6a588f, c1077fc) |
| T-04-15 | copy as markdown | low | accept | CLOSED | Theo starts the copy; his own board, no ids; accepted risk |
| T-04-16 | focus switch leak | medium | mitigate | CLOSED | focus change resets view state and busy flags (WR-02 fix) |
| T-04-17 | long text | low | mitigate | CLOSED | `test_long_text_wraps_and_is_never_cut`; store cap 500 |
| T-04-18 | add text | low | mitigate | CLOSED | trim, `maxLength` 500, store caps; full board test in tests/test_pane_add.py |
| T-04-19 | repeated Enter | medium | mitigate | CLOSED | `test_enter_during_a_write_sends_nothing` |
| T-04-20 | subtask parent | medium | mitigate | CLOSED | `parent_id` from the rendered id; stale subtask add test in tests/test_pane_add.py |
| T-04-21 | delete with subtasks | high | mitigate | CLOSED | SDK confirm dialog with the count; `base_rev` on the remove; tests in tests/test_pane_edit_delete.py |
| T-04-22 | edit saved twice or to the wrong item | medium | mitigate | CLOSED | `test_enter_then_blur_saves_once`; CR-01 fix adds the session check |
| T-04-23 | blank edit | low | mitigate | CLOSED | `test_unchanged_or_blank_text_sends_nothing` |
| T-04-24 | real data.db | high | mitigate | CLOSED | read-only checks; deletion behind the recorded yes with dry runs before and after (04-08-SUMMARY) |
| T-04-25 | plugin.js on the Mac | medium | mitigate | CLOSED | temp file then move; hash printed by the script |
| T-04-26 | gateway restart | low | mitigate | CLOSED | no restart; no plugin Python file changed (04-08-SUMMARY Task 1) |
| T-04-27 | `-RemotePath` in scp | medium | mitigate | CLOSED | `Test-RemotePath` allowlist; `test_bad_remote_path_is_refused` (5 cases). Open info IN-01: `..` segments pass; the person at the keyboard supplies the value |
| T-04-28 | wrong file installed | low | mitigate | CLOSED | `copy:` and `sha256:` lines; plans 03-10 and 03-11 compare the hash |
| T-04-SC | package installs | high | mitigate | CLOSED | no package install in the phase; `git diff` shows no package.json or lock file |

## Accepted risks

- T-04-04: the route takes the session id from the request body (D-25). Only the Desktop reaches the route, through the gateway session token.
- T-04-15: copy as markdown puts Theo's own board on his clipboard on his own click.

## Summary threat flags

Every SUMMARY reports `None`.
