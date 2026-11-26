---
phase: 03-rest-router-and-client-install-spike
reviewed: 2026-11-02T00:00:00Z
depth: standard
files_reviewed: 39
files_reviewed_list:
  - README.md
  - plugin/dashboard/manifest.json
  - plugin/dashboard/plugin_api.py
  - plugin/desktop/plugin.js
  - plugin/plugin.yaml
  - plugin/session_tasks/board_api.py
  - plugin/session_tasks/board_json.py
  - plugin/session_tasks/board_tools.py
  - plugin/session_tasks/events.py
  - plugin/session_tasks/hooks.py
  - plugin/session_tasks/results.py
  - plugin/session_tasks/rows.py
  - plugin/session_tasks/store.py
  - plugin/session_tasks/tool_text.py
  - plugin/session_tasks/version.py
  - plugin/session_tasks/wiring.py
  - pyproject.toml
  - scripts/install-desktop.ps1
  - tests/api_client.py
  - tests/desktop_pane_harness.mjs
  - tests/hermes_dispatch_snippet.py
  - tests/live/own_job/analyze.py
  - tests/live/own_job/job.txt
  - tests/live/own_job/run.sh
  - tests/rest_relay.py
  - tests/test_api.py
  - tests/test_api_load.py
  - tests/test_board_tools.py
  - tests/test_desktop_plugin.py
  - tests/test_events.py
  - tests/test_hermes_dispatch.py
  - tests/test_install_script.py
  - tests/test_layout.py
  - tests/test_own_job_analyze.py
  - tests/test_pre_llm_hook.py
  - tests/test_register.py
  - tests/test_store_list.py
  - tests/test_tool_text.py
  - tests/test_version.py
findings:
  critical: 0
  warning: 3
  info: 8
  total: 11
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-11-02
**Depth:** standard
**Files Reviewed:** 39
**Status:** issues_found

## Summary

The code was reviewed as it stands at HEAD. The diff base is `58b44d8` (the parent of `0d7f38e`). Phase 4 rewrote `plugin/desktop/plugin.js` and Phase 5 changed `hooks.py`, `store.py`, `rows.py` and `board_tools.py`. Each finding names the phase that introduced it.

The Python route layer is sound. `plugin_api.py` holds no relative import and loads the core by path under a fixed key. Every handler is a plain `def`. All SQL is parameterised, and the only f-string SQL pieces are module constants. The dashboard host puts `/api/plugins/` behind its auth middleware, so `GET /boards` and `POST /board/edit` are not open to the network (checked in `hermes_cli/web_server.py:444-458`). The pane renders item text as React children and builds the board URL with `encodeURIComponent`, so no XSS path exists. `plugin.js` holds no hex or `rgb()` colour. The install script validates both the host name and the remote path before it calls `scp`. No em dash or en dash exists in the reviewed files. No external reviewer evidence and no structural findings were supplied.

No blocker was found. The three warnings are a route that can answer with a bare 500 although its contract says it never raises, and a pane rule that can freeze the board view silently until Desktop restarts. The info items are small duplication and robustness points.

## Warnings

### WR-01: A deeply nested `ops` string makes `POST /board/edit` answer 500 (introduced by 03-02)

**File:** `plugin/session_tasks/edit_args.py:136` and `plugin/session_tasks/edit_args.py:168`, reached from `plugin/session_tasks/board_api.py:124`
**Issue:** `_as_object` and `_op_list` call `json.loads` and catch only `ValueError`. Python raises `RecursionError` for a string such as `"[" * 100000`, and `RecursionError` is a `RuntimeError`, not a `ValueError`. I ran `edit_args.parse({"ops": ["[" * 100000], "base_rev": 0})` in `.venv` and it raised `RecursionError`. The route accepts `ops: list[Any]`, so a string element reaches this code. `BoardApi.edit` catches only `BoardError`, so the call ends in an unhandled 500. The module docstring of `board_api.py` says "a request fault never raises". The tool path has the same hole: Hermes catches it, and the `pre_tool_call` guard turns it into a block, so only the route shows a visible fault.
**Fix:**
```python
# edit_args.py, both json.loads sites
except (ValueError, RecursionError):
    raise EditArgsError(OPS_NOT_LIST) from None   # and "an operation must be an object" in _as_object
```

