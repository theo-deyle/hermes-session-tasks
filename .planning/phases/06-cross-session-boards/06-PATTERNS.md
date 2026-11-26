# Phase 6: Cross-session boards - Pattern Map

**Mapped:** 2026-11-02
**Files analyzed:** 22 (9 new, 13 modified)
**Analogs found:** 22 / 22

All analog paths are git-tracked (checked with `git ls-files plugin tests`).
Line numbers are from the files as read on 2026-11-02. Where a range is approximate, the symbol name is the anchor.

## File Classification

| New or modified file | Role | Data flow | Closest analog | Match |
|----------------------|------|-----------|----------------|-------|
| `plugin/session_tasks/copy_plan.py` (new) | utility (pure plan) | transform | `plugin/session_tasks/markdown.py` `plan_import` | exact |
| `plugin/session_tasks/copy_args.py` (new) | utility (arg parser) | transform | `plugin/session_tasks/edit_args.py` | exact |
| `plugin/session_tasks/titles.py` (new) | service (read-only lookup) | request-response | `plugin/session_tasks/lineage.py` `_Walk.reader()` | role-match |
| `plugin/session_tasks/store.py` (add `copy_items`, `after_ops` hook in `_apply`) | service | CRUD | `store.py` `apply` and `_apply`; `fork.py` | exact |
| `plugin/session_tasks/model.py` (`ChangeOp` gains `copied`; `CopyApplied`; `NoSourceBoard`) | model | n/a | `model.py` `ChangeOp`, `Applied`, `BoardFull` | exact |
| `plugin/session_tasks/lineage.py` (`SessionReader` Protocol widens) | model (Protocol) | n/a | itself, lines 22-31 | exact |
| `plugin/session_tasks/session_reader.py` | adapter | request-response | itself (no change needed; `SessionDB` already has the methods) | exact |
| `plugin/session_tasks/results.py` (`sessions_result`, `cross_read_result`, `copy_result`, `DELEGATE_COPY`) | utility (format) | transform | `results.py` `read_result`, `applied_result`, `DELEGATE_EDIT` | exact |
| `plugin/session_tasks/board_tools.py` (`board_read` cross path, `board_sessions`, `board_copy`) | controller (tool handler) | request-response | `board_tools.py` `board_read`, `board_edit` | exact |
| `plugin/session_tasks/board_api.py` (`BoardApi.copy`) | controller | request-response | `board_api.py` `edit` (lines 114-138) | exact |
| `plugin/session_tasks/tool_text.py` (two schemas, `board_read` `session_id`) | config (static text) | n/a | `tool_text.py` `BOARD_READ_SCHEMA`, `BOARD_EDIT_SCHEMA` | exact |
| `plugin/session_tasks/wiring.py` | config | event-driven | `wiring.py` lines 46-66 | exact |
| `plugin/plugin.yaml` (`provides_tools`) | config | n/a | itself | exact |
| `plugin/skills/board-rules/SKILL.md` | doc | n/a | itself | exact |
| `plugin/dashboard/plugin_api.py` (`CopyBody`, `POST /board/copy`) | route | request-response | `plugin_api.py` `EditBody`, `edit_board` | exact |
| `plugin/desktop/plugin.js` (picker, read-only view, copy flow) | component | request-response, event-driven | `plugin.js` `Header`, `Pane`, `showNotice`, `noticeText`, `postOp` | exact |
| `tests/test_store_copy.py` (new) | test | CRUD | `tests/test_store_seen.py`, `tests/test_fork.py` | role-match |
| `tests/test_copy_plan.py`, `tests/test_copy_args.py` (new) | test | transform | `tests/test_edit_args.py`, `tests/test_markdown.py` | exact |
| `tests/test_board_cross.py` (new) | test | request-response | `tests/test_board_tools.py` | exact |
| `tests/test_api_copy.py` (new) | test | request-response | `tests/test_api.py` with `api_client.py` | exact |
| `tests/test_pane_picker.py`, `tests/test_pane_copy.py` (new) plus harness | test | request-response | `tests/test_pane_view.py`, `tests/desktop_pane_harness.mjs`, `tests/pane_rig.py` | exact |
| `tests/fakes.py`, `tests/test_tool_text.py`, `tests/test_register.py`, `tests/test_hermes_contract.py`, `tests/test_hermes_dispatch.py` (modify) | test | n/a | themselves | exact |

