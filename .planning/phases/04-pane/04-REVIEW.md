---
phase: 04-pane
reviewed: 2026-11-01T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - plugin/desktop/plugin.js
  - scripts/install-desktop.ps1
  - tests/desktop_pane_harness.mjs
  - tests/fixtures/harness_probe.js
  - tests/pane_rig.py
  - tests/conftest.py
  - tests/test_desktop_plugin.py
  - tests/test_install_script.py
  - tests/test_pane_add.py
  - tests/test_pane_edit_delete.py
  - tests/test_pane_harness.py
  - tests/test_pane_view.py
  - tests/test_pane_writes.py
  - README.md
findings:
  critical: 1
  warning: 5
  info: 4
  total: 10
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-11-01
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

The pane follows the project rules:
- It has three imports.
- Only `Pane` calls hooks, and every hook runs before the early return.
- It uses `var(--ui-*)` colours only.
- `ctx.setTimeout`, `ctx.setInterval` and `ctx.onEvent` each return a disposer in the SDK doc (`desktop-plugin-sdk.md:192-198`). The effects return them correctly.

The main risk is that the pane keeps board state per session in refs, but item ids are per board. The table `items` has `PRIMARY KEY (root_id, id)` (`schema.py:34`), so id 1 exists on every board. Several callbacks that finish after a focus switch use the current session instead of the session they started on. The write queue also has no guard against one thrown error.

The install script guard is sound against shell injection. Only `..` segments pass it.

## Critical Issues

### CR-01: A failed or stale text edit can reopen on another session's item and overwrite it

**File:** `plugin/desktop/plugin.js:667-678` (also 453-457, 463-467)
**Issue:** `saveEdit` restores the typed text with `changeEdit({ ...open, text })`. The guard is `hasItem(state.board, open.id)`. `state.board` always holds the board of the current focus. The `open` record carries no session id.

Failing sequence:
1. Theo edits item 1 on session A and presses Enter.
2. He switches to session B before the write settles.
3. The write comes back stale or failed.
4. Session B also has an item 1, so `hasItem` is true.
5. The pane opens an edit on B's item 1 with A's text.
6. Blur saves it, because the Input saves on blur (D-31).
7. B's item 1 now holds A's text.

The same session-less shape causes a smaller leak. `saveEdit`, `onCheck` and `onDelete` all call `sendOp`, which reads `current.current.sid` at call time. `sendOp` sets that to the new session in the render phase. A blur that fires between the render and the `[sid]` effect sends A's item id to B's board.

**Fix:** Put the session in the edit record and check it at every use.
```js
changeEdit({ sid: current.current.sid, id: item.id, text: item.text, original: item.text })
// saveEdit: capture the session once, then compare in the callback
const asked = open.sid
if (asked !== state.sid) return          // never write an edit across a focus change
sendOp({ op: 'set_text', item_id: open.id, text }, outcome => {
  if (outcome === 'ok' || state.sid !== asked || state.edit !== null || !hasItem(state.board, open.id)) return
  changeEdit({ ...open, text })
})
```
Give `sendOp` an optional `asked` argument so the caller names the session.

## Warnings

### WR-01: One thrown error in the write queue stops every later write

**File:** `plugin/desktop/plugin.js:580`
**Issue:** The queue line is `queue = queue.then(() => runWrite(...))` with no `.catch`. `runWrite` guards its `try`, but the code after `finally` is not guarded. That code is `showNotice`, `reload` and `onOutcome`. `showNotice` calls `ctx.setTimeout`, which can throw after the plugin is disposed or hot-reloaded.

One throw rejects the queue promise. Every later `.then` is skipped. After that:
- Optimistic rows never leave `pending`.
- `addBusy` and `subBusy` stay true, so the add line stays read-only for good.
- The user sees no error.

**Fix:**
```js
current.current.queue = current.current.queue
  .then(() => runWrite(asked, entry, onOutcome))
  .catch(() => {})
```
Better, also wrap the part after `finally` in its own try/catch.

### WR-02: Focus change leaves busy flags and the load notice behind

**File:** `plugin/desktop/plugin.js:555-568`, `587`, `604`, `635-639`
**Issue:** The `[sid]` effect resets the state values but not their ref copies.
- `current.current.addBusy` and `subBusy` stay true until the old session's write settles. Enter on the new session's add line does nothing until then.
- The `onOutcome` callback of a subtask add on session A runs `delete state.subBusy[parentId]` and `patchSubLine(parentId, ...)` after a switch. Parent ids are per board, so this resets the busy flag of a different line on session B. A second Enter on B can then double-send.
- `loadFailed` is never reset on a focus change. A failed load on A shows "Could not load the board. Retrying." on B until B loads.
- Unsent text in the add line is dropped on a focus change, with no restore.

