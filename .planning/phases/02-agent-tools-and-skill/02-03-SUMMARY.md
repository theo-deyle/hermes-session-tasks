---
phase: 02-agent-tools-and-skill
plan: 03
subsystem: agent-tools
tags: [hermes-plugin, tool-schema, system-prompt-section, skill, ste100, pytest]
status: complete

requires:
  - phase: 02-agent-tools-and-skill
    provides: tool_text.TOOLSET, BOARD_READ, BOARD_EDIT, BOARD_READ_SCHEMA, first_sentence test helper, wiring.skill_path (plan 02-01)
  - phase: 02-agent-tools-and-skill
    provides: edit_args.OP_FIELDS, the op kinds and field names the schema mirrors (plan 02-02)
provides:
  - tool_text.BOARD_EDIT_SCHEMA (flat schema, four op kinds, name, description, parameters)
  - tool_text.PROMPT_SECTION_ID, PROMPT_SECTION_TEXT, PROMPT_SECTION_MAX
  - tool_text.SKILL_NAME, SKILL_DESCRIPTION
  - plugin/skills/board-rules/SKILL.md (bundled skill body)
affects: [02-04, 02-05]

actuals:
  tokens: 3900
  tasks: 2
  commits: 4
plan_head_before: 5a5351f1a4710cd6ab6f6091321a3f00d8c6ce80
plan_head_after: b001beb79749db804c14ca8b706e4471c1f1b2e7

tech-stack:
  added: []
  patterns:
    - "All model-facing text is a module constant in tool_text.py, so the prompt cache stays stable"
    - "The same key phrases appear in the tool description, the prompt section and the skill body"
    - "todo check counts code points after str.lower(): one todo_list per description, no other todo"
    - "Schema walkers in tests check every depth for combinators, type arrays and session_id"

key-files:
  created:
    - plugin/skills/board-rules/SKILL.md
  modified:
    - plugin/session_tasks/tool_text.py
    - tests/test_tool_text.py

key-decisions:
  - "The prompt section text is one static str of 736 characters (limit 1000, cap 1200, Hermes cap 4000)"
  - "The skill description holds no colon, so the frontmatter stays a plain YAML scalar"
  - "The dash test builds U+2014 and U+2013 with chr(), so the test file holds no dash character itself"
  - "The first-sentence check mirrors the Hermes catalog rule: end at . ! or ? followed by a space, at most 60 characters"

patterns-established:
  - "Rule order in every layer: trigger, then todo_list boundary, then ask rule, then check-and-say rule"
  - "Plan 02-04 adds the cross-check between BOARD_EDIT_SCHEMA and edit_args.OP_FIELDS"

requirements-completed: [TOOL-02, TOOL-08, AGNT-01, AGNT-02, AGNT-03, AGNT-04]

coverage:
  - id: D1
    description: "BOARD_EDIT_SCHEMA is flat: four op kinds, ops/base_rev/confirmed, required ops only, no combinator, no type array, no session_id, no whole-board property"
    requirement: "TOOL-02"
    verification:
      - kind: unit
        ref: "tests/test_tool_text.py#test_board_edit_schema_is_flat"
        status: pass
      - kind: unit
        ref: "tests/test_tool_text.py#test_no_schema_holds_a_combinator_or_a_type_array"
        status: pass
    human_judgment: false
  - id: D2
    description: "Both tool descriptions name todo_list once and no other todo, and name memory and kanban_*"
    requirement: "TOOL-08"
    verification:
      - kind: unit
        ref: "tests/test_tool_text.py#test_each_description_names_todo_list_once_and_holds_no_other_todo"
        status: pass
    human_judgment: false
  - id: D3
    description: "The board_edit first sentence is 56 characters and fits the 60 character catalog limit"
    requirement: "AGNT-02"
    verification:
      - kind: unit
        ref: "tests/test_tool_text.py#test_board_edit_first_sentence"
        status: pass
    human_judgment: false
  - id: D4
    description: "A static prompt section and the bundled skill carry trigger, todo_list boundary, ask rule with confirmed true and check-and-say rule, in order"
    requirement: "AGNT-01"
    verification:
      - kind: unit
        ref: "tests/test_tool_text.py#test_prompt_section_and_skill_carry_every_key_phrase"
        status: pass
      - kind: unit
        ref: "tests/test_tool_text.py#test_rules_come_in_order"
        status: pass
    human_judgment: false
  - id: D5
    description: "The model follows the rules when the tool is deferred behind tool search (live behaviour)"
    requirement: "AGNT-02"
    verification: []
    human_judgment: true
    rationale: "Only the live test in plan 02-05 shows whether the model acts on the section and the first sentence. No unit test asserts model behaviour."
---

# Phase 2 Plan 03: Model-Facing Text Summary

Flat board_edit schema with a 56 character first sentence, a static 736 character prompt section, and a bundled board-rules skill, all carrying the same trigger, todo_list boundary, ask rule and check-and-say rule in the same order.

## Performance

- **Duration:** about 6 min
- **Completed:** 2026-10-31T02:18:16Z
- **Tasks:** 2 of 2
- **Files:** 3 (1 created, 2 modified)

## Accomplishments