## Pattern Assignments

### `plugin/session_tasks/copy_plan.py` (utility, transform)

**Analog:** `plugin/session_tasks/markdown.py` `plan_import` (lines 165-190). Pure function, `AddItem` ops in display order, `parent_ref` for subtasks, a capacity, an `overflow` count.

**Core pattern to copy** (markdown.py lines 175-190):
```python
ops: list[AddItem] = []
overflow = 0
for top in result.items:
    if len(ops) >= capacity:
        overflow += 1 + len(top.children)
        continue
    parent_index = len(ops)
    ops.append(AddItem(top.text, top.checked))
    for child in top.children:
        if len(ops) >= capacity:
            overflow += 1
            continue
        ops.append(AddItem(child.text, child.checked, parent_ref=parent_index))
return ImportPlan(tuple(ops), overflow)
```
Differences for `plan_copy(source_items, item_ids, target_items, capacity)`:
- Input is `rows.read_items` tuples, not a parse tree. Group subtasks by `parent_id`.
- Every `AddItem` starts unchecked (leave `checked` at its default).
- Skip rule (D-42): an item whose text equals the text of an open target item. Add each planned text to the open set, so a repeat inside one batch counts.
- Skipping a parent also skips its subtasks and counts each one.
- Return a frozen dataclass with `ops`, `source_ids` (parallel to `ops`, feeds the `copied` rows), `skipped`, `overflow`, `missing_id`.
- Capacity is `MAX_ITEMS - len(target_items)` (all items count, checked or not).
- Keep it import-free except `.model` (`AddItem`, `Item`). No SQL, no clock.

---

### `plugin/session_tasks/copy_args.py` (utility, transform)

**Analog:** `plugin/session_tasks/edit_args.py` (209 lines). Same discipline: a frozen result dataclass, an `EditArgsError`-style error, `_whole` for whole numbers, `check_base_rev` for `base_rev`.

**Validation rules to copy** (edit_args.py lines 47-63, 196-209, from RESEARCH Q5): `_whole(value)` accepts an `int` that is not a `bool`, or ASCII digits in a string, up to `MAX_WHOLE`. `_op_list` accepts a list, a JSON string of a list, or one object. Error text is `f"{field} must be a whole number"`.

Recommended shape:
- `parse(args) -> CopyArgs(from_session_id, item_ids | None, base_rev | None)`.
- `from_session_id`: non-blank `str`, at most 256 characters.
- `item_ids`: `None` means all open. Otherwise a list, a JSON string of a list, or one whole number; 1 to 100 whole numbers each at least 1, de-duplicated in order. An empty list is an error. A `bool` is rejected.
- Keys outside the three are ignored on the tool path (same as `edit_args.parse`).
- Do not copy `_whole`. Add one public `whole_number` in `edit_args.py` (or a shared helper) and import it.
- The route re-parses in core like `edit` does (board_api.py line 124): pydantic only checks shape and `extra="forbid"`.

---

### `plugin/session_tasks/titles.py` (service, request-response)

**Analog:** `lineage.py` `_Walk.reader()` (lines 60-65 per RESEARCH) for the open-and-close and the `sqlite3.OperationalError` handling; `session_reader.open_session_reader` for the factory (`ReaderFactory`, lineage.py line 34).

