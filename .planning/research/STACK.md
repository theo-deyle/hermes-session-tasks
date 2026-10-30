# Stack Research

**Domain:** Hermes Agent + Hermes Desktop unified plugin (Python backend half, plain ESM React pane half), one task board per session
**Researched:** 2026-10-30
**Confidence:** HIGH for versions and Hermes APIs (read from local source and run on devpc). MEDIUM for three items marked in "Open items".

Method: every fact below comes from the local Hermes source at `~/.hermes/hermes-agent` (Hermes Agent v0.22.5, 2026.9.24), the installed plugins in `~/.hermes/plugins/`, or a command run on devpc on 2026-10-30. The web was not used. Paths are cited as `file:line`. Lines in the docs are in `~/.hermes/hermes-agent/website/docs/developer-guide/`, shortened to `sdk-doc` (`desktop-plugin-sdk.md`) and `plugins-doc` (`plugins/index.md`).

## Answers to the five questions

| # | Question | Answer |
|---|----------|--------|
| 1 | Gateway Python and venv packages | Python 3.11.16. fastapi 0.133.1, pydantic 2.13.4 (core 2.46.4), starlette 1.3.1, httpx 0.28.1, uvicorn 0.41.0, PyYAML 6.0.3. SQLAlchemy and aiosqlite are NOT installed. pytest and ruff are NOT installed. |
| 2 | Storage | Stdlib `sqlite3` through Hermes's own `plugins.plugin_storage.plugin_db("hermes-session-tasks")`. No JSON files. |
| 3 | Desktop half | React 19.2.7. SDK UI kit has every component the pane needs. Test with `node --check` plus the VM smoke harness copied from hermes-memory-ui. No linter, no build. |
| 4 | Dev tooling | uv project at the repo root, Python 3.11 managed build, dev group pins the gateway's fastapi, starlette, pydantic and httpx. pytest 9.1.1, ruff 0.15.10, pyright. The `pyproject.toml` stays OUTSIDE the symlinked package dir. |
| 5 | Markdown checklist | A hand-written stdlib line parser, about 60 lines, in the Python core only. The pane never parses markdown. |

## Verified facts from the local gateway

| Fact | Evidence |
|------|----------|
| Gateway Python is 3.11.16 | `~/.hermes/hermes-agent/venv/bin/python --version`; `venv/pyvenv.cfg` has `version_info = 3.11` |
| Hermes accepts Python `>=3.11,<3.15` | `hermes-agent/pyproject.toml:15` |
| Installed: fastapi 0.133.1, starlette 1.3.1, pydantic 2.13.4, httpx 0.28.1 | `venv/bin/python -m pip list` run 2026-10-30 |
| Hermes pins its own dev tools: pytest 9.1.1, ruff 0.15.10, starlette 1.3.1 | `hermes-agent/pyproject.toml:540, 546, 543` |
| The gateway Python links SQLite 3.53.1 | `venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"` |
| System `python3` links SQLite 3.40.1, which Hermes treats as WAL-reset vulnerable and downgrades to `journal_mode=DELETE` | Observed warning on 2026-10-30; `hermes_cli/sqlite_runtime.py:23` |
| `get_hermes_home()` is `from hermes_constants import get_hermes_home`, returns a `Path`, honours a context-local override, then `HERMES_HOME`, then the platform default | `hermes_constants.py:188-195` |
| `hermes_constants`, `hermes_state`, `hermes_cli.plugin_events`, `plugins.plugin_storage` are the documented public imports; other core modules are flagged as private | `hermes_cli/plugin_validate_private_imports.py:38` |
| Dashboard `plugin_api.py` is imported with `spec_from_file_location`, so it is NOT part of a package and cannot use relative imports | `hermes_cli/web_server_dashboard.py:1169`; comment in `~/.hermes/plugins/memory-wiki/dashboard/plugin_api.py:30-35` |
| The agent half (`__init__.py`) loads as package `hermes_plugins.<slug>`, so relative imports work there | `hermes_cli/plugins_loader.py:701-740` |
| Tool handlers get `session_id` only if the signature names it | `tools/registry.py:954-962`; `plugins-doc:876-882` |
| `plugins.isolation` defaults to `in_process`; the `host` mode moves third-party plugin code and dashboard plugin APIs into a separate process | `hermes_cli/plugin_isolation.py:28-30, 94-103`; `~/.hermes/config.yaml` has no `isolation` key |

## Recommended Stack