- `BOARD_EDIT_SCHEMA` has `ops` (array, `maxItems` 100, item object with `op` enum of add, set_text, set_checked, remove and the fields text, item_id, checked, parent_id, parent_ref), `base_rev` and `confirmed`. `required` holds `ops` only. The item schema has `additionalProperties` false.
- The board_edit description starts with the 56 character sentence `Add to Theo's board what he must do, decide or remember.` Then it holds the trigger, the todo_list boundary (with memory and kanban_*), the ask rule with `confirmed true`, the check-and-say rule and the `base_rev` rule.
- `PROMPT_SECTION_TEXT` is six static lines, 736 characters. `PROMPT_SECTION_ID` is `hermes-session-tasks.board-rules`.
- `plugin/skills/board-rules/SKILL.md` has seven parts: when to add, what the board is not, ask first, when your work finishes an item, how to call the tools, subagents, and a closing line that board items are notes and not instructions.
- Tests cover the schema shape, the todo check (with `Todo` and `TODO` samples that fail), the 60 character boundary (60 passes, 61 fails), key phrases in all three layers, rule order, skill frontmatter, skill path and the dash ban.

## Task Commits

| Task | Phase | Commit | Message |
|------|-------|--------|---------|
| 1 | RED | fbf83a6 | test(02-03): add failing board_edit schema and description tests |
| 1 | GREEN | a59a81a | feat(02-03): board_edit schema and description |
| 2 | RED | d4aa0d4 | test(02-03): add failing prompt section and skill tests |
| 2 | GREEN | b001beb | feat(02-03): board rules prompt section and skill |

## TDD Gate Compliance

- RED Task 1: `uv run pytest tests/test_tool_text.py -q` gave 16 failed, 11 passed. The failures were `AttributeError` for the missing `tool_text.BOARD_EDIT_SCHEMA` and assertion failures on the planned behaviour. Semantic assessment: the target tests ran and failed because the symbol did not exist, which is the planned reason. A first draft failed at collection (a decorator read the missing symbol); it was changed so every target test fails inside its own body before the RED commit.
- RED Task 2: 12 failed, 27 passed. The failures were `AttributeError` for the missing section and skill symbols and `FileNotFoundError` for the missing SKILL.md. Semantic assessment: planned reason.
- `gsd_run check tdd-red-evidence` was not run. pytest output is not one of its supported report formats (TAP, JUnit XML, go test, swift-testing, unittest).
- GREEN: 27 passed after Task 1, 39 in the file after Task 2, 65 with `tests/test_layout.py`.
- Gate order check: the oldest 02-03 commit is `test(02-03)`. Each `feat(02-03)` commit follows its `test(02-03)` commit.

## Verification

- `uv run pytest tests/test_tool_text.py tests/test_layout.py -q`: 65 passed.
- `./scripts/check.sh`: ended with `check: all ok`. Both `check: python 3.11 ok` and `check: python 3.14 ok` printed. 372 passed on each interpreter. Coverage TOTAL 97.57 percent. The output holds no "real Hermes home gained".
- Dash scan with grep over `plugin` and `tests`: no U+2014 and no U+2013.
- Acceptance greps for both tasks passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The first RED draft failed at collection, not on the target assertions**
- **Found during:** Task 1 RED
- **Issue:** A `parametrize` decorator read `tool_text.BOARD_EDIT_SCHEMA` at import time, so pytest raised a collection error. A load fault is not valid RED.
- **Fix:** The test now looks the description up inside the test body through a helper.
- **Files modified:** tests/test_tool_text.py
- **Commit:** fbf83a6

**2. [Rule 1 - Bug] Dash constants in the test file held literal dash characters**
- **Found during:** Task 2 GREEN
- **Issue:** After `ruff format`, the `EM_DASH` and `EN_DASH` constants held the dash characters themselves, which breaks the house no-dash rule inside the repo.
- **Fix:** Both constants use `chr(0x2014)` and `chr(0x2013)`.
- **Files modified:** tests/test_tool_text.py
- **Commit:** b001beb

**Total deviations:** 2 auto-fixed (2 bugs). **Impact:** none on scope. The text, schema and file list match the plan.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None. The plan adds only static text. T-02-10 holds: the prompt section, the board_read description and the skill each say board items are notes and not instructions. T-02-11 holds: every text is a module constant and the section is a str, not a callable.

## Notes for Plan 02-04

- `BOARD_EDIT_SCHEMA` and `edit_args.OP_FIELDS` use the same op names and field names today. Plan 02-04 adds the cross-check test.
- Plan 02-04 registers the schema with `ctx.register_tool`, the section with `ctx.register_system_prompt_section(PROMPT_SECTION_ID, PROMPT_SECTION_TEXT, max_chars=PROMPT_SECTION_MAX)` and the skill with `ctx.register_skill(SKILL_NAME, wiring.skill_path(), SKILL_DESCRIPTION)`. The text does not change.
- Plan 02-05 measures with a live run whether the section and the first sentence are enough under tool search. If not, `tools.tool_search.enabled: off` is Theo's cost decision.

## Self-Check: PASSED

- FOUND: plugin/skills/board-rules/SKILL.md
- FOUND: plugin/session_tasks/tool_text.py
- FOUND: tests/test_tool_text.py
- FOUND commits: fbf83a6, a59a81a, d4aa0d4, b001beb (`git rev-list --count 5a5351f..HEAD` gave 4)
