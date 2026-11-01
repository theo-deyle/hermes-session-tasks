# Phase 3: REST router and client install spike - Pattern Map

**Mapped:** 2026-10-31
**Files analyzed:** 25 new or modified
**Analogs found:** 24 / 25

All in-repo analogs are git-tracked under `plugin/` and `tests/`. External analogs live outside this repo: `deploy-dash/scripts/install-desktop.ps1` and `hermes-memory-ui` are tracked in their own repos. `~/.hermes/plugins/memory-wiki` has no git repo, so treat it as a read-only reference.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `plugin/dashboard/plugin_api.py` | route | request-response | `~/.hermes/plugins/memory-wiki/dashboard/plugin_api.py` (load) + `plugin/session_tasks/board_tools.py` (logic) | role-match |
| `plugin/dashboard/manifest.json` | config | n/a | `~/.hermes/plugins/gsd-status-api/dashboard/manifest.json` | exact |
| `plugin/desktop/plugin.js` | component | request-response + event-driven | `~/.hermes/plugins/hermes-memory-ui/desktop/plugin.js` | role-match |
| `plugin/session_tasks/board_json.py` | utility | transform | `plugin/session_tasks/results.py` | exact |
| `plugin/session_tasks/events.py` | service (adapter) | pub-sub | `plugin/session_tasks/session_reader.py` (lazy Hermes import) | role-match |
| `plugin/session_tasks/version.py` | utility | file-I/O | RESEARCH Code Example 2 | no analog |
| `plugin/session_tasks/nudge.py` | utility | transform | `plugin/session_tasks/tool_text.py` + `markdown.py` render | role-match |
| `plugin/session_tasks/hooks.py` (add `make_pre_llm_call`) | hook | request-response | same file, `make_pre_tool_call` / `make_post_compaction` | exact |
| `plugin/session_tasks/store.py` (add `list_boards`) | model/service | CRUD (read) | same file, `get_board`, `user_touched_ids` | exact |
| `plugin/session_tasks/board_tools.py` (change `after_write`) | service | CRUD | same file | exact |
| `plugin/session_tasks/wiring.py` (register hook, publisher) | config | n/a | same file | exact |
| `plugin/plugin.yaml` (add `pre_llm_call`) | config | n/a | same file | exact |
| `scripts/install-desktop.ps1` | utility | file-I/O | `deploy-dash/scripts/install-desktop.ps1` | exact (fix home logic) |
| `tests/test_api.py`, `tests/test_api_load.py` | test | request-response | `tests/test_board_tools.py`, `tests/test_register.py` | role-match |
| `tests/test_events.py` | test | pub-sub | `tests/test_board_tools.py` | role-match |
| `tests/test_version.py` | test | file-I/O | `tests/test_register.py` `manifest_list` | role-match |
| `tests/test_pre_llm_hook.py` | test | request-response | `tests/test_hooks.py` | exact |
| `tests/test_desktop_plugin.py` | test | transform | `hermes-memory-ui/tests/test_desktop_plugin.py` + `desktop_plugin_smoke.mjs` | exact |
| `tests/test_install_script.py` | test | file-I/O | none in repo | no match |
| `tests/test_register.py`, `tests/test_board_tools.py` (modify) | test | n/a | themselves | exact |
| `tests/live/own_job/*` | test harness | batch | Phase 2 scratchpad `run.sh`, `analyze.py` (gone with the session; copy before it is cleaned) | partial |
| `pyproject.toml` (filterwarnings) | config | n/a | same file line 26 | exact |
| `README.md` | doc | n/a | none | no analog |

## Pattern Assignments

### `plugin/session_tasks/hooks.py` - add `make_pre_llm_call` (hook, request-response)

**Analog:** the same file. Copy the factory shape, the keyword-only session id, the delegate skip and the never-raise wrapper.

**Imports already present** (lines 9-18):
```python
from __future__ import annotations
import logging
from collections.abc import Callable, Mapping
from . import edit_args, guard, tool_text
from .lineage import SessionResolver
from .model import BoardError
from .results import describe
from .store import BoardStore
log = logging.getLogger(__name__)
```

