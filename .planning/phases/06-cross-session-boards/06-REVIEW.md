---
phase: 06-cross-session-boards
reviewed: 2026-11-03T02:28:22Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - plugin/dashboard/plugin_api.py
  - plugin/desktop/plugin.js
  - plugin/plugin.yaml
  - plugin/session_tasks/board_api.py
  - plugin/session_tasks/board_tools.py
  - plugin/session_tasks/copy_args.py
  - plugin/session_tasks/copy_plan.py
  - plugin/session_tasks/edit_args.py
  - plugin/session_tasks/lineage.py
  - plugin/session_tasks/model.py
  - plugin/session_tasks/results.py
  - plugin/session_tasks/store.py
  - plugin/session_tasks/titles.py
  - plugin/session_tasks/tool_text.py
  - plugin/session_tasks/wiring.py
  - plugin/skills/board-rules/SKILL.md
  - tests/desktop_pane_harness.mjs
  - tests/fakes.py
  - tests/hermes_contract_snippet.py
  - tests/hermes_dispatch_snippet.py
  - tests/live/cross/cross_live.py
  - tests/pane_rig.py
  - tests/test_api_copy.py
  - tests/test_board_cross.py
  - tests/test_copy_args.py
  - tests/test_copy_plan.py
  - tests/test_live_cross.py
  - tests/test_pane_copy.py
  - tests/test_pane_picker.py
  - tests/test_pane_readonly.py
  - tests/test_store_copy.py
  - tests/test_titles.py
findings:
  critical: 0
  warning: 2
  info: 7
  total: 9
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-11-03T02:28:22Z
**Depth:** standard
**Files Reviewed:** 32
**Status:** issues_found

## Summary

The cross-session code holds the rules it claims. The calling session of every tool comes from the `session_id` keyword only, and the one read of `session_id` from the arguments names a board to read (`copy_args.read_target`). A cross read never marks the board seen. The copy runs in one `BEGIN IMMEDIATE` transaction, the skip rule and the cap are pure functions, and a missing source id writes nothing. The route refuses extra fields and a delegate target. The title lookup never raises, closes its one reader, and sanitises every label. The pane keeps the picked board read only, chains a copy behind earlier writes, and never retries a copy. The Hermes claims were checked against `~/.hermes/hermes-agent`: `dispatch` calls `handler(args, **kwargs)` so a `session_id` argument and the keyword never collide; `get_messages(limit=5)` returns the first five messages in insertion order; `get_session_title` reads the title of the root row.

No blocker was found. The one real defect is in the journal: the `copied` rows share the 100 row cap with the `add` rows, so one large copy evicts its own add rows and the delta note falls back to the pointer line. The live tool `cross_live.py stop` still has no refusal of the real Hermes home, the gap that 05 WR-03 named. The rest is small: a stale docstring, a parsed but unused `base_rev`, a transient label state in the pane, and duplicated text. No em dash or en dash exists in the reviewed files. No external reviewer evidence was supplied. No structural findings were supplied.

## Warnings

### WR-01: the `copied` journal rows evict the `add` rows of the same copy

**File:** `plugin/session_tasks/store.py:185-204` (`_provenance`), `337-338` (the call), `368-369` (`prune_changes`)
**Issue:** A copy of N items writes N `add` rows, then N `copied` rows, all in one batch. `prune_changes` then keeps the newest 100 rows by `seq`. When N is over 50, the oldest `add` rows of this same copy are the first to go. Reproduced with the store: a pane copy of 60 open items onto a seen board leaves 40 `add` rows and 60 `copied` rows. `unseen_changes` then reports `covered = False` (100 rows, oldest rev above the seen rev), and `delta_note` returns the pointer line instead of the 60 `added #n text` lines. The loss is conservative, the agent is still told to call `board_read`, but the note Phase 5 built is gone for the one case where Theo moved the most. Every smaller copy also fills the journal twice as fast, so older Theo changes drop out of the note sooner than Phase 5 planned. `user_touched_ids` is not affected, because the `copied` row carries the item id.
**Fix:** Keep the cap on the rows the note reads, and prune the `copied` rows with their adds:
```python
def prune_changes(conn, root_id, keep):
    sql = (
        f"DELETE FROM {CHANGES} WHERE root_id = ? AND seq NOT IN "
        f"(SELECT seq FROM {CHANGES} WHERE root_id = ? AND op != 'copied' "
        "ORDER BY seq DESC LIMIT ?) AND op != 'copied'"
    )
    conn.execute(sql, (root_id, root_id, keep))
    conn.execute(
        f"DELETE FROM {CHANGES} WHERE root_id = ? AND op = 'copied' AND rev < "
        f"(SELECT COALESCE(MIN(rev), 0) FROM {CHANGES} WHERE root_id = ? AND op != 'copied')",
        (root_id, root_id),
    )
```
Then `journal_span` must count `op != 'copied'` rows too. Add a store test: copy 60 items as user onto a seen board, assert 60 `add` rows remain, `covered` is True and the note holds 60 lines.

