---
phase: quick-261031-uzq
plan: 01
subsystem: agent-tools-and-skill
tags: [tool-text, skill, prompt-section, planning-docs]
requires:
  - phase: 02-agent-tools-and-skill
    provides: board_read and board_edit tools, guard, prompt section, board-rules skill
provides:
  - own-plan rule text in both tool descriptions, the prompt section, SKILL_DESCRIPTION and the skill
  - D-21 in 02-CONTEXT.md and matching PROJECT, REQUIREMENTS, ROADMAP and CLAUDE.md text
affects: [phase 2 live test, agent behavior]
actuals:
  tokens: 9000
  tasks: 2
  commits: 3
plan_head_before: 955b6aedd8ab2567f8a377e66cd69e88b5ec9503
plan_head_after: fbb003ee9aa82c48a6a8743673473f73b94fb3cb
tech-stack:
  added: []
  patterns: ["static rule text pinned by tests on every surface"]
key-files:
  created: []
  modified:
    - tests/test_tool_text.py
    - plugin/session_tasks/tool_text.py
    - plugin/skills/board-rules/SKILL.md
    - .planning/PROJECT.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/phases/02-agent-tools-and-skill/02-CONTEXT.md
    - .claude/CLAUDE.md
key-decisions:
  - "D-21: the board holds Theo's reminders and the agent's own steps; a job of 3 or more steps goes on the board first and each step is checked off"
  - "The agent checks a finished step off and does not remove it, so the D-18 guard keeps its meaning"
requirements-completed: [AGNT-01, AGNT-02, TOOL-08]
status: complete
---

# Phase quick-261031-uzq Plan 01: Board holds the agent's own plan Summary

Tool descriptions, prompt section and skill now tell the agent to put a job of 3 or more steps on the board first and check each step off, with `todo_list` named only as `not todo_list`.

## Tasks

| Task | Name | Commits |
| ---- | ---- | ------- |
| 1 (TDD) | Tool text, prompt section and skill carry the own-plan rule | RED d3d8204, GREEN 950122c |
| 2 | Planning files record D-21 | fbb003e |

## TDD

- RED: 18 new or changed cases failed on assertions for the planned text (own-plan rule, both-lists sentence, not-the-board sentence, retired phrases, exact skill description, rule order). 48 other cases passed. The failures were assertion errors and one `ValueError` in the order test because the new phrase was absent.
- GREEN: `tests/test_tool_text.py` 66 passed. The four-file run (tool_text, register, hermes_dispatch, layout) gave 103 passed.
- REFACTOR: none needed.

## Gates

- Prompt section is 960 characters. `BOARD_EDIT_DESCRIPTION` is 985 characters. `PROMPT_SECTION_MAX` stays 1200.
- The seven protected modules (guard, hooks, edit_args, store, board_tools, results, wiring) have no diff against 955b6ae.
- `./scripts/check.sh` ended with `check: all ok` (461 passed on Python 3.11 and the 3.14 leg ok).
- `env -u HERMES_HOME timeout 120 hermes plugins validate plugin/` printed `Validation passed.`
- No em dash or en dash in any changed file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Leftover "scratch plan" in .claude/CLAUDE.md line 209**
- **Found during:** Task 2 verify (grep for `working plan` and `scratch plan` in PROJECT.md, REQUIREMENTS.md, CLAUDE.md)
- **Issue:** The Stack Patterns section of `.claude/CLAUDE.md` said usage rules include "never use as scratch plan". The plan listed only lines 7 and 9 of that file. The line contradicts D-21 and failed the verify gate.
- **Fix:** Replaced the phrase with "put its own multi-step plan on the board".
- **Files modified:** .claude/CLAUDE.md
- **Commit:** fbb003e

**Total deviations:** 1 auto-fixed (1 bug). **Impact:** none on scope; one more sentence in the same file now agrees with D-21.

## Known Stubs

None.

## Threat Flags

None. No new network, auth, file or schema surface.

## Self-Check: PASSED

- Commits d3d8204, 950122c, fbb003e are ancestors of HEAD.
- tool_text.py, SKILL.md and the five planning files exist and hold the new text.
