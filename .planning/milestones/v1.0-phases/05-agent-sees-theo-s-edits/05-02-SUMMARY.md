---
phase: 05-agent-sees-theo-s-edits
plan: 02
subsystem: live-test-tools
tags: [live-checks, theo-edit, token-arms, twin-homes, stdlib, pytest]
status: complete

requires:
  - phase: 05-agent-sees-theo-s-edits
    provides: delta.py, the seen rules and the pre_llm_call note (plan 05-01)
provides:
  - theo_edit.py, the scripted Theo edit through the pane write path
  - delta_live.py, the run reader, the session row reader, the three-arm runner, the gateway stop and the port check
  - make_home.py, twin test Hermes homes (plugin on and plugin off) with no secret file
affects: [05-05, 05-06, 05-07]

actuals:
  tokens: 21500
  tasks: 3
  commits: 6
plan_head_before: cdfb520a23dd228ca0816f7746f578acc85df8de
plan_head_after: 175d061c0bfb1e57501e4bb3b45e02b945318eda
commits: 6

tech-stack:
  added: []
  patterns:
    - live scripts load by file path in tests, registered in sys.modules so dataclasses resolve
    - state files open read only through a sqlite URI with mode=ro
    - PyYAML only inside the gateway venv Python; the dev environment parses nothing
    - the gateway stop checks the pid file and the process environment before any signal

key-files:
  created:
    - tests/live/delta/theo_edit.py
    - tests/live/delta/delta_live.py
    - tests/live/delta/make_home.py
    - tests/live/delta/ok.txt
    - tests/live/delta/changes.txt
    - tests/test_live_delta.py
  modified: []

key-decisions:
  - "SC3 reading: three measured numbers (notes size, plugin fixed cost, sum against the no-plugin arm). Plan 05-07 puts the measured fixed cost next to the one derived from the code."
  - "The no-plugin arm runs in a twin test home built from the same allowlisted config, so quiet minus bare is the plugin alone. No secret file: the model provider reads the Claude Code store outside HERMES_HOME."
  - "The reminder split is built now: D-36 names the one reminder line as its own fallback, and RESEARCH predicts the own-plan gate in plan 05-05 will need it. Plan 05-07 then runs the token arms on whatever plan 05-06 settles, with no tool change in a live plan."
  - "Every listener and outside poller is off in a test home: platform blocks, proxy, update checks and plugin update checks. A kept port, listen or bind key with a non-zero value stops the build."

requirements-completed: [AGNT-05, STOR-07]

coverage:
  - id: D1
    description: "A scripted Theo edit lands in a temporary Hermes home through the pane write path and touches only its own board."
    requirement: AGNT-05
    verification:
      - kind: integration
        ref: "tests/test_live_delta.py#test_theo_edit_writes_as_theo_in_a_temporary_home"
        status: pass
      - kind: integration
        ref: "tests/test_live_delta.py#test_theo_edit_leaves_other_boards_alone"
        status: pass
    human_judgment: false
  - id: D2
    description: "The run reader, the session row reader and the three-arm comparison judge the notes, the cap, the character difference and the token ratio."
    requirement: AGNT-05
    verification:
      - kind: unit
        ref: "tests/test_live_delta.py#test_compare_three_arms_passes_with_a_positive_fixed_cost"
        status: pass
      - kind: unit
        ref: "tests/test_live_delta.py#test_compare_names_the_failed_check"
        status: pass
      - kind: command
        ref: ".venv-py3.14/bin/python -I -S tests/live/delta/delta_live.py result ~/.cache/hermes-session-tasks/own-job/nudge-check.jsonl"
        status: pass
    human_judgment: false
  - id: D3
    description: "A test home holds no secret, enables no platform or listener, refuses a kept port and a secret-looking key, and uses private modes."
    requirement: STOR-07
    verification:
      - kind: integration
        ref: "tests/test_live_delta.py#test_make_home_holds_no_secret_file"
        status: pass
      - kind: integration
        ref: "tests/test_live_delta.py#test_make_home_refuses_a_kept_port"
        status: pass
      - kind: unit
        ref: "tests/test_live_delta.py#test_make_home_turns_every_listener_off"
        status: pass
    human_judgment: false
  - id: D4
    description: "The tool stops only the test gateway it caused and reports the ports of the test and real gateways."
    requirement: STOR-07
    verification:
      - kind: unit
        ref: "tests/test_live_delta.py#test_stop_refuses_a_pid_file_for_another_home"
        status: pass
      - kind: unit
        ref: "tests/test_live_delta.py#test_stop_refuses_a_process_whose_environment_names_another_home"
        status: pass
      - kind: unit
        ref: "tests/test_live_delta.py#test_port_clash_names_a_shared_port_and_a_public_listener"
        status: pass
    human_judgment: false