### Core Technologies (gateway half)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11 (gateway has 3.11.16; dev uses uv-managed 3.11.15) | Runtime for `__init__.py`, `plugin_api.py`, core package | The gateway runs 3.11. Code must not use 3.12+ syntax (no PEP 695 `type X = ...`, no f-string nesting tricks). Confidence HIGH. |
| Standard library only in core | n/a | Domain code: models, markdown parser, board store | `plugins-doc:651-701` says Hermes resolves plugin dependencies into its own venv. A plugin with zero dependencies avoids that step and any version clash. Confidence HIGH. |
| fastapi | 0.133.1 (gateway-owned) | `APIRouter` in `dashboard/plugin_api.py`, exports `router` | Required contract: `sdk-doc:1792-1815`. The gateway ships it, so the plugin declares no dependency. HIGH. |
| pydantic | 2.13.4 (gateway-owned) | Validate REST request bodies at the `plugin_api.py` boundary only | House rule "validate every external value at the boundary". Core stays on `@dataclass` so domain code imports no framework. HIGH. |
| `sqlite3` (stdlib) | SQLite 3.53.1 in the gateway | Board storage | See "Storage decision" below. HIGH. |
| `plugins.plugin_storage.plugin_db` | Hermes v0.22.5 | Opens `<HERMES_HOME>/plugin-data/hermes-session-tasks/data.db` with WAL, foreign keys, 5000 ms busy timeout | `plugins/plugin_storage.py:27-47`. Verified in a clean 3.11 venv: returns `journal_mode=wal`, `foreign_keys=1`, `busy_timeout=5000`. HIGH. |
| `hermes_cli.plugin_events.broadcast_plugin_event` | Hermes v0.22.5 | Push `board.updated` to every connected Desktop | `hermes_cli/plugin_events.py:50-86`. Wire name `plugin.hermes-session-tasks.board.updated`. Logs a warning and returns when no gateway is present, so it never raises in tests (`plugin_events.py:80-86`). HIGH. |
| Plugin hooks `pre_llm_call`, `post_compaction`, `on_session_delete` | Hermes v0.22.5 | Inject Theo's edits; follow session lineage; clean up | Hook table `plugins-doc:1505-1530`; `post_compaction(session_id, old_session_id, ...)` in `website/docs/user-guide/features/hooks.md:1118-1139`. HIGH. |
| `ctx.register_tool`, `ctx.register_hook`, `ctx.register_skill` | Hermes v0.22.5 | Agent half registration | `hermes_cli/plugins.py:462, 943`; `hermes_cli/plugins_content.py:23`. HIGH. |

### Storage decision: SQLite through `plugin_db`

One recommendation: a single SQLite file, opened per operation through `plugin_db`.

Why SQLite beats JSON files:

1. **Cross-process safety.** The agent tools, the REST routes and the hooks can run in different processes. Examples: `dashboard.turn_isolation` child (`sdk-doc:1867`) and `plugins.isolation: host` (`web_server_dashboard.py:1141`). A Python `threading.Lock` does not cross a process boundary. `ctx.state` itself uses `threading.RLock` only (`hermes_cli/plugins_state.py:20`). SQLite `BEGIN IMMEDIATE` locks across processes.
2. **The stale-write rule is one transaction.** Inside `BEGIN IMMEDIATE`, read `boards.rev`, compare it with the caller's `base_rev`, apply the change, set `rev = rev + 1`, commit. JSON files need a lock file plus read-modify-write plus atomic rename to get the same result.
3. **Hermes sanctions it.** `plugins-doc:1144-1164` names `plugin_data_dir()` and `plugin_db()` as the durable-state home. It survives `hermes plugins update` and `remove` and follows the active profile. The PROJECT.md rule "never in `state.db`" holds, because this is a separate file.
4. **WAL is handled for the plugin.** `plugin_db` goes through Hermes's WAL fallback (`plugins/plugin_storage.py:43-47`). Readers (the pane poll) do not block the writer (agent tool).
5. **No size limit.** `ctx.state` caps at 10 MiB per plugin (`plugins_state.py:19`) and replaces the whole blob on each write.

Rules for the adapter (one module, the only one that imports Hermes storage):

