---
phase: 03-rest-router-and-client-install-spike
plan: 03
subsystem: desktop-install
tags: [powershell, pwsh, scp, hermes-desktop, install-script, pytest, readme]
status: complete

requires:
  - phase: 03-rest-router-and-client-install-spike
    provides: D-26 decision (copy script) and RESEARCH Answer 5 (Desktop home rule)
provides:
  - scripts/install-desktop.ps1 with Resolve-HermesHome, Get-DesktopHome, Test-DevpcHost, Copy-RemoteFile, Install-PanePlugin, Invoke-Main
  - tests/test_install_script.py with a fake scp rig, 36 tests
  - README.md with install steps for the Mac and the Windows PC
affects: [03-08, 03-10, phase-07]

actuals:
  tokens: 5927
  tasks: 3
  commits: 6
plan_head_before: 81916abdc2fd6a8558a7126c60acc6826146112b
plan_head_after: e5fbc15e6c2b0f5fa6374904d3725a33ae8ab432

tech-stack:
  added: []
  patterns:
    - "Script functions are pure where possible: Resolve-HermesHome takes every input as a parameter, so a dot-source test reaches the Windows branch on Linux"
    - "The last script line runs Invoke-Main only when the script is not dot-sourced"
    - "Output lines use Write-Host so a function can return its exit code without noise"
    - "pwsh tests run the script with -File and a fake scp first on PATH; the fake runs as a child process"

key-files:
  created:
    - scripts/install-desktop.ps1
    - tests/test_install_script.py
    - README.md
  modified: []

key-decisions:
  - "Install script returns an exit code from Invoke-Main and calls exit only on the last line, so a dot-source defines functions and runs nothing"
  - "Output uses Write-Host and errors use [Console]::Error, so functions return only their value"
  - "A relative -HermesHome is refused with exit 1 before any folder or scp work"
  - "A directory in place of plugin.js is refused (added beyond the plan)"
  - "Bad-host tests pass the value as -DevpcHost:<value> so a leading dash reaches the guard"

requirements-completed: [DEV-05]

coverage:
  - id: D1
    description: "install-desktop.ps1 copies plugin.js through scp into the Desktop slot in one atomic move and prints the path and SHA-256"
    requirement: DEV-05
    verification:
      - kind: integration
        ref: "tests/test_install_script.py#test_script_installs_the_file_and_prints_path_and_hash"
        status: pass
      - kind: integration
        ref: "tests/test_install_script.py#test_second_run_gives_the_same_hash"
        status: pass
    human_judgment: false
  - id: D2
    description: "The script finds the Desktop home on Windows, macOS and Linux as data-paths.mjs does, refuses bad input, supports a dry run and keeps an installed file on failure"
    requirement: DEV-05
    verification:
      - kind: unit
        ref: "tests/test_install_script.py#test_resolve_hermes_home_follows_the_desktop_rule"
        status: pass
      - kind: integration
        ref: "tests/test_install_script.py#test_failed_copy_keeps_the_old_file"
        status: pass
      - kind: integration
        ref: "tests/test_install_script.py#test_bad_host_is_refused"
        status: pass
      - kind: integration
        ref: "tests/test_install_script.py#test_dry_run_writes_nothing"
        status: pass
    human_judgment: false
  - id: D3
    description: "README gives numbered PowerShell steps for the Mac and the Windows PC, the file location, dry run, update and pane-close behavior with no long dashes"
    requirement: DEV-05
    verification:
      - kind: unit
        ref: "tests/test_install_script.py -k readme"
        status: pass
    human_judgment: false
  - id: D4
    description: "The script works on the real Mac and the real Windows PC over the real SSH link (scp -O, drive letter target, Windows home)"
    requirement: DEV-05
    verification: []
    human_judgment: true
    rationale: "Only a run on each machine proves the Tailscale SSH copy and the Windows home. Plans 03-08 (Mac) and 03-10 (Windows PC) own those runs."

duration: 8min
completed: 2026-11-01
---

# Phase 3 Plan 03: Desktop install script and README Summary

**PowerShell 7 script that copies the Desktop pane file from devpc over scp into the slot Desktop scans, with Desktop's own home rule per OS, host and home guards, a dry run and an atomic replace, plus per-machine README steps.**

## Performance

- **Duration:** 8 min (2026-11-01T04:23:23Z to 04:31Z)
- **Tasks:** 3
- **Files created:** 3
- **Commits:** 6 (3 test, 2 feat, 1 docs)

## Accomplishments

- `scripts/install-desktop.ps1` copies `devpc:/home/theo/local_repo/hermes-session-tasks/plugin/desktop/plugin.js` to `.plugin.js.new` in `<home>/desktop-plugins/hermes-session-tasks/`, requires `export default`, moves it over `plugin.js` and prints `home:`, `slot:`, `copy:`, `installed:`, `sha256:` in that order. It tries `scp -O` then plain `scp`.
- `Resolve-HermesHome` follows `data-paths.mjs`: env home first (a `profiles` parent maps to the grandparent), then on Windows the user registry value, then `%LOCALAPPDATA%\hermes` plus suffix, with the legacy `~\.hermes` only when the default is missing, the legacy exists and no suffix is set; `~/.hermes` plus suffix elsewhere. Eleven table cases cover each branch.
- Guards: `Test-DevpcHost` allows only `^[A-Za-z0-9._@-]+$` with no leading dash; `-HermesHome` must be a full path. Both refuse with exit 1 before any scp call or folder.
- `-DryRun` prints the plan and `dry run: nothing written`, creates nothing and calls no scp.
- A failed copy, an empty file or a file without `export default` leaves the old `plugin.js` byte for byte and no temp file.
- `README.md` has numbered PowerShell steps for the Mac and the Windows PC, `%LOCALAPPDATA%\hermes` for Windows, the dry run, the update path and the known behavior (closing the only pane disables the plugin; Reset layout).

