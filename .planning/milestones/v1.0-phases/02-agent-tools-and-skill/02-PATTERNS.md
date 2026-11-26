# Phase 2: Agent tools and skill - Pattern Map

**Mapped:** 2026-10-30
**Files analyzed:** 22 (8 source, 3 plugin assets, 11 test files)
**Analogs found:** 20 / 22

Tracked-source note: every in-repo analog is git-tracked (`git ls-files` confirmed). The external analogs under `~/.hermes/plugins/` are not in any git repo. They are read-only style references, not mirrors of a tracked tree. Cite them for shape only.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `plugin/plugin.yaml` | config | n/a | `~/.hermes/plugins/agent-importers/plugin.yaml` | role-match |
| `plugin/__init__.py` | provider (register) | request-response | `~/.hermes/plugins/agent-importers/__init__.py:43-57` plus `homeassistant/tools.py:371-376` | role-match |
| `plugin/skills/board-rules/SKILL.md` | config (content) | n/a | `~/.hermes/plugins/agent-importers/skills/` | role-match |
| `plugin/session_tasks/tool_text.py` | config (static data) | n/a | `~/.hermes/plugins/homeassistant/tools.py:232-300` (schema dicts) | role-match |
| `plugin/session_tasks/edit_args.py` | utility (validator) | transform | `plugin/session_tasks/revision.py` (`check_base_rev`) + `markdown.py` parse | role-match |
| `plugin/session_tasks/guard.py` | utility (pure rule) | transform | `plugin/session_tasks/revision.py:22-39` (`is_stale`) | exact |
| `plugin/session_tasks/results.py` | utility (formatter) | transform | `plugin/session_tasks/markdown.py:24-42` (`_line`, `render`) | role-match |
| `plugin/session_tasks/board_tools.py` | service (handlers) | request-response, CRUD | `plugin/session_tasks/lineage.py` `SessionResolver` (frozen dataclass over factories) + `store.py:187-241` | role-match |
| `plugin/session_tasks/hooks.py` | middleware (hooks) | event-driven | `plugin/session_tasks/lineage.py:126` (`record_compaction`) | partial |
| `tests/test_edit_args.py`, `test_guard.py`, `test_results.py` | test | transform | `tests/test_markdown.py`, `tests/test_store_revision.py` | role-match |
| `tests/test_board_tools.py` | test | CRUD | `tests/test_store_items.py`, `tests/test_phase_flow.py` | exact |
| `tests/test_register.py`, `tests/test_hooks.py`, `tests/test_tool_text.py` | test | request-response | `tests/test_layout.py` (AST guards) | role-match |
| `tests/fakes.py` (modify: add `FakeCtx`) | test util | n/a | `tests/fakes.py` `FakeReaderFactory` (line 121) | exact |
| `tests/test_hermes_dispatch.py` + snippet | test (contract) | request-response | `tests/test_hermes_contract.py` + `tests/hermes_contract_snippet.py` | exact |
| `tests/test_layout.py` (modify, if needed) | test | n/a | itself | exact |

## Pattern Assignments

### `plugin/session_tasks/guard.py` (utility, transform)

**Analog:** `plugin/session_tasks/revision.py` (pure functions over `model` types, no I/O).

**Module shape** (`revision.py:1-8`, `15-39`):
```python
"""The stale-write rule as pure functions over the pre-batch board. No SQL and no I/O."""

from __future__ import annotations

from .model import AddItem, Board, Op, RemoveItem

def target_id(op: Op) -> int | None:
    """Return the id of the existing item the operation targets, or None for a top-level add."""
    if isinstance(op, AddItem):
        return op.parent_id
    return op.item_id
```
Copy: docstring-first module, `from __future__ import annotations`, relative `.model` imports, `isinstance` dispatch over the `Op` union. Use `Board.item(id)` (`model.py:50-54`) and `Item.updated_by` (`model.py:37`). Use `RESEARCH.md` Pattern 4 (`guarded_reasons`) as the body. `revision.target_id` can be reused for "needs `base_rev`" logic in `edit_args`.