- Open a connection per operation and close it. Never cache a connection or the path. `plugin_data_dir` resolves `get_hermes_home()` on every call so the active profile applies (`plugin_storage.py:27-33`). Hermes fixed a file-descriptor leak from unclosed WAL connections (`hermes_cli/sqlite_util.py:3-6`).
- `plugin_db` returns `row_factory=None` (tuples) and `check_same_thread=False`. The adapter maps tuples to dataclasses.
- Own a 10-line `write_txn` helper (`BEGIN IMMEDIATE`, `COMMIT`, guarded `ROLLBACK`). Hermes has one in `hermes_cli/sqlite_util.py:99-115`, but that module is not on the public import list, so a copy is safer.
- Migrate with `PRAGMA user_version`. Avoid `STRICT` tables so the file also works on older SQLite.
- Plugin handlers are plain `def`, not `async def`. FastAPI runs them in its thread pool. Hermes's own ruff config bans blocking calls inside `async def` because they froze the whole gateway (`hermes-agent/pyproject.toml:753-767`).
- Return a stale write as HTTP 200 with `{"ok": false, "error": "stale", "board": {...}}`. Desktop turns any 4xx into `new Error("409: <body text>")` and the `statusCode` property may not survive the IPC hop (`apps/desktop/electron/api-transport.ts:183-190`). A structured 200 avoids string parsing in the pane. Confidence MEDIUM until tested.
- The code must work with `journal_mode=DELETE` too. A vulnerable SQLite (system python3 has 3.40.1) disables WAL. Readers then wait on writers up to the 5 s busy timeout. Tests that need WAL carry a `requires_wal` style marker.

### Desktop half (pane)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| One plain ESM file `desktop/plugin.js` | n/a | Pane, default export `{ id, name, register(ctx) }` | Contract `sdk-doc:158-166`. No JSX, no build: `sdk-doc:1998-2001`. HIGH. |
| `react` | 19.2.7 (Desktop-owned) | Hooks: `useState`, `useEffect`, `useMemo`, `useRef` | `apps/desktop/package.json:141, 144`. Only `@hermes/plugin-sdk`, `react`, `react/jsx-runtime` resolve (`sdk-doc:2001-2002`). HIGH. |
| `react/jsx-runtime` | with React 19.2.7 | `jsx(type, props, key?)` and `jsxs(type, props, key?)` | hermes-memory-ui imports `{ Fragment, jsx, jsxs }` at `~/.hermes/plugins/hermes-memory-ui/desktop/plugin.js:25`. Children go in `props.children`. The key is the third argument (`plugin.js:667, 709`). `jsxs` takes a children array. HIGH. |
| `@hermes/plugin-sdk` | Desktop-owned | UI kit, `host`, React Query, i18n | Canonical export list is `apps/desktop/src/sdk/index.ts` (`sdk-doc:2043`). HIGH. |
| `@tanstack/react-query` via SDK | 5.101.2 | `useQuery`, `useMutation`, `useQueryClient`, shared `queryClient` | `apps/desktop/package.json:106`; exports `sdk/index.ts:2008, 1895`. Used with `useQuery({ queryKey, queryFn, staleTime })` in memory-ui `plugin.js:1779`. HIGH. |

SDK names the pane needs, each verified in `apps/desktop/src/sdk/index.ts`:

| Need | Export (line) |
|------|---------------|
| Checkbox | `Checkbox` (1732) |
| Text entry | `Input` (1779), `Textarea` (1802) |
| Buttons and badges | `Button` (1731), `Badge` (1730) |
| Scrolling list | `ScrollArea` (1794) |
| Empty and error states | `EmptyState` (1775), `ErrorState` (1776), `Skeleton` (1799) |
| Session picker | `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue` (1797) |
| Row menu | `ContextMenu*` (1741-1751), `DropdownMenu*` (1769-1773) |
| Confirm delete | `ConfirmDialog` (1739) |
| Copy markdown | `CopyButton` (1753) |
| Tooltips | `Tip`, `Tooltip*` (1803) |
| Icons | `icons` (1869) |
| Class merge | `cn` (documented `sdk-doc:1660-1686`) |
| State | `host` (577), `useValue` (2004) |
| Live update | `host.onEvent` (1375), `ctx.onEvent` (`sdk-doc:192`) |
| Focused session | `host.state.focusedStoredSessionId` (609) |
| Plugin strings | `usePluginI18n` (1845) and `ctx.i18n.register` (template `~/.hermes/skills/hermes-desktop-plugins/templates/plugin.js`) |

Note: the table in `sdk-doc:2030-2043` does not list `usePluginI18n`, but the source exports it. The source wins.

Pane rules confirmed in `sdk-doc:1998-2026`:

- Theme variables only (`var(--ui-text-secondary)`, `var(--ui-stroke-secondary)`, `var(--ui-accent)`). No hex or `rgb()`.
- Use `ctx.setTimeout`, `ctx.setInterval`, `ctx.addEventListener`, `ctx.onDispose`. Bare `window.*` timers survive hot reload.
- `ctx.socket` is a no-op on OAuth remotes (`sdk-doc:1900-1901`, `2026`). Live update uses `host.onEvent('plugin.hermes-session-tasks.board.updated', ...)` plus a `useQuery` `refetchInterval` fallback of 5 to 10 s.
- Pane registration: `ctx.register({ id: 'pane', area: 'panes', title, data: { placement: 'right', width: '320px' }, render })` (`sdk-doc:252-259`).

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None at runtime | n/a | The plugin declares no Python dependency | Always. `plugin.yaml` has no `python_dependencies`. A `pyproject.toml` with `dependencies = []` next to `plugin.yaml` would count as no declaration (`plugins-doc:690-692`), but a dev group there would not. See layout below. |
| `pytest-cov` | 7.1.0 | Coverage on `plugin/session_tasks` | House target 80 percent. Dev only. |

### Development Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| uv | 0.11.26 on devpc | Environment and lock | `uv sync` with `python-preference = "only-managed"` gives Python 3.11.15 with SQLite 3.53.1, the same SQLite as the gateway. The system 3.11.2 has SQLite 3.40.1 and silently drops WAL. Verified 2026-10-30. |
| pytest | 9.1.1 | Tests | Same pin as Hermes (`pyproject.toml:540`). `--import-mode=importlib` as in `~/.hermes/plugins/homeassistant/pytest.ini` and `agent-importers/pytest.ini`. |
| ruff | 0.15.10 | Lint and format | Same pin as Hermes (`pyproject.toml:546`). `target-version = "py311"`. Select `E, F, I, UP, B, ASYNC, PLW1514`. |
| pyright | 1.1.414 | Type check | Resolved by uv on 2026-10-30. `pythonVersion = "3.11"`. House gate is `ruff check`, `ruff format --check`, `pyright`, `pytest`. |
| `hermes plugins validate <path>` | Hermes v0.22.5 | Plugin gate | Ran on a prototype of the nested layout: manifest, loadable, declared tools match, declared hooks match, built-in tool collisions, security scan, and "desktop surface - stays inside the plugin SDK surface" all passed. This is the pane import check. |
| Node | 24.19.0 on devpc | `node --check`, VM smoke harness | CI in hermes-memory-ui uses Node 22. |

### Repo layout (verified by prototype)

```
hermes-session-tasks/                 # repo root
  pyproject.toml  uv.lock  .python-version   # dev only, NOT visible to Hermes
  tests/
    conftest.py
    test_markdown.py  test_store.py  test_api.py  test_tools.py  test_desktop_plugin.py
    desktop_plugin_smoke.mjs                 # copied from hermes-memory-ui, adapted
  plugin/                             # symlink target for ~/.hermes/plugins/hermes-session-tasks
    plugin.yaml
    __init__.py                       # register(ctx): tools, hooks, skill
    skills/session-tasks/SKILL.md
    session_tasks/                    # shared core, stdlib only
      __init__.py  models.py  markdown.py  store.py  service.py
    dashboard/
      manifest.json                   # { "name": "hermes-session-tasks", "api": "plugin_api.py" }
      plugin_api.py                   # router; path-loads session_tasks
    desktop/
      plugin.js
```

Why `pyproject.toml` lives at the repo root and not in `plugin/`: Hermes reads a `pyproject.toml` next to `plugin.yaml` as the plugin's dependency declaration, and a file with dependency groups counts as a real declaration (`plugins-doc:651-692`). Hermes would then try to resolve it into the gateway venv. The installed plugins `homeassistant` and `agent-importers` put it next to `plugin.yaml` only because they have runtime dependencies.

Why a shared `session_tasks/` package: the agent half (`__init__.py`, package-relative import) and the REST half (`plugin_api.py`, no package) must run the same board code. Prototype that passed on 2026-10-30:

```python
# plugin/dashboard/plugin_api.py (top of file)
def _load_core():
    name = "hermes_session_tasks_core"
    if name in sys.modules:
        return sys.modules[name]
    core_dir = Path(__file__).resolve().parent.parent / "session_tasks"
    spec = importlib.util.spec_from_file_location(
        name, core_dir / "__init__.py", submodule_search_locations=[str(core_dir)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
```

The loader returned the core, relative imports inside the core resolved, and a `TestClient` call to the router returned 200. This is the same idea as `memory-wiki/dashboard/plugin_api.py:28-45`, extended with `submodule_search_locations` so a multi-file package works. Core code holds no module-level mutable state, because the two halves hold two copies of the module.

