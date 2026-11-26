# Phase 4: Pane - Pattern Map

**Mapped:** 2026-11-01
**Files analyzed:** 4
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `plugin/desktop/plugin.js` | component (pane) | request-response + event-driven | `plugin/desktop/plugin.js` (phase 3 test pane, tracked) | exact |
| `tests/desktop_pane_harness.mjs` | test harness | transform (VM render walk) | itself (phase 3) | exact |
| `tests/test_desktop_plugin.py` | test | request-response | itself (phase 3) | exact |
| `tests/rest_relay.py` | test utility | request-response | itself | likely no change |

Note: `~/.hermes/plugins/hermes-memory-ui/desktop/plugin.js` is outside this repo. Use it for style only. Do not name it as a tracked path in plans.

## Pattern Assignments

### `plugin/desktop/plugin.js` (component, request-response + event-driven)

**Analog:** the current `plugin/desktop/plugin.js` (196 lines). Keep these pieces, replace the body.

**Imports** (lines 7-9). Add the new SDK names to the first line. Nothing else may be imported.
```js
import { Button, host, useValue } from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'
```
New SDK names to add: `Checkbox, Input, ScrollArea, ConfirmDialog, CopyButton, EmptyState, Tip, icons, cn`.

**Focus read and ref for long-lived callbacks** (lines 75-84). Copy as is. The listener and interval read `current.current`, not render closures.
```js
const sid = useValue(host.state.focusedStoredSessionId)
const current = useRef({ sid: null, root: null })
current.current.sid = sid || null
current.current.root = reply && reply.ok === true ? reply.root_id : null
```

**Reload with stale-focus guard** (lines 86-95). Keep. Phase 4 sets the board from `body` only when `current.current.sid === asked`.
```js
function reload() {
  const asked = current.current.sid
  if (!asked) return Promise.resolve()
  return ctx.rest(boardPath(asked)).then(body => {
    if (current.current.sid === asked) setReply(body)
  }).catch(() => {})
}
```

**Poll plus event** (lines 108-129). Keep both. `ctx.setInterval` returns the cleanup. `ctx.onEvent` returns the unsubscribe. Event payload fields: `session_id`, `rev`, `actor`, `root_id`. POLL_MS = 6000 already fits 5 to 10 s.
```js
useEffect(() => { if (!sid) { setReply(null); return undefined } reload(); return ctx.setInterval(reload, POLL_MS) }, [sid])
useEffect(() => ctx.onEvent(EVENT_TYPE, event => { /* payload = event.payload */ reload() }), [])
```

**Meta and version banner** (lines 17-18, 55-64, 97-106, 162). Keep `backendLine`, `isMismatch`, `MISMATCH_LINE` (D-29). Show the banner only on mismatch. Drop the debug lines (event lines, "write test", "pane 0.1.0").

**Write call and stale reply shape** (lines 138-148). Route is `POST /board/edit` with `{ session_id, ops: [...], base_rev }`. Reply is `{ ok: true, rev, board }` or `{ ok: false, error: 'stale', reason, rev, board }`, always HTTP 200. Op shapes seen: `{ op: 'add', text }` and `{ op: 'set_checked', item_id, checked }`. Read `plugin/dashboard/plugin_api.py` and `plugin/session_tasks/edit_args.py` for the full op list (edit text, delete, add with parent) before planning. Never address an item by anything but `item.id`.
```js
const first = await ctx.rest('/board/edit', { method: 'POST', body: { session_id: target, ops: [addOp()] } })
```

**Parent check** (lines 22-24). Reuse `isTopLevel(item)` to build the two-level tree. Items arrive as a flat list with `parent_id`.

**Registration and exports** (lines 182-196). Keep id, area, title, and the dock data exactly. Rename `name` to drop "(test)".
```js
ctx.register({ id: 'pane', area: 'panes', title: 'Session tasks',
  data: { placement: 'right', dock: { pane: 'workspace', pos: 'right' }, width: '320px' },
  render: () => jsx(Pane, { ctx }) })
```
`tests/test_desktop_plugin.py` asserts these exact values.

**Timers:** use `ctx.setTimeout(fn, ms)` for the "Board changed, showing the latest" notice. It returns a cleanup. Never use bare `window.*` timers.