duration: about 55 min (the start time was not recorded)
completed: 2026-11-02
---

# Phase 5 Plan 02: Live test tools Summary

**Four small tools for the live checks of plans 05-05 to 05-07: a scripted Theo edit through the pane write path, a run and session reader with a three-arm token comparison, and a builder of twin test Hermes homes (plugin on and off) with no secret file, every listener off and a safe gateway stop.**

## Performance

- **Duration:** about 55 min
- **Completed:** 2026-11-02
- **Tasks:** 3 (one tracer, two auto, all TDD)
- **Files:** 6 created, 0 modified

## Accomplishments

- `theo_edit.py`: reads the board rev through `BoardApi.read`, edits through `BoardApi.edit` with a no-op publisher, prints one JSON line, exits 0, 1 or 2.
- `delta_live.py`: `result`, `rows`, `arms` and `ports`. Pure helpers `parse_result`, `note_of`, `split_reminder`, `edit_ops`, `build_runs`, `compare`, `parse_ss`, `port_clash`, and `stop_test_gateway`. State files open with `mode=ro`.
- `compare` checks eight things: `reminder_runs_match`, `notes_only_on_edit_runs`, `every_note_within_cap`, `user_char_diff_equals_notes`, `token_growth_ratio_in_band`, `bare_arm_has_no_note`, `fixed_user_chars_match_reminder`, `fixed_cost_positive`. It reports the notes size, the fixed cost at run 1 and run N, and the edits-minus-bare tokens. `arms` adds the system prompt length of each home.
- `make_home.py`: allowlisted config, platforms and listeners off, memory off, one or two plugins linked, private modes. A dry build from the real config.yaml into the scratchpad succeeded (key names only on stdout, no secret file in the out dir) and the scratch dir was deleted.
- `arms` stops each test gateway in a `finally` block with `stopped`, `not running` or `refused`, and the report holds the result under `test_gateways`.

## RED evidence

- Task 1 RED: two of three tests failed on the missing script (`can't open file ... theo_edit.py`). The third (`test_theo_edit_rejects_bad_ops_json`) already passed, because Python exits 2 for a missing file. Semantic assessment: the bad-ops test proved nothing until the script existed. After GREEN it passes because the script itself exits 2 and writes nothing.
- Task 2 RED: collection failed with `FileNotFoundError` for `delta_live.py`. This is a load failure, not an assertion failure. The GREEN run passed every assertion.
- Task 3 RED: 28 failed, 10 passed. The failures were missing `make_home.py`, the changed `compare` signature, and the missing `stop_test_gateway`, `parse_ss` and `port_clash`.

## Task Commits

1. Task 1 RED: `e4b5246` test(05-02): add failing test for the scripted Theo edit
2. Task 1 GREEN: `df034c3` feat(05-02): add the scripted Theo edit for live checks
3. Task 2 RED: `afd505f` test(05-02): add live measurement helper tests
4. Task 2 GREEN: `f35691a` feat(05-02): add the live note and token arm measurement tool
5. Task 3 RED: `9ac5b60` test(05-02): add twin test home and no-plugin arm tests
6. Task 3 GREEN: `175d061` feat(05-02): add twin test homes and the no-plugin arm

## TDD Gate Compliance

The first 05-02 commit is a test commit. Each GREEN commit follows its RED commit. The ordering command of Task 1 exits 0.

## Decisions Made

1. SC3 reading, mechanism of the no-plugin arm and the reason for the reminder split: see `key-decisions` above.
2. `split_reminder` returns `(False, injected)` when the injected text starts with the reminder but no blank line follows. A longer line that only begins with the same words is then not treated as the reminder.
3. The fixed user character difference per reminder run is `reminder_chars + 2`, and 0 when no reminder file is given. Without a reminder file no run carries the reminder flag, so the check demands a difference of 0.
4. `compare` checks the user character difference on every run, not only the last one, so an error in the middle of a run cannot cancel out.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan contradicts itself on the `updates` key**
- **Found during:** Task 3 (tests)
- **Issue:** The allowlist test says the written config has no `updates` key. The listener test and the action text say `updates: {"check": False}`.
- **Fix:** The written config holds `updates` equal to exactly `{"check": False}`. The allowlist test asserts that equality, so no source value of `updates` survives. The other six dropped keys are absent.
- **Files modified:** `tests/test_live_delta.py`, `tests/live/delta/make_home.py`
- **Commit:** 9ac5b60, 175d061

**2. [Rule 1 - Bug] The tests cannot import PyYAML**
- **Found during:** Task 3 (tests)
- **Issue:** The dev environment has no PyYAML. The first test draft imported it.
- **Fix:** The tests write the fake source config as JSON (valid YAML) and read the written config through the gateway venv Python in a subprocess.
- **Files modified:** `tests/test_live_delta.py`
- **Commit:** 9ac5b60

