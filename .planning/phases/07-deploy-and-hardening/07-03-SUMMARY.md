---
phase: 07-deploy-and-hardening
plan: 03
subsystem: infra
tags: [catalog, ci, github-actions, history-scan, security]

requires:
  - phase: 07-deploy-and-hardening
    provides: "07-01 neutral wording, 07-02 catalog page and CONTRIBUTING.md"
provides:
  - catalog/hermes-session-tasks.yaml, a ready catalog entry (not submitted) that both Hermes catalog checks accept
  - .github/workflows/ci.yml, which runs ./scripts/check.sh on push and pull request with read-only rights and pinned actions
  - scripts/history_scan.py, a stdlib scan of the whole git history that prints counts only
  - the first scan table of HEAD (0 credential hits)
affects: [07-05, 07-06]

actuals:
  tokens: 5977
  tasks: 3
  commits: 5
plan_head_before: ac1bb82ac4a9de09231a82e404b065ab5a814bc7
plan_head_after: 358a0b608b9a5479fd16a876c2452ae825a1a358
commits: 5
status: complete

tech-stack:
  added: []
  patterns:
    - "Line-based stdlib readers for YAML files in tests, because the dev group has no YAML parser"
    - "Fake secrets in tests are joined from parts at run time, so no token-shaped text sits in the repo"

key-files:
  created:
    - catalog/hermes-session-tasks.yaml
    - tests/test_catalog_entry.py
    - .github/workflows/ci.yml
    - tests/test_ci_file.py
    - scripts/history_scan.py
    - tests/test_history_scan.py
  modified:
    - scripts/check.sh

key-decisions:
  - "The catalog entry carries a known_issues line (Closing the only pane disables the plugin.); both validators accept it."
  - "The scan counts a word only as a whole word: letters or digits next to it break the match."
  - "The credential-hit total is the sum of matching diff lines over the ten credential classes; the exit code is 1 when it is above 0."
  - "The check.sh pytest bound moves from 300 to 900 seconds so the local script and CI finish."

requirements-completed: [DEV-06]

coverage:
  - id: D1
    description: "Catalog entry file that matches plugin.yaml and passes the Hermes validator and loader"
    requirement: DEV-06
    human_judgment: false
    verification:
      - kind: unit
        ref: "tests/test_catalog_entry.py (9 tests, 2 of them hermes-marked)"
        status: pass
  - id: D2
    description: "CI workflow that runs the house gate with read-only rights and three pinned actions"
    requirement: DEV-06
    human_judgment: true
    rationale: "The file is checked line by line. The first real run on a GitHub runner happens in plan 07-06 after the push."
    verification:
      - kind: unit
        ref: "tests/test_ci_file.py (7 tests)"
        status: pass
  - id: D3
    description: "History scan that prints counts only and exits 1 on a credential-class hit"
    requirement: DEV-06
    human_judgment: false
    verification:
      - kind: unit
        ref: "tests/test_history_scan.py (8 tests)"
        status: pass
      - kind: other
        ref: "python3 -I scripts/history_scan.py . --word devpc exits 0 with credential hits 0"
        status: pass
---

# Phase 7 Plan 03: Catalog entry, CI and history scan Summary

A ready catalog entry (not submitted), a CI workflow that runs the house gate, and a stdlib history scan that prints counts only; HEAD scans clean with 0 credential hits.

## Accomplishments

- `catalog/hermes-session-tasks.yaml` has the `plugin-catalog` shape: quoted placeholder `sha`, `subdir: plugin`, quoted `version` equal to the manifest, capabilities equal to the manifest lists, and the disclosure in the description.
- The Hermes validator prints `OK: 1 file(s) valid`. The Hermes loader (`entry_from_mapping`) gives the install identifier `https://github.com/theo-deyle/hermes-session-tasks#plugin`.
- `.github/workflows/ci.yml` runs on push and pull request with `contents: read`, `actions/checkout@v7`, `actions/setup-node@v7`, `astral-sh/setup-uv@v10.3.3`, the whitespace check, `node --check` and `./scripts/check.sh`. `HERMES_AGENT_REPO` points at a missing path so the hermes-marked tests skip.
- `scripts/history_scan.py` streams `git log --all -p`, counts ten credential classes and the report classes (GUID, commit identity, other email, each `--word`), and prints names and counts only.

## Validator output

```
OK: 1 file(s) valid
https://github.com/theo-deyle/hermes-session-tasks#plugin
```

## History scan of HEAD (first scan, commit 358a0b6)

Command: `python3 -I scripts/history_scan.py . --word Theo --word Deyle --word devpc --word devbox --word donmor --word Don-Mor --word tailscale --word /home/theo --word customer --word dealer --word dealership`. Exit code 0.

