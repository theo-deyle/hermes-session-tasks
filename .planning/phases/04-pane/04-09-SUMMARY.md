---
phase: 04-pane
plan: 09
subsystem: desktop-install
tags: [powershell, scp, install-script, pytest]
status: complete

requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: scripts/install-desktop.ps1 and its test rig with a fake scp
provides:
  - an optional -RemotePath parameter on the Desktop install script
  - a guard that refuses an unsafe remote path before any scp call
  - one README sentence that names the option
affects: [03-10, 03-11]

requirements-completed: [DEV-05]

actuals:
  tokens: 4500
  tasks: 2
  commits: 4
commits: 4
plan_head_before: 48b3f1f1e75d4e88ca704344fae741e385f3d793
plan_head_after: 7e0f5eca8e7bb6669b2fa158eca804b8f1718cb0

tech-stack:
  added: []
  patterns:
    - allow-list guard for a value that reaches the legacy scp shell

key-files:
  created: []
  modified:
    - scripts/install-desktop.ps1
    - tests/test_install_script.py
    - README.md

key-decisions:
  - "The default of -RemotePath is the old literal, so a run without the parameter copies the same file as before."
  - "Test-RemotePath accepts only an absolute path of letters, digits, dot, underscore, dash and slash, because scp -O hands the path to a shell on devpc."

coverage:
  - deliverable: "-RemotePath installs another file and prints its copy line"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_install_script.py#test_remote_path_names_another_file"
        status: pass
  - deliverable: "Default path unchanged"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_install_script.py#test_script_installs_the_file_and_prints_path_and_hash"
        status: pass
  - deliverable: "Unsafe remote path refused before any scp call"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_install_script.py#test_bad_remote_path_is_refused"
        status: pass
  - deliverable: "README names the option"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_install_script.py#test_readme_names_the_remote_path_option"
        status: pass
---

# Phase 4 Plan 09: Install script remote path Summary

The Desktop install script takes an optional `-RemotePath`, so the Phase 3 Windows steps can install the frozen Phase 3 test pane while `plugin.js` holds the Phase 4 pane.

## Accomplishments

- `-RemotePath` parameter with the old literal as its default. The script-level assignment is gone. The help block has a `.PARAMETER RemotePath` entry.
- `Test-RemotePath` guard. `Invoke-Main` refuses a bad path with `refusing RemotePath` on stderr and exit code 1, before any folder or scp work (T-04-27).
- One README sentence in the install section.
- Install test file: 43 tests pass, 0 skipped.

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 red | failing test for the remote path | 590c022 |
| 1 green | optional remote path parameter | f472b06 |
| 2 red | guard and README tests | 5e07b55 |
| 2 green | guard and README sentence | 7e0f5ec |

## Verification

- `uv run pytest tests/test_install_script.py -q -rs`: 43 passed, 0 skipped.
- `ruff check`, `ruff format --check` and `pyright` on `tests/test_install_script.py`: clean.
- The oldest 04-09 commit is a `test(04-09)` commit.
- `./scripts/check.sh`:
  - `check: python 3.11 ok`
  - `check: python 3.14 ok`
  - `check: all ok`

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. T-04-27 is mitigated by `Test-RemotePath` and its five-case test. T-04-28 is covered by the existing `copy:` and `sha256:` output lines.

## Next Phase Readiness

Plans 03-10 and 03-11 can run `-RemotePath /home/theo/share/hermes-todo/phase3-test-pane.plugin.js` on the Windows PC and compare the `sha256:` line with `5dda4c37a622e5ef88d8d1fb0c6dfc9fa854999d4fd48a350d4169d135deacfa`.

## Self-Check: PASSED

- scripts/install-desktop.ps1, tests/test_install_script.py, README.md: found.
- Commits 590c022, f472b06, 5e07b55, 7e0f5ec: found on main.