**Factory shape** (lines 52-65):
```python
def make_pre_tool_call(store, resolver) -> Callable[..., dict[str, str] | None]:
    def pre_tool_call(tool_name: str = "", args: object = None, session_id: object = "", **kwargs: object):
        ...
        except Exception:
            log.exception("board guard failed")
```

**Session and delegate skip** (lines 38-42):
```python
if not isinstance(session_id, str) or not session_id.strip():
    return None
resolution = resolver.resolve(session_id)
if resolution.kind == "delegate":
    return None
```

**Apply:** `make_pre_llm_call(store, resolver)` returns `pre_llm_call(session_id: object = "", **kwargs) -> str | None`. Blank session returns `None`. A delegate returns `None`. Build the nudge from `nudge.py`, add the board block when `store.get_board(resolution.root_id).items` is not empty. Wrap the body in `try/except Exception` and call `log.warning(..., exc_info=True)`, return `None` (D-28). The guard hook uses `log.exception`; D-28 asks for a warning. Also catch `InvalidSession` from `resolver.resolve` (see `board_tools.py` below).

---

### `plugin/session_tasks/board_tools.py` - change `after_write` (service, CRUD)

**Analog:** the same file.

**Current seam** (lines 24-26, 76-82):
```python
def _no_listener(root_id: str) -> None:
    return None
...
    after_write: Callable[[str], None] = _no_listener
...
        if result.changed_ids:
            try:
                self.after_write(resolution.root_id)
            except Exception:
                log.warning("board after_write listener failed", exc_info=True)
        return applied_result(result)
```

**Apply:** change the type to `Callable[[str, str, int], None]` taking `(root_id, session_id, rev)`, default `_no_listener(root_id, session_id, rev)`. Call it with `result.board.rev` (the `Applied` has `board` and `changed_ids`). Keep the swallow and warning. Update `tests/test_board_tools.py` and `tests/test_register.py` in the same commit.

**Session guard pattern** to reuse on the route (lines 36-45):
```python
if not isinstance(session_id, str) or not session_id.strip():
    return error_result(NO_SESSION)
try:
    resolution = self.resolver.resolve(session_id)
except InvalidSession:
    return error_result(NO_SESSION)
if resolution.kind == "delegate":
    return error_result(DELEGATE_EDIT)
```

---

### `plugin/dashboard/plugin_api.py` (route, request-response)

**Analog A (load):** `~/.hermes/plugins/memory-wiki/dashboard/plugin_api.py` lines 13-45. Path-loaded, no relative imports, `sys.modules` insert before `exec_module`, pop on failure:
```python
def _core():
    mod = sys.modules.get(_CORE_MODULE)
    if mod is not None:
        return mod
    path = Path(__file__).with_name("memory_wiki_core.py")
    spec = importlib.util.spec_from_file_location(_CORE_MODULE, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_CORE_MODULE] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(_CORE_MODULE, None)
        raise
    return mod
```
Adapt it as RESEARCH Code Example 1 `load_core()` does: load the package `session_tasks/__init__.py` with `submodule_search_locations=[str(init.parent)]` under key `hermes_session_tasks_core`. Reach submodules with `importlib.import_module(CORE_KEY + ".store")`.

**Analog B (logic):** `board_tools.py` `board_edit` (above). The route does the same steps with `actor="user"`: resolve, delegate check, `edit_args.parse`, `store.apply`, map `Stale` and `BoardError` to JSON with HTTP 200 (D-22), publish after a changed write (`result.changed_ids`). No `confirmed` field (D-24).

**Rules:** plain `def` handlers. Use `APIRouter()` and export `router`. Pydantic models at the boundary only (`EditBody` with `session_id: str = Field(min_length=1)`, `ops: list[Any]`, `base_rev: int | None`). Reuse `edit_args.parse`, `results.describe` and `Stale.reason`. `reason` is `"stale"` or `"not_found"` (model.py:13), not the CONTEXT example text. Put a machine code in `error` and the human line in `message`.

---

### `plugin/session_tasks/board_json.py` (utility, transform)

**Analog:** `plugin/session_tasks/results.py` (stdlib only, dataclass in, JSON shape out).

**Shape to copy** (lines 1, 82-89): module docstring states the key rule; helpers like `_changed_line(board, item_id)` take `Board` and `Item` and return plain values; `applied_result(applied: Applied) -> str` is the model for `applied_json`. Return dicts, not strings, here. Reuse `describe(exc)` for the human line. Keep the module under the 500 line layout limit and stdlib at module level (`tests/test_layout.py`).

