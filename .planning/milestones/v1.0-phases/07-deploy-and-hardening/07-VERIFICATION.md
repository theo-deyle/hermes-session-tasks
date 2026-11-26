---
phase: 07-deploy-and-hardening
verified: 2026-11-26T18:20:00Z
status: passed
score: 5/5 success criteria verified (2 with a recorded deviation)
covered_files:
  - ".planning/phases/07-deploy-and-hardening/07-01-PLAN.md"
  - ".planning/phases/07-deploy-and-hardening/07-01-SUMMARY.md"
  - ".planning/phases/07-deploy-and-hardening/07-02-PLAN.md"
  - ".planning/phases/07-deploy-and-hardening/07-02-SUMMARY.md"
  - ".planning/phases/07-deploy-and-hardening/07-03-PLAN.md"
  - ".planning/phases/07-deploy-and-hardening/07-03-SUMMARY.md"
  - ".planning/phases/07-deploy-and-hardening/07-04-PLAN.md"
  - ".planning/phases/07-deploy-and-hardening/07-04-SUMMARY.md"
  - ".planning/phases/07-deploy-and-hardening/07-05-PLAN.md"
  - ".planning/phases/07-deploy-and-hardening/07-05-SUMMARY.md"
  - ".planning/phases/07-deploy-and-hardening/07-06-PLAN.md"
  - ".planning/phases/07-deploy-and-hardening/07-06-SUMMARY.md"
  - ".planning/phases/07-deploy-and-hardening/07-07-PLAN.md"
  - ".planning/phases/07-deploy-and-hardening/07-07-SUMMARY.md"
  - ".planning/phases/07-deploy-and-hardening/07-08-PLAN.md"
  - ".planning/phases/07-deploy-and-hardening/07-08-SUMMARY.md"
  - ".planning/phases/07-deploy-and-hardening/07-09-PLAN.md"
  - ".planning/phases/07-deploy-and-hardening/07-09-SUMMARY.md"
---

# Phase 7 verification: deploy and hardening

Goal: the plugin installs on any Hermes host with one `hermes plugins install` line, its pane installs on any Hermes Desktop machine, and the public repo holds what the Hermes plugin catalog asks of a submission.

## Success criteria

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | The install line installs and enables the plugin on a host other than devpc, with no hand edit of `config.yaml`; the restart is announced | Passed with a deviation | 07-07-SUMMARY.md: Theo's paste from his Windows host shows `Plugin installed` and `Plugin hermes-session-tasks enabled.` Deviation: devpc no longer holds the dev link. Since 2026-11-13 it holds an installed copy from the public repo (Theo's change). |
| 2 | After a restart on devpc, every running backend runs the new code; a backend stops only after the owner check and Theo's go | Passed | 07-08-SUMMARY.md: restart on 2026-11-15 after "go ahead", new gateway pid, the live backend started after the last plugin commit, route check 401. No stop was needed. |
| 3 | A live pass on the Mac and on a Windows PC: install the pane, the agent lists items, the pane shows them, Theo edits one, the agent sees the edit | Passed with a deviation | 07-09-SUMMARY.md: Theo's report "The windows PCs (both work and home) are done, so is the mac." The data on devpc shows 24 Desktop boards and 3 boards with pane edits after 2026-11-15. Deviation: the scripted four-step record does not exist; the per-machine proof is Theo's report. |
| 4 | The public repo holds the history, the README, CONTRIBUTING, a catalog entry file and a CI run; `hermes plugins validate` passes; the README says that closing the only pane disables the plugin | Passed | `theo-deyle/hermes-session-tasks` at 5a8c54f equals local `main` minus one merge commit. CI runs on 6daab51, 4342a15, aa751b7, e45e480 and f28917b: success. `hermes plugins validate plugin`: `Validation passed.` on 2026-11-26. `README.md` Known behaviour holds the line. `catalog/hermes-session-tasks.yaml` holds a placeholder sha until the entry is submitted, as planned. |
| 5 | The three pane review warnings, the stale UI-SPEC line and review note IN-05 are fixed; no user-facing string names a person or a host | Passed | 07-01, 07-04 and 07-05 SUMMARY files; `tests/test_neutral_wording.py` passes (58 doc and wording tests on 2026-11-26). |

## Requirements

| Requirement | Result |
|-------------|--------|
| DEV-04 | Complete |
| DEV-06 | Complete |

## Changes after the phase plans (quick tasks)

| Task | Change | Check |
|------|--------|-------|
| 261123-b4n | Tasks button on the status bar and a palette command | pane tests |
| 261123-c04 | Width cap of the pane | pane tests |
| 261126-n7k | Item number beside each item | 213 pane tests passed |
| 261126-s4r | Session reads through the Hermes storage interface; version 0.2.1; Requirements section in the READMEs | probe against Hermes v0.23.4-86, 957 tests passed, confirmed by Theo on the affected gateway |

## Known gaps (devpc test environment, not the product)

- `scripts/check.sh` stops at its pin check on devpc: the repo pins ruff 0.15.10 and Hermes v0.23.1 pins 0.15.22.
- Two tests in `tests/test_catalog_entry.py` and the `hermes`-marked tests name `~/.hermes/hermes-agent/venv/bin/python`. Hermes v0.23 runs on `~/.hermes/tools/python-3.14.9` and that path is gone. CI on GitHub does not run these tests and is green.
- The org repo `Don-Mor-Software-Group/hermes-session-tasks` is behind `main` since PR #1. It accepts changes only through a pull request.