**Door** (session_reader.py, whole file):
```python
def open_session_reader() -> SessionReader:
    from hermes_state import SessionDB  # pyright: ignore[reportMissingImports]
    return SessionDB(read_only=True)
```
No new Hermes import. `SessionDB` already has `get_session_title(session_id) -> str | None` and `get_messages(session_id, limit=)`.

**Pattern for `TitleLookup`:**
- Hold the `ReaderFactory`. Open one reader per call, close it in `finally`.
- Per root id: `get_session_title`, else the first `role == "user"` message among the first 5 (`sanitize_text`, cut to 60 characters), else `"Untitled session"`.
- A missing `state.db` (`sqlite3.OperationalError`) or any per-id exception logs one warning and falls to `"Untitled session"`. It never fails the tool (use `log.warning(..., exc_info=True)` as in `board_tools._mark_seen`).
- Widen the `SessionReader` Protocol in `lineage.py` lines 22-31 with `get_session_title(self, session_id: str) -> str | None: ...` and `get_messages(self, session_id: str, *, limit: int | None = None) -> list[dict[str, Any]]: ...`. Update the docstring ("the four public methods" becomes six).
- Extend `FakeSessionReader` in `tests/fakes.py` (`_maybe_raise(method)` pattern, lines 18-30) with the same two methods and a title and first message on `SessionSpec`.

---

### `plugin/session_tasks/store.py` `copy_items` (service, CRUD)

**Analog:** `apply` and `_apply` (store.py lines 258-303) for the transaction; `fork.py` for "read two boards, write one, one transaction".

**Transaction shape to copy** (store.py `apply`):
```python
try:
    with schema.open_db(self.connect) as conn, write_txn(conn):
        return self._apply(conn, root_id, ops, actor, base_rev)
except _StaleSignal as stale:
    board = self.get_board(root_id)
    return Stale(board, stale.reason, stale.op_index, stale.item_id)
```
**Fork precedent for reading a second board inside one lock** (fork.py lines 18-24):
```python
with schema.open_db(connect) as conn, write_txn(conn):
    if rows.read_board(conn, parent_root) is None:
        return False
    now = clock()
    parent_items = rows.read_items(conn, parent_root)
```
**`_apply` extension:** add an optional `after_ops: Callable[[_Batch], None] | None = None` parameter. Call it after the op loop and the cap check, before `rows.save_board` and `rows.prune_changes` (store.py lines 296-300), so the `copied` rows share the new rev and the prune. Insert the rows with `rows.insert_change(batch.conn, batch.root_id, Change(batch.new_rev, batch.actor, "copied", new_id, f"{source_root}#{source_id}", batch.now))`, as `fork.py` line 36 does for `forked`. Do not append to `batch.entries` or `batch.changed`, so `summary_line` stays add-only.

**Guards (from RESEARCH pitfalls P2, P5, P6):**
- Source `rows.read_board(conn, source) is None` raises `NoSourceBoard` (a `BoardError` subclass, like `BoardFull` in model.py).
- Unknown `item_ids` entry: raise `_StaleSignal("not_found", 0, missing_id)` so the transaction rolls back and the caller gets `Stale`.
- Empty plan: return before `_apply`, so no empty target board row is created.
- Call `check_session_id` on both ids first, as `apply` does.
- Pass `base_rev=0`. A top-level or `parent_ref` add is never stale (store.py `_add`).
- Keep `store.py` under 800 lines (303 now).

---

### `plugin/session_tasks/model.py` (model)

**Analog:** itself. `ChangeOp: TypeAlias = Literal["add", "text", "check", "uncheck", "remove", "forked"]` (line 12): add `"copied"`. `changes.op` is `TEXT NOT NULL` with no CHECK, so `SCHEMA_VERSION` stays 1. Add a frozen `CopyApplied` dataclass (applied result plus `copied`, `skipped`, `overflow`) next to `Applied`, and `NoSourceBoard(BoardError)` next to `BoardFull`. `MAX_ITEMS = 100` is at line 16.

