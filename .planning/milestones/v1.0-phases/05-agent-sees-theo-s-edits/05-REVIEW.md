---
phase: 05-agent-sees-theo-s-edits
reviewed: 2026-11-02T00:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - plugin/plugin.yaml
  - plugin/session_tasks/aliases.py
  - plugin/session_tasks/board_tools.py
  - plugin/session_tasks/delta.py
  - plugin/session_tasks/hooks.py
  - plugin/session_tasks/rows.py
  - plugin/session_tasks/store.py
  - plugin/session_tasks/tool_text.py
  - plugin/session_tasks/wiring.py
  - tests/hermes_dispatch_snippet.py
  - tests/hermes_session_delete_snippet.py
  - tests/hermes_snippet_setup.py
  - tests/hermes_thirty_turn_snippet.py
  - tests/live/delta/delta_live.py
  - tests/live/delta/make_home.py
  - tests/live/delta/theo_edit.py
  - tests/test_board_tools.py
  - tests/test_delta.py
  - tests/test_hermes_dispatch.py
  - tests/test_hermes_session_delete.py
  - tests/test_hermes_thirty_turn.py
  - tests/test_live_delta.py
  - tests/test_pre_llm_hook.py
  - tests/test_register.py
  - tests/test_session_delete.py
  - tests/test_store_seen.py
  - tests/test_tool_text.py
findings:
  critical: 0
  warning: 6
  info: 4
  total: 10
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-11-02
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

The plugin code is sound. The note fence in `delta.py` escapes every `<`, so no item text can open or close the tag. The seen mark never moves down, and an agent write advances it only when it equals the old board rev. The journal gap rule is conservative in the right direction. Both new hooks catch `Exception` and return None or nothing. The delete path matches exact root ids only and an alias match removes the alias row alone.

No blocker was found. The weak points are in the delete reason filter, the live test tooling (secret check, real gateway guard, fault detection), and one ordering choice in `pre_llm_call`. Every claim below was checked against the source, and the Hermes behaviour claims were checked against `~/.hermes/hermes-agent`. No em dash or en dash exists in the reviewed files. No external reviewer evidence was supplied. No structural findings were supplied.

## Warnings

### WR-01: `on_session_delete` deletes the board for every reason except "archive"

**File:** `plugin/session_tasks/hooks.py:140`
**Issue:** The filter is a deny list: only `reason == "archive"` keeps the board. Hermes emits more reasons than delete. `hermes_state_profile_repair.py:293` (`delete_moved_session`) emits `reason="profile_repair"` after it MOVES a session into another profile store. The session still exists, but the plugin deletes its board. The other reasons seen in the checkout are `delete`, `empty_sweep`, `ghost_prune` and `prune`, which are real deletes. A destructive action should use an allow list, so a future non-destructive reason (a restore, a move) cannot remove a board. The board is also not reachable from the target profile, because its plugin data dir differs. So the loss is a stranded board, not a live one, which is why this stays a warning.
**Fix:**
```python
DELETE_REASONS = frozenset({"delete", "empty_sweep", "ghost_prune", "prune"})
...
if not isinstance(reason, str) or reason not in DELETE_REASONS:
    return
```
Add a parametrised test with `profile_repair` and an unknown reason, both expecting no removal.

### WR-02: `make_home.py` secret check misses a list of secrets and writes it to the test home

**File:** `tests/live/delta/make_home.py:59-69` (called at 163-164)
**Issue:** `_walk` refuses only a string value that sits directly under a secret-looking key. A list under such a key is walked element by element, and a bare string element has no key, so it passes. Reproduced with the module: `{'agent': {'api_keys': ['sk-abc']}}` and `{'agent': {'tokens': {'a': 'x'}}}` both pass, and `{'model': {'base_url': 'https://u:p@h/'}}` passes. `test_home_config` then writes those values into `<out>/config.yaml`. The T-05-25 mitigation says the tool never copies a secret. The guard also gives false refusals, for example `passthrough_mode` matches `pass`.
**Fix:** Treat any non-empty scalar, list or mapping under a secret-named key as a refusal, and scan string values for a credential in a URL:
```python
if SECRET_NAME.search(str(key)) and value not in (None, "", [], {}, False, 0):
    raise Refused(f"a kept key looks like a secret: {where}")
...
if isinstance(node, str) and URL_CREDENTIALS.search(node):
    raise Refused(f"a kept value holds credentials in a URL: {path}")
```
Anchor the name regex on word edges (`(^|_)(key|token|secret|password|auth|credential|bearer)(s)?(_|$)`) to stop the `pass` false positive. Add tests for the list and nested cases.

### WR-03: `delta_live.py arms` accepts the real home, and the stop guard then signals the real gateway