---

### `plugin/session_tasks/events.py` (adapter, pub-sub)

**Analog:** `plugin/session_tasks/session_reader.py` for the lazy Hermes import style, and RESEARCH Code Example 3 for the body.
```python
def publish(root_id: str, session_id: str, rev: int, actor: str) -> None:
    payload = {"session_id": session_id, "root_id": root_id, "rev": rev, "actor": actor}
    try:
        from hermes_cli.plugin_events import broadcast_plugin_event  # pyright: ignore[reportMissingImports]
        broadcast_plugin_event(PLUGIN_ID, EVENT, payload)
    except Exception:
        log.warning("board.updated publish failed", exc_info=True)
```
`hermes_cli.plugin_events` is already on `HERMES_PUBLIC_IMPORTS` in `tests/test_layout.py`. Import inside the function only. Publish after commit.

---

### `plugin/session_tasks/store.py` - add `list_boards` (CRUD read)

**Analog:** the same file, `get_board` (lines 194-198):
```python
check_session_id(root_id)
with schema.open_db(self.connect) as conn, read_txn(conn):
    return _read_board(conn, root_id)
```
**Apply:** one `with schema.open_db(self.connect) as conn, read_txn(conn):` and a SQL helper in `rows.py` (the module that holds `read_user_touched_ids`). Return root id, rev, open count, total, updated_at. Do not read `state.db` (titles are Phase 6).

---

### `plugin/session_tasks/wiring.py` and `plugin/plugin.yaml`

**Analog:** the same files. Add one line next to the other hooks (wiring.py lines under `register`):
```python
ctx.register_hook("pre_tool_call", hooks.make_pre_tool_call(store, resolver))
ctx.register_hook("post_compaction", hooks.make_post_compaction(resolver))
```
Add `ctx.register_hook("pre_llm_call", hooks.make_pre_llm_call(store, resolver))` and pass `after_write=` built from `events.publish` into `BoardTools(store, resolver, after_write=...)`. Add `pre_llm_call` under `provides_hooks` in `plugin.yaml` in the same commit. `tests/test_register.py::test_manifest_provides_exactly_the_registered_tools_and_hooks` compares the two lists. The `PluginContext` Protocol in wiring.py needs no change (`register_hook` exists).

---

### `plugin/desktop/plugin.js` (component, request-response + event-driven)

**Analog:** `~/.hermes/plugins/hermes-memory-ui/desktop/plugin.js` (plain ESM, `jsx`/`jsxs`, `ctx.register`). Also RESEARCH Code Example 4 for the stub body.

**Registration shape** (memory-ui lines 1862-1871):
```javascript
function register(ctx) {
  ctx.register({ id: 'page', area: ROUTES_AREA, data: { path: PLUGIN_ROUTE }, render: () => jsx(MemoryPage, { ctx }) })
}
```
Use `ctx.register({ id: 'pane', area: 'panes', title, data: { placement: 'right', width: '320px' }, render })` instead.

**Rules:** imports only `@hermes/plugin-sdk`, `react`, `react/jsx-runtime`. `const PLUGIN_VERSION = '0.1.0'` and `const API_VERSION = 1` near the top, each on its own line so the drift test regex finds them. Use `ctx.rest`, `ctx.onEvent('plugin.hermes-session-tasks.board.updated', ...)`, `ctx.setInterval` at 5 to 8 s. No hex or `rgb()` colours, no `JSON.stringify`, no JSX. Check `e.payload.root_id` against the last board answer.

---

### `plugin/dashboard/manifest.json`

**Analog:** `~/.hermes/plugins/gsd-status-api/dashboard/manifest.json`. Content:
```json
{"name": "hermes-session-tasks", "api": "plugin_api.py", "tab": {"hidden": true}}
```
The layout guard bans manifest file names under `plugin/` (check `tests/test_layout.py` for the exact list). Confirm `manifest.json` is not on it before adding.

---

### `scripts/install-desktop.ps1` (utility, file-I/O)

**Analog:** `/home/theo/local_repo/deploy-dash/scripts/install-desktop.ps1`. Copy these pieces:

**Input guards** (lines 25-52): `Test-GsdHost` (strict regex `^[A-Za-z0-9._@-]+$`, no leading `-`), `Test-GsdRel`, `Test-GsdHome` (`IsPathRooted`).

**scp with fallback** (lines 54-66):
```powershell
& scp -O -q $Source $Target 2>$null
if ($LASTEXITCODE -eq 0) { return $true }
& scp -q $Source $Target
return ($LASTEXITCODE -eq 0)
```

**Atomic install** (lines 68-95): create the slot folder, copy to `.plugin.js.new` in it, check `export default`, `Move-Item -Force`, delete the temp in `finally`, print SHA-256 (lines 117-120).

**Change it:**
- Do not copy the home logic (line 100: `Join-Path $HOME '.hermes'`). Resolve as `data-paths.mjs` does: env `HERMES_HOME`, else on Windows the user env var then `%LOCALAPPDATA%\hermes` (legacy `~\.hermes` only when the first does not exist and the second does), else `~/.hermes`. Offer `-HermesHome`, `-DryRun` and a host parameter for the devpc alias. Use `param()` and `-File` style (D-26 says run with pwsh 7), so `exit` is allowed; the sibling avoids `exit` only because it runs through `Invoke-Expression`.
- Source path: `plugin/desktop/plugin.js` in this repo. Slot: `desktop-plugins/hermes-session-tasks/plugin.js`. Never write `.hermes-package.json`.
- Test on devpc with `pwsh -File` and a fake `scp` first on `PATH` (Pester is not installed).

---

### `tests/test_pre_llm_hook.py` (test, request-response)

**Analog:** `tests/test_hooks.py`. Reuse the fixtures and helper style:
```python
from conftest import ResolverFor
from fakes import FakeReaderFactory, RaisingReaderFactory, SessionSpec
...
def broken_connect() -> sqlite3.Connection:
    raise RuntimeError("service is down")

@pytest.fixture
def broken_store() -> BoardStore:
    return BoardStore(broken_connect)

@pytest.fixture
def hook(store, resolver_for):
    resolver, _ = resolver_for({})
    return make_pre_tool_call(store, resolver)
```
Cases: nudge only on an empty board; board block with ids after `store.apply("s1", [AddItem("Call John")], actor="agent", base_rev=0)`; delegate returns `None`; blank session returns `None`; broken store returns `None` and logs a warning (`caplog`); fence text escaped and capped.

---

### `tests/test_api.py` and `tests/test_api_load.py` (test, request-response)

**Analog:** `tests/test_register.py` for fixtures (`connect`, `store`) and `tests/conftest.py` (autouse `hermes_home` tmp dir, no network, fake clock). Build `FastAPI()`, `include_router(router, prefix="/api/plugins/hermes-session-tasks")`, call with `TestClient`. `test_api_load.py` loads `plugin_api.py` as the host does: `spec_from_file_location("hermes_dashboard_plugin_hermes-session-tasks", path)`, put in `sys.modules` before `exec_module`. Route code must receive the same `connect` as the fixtures: set `HERMES_HOME` (already autouse) so `paths.connect` uses the tmp home.

**Needed config** (`pyproject.toml` line 26, after `"error"`):
```toml
filterwarnings = [
  "error",
  "ignore:Using `httpx` with `starlette.testclient`:starlette.exceptions.StarletteDeprecationWarning",
  "ignore:The anyio.abc.BlockingPortal alias is deprecated:DeprecationWarning",
]
```

---

### `tests/test_version.py`

**Analog:** `tests/test_register.py` lines 19-34, `manifest_list`. Add `manifest_value("version")` in the same line-scan style (regex `^version:\s*(\S+)\s*$`). Asserts: `plugin.js` `PLUGIN_VERSION` equals the manifest; `plugin.js` `API_VERSION` equals `session_tasks.version.API_VERSION`.

---

### `tests/test_desktop_plugin.py` (test, transform)

**Analog:** `~/.hermes/plugins/hermes-memory-ui/tests/test_desktop_plugin.py` plus `tests/desktop_plugin_smoke.mjs`.

