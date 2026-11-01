---
phase: 02-agent-tools-and-skill
reviewed: 2026-10-31T00:00:00Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - plugin/__init__.py
  - plugin/plugin.yaml
  - plugin/session_tasks/board_tools.py
  - plugin/session_tasks/edit_args.py
  - plugin/session_tasks/guard.py
  - plugin/session_tasks/hooks.py
  - plugin/session_tasks/results.py
  - plugin/session_tasks/tool_text.py
  - plugin/session_tasks/wiring.py
  - plugin/skills/board-rules/SKILL.md
  - tests/fakes.py
  - tests/hermes_dispatch_snippet.py
  - tests/test_board_tools.py
  - tests/test_edit_args.py
  - tests/test_guard.py
  - tests/test_hermes_dispatch.py
  - tests/test_hooks.py
  - tests/test_layout.py
  - tests/test_register.py
  - tests/test_results.py
  - tests/test_tool_text.py
findings:
  critical: 1
  warning: 2
  info: 4
  total: 7
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-10-31
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

Scope: the agent half of the plugin (two tool handlers, the argument parser, the guard rule, both hooks, result text, static tool text, wiring, the skill) and its tests. Baseline: `uv run pytest -q -p no:cacheprovider` gives 426 passed, `ruff check` and `pyright` are clean. I also checked the Hermes dispatch path in `~/.hermes/hermes-agent` (`tools/registry.py` dispatch, `model_tools._pre_dispatch_guards`, `hermes_cli/plugins.py` directive handling). The hook return shape, the handler keyword filtering and `register_system_prompt_section` match the installed Hermes.

The main defect is a hole in the hard guard: an item that Theo wrote loses its reword protection after the agent checks it. Two robustness defects follow: huge integers escape the parser as raw exceptions, and the success summary counts submitted ops instead of real changes. No hardcoded secret, injection path, or `todo_list` access was found. The session id comes only from the handler keyword and the hook keyword. No em dash or en dash appears in the reviewed files.

## Critical Issues

### CR-01: Reword guard is bypassed after the agent checks an item Theo wrote

**File:** `plugin/session_tasks/guard.py:36-40` (rule), `plugin/session_tasks/store.py:131-142` (`_touch` sets `updated_by=batch.actor`)
**Issue:** The guard blocks `set_text` only when `item.updated_by == "user"`. `_touch` overwrites `updated_by` with the actor of every change, and a `set_checked(true)` is never guarded (D-19). The agent is told to check items when its work finishes them (AGNT-04). So this sequence passes with no block and no `confirmed`:
1. Theo adds "Call John" (`updated_by` = user).
2. The agent checks it. The guard returns no reason. `updated_by` becomes `agent`.
3. The agent rewords it. `guarded_reasons` returns `()` because the item is now agent-owned.

I reproduced this against `BoardStore` and `guard.guarded_reasons`: after step 2 `updated_by` is `agent`, and the reword gives an empty reason tuple. `plugin/skills/board-rules/SKILL.md` promises "Any change by Theo makes the item his", but an agent check silently takes it back. D-18 calls this a hard guard for "an item Theo wrote". The tests (`test_hooks.py:70-72`, `test_guard.py`) seed `updated_by` with a user actor directly, so none of them cover an agent change after a user change. Impact: Theo's own wording is replaced with no question. The journal keeps the old text, but only for the last 100 changes, and Theo is not told.
**Fix:** Make the author sticky. Either keep `updated_by == "user"` when the agent only flips `checked` or rewords with a confirmed call, or give the item a separate `user_touched` flag that only the user actor sets. Smallest change in `store._touch`:
```python
updated_by = item.updated_by if batch.actor == "agent" and item.updated_by == "user" else batch.actor
```
Check first that the Phase 3 and 4 pane code does not read `updated_by` as "last writer". If it does, add the new column instead. Add a test: user adds, agent checks, then a `set_text` with no `confirmed` must block.

## Warnings

### WR-01: Very large integers escape the parser as raw exceptions

**File:** `plugin/session_tasks/edit_args.py:44-54` (`_whole`), `plugin/session_tasks/edit_args.py:171-180` (`_base_rev`)
**Issue:** `_whole` has no upper bound. I ran three inputs:
- `item_id: "9" * 5000` makes `int()` raise `ValueError: Exceeds the limit (4300 digits)`. `parse` does not catch it, because `EditArgsError` is the only error it maps.
- `item_id: 10**30` parses, then `store.apply` raises `OverflowError: Python int too large to convert to SQLite INTEGER`. The same happens with `parent_id`.
- `base_rev: 10**30` on an add-only call is accepted with no error.