**Colour:** only `var(--ui-*)` and Tailwind classes. Reference style from memory-ui (outside repo): `const MUTED = { color: 'var(--ui-text-secondary)' }` and `const BORDER = { borderColor: 'var(--ui-stroke-secondary)' }`, used as `style: MUTED`. The existing LINE_CLASS uses `text-(--ui-text-secondary)`. Use the same form for the checked-item muted colour (D-33). The colour scan regex rejects `#abc` and `rgb(`.

**SDK component props** (from `~/.hermes/hermes-agent/apps/desktop/src/components/ui/*.tsx`, exports in `sdk/index.ts` lines 1731-1869):

| Export | Props as the file shows them |
|--------|------------------------------|
| `Checkbox` | Radix Checkbox Root props plus `className`. Use `checked`, `onCheckedChange(value)`, `disabled`, `aria-label`. `data-state` is checked or unchecked. |
| `Input` | Native `<input>` props plus `prefix`, `suffix`, `containerClassName`, `size`. Use `value`, `onChange: e => e.target.value`, `onKeyDown`, `onBlur`, `placeholder`, `autoFocus`. Autocorrect, spellcheck and autocapitalize are off by default. |
| `ScrollArea` | Radix ScrollArea Root props plus `className`, `children`. Root is `relative overflow-hidden`, so give it a height (`className: 'min-h-0 flex-1'`). |
| `ConfirmDialog` | `open: boolean`, `onClose()`, `onConfirm()` (may be async, throw keeps it open), `title`, `description?`, `children?`, `confirmLabel?`, `busyLabel?`, `doneLabel?`, `cancelLabel?`, `destructive?`, `dismissOnConfirm?`, `secondaryAction?`. Enter confirms. Esc cancels. |
| `CopyButton` | `text: string \| (() => string \| Promise<string>)`, `appearance?` ('button' default, 'icon', 'inline'), `buttonVariant?` ('ghost' default), `buttonSize?`, `label?`, `showLabel?`, `title?`, `side?`, `onCopied?`, `onCopyError?`, `disabled?`, `children?`. Handles clipboard and the "copied" state itself. |
| `EmptyState` | `{ title: string, description?: string, className? }`. Centered, `min-h-48`. Use `title` for the empty-state line. Pass the D-30 wording through `title` or `description`. |
| `Tip` | `{ label: ReactNode, children: single element, delayDuration? }` plus tooltip content props such as `side`. Wrap one element. Renders the child alone when `label` is falsy. |
| `icons` | Namespace export of `lib/icons.ts`. Verified names: `icons.Trash2` (trash), `icons.Plus`, `icons.ChevronRight`, `icons.ChevronDown`. Used as components: `jsx(icons.Trash2, { className: 'size-3.5' })`. |

**Working reference outside the repo** (`hermes-memory-ui/desktop/plugin.js`): `jsx(Input, { value, onChange: event => update(event.target.value), placeholder })` at lines 975-980, `jsx(EmptyState, { title: t('empty') })`, and a Fragment import `{ Fragment, jsx, jsxs }`. Keys go as the third argument.

**Test hooks.** The harness stubs only `Button`. Anything new the pane imports needs a stub there (see below). Item text must stay plain text: `test_item_text_stays_plain_text` and the raw-HTML scan forbid `dangerouslySetInnerHTML`. Never name `todo` (the `todo_list` boundary test).

---

### `tests/desktop_pane_harness.mjs` (test harness, transform)

**Analog:** itself. Extend, do not rewrite.

**Stub SDK values** (lines 95-102). Add one stub function per new component and add each to `sdkValues`. Keep `cn`.
```js
function Button() {}
const sdkValues = { Button, cn: ..., host: { state: { focusedStoredSessionId: focusedAtom } }, useValue: atom => atom.get() }
```
Add: `Checkbox, Input, ScrollArea, ConfirmDialog, CopyButton, EmptyState, Tip, icons`. `icons` must be an object with `Trash2`, `Plus`, `ChevronRight`, `ChevronDown` stub functions. Missing stub names throw at link time.

**Render walk** (lines 190-211). Today it records only `Button` clicks and text lines. It must also:
- record a `Checkbox` with its `checked` and `onCheckedChange`, keyed by the row text;
- record an `Input` with `value`, `onChange`, `onKeyDown`, `onBlur`, `placeholder`;
- walk through `ScrollArea`, `Tip` and `ConfirmDialog` children (a function component is called, but a stub type is not, so the walk needs explicit cases);
- record `ConfirmDialog` `open`, `title`, `onConfirm`, `onClose`;
- record `EmptyState` title and description as lines;
- record `CopyButton` `text` (call it when it is a function).