**File:** `tests/live/delta/delta_live.py:323-352` (stop), `590-600` (`cmd_arms`)
**Issue:** The docstring says the stop "never signals the real gateway". The guard only checks that `gateway.pid` and the process environment name the home that was passed in. If `--plugin-home` or `--bare-home` is `~/.hermes` (a typo, or `$HERMES_HOME` expanded by the shell), both checks pass, the arms run 90 turns and `theo_edit.py` writes into the real boards, and the `finally` block sends SIGTERM to Theo's real gateway. That drops every live Desktop connection, the exact harm the project rules warn about. `make_home.py` has a real-home refusal; `cmd_arms` has none.
**Fix:** In `cmd_arms` and `stop_test_gateway`, refuse when a home equals `DEFAULT_HOME.resolve()` or `$HERMES_HOME` of the calling shell, or when its `config.yaml` or marker lacks a `make_home` stamp. Return `refused` and exit 2 before any run. Add a test with the real home as the argument.

### WR-04: the broken-run detector looks for a log line that nothing prints

**File:** `tests/live/delta/delta_live.py:59, 510-511`
**Issue:** `HOOK_FAULT = "pre_llm_call hook failed"` appears nowhere in the Hermes checkout. Hermes logs a raised callback as `... callback <name> raised: ...` (`plugins_dispatch.py:317`). The plugin's own hook catches its fault and logs `board turn context failed` (`hooks.py:115`). So neither text matches, a faulted hook goes undetected, and the arms then read as a measured fail (exit 1) instead of a broken run (exit 2). The 05-05 and 05-07 summaries cite "no `pre_llm_call hook failed` line" as evidence. That evidence is empty.
**Fix:** Match the real texts: `board turn context failed`, and the Hermes `callback .* raised` pattern for `pre_llm_call`. Add a test that feeds each text to `run_turn`.

### WR-05: `pre_llm_call` marks the board seen before Hermes takes the note

**File:** `plugin/session_tasks/hooks.py:111-113`
**Issue:** `mark_seen` runs before the note returns to Hermes. Hermes runs this hook under a 30 second abandon timeout (`plugins_dispatch.py:162`), and a turn can still fail before the API call. In either case the mark is durable and the note is lost, and the pointer line never comes back, because the board then counts as seen. Theo's edit stays invisible to the agent until the agent calls `board_read` by chance. The window is small, but the loss is silent.
**Fix:** Mark the previous rev at the start of the next hook call, or mark only when the same session shows the note in its history. If that is too heavy, state the accepted loss in the hook docstring and in `05-CONTEXT.md`.

### WR-06: an exception in the stop path skips the second gateway and hides the report

**File:** `tests/live/delta/delta_live.py:346`, `597-600`
**Issue:** `os.kill` is not guarded. If the process exits between `_alive` (line 342) and the kill, `ProcessLookupError` propagates out of `stop_test_gateway`. In `cmd_arms` the `finally` block calls the plugin home first, so the bare gateway is then never stopped, and the exception replaces the run result.
**Fix:**
```python
try:
    os.kill(pid, signal.SIGTERM)
except ProcessLookupError:
    return "not running"
```
Also stop each home in its own `try`, so one failure cannot skip the other.

## Info

### IN-01: `delete_aliases` binds up to 1000 parameters per statement

**File:** `plugin/session_tasks/aliases.py:27-30`, `plugin/session_tasks/store.py:38`
**Issue:** `SQL_IN_CHUNK = 500` and the alias SQL uses the chunk twice, so one statement carries 1000 variables. SQLite before 3.32 limits this to 999. The gateway links 3.53.1, so this does not fail today, but the chunk size is sized for `rows.delete_boards` only.
**Fix:** Use a chunk of 400, or document the 3.32 floor next to `SQL_IN_CHUNK`.

### IN-02: scripts that write to `HERMES_HOME` never check it is a test home

**File:** `tests/hermes_snippet_setup.py:25-26`, `tests/hermes_dispatch_snippet.py:26-27`, `tests/live/delta/theo_edit.py:54-70`
**Issue:** `link_and_enable` overwrites `config.yaml` in whatever home the caller names. `theo_edit.py` writes to the active home, and the real home when `HERMES_HOME` is unset. The test callers always set a temporary home, so this is a latent risk only.
**Fix:** Exit 2 in each script when `HERMES_HOME` is unset or equals `~/.hermes`.

### IN-03: `hermes_dispatch_snippet.py` repeats the helpers of `hermes_snippet_setup.py`

**File:** `tests/hermes_dispatch_snippet.py:23-27, 38-47`
**Issue:** The file keeps its own `link_and_enable` and its own stub of `tui_gateway.server`. The two newer snippets import the shared module. The copies can drift.
**Fix:** Import `link_and_enable` and `stub_gateway_server` from `hermes_snippet_setup`.

### IN-04: `arms --runs` takes any integer

**File:** `tests/live/delta/delta_live.py:661`, `566-570`
**Issue:** `--runs 0` leaves `sessions` empty and the report step raises `KeyError`. A value below 25 fails the edit-run check as a measured fail, not as a usage error.
**Fix:** Reject `--runs` below `max(EDIT_RUNS)` with exit 2 before the first model call.

---

_Reviewed: 2026-11-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