Consumers already tolerate an unknown op: `delta.change_line` ends with `case _: return None`; `results._KIND_OF.get(op)` ignores unknown ops. Check both with a test.

---

### `plugin/session_tasks/results.py` (utility, transform)

**Analog:** `read_result`, `applied_result`, `error_result` and the `DELEGATE_EDIT` constant (results.py lines 19-22).

- Add `DELEGATE_COPY` beside `DELEGATE_EDIT`. No dash characters (tested).
- Add `NO_BOARD` text: "no board for that session id; call board_sessions".
- `sessions_result(entries, more)` and `cross_read_result(board, root_id, title)` and `copy_result(...)` all use `json.dumps(..., ensure_ascii=False)` as `read_result` does.
- `copy_result` summary line follows D-42: `Copied N to <title>. M skipped, already on the board.`, plus ` K not copied, the board holds 100 items.` only when `overflow > 0`. The `changed` lines reuse `_changed_line` (D-13 agent form with ids).
- The cross read result must say it is another session's board and that its rev does not apply to the caller's board (RESEARCH "Tool result shapes").

---

### `plugin/session_tasks/board_tools.py` (tool handler, request-response)

**Analog:** `board_read` and `board_edit` in the same file (97 lines). The file will pass 150 lines. Keep it under 800. If the cross paths grow, put them in a second small class or module.

**Session from the keyword, never from args** (board_tools.py lines 36-43):
```python
if not isinstance(session_id, str) or not session_id.strip():
    return error_result(NO_SESSION)
try:
    resolution = self.resolver.resolve(session_id)
except InvalidSession:
    return error_result(NO_SESSION)
```
Update the `board_read` docstring: it says `args` is never read (TOOL-06). Now only `args["session_id"]` is read, as the target, and never as the caller. Name locals `caller_id` and `target_arg` (RESEARCH P3).

**Cross read rule (D-38, P1, P2):**
- Absent or blank `target_arg`: the existing own read path with `_mark_seen`.
- `target_arg` resolves to the caller's own root: own read, mark seen as before.
- Another root: `board = self.store.get_board(other.root_id)`. `board.rev == 0` means no board, return `error_result(NO_BOARD)`. Otherwise return `cross_read_result`. Never call `_mark_seen`, never write.
- Non-string `target_arg`: error result.
- A delegate caller may cross read and never marks seen.

**`board_copy` delegate check to copy** (board_tools.py lines 71-72):
```python
if resolution.kind == "delegate":
    return error_result(DELEGATE_EDIT)
```
-> `DELEGATE_COPY`. Resolve the source with `self.resolver.resolve(from_id)`. Same root as the target returns an error.

**Error and listener guard to copy** (board_tools.py `board_edit`, end of function):
```python
except BoardError as exc:
    return error_result(describe(exc))
...
if result.changed_ids:
    try:
        self.after_write(resolution.root_id, session_id, result.rev)
    except Exception:
        log.warning("board after_write listener failed", exc_info=True)
```
`Stale` from `copy_items` (a missing source id) becomes `error_result` with a source-specific message. Do not reuse `stale_text`, which says "not on the board". After a successful agent copy the store already advances seen (`advance_seen` in `_apply`).

**`board_sessions`:** `self.store.list_boards()` (store.py line 202, already newest first), title per root from `TitleLookup`, cap 50 lines plus a "more" count, mark the caller's own root "(this session)". Takes `session_id` keyword only to mark the own board; a blank keyword still lists. Add a `titles: TitleLookup` field to the frozen `BoardTools` dataclass with a default, so existing constructors in tests still work.

---

### `plugin/session_tasks/board_api.py` (controller, request-response)

**Analog:** `BoardApi.edit` (lines 114-138).