---

### `plugin/session_tasks/edit_args.py` (utility, transform)

**Analog:** `plugin/session_tasks/revision.py:8-12` for strict type checks, errors via `BoardError(message, op_index)`.

**Strict int check pattern** (`revision.py:8-12`):
```python
def check_base_rev(base_rev: object) -> int:
    if isinstance(base_rev, bool) or not isinstance(base_rev, int) or base_rev < 0:
        raise ValueError(f"base_rev must be a non-negative int, got {base_rev!r}")
    return base_rev
```
Reuse `check_base_rev` directly. Reject bool-as-int for `item_id`, `parent_id`, `parent_ref`. Output frozen `@dataclass(frozen=True, slots=True)` `ParsedEdit` (style of `model.py:29`, `42`, `118`).

**Error type** (`model.py:138-143`): raise `BoardError(message, op_index)` or a subclass; the handler turns it into `{"error": "op N: rule"}` (D-16). Map to ops `AddItem(text, checked, parent_id, parent_ref)`, `SetText(item_id, text)`, `SetChecked(item_id, checked)`, `RemoveItem(item_id)` (`model.py:83-103`).

---

### `plugin/session_tasks/results.py` (utility, transform)

**Analog:** `plugin/session_tasks/markdown.py:24-42` (render agent view).

```python
return "".join(_line(item, include_ids) for item in board.items)   # markdown.py:41-42
```
Call `render(board, include_ids=True)` for the stale board and the changed lines. For changed ids, `board.item(id) is None` means removed (RESEARCH Pitfall 6). Return `json.dumps(obj, ensure_ascii=False)`. Failure objects carry a top-level `error` key. Success objects do not. Shapes are in RESEARCH `Code Examples`.

---

### `plugin/session_tasks/board_tools.py` (service, request-response / CRUD)

**Analog:** `plugin/session_tasks/lineage.py:103-107` (frozen dataclass holding injected factories, no module state) and `store.py:187-200`.

**Class shape** (`lineage.py:103-107`, `store.py:187-190`):
```python
@dataclass(frozen=True)
class SessionResolver:
    connect: ConnFactory
    open_reader: ReaderFactory
    clock: Clock = utc_now

@dataclass(frozen=True)
class BoardStore:
    connect: ConnFactory
    clock: Clock = utc_now
```
Copy: `@dataclass(frozen=True) class BoardTools: store; resolver; after_write: Callable[[str], None] = _noop` (RESEARCH Open Question 3 seam).

**Calls to make:**
- `self.resolver.resolve(session_id)` returns `Resolution(root_id, kind, forked_from)` (`lineage.py:38-42`). Blank id: `check_session_id` raises `InvalidSession` (`model.py:166-170`); catch it and return the `no session id` error. Delegate rule: `resolution.kind == "delegate"` blocks `board_edit` (D-20).
- `self.store.get_board(root_id)` (`store.py:192`) for `board_read`.
- `self.store.apply(root_id, ops, actor="agent", base_rev=...)` (`store.py:198`) returns `Applied(board, rev, changed_ids)` or `Stale(board, reason, op_index, item_id)` (`model.py:109-125`). `BoardError` propagates out of `apply` and is caught in the handler.

**Handler signature** (RESEARCH Code Examples, `tools/registry.py:1086-1096`): `def board_edit(self, args: dict, session_id: str | None = None, **kwargs) -> str`. Plain `def`. Never read `args["session_id"]`.

---

### `plugin/session_tasks/hooks.py` (middleware, event-driven)

**Analog (post_compaction target):** `plugin/session_tasks/lineage.py:126` `SessionResolver.record_compaction(session_id, old_session_id)`.

The hook is a closure that forwards two ids. It never raises (try/except plus `log.exception`). Logging style: module `log = logging.getLogger(__name__)` as in `lineage.py` (see `log.warning` at the loop handlers). Skip I/O when `old_session_id` is blank.