### WR-02: Resolver and store faults other than `InvalidSession` escape the route as a bare 500 (introduced by 03-02)

**File:** `plugin/session_tasks/board_api.py:77-84`, `plugin/session_tasks/board_api.py:91`, `plugin/session_tasks/board_api.py:127`
**Issue:** `_resolve` catches `InvalidSession` only. `SessionResolver.resolve` can also raise `ImportError` (the lazy `from hermes_state import SessionDB` in `session_reader.py` when the route runs in a process without that module), `sqlite3.DatabaseError` from `state.db` (only `OperationalError` is caught in `lineage._Walk.reader`), and `schema.SchemaTooNew`. `get_board`, `list_boards` and `store.apply` can raise `OperationalError: database is locked` after the 5 second busy timeout. None of these becomes a reply. FastAPI answers with a plain-text "Internal Server Error", and nothing is logged by the plugin. The pane copes (it shows "Could not load the board. Retrying."), but the contract in the module docstring is false, and the pane cannot tell a locked file from a schema mismatch.
**Fix:** Add one guard in the router that logs the fault and returns the same envelope the other errors use.
```python
def _fault(exc: Exception) -> JSONResponse:
    log.exception("board route failed")
    return JSONResponse({"ok": False, "error": "internal", "message": "board unavailable"}, status_code=500)
```
Wrap each handler body in `try/except Exception`, or register one `app.exception_handler`-style wrapper in `plugin_api.py` (a router cannot hold an exception handler, so a small decorator is the simplest form).

### WR-03: The pane drops every reload when a board comes back with a lower rev (introduced by 03-06, kept by Phase 4)

**File:** `plugin/desktop/plugin.js:484` (inside `reload`, lines 475-491)
**Issue:** `reload` discards a reply when `body.rev < (state.revs[asked] ?? 0)`. The rule assumes the rev of a board only grows. A board can be deleted and then written again under the same session id: `BoardStore.delete_boards` removes the row, the next write recreates it at rev 1, and plan 03-12 deleted six test boards while their sessions still existed. After that, the pane keeps `revs[asked]` at the old higher value. Every poll and every `board.updated` event is dropped without a notice, so the pane shows the old board until Desktop restarts. A write sends the old higher `base_rev`, the backend answers stale (`base_rev > pre.rev`), and the stale reply carries the low rev, which `take` accepts. The pane therefore heals only through a write, and the user sees stale data in the meantime.
**Fix:** Drop a reply for the one reason the comment gives, a write that finished after the request started. Use an epoch counter, and remove the rev comparison.
```js
// state.writeEpoch += 1 in runWrite's finally block
const startedAt = state.writeEpoch
...then(body => {
  if (state.sid !== asked || state.inFlight > 0 || state.writeEpoch !== startedAt) return
  take(asked, body)
```
Also keep a request counter so a late reply from an older reload cannot overwrite a newer one (the rev rule covered that case today).

## Info

### IN-01: `GET /board` writes to the data file on a polled route (introduced by 03-02)

**File:** `plugin/session_tasks/board_api.py:86-99` through `plugin/session_tasks/lineage.py:190-199`
**Issue:** `read` calls `resolver.resolve`, which can insert an alias row (`_compression`) or copy a parent board (`fork_copy` for a branch). The pane polls this route every 6 seconds, and each write takes `BEGIN IMMEDIATE`, so a poll can wait on the write lock. The behaviour is by design ("a branch gets a copy on its first touch"), and the copy runs once. The point is only that a GET carries this side effect.
**Fix:** Keep the design. Add one sentence to the route docstring that GET can create an alias row or a branch copy.

