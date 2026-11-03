---
phase: 07-deploy-and-hardening
plan: 06
subsystem: infra
tags: [github, public-repo, license, ci, history-scan]
requires:
  - phase: 07-deploy-and-hardening
    provides: 07-02 catalog page and CONTRIBUTING.md, 07-03 CI workflow and history scan, 07-05 version 0.2.0 head
provides:
  - The public repo theo-deyle/hermes-session-tasks with the full history of main, no squash
  - LICENSE with the MIT text in the name Theo Deyle
  - The Repo and Deploy lines of .claude/CLAUDE.md name both remotes and the host install line
  - The first CI run on the public repo passed
affects: [07-07, 07-08, 07-09]
actuals:
  tokens: 2250
  tasks: 3
  commits: 4
plan_head_before: 6079926db9f2da213b5b6807660a18c6670e18da
plan_head_after: d39efa98f8568cc3c393e7ebecdf5e20e3a2b9e5
commits: 4
tech-stack:
  added: []
  patterns:
    - "A public surface step (repo create, push) runs from one non-interactive script that Theo starts with a `!` line; the orchestrator does every step before and after it"
key-files:
  created:
    - LICENSE
  modified:
    - .claude/CLAUDE.md
key-decisions:
  - "Publish the full history as it is (option publish-as-is), MIT license, holder Theo Deyle. Theo's reply: Go ahead."
  - "The org repo Don-Mor-Software-Group/hermes-session-tasks and its remote origin stay untouched"
patterns-established:
  - "The history scan runs again at the final head before every push"
requirements-completed: [DEV-06]
coverage:
  - id: D1
    description: "The public repo serves the full history at the head of main"
    requirement: DEV-06
    verification:
      - kind: integration
        ref: "GIT_TERMINAL_PROMPT=0 git ls-remote https://github.com/theo-deyle/hermes-session-tasks refs/heads/main equals git rev-parse main (d39efa9)"
        status: pass
      - kind: integration
        ref: "gh api repos/theo-deyle/hermes-session-tasks --jq .private prints false"
        status: pass
  - id: D2
    description: "The first CI run on the public repo passed"
    requirement: DEV-06
    verification:
      - kind: e2e
        ref: "gh run 41689002986 on theo-deyle/hermes-session-tasks, conclusion success"
        status: pass
  - id: D3
    description: "LICENSE holds the MIT text in the name Theo Deyle"
    requirement: DEV-06
    verification:
      - kind: other
        ref: "head -3 LICENSE prints MIT License and Copyright (c) 2026 Theo Deyle"
        status: pass
status: complete
requirements: [DEV-06]
---

# Phase 7 Plan 06: Public push Summary

The repo is public at `theo-deyle/hermes-session-tasks` with the full history of `main` (458 commits, no squash), the MIT license in the name Theo Deyle, and a green first CI run. The org repo and its remote `origin` are unchanged.

## Task 1: pre-push checks (head 6079926)

| Check | Result |
|-------|--------|
| Fresh clone of HEAD, `HERMES_AGENT_REPO=/nonexistent/hermes-agent ./scripts/check.sh` | `1130 passed, 30 skipped in 218.06s`, then `check: python 3.14 ok`, then `check: all ok` |
| `hermes plugins validate plugin --install-deps` | `Validation passed.` |
| `node --check plugin/desktop/plugin.js` | exit 0 |
| History scan | exit 0, `history-scan: commits 453, diff lines 78066, credential hits 0` |

### Scan table

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
| other email | 24 | 9 | 10 |
| Theo | 2786 | 175 | 197 |
| Deyle | 147 | 19 | 29 |
| devpc | 725 | 85 | 109 |
| devbox | 37 | 14 | 17 |
| donmor | 76 | 22 | 26 |
| Don-Mor | 25 | 9 | 13 |
| tailscale | 27 | 14 | 16 |
| /home/theo | 198 | 46 | 57 |
| customer | 45 | 14 | 15 |
| dealer | 12 | 3 | 4 |
| dealership | 7 | 3 | 4 |

The "other email" lines are code decorators such as `@pytest.fixture`, `noreply@anthropic.com` (commit trailers), `git@github.com`, and three `.invalid` sample addresses. No third-party person email exists.

### Customer, dealer and dealership lines (read)