**pre_tool_call:** first line returns `None` for any tool name other than `board_edit` (RESEARCH Pitfall 4). Signature `pre_tool_call(tool_name, args, session_id="", **kwargs)`. Block shape `{"action": "block", "message": "..."}`. Shared `edit_args.parse` and `guard.guarded_reasons` do the work. Read the board only when a `SetText` op exists.

---

### `plugin/__init__.py` (provider, register)

**Analog 1:** `~/.hermes/plugins/agent-importers/__init__.py:20, 43-57` (skill path and `register_skill`).
```python
_SKILL_MD = Path(__file__).resolve().parent / "skills" / "openclaw-migration" / "SKILL.md"

def register(ctx) -> None:
    """Plugin entry point - called by the Hermes plugin loader."""
    ...
        ctx.register_skill(
            name="openclaw-migration", path=_SKILL_MD,
            description="Guided OpenClaw ... migration ...")

__all__ = ["register"]
```
**Analog 2:** `~/.hermes/plugins/homeassistant/tools.py:371-376`:
```python
def register_tools(ctx) -> None:
    for schema, handler in TOOLS:
        ctx.register_tool(
            name=schema["name"], toolset=TOOLSET, schema=schema, handler=handler,
            check_fn=_check_ha_available, emoji="...")
```
Handler signature there is `def _handle_get_state(args: dict, **kw) -> str` (`tools.py:189`): handlers return `str`. Schema is a flat dict with `name`, `description`, `parameters` (`tools.py:232-300`); do not include `session_id` in `parameters`.

Full `register(ctx)` body to copy is RESEARCH Pattern 1. Build `BoardStore(paths.connect)` and `SessionResolver(paths.connect, session_reader.open_session_reader)`. Both factories are lazy (`session_reader.py` imports `hermes_state` inside the function with `# pyright: ignore[reportMissingImports]`). Register in this order: two tools, `pre_tool_call`, `post_compaction`, prompt section, skill.

---

### `plugin/plugin.yaml` (config)

**Analog:** `~/.hermes/plugins/agent-importers/plugin.yaml` (keys: `name`, `version`, `description`, `requires_hermes: ">=0.21.6"`, `provides_tools: []`, `provides_hooks: []`). Copy the keys. Fill `provides_tools: [board_read, board_edit]` and `provides_hooks: [pre_tool_call, post_compaction]`. Use the manifest in RESEARCH Code Examples. No `python_dependencies`. The manifest guard in `tests/test_layout.py:28-39` allows `plugin.yaml`.

---

### `plugin/session_tasks/tool_text.py` (config, static data)

**Analog:** `~/.hermes/plugins/homeassistant/tools.py:232-300` (module-level `*_SCHEMA` dicts with `description` and `parameters`). Constants named `BOARD_READ_SCHEMA`, `BOARD_EDIT_SCHEMA`, `TOOLSET`, `PROMPT_SECTION_ID`, `PROMPT_SECTION_TEXT`, `PROMPT_SECTION_MAX`, `SKILL_DESCRIPTION`. Static text only, no counts or session ids. First sentence of each description is 60 characters or fewer (RESEARCH Pitfall 2). No `oneOf`, no type arrays (Pattern 3).

---

### Test files

**`tests/test_board_tools.py`** - analog `tests/test_store_items.py` and `tests/test_phase_flow.py`. Use fixtures `store`, `resolver_for`, `clock` from `tests/conftest.py:63-100`:
```python
@pytest.fixture
def store(connect: ConnFactory, clock: FakeClock) -> BoardStore:
    return BoardStore(connect, clock)

@pytest.fixture
def resolver_for(connect, clock) -> ResolverFor:
    def build(specs: dict[str, SessionSpec]) -> tuple[SessionResolver, FakeReaderFactory]:
        factory = FakeReaderFactory(specs)
        return SessionResolver(connect, factory, clock), factory
    return build
```
Autouse fixtures `hermes_home` (conftest.py:41-47) and `no_network` apply to every test. Use `SessionSpec` for a delegate session spec (`fakes.py:16`).