**Steps** (lines 251-264). Add step kinds: `{"check": "<row text>", "value": bool}`, `{"type": {"input": "<placeholder or id>", "text": "..."}}`, `{"key": {"input": ..., "key": "Enter"}}`, `{"blur": ...}`, `{"confirm": true}`. Keep the `click` and `event` steps. Same unknown-step error.

**ctx stub** (lines 157-178). `setTimeout` is a no-op returning a cleanup. For the notice test, record the delay in an array and add it to the output. `setInterval` records the ms. Both return cleanups, so keep that shape.

**Output** (lines 266-278). Add `checkboxes`, `inputs`, `confirm`, `copyText` to the JSON line.

**Settle loop** (lines 238-248). Keep it. Optimistic updates call `setReply` before the network reply, so settle waits on `pending`.

---

### `tests/test_desktop_plugin.py` (test, request-response)

**Analog:** itself (343 lines).

**Rig and relay** (lines 59-82). Reuse `Rig.run(tmp_path, focused=..., steps=[...], restOverrides=...)`. Seed through `rig.store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)` (lines 85-86). Check results two ways: `result["restCalls"]` and a store read.
```python
def seed_call_john(store: BoardStore) -> None:
    store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)
```

**Static guards to keep unchanged** (lines 150-233, found by the grep): the colour regex `#[0-9a-fA-F]{3,8}\b|\brgba?\s*\(`, `import_specifiers` plus the allowlist (only the SDK, `react`, `react/jsx-runtime`), `node_check`, "no raw html and no socket", "never names todo", and the dock contribution assertions (lines 105-110 of the file). These cover the CONTEXT "import allowlist, no hardcoded colour" item.

**Tests to replace.** The phase 3 tests assert debug lines (`"[ ] #1 Call John"`, `"pane 0.1.0, api 1"`, the event lines, the write test). Rewrite them against the real pane output: item text rows, "N of M open", the empty state, a hover-free trash control. Keep the poll-interval test (`intervals`), the event-triggers-reload test (`board_gets`), the no-focus test (no `/board` call), the mismatch banner test and the meta failure test.

**New tests the decisions need:**
- D-30: Enter on the bottom input sends `add` and the input clears. Escape clears without a call. The subtask add sends `parent_id`.
- D-31: text edit sends the edit op on Enter and on blur. Escape sends nothing.
- D-32: delete without subtasks sends at once. Delete with subtasks opens the dialog with the count and sends only on confirm.
- D-33: a checked item keeps its position. The header says "N of M open".
- D-34: stale reply on a check retries once with the same op on the new rev. Stale reply on add or edit does not retry and keeps the typed text. Make staleness real with a store write between the pane load and the pane write, or use `restOverrides` for `/board/edit`.
- Copy: `copyText` is markdown with no ids (D-05). Compare against `session_tasks/markdown.py` output.

---

### `tests/rest_relay.py` (test utility)

**Analog:** itself. It already forwards GET and POST JSON with a lock (lines 35-38, 43-59). No change expected. Change it only if a test needs a delayed reply, to prove the optimistic update shows before the reply. Do that with `restOverrides` first.

## Shared Patterns

### Long-lived callbacks read a ref
**Source:** `plugin/desktop/plugin.js` lines 82-84.
**Apply to:** event listener, interval, `ctx.setTimeout` callback, retry after stale.

### Every write is one ops call
**Source:** `plugin/desktop/plugin.js` lines 138-148 and `plugin/dashboard/plugin_api.py` (`POST /board/edit`).
**Apply to:** check, add, subtask add, edit, delete. Send `base_rev` from the last board. Treat `ok: false, error: 'stale'` as a normal reply and take `reply.board`.

### Plain text only, theme variables only
**Source:** `tests/test_desktop_plugin.py` colour and raw-HTML tests.
**Apply to:** all new JSX. Children are strings. No `dangerouslySetInnerHTML`. No hex or `rgb()`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | | | Optimistic update and in-place edit have no analog in this repo. Use the CONTEXT decisions D-30 to D-34 as the spec. |

## Metadata

**Analog search scope:** `plugin/desktop`, `tests/`, `~/.hermes/plugins/hermes-memory-ui/desktop/plugin.js`, `~/.hermes/hermes-agent/apps/desktop/src/components/ui`, `sdk/index.ts`, `lib/icons.ts`.
**Files scanned:** about 12
**Pattern extraction date:** 2026-11-01