In the hook, the `ValueError` is caught by the generic `except Exception` and the agent gets "the guard could not check this call. Try again.", which is false advice because a retry fails the same way. In the handler, the `OverflowError` and `ValueError` are not `BoardError`, so Hermes catches them and returns `Tool execution failed: OverflowError: ...`. Neither message names the op index or the rule (D-16).
**Fix:** Bound the value and catch the conversion error:
```python
MAX_INT = 2**63 - 1

def _whole(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        digits = value.strip()
        if not (digits.isascii() and digits.isdigit()) or len(digits) > 19:
            return None
        value = int(digits)
    return value if isinstance(value, int) and 0 <= value <= MAX_INT else None
```
Keep the existing "must be a whole number" error for a rejected value. Add parser tests for `10**30` and a 5000-digit string.

### WR-02: Success summary counts submitted ops, not changes

**File:** `plugin/session_tasks/results.py:78-84` (`summary_line`), `plugin/session_tasks/results.py:94-102`
**Issue:** The summary counts ops by kind. `store._set_checked` and `store._set_text` skip an op that changes nothing, and a remove cascades to subtasks. I ran two cases:
- `[set_checked(1, true), set_checked(1, true)]` returns `"rev 2: checked 2 items"` with one `changed` line.
- `[remove(1)]` on a parent with one subtask returns `"removed 1 item"` with two `changed` lines (`- removed #1`, `- removed #2`).

The agent reads the summary to tell Theo what happened (AGNT-04). It will report two items checked when one was, or one removed when two were. The docstring admits "Counts follow the submitted ops", but D-13 asks for a summary of the change.
**Fix:** Derive the counts from `changed_ids` and the post-write board, or have `BoardStore.apply` return one (kind, id) pair per journaled change. Remove the op-based `Counter`. Add a test with a repeated no-op `set_checked` and with a cascade remove.

## Info

### IN-01: Stale message is wrong when `base_rev` is ahead of the board

**File:** `plugin/session_tasks/results.py:105-110`, `plugin/session_tasks/revision.py` (`is_stale`: `base_rev > pre.rev`)
**Issue:** An agent that invents `base_rev` 50 on a board at rev 3 gets "stale: #1 changed after rev 50". Nothing changed after rev 50. The agent may wait and retry with the same number.
**Fix:** In `stale_result`, when `base_rev > stale.board.rev`, say "base_rev 50 is newer than the board (rev 3). Call board_read and use its rev."

### IN-02: `after_write` listener is never wired

**File:** `plugin/session_tasks/board_tools.py:26-34, 76-82`, `plugin/session_tasks/wiring.py:52`
**Issue:** `register` builds `BoardTools(store, resolver)` with no listener, so `_no_listener`, the `try/except` around it and the "listener fault" logging path never run in production. This is a Phase 3 hook point built early.
**Fix:** Accept it for now, since the tests exercise the branch. Wire it in Phase 3, or remove it if Phase 3 does not need a push from the agent half.

### IN-03: The ask rule has three hand-written copies, and one number is duplicated

**File:** `plugin/session_tasks/tool_text.py:35-42, 114-122, 66`; `plugin/skills/board-rules/SKILL.md`
**Issue:** The ask rule appears in `BOARD_EDIT_DESCRIPTION`, `PROMPT_SECTION_TEXT` and `SKILL.md`. Quick task 261031-lbp already had to edit all three at once. `"maxItems": 100` repeats `edit_args.MAX_OPS` without an import, so the two can drift.
**Fix:** Build the schema `maxItems` from `edit_args.MAX_OPS`. Share one rule string between the description and the prompt section, or add a test that fails when the three texts disagree on the two cases.

### IN-04: Unreachable `board is None` branch in the reword rule

**File:** `plugin/session_tasks/guard.py:37-40`
**Issue:** `hooks._check` loads the board whenever `needs_board` is true, and `needs_board` is true exactly when a `SetText` op exists. So `_reason` never sees `board is None` for a `SetText` through the hook, and the "err toward asking" comment describes a path that cannot run. The guard tests reach it only by passing `None` directly.
**Fix:** Drop the `board is None` clause and make `board` required for `guarded_reasons`, or keep it and say it is a defensive default.

---

_Reviewed: 2026-10-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