**`tests/fakes.py`** - add `FakeCtx` after `RaisingReaderFactory` (`fakes.py:143`). Body in RESEARCH Fake ctx test. Signature `register_tool(self, name, toolset, schema, handler, **kw)`.

**`tests/test_tool_text.py`, `test_register.py`** - analog `tests/test_layout.py`: AST guards where each helper takes a directory and returns findings (`test_layout.py:48-80`: `_parse`, `_finding`, `_imported_modules`). Reuse `_parse(path)` and `_python_files(directory)` style for the TOOL-06 AST test (no source file reads `args["session_id"]`). `MAX_MODULE_LINES = 500` (`test_layout.py:46`) applies to every new module. `CORE_DIR` is the whole `session_tasks` dir, so new modules are scanned automatically: stdlib-only imports, no `async def`.

**`tests/test_hermes_dispatch.py`** - analog `tests/test_hermes_contract.py` (marker `pytestmark = pytest.mark.hermes`, `GATEWAY_PYTHON = HERMES_AGENT_REPO / "venv" / "bin" / "python"`, `SNIPPET = ...`, `PLUGIN_DIR`, lines 12-24) and the standalone snippet `tests/hermes_contract_snippet.py:1-30` (args: plugin dir, checkout dir; sets `sys.dont_write_bytecode`, prints one JSON object, no pytest in the gateway venv). Skip logic: `conftest.py:107-113` skips `hermes` items when the checkout is missing.

## Shared Patterns

### Core module rules
**Source:** `tests/test_layout.py:24-46` and `.claude/CLAUDE.md`.
**Apply to:** every new file in `plugin/session_tasks/`. Stdlib only, no top-level Hermes import, no `async def`, at most 500 lines (aim for 300), Python 3.11 syntax, relative imports inside the package.

### Lazy Hermes adapter
**Source:** `plugin/session_tasks/session_reader.py:12-17`
```python
def open_session_reader() -> SessionReader:
    from hermes_state import SessionDB  # pyright: ignore[reportMissingImports]
    return SessionDB(read_only=True)
```
**Apply to:** any new Hermes import. Phase 2 needs none: `ctx` is passed into `register`.

### Errors
**Source:** `plugin/session_tasks/model.py:138-167`. `BoardError(message, op_index)` and its subclasses `EmptyText`, `TextTooLong`, `BoardFull`, `DepthExceeded`, `BadParentRef`; `InvalidSession(ValueError)`.
**Apply to:** `edit_args`, `board_tools`. Catch `BoardError` and `InvalidSession` in the handler and return `{"error": ...}`. Never let either escape a tool handler or a hook.

### Handler result shape
**Source:** RESEARCH Code Examples; `tools/registry.py:929-944`. Handlers return `str` (`json.dumps`). A plain dict becomes an error.
**Apply to:** `board_read`, `board_edit`.

### Session identity
**Source:** handler keyword `session_id` (`registry.py:954-962`), `check_session_id` (`model.py:170`).
**Apply to:** both handlers and both hooks. The model argument `session_id` is ignored.

### Test home isolation
**Source:** `tests/conftest.py:41-47` autouse `hermes_home` fixture plus `tests/home_guard.py`.
**Apply to:** all tests. No test touches the real `~/.hermes`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `plugin/session_tasks/hooks.py` (`pre_tool_call` half) | middleware | request-response | No hook exists in the repo or in the sampled plugins. Use the RESEARCH Pattern 4 sketch and `hooks.md:548-594`. |
| `plugin/skills/board-rules/SKILL.md` (body) | content | n/a | Only the registration path has an analog. Write the body from CONTEXT D-17 to D-20 and RESEARCH Pitfall 7. Check the frontmatter in `~/.hermes/plugins/agent-importers/skills/openclaw-migration/SKILL.md`. |

## Metadata

**Analog search scope:** `/home/theo/local_repo/hermes-session-tasks/plugin`, `tests`, `scripts`; `~/.hermes/plugins/{homeassistant,agent-importers,memory-wiki}`.
**Files scanned:** about 35.
**Pattern extraction date:** 2026-10-30
