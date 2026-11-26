---
phase: 07-deploy-and-hardening
plan: 02
subsystem: docs
tags: [readme, catalog-page, contributing, install-docs]

requires:
  - phase: 07-deploy-and-hardening
    provides: "07-01 neutral wording (no person name in package text)"
provides:
  - plugin/README.md as the catalog page with the host line, the full pane URL, update, known behaviour and disclosure
  - README.md as the repo front page (catalog page text plus a pointer to CONTRIBUTING.md)
  - CONTRIBUTING.md with the devpc dev setup, restart rule, version rule, catalog note and the fallback script steps
  - tests/test_docs.py as the standing guard for identifier forms, the pane line, the disclosure, names and dashes
affects: [07-03, 07-05, 07-09]

actuals:
  tokens: 9200
  tasks: 2
  commits: 2
plan_head_before: 0ce5807e9d69289a89197c0a3f27cf0e037b095e
plan_head_after: dd81fc9b8f1dda133f269cbdea30a6aa031d906d
commits: 2

tech-stack:
  added: []
  patterns: ["User pages are scanned by a test for person names, host words and long dashes; the dev file is scanned for the person name only"]

key-files:
  created: [plugin/README.md, CONTRIBUTING.md, tests/test_docs.py]
  modified: [README.md, tests/test_install_script.py, scripts/install-desktop.ps1]

key-decisions:
  - "The old README sections for the fallback script move to CONTRIBUTING.md with their words, commands and headings. The sub-headings drop one level and the Update heading reads Update by script."
  - "CONTRIBUTING.md keeps the sentence 'Closing the only pane disables the plugin' under its own heading, so the moved script test keeps every assertion."

requirements-completed: [DEV-04, DEV-06]

coverage:
  - id: D1
    description: "plugin/README.md holds the host install and update lines, the full Desktop URL and path form, the pane line and the disclosure words"
    requirement: DEV-04
    verification:
      - kind: unit
        ref: "tests/test_docs.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "README.md starts with the text of plugin/README.md and points to CONTRIBUTING.md; neither user page names a person or a host"
    requirement: DEV-06
    verification:
      - kind: unit
        ref: "tests/test_docs.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "CONTRIBUTING.md holds the dev setup, restart rule and fallback script steps; the script tests follow the move"
    requirement: DEV-06
    verification:
      - kind: unit
        ref: "tests/test_docs.py, tests/test_install_script.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "The install lines work in a real Desktop dialog on the Mac and the Windows PC"
    requirement: DEV-04
    verification: []
    human_judgment: true
    rationale: "Plan 07-09 runs the first Desktop install. This plan pins the text by tests only."

duration: 30min
completed: 2026-11-03
status: complete
---

# Phase 7 Plan 02: Catalog page and CONTRIBUTING Summary

**The README becomes the catalog page with the one-line host install and the full-URL Desktop identifier, and the devpc setup plus the fallback script steps move to CONTRIBUTING.md, guarded by tests/test_docs.py.**

## Performance

- **Duration:** about 30 min
- **Tasks:** 2 of 2
- **Files:** 3 created, 3 modified
- **Commits:** 2 (measured from the plan ledger)

## Accomplishments

- `plugin/README.md` holds, in order: the one-sentence intro, install on a host, install the pane in Hermes Desktop, update, known behaviour, and what the plugin stores and reads.
- The host line is `hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable`. The pane section pins `https://github.com/theo-deyle/hermes-session-tasks#plugin` and the path form `theo-deyle/hermes-session-tasks/plugin`, and says the short form with `#` does not work in the dialog.
- `README.md` is the text of `plugin/README.md` plus a `## Contributing` pointer.
- `CONTRIBUTING.md` holds Set up on devpc, Link the plugin on devpc, Restart rule, Version, Catalog entry, Repos, and the fallback script section (Mac steps, Windows PC steps, dry run, update by script).
- `scripts/install-desktop.ps1` names itself as the fallback in `.DESCRIPTION`. No parameter and no code line changed.
- `tests/test_docs.py` holds 19 cases: install and update lines, pane line, disclosure words, dialog path, no bare short form, README equality, no person or host on the user pages, no long dash in the three files, the CONTRIBUTING needles and a self-test of the name and host rules.

## Task Commits

| Task | Commit | What |
|------|--------|------|
| 1 (tracer) | b530a73 | plugin/README.md, README.md, CONTRIBUTING.md fallback section, test_docs.py, test_install_script.py pins |
| 2 | dd81fc9 | CONTRIBUTING.md dev sections, CONTRIBUTING test, fallback sentence in the script |

## Verification

- `uv run pytest tests/test_docs.py tests/test_install_script.py -q -rs`: 62 passed, 0 skipped.
- `timeout 120 hermes plugins validate plugin`: `Validation passed.`
- Acceptance greps for both tasks: each needle appears.
- House gate on Python 3.11: `uv run ruff check` all checks passed; `uv run ruff format --check` 109 files already formatted; `uv run pyright` 0 errors; `uv run pytest -q` 1128 passed in 276 s.
- `./scripts/check.sh` (plan-level check) was not run. It runs under `timeout 300` and the 07-01 summary records that the suite takes about 290 s on this box. The same four gate commands ran directly on 3.11.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The moved script test needed the pane sentence in CONTRIBUTING.md**
- **Found during:** Task 1
- **Issue:** `test_contributing_warns_that_closing_the_pane_disables_the_plugin` keeps its assertion (plan step 4) and checks `closing the only pane` and `Reset layout` in the file. The plan listed no such text for CONTRIBUTING.md.
- **Fix:** Added the short section "Known behaviour of the pane" with the pane line at the end of CONTRIBUTING.md.
- **Files modified:** CONTRIBUTING.md
- **Commit:** b530a73

**Total deviations:** 1 auto-fixed. **Impact:** none on scope.

## Deferred Issues

- None new. The `scripts/check.sh` 300 s timeout noted in 07-01 still stands for plan 07-03.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None. Docs and tests only. T-07-03 and T-07-04 are mitigated by `tests/test_docs.py`.

## Next Phase Readiness

- CONTRIBUTING.md says `catalog/hermes-session-tasks.yaml` exists and is not submitted. Plan 07-03 creates that file.
- Plan 07-09 runs the first Desktop install and records what each dialog shows (RESEARCH A7).

## Self-Check: PASSED

- `plugin/README.md`, `README.md`, `CONTRIBUTING.md` and `tests/test_docs.py` exist.
- Commits b530a73 and dd81fc9 are ancestors of HEAD.
