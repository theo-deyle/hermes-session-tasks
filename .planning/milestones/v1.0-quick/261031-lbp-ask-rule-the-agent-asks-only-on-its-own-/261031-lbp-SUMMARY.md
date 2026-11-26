---
phase: quick-261031-lbp
plan: 01
subsystem: agent-tools
tags: [ask-rule, board_edit, guard, skill, tool-text]
status: complete
requirements-completed: [AGNT-03]
actuals:
  tokens: 9000
  tasks: 3
  commits: 6
plan_head_before: 5b6897ec78fd3c8129a95bcef41d10be2037ea7e
plan_head_after: db25d56
key-files:
  modified:
    - plugin/session_tasks/guard.py
    - plugin/session_tasks/tool_text.py
    - plugin/skills/board-rules/SKILL.md
    - tests/test_guard.py
    - tests/test_hooks.py
    - tests/test_tool_text.py
    - .planning/phases/02-agent-tools-and-skill/02-CONTEXT.md
    - .planning/phases/02-agent-tools-and-skill/02-07-PLAN.md
    - .planning/REQUIREMENTS.md
key-decisions:
  - "Theo's own message that names a remove, uncheck, reword or bulk change is his answer: the agent acts at once with confirmed true."
  - "The agent asks one plain question first only on its own decision to remove, uncheck or reword, or when unsure which item Theo means."
  - "The hard guard stays unchanged; only block_message text changed."
duration: 3 min
completed: 2026-10-31
---

# Quick Task 261031-lbp: Ask rule, the agent asks only on its own decision

The block message, the board_edit description, the confirmed field, the prompt section and the skill now treat Theo's own message as his answer. The guard rule is unchanged.

## TDD record

- Task 1 RED (acd5390): 2 tests failed on the planned assertions (block message text, hook path text). GREEN (02e1be6): only `block_message` changed.
- Task 2 RED (30fb202): 11 failures (10 on the new phrases, 1 `ValueError` in `test_rules_come_in_order` because the new phrase "Theo's own message" was absent). GREEN (f26421d): 49 passed in `tests/test_tool_text.py`.
- Task 3 (30ac918): D-17 and D-18 reworded in 02-CONTEXT.md, D-19 unchanged.
- Extra docs (db25d56): plan 02-07 and AGNT-03 aligned with the new rule.

## Gates

- `uv run pytest` on guard, hooks, dispatch and tool text: 97 passed.
- Guard AST gate: `guard rule unchanged`. `git diff --quiet 5b6897e -- plugin/session_tasks/hooks.py`: exit 0.
- `./scripts/check.sh`: 426 passed on each Python, last line `check: all ok`.
- `env -u HERMES_HOME hermes plugins validate plugin/`: `Validation passed.`
- No em dash or en dash in any changed file.

## Deviations from Plan

None - plan executed exactly as written. The extra docs task changed 02-07 as follows: Task 2 is now an auto task that only runs the `read` check; the `read` mode exits 1 when `paint_present` is true (the agent did not act at once) instead of when it is false.

## Threat Flags

None.

## Known Stubs

None.

## Self-Check: PASSED

All six commits exist on main and the changed files exist on disk.
