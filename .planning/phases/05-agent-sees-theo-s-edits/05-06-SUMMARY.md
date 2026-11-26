---
phase: 05-agent-sees-theo-s-edits
plan: 06
subsystem: hook-text
tags: [hermes-plugin, pre_llm_call, own-plan, reminder-line, AGNT-05]
status: complete

requires:
  - phase: 05-agent-sees-theo-s-edits
    provides: the own-plan result, gate passed 3 of 3 (05-05)
provides:
  - The one-line reminder text and its two tests are gone; the prompt section is the only carrier of the own-plan rule
  - The ask to Theo about the reminder was not needed
affects: [05-07]

actuals:
  tokens: 400
  tasks: 3
  commits: 1
plan_head_before: c8e0730e6716e531dcf7235770e6680ee44cb9d9
plan_head_after: 517140951bc0d8466f99285c806df42a185dc7f1
commits: 1

tech-stack:
  added: []
  patterns:
    - "Remove dead text constants together with their tests in one commit"

key-files:
  created:
    - .planning/phases/05-agent-sees-theo-s-edits/05-06-SUMMARY.md
  modified:
    - plugin/session_tasks/tool_text.py
    - tests/test_tool_text.py

key-decisions:
  - "Branch none: the own-plan test passed 3 of 3 with the prompt section alone, so no reminder returns on any turn."

requirements-completed: [AGNT-05]

coverage:
  - id: D1
    description: "The one-line reminder constant and its two tests are removed; no reminder text reaches any turn"
    requirement: AGNT-05
    verification:
      - kind: other
        ref: "grep -rn --include='*.py' NUDGE_LINE plugin tests (no output)"
        status: pass
      - kind: integration
        ref: "./scripts/check.sh (830 passed on 3.11, python 3.14 ok, check: all ok)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The delta part of the note, the seen rules and the store are unchanged"
    requirement: AGNT-05
    verification:
      - kind: other
        ref: "git diff --quiet <05-05 commit> -- plugin/session_tasks/delta.py store.py rows.py (exit 0)"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-02
---

# Phase 5 Plan 06: Own-plan reminder decision Summary

**The own-plan test passed 3 of 3 without the one-line reminder, so the reminder text and its two tests were removed and the prompt section stays the only carrier.**

## Performance

- **Duration:** 8 min
- **Completed:** 2026-11-02T16:11:00Z
- **Tasks:** 3 (Tasks 1 and 3 recorded their no-question outcome)
- **Files modified:** 2

## Branch

branch: none (gate passed 3 of 3 in 05-05-SUMMARY.md line 134). Theo was not asked: no question.

hooks.py changed: no

No second restart needed. Plan 05-07 reads this line as its precondition: the code that runs in the gateway did not change in this plan, because `NUDGE_LINE` was never read by any hook after plan 05-01 (only the constant and its two tests existed).

## Accomplishments

- Removed `NUDGE_LINE` from `plugin/session_tasks/tool_text.py`.
- Removed `NUDGE_LINE_MAX_CHARS`, `NUDGE_ALLOWED_DIGITS` and the two reminder tests from `tests/test_tool_text.py`.
- `PROMPT_SECTION_TEXT` is unchanged. The note of Theo's changes, its cap and its seen rules are unchanged (`delta.py`, `store.py`, `rows.py` show no diff against the 05-05 commit).
- ROADMAP Phase 5 criterion 2 stays as written: a turn with no change gets no injected text.

## Task Commits

1. **Task 1: Ask Theo about the one-line reminder, only when the gate failed** - no commit. Branch none, gate passed, no question.
2. **Task 2: Make the branch change** - `5171409` (refactor). The branch none change deletes code and tests only, so no RED commit applies: there is no new behavior to fail first.
3. **Task 3: Second restart announcement, only when hooks.py changed** - no commit. `hooks.py changed: no`, so no second restart needed and nothing to ask.

**Plan metadata:** the docs commit that holds this file.

## Files Created/Modified

- `plugin/session_tasks/tool_text.py` - `NUDGE_LINE` removed.
- `tests/test_tool_text.py` - two reminder tests and their two constants removed.

## Verification

- `grep -rn --include='*.py' NUDGE_LINE plugin tests`: no output (pass).
- `./scripts/check.sh`: 830 passed, `check: python 3.14 ok`, `check: all ok` (pass).
- `git diff --quiet <05-05 commit> -- plugin/session_tasks/delta.py plugin/session_tasks/store.py plugin/session_tasks/rows.py`: exit 0 (pass).

## Decisions Made

- Branch none, taken from the measured result. The accepted own-plan rate is the measured 3 of 3 with the prompt section as the only carrier (05-05).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The `tests/home_guard.py` noise from live use did not fire in the check run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 05-07 may start. The hook code did not change, but plan 05-07 still announces its own gateway restart and waits for Theo's go before it restarts (T-05-21).

## Self-Check: PASSED

- FOUND: commit 5171409 is an ancestor of HEAD.
- FOUND: plugin/session_tasks/tool_text.py and tests/test_tool_text.py changed as listed.
- No em dash or en dash in this file.

---
*Phase: 05-agent-sees-theo-s-edits*
*Completed: 2026-11-02*