### WR-02: `cross_live.py stop` accepts the real Hermes home

**File:** `tests/live/cross/cross_live.py:225-230` (`cmd_stop`), `37-45` (`refuse_real_home`, used by `seed` only)
**Issue:** `cmd_seed` refuses an unset `HERMES_HOME` and `~/.hermes` before any Hermes import. `cmd_stop` has no such check. It passes `--home` straight to `stop_test_gateway` of `tests/live/delta/delta_live.py:323-352`, which only compares the pid file and the process environment to the given home. Phase 5 review WR-03 named that gap, and the function is unchanged. A `stop --home ~/.hermes` on a real gateway that was started with `HERMES_HOME=/home/theo/.hermes` in its environment sends SIGTERM to Theo's gateway and drops every live Desktop connection, the harm the project rules name. The module docstring says "stop stops only a test gateway", which the code does not enforce.
**Fix:** Run the same refusal in `cmd_stop`, against the argument instead of the environment:
```python
def cmd_stop(args):
    home = Path(args.home).expanduser()
    if home.resolve() == (Path.home() / ".hermes").resolve():
        return _fail(f"{home} is the real Hermes home: stop refuses it")
    ...
```
Add a test that calls `main(["stop", "--home", "~/.hermes"])` and expects exit 2 with no pid file read.

## Info

### IN-01: `_cross_read` says "no store write" but a branch id creates a board

**File:** `plugin/session_tasks/board_tools.py:82-87`, `plugin/session_tasks/lineage.py:201-205`
**Issue:** `board_read` with a `session_id` of a branch session that has no board yet runs `resolver.resolve`, and `_branch` calls `fork_copy`, which creates a board and an alias row. A compression tip gets an alias row the same way. `tests/test_board_cross.py:421` tests this as intended, so the behaviour is by design. The docstring on line 83 is wrong, and the D-38 wording "read only" is narrower than what the resolver does.
**Fix:** Say what happens: "No seen mark. The resolver can still give a branch its first copy or alias a compression tip, as any touch does."

### IN-02: `base_rev` on the copy path is parsed and never used

**File:** `plugin/session_tasks/copy_args.py:92-95`, `plugin/session_tasks/board_api.py:181-199`, `plugin/session_tasks/board_tools.py:178`, `plugin/session_tasks/tool_text.py:154-170`
**Issue:** `copy_items` always runs with base rev 0, because a copy is an add (D-40). The route still accepts `base_rev` (D-46) and `board_api.copy` keeps `base` only to pass it to `_stale_reply`, where the message argument overrides the one place that reads it. `copy_args.parse` also validates `base_rev` for the tool, whose schema has no such field, so a stray `base_rev: "x"` from the model fails the call with the `board_edit` error text. Dead data on three layers.
**Fix:** Drop `base_rev` from `CopyArgs` and from `parse`, keep it on `CopyBody` as an accepted and ignored field with a comment that names D-46, and pass a fixed 0 to `_stale_reply`. Or state in the `copy_items` docstring that the route field is accepted for the D-22 shape only.

### IN-03: before the first board reply the picker treats the session id as the root

**File:** `plugin/desktop/plugin.js:1227`, `1196-1201`, `193-208`
**Issue:** `focusedRoot` is the focused session id until `/board` answers. For a compressed session the id is the tip, not the root. If the menu opens in that window, `orderBoards` does not find the own board under `focusedRoot`, lists it under the others, and a pick of it opens the own board read only. The window closes on the first reply, and when the reply fails `/boards` fails too, so the menu shows the failure line. Transient only.
**Fix:** Disable the trigger until `shown !== null`, or pass `focusedRoot: null` to `orderBoards` and skip the others list while it is null.

### IN-04: the system prompt section names two of the four tools

**File:** `plugin/session_tasks/tool_text.py:175`
**Issue:** `PROMPT_SECTION_TEXT` opens with "(tools board_read and board_edit, toolset task-board)". `board_sessions` and `board_copy` are in the tool descriptions and in the skill, and the 06-12 live check passed, so the model finds them. The line is still out of date and the cache-stable text was changed in this phase anyway.
**Fix:** "(tools board_read, board_edit, board_sessions and board_copy, toolset task-board)".

### IN-05: `SESSION_ID_MAX` lives in two files

**File:** `plugin/dashboard/plugin_api.py:22`, `plugin/session_tasks/copy_args.py:15`
**Issue:** The route and the parser each define 256. The dashboard file cannot import the core at module level, which explains the first copy. The second copy can drift from it.
**Fix:** Export the value from `copy_args` and read it in `get_api` time code, or add a layout test that asserts the two constants are equal.