The symlink target `plugin/` works: `~/.hermes/plugins/gsd-status-api` is already a symlink into a repo (`ls -la` 2026-10-30), and `hermes plugins validate` passed on the nested layout.

### pyproject sketch (repo root)

```toml
[project]
name = "hermes-session-tasks"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dependencies = []

[dependency-groups]
dev = [
  "fastapi==0.133.1",
  "starlette==1.3.1",
  "pydantic==2.13.4",
  "httpx==0.28.1",
  "pytest==9.1.1",
  "pytest-cov==7.1.0",
  "ruff==0.15.10",
  "pyright==1.1.414",
]

[tool.uv]
python-preference = "only-managed"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["plugin"]
addopts = "--import-mode=importlib -m 'not hermes'"
markers = ["hermes: needs the hermes-agent checkout on sys.path"]

[tool.ruff]
target-version = "py311"
preview = true

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "ASYNC", "PLW1514"]

[tool.pyright]
pythonVersion = "3.11"
include = ["plugin", "tests"]
venvPath = "."
venv = ".venv"
```

How the tests run against the gateway's versions:

- The dev group pins the same fastapi, starlette, pydantic and httpx the gateway has. A `hermes`-marked test runs `~/.hermes/hermes-agent/venv/bin/python -c "import importlib.metadata ..."` and fails when the pins drift from the gateway. Nothing is installed into the gateway venv.
- `@pytest.mark.hermes` tests put `HERMES_AGENT_REPO` (default `~/.hermes/hermes-agent`) on `sys.path`, the pattern in `~/.hermes/plugins/memory-wiki/conftest.py`. Verified: `plugins.plugin_storage.plugin_db` and `broadcast_plugin_event` import and run from a clean uv 3.11 venv this way.
- Default tests need no Hermes. The adapter takes a `sqlite3.Connection` factory, so `store` tests use `sqlite3.connect(":memory:")` or a `tmp_path` file. A GitHub CI run without hermes-agent still passes.
- Two Hermes imports in the adapter carry `# pyright: ignore[reportMissingImports]`. Everything else is typed.
- API tests build `FastAPI()`, `include_router(router, prefix="/api/plugins/hermes-session-tasks")`, and use `fastapi.testclient.TestClient` (needs httpx).

How installed plugins lay this out (for reference):

| Plugin | `pyproject.toml` | `pytest.ini` | `tests/` |
|--------|------------------|--------------|----------|
| `homeassistant` | yes, `requires-python >=3.11`, one dependency (`aiohttp`) | `testpaths = tests`, `--import-mode=importlib`, `asyncio_mode = strict` | `conftest.py` loads the plugin dir as package `homeassistant_plugin`, removes the plugin root from `sys.path` so its `tools.py` does not shadow core `tools` |
| `agent-importers` | yes, `dependencies = []` | same without asyncio | `conftest.py` plus 7 test files |
| `hermes-memory-ui` | none | none | `test_*.py`, two `.mjs` harnesses, CI in `.github/workflows/ci.yml` |
| `memory-wiki` | none | none (root `conftest.py`) | loads dashboard modules by path, `HERMES_HOME` fixture on `tmp_path` |
| `hindsight` | yes plus `uv.lock` | none | `conftest.py` |

The lesson from `homeassistant/tests/conftest.py`: a top-level module name in the plugin root can shadow a Hermes module. The shared package is therefore named `session_tasks`, never `tools`, `core` or `utils`.

### Testing the pane with no build step

Recommendation: three cheap checks, no npm install.

1. `node --check plugin/desktop/plugin.js`. Verified on Node 24.19.0 against hermes-memory-ui's 71 KB `desktop/plugin.js` with no `package.json`. Node detects ESM syntax.
2. The VM smoke harness. Copy `~/.hermes/plugins/hermes-memory-ui/tests/desktop_plugin_smoke.mjs` (about 200 lines). It loads the file as a `vm.SourceTextModule` with synthetic modules for the three allowed specifiers, runs `register(ctx)` against a fake `ctx`, and prints JSON. It ran on Node 24.19.0 with `node --experimental-vm-modules`. Extend the fake SDK with `Checkbox`, `ScrollArea`, `host.onEvent` and `host.state.focusedStoredSessionId`, then assert the pane registers `area: 'panes'` with `placement: 'right'` and that `ctx.rest` receives the board paths.
3. A pytest file modelled on `hermes-memory-ui/tests/test_desktop_plugin.py:9-39`: the import set is a subset of `{@hermes/plugin-sdk, react, react/jsx-runtime}`, and the source has no hex colour or `rgb(` literal. `hermes plugins validate` repeats the import check.