**Fix:**
- In the `[sid]` effect, set `current.current.addBusy = false` and `current.current.subBusy = {}`, and call `setLoadFailed(false)`.
- Key `subBusy` and `subLines` by `${sid}:${parentId}`, or check `state.sid === asked` before the patch.

### WR-03: The pane changes a ref during render and drops the session rev on every return

**File:** `plugin/desktop/plugin.js:452-457`
**Issue:**
- The render body sets `current.current.sid` and runs `delete current.current.revs[focused]`. React 19 can discard a render without committing it. The ref then holds the new session while the state shows the old one.
- Deleting `revs[A]` when Theo returns from B to A makes the next write use `base_rev: 0`. `postOp` reads `revs[asked] ?? 0`. If Theo presses Enter or clicks a checkbox before the reload lands, the server answers stale. An add, edit or delete is then lost behind a "Board changed" notice. Only a check is retried.
- When `focused` is null, the code runs `delete revs[null]`, a string key `"null"`.

**Fix:** Move the sid and board reset into the `[sid]` effect. Keep `revs` entries, because the rev only grows, and let `reload` set them. `reload` already drops lower revs. Do not delete a rev.

### WR-04: A stale or failed text save can silently drop the typed text

**File:** `plugin/desktop/plugin.js:675`
**Issue:** The guard `state.edit !== null` returns without restoring the text when Theo has opened another edit meanwhile. D-34 says an edit keeps the typed text after a stale reply. Here the text is gone and the only sign is the "Board changed" notice. The optimistic text also vanishes with no trace.

**Fix:** Hold the failed text in a small map by item id and show it when that item next opens for edit. At minimum, keep the text in the notice flow, not just a count.

### WR-05: `isMismatch` crashes the render when `/meta` returns nothing

**File:** `plugin/desktop/plugin.js:200-203`, `548`
**Issue:** `setMeta(body)` stores whatever `ctx.rest` resolves with. The guard is `meta === null || meta.ok !== true`. A body of `undefined` (an empty reply) passes the first check and throws `TypeError` inside `noticeText` during render. That blanks the whole pane.

**Fix:**
```js
if (!meta || meta.ok !== true) return false
```
Or store `setMeta(body ?? null)`.

## Info

### IN-01: `-RemotePath` accepts `..` segments and `//`

**File:** `scripts/install-desktop.ps1:125-131`
**Issue:** The regex `^/[A-Za-z0-9._/-]+\z` blocks every shell metacharacter, a leading dash and a relative path. That is correct for the legacy scp shell. It allows `/home/theo/../../etc/x`. The `export default` check limits the damage, and only the person at the keyboard supplies the value. The tests (`test_install_script.py:260-272`) cover `;`, space, `$()`, a leading dash and a relative path. They do not cover `..`, `//` or a trailing newline.

**Fix:** Add `if ($Path -match '(^|/)\.\.(/|$)') { return $false }` and a test for `..` and for `"/tmp/a\n"`.

### IN-02: The harness never fires the poll interval

**File:** `tests/desktop_pane_harness.mjs:271-274`
**Issue:** The `ctx.setInterval` stub records the ms value and drops `fn`. `test_poll_interval` and `test_no_poll_without_a_focused_session` only read that list. The poll path that calls `reload` is never run. A broken interval callback would pass every test. Reload is covered only through the event step. The `[sid]` effect cleanup is also never called on a focus change with a live interval.

**Fix:** Store `fn`, add a `{"tick": true}` step that runs it, and add a test that a tick during a write is dropped and a tick after a focus change loads the new board.

### IN-03: Two tests pin source text, not behaviour

**File:** `tests/test_desktop_plugin.py:415-423`
**Issue:** `test_checkbox_border_is_visible` and `test_rows_without_subtasks_start_at_the_checkbox` assert that exact source strings exist, including line breaks and indent. A harmless reformat fails them. A dead constant still passes them.

**Fix:** Assert in the harness output: the checkbox record carries the class, and a row without children has no chevron node.

### IN-04: `Pane` is one function of about 350 lines

**File:** `plugin/desktop/plugin.js:414-768`
**Issue:** Hooks must stay in `Pane`, which is why the logic is there. The write queue, the edit state and the sub-line state share it, and WR-01 to WR-04 sit in those closures. The one-file rule limits the options.

**Fix:** Move the write queue (`sendOp`, `runWrite`, `postOp`, `take`) into a plain factory function in the same file. Give it the `ctx`, the ref and the setters as arguments, so it can be tested by itself.

---

_Reviewed: 2026-11-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