**Import allowlist** (memory-ui lines 11-24):
```python
ALLOWED_DESKTOP_IMPORTS = {"@hermes/plugin-sdk", "react", "react/jsx-runtime"}
imports = set(re.findall(r"from\s+['\"]([^'\"]+)['\"]", source))
assert imports and imports <= ALLOWED_DESKTOP_IMPORTS
assert "JSON.stringify" not in source
assert not re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\s*\(", source)
```
**VM harness call** (lines 36-47): `subprocess.run(["node", "--experimental-vm-modules", str(SMOKE_HARNESS), str(DESKTOP_PLUGIN)], cwd=ROOT, check=False, capture_output=True, text=True)` then `json.loads(completed.stdout)`. The harness stubs SDK values (`useState`, `useEffect`, `host`, ...) and runs the plugin in `node:vm`. Copy it and stub `ctx.rest`, `ctx.onEvent`, `ctx.setInterval`; feed a `/meta` answer with a different `backend_version` and assert the banner text.

**Change vs analog:** do NOT rely on plain `node --check plugin.js`. It returns 0 on a truncated ESM file (RESEARCH Pitfall 1). Pipe the source: `subprocess.run(["node", "--input-type=module", "--check"], input=source, ...)`. Add a self-test that a truncated string fails.

---

### `tests/live/own_job/` (batch harness)

No tracked analog yet. Source files are in the Phase 2 scratchpad `live-gap-ownjob2/job.txt`, `live-02-05/run.sh`, `live-02-05/analyze.py` (RESEARCH Answer 6). Copy them into the repo in the first plan, before the scratchpad goes away. Make the job a parameter. Pass rule: 3 of 3 runs show a `board_edit` with 2 or more `add` ops, a later `set_checked` with `checked` true, and a final board with every added item checked.

## Shared Patterns

### Never raise from a hook or a publish
**Source:** `plugin/session_tasks/board_tools.py` lines 78-82 and `hooks.py` lines 64-65.
**Apply to:** `events.publish`, `make_pre_llm_call`, the `after_write` listener call.
```python
try:
    self.after_write(resolution.root_id)
except Exception:
    log.warning("board after_write listener failed", exc_info=True)
```

### Session id and delegate rule
**Source:** `board_tools.py` lines 36-45 (above). **Apply to:** the route handlers and the pre_llm_call hook. Tools take the session only from the keyword (TOOL-06). The route takes it from the request (D-25), then resolves the same way.

### One write path
**Source:** `BoardStore.apply(root_id, ops, *, actor, base_rev)` in `store.py` line 210. Returns `Applied` or `Stale`, raises `BoardError`. Route passes `actor="user"`. Publish only when `result.changed_ids` is not empty.

### Module rules (layout guard)
**Source:** `tests/test_layout.py`. Each module in `plugin/session_tasks` stays under 500 lines, imports only the standard library at module level, and `plugin/` holds no manifest file such as `package.json` or `pyproject.toml`. Hermes and fastapi imports go in `plugin_api.py` or inside functions.

### Plain `def` handlers, one connection per operation
**Source:** `store.py` `schema.open_db(self.connect)` plus `read_txn` or `write_txn`. No module-level state in `plugin_api.py` beyond the cached core module and the router.

### Docs and strings
No em dash or en dash in any file. Use a spaced hyphen. Script and README commands for Theo are PowerShell 7.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `plugin/session_tasks/version.py` | utility | file-I/O | No version reader exists. Use RESEARCH Code Example 2 (`API_VERSION = 1`, regex over `plugin.yaml`, return `"unknown"` on a miss). |
| `tests/test_install_script.py` | test | file-I/O | No PowerShell test exists here. Run `pwsh -File` with a fake `scp` first on `PATH` and a `-DryRun` case. |
| `README.md` | doc | n/a | No README yet. Give per-machine steps (Mac, Windows PC), the Windows home `%LOCALAPPDATA%\hermes`, the "closing the only pane disables the plugin" fix, and the gateway restart note. |

## Metadata

**Analog search scope:** `plugin/`, `tests/`, `scripts/`, `~/.hermes/plugins/{memory-wiki,hermes-memory-ui,gsd-status-api}`, `~/local_repo/deploy-dash/scripts`.
**Files scanned:** about 20 read or excerpted.
**Pattern extraction date:** 2026-10-31