| Pattern | Lines | Commits | Files |
|---------|------:|--------:|------:|
| GitHub token | 0 | 0 | 0 |
| GitLab token | 0 | 0 | 0 |
| sk- API key | 0 | 0 | 0 |
| AWS access key id | 0 | 0 | 0 |
| Slack token | 0 | 0 | 0 |
| private key block | 0 | 0 | 0 |
| JWT | 0 | 0 | 0 |
| authorization header literal | 0 | 0 | 0 |
| secret-like assignment | 0 | 0 | 0 |
| internal IPv4 address | 0 | 0 | 0 |
| GUID | 12 | 9 | 8 |
| commit identity | 13 | 9 | 9 |
| other email | 23 | 8 | 9 |
| Theo | 2780 | 173 | 196 |
| Deyle | 143 | 18 | 28 |
| devpc | 722 | 84 | 108 |
| devbox | 35 | 13 | 16 |
| donmor | 74 | 21 | 25 |
| Don-Mor | 23 | 8 | 12 |
| tailscale | 25 | 13 | 15 |
| /home/theo | 196 | 45 | 56 |
| customer | 43 | 13 | 14 |
| dealer | 10 | 2 | 3 |
| dealership | 5 | 2 | 3 |

Last line: `history-scan: commits 443, diff lines 77239, credential hits 0` (2 refs).

The report-class rows are counts for a read in plan 07-06 (RESEARCH A6). They do not change the exit code.

## Task commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (tracer) | 0493a93 | feat(07-03): add catalog entry file and its checks |
| 2 | 3e813e8 | feat(07-03): add CI workflow that runs the house gate |
| 2 (deviation) | 5973968 | fix(07-03): raise the check.sh pytest bound to 900 seconds |
| 3 RED | d4d26e8 | test(07-03): add failing tests for the history scan |
| 3 GREEN | 358a0b6 | feat(07-03): add the history scan that prints counts only |

Tracer gate: the tracer `<verify>` (stdlib tests, hermes-marked tests, Hermes validator) ran and passed before Task 2 started. Tracer verified end-to-end, then expanded.

## House gate (run directly, not through check.sh)

| Command | Result |
|---------|--------|
| `uv run ruff check` | All checks passed |
| `uv run ruff format --check` | 113 files already formatted |
| `uv run pyright` | 0 errors, 0 warnings |
| `uv run pytest -q` | 1152 passed in 271.66s |

The tracer sabotage check for Task 2 passed: changing `setup-node@v7` to `@v6` made `test_the_actions_are_exactly_the_three_pinned_ones` fail, and the revert made it pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] check.sh pytest bound too short**
- **Found during:** Task 2 (the CI workflow calls `./scripts/check.sh`)
- **Issue:** The two `timeout 300` bounds in `scripts/check.sh` are shorter than the full suite (about 272 to 292 s here, slower on a runner). The script would time out before `check: all ok`, in CI and locally. Plans 07-01 and 07-02 hit this and ran the gate commands directly.
- **Fix:** Both bounds are now `timeout 900`. The CI job limit stays at 25 minutes.
- **Files modified:** scripts/check.sh
- **Commit:** 5973968

**2. [Note - RED evidence] One RED test passed for the wrong reason**
- **Found during:** Task 3 RED run
- **Issue:** `test_a_path_that_is_not_a_repo_gives_one_error_line` passed while the script did not exist, because Python exits 2 with one stderr line for a missing file. 7 of 8 tests failed as expected.
- **Fix:** The test now also asserts that stderr starts with `history-scan: error:`. It is tightened in the GREEN commit (358a0b6).

**Total deviations:** 1 auto-fixed (1 blocking), 1 note. **Impact:** none on scope; `check.sh` now ends with `check: all ok`.

## Known Stubs

None. The `sha` in the catalog entry is a deliberate placeholder with a `# PLACEHOLDER` comment; it is replaced at submission (T-07-07, deferred).

## Threat Flags

None. The new surface (CI workflow, scan script, catalog file) is the surface in the plan's threat model (T-07-05, T-07-06, T-07-07, T-07-SC).

## Flagged assumptions that stay open

- The GitHub runner finishing under 25 minutes, running the pane harness on node 22 and downloading the managed Pythons through uv is checked in plan 07-06 after the push.
- The scan covers the listed patterns only. A secret in a custom format would not match.

## Issues Encountered

None.

## Next

Ready for the next plan of phase 07.

## Self-Check: PASSED

- Files found: catalog/hermes-session-tasks.yaml, tests/test_catalog_entry.py, .github/workflows/ci.yml, tests/test_ci_file.py, scripts/history_scan.py, tests/test_history_scan.py.
- Commits found: 0493a93, 3e813e8, 5973968, d4d26e8, 358a0b6.
- First commit of tests/test_history_scan.py starts with `test(07-03)`.
