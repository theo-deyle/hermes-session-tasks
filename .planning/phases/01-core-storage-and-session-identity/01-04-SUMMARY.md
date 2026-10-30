---
phase: 01-core-storage-and-session-identity
plan: 04
subsystem: markdown
tags: [markdown, parser, renderer, escape-rule, round-trip, import-plan]

requires:
  - phase: 01-02
    provides: model.py (sanitize_text, AddItem, MAX_TEXT_CHARS), markdown.render without the escape rule
provides:
  - markdown.render with the one-backslash escape for text that starts with #<digits>
  - markdown.parse into ParseResult and ParsedItem (checklist items, plain bullets, id hint, nesting, counts)
  - markdown.plan_import into ImportPlan (AddItem ops with parent_ref, overflow count)
affects: [01-06, phase-2, phase-4]

plan_head_before: d6166558e3aaaab8021c154d644ae915c3a27ce7
plan_head_after: 9c0d10a82f7e4ec3ac77ee67c80facc5477708f1

actuals:
  tokens: 11000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "parse splits into a line matcher, a text cleaner and a tree builder; a skipped line stays on the nesting stack as a placeholder"
    - "A seeded random.Random(1234) generator builds boards directly from sanitised texts; no extra package"

key-files:
  created:
    - tests/test_markdown.py
    - tests/test_markdown_roundtrip.py
  modified:
    - plugin/session_tasks/markdown.py

key-decisions:
  - "moved counts only lines that import. A line that is also skipped is counted once, in skipped_empty or too_long."
  - "A line under a skipped or too-long top-level entry becomes top-level itself, and a skipped entry never takes a child."
  - "The id token strips at any length. hint_id is an int only for a run of 18 digits or fewer, else None."

requirements-completed: [STOR-08]

coverage:
  - id: D1
    description: "A pasted checklist parses with D-02, D-05, D-08, D-09 and the D-10 line-length skip, and every moved or skipped line is counted"
    requirement: STOR-08
    verification:
      - kind: unit
        ref: "tests/test_markdown.py (24 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "500 seeded random two-level boards round trip through render and parse with ids on and off, and stored text that starts with #<digits>, backslashes, [x] or - survives"
    requirement: STOR-08
    verification:
      - kind: unit
        ref: "tests/test_markdown_roundtrip.py#test_500_random_boards_round_trip_with_ids_on"
        status: pass
      - kind: unit
        ref: "tests/test_markdown_roundtrip.py#test_500_random_boards_round_trip_with_ids_off"
        status: pass
      - kind: unit
        ref: "tests/test_markdown_roundtrip.py#test_stored_text_survives_a_round_trip_unchanged"
        status: pass
    human_judgment: false
  - id: D3
    description: "plan_import stops at the free capacity, reports the overflow, never orphans a subtask and rejects a negative capacity"
    requirement: STOR-08
    verification:
      - kind: unit
        ref: "tests/test_markdown_roundtrip.py (plan_import tests)"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-10-30
status: complete
---

# Phase 1 Plan 04: Markdown parser, escape rule and import plan Summary

**The board now converts to a markdown checklist and back with no loss: render escapes text that starts with `#<digits>`, parse reads checklists and plain bullets with every moved, empty or over-long line counted, and plan_import stops at the free item capacity.**

## Performance

- **Duration:** 8 min
- **Completed:** 2026-10-30T23:35Z
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `render` puts one backslash before text that matches `^\\*#[0-9]+(\s|$)`. `parse` removes exactly one backslash from text of the same shape. The agent view and the clipboard view both read back exactly.
- `parse` handles CRLF, tabs (4 columns), `-`, `*` and `+` bullets, `[ ]`, `[x]` and `[X]` boxes, thematic breaks, and a box without a following space (`- [ ]foo` is plain text).
- A depth 2 or deeper line becomes a subtask of the nearest top-level item and counts in `moved`. Empty lines, including `- [ ]`, `- [x]`, `- [X]` and `- `, count in `skipped_empty`. A line over 500 code points counts in `too_long`, and the next line still imports.
- `plan_import` walks the tree in display order, links subtasks with `parent_ref`, and counts every item that does not fit in `overflow`.
- A mutation check removed the escape from `render`. The three round trip tests failed at once, so the tests guard the rule.

## Task Commits

1. **Task 1 RED** - `7ce8f4a` (test): 24 fixed-case tests. The run failed at collection (`ImportError: cannot import name 'ParsedItem'`).
2. **Task 1 GREEN** - `32ec661` (feat): `markdown.py` with escape rule, parser and `plan_import`. 59 passed with the tracer and layout tests.
3. **Task 2 tests** - `9c0d10a` (test): seeded round trip and import planning tests, 12 tests.

**Plan metadata:** the docs commit that holds this file, STATE.md, ROADMAP.md and REQUIREMENTS.md.

## Test Results

- `uv run pytest tests/test_markdown.py -q`: 24 passed (floor 17).
- `uv run pytest tests/test_markdown_roundtrip.py -q`: 12 passed (floor 9).
- `uv run ruff check`, `ruff format --check` and `pyright` on the three plan files: clean.
- `./scripts/check.sh`: 138 passed on each interpreter, `check: python 3.11 ok`, `check: python 3.14 ok`, `check: all ok`.

## Decisions Made

- `moved` counts a line only when it imports. A deep line that is also empty counts once, in `skipped_empty`, so no line counts twice.
- A line below a skipped or too-long top-level entry becomes top-level itself. The skipped parent counts in `skipped_empty` or `too_long`, so the accounting stays complete.
- `plan_import` cuts at the item level. A top-level item that does not fit takes its subtasks into `overflow` with it.

## Deviations from Plan

**1. [Process] plan_import landed with the Task 1 commit**
- **Issue:** `markdown.py` was written once, with `plan_import` and `ImportPlan` included, and the Task 1 commit holds it. The Task 2 commit holds only the tests, which passed at once. There is no separate RED run for Task 2.
- **Impact:** none on behavior. The mutation check above shows the round trip tests can fail.

**Total deviations:** 0 auto-fixed, 1 process note. **Impact:** none.

The commit trailer uses `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, the attribution line from the harness, as plans 01-01 to 01-03 did. The dispatch prompt named `Claude Fable 5.1`. This is a message trailer only.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path or file access. T-01-11 (one pass, depth clamp, line skip, capacity stop), T-01-12 (escape rule), T-01-20 (sanitize_text on parsed text) are implemented and tested. T-01-SC: no new package.

## Next Phase Readiness

- Plan 01-06 can wire `plan_import(parse(text), MAX_ITEMS - current_count)` to `BoardStore.apply` and prove the round trip through the store.
- Phase 2 renders the agent view with `render(board, include_ids=True)`. Phase 4 copies the clipboard view with `include_ids=False`.

## Self-Check: PASSED

- Created files exist: tests/test_markdown.py, tests/test_markdown_roundtrip.py. Modified: plugin/session_tasks/markdown.py.
- Commits found in HEAD history: 7ce8f4a, 32ec661, 9c0d10a.
- Acceptance greps exit 0: `def parse`, `class ParseResult`, `class ParsedItem`, `def plan_import`, `class ImportPlan`, `random.Random(1234)`.
- `./scripts/check.sh` ended with `check: all ok`.

---
*Phase: 01-core-storage-and-session-identity*
*Completed: 2026-10-30*