Pure logic stays out of the pane. The pane renders the JSON tree the API returns and sends raw markdown text on import. All parsing, ordering and conflict logic runs in Python, where pytest covers it. That keeps untested JavaScript small.

Not recommended: ESLint, Prettier, TypeScript `--checkJs`, Vitest, Playwright, react-test-renderer. Each needs `node_modules` and a `package.json`. The SDK has no npm type package here. The `@hermes/plugin-sdk` specifier only exists inside Desktop.

House-rule note: `donmor-coding-practices/SKILL.md` allows plain JavaScript only in a Cloudflare Pages site. This plugin is a recorded exception because Desktop loads one uncompiled file (`sdk-doc:1998-1999`).

### Markdown checklist parser

Recommendation: write a small stdlib parser in `session_tasks/markdown.py`. No library.

Why: markdown libraries (`markdown-it-py`, `mistune`, `mdformat`) are not in the gateway venv (`pip list`, 2026-10-30). The task grammar is three line shapes. A parser that returns only what the board stores is easier to test than a full CommonMark tree.

Working line rule, tested on a prototype on 2026-10-30:

```python
_ITEM = re.compile(r"^(?P<indent> *)(?P<bullet>[-*+]) +\[(?P<mark>[ xX])\](?: +(?P<text>.*?))? *$")
```

Steps: normalise `\r\n` to `\n`; call `line.expandtabs(4)` first; match; keep a stack of `(indent, node)`; pop while the top indent is `>=` the new indent; the top of the stack becomes the parent. Render is the inverse: two spaces per level, lowercase `x`.

Pitfalls (the prototype hit the first two):

| Pitfall | What happens | Rule |
|---------|--------------|------|
| Tab versus spaces | A tab and four spaces both mean one level in CommonMark | `expandtabs(4)` before matching; compare indent columns, not counts |
| Non-checkbox bullet (`- plain`) is skipped | Its checkbox children attach to the previous sibling's branch | Decide in discuss: treat a plain bullet as an unchecked item, or as a note. Never drop it silently |
| Depth cap | A line nested deeper than the board allows | Clamp to the maximum depth and attach to the deepest allowed parent. Do not drop the line |
| Indent jump (0 then 6 spaces) | Looks like a level skip | Stack rule makes it a child of the last item. Fine |
| Uppercase `[X]`, bullets `*` and `+` | Common in hand-written lists | Accept on import, emit `- [x]` on export |
| `- [ ]` with empty text | Regex allows it | Reject or skip empty text on import; the board needs a non-empty title |
| Trailing text after `]` without a space (`- [ ]foo`) | Not a checkbox in CommonMark | Not matched; treated as a plain line |
| Headings, paragraphs, blank lines | Present in pasted text | Ignore on import |
| No stable id in markdown | Round trip loses ids; the agent cannot name an item | Render a short per-board handle in the agent view (for example `- [ ] text (#3)`) and strip it on parse. Decide the handle format in discuss |
| Item text containing newline or leading `[ ]` | Breaks the line format | Collapse newlines to a space on write; cap text length |

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| SQLite via `plugin_db` | JSON files under `plugin-data/` | Only if writes were single-process and never concurrent. The requirement says agent and pane write at the same time, so this does not hold. |
| SQLite via `plugin_db` | `ctx.state` (`hermes_cli/plugins_state.py`) | Small settings or cursors. It is a key-value blob with a 10 MiB cap and an in-process lock only. Not available inside `plugin_api.py` because there is no `ctx`. |
| `plugin_db` | Raw `sqlite3.connect` on `get_hermes_home() / ...` | Never. Raw `PRAGMA journal_mode=WAL` bypasses Hermes's WAL-reset and network-filesystem fallback (`tests/hermes_cli/test_sqlite_util_canonical.py:109-133`). |
| Hand-written parser | A markdown library | Only if the format grows to full CommonMark. Not a v1 need. |
| `node --check` plus VM harness | A Vite or esbuild build | Never for a disk plugin. Desktop loads the file uncompiled (`sdk-doc:1998-1999`). |
| uv-managed 3.11 | System `python3` 3.11.2 | Never for tests that need WAL. SQLite 3.40.1 triggers the WAL downgrade. |
| Shared `session_tasks/` package, path-loaded | Duplicate the code in `__init__.py` and `plugin_api.py` | Never. Two copies drift. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Any third-party Python dependency in gateway code | Hermes resolves plugin dependencies into its own venv (`plugins-doc:651-701`). A clash fails the install. The gateway already ships what is needed | stdlib, fastapi, pydantic |
| SQLAlchemy, aiosqlite | Not installed in the gateway venv (`pip list`) | stdlib `sqlite3` |
| `state.db` or `SessionDB` for board data | PROJECT.md boundary. `hermes_state` is allowed only to read lineage | `plugin_db` |
| A Python `threading.Lock` as the concurrency guard | Does not cross a process boundary | `BEGIN IMMEDIATE` plus `rev` compare |
| `async def` route handlers that call sqlite | Blocks the gateway event loop (`hermes-agent/pyproject.toml:753-767`) | Plain `def` handlers |
| `ctx.socket` as the live feed | No-op on OAuth remotes (`sdk-doc:1900-1901`, `2026`) | `host.onEvent` plus `useQuery` `refetchInterval` |
| Polling faster than a few seconds | `sdk-doc:2013` | 5 to 10 s |
| JSX syntax, npm packages, bundlers in `desktop/` | Disk plugin loads uncompiled; only three specifiers resolve | `jsx()` and `jsxs()` |
| Hex or `rgb()` colours | `sdk-doc:2003-2005` | `var(--ui-*)` |
| `pyproject.toml` with dev dependencies inside `plugin/` | Hermes reads it as the plugin's runtime dependency list | Repo-root `pyproject.toml` |
| Importing private Hermes modules (`hermes_cli.sqlite_util`, `tui_gateway.server`) | Can move between releases; flagged by the admission lint (`plugin_validate_private_imports.py`) | `plugins.plugin_storage`, `hermes_cli.plugin_events`, own 10-line helpers |
| A session id taken from model arguments for the current session | PROJECT.md rule; spoofable | `session_id` keyword from the handler signature |
| Top-level module names `tools`, `core`, `utils` in `plugin/` | Shadow Hermes modules in tests (`homeassistant/tests/conftest.py:20-24`) | `session_tasks/` |