```python
resolution = self._resolve(session_id)
if resolution is None:
    return _no_session()
if resolution.kind == "delegate":
    return _invalid(None, DELEGATE_EDIT, DELEGATE_EDIT)
...
except BoardError as exc:
    return _invalid(exc.op_index, str(exc), describe(exc))
if isinstance(result, Stale):
    return _stale_reply(result, base, root_id)
if result.changed_ids:
    try:
        self.after_write(root_id, session_id, result.rev)
    except Exception:
        log.warning("board after_write listener failed", exc_info=True)
return _applied_reply(result, root_id)
```
`copy(session_id, from_session_id, item_ids, base_rev)`: same order. Actor is `"user"`. Parse with `copy_args.parse({"from_session_id": ..., "item_ids": ..., "base_rev": ...})`. Resolve the source with `self._resolve`; an unresolvable source id gives `_invalid`. Applied reply uses the `_applied_reply` keys (board_api.py lines 55-64) plus `copied`, `skipped`, `overflow`. A missing source id uses the `_stale_reply` shape with `reason "not_found"` and the target board. `_invalid`, `_no_session` and `_stale_reply` are module-level helpers (lines 25-45); reuse them.

---

### `plugin/session_tasks/tool_text.py` (config, static text)

**Analog:** `BOARD_READ_DESCRIPTION` / `BOARD_READ_SCHEMA` (lines 15-26) and `BOARD_EDIT_SCHEMA` (line 60).

```python
BOARD_READ_SCHEMA: dict[str, Any] = {
    "name": BOARD_READ,
    "description": BOARD_READ_DESCRIPTION,
    "parameters": {"type": "object", "properties": {}},
}
```
- Add `BOARD_SESSIONS = "board_sessions"` and `BOARD_COPY = "board_copy"` next to lines 12-13, each with a description and schema.
- `board_read` gains an optional string property `session_id` (not in `required`).
- `board_copy` schema: required `from_session_id` (string), optional `item_ids` (array of integers).
- First sentence at most 60 characters, distinct: "List the sessions that have a task board." and "Copy items from another session's board.".
- Each description names `todo_list` exactly once and says "not todo_list" (tested, `tests/test_tool_text.py` lines 41-46, 182-188). Say the agent copies only when Theo asks.
- Do not edit `PROMPT_SECTION_TEXT` (960 of 1000 characters, passed the own-plan gate). Cross-session rules go in the two descriptions and the skill.
- No em dash or en dash (tested, `test_no_em_or_en_dash_in_tool_text_or_skill`).
- Static text, no count, no id, no date.

---

### `plugin/session_tasks/wiring.py` and `plugin/plugin.yaml` (config)

**Analog:** wiring.py lines 46-65.
```python
store = BoardStore(connect)
resolver = SessionResolver(connect, open_reader)
tools = BoardTools(store, resolver, after_write=events.listener("agent", publish))
ctx.register_tool(
    name=tool_text.BOARD_READ,
    toolset=tool_text.TOOLSET,
    schema=tool_text.BOARD_READ_SCHEMA,
    handler=tools.board_read,
    emoji=tool_text.TOOL_EMOJI,
)
```
Build `TitleLookup(open_reader)` and pass it into `BoardTools`. Add two `ctx.register_tool` blocks with the same keyword set. Add `board_sessions` and `board_copy` to `provides_tools` in `plugin/plugin.yaml` (the manifest-equality check is in `tests/test_register.py`). `hermes plugins validate plugin/` must still report "declared tools - match".

---

### `plugin/skills/board-rules/SKILL.md` (doc)

**Analog:** itself. Add a short section: call `board_sessions` to find a board, `board_read` with `session_id` to look (rev does not apply to your board), `board_copy` only when Theo asks, copies skip texts already open. Plain language, spaced hyphen, no dash characters.

---

### `plugin/dashboard/plugin_api.py` (route, request-response)