### IN-06: `cross_live.py seed` crashes on a second run and trusts `~/.hermes` as the only real home

**File:** `tests/live/cross/cross_live.py:85-89`, `37-45`
**Issue:** `set_session_title` raises `ValueError` when another session in the same store holds the title (`hermes_state_titles.py:155-163`). A second `seed` with the same title in a reused test home ends in a traceback after `create_session` wrote the row, and exits 1 instead of 2. `refuse_real_home` also compares only to `~/.hermes`; a shell whose real `HERMES_HOME` is elsewhere passes.
**Fix:** Catch `ValueError` around `set_session_title` and return `_fail(str(exc))`. Document the `~/.hermes` assumption in the docstring, as 05 IN-02 asked for the delta tools.

### IN-07: a refused copy shows the "save" notice and keeps the gone board on screen

**File:** `plugin/desktop/plugin.js:956-958`, `972-974`
**Issue:** When the route answers `error: "invalid"` (the picked board was deleted, or the target became a delegate), `runCopy` treats it as `failed`, shows "Could not save that change. Try again.", and reloads the focused board only. The read-only view still shows the old picked items, and a second click gives the same line.
**Fix:** On `reply.error === 'invalid'` call `reloadPicked()` too, and show the route `message` when it is a string, else the failed notice.

## Per-file table

| File | Lines | Result |
|------|-------|--------|
| `plugin/dashboard/plugin_api.py` | 112 | `CopyBody` forbids extra fields; plain `def` handlers; IN-05 |
| `plugin/desktop/plugin.js` | 1342 | Under the 1400 ceiling; hooks in `Pane` only; theme variables only, `--ui-yellow` exists in `styles.css:245`; IN-03, IN-07 |
| `plugin/plugin.yaml` | 14 | Declares the two new tools; matches `wiring.py` |
| `plugin/session_tasks/board_api.py` | 219 | Delegate refused before any write; listener fault kept out of the reply; IN-02 |
| `plugin/session_tasks/board_tools.py` | 199 | Caller from the keyword only; cross read marks nothing; IN-01 |
| `plugin/session_tasks/copy_args.py` | 112 | Bool, float and oversized ids refused; de-duplication keeps order; IN-02, IN-05 |
| `plugin/session_tasks/copy_plan.py` | 140 | Pure; parent before subtask; cut never orphans a subtask; no finding |
| `plugin/session_tasks/edit_args.py` | 209 | Two helpers made public, no logic change |
| `plugin/session_tasks/lineage.py` | 205 | Protocol gains two read methods; no logic change |
| `plugin/session_tasks/model.py` | 231 | `copied` op, `CopyApplied`, two errors; no finding |
| `plugin/session_tasks/results.py` | 184 | `summary_line` ignores `copied`; cross read result names the board; no finding |
| `plugin/session_tasks/store.py` | 373 | One transaction per copy; WR-01 |
| `plugin/session_tasks/titles.py` | 80 | One reader per call, closed in `finally`; every label sanitised; no finding |
| `plugin/session_tasks/tool_text.py` | 198 | Static text; IN-04 |
| `plugin/session_tasks/wiring.py` | 97 | Registers four tools with one `TitleLookup`; no finding |
| `plugin/skills/board-rules/SKILL.md` | 67 | Names the copy rule and the delegate rule; no finding |
| `tests/desktop_pane_harness.mjs` | - | Menu, request and interval stubs; no finding |
| `tests/fakes.py` | - | Fake reader mirrors the six methods; no finding |
| `tests/hermes_contract_snippet.py` | - | Scratch home only; plain SQL message seed is test setup; no finding |
| `tests/hermes_dispatch_snippet.py` | - | Scratch home only; no finding |
| `tests/live/cross/cross_live.py` | 242 | WR-02, IN-06 |
| `tests/pane_rig.py` | - | `TZ=UTC` for stable labels; `/board?` filter correct; no finding |
| `tests/test_api_copy.py` | - | Asserts present; no flaky pattern |
| `tests/test_board_cross.py` | - | Covers the argument `session_id` rule and the branch copy; no flaky pattern |
| `tests/test_copy_args.py` | - | Covers the coerced forms; no finding |
| `tests/test_copy_plan.py` | - | Covers skip, cap and missing id; no finding |
| `tests/test_live_cross.py` | - | Skips without the gateway venv; no finding |
| `tests/test_pane_copy.py` | - | Covers queue order, no retry, focus change; no finding |
| `tests/test_pane_picker.py` | - | Covers order, labels, failures; no finding |
| `tests/test_pane_readonly.py` | - | Covers events, poll and back; no finding |
| `tests/test_store_copy.py` | - | No test for a copy over 50 items (WR-01) |
| `tests/test_titles.py` | - | Covers the chain and the faults; no finding |

---

_Reviewed: 2026-11-03T02:28:22Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