### IN-02: `GET /boards` has no caller (introduced by 03-02)

**File:** `plugin/dashboard/plugin_api.py:80-83`, `plugin/session_tasks/board_api.py:101-112`
**Issue:** The pane never calls `/boards` (a grep of `plugin/` finds no use). Only `tests/test_api.py` and `tests/test_store_list.py` exercise it. It returns every board root id, which is more data than the current pane needs.
**Fix:** Keep it only if a later phase uses it. Otherwise remove the route, `list_boards`, `list_board_summaries` and their tests.

### IN-03: `_no_listener` is defined twice (introduced by 03-05)

**File:** `plugin/session_tasks/board_api.py:67` and `plugin/session_tasks/board_tools.py:27`
**Issue:** Two identical no-op listeners. `events.py` already owns the `WriteListener` type.
**Fix:** Define `NO_LISTENER` once in `events.py` and import it in both modules.

### IN-04: The version regex keeps quotes (introduced by 03-04)

**File:** `plugin/session_tasks/version.py:19`
**Issue:** `^version:\s*(\S+)\s*$` returns `"0.1.0"` with the quotes if `plugin.yaml` ever quotes the value, which YAML allows. The pane would then show a false "Version mismatch" banner on every start.
**Fix:** Strip one pair of matching quotes, `found.group(1).strip("'\"")`, and add a test for a quoted value.

### IN-05: The install script treats `-HermesHome` and the env home differently (introduced by 03-03)

**File:** `scripts/install-desktop.ps1:93-98` and `scripts/install-desktop.ps1:38`
**Issue:** `Resolve-HermesHome` maps a `.../profiles/<name>` home to the parent through `Get-HomeRoot`. The `-HermesHome` branch of `Get-DesktopHome` returns the value raw, so the same path gives two slots depending on how it is passed. The default `-RemotePath` also bakes in the devpc user path `/home/theo/...`; a second developer must always pass `-RemotePath`.
**Fix:** Call `Get-HomeRoot $HermesHome` in the override branch, or state in the help text that the override is used as given. Move the default path to the README if more than one user will run the script.

### IN-06: `analyze.py` builds a SQLite URI from an unescaped path (introduced by 03-01)

**File:** `tests/live/own_job/analyze.py:158`
**Issue:** `f"file:{db_path}?mode=ro"` breaks when the path holds `?`, `#` or `%`, and it reads the wrong file on some Windows paths. The harness runs only on devpc today, so the risk is small.
**Fix:** `sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)`.

### IN-07: Two tests prove less than they claim (introduced by 03-04 and 03-05)

**File:** `tests/test_version.py:20-30`, `tests/test_events.py:150`, `tests/test_hermes_dispatch.py:29`
**Issue:** `test_backend_version_matches_the_manifest` compares `read_backend_version` with a helper that uses the same regex on the same file, so a regex fault passes both sides (the `0.1.0` constant in `test_meta_route_returns_both_versions` is the only independent check). The two gateway-venv tests call `pytest.skip` at run time when the venv Python is missing. A machine without the gateway reports green and skips the only checks of the real Hermes dispatch. The `hermes` marker in `pyproject.toml` exists for this case.
**Fix:** Parse `plugin.yaml` with a different method in the test (a literal expected value is enough). Mark the gateway tests `@pytest.mark.hermes` so a skipped run is visible in the report.

### IN-08: The pane counts UTF-16 units, the backend counts code points (introduced by 03-06)

**File:** `plugin/desktop/plugin.js:42` and `plugin/desktop/plugin.js:380`
**Issue:** `maxLength: 500` limits UTF-16 units, while `clean_text` limits Unicode code points. A line of emoji stops at 250 characters in the pane, which the backend would accept up to 500. The backend also strips format characters, so the pane count and the stored count can differ in both directions.
**Fix:** Leave the limit, because the backend is the authority, or enforce the limit in `onChange` with `[...value].length`.

---

_Reviewed: 2026-11-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