**Analog:** `EditBody` and `edit_board` (lines 27-34, 71-89).
```python
class EditBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=SESSION_ID_MAX)
    ops: list[Any]
    base_rev: StrictInt | None = None

@router.post("/board/edit")
def edit_board(body: EditBody, api: ApiDep) -> JSONResponse:
    reply = api.edit(body.session_id, body.ops, body.base_rev)
    return JSONResponse(reply.body, status_code=reply.status)
```
Copy as `CopyBody` with `session_id`, `from_session_id` (both min 1, max `SESSION_ID_MAX`), `item_ids: list[Any] | None = None`, `base_rev: StrictInt | None = None`, and `POST /board/copy` calling `api.copy(...)`. Keep the plain `def` handler and no logic in the route. This file loads by path with no relative import; reach core only through `core_module`.

---

### `plugin/desktop/plugin.js` (component, request-response and event-driven)

**Analog:** the file itself (799 lines, over the soft ceiling before this phase). Open Question 3 in RESEARCH asks whether to split the pane. CLAUDE.md says Desktop loads one plain file, so a split needs a planner decision. The pure helpers are exported at the bottom (lines 797-798) for the harness tests; keep that pattern for new pure helpers.

**Header to replace** (lines 218-231): the picker row replaces `Header`'s "N of M open" line. Keep `headerText(counts)` (line 95) as the count string so existing tests that look for "N of M open" keep passing. Update `tests/test_pane_view.py` `test_header_sits_outside_the_scroll_area` (line 201) to the new count node.

**Notice line** (lines 205-216, 493-502):
```js
function noticeText({ meta, notice, loadFailed }) {
  if (isMismatch(meta)) return MISMATCH_LINE
  const kind = notice ? notice.kind : null
  if (kind === 'failed') return WRITE_FAILED_NOTICE
  if (kind === 'stale') return STALE_NOTICE
  return loadFailed ? LOAD_FAILED_NOTICE : null
}
...
function showNotice(kind) {
  const state = current.current
  state.seq += 1
  const mine = state.seq
  if (typeof state.noticeCleanup === 'function') state.noticeCleanup()
  setNotice({ kind, seq: mine })
  state.noticeCleanup = ctx.setTimeout(() => {
    if (current.current.seq === mine) setNotice(null)
  }, NOTICE_MS)
}
```
Extend with `showNotice(kind, text)` and a `copied` kind whose text is the D-42 sentence. Keep one notice at a time (RESEARCH P10).

**Write flow to copy:** `sendOp(op, onOutcome, asked)` takes the session at the start (lines ~584-593); `take(focused, reply)` records `revs[asked]` (lines ~455-465); the focus-change reset effect keyed on `[sid]` (lines ~558-577) must also clear `picked` (D-45, RESEARCH P9). `postOp` retries only `set_checked` (lines ~187-193): never retry a copy. `boardPath(sid)` (line 195) serves the read-only view: GET `/board?session_id=<root>`.

**Picker:** `DropdownMenu`, `DropdownMenuTrigger` (asChild, `Button` ghost sm), `DropdownMenuContent`, `DropdownMenuItem` with `onSelect`. Code sketch is in RESEARCH "Picker menu" and the in-tree precedent is Desktop `kanban/board-switcher.tsx` lines 344-376. `Select` precedent is memory-ui `plugin.js` lines 537-548 (not used here).

**Titles:** `host.request('session.list', { limit: 200 })`, join on `row._lineage_root_id ?? row.id` (use `??`, not `||`). Call on mount, on focus change and when the picker opens, not on the 6 s poll. A failure keeps fallback labels and shows no error line.

**Read-only view:** reuse `ItemRow` and `ItemBlock` (lines 288-358) with an `actions` prop that has no checkbox handler, no `AddLine` (line 360), no delete. Add a hover "Copy" `RowButton` (line 252) on top-level rows only. Banner text "Read only. Viewing another session." with a Back link. Event handler: match `payload.root_id` against the shown root (D-45).