**3. [Rule 1 - Bug] A leaked SQLite connection in a test failed the Python 3.14 run**
- **Found during:** Task 3 (`./scripts/check.sh`)
- **Issue:** `live.open_ro(state).execute(...)` left the connection open. Python 3.14 raised a `PytestUnraisableExceptionWarning` in a later test.
- **Fix:** The test closes the connection with `contextlib.closing`.
- **Files modified:** `tests/test_live_delta.py`
- **Commit:** 175d061

**4. [Rule 2 - Missing critical functionality] Extra tests for logic the plan did not cover**
- **Issue:** The plan lists no test for the read-only row reader, `build_runs`, or the positive and environment-mismatch paths of `stop_test_gateway`.
- **Fix:** Added `test_rows_report_reads_only_the_given_session_read_only`, `test_build_runs_counts_cumulative_characters`, `test_stop_ends_a_process_whose_environment_names_the_home` and `test_stop_refuses_a_process_whose_environment_names_another_home`. The stop tests use a real `sleep` child process.
- **Commit:** f35691a, 9ac5b60

**5. [Instruction conflict] Commit trailer**
- The dispatch prompt names `Co-Authored-By: Claude Fable 5.1`. The harness attribution rule for this session names `Co-Authored-By: Claude Sonnet 5.5`, which matches the model that wrote the commits. All six commits carry the Sonnet 5.5 line. The first commit was amended before the others to match.

**Total deviations:** 3 auto-fixed bugs, 1 added coverage, 1 instruction conflict. **Impact:** none on the plan's goal.

## Issues Encountered

- `./scripts/check.sh` shows 801 passed on Python 3.11 (coverage 97.59 percent, ends `check: python 3.11 ok`) and 801 passed on Python 3.14. On 3.14 the session guard in `tests/home_guard.py` then reported `real Hermes home changed: plugin-data/hermes-session-tasks/data.db` and the script exited 1. This happened on two full runs. Evidence that no test of this plan caused it:
  - Running `tests/test_live_delta.py` alone under 3.14 left the size and change time of the real `data.db` unchanged.
  - The real data file holds no row for the test session ids `live-s1` and `other` and no test item text.
  - The newest rows in the real file are `user` actions on old boards, written at 13:32, 13:37 and 13:39 UTC while the check ran. Live use of the real Hermes gateway wrote them.
  The guard therefore trips on live use of the real gateway during a 3 minute run. A clean `check: all ok` needs a run in a quiet window. The orchestrator can rerun `./scripts/check.sh` once no one uses Hermes.

## Known Stubs

None.

## Threat Flags

None. The new surface (a second gateway process, a config copy) is the surface of the plan's own threat register: T-05-06, T-05-07, T-05-08, T-05-25, T-05-26 and T-05-27 are covered by the theo_edit tests, the read-only row test, the loop stop in `run_turn`, the make_home tests, `test_make_home_turns_every_listener_off` with the port tests, and the stop tests.

## Verification

- `uv run pytest tests/test_live_delta.py -q -rs`: 38 passed, 0 skipped.
- `ruff check`, `ruff format --check` and `pyright` on the four Python files: clean.
- `.venv-py3.14/bin/python -I -S tests/live/delta/delta_live.py result ~/.cache/hermes-session-tasks/own-job/nudge-check.jsonl` prints session id `local-8b8faa2570f5e13eec1792cd7431c84977a5a9801db2b652d586d0eda2505173` and `"input_tokens": 96089`, exit 0. `-S` shows the module imports only the standard library.
- `grep -n "mode=ro"` prints three lines. `grep -n "KEPT_KEYS"` prints three lines in `make_home.py`. `grep -n "def stop_test_gateway"` prints one line. `grep -n "board_api.build"` prints one line in `theo_edit.py`.
- No live run happened: no gateway started, no `hermes chat` run, no real home written.

## Next Phase Readiness

Ready for 05-03. Plan 05-07 needs one probe turn per test home first. If the probe gets an auth error, the task stops and tells Theo in one plain line. No secret and no Infisical step is planned. The allowlist may miss a key a test home needs to start. The 05-07 probe finds that, and the executor adds the missing non-secret key to `KEPT_KEYS` with a test.

## Self-Check: PASSED

- Files found: `tests/live/delta/theo_edit.py`, `tests/live/delta/delta_live.py`, `tests/live/delta/make_home.py`, `tests/live/delta/ok.txt`, `tests/live/delta/changes.txt`, `tests/test_live_delta.py`.
- Commits found in HEAD: e4b5246, df034c3, afd505f, f35691a, 9ac5b60, 175d061.