## Stack Patterns by Variant

**Deployment across the SSH remote (Theo's Macs and Windows PCs).**
- The symlink on devpc delivers the Python half and the agent tools. It does NOT deliver `desktop/plugin.js` to a remote Desktop.
- `sdk-doc:1766-1773` says the Desktop half copy is local to the machine the app runs on, and that for a remote backend the install dialog clones the desktop half separately into `desktop-plugins/`. A package whose agent half was installed on the remote host without that clone shows its Desktop half as "unavailable (remote backend)".
- Impact: each Desktop machine needs the Desktop half installed from Git with the Desktop target checked, and the repo must be reachable from that machine. The repo is private on GitHub. This is a deployment question for the roadmap. Confidence HIGH on the doc text, MEDIUM on how it plays with the SSH remote setup, because it was not tested.
- Develop on devpc only: `ln -s /home/theo/local_repo/hermes-session-tasks/plugin ~/.hermes/plugins/hermes-session-tasks`. A linked package hot-reloads the Desktop half when Desktop runs on the same machine (`sdk-doc:1739-1746`).

**If the gateway runs with `plugins.isolation: host`.**
- Dashboard plugin APIs are served through the plugin host with buffered responses (seen in the `hermes plugins validate` output). The SQLite design already works across processes. `broadcast_plugin_event` is relayed to the parent (`sdk-doc:1867`). Not the current config.

**Session identity and compression.**
- Tools receive `session_id` by signature. The pane reads `host.state.focusedStoredSessionId` (`sdk/index.ts:609`). Desktop's stored id is the gateway `session_key` (`tui_gateway/server.py:1609`). That the two are equal after compression is NOT verified.
- Hermes gives two signals for lineage: the `post_compaction` hook with `session_id` and `old_session_id`, and `SessionDB.get_conversation_root(session_id)` (`hermes_state_messages.py:1745`) with `get_compression_lineage` (`hermes_state_compression.py:914`). The stack supports an alias table keyed by session id and filled from the hook, with the lineage call as a lazy fallback. The choice belongs to discuss-phase.

**Bundled skill reach.**
- `plugins-doc:1201` says plugin skills are not listed in the system prompt. The `register_skill` docstring (`plugins_content.py:23-27`) says they are listed in `<available_skills>`. The two disagree. Tool descriptions are always in the model's view, so the usage rules (when to add, ask before ambiguous changes, never use as scratch plan) go in the tool schemas as well as in the skill. Confidence MEDIUM.

## Installation

```bash
# bash or zsh on devpc, from the repo root
uv sync --managed-python          # Python 3.11.x with SQLite 3.53.1, dev group pinned to gateway versions
uv run ruff check plugin tests
uv run ruff format --check plugin tests
uv run pyright
uv run pytest
node --check plugin/desktop/plugin.js
node --experimental-vm-modules tests/desktop_plugin_smoke.mjs plugin/desktop/plugin.js
~/.hermes/hermes-agent/venv/bin/hermes plugins validate plugin
```

Deploy (announce the gateway restart first: it drops live Desktop connections):

```bash
ln -s /home/theo/local_repo/hermes-session-tasks/plugin ~/.hermes/plugins/hermes-session-tasks
hermes plugins enable hermes-session-tasks   # never hand-edit config.yaml
# then restart the gateway so plugin_api.py routes mount
```

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| fastapi 0.133.1 | starlette 1.3.1, pydantic 2.13.4 | Gateway set. The dev group repeats it exactly. |
| `TestClient` | httpx 0.28.1 | httpx is required by Starlette's test client. |
| Python 3.11.15 (uv managed) | SQLite 3.53.1 | Equals the gateway's SQLite. System 3.11.2 has SQLite 3.40.1, which disables WAL. |
| React 19.2.7 | `react/jsx-runtime` `jsx(type, props, key)` | Verified in hermes-memory-ui. |
| Hermes Agent v0.22.5 | `plugins.plugin_storage`, `hermes_cli.plugin_events`, `post_compaction` hook | Re-check after each `hermes update`. `plugin.yaml` can set `requires_hermes` once the floor is known. |

## Open items for phase research

1. **Stale-write transport (MEDIUM).** Confirm in a live Desktop that a 409 loses its `statusCode` across IPC. If it does, keep the structured 200. Test in the REST phase.
2. **Session id equality after compression (MEDIUM).** Confirm that the tool's `session_id` and Desktop's `focusedStoredSessionId` follow the same id after a compaction. Test with a forced `/compress` on devpc.
3. **Skill visibility (MEDIUM).** Confirm whether a plugin skill appears in the system prompt. Settles whether the skill or the tool descriptions carry the behaviour rules.
4. **Remote Desktop install (MEDIUM).** Confirm how the Desktop half reaches the Mac and Windows machines over the SSH remote.
5. **`ctx.rest` error shape on non-2xx.** Not needed if the structured-200 rule holds.

## Sources

- `~/.hermes/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md` (lines 153-263, 1693-1933, 1996-2076) - HIGH
- `~/.hermes/hermes-agent/website/docs/developer-guide/plugins/index.md` (lines 347-430, 651-701, 789-950, 1144-1210, 1505-1650) - HIGH
- `~/.hermes/hermes-agent/website/docs/user-guide/features/hooks.md` (`post_compaction`, line 1118) - HIGH
- `~/.hermes/hermes-agent/apps/desktop/src/sdk/index.ts`, `apps/desktop/package.json`, `apps/desktop/electron/api-transport.ts` - HIGH
- `~/.hermes/hermes-agent/plugins/plugin_storage.py`, `hermes_cli/sqlite_util.py`, `hermes_cli/plugin_events.py`, `hermes_cli/plugins_state.py`, `hermes_cli/plugin_validate_private_imports.py`, `hermes_cli/web_server_dashboard.py`, `hermes_cli/plugin_isolation.py`, `hermes_constants.py`, `tools/registry.py`, `pyproject.toml` - HIGH
- `~/.hermes/plugins/hermes-memory-ui/` (`desktop/plugin.js`, `tests/`, `.github/workflows/ci.yml`), `memory-wiki/`, `homeassistant/`, `agent-importers/`, `gsd-status-api/` - HIGH
- `~/.hermes/skills/hermes-desktop-plugins/templates/plugin.js` - HIGH
- `~/.claude/skills/donmor-coding-practices/SKILL.md` and `python/*.md` - HIGH (house rules)
- Commands run on devpc 2026-10-30: gateway `pip list`, `python --version`, `sqlite3.sqlite_version`, `hermes plugins validate` on a prototype layout, `uv sync` on a pinned dev group, `node --check`, VM smoke harness, a prototype checklist parser, a `plugin_db` and `broadcast_plugin_event` import test in a clean 3.11 venv - HIGH (executed, not read)