**Theme and API rules:** only `var(--ui-*)` colours, `ctx.setTimeout` and friends, no JSX, imports only from `@hermes/plugin-sdk`, `react`, `react/jsx-runtime`.

---

### `tests/test_store_copy.py` (test, CRUD)

**Analog:** `tests/test_store_seen.py` and `tests/test_fork.py` for fixtures (`store`, `connect`, `clock` from `tests/conftest.py` lines 83-99) and for direct `BoardStore` use. Seed with `store.apply(session, [AddItem(text)], actor="agent", base_rev=0)` as `tests/test_pre_llm_hook.py` `add` does. Cases: new ids continue from `next_item_id`; subtasks follow parents; copies start unchecked; actor is the copier; one `copied` row per item with `<source>#<id>`; no board row created for an empty plan (use `count_rows` from `test_board_tools.py`); cap at 98 plus 5 gives 2 copied and 3 overflow; case-sensitive skip; a checked duplicate on the target does not block; a missing source id rolls back everything.

---

### `tests/test_board_cross.py` (test, request-response)

**Analog:** `tests/test_board_tools.py` (590 lines, so new tests go in a new file). Reuse its helpers `tools_for(store, resolver_for, specs)`, `read(tools, session_id, args)`, `count_rows`, `seen(connect, root)`. Cases: cross read leaves the source `agent_seen_rev` unchanged; an arg `session_id` never changes the caller; a blank arg reads the own board; a typo gives the no-board error; a delegate cannot copy but can cross read; `board_sessions` order, cap, "(this session)", title fallback chain (title, first user message, "Untitled session"); a compressed lineage id reaches its root board.

**Tests that must change in the same plan** (RESEARCH Q6):
- `tests/test_board_tools.py` line 76 `test_read_ignores_a_session_id_in_the_arguments`: replace with the cross read cases.
- `tests/test_tool_text.py` line 62 `test_board_read_schema_declares_no_session_id_property`: replace with "declared, optional, not required".
- Keep `test_no_schema_declares_session_id` (line 159) for `BOARD_EDIT_SCHEMA` and add the check for `BOARD_COPY_SCHEMA` (`from_session_id` allowed, plain `session_id` not).
- `tests/test_register.py`: tool list and manifest.

---

### `tests/test_api_copy.py` (test, request-response)

**Analog:** `tests/test_api.py` (375 lines) with `tests/api_client.py`: real router through `TestClient`, the `rig` fixture, `RULE_CASES`, `test_confirmed_field_is_refused` (extra field refused, copy as `test_extra_field_is_refused`), `test_boards_lists_roots_newest_first`. Cases: applied reply keys, stale-shaped reply for a missing source id, invalid for no source board and same board, 400 for a blank session, delegate target refused.

---

### `tests/test_pane_picker.py`, `tests/test_pane_copy.py` and the harness (test, request-response)

**Analog:** `tests/test_pane_view.py`, `tests/test_desktop_plugin.py`, `tests/pane_rig.py`, `tests/desktop_pane_harness.mjs` (657 lines; renders only `Button`, `Checkbox`, `ConfirmDialog`, `CopyButton`, `EmptyState`, `Input`, `ScrollArea`, `Tip` stubs; an unknown stub renders nothing).

Harness additions (RESEARCH Q6): stubs for `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuSeparator` rendering children, recording `menuItems`; a `host.request` stub fed from config key `sessionList` (`"__error__"` rejects with `Hermes gateway unavailable`) and a `requestCalls` output; `icons.Copy`; steps `{"pick": "<text>"}` and reuse `{"click": "Copy", "row": "<id>"}`. Event steps already pass the full object with `payload` (`board_event`, `tests/test_desktop_plugin.py` lines 81-87).

Existing filters that start with `/board` also match `/boards` and `/board/copy`: tighten them (for example `test_event_with_no_focus_makes_no_board_call`, around line 79) or the pane must skip `/boards` with no focus.

---

### Hermes-marked tests