- `dealer` and `dealership`: all lines sit in scan commands and scan results inside `07-03-PLAN.md`, `07-03-SUMMARY.md`, `07-06-PLAN.md` and `07-RESEARCH.md`. Class: scan words, not data. Count outside those files: 0.
- `customer`: 45 lines. Class sample item text: 23 lines in 9 files outside the scan files, all the sample item `Reply to the customer` (also `Reply to the customer about 4910`). Files: `tests/test_board_cross.py`, `tests/test_pane_copy.py`, `tests/test_pane_picker.py`, `tests/test_pane_readonly.py`, `.planning/phases/06-cross-session-boards/06-04-PLAN.md`, `06-08-PLAN.md`, `06-11-PLAN.md`, `06-RESEARCH.md`, `.planning/sketches/06-session-picker.html`. The remaining lines are the scan words in `07-03-*`, `07-06-PLAN.md`, `07-RESEARCH.md` and `07-VALIDATION.md`.
- Real data lines (real person, firm, phone, address): 0. Two sample strings carry a first name (`Call John`) and a ticket number (`Syncro ticket 4910`) used as test titles. They identify no customer.

### Numbers for Theo

| Number | Value |
|--------|------:|
| Tracked files at HEAD | 338 |
| Files under `.planning/` | 204 |
| Commits | 453 |
| Lines with the name Theo | 2786 in 175 commits |
| Lines with devpc | 725 in 85 commits |
| Lines with Don-Mor | 25 in 9 commits |
| Author and committer email | `theo.deyle@donmor.ca` on every commit (one address) |

## Tree state

`git status --porcelain` shows `.planning/config.json` and `.planning/state.json` as modified. The orchestrator owns both files and ordered that this executor must not touch or commit them, so the plan step "commit pending planning state" was not run. The continuation agent needs a clean tree before the push: the orchestrator must commit or settle both files first.

## Task 2: decision

Theo saw the three points (what goes public with the full history, the work email on every commit, the MIT license recommended in his name) and the one recommendation. Before the reply he asked how the pane finds its gateway on other machines and whether a homelab Hermes host works; the answer was that the pane calls `ctx.rest` and follows the active Desktop connection, and that any host installs from the public repo.

Theo's reply, word for word: "Go ahead."

Chosen option: publish-as-is. License: MIT. Copyright holder: Theo Deyle.

The orchestrator committed `.planning/config.json` and `.planning/state.json` as 89e7fa8 before Task 3, so the tree is clean.

## Task 3: license, repo lines, final scan, push, CI

The auto mode safety check of Claude Code blocked the executor dispatch for this task (it creates a public surface). The orchestrator ran the steps before and after the push itself, and Theo started one non-interactive script for the repo creation, the remote and the push.

- `LICENSE`: MIT text copied from the Hermes LICENSE with the line `Copyright (c) 2026 Theo Deyle`. Commit a5bde81.
- `.claude/CLAUDE.md`: Repo line names the public repo (remote `public`, MIT) as the install source and the org repo (remote `origin`, private) as unchanged. Deploy line keeps the devpc symlink as dev mode and gives `hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable` for every other host. Commit 8c74e6c.
- SUMMARY with the decision: commit d39efa9. `git status --porcelain` printed nothing.
- Final-head scan at d39efa9: `history-scan: commits 458, diff lines 78199, credential hits 0`. Report counts: customer 49 lines, dealer 15, dealership 10, all sample text and scan words as read in Task 1.
- Repo: `gh repo view` returned not found, so `gh repo create theo-deyle/hermes-session-tasks --public` created it. Remote `public` added as `git@github.com:theo-deyle/hermes-session-tasks.git`.
- Push output: `To github.com:theo-deyle/hermes-session-tasks.git` and `* [new branch] main -> main`. No GH007 refusal.
- Checks: anonymous `git ls-remote` printed `d39efa98f8568cc3c393e7ebecdf5e20e3a2b9e5`, equal to `git rev-parse main`. `gh api ... --jq .private` printed `false`.
- CI: run 41689002986, event push, head d39efa9, conclusion `success`. Created 17:56:16Z, updated 18:03:07Z, about 7 minutes.
- `origin/main` before and after: 6a6dbde568495811ee236250161833e5e7aa1d74. No push to origin, no pull request.

## Self-Check: PASSED

- Commits a5bde81, 8c74e6c and d39efa9 are ancestors of HEAD and of `public/main`.
- `LICENSE` starts with `MIT License`.
- `.claude/CLAUDE.md` contains `theo-deyle/hermes-session-tasks` and `hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable`.
- The public head, the private flag and the CI conclusion match the plan's three automated checks.