## TDD record

**Task 1 (tracer)**
- RED: `test_script_installs_the_file_and_prints_path_and_hash` failed on `assert 64 == 0`. The first run hit a fixture fault (`bin_dir.mkdir()` without `parents=True`), which is not a valid red, so I fixed the fixture and ran again. The second run failed on the planned assertion because `scripts/install-desktop.ps1` did not exist (pwsh exit 64). Semantic assessment: the target test ran and failed for the intended reason. Commit `20e11bb`.
- GREEN: the script copies, checks, moves and prints. 1 passed. Commit `95749a0`.
- Tracer gate: the verify command ran again after the commit (1 passed) and the commit order check passed (oldest 03-03 commit is `test(03-03)`). Log: `Tracer verified end-to-end - expanding`.

**Task 2**
- RED: 20 failed, 10 passed. The 20 failures hit the planned gaps: no `Resolve-HermesHome` (11 cases), the default and env home, relative home, three bad hosts, dry run and the directory guard. The 10 passing tests cover Task 1 behavior (fallback, failed copy, bad file, second run, order, source check). Commit `9db3576`.
- GREEN: 29 passed after the script change, then 30 after one test fix (see Deviations). Final 36 passed with the README tests. Commit `45d935e`.

**Task 3**
- RED: 6 failed because `README.md` did not exist. Commit `67a260a`.
- GREEN: README written; 6 passed after one test fix. Commit `e5fbc15`.

## Verification

- `uv run pytest tests/test_install_script.py -q -rs`: 36 passed, 0 skipped.
- `uv run pytest tests/test_install_script.py -q -rs -k readme`: 6 passed.
- README dash check with `chr(0x2014)` and `chr(0x2013)`: exit 0.
- Full suite `uv run pytest -q`: 565 passed. `ruff check .`, `ruff format --check .` and `pyright`: clean.
- Acceptance greps (`function Resolve-HermesHome`, `LOCALAPPDATA`, `dry run: nothing written`, the remote path, `#Requires -Version 7.0`, `InvocationName -ne '.'`, `LOCALAPPDATA%\hermes`, `Reload desktop plugins`, `-DevpcHost`): all exit 0.
- `./scripts/check.sh` was not run here. The plan asks for it after the wave merges, and it syncs two Python environments.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Directory in place of plugin.js**
- **Found during:** Task 2
- **Issue:** `Move-Item -Force` onto an existing directory moves the file inside it, so the script would report an install that Desktop never loads.
- **Fix:** `Install-PanePlugin` refuses with exit 1 and no scp call when `plugin.js` is a directory. Test `test_directory_in_place_of_plugin_js_is_refused` covers it.
- **Files modified:** scripts/install-desktop.ps1, tests/test_install_script.py
- **Commit:** 45d935e

**2. [Rule 1 - Bug] Test faults found while writing the tests**
- **Found during:** Tasks 1, 2 and 3
- **Issue:** (a) the rig fixture did not create its parent folder; (b) an empty `-DevpcHost:` value is dropped by pwsh and the default host applies, so that case never reached the guard; (c) the README test searched for lower case `closing the only pane` while the README sentence starts with a capital.
- **Fix:** (a) `mkdir(parents=True)`; (b) the empty name is tested through a dot-source call of `Test-DevpcHost` (`test_empty_host_name_is_refused`); (c) the test lowers the README text first.
- **Files modified:** tests/test_install_script.py
- **Commits:** 20e11bb, 45d935e, e5fbc15

**3. [Rule 3 - Blocking] Stray `rel/` folder in the repo root**
- **Found during:** Task 3 status check
- **Issue:** The Task 2 red run executed the Task 1 script with `-HermesHome rel/path`. With no home guard yet, it wrote `rel/path/desktop-plugins/...` under the repo root. The green script refuses a relative home.
- **Fix:** Removed the untracked `rel/` folder. Later runs do not create it.
- **Files modified:** none tracked

**Total deviations:** 3 (1 missing critical, 1 bug in tests, 1 blocking cleanup). **Impact:** none on scope; the script and README match the plan.

## Threat model

T-03-09 (host argument), T-03-10 (downloaded file), T-03-11 (home argument) and T-03-12 (no expression runner) are mitigated and tested. T-03-SC: no package install. The script and README hold no secret.

## Issues Encountered

None open.

## Known Stubs

None.

## Threat Flags

None. The script adds no network endpoint or auth path. It runs `scp` over the SSH link the Desktop already uses.

## Flagged assumptions (carried forward)

- RESEARCH A3: the Windows PC ssh name for devpc is unknown. The README tells the reader to use the name from the SSH config of that PC.
- RESEARCH A4 and A5: `scp -O` may be needed in front of Tailscale SSH, and a relative target avoids the Windows drive-letter problem. Only the runs in plans 03-08 and 03-10 confirm both. No test here reaches a real SSH link or a real Windows host.
- The Windows branch of the home rule is tested on Linux through parameters, not on Windows.

## Next Phase Readiness

Ready for 03-04. The script and README are ready for the Mac run (03-08) and the Windows PC run (03-10). The Desktop file `plugin/desktop/plugin.js` does not exist yet, so a real install waits for the plan that writes it.

## Self-Check: PASSED

- Files found: scripts/install-desktop.ps1, tests/test_install_script.py, README.md.
- Commits found on HEAD: 20e11bb, 95749a0, 9db3576, 45d935e, 67a260a, e5fbc15.