**Analog:** `tests/hermes_contract_snippet.py` with `tests/test_hermes_contract.py` (fake versus real `SessionDB`) and `tests/hermes_dispatch_snippet.py` with `tests/test_hermes_dispatch.py`. Add parity for `get_session_title` and `get_messages(limit=)`, and dispatch of `board_sessions` and `board_copy` through the real registry. The gateway venv has no pytest, so the snippet prints one JSON line and the wrapper module asserts. Copy the snippet header and the `hermes` marker use; the run command is `pytest -m hermes tests/test_hermes_contract.py`. Reuse `tests/hermes_snippet_setup.py`.

## Shared Patterns

### Session from the keyword, delegate gets no write
**Source:** `plugin/session_tasks/board_tools.py` lines 36-43 and 71-72; `board_api.py` lines 116-120
**Apply to:** `board_sessions`, `board_read` cross path, `board_copy`, `BoardApi.copy`. The caller comes only from the keyword (tools) or the request `session_id` (route). A delegate never copies and never marks seen.

### One write transaction, `BEGIN IMMEDIATE`
**Source:** `plugin/session_tasks/db.py` `write_txn` (line 14), `store.py` `apply` (`with schema.open_db(self.connect) as conn, write_txn(conn):`)
**Apply to:** `copy_items`. The skip check and the insert share one lock. No Python lock. No second connection for the `copied` rows.

### Listener fault never breaks a committed write
**Source:** `board_tools.py` `board_edit` end; `board_api.py` lines 132-137
**Apply to:** `board_copy` and `BoardApi.copy`. Fire `after_write` only when `result.changed_ids` is non-empty, inside `try/except Exception` with `log.warning(..., exc_info=True)`.

### Errors as results, not exceptions
**Source:** `board_tools.py` `except BoardError as exc: return error_result(describe(exc))`; `board_api.py` `_invalid(exc.op_index, str(exc), describe(exc))`
**Apply to:** `NoSourceBoard`, bad `copy_args`, same-board copy.

### Frozen dataclass results and pure modules
**Source:** `markdown.py` `ImportPlan`, `delta.py`, `nudge.py`
**Apply to:** `copy_plan.py`, `copy_args.py`. No I/O in pure modules.

### Parameterised SQL, table names in constants
**Source:** `rows.py` (`f"... {CHANGES} WHERE root_id = ?"`)
**Apply to:** any new query. Phase 6 should need none: `list_board_summaries`, `read_board`, `read_items`, `insert_item`, `insert_change` already cover it.

### Static tool text
**Source:** `tool_text.py` header docstring ("The text holds no count, no session id and no date.")
**Apply to:** both new descriptions and schemas.

### Docs style
No em dash or en dash in code, comments, tool text, the skill or this file. Use a spaced hyphen. Plain language.

### Size ceiling
`tests/test_board_tools.py` (590), `tests/test_api.py` (375), `tests/desktop_pane_harness.mjs` (657) and `plugin/desktop/plugin.js` (799) are near or over the 800-line soft ceiling. Put new tests in new files. Decide the pane split before planning the pane tasks.

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `host.request('session.list')` call from a pane | client call | No plugin on this machine calls `host.request` yet (RESEARCH Q2). Use the SDK doc and the Desktop `canonical-chat.ts` precedent; add a live smoke check on devpc. |
| `DropdownMenu` in the harness | test stub | The harness has no menu stubs. Add them as listed above. |

## Metadata

**Analog search scope:** `plugin/session_tasks/`, `plugin/dashboard/`, `plugin/desktop/plugin.js`, `plugin/plugin.yaml`, `tests/`
**Files read or grepped:** about 14 (board_tools, board_api, store, fork, markdown, results, lineage, session_reader, wiring, tool_text, plugin_api, plugin.js, fakes, plus CONTEXT, RESEARCH and the Phase 5 pattern map)
**Pattern extraction date:** 2026-11-02
