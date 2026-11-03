---
phase: 07-deploy-and-hardening
plan: 06
status: in-progress
requirements: [DEV-06]
plan_head_before: 6079926db9f2da213b5b6807660a18c6670e18da
---

# Phase 7 Plan 06: Public push Summary (in progress)

Task 1 passed. Task 2 (Theo's decision on the public push and the license) is open. Task 3 has not started. Nothing is pushed, no GitHub repo exists, and no LICENSE file is written.

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

## Task 3

Not started.
