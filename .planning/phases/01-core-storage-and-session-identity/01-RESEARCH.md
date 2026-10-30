# Phase 1: Core, storage and session identity - Research

**Researched:** 2026-10-30
**Domain:** Python stdlib core (SQLite board store, markdown checklist, session lineage) for a Hermes Agent plugin, plus the uv, ruff, pyright and pytest matrix on Python 3.11 and 3.14
**Confidence:** HIGH for lineage, storage, tooling and test design (all run on devpc this session). MEDIUM for live Desktop behaviour (read from source, not run).

Path shorthand: `HA/` = `~/.hermes/hermes-agent/` (checkout at commit `bf0203a794`, 2026-10-22, read this session). `proto/` = a throwaway prototype project in the session scratchpad that was built to prove the repo layout, the matrix script and the two-process test. It is not in the repo.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** An item may have subtasks. A subtask may not have subtasks. Two levels total. The schema keeps `parent_id` so the depth can change later (STOR-03). - **Reversibility:** reversible - the schema is depth-agnostic; only the parser, the store check and the pane change.
- **D-02:** A pasted line nested deeper than one subtask level moves up to the subtask level under the nearest top-level item. The import result reports how many lines moved. No line is dropped.
- **D-03:** Each item has a per-board integer id that starts at 1 and is never reused, even after a delete. The store keeps a `next_item_id` counter per board. - **Reversibility:** costly - the agent view and every tool operation address items by this id; a change breaks the Phase 2 tool contract.
- **D-04:** The agent view of the board shows the id first, after the checkbox: `- [ ] #3 Call John`. A subtask is indented two spaces: `  - [x] #4 Book the room`.
- **D-05:** The parser strips a leading `#<digits> ` token after the checkbox and keeps the rest as text. The clipboard export for Theo carries no ids. The renderer has an `include_ids` switch.
- **D-06:** A session that Hermes marks as an explicit branch starts with a copy of its parent's board, taken the first time the branch touches the board. The copy gets new item ids and a journal row that names the parent. After the copy, the two boards do not share edits. - **Reversibility:** reversible - the alternative is an empty board; no stored data changes shape.
- **D-07:** A compression child (when `compression.in_place` is false) is the same board, resolved through the alias table to the root session id. A `/new` or reset session is a separate conversation and gets an empty board.
- **D-08:** A plain bullet with no checkbox (`- text`, `* text`, `+ text`) becomes an unchecked item. Uppercase `[X]` counts as checked. Headings, paragraphs and blank lines are ignored.
- **D-09:** A checkbox line with empty text is skipped and counted in the import result. Item text is one line; newlines collapse to a space on write.
- **D-10:** Caps: 100 items per board and 500 characters per item. The store enforces both. An import that would pass a cap stops at the cap and reports the overflow count. - **Reversibility:** reversible - a constant in `model`; raising it needs no migration.

### Claude's Discretion

- SQLite schema shape, `user_version` migration, `BEGIN IMMEDIATE` write helper, journal size (research says last 100 rows), alias table layout.
- The lineage walker on public `SessionDB` methods, the fake-`SessionDB` tests, and the `hermes`-marked contract tests.
- Repo layout, pyproject pins, test matrix wiring for 3.11 and 3.14, and the two-process write race test (use `spawn`).

### Deferred Ideas (OUT OF SCOPE)

- Write result contract (compact versus full board) - Phase 2 discuss.
- Tool names and count - Phase 2 discuss.
- Stale-write transport (HTTP 409 versus structured 200) - Phase 3 discuss.
- Archive keeps the board, delete removes it, orphan sweep - Phase 5.
- Reorder items (BORD-01), import from the pane (BORD-02) - v2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOR-01 | Board lives in a plugin-owned SQLite file under `$HERMES_HOME/plugin-data/hermes-session-tasks/`, never in `state.db` | `plugin_db` path and pragmas verified (section "plugin_db facts"). Lineage opens `state.db` with `SessionDB(read_only=True)` only. |
| STOR-02 | Item fields: id, text, checked, parent id, position, created and updated timestamps, last writer | Draft schema v1 (section "Recommended schema"). Timestamps as UTC ISO text with `Z`. |
| STOR-03 | Subtasks, `parent_id` kept so depth can change | Composite foreign key `(root_id, parent_id)` with cascade proven on SQLite 3.53.1. Depth check in the store (D-01). |
| STOR-04 | Board revision. A write to an item changed since the base revision is rejected and returns the current board | Revision rule with the cascade-descendant clause (section "Revision rule"). |
| STOR-05 | Safe concurrent writes from different processes | `BEGIN IMMEDIATE` per write, one connection per operation. 4 processes x 150 writes, no lost write, on 3.11.15 and 3.14.6 (proto run). |
| STOR-06 | Board follows its session through compression and branches | `get_compression_lineage` is the public root primitive, proven against a real `SessionDB` fixture. Branch, delegate and reset behaviour verified. |
| STOR-08 | Markdown round trip with a stdlib renderer and parser | Parser rules for D-02, D-05, D-08, D-09, D-10 and the `#<digits>` escape needed for a lossless round trip. |
| DEV-01 | uv project, ruff, pyright, pytest green on 3.11 and 3.14 | `scripts/check.sh` matrix ran green on both interpreters in 9.6 s (proto). |
| DEV-02 | Tests run without a gateway, including a two-process write test | Spawn test with the worker in a helper module, hard timeouts, `hermes` marker for the checkout. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Source: `/home/theo/local_repo/hermes-session-tasks/.claude/CLAUDE.md` and `~/.claude/CLAUDE.md`. The plan must obey these.

- Tooling: uv, ruff, pyright, pytest. Plugin code runs and is tested on Python 3.11 and 3.14. It imports only the standard library, fastapi and pydantic. Phase 1 imports only the standard library in `plugin/session_tasks/`.
- Structure: small modules with one responsibility each. Plan the module map first. Budgets from `donmor-coding-practices` (module 300 lines soft and 500 hard, function 50, class 150, 5 parameters, nesting 4). No module-level mutable state. Inject dependencies.
- Desktop half: out of scope here (Phase 4).
- `pyproject.toml` stays at the repo root, outside the symlinked `plugin/` dir.
- Never read, write, wrap or replace `todo_list`.
- No secrets are needed. If one is ever needed it comes from Infisical.
- Docs: plain language (ASD-STE100), no em dash or en dash anywhere, spaced hyphen instead.
- Commit identity: Theo Deyle <theo.deyle@donmor.ca>.
- GSD gate: all file changes go through a GSD command (`/gsd-execute-phase` for this phase).
- Deploy rules (symlink, enable, announce restart) belong to Phase 7. Nothing in Phase 1 restarts the gateway.
- Never write to `state.db`. Never use the real `~/.hermes` home in a test (see Pitfall 9).

## Summary

The store and markdown design in CONTEXT.md and `research/ARCHITECTURE.md` stands. This research adds the lineage facts and the toolchain proof that the plan needs. Everything below was run on devpc today.

Eight findings change or sharpen the plan:

1. **Use `SessionDB.get_compression_lineage(session_id)` as the root primitive. Do not write a walker.** It is public, returns `[root, ..., tip]` for a compression chain, `[session_id]` for a branch, delegate, tool or reset child, and `[]` for a missing session. `lineage[0]` is the board key. ARCHITECTURE.md says "write a 15-line walker on public methods"; this method makes that unnecessary. PITFALLS P2 already named it. `get_conversation_root` is the wrong call: it crosses branch, delegate and reset edges.
2. **A branch row stores its parent as the parent's current tip, not the root.** The fork copy must resolve the `_branched_from` id through the same alias and lineage path before it reads the parent's board.
3. **`is_explicit_fork_child` is true for delegate (subagent) children too, not only `/branch`.** 28 of the 30 child rows in the live `state.db` are delegate children. The resolver must tell a branch (`_branched_from` set) from a delegate (`_delegate_from` set). D-06 covers only the branch. The delegate policy is open (Open Question 1).
4. **This box has zero compression-child rows.** `compression.in_place` defaults to true and `~/.hermes/config.yaml` does not set it. The rotating path is a safety net. Only a fixture proves it, and the fixture is easy to build with the real `SessionDB` in a temporary `HERMES_HOME`.
5. **`from hermes_state import SessionDB` fails in a clean uv venv** (missing `ruamel`, and `dotenv` for the event path). `plugins.plugin_storage.plugin_db` does import and run in a clean 3.11 and 3.14 venv. So the real-`SessionDB` contract test must run in a subprocess with the gateway venv Python. The fake-`SessionDB` tests carry the daily load.
6. **The live `/compress` check in CONTEXT.md "Specific Ideas" cannot run in Phase 1.** No tool, no hook registration and no pane exist until Phases 2 and 4. Source reading shows the server re-anchors `session_key` (the `stored_session_id` Desktop receives) to the new `agent.session_id` after a rotation. Whether Desktop's `focusedStoredSessionId` follows is a client question. The resolver makes it moot because tip and root resolve to one board. Move the live check to Phase 2.
7. **Toolchain traps, all hit and fixed in the prototype:** `uv run --python 3.14` replaces `.venv` unless `UV_PROJECT_ENVIRONMENT` is set; pytest `--import-mode=importlib` makes a spawn worker defined in a test module fail to unpickle and the suite hangs; `Queue.get(60)` means `block=60`, not a timeout; pyright needs `extraPaths`; ruff scans `.venv-py*` unless excluded; `requires-python` in STACK.md (`<3.12`) must become `>=3.11,<3.15`.
8. **Python 3.14 differences that touch this phase:** the default multiprocessing start method on Linux is `forkserver` (3.11 uses `fork`); an unclosed `sqlite3.Connection` raises `ResourceWarning` on 3.14 but not on 3.11; the default sqlite3 `datetime` adapter raises `DeprecationWarning`. Run pytest with `filterwarnings = ["error"]` so connection leaks and adapter use fail the suite.

**Primary recommendation:** Build `plugin/session_tasks/` as a stdlib-only package with a connection factory seam, one `BEGIN IMMEDIATE` write path with the per-item revision rule, a lineage resolver over a four-method `SessionReader` Protocol (`get_session`, `get_compression_lineage`, `is_explicit_fork_child`, `close`) backed by `SessionDB(read_only=True)`, and prove it with `scripts/check.sh` on 3.11 and 3.14 plus a `hermes`-marked contract test that runs in the gateway venv.

## Architectural Responsibility Map

This phase has no browser, SSR or CDN tier. The tiers are the plugin's own layers inside the Hermes gateway process.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Item and board rules (caps, depth, sanitise, revision rule) | Core domain (`model`, `store`) | - | Pure Python. No Hermes import. Same code runs for tools, routes and hooks. |
| Persistence and cross-process locking | Database / Storage (plugin SQLite file) | Core `store` | SQLite file lock is the only lock that spans processes. |
| Markdown render and parse | Core domain (`markdown`) | - | Pure functions. The pane never parses markdown. |
| Session id to board key | Core `lineage` over a Hermes adapter | Database (alias table) | Logic is pure over a Protocol. `SessionDB` access sits in one thin adapter. |
| Path and connection to the plugin DB | Hermes adapter (`paths`) | - | `plugin_db` owns WAL, busy timeout and the old-SQLite fallback. |
| Change broadcast | Hermes adapter (`events`) | - | Fire and forget. A failure never fails a write. |
| Test harness and matrix | Dev tooling (uv, pytest, scripts) | - | Runs with no gateway. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`sqlite3`, `dataclasses`, `re`, `json`, `unicodedata`, `multiprocessing` in tests) | 3.11.15 and 3.14.6 (uv-managed, both link SQLite 3.53.1) | The whole Phase 1 runtime | CLAUDE.md: the plugin runtime imports stdlib plus fastapi and pydantic. Phase 1 needs neither fastapi nor pydantic. [VERIFIED: `uv python find 3.11` and `3.14`, then `sqlite3.sqlite_version` printed `3.53.1` on both, run 2026-10-30] |
| `plugins.plugin_storage.plugin_db` (Hermes v0.22.5 checkout) | `bf0203a794` | Opens the plugin DB: WAL, foreign keys, 5000 ms busy timeout | `HA/plugins/plugin_storage.py:36-45`. [VERIFIED: read this session] |
| `hermes_state.SessionDB` (public module `hermes_state`) | same | Read-only lineage lookups: `get_session`, `get_compression_lineage`, `is_explicit_fork_child` | `hermes_state` is on the public import allowlist (`HA/hermes_cli/plugin_validate_private_imports.py:38`, entry `"hermes_constants", "hermes_platform", "hermes_state", "plugins.plugin_storage"`). [VERIFIED: read this session] |
| `hermes_cli.plugin_events.broadcast_plugin_event` | same | Fire and forget `board.updated` event | `HA/hermes_cli/plugin_events.py:66`: `def broadcast_plugin_event(plugin_id: str, event: str, payload: Optional[dict[str, Any]] = None) -> None:`. [VERIFIED: read this session] |

### Supporting (dev dependency group only, never runtime)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 | Tests | Same pin as Hermes (`HA/pyproject.toml:540` `"pytest==9.1.1",`). Latest on PyPI is 9.2.0; keep the Hermes pin on purpose. [VERIFIED: PyPI JSON 2026-10-30] |
| pytest-cov | 7.1.0 | Coverage, house target 80 percent | `--cov=plugin/session_tasks` in the full run. [VERIFIED: PyPI JSON, latest is 7.1.0] |
| ruff | 0.15.10 | Lint and format | Same pin as Hermes (`HA/pyproject.toml:546` `"ruff==0.15.10",`). Latest is 0.17.3; keep the Hermes pin. [VERIFIED] |
| pyright | 1.1.414 | Type check | Latest on PyPI is 1.1.414. [VERIFIED] |
| fastapi 0.133.1, starlette 1.3.1, pydantic 2.13.4, httpx 0.28.1 | pins equal the gateway | Not imported in Phase 1. Pin now so later phases (routes, `TestClient`) need no lock change. | Equal to the `pip list` of `HA/venv` and to the live 3.14 install env. [VERIFIED: `venv/bin/python -m pip list` and `ls .../site-packages` on devpc] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `get_compression_lineage` | Hand walker over `get_session` | More code, same answer. Use the walker only if a Hermes update removes the method; the contract test catches that. |
| Subprocess contract test in gateway venv | Add `ruamel.yaml`, `python-dotenv` and more to the dev group so `hermes_state` imports in-process | Chases Hermes's dependency set and widens the lock. Rejected. |
| `scripts/check.sh` | Nox, tox, CI matrix only | A new tool for a two-version loop. A 10-line script is enough. A GitHub workflow can call the same script in Phase 7. |

**Installation (repo root, bash):**
```bash
uv sync --locked --python 3.11     # dev env, .python-version holds 3.11
./scripts/check.sh                  # full matrix, 3.11 then 3.14
```

**Version verification (run 2026-10-30):** `uv sync` resolved 26 packages and installed `fastapi==0.133.1 pydantic==2.13.4 pydantic-core==2.46.4 pyright==1.1.414 pytest==9.1.1 pytest-cov==7.1.0 ruff==0.15.10 starlette==1.3.1` on both 3.11.15 and 3.14.6 from one `uv.lock`. [VERIFIED: proto run]

## Package Legitimacy Audit

All packages are in the dev group. Nothing is added to the plugin runtime.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| fastapi | PyPI | years | not reported by the seam | github.com/fastapi/fastapi | SUS (too-new, unknown-downloads) | Approved - see note |
| starlette | PyPI | years | not reported | github.com/Kludex/starlette | SUS (too-new, unknown-downloads) | Approved - see note |
| pydantic | PyPI | years | not reported | github.com/pydantic/pydantic | SUS (too-new, unknown-downloads) | Approved - see note |
| httpx | PyPI | years | not reported | github.com/encode/httpx | SUS (unknown-downloads) | Approved - see note |
| pytest | PyPI | years | not reported | github.com/pytest-dev/pytest | SUS (too-new, unknown-downloads) | Approved - see note |
| pytest-cov | PyPI | years | not reported | none listed by the seam | SUS (unknown-downloads, no-repository) | Approved - see note |
| ruff | PyPI | years | not reported | docs.astral.sh/ruff | SUS (too-new, unknown-downloads) | Approved - see note |
| pyright | PyPI | years | not reported | github.com/RobertCraigie/pyright-python | SUS (unknown-downloads) | Approved - see note |

**Seam output:** `gsd-tools.cjs query package-legitimacy check --ecosystem pypi ...` returned SUS for all eight. The "too-new" reason reads the date of the latest release (for example pydantic 2026-10-29), and "unknown-downloads" means the seam has no PyPI download stats. Neither reason points to a slopsquatted name. [VERIFIED: seam run 2026-10-30]

**Note on disposition:** The planner must treat this as one gate, not eight human checkpoints. The evidence that replaces the checkpoint is automatic and already collected: fastapi, starlette, pydantic and httpx are the exact versions installed in the gateway venv and in the live 3.14 install env, and pytest and ruff equal the pins in `HA/pyproject.toml:540,546`. Add one task: after `uv lock`, a script compares `uv.lock` versions to the gateway `pip list`. A mismatch fails the task. That is the `checkpoint:human-verify` substitute. `pytest-cov` and `pyright` are the two names with no Hermes pin; both are long-established (pytest-dev and the Microsoft pyright wrapper) and were confirmed on PyPI. [ASSUMED] that the planner accepts the single automated gate in place of per-package human checkpoints (Assumption A9).

**Packages removed due to SLOP verdict:** none
**Packages flagged SUS:** all eight, see note above.

## Architecture Patterns

### System Architecture Diagram

```
 caller (Phase 2 tool, Phase 3 route, Phase 5 hook; in Phase 1 only tests)
        |  session_id (never empty), actor, base_rev, ops
        v
 +--------------------------------------------------------------+
 | service seam (Phase 2)   -- Phase 1 exposes store + lineage  |
 +--------------------------------------------------------------+
        |                                   |
        | resolve(session_id)               | apply(root_id, ops, actor, base_rev)
        v                                   v
 +-------------------+              +---------------------------+
 | lineage.py        |              | store.py                  |
 |  alias hit -> root|              |  BEGIN IMMEDIATE          |
 |  miss: SessionRdr |              |  revision rule, caps,     |
 |  .get_compression_|              |  depth rule, journal,     |
 |  lineage()[0]     |              |  rev bump, COMMIT         |
 |  branch? fork copy|------------->|  Stale -> current Board   |
 +---------+---------+  fork copy   +-------------+-------------+
           |  (read only)                          |
           v                                       v
 +-------------------+              +---------------------------+
 | SessionDB(        |              | plugin data.db (WAL)      |
 |  read_only=True)  |              |  boards items aliases     |
 |  state.db (never  |              |  changes, user_version    |
 |  written)         |              +---------------------------+
 +-------------------+                            ^
                                                  | connection factory (one per op)
 markdown.py: render(board, include_ids) / parse(text) -> ParseResult (pure)
 paths.py: factory -> plugin_db("hermes-session-tasks")   events.py: publish after commit
```

### Recommended Project Structure

The module map is decided before code (house rule). STACK.md names the shared package `session_tasks`; ARCHITECTURE.md calls it `core`. Use **`session_tasks`**: the name `core` can shadow a Hermes module in tests.

```
hermes-session-tasks/                 # repo root
  pyproject.toml  uv.lock  .python-version  .gitignore   # dev only, outside plugin/
  scripts/check.sh                    # 3.11 and 3.14 matrix
  tests/
    conftest.py                       # hermes_home autouse, hermes marker skip, clock fixture
    race_worker.py                    # spawn workers live HERE, never in a test module
    fakes.py                          # FakeSessionReader
    test_model.py test_markdown.py test_store_*.py test_race.py
    test_lineage.py test_events.py test_paths.py test_layout.py
    test_hermes_contract.py           # marker: hermes
  plugin/                             # symlink target in Phase 7
    plugin.yaml  __init__.py          # Phase 2
    session_tasks/
      __init__.py
      model.py        # Item, Board, ops, errors, caps, sanitize_text      (no I/O)
      markdown.py     # render, parse, ParseResult                          (no I/O)
      schema.py       # DDL string, SCHEMA_VERSION, migrate(conn)
      db.py           # ConnFactory alias, write_txn, open_for(factory)
      store.py        # get_board, apply, Stale/Applied results
      aliases.py      # alias get/put, fork_copy (uses db + store helpers)
      lineage.py      # SessionReader Protocol, resolve(), record_compaction()
      paths.py        # connect() -> plugin_db, connect_path(path) for tests
      events.py       # publish(root_id, rev, actor, broadcast=None)
```

`plugin/` must hold no `pyproject.toml` (Hermes reads one next to `plugin.yaml` as the plugin's dependency list, `STACK.md` "Repo layout"). Guard it with `test_layout.py`.

### Hermes API reference for lineage (all read and run this session)

**`SessionDB` constructor.** [VERIFIED: `HA/hermes_state.py:582`]
```python
    def __init__(self, db_path: Path | None = None, read_only: bool = False):
```
- Default path is `_default_db_path()` at call time: `return DEFAULT_DB_PATH if DEFAULT_DB_PATH != _IMPORT_DEFAULT_DB_PATH else get_hermes_home() / "state.db"` (`HA/hermes_state.py:200-203`). It follows the active profile.
- `read_only=True` calls `self._open_read_only()` (`HA/hermes_state.py:652-653`), which connects with `read_only_db_uri(self.db_path)` = `Path(db_path).resolve().as_uri() + "?mode=ro"` (`HA/hermes_state_holders.py:27-30`, `HA/hermes_state.py:765-770`).
- A missing `state.db` raises `sqlite3.OperationalError: unable to open database file`. [VERIFIED: ran `SessionDB(db_path=Path("/nonexistent-dir-xyz/state.db"), read_only=True)`.] The adapter must catch it and fall back to "root is the session id", with no alias write.
- Close with `close()` (`HA/hermes_state.py:1521`). Always `try/finally`. Cost measured on the live 100 MB `state.db`: open 1.6 ms, lineage 0.5 ms, close 0.3 ms.
- Do not use `hermes_state_registry.acquire`: that module is not on the public allowlist.

**`get_session`.** [VERIFIED: `HA/hermes_state_sessions.py:832`]
```python
    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
```
Returns a dict of all `sessions` columns, or `None`. `model_config` is a JSON **string**. `_session_row_dict` also lifts two markers to top-level keys when present: `data["_reset_from"]` and `data["_branched_from"]` as stripped strings (`HA/hermes_state.py:533-562`). `_delegate_from` is not lifted; it sits only inside the `model_config` JSON. Live check: for a branch row the dict had `parent_session_id`, `_branched_from` equal to the parent, `source: 'desktop'`, `end_reason: None`.

**`is_explicit_fork_child`.** [VERIFIED: `HA/hermes_state_messages.py:1899`]
```python
    def is_explicit_fork_child(self, session_id: str) -> bool:
```
Docstring: `Read-only :meth:`_is_explicit_fork_child_row`; a missing row is not a fork`. The row predicate (`HA/hermes_state_messages.py:1878-1897`) is true when `session.get("source") == "tool"` or the parent id equals `_branched_from` or `_delegate_from` in `model_config` (`_reset_from` only with `include_reset=True`, which the public method does not pass). So it is true for **branch, delegate and tool** children, and false for a reset child.

**`get_compression_lineage`.** [VERIFIED: `HA/hermes_state_compression.py:914`]
```python
    def get_compression_lineage(self, session_id: str) -> list[str]:
        """Return compression ancestors through tip in chronological order."""
```
Behaviour (read at lines 914-948, then run): missing session returns `[]`; an explicit fork child returns `[session_id]`; otherwise it walks up while `_is_compression_child_row` (parent exists and `parent.get("end_reason") == "compression"`, child not an explicit fork or reset fork, `HA/hermes_state_compression.py:906-912`), then walks down to the tip. The last line is `return lineage if session_id in lineage else [session_id]`. `lineage[0]` is the compression root.

**Not to use:** `get_conversation_root` (`HA/hermes_state_messages.py:1745`) returns `chain[0]` of the raw parent walker `_session_lineage_root_to_tip` (`HA/hermes_state_sessions.py:1543`), which crosses branch, delegate and reset edges. `_resume_lineage_ids` (`HA/hermes_state_messages.py:1667`) and `_is_compression_child_row` are private.

**Verified fixture run** (real `SessionDB`, temporary `HERMES_HOME`, gateway venv Python 3.11.16). Rows: `root` (ended `compression`), `comp1` child of `root` (ended `compression`), `comp2` child of `comp1`, `br` child of `comp2` with `{"_branched_from": "comp2"}`, `dg` child of `comp2` with `{"_delegate_from": "comp2"}`, `rs` child of `comp2` with `{"_reset_from": "comp2"}`, `plain`. Output:

| id | `is_explicit_fork_child` | `get_compression_lineage` | `get_conversation_root` |
|----|-------------------------|---------------------------|-------------------------|
| root | False | `['root','comp1','comp2']` | root |
| comp1 | False | `['root','comp1','comp2']` | root |
| comp2 | False | `['root','comp1','comp2']` | root |
| br | **True** | `['br']` | root (wrong for us) |
| dg | **True** | `['dg']` | root (wrong for us) |
| rs | False | `['rs']` | root (wrong for us) |
| plain | False | `['plain']` | plain |
| missing | False | `[]` | missing |

Also confirmed: the `br` row has `parent_session_id = 'comp2'`, the **tip**, not `root`. A read-only `SessionDB(db_path=..., read_only=True)` returns the same lineage. The temporary home passed Hermes's test-isolation guard with `PYTEST_CURRENT_TEST` set (`HA/hermes_state.py:211-220`, `_ensure_test_isolation`), because the path was not a production DB.

### How branch and compression rows look in the live `state.db`

Read with `sqlite3` `mode=ro` through the gateway venv Python on 2026-10-30. Nothing was written.

- The `sessions` table has `id TEXT PRIMARY KEY`, `source TEXT NOT NULL`, `model_config TEXT`, `parent_session_id TEXT`, `ended_at REAL`, `end_reason TEXT`, `title TEXT`, `archived INTEGER NOT NULL DEFAULT 0`, plus `FOREIGN KEY (parent_session_id) REFERENCES sessions(id)`. Ids look like `20261028_143857_b4c720`.
- 99 rows, 30 with a parent. By marker:

| Count | `source` | marker keys in `model_config` | parent `end_reason` | Meaning |
|-------|----------|-------------------------------|---------------------|---------|
| 27 | desktop | `_delegate_from`, `_usage_anchor` | None | delegate child (subagent run shown as a session) |
| 1 | subagent | `_delegate_from`, `_usage_anchor` | None | delegate child |
| 2 | desktop | `_branched_from`, `_usage_anchor` | None or `startup_orphan_reap` | `/branch` child. `_branched_from` equals `parent_session_id`. The parent did **not** end with `branched`. |
| 0 | - | - | `compression` | compression child (none exist here) |

- Branch marker is the stable key `model_config._branched_from` (`HA/hermes_state_sessions.py:131-134` comment and `HA/hermes_state_common.py:171` `_BRANCH_CHILD_SQL`). Compression marker is the **parent's** `end_reason = 'compression'` (`HA/hermes_state_common.py:174` `_COMPRESSION_CHILD_SQL`). Branch creation writes `model_config={'_branched_from': target}` (`HA/hermes_state_mutation_branch.py:79`).
- Do not detect a branch by the parent's `end_reason`. The live rows show it is not `branched`.

### Compression config on this machine

- Default: `"in_place": True,` at `HA/hermes_cli/config_defaults.py:700`. Comment above it: "in_place: compaction rewrites the message list and system prompt WITHOUT rotating the session id (no parent_session_id chain ...)". The agent reads it with `in_place=is_truthy_value(cfg.get("in_place"), default=True),` (`HA/agent/agent_init.py:1584`).
- `~/.hermes/config.yaml` has a `compression:` block (`enabled`, `threshold`, `target_ratio`, `protect_last_n`, ...) with **no** `in_place` key (grep returned nothing). There is no `~/.hermes/profiles/` directory. [VERIFIED: grep and ls this session]
- Effect: the session id does not change on `/compress` on this machine. `post_compaction` arrives with `old_session_id=""`.

### `post_compaction` hook

- Docs (`HA/website/docs/user-guide/features/hooks.md`, section `post_compaction`, lines 1118-1139): signature `def my_callback(session_id: str, kind: str, reason: str, **kwargs):`. `old_session_id` is "The session the compaction started in when it rotated to a new one; `""` when compacted in place." Fires "in the agent loop, in the process that compacted (CLI, TUI and Desktop backends, gateway agents, cron)". Return value ignored. A raising callback is logged and skipped. Callbacks are bounded by `plugins.hook_callback_timeout` (default `"hook_callback_timeout": 30,` at `HA/hermes_cli/config_defaults.py:1733`). [CITED: hooks.md]
- Source: `fire_post_compaction(*, session_id: str, old_session_id: str = "", kind, reason, before_tokens, after_tokens, messages_removed)` calls `invoke_hook("post_compaction", session_id=..., old_session_id=..., ...)` only when `has_hook("post_compaction")` (`HA/agent/compaction_events.py:239-249`). The caller passes `old_session_id=payload["session_id"] if payload["session_id"] != session_id else ""` (`compaction_events.py:253-256`). [VERIFIED: read]
- Narrow callback signatures receive only the fields they name; `**kwargs` callbacks receive all (`HA/hermes_cli/plugins_dispatch.py`, `invoke_hook` docstring: "Payloads evolve additively: ``**kwargs`` callbacks get everything, narrow signatures only what they declare."). So write `def on_post_compaction(session_id: str = "", old_session_id: str = "", **kwargs)`.
- Phase 1 delivers the function the hook calls: `lineage.record_compaction(factory, reader_factory, session_id, old_session_id)`. It does nothing when `old_session_id` is empty or equal to `session_id`. Otherwise it writes `alias(session_id -> root_of(old_session_id))`, where `root_of(old)` is an alias hit, else one `get_compression_lineage(old)[0]`, else `old` itself. Hook registration lands in Phase 2.
- Not verified on a live Desktop: the hook is documented to fire there, but no live run was possible (Finding 6). [CITED: hooks.md; live run deferred to Phase 2]

### Tool `session_id` versus `focusedStoredSessionId` after `/compress`

Read from source this session, not run live.

- Tool side: `handle_function_call(..., session_id=agent.session_id or "", ...)` (`HA/agent/tool_executor.py:1725`). `registry.dispatch(function_name, next_args, **dispatch_kwargs)` with `dispatch_kwargs = {"task_id": ids.task_id, "session_id": ids.session_id}` (`HA/model_tools.py:827-839`). A handler gets `session_id` only if its signature names it: `kwargs = _kwargs_accepted_by(entry.handler, kwargs)` (`HA/tools/registry.py:955-957`). The tool id is the **live** `agent.session_id`.
- Desktop side: `session.info` carries `"stored_session_id": session_key or "",` (`HA/tui_gateway/server.py:1609`). After a manual `/compress` (`HA/tui_gateway/methods_slash.py:420`) and after a turn that auto-compressed (`HA/tui_gateway/prompt_turn.py:879`), `_sync_session_key_after_compress` runs `session["session_key"] = new_session_id` (`HA/tui_gateway/session_compression.py:331`) when `agent.session_id` rotated. So the **server** stored id follows the tip.
- Not determined by reading: whether the Desktop client updates `focusedStoredSessionId` from that `session.info` payload (`HA/apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/session-info.ts`). It also keeps `_lineage_root_id` for the sidebar (`HA/apps/desktop/src/lib/session-branch-tree.ts:46`).
- With `in_place: true` (this machine) there is no rotation, so the two ids are equal. With rotation, the resolver maps tip and root to one board, so the pane and the agent cannot split. **Conclusion for the plan:** write no code that compares the two ids. Resolve both through `lineage.resolve`.

### `plugin_db` facts

[VERIFIED: `HA/plugins/plugin_storage.py:27-45`, `HA/hermes_cli/sqlite_util.py:18-67`, run in clean uv 3.11.15 and 3.14.6 venvs with the checkout on `sys.path`]

```python
def plugin_data_dir(name: str) -> Path:
    from hermes_constants import get_hermes_home
    root = get_hermes_home() / "plugin-data" / _validate_name(name)
    root.mkdir(parents=True, exist_ok=True)
    return root

def plugin_db(name: str, filename: str = "data.db") -> sqlite3.Connection:
    ...
    return open_db(plugin_data_dir(name) / filename, db_label=f"plugin-data/{name}/{filename}",
                   foreign_keys=True, row_factory=None, check_same_thread=False)
```
- Name rule: `^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$`. `hermes-session-tasks` passes.
- Path: `<HERMES_HOME>/plugin-data/hermes-session-tasks/data.db`. The directory is created on call, even for a read.
- Pragmas observed on both Pythons: `journal_mode=wal`, `foreign_keys=1`, `busy_timeout=5000`, `synchronous=2`. `row_factory` is `None` (tuples). `isolation_level` is `''` (legacy transaction control). The connection is **not** closed for you.
- `get_hermes_home()` (`HA/hermes_constants.py:188-195`): "context-local override -> ``HERMES_HOME`` env var -> platform default". It reads the environment on each call: changing `os.environ["HERMES_HOME"]` after import moved `plugin_data_dir` to the new path in a test. Deleting the variable falls back to `~/.hermes`. [VERIFIED: ran it]
- `open_db` goes through `apply_wal_with_fallback` (`HA/hermes_state_wal.py:254`), the only WAL setter that carries the old-SQLite gate. `is_sqlite_wal_reset_vulnerable` (`HA/hermes_cli/sqlite_runtime.py:23-29`) is true unless the version is `< 3.7.0`, `>= 3.51.3`, in `[3.50.7, 3.51.0)` or in `[3.44.6, 3.45.0)`. The system `python3` (3.11.2, SQLite 3.40.1) is vulnerable and drops WAL. Both uv-managed interpreters (SQLite 3.53.1) are not.
- Runtime on the live gateway: the Hermes tools Python `~/.hermes/tools/python-3.14.9+20261021-linux-x64` has SQLite 3.53.1 and start method `forkserver`. [VERIFIED: ran it]

### Recommended schema (v1, `PRAGMA user_version = 1`)

Proven pieces: composite foreign key with `ON DELETE CASCADE` for subtasks and board delete, orphan insert rejected, `CHECK` constraints (run on 3.14.6 with SQLite 3.53.1).

```sql
CREATE TABLE boards (
  root_id        TEXT PRIMARY KEY,
  rev            INTEGER NOT NULL DEFAULT 0,
  next_item_id   INTEGER NOT NULL DEFAULT 1,
  agent_seen_rev INTEGER NOT NULL DEFAULT 0,   -- used from Phase 5; free to carry now
  forked_from    TEXT,                          -- parent root id, set once by the branch copy
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);
CREATE TABLE items (
  root_id    TEXT NOT NULL REFERENCES boards(root_id) ON DELETE CASCADE,
  id         INTEGER NOT NULL,
  parent_id  INTEGER,
  position   INTEGER NOT NULL,
  text       TEXT NOT NULL,
  checked    INTEGER NOT NULL DEFAULT 0 CHECK (checked IN (0, 1)),
  rev        INTEGER NOT NULL,
  updated_by TEXT NOT NULL CHECK (updated_by IN ('agent', 'user')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (root_id, id),
  FOREIGN KEY (root_id, parent_id) REFERENCES items(root_id, id) ON DELETE CASCADE
);
CREATE INDEX items_by_parent ON items(root_id, parent_id, position);
CREATE TABLE aliases (session_id TEXT PRIMARY KEY, root_id TEXT NOT NULL);   -- no FK on purpose
CREATE TABLE changes (
  seq     INTEGER PRIMARY KEY AUTOINCREMENT,
  root_id TEXT NOT NULL REFERENCES boards(root_id) ON DELETE CASCADE,
  rev     INTEGER NOT NULL,
  actor   TEXT NOT NULL CHECK (actor IN ('agent', 'user')),
  op      TEXT NOT NULL,        -- add, text, check, uncheck, remove, forked
  item_id INTEGER,
  text    TEXT,
  ts      TEXT NOT NULL
);
```
Notes:
- A NULL `parent_id` is not checked by the composite key (SQLite `MATCH SIMPLE`), so top-level items work. [VERIFIED: ran it]
- `aliases` has no foreign key because `post_compaction` can alias a root that has no board yet. Phase 5 deletes alias rows with the board.
- `next_item_id` lives on `boards` and is bumped in the same transaction as every insert, so an id is never reused after a delete (D-03).
- Timestamps are UTC ISO 8601 text with `Z` (PITFALLS m1). Take the clock as an injected `Callable[[], str]`. Never bind a `datetime` object: Python 3.12+ raises `DeprecationWarning` for the default adapter (observed on 3.14.6).
- `agent_seen_rev` is carried in v1 because ARCHITECTURE.md already designs it and a column costs nothing now. It is optional (Assumption A5).

### Write path and revision rule

One helper, the same shape that passed the race tests (proto):

```python
@contextmanager
def write_txn(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
```
- Open one connection per operation from the injected factory and close it in `finally`. Run `PRAGMA foreign_keys=ON` before the `BEGIN` (it is a no-op inside a transaction).
- Migrate once per connection: read `PRAGMA user_version` outside the transaction. If it is below `SCHEMA_VERSION`, take `BEGIN IMMEDIATE`, read it again, then apply. If it is above, raise `SchemaTooNew`. Two processes opening an empty file together are safe because the re-check sits inside the write lock.

Revision rule (extends ARCHITECTURE.md; every clause is testable):
1. `boards.rev` rises by 1 per committed write operation. A batch is one operation. Items touched get `rev = new board rev`.
2. `base_rev` is one integer per call. Operations: `AddItem`, `SetText`, `SetChecked`, `RemoveItem`. Add never conflicts (caps and depth can still reject).
3. `SetText`, `SetChecked`, `RemoveItem` on item X are **stale** when `X.rev > base_rev`. A missing X is `not_found`. Both return the current board.
4. `RemoveItem` of a parent P is also stale when **any descendant** has `rev > base_rev`. Without this clause a delete cascades over a subtask the other writer just added or changed.
5. A batch is all or nothing. One stale or invalid operation rolls back the whole batch and returns the current board. The error names the first failing operation.
6. A rejected write leaves `boards.rev` unchanged, writes no journal row, and must not publish an event.
7. `AddItem` with a `parent_id` fails with `DepthExceeded` if the parent has a parent (D-01), or `not_found` if the parent is gone.
8. Caps (D-10): more than 100 items on the board after the batch raises `BoardFull`; text over 500 characters raises `TextTooLong`. Both reject the whole batch. The import helper trims to capacity first and reports the overflow count, so import never trips `BoardFull`.
9. Sanitise text on write inside `model.sanitize_text`: `" ".join(text.split())` (collapses newline, tab, NBSP, U+2028 and U+0085), then drop characters whose `unicodedata.category` is `Cc`, `Cf`, `Cs` or `Co`. Empty after sanitising is `EmptyText`. The function is idempotent, which the round-trip test relies on. (PITFALLS P11 asks for sanitise on write.)
10. Journal: one `changes` row per changed item per operation, pruned to the last 100 rows per board in the same transaction. The fork copy writes one row with `op = 'forked'` and the parent root id in `text` (D-06).

Return type: a frozen dataclass union `Applied(board, rev, changed_ids)` or `Stale(board, reason, item_id)`. Transport (409 versus 200) is a Phase 3 matter and stays out of the store.

### Lineage resolver

```python
class SessionReader(Protocol):          # satisfied by SessionDB and by tests.fakes.FakeSessionReader
    def get_session(self, session_id: str) -> dict[str, Any] | None: ...
    def get_compression_lineage(self, session_id: str) -> list[str]: ...
    def is_explicit_fork_child(self, session_id: str) -> bool: ...
    def close(self) -> None: ...

@dataclass(frozen=True)
class Resolution:
    root_id: str
    kind: Literal["plain", "compression", "branch", "delegate"]
    forked_from: str | None = None       # parent session id for a branch
```
Algorithm for `resolve(factory, open_reader, session_id)`:
1. Reject an empty or non-string `session_id` with `InvalidSession`. Never default to `""`.
2. Alias hit returns `Resolution(root_id, "compression" or "plain")` with no `SessionDB` open.
3. Miss: `reader = open_reader()` in `try/finally`. If it raises `sqlite3.OperationalError` (no `state.db`), return `Resolution(session_id, "plain")` and write no alias.
4. `row = reader.get_session(session_id)`. Missing row: return `Resolution(session_id, "plain")`, write no alias (the row may appear later).
5. `reader.is_explicit_fork_child(session_id)` true: `branched = row.get("_branched_from")`, falling back to `json.loads(row["model_config"]).get("_branched_from")`. A non-empty value means `kind="branch"`, `forked_from=branched`. Otherwise `kind="delegate"` with `root_id` = the root of the `_delegate_from` parent (or of `parent_session_id`). No board is created and nothing is copied for a delegate.
6. Not a fork: `root_id = lineage[0]` from `get_compression_lineage(session_id)`; `kind="compression"` when `root_id != session_id`.

Branch fork copy (D-06). Triggered on the first **touch** of a branch (read or write), inside one `BEGIN IMMEDIATE`:
1. If an alias row or a board row already exists for the branch id, do nothing (idempotent across two racing processes; the second one sees the first one's commit).
2. Resolve the parent: `forked_from` is the parent's **tip**, so call `resolve` on it (recursion with a `visited` set and a depth cap of 20 covers a branch of a branch).
3. If the parent root has no board row, write only the alias `branch -> branch` and stop. Do not create an empty board on a read (PITFALLS P2.4).
4. Else create the branch board with `forked_from = parent_root`, copy items in `(parent_id IS NOT NULL, position, id)` order with **new ids** `1..n` (remap `parent_id`), set `next_item_id = n + 1`, set `rev = 1`, write a journal row `op = 'forked'`, write the alias, commit.

Alias writing rules (to keep the table small, PITFALLS P2 "Warning signs"): write an alias when a board row is first created for a session, and when `kind == "compression"` and the root has a board. A read of a never-written plain session walks every time (about 2.5 ms) and caches nothing.

### Markdown rules

Render (`render(board, *, include_ids: bool) -> str`):
- Top-level: `- [ ] #3 Call John`. Subtask: two spaces then the same form (D-04). `include_ids=False` omits `#<id> ` (clipboard, D-05). Order: top-level by `position`, then each item's subtasks by `position`. Emit `[x]` lowercase. Final newline.
- **Escape rule (needed for "no loss"):** D-05 makes the parser strip a leading `#<digits> `. An item whose own text starts that way (`#3 priority`) would lose its first token on an ids-off round trip. The renderer prefixes a backslash to any text that matches `^\\*#\d+(\s|$)`, and the parser removes exactly one backslash from text that matches the same pattern. This keeps D-05 intact and makes the round trip lossless. With ids on, the id token is stripped first, so the escape is also applied for consistency.

Parse (`parse(text) -> ParseResult`), derived from the pitfall table in `STACK.md` and CONTEXT D-02, D-08, D-09, D-10:
- `text.expandtabs(4)`, split with `str.splitlines()` (handles CRLF).
- Line pattern: `^(\s*)[-*+]\s+(?:\[( |x|X)\]\s+)?(.*)$`. No checkbox means unchecked (D-08). `- [ ]foo` (no space) does not match the checkbox group, so the line is a plain bullet with text `[ ]foo`. Ignore headings, paragraphs and blank lines.
- Strip one leading `#<digits>` plus space, then unescape one leading backslash (above). Sanitise with `model.sanitize_text`. Empty text is skipped and counted in `skipped_empty` (D-09). Text over 500 characters is skipped and counted in `too_long` (never truncated silently, Assumption A4).
- Nesting by indent columns with a stack: pop while the stack top's indent is `>=` the line's indent. Depth is the stack size. Depth 0 is top-level. Depth 1 is a subtask. Depth 2 or more attaches to the nearest top-level item as a subtask and increments `moved` (D-02). A first line that is indented has no parent and becomes top-level.
- Result: `ParseResult(items: tuple[ParsedItem, ...], moved: int, skipped_empty: int, too_long: int)`, with `ParsedItem(text, checked, children)` and an optional `hint_id: int | None` for the stripped id. A separate `plan_import(result, capacity) -> (ops, overflow)` trims to the free capacity (D-10) and reports the overflow count.

### Anti-Patterns to Avoid

- **`get_conversation_root` for the board key.** It crosses branch, delegate and reset edges. A branch would write into its parent's board.
- **Detecting a branch by the parent's `end_reason`.** Live rows show the parent is not `branched`.
- **Reading `state.db` with raw `sqlite3`.** Private schema. Use `SessionDB(read_only=True)`.
- **A `threading.Lock` as the guard.** Several `hermes serve` processes and the gateway share the file (`ARCHITECTURE.md` finding 2).
- **A cached connection, path or `SessionDB`.** Resolve per call; Hermes fixed a descriptor leak from unclosed WAL connections (`STACK.md`, `HA/hermes_cli/sqlite_util.py:3-6`).
- **Spawn workers defined in a test module.** See Pitfall 2.
- **Creating a board on a read.** Reads of an unknown session return an empty board with no row, except the one allowed write: the branch fork copy when the parent has a board.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Compression root lookup | A `parent_session_id` walker | `SessionDB.get_compression_lineage(id)[0]` | Hermes already gates each hop on `end_reason == 'compression'` and excludes fork and reset children. Hand walkers cross boundaries. |
| WAL, busy timeout, old-SQLite fallback | `sqlite3.connect` plus `PRAGMA journal_mode=WAL` | `plugins.plugin_storage.plugin_db` | A raw WAL pragma bypasses the WAL-reset gate and the network-filesystem fallback (`HA/hermes_cli/sqlite_util.py:35-37` docstring). |
| Cross-process locking | File locks, `threading.Lock` | SQLite `BEGIN IMMEDIATE` | The SQLite file lock already spans processes. |
| Schema versioning | A homemade migration table | `PRAGMA user_version` | Atomic with the DDL inside one transaction. |
| Process pool for the race test | Custom `fork` code | `multiprocessing.get_context("spawn")` | Same start method on 3.11 and 3.14. |
| Hypothesis-style generators | A new dependency | A seeded `random.Random(1234)` board generator in the test | CLAUDE.md allows no new dependency. The generator needs about 30 lines. |

**Key insight:** every deceptively hard part of this phase (lineage, WAL, locking) already has a Hermes or SQLite primitive. The plugin's own code is rules and glue.

## Common Pitfalls

### Pitfall 1: `uv run --python 3.14` replaces `.venv`
**What goes wrong:** the project `.venv` flips between 3.11 and 3.14. Each flip reinstalls 24 packages.
**Why:** `uv run --python X` recreates the project environment for that interpreter. [VERIFIED: `.venv/bin/python -V` printed 3.11.15, then 3.14.6 after the run, then 3.11.15 after a plain `uv run`.]
**How to avoid:** one environment per interpreter: `UV_PROJECT_ENVIRONMENT=.venv-py3.14`. `scripts/check.sh` does this. Add `.venv*/` to `.gitignore` (current file has only `.venv/`) and `".venv*"` to ruff `extend-exclude`.
**Warning signs:** `Creating virtual environment` on every run; ruff reports thousands of errors in `.venv-py3.14/`.

### Pitfall 2: a spawn worker defined in a test module hangs the suite
**What goes wrong:** with `--import-mode=importlib` the test module is not importable by name in the child. Unpickling the worker fails in the child, the child exits, the parent waits forever.
**How to avoid:** put every worker function in `tests/race_worker.py` and add `"tests"` to pytest `pythonpath` so the child can import it (spawn passes `sys.path` to the child). Use hard deadlines. [VERIFIED: the first prototype run hung for 5 minutes; after moving the worker it passed in 1.5 s on both versions.]

### Pitfall 3: `Queue.get(60)` is not a timeout
**What goes wrong:** `get(block=True, timeout=None)`. `get(60)` sets `block=60` and waits forever.
**How to avoid:** `q.get(timeout=60)`, `p.join(timeout=30)`, then `p.kill()` in a `finally`. pyright flagged it (`Argument of type "Literal[60]" cannot be assigned to parameter "block" of type "bool"`). [VERIFIED: pyright output]

### Pitfall 4: pyright cannot see pytest's `pythonpath`
**What goes wrong:** `Import "session_tasks.store" could not be resolved`.
**How to avoid:** `[tool.pyright] extraPaths = ["plugin", "tests"]`. Run 3.14 with `pyright --pythonversion 3.14 --pythonpath .venv-py3.14/bin/python`. Lazy Hermes imports carry `# pyright: ignore[reportMissingImports]`; verified that the comment silences exactly that line. [VERIFIED: proto]

### Pitfall 5: `hermes_state` does not import in a clean uv venv
**What goes wrong:** `ModuleNotFoundError: No module named 'ruamel'` (and `dotenv` for `broadcast_plugin_event`, which then logs a warning with a traceback and returns). `plugin_db` is fine.
**How to avoid:** the real-`SessionDB` contract test runs a snippet in `HA/venv/bin/python` as a subprocess and compares JSON. Skip when that Python is absent. Patch `broadcast` in events tests, so the traceback never prints. [VERIFIED: ran in `.venv` and `.venv-py3.14`]

### Pitfall 6: 3.14 start method and warnings
**What goes wrong:** `fork` on 3.11 hides bugs that `forkserver` on 3.14 shows. An unclosed connection is silent on 3.11 and a `ResourceWarning` on 3.14 (`unclosed database in <sqlite3.Connection ...>`). `datetime` binding raises `DeprecationWarning` on 3.12+.
**How to avoid:** `get_context("spawn")` always. `filterwarnings = ["error"]`. Close every connection in `finally`. Store timestamps as text. [VERIFIED: ran on 3.11.15 and 3.14.6]

### Pitfall 7: ruff and E501 and PLW1514
**What goes wrong:** long SQL strings fail `E501`; `PLW1514` (unspecified encoding) is a preview rule and does nothing without preview.
**How to avoid:** house precedent from `time-attendance`: `line-length = 100` and `ignore = ["E501"]`. Enable `PLW1514` with `preview = true` and `explicit-preview-rules = true`. [VERIFIED: a test `open("f")` was flagged, "Add explicit `encoding` argument".]

### Pitfall 8: the branch parent is a tip, and a delegate looks like a fork
**What goes wrong:** the fork copy looks for a board under the tip id and finds none. A delegate child is copied as if it were a branch, or writes a board of its own.
**How to avoid:** resolve `_branched_from` through `lineage.resolve`; classify with `_branched_from` before copying; return `kind="delegate"` and let Phase 2 decide the policy.

### Pitfall 9: a test that touches the real `~/.hermes`
**What goes wrong:** `plugin_data_dir` creates `~/.hermes/plugin-data/hermes-session-tasks/` when `HERMES_HOME` is unset. This happened once during this research and the empty directory was removed by hand.
**How to avoid:** an **autouse** fixture in `tests/conftest.py` sets `HERMES_HOME` to `tmp_path / "hermes-home"` for every test. Never import `SessionDB()` without an explicit tmp path under pytest (Hermes's guard `_ensure_test_isolation` refuses a production `state.db` in a pytest process).

### Pitfall 10: markdown round trip on text that looks like syntax
**What goes wrong:** item text `#3 priority`, `[x] done`, or text with two spaces changes after a round trip.
**How to avoid:** the escape rule above; sanitise is idempotent; the generator test draws texts from a pool that includes `#12 x`, `\#12 x`, `[x] y`, `- z`, tabs, NBSP and 500-character strings.

## Code Examples

### Two-process race test (spawn, hard deadlines)

Verified on 3.11.15 and 3.14.6 with `filterwarnings = ["error"]`: 4 processes x 150 writes released by one barrier, 600 rows, `rev == 600`, 1.4 s.

```python
# tests/race_worker.py  (importable by the spawned child)
def barrier_run(path, tag, barrier, queue):
    barrier.wait(30)
    queue.put(run(path, "root", tag, 150))      # run() calls store.add_item per write

# tests/test_race.py
import multiprocessing as mp
from race_worker import barrier_run

def test_four_processes_released_together_lose_no_write(tmp_path):
    db = str(tmp_path / "data.db")
    ...migrate once, close...
    ctx = mp.get_context("spawn")
    barrier, q = ctx.Barrier(4), ctx.Queue()
    procs = [ctx.Process(target=barrier_run, args=(db, f"p{i}", barrier, q)) for i in range(4)]
    try:
        for p in procs:
            p.start()
        got = [q.get(timeout=60) for _ in procs]
        for p in procs:
            p.join(timeout=30)
            assert p.exitcode == 0
    finally:
        for p in procs:
            if p.is_alive():
                p.kill()
    ...assert 600 rows, board rev 600, ids 1..600 unique...
```
Add a second race for **conflict**: two processes release together and both `SetChecked` the same item with the same `base_rev`. Exactly one gets `Applied`; the other gets `Stale` with the winner's board. This proves STOR-04 across processes. Single-process stale tests stay deterministic and do not use threads.

### pyproject (repo root) - proven shape

```toml
[project]
name = "hermes-session-tasks"
version = "0.1.0"
requires-python = ">=3.11,<3.15"
dependencies = []

[dependency-groups]
dev = ["fastapi==0.133.1", "starlette==1.3.1", "pydantic==2.13.4", "httpx==0.28.1",
       "pytest==9.1.1", "pytest-cov==7.1.0", "ruff==0.15.10", "pyright==1.1.414"]

[tool.uv]
python-preference = "only-managed"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["plugin", "tests"]
addopts = "--import-mode=importlib"
filterwarnings = ["error"]
markers = ["hermes: needs the hermes-agent checkout (HERMES_AGENT_REPO); skipped when absent"]

[tool.ruff]
target-version = "py311"
line-length = 100
extend-exclude = [".planning", ".venv*"]
preview = true

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "ASYNC", "PLW1514"]
explicit-preview-rules = true
ignore = ["E501"]

[tool.pyright]
pythonVersion = "3.11"
include = ["plugin", "tests"]
extraPaths = ["plugin", "tests"]
venvPath = "."
venv = ".venv"
```
Changes against `STACK.md`: `requires-python` widened to `<3.15`; `-m 'not hermes'` dropped from `addopts` (the marker skips by itself when the checkout is absent); `extraPaths` and `tests` on `pythonpath` added; `explicit-preview-rules` added; `E501` ignored. `.python-version` holds `3.11`. Note: `donmor-coding-practices` sets a `>=3.14` baseline for new projects. This project is the recorded exception because Hermes accepts `>=3.11,<3.15` (`HA/pyproject.toml:15`) and the checkout venv is 3.11.16.

### `scripts/check.sh` (bash) - ran green in 9.6 s on both interpreters

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for v in 3.11 3.14; do
  export UV_PROJECT_ENVIRONMENT=".venv-py${v}"
  uv sync --locked --python "$v"
  uv run --python "$v" ruff check .
  uv run --python "$v" ruff format --check .
  uv run --python "$v" pyright --pythonversion "$v" --pythonpath "${UV_PROJECT_ENVIRONMENT}/bin/python"
  uv run --python "$v" pytest -q
done
```

### Gateway-venv contract test (marker `hermes`)

```python
# tests/test_hermes_contract.py (shape)
GATEWAY_PY = HERMES_AGENT_REPO / "venv" / "bin" / "python"
pytestmark = pytest.mark.hermes

def test_lineage_matches_real_sessiondb(tmp_path):
    home = tmp_path / "hh"; home.mkdir()
    env = {**os.environ, "HERMES_HOME": str(home), "PYTEST_CURRENT_TEST": "contract"}
    out = subprocess.run([str(GATEWAY_PY), "-c", FIXTURE_SNIPPET], cwd=HERMES_AGENT_REPO,
                         env=env, capture_output=True, text=True, timeout=90, check=True).stdout
    real = json.loads(out)                      # {id: {"fork": bool, "lineage": [...]}}
    fake = {sid: {"fork": f.is_explicit_fork_child(sid), "lineage": f.get_compression_lineage(sid)} ...}
    assert real == fake                         # the fake used by every other test is pinned to Hermes
```
`FIXTURE_SNIPPET` builds the seven-row fixture above with `create_session` and `end_session` and prints JSON. [VERIFIED: the same calls ran in the gateway venv.] Other `hermes` tests, in process with the checkout on `sys.path` and `HERMES_HOME` on `tmp_path`: `plugin_db` returns `journal_mode=wal`, `foreign_keys=1`, `busy_timeout=5000`, the file lands at `<home>/plugin-data/hermes-session-tasks/data.db`, no `state.db` appears in the home, and `paths.connect_path` (the no-Hermes twin used by default tests) reports the same pragma values.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rotating compression with a `parent_session_id` chain | In-place compaction, same session id | Default `"in_place": True` in the 2026-10-22 checkout | Lineage is a safety net here. No compression child exists on this box. |
| `fork` start method on Linux | `forkserver` default | Python 3.14 | Spawn explicitly. Workers must be importable. |
| Silent unclosed sqlite3 connection | `ResourceWarning` | Python 3.13 and later (seen on 3.14.6) | `filterwarnings = ["error"]` finds leaks. |
| Default `datetime` adapter in sqlite3 | Deprecated | Python 3.12 | Store ISO text. |

**Deprecated or avoid:** `get_conversation_root` for per-conversation keys; `hermes_state_registry`; `_resume_lineage_ids`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A delegate child resolves to the delegator's root with `kind="delegate"`, and Phase 2 decides whether a subagent may write. Phase 1 creates no board and copies nothing for a delegate. | Lineage resolver | Phase 2 tool policy changes; the Phase 1 API already carries `kind`, so no schema change. |
| A2 | A branch of a branch copies through recursion (parent resolved with a visited set, depth cap 20). | Lineage resolver | Without recursion, a branch taken from an untouched branch starts empty. |
| A3 | The 100-item cap counts subtasks (total rows per board). | Revision rule 8 | A cap of 100 top-level items would be a different constant and a different test. |
| A4 | An import line over 500 characters is skipped and counted in `too_long`, never truncated. | Markdown rules | Truncation would be silent data loss. A user might prefer truncation. |
| A5 | `agent_seen_rev` is carried in schema v1 even though Phase 5 uses it. | Schema | If dropped, Phase 5 needs a v2 migration (the framework supports it). |
| A6 | Desktop's `focusedStoredSessionId` follows the rotated stored id. Not verified. | Id equality | None for correctness, because the resolver accepts tip or root. |
| A7 | The `post_compaction` hook fires on a live Desktop backend as `hooks.md` says. Not run live. | `post_compaction` hook | If it does not, the alias is still learned lazily by `resolve`. Slower, not wrong. |
| A8 | The live `/compress` check moves to Phase 2 because no tool or hook exists in Phase 1. | Summary finding 6 | Theo may want a throwaway probe plugin in Phase 1 instead (needs a gateway restart announcement). |
| A9 | One automated pin-versus-gateway comparison replaces eight `checkpoint:human-verify` tasks for the SUS packages. | Package Legitimacy Audit | If the planner or Theo wants a human check, add one checkpoint covering the whole dev group. |
| A10 | Coverage target of 80 percent on `plugin/session_tasks` (house rule in `~/.claude/rules/ecc/testing.md`). | Validation | A lower gate would let untested branches through. |

## Open Questions (RESOLVED)

1. **What does a delegate (subagent) session do with the board?**
   - What we know: 28 of 30 child rows in the live `state.db` are delegate children. `is_explicit_fork_child` is true for them. They carry their own `session_id` in a tool call.
   - What is unclear: whether a subagent may add items to Theo's board.
   - Recommendation: Phase 1 returns `kind="delegate"` and the delegator's root. Phase 2 refuses writes from a delegate with a plain tool error, because the board is Theo's list and not the agent's working plan. State this in the Phase 2 discuss.
   - **RESOLVED (orchestrator decision 1):** a delegate resolves to the delegator's root with kind `delegate`, and Phase 1 stores nothing for it. The write policy for delegates is a Phase 2 tool decision. Plan 01-05 Task 1.
2. **Where does the live `/compress` check run?**
   - What we know: it needs a tool, a hook and a pane. None exists before Phase 2 and Phase 4. Config has `in_place` unset (default true), so a forced `/compress` here proves "same id", not rotation.
   - Recommendation: Phase 2 verification runs the in-place check with the real tool. Rotation is covered by the fixture contract test. Skip a throwaway probe plugin.
   - **RESOLVED (orchestrator decision 2):** the live `/compress` check moves to Phase 2. Phase 1 covers rotation with the `hermes`-marked contract test against a real `SessionDB` (plan 01-05 Task 3). No probe plugin.
3. **Should a read of a branch trigger the fork copy?**
   - What we know: success criterion 3 says a branch "shows its parent's items". D-06 says "the first time the branch touches the board". PITFALLS P2.4 says reads create no row.
   - Recommendation: yes, a read triggers the one allowed write, and only when the parent has a board. If the parent has none, nothing is written.
   - **RESOLVED (orchestrator decision 3):** yes. The first resolve of a branch copies the parent board once, and only when the parent has a board. A parent with no board leads to no write. Plan 01-05 Task 2.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | DEV-01 | yes | 0.11.26 | - |
| CPython 3.11 (uv-managed) | matrix | yes | 3.11.15, SQLite 3.53.1 | - |
| CPython 3.14 (uv-managed) | matrix | yes | 3.14.6, SQLite 3.53.1 | `uv python install 3.14` |
| Gateway Python (checkout venv) | contract test | yes | 3.11.16 at `~/.hermes/hermes-agent/venv/bin/python` | test skips |
| Live gateway Python | reference | yes | 3.14.9 at `~/.hermes/tools/python-3.14.9+20261021-linux-x64`, SQLite 3.53.1 | not used for tests |
| Hermes checkout | `hermes` marker | yes | `bf0203a794` at `~/.hermes/hermes-agent` | tests skip, CI passes |
| Node (pyright wrapper downloads its own) | pyright | yes | cached; first run needs network | - |
| System `python3` | not used | yes | 3.11.2, SQLite 3.40.1, WAL-vulnerable | never use for tests |
| PyPI network | `uv lock` | yes | - | - |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none. No gateway process is needed by any Phase 1 test.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 plus pytest-cov 7.1.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (Wave 0 creates it) |
| Quick run command | `uv run pytest tests/test_<module>.py -q` |
| Full suite command | `./scripts/check.sh` (ruff, format check, pyright, pytest on 3.11 then 3.14) |
| Coverage | `uv run pytest --cov=plugin/session_tasks --cov-fail-under=80 -q` (3.11 env) |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STOR-01 | DB path is `<HERMES_HOME>/plugin-data/hermes-session-tasks/data.db`; no `state.db` created; lineage opens the reader with `read_only=True` | contract (`hermes`) and unit | `uv run pytest tests/test_paths.py tests/test_hermes_contract.py -q` | Wave 0 |
| STOR-02 | Item stores id, text, checked, parent, position, timestamps, `updated_by`; timestamps end in `Z` | unit | `uv run pytest tests/test_store_items.py -q` | Wave 0 |
| STOR-03 | Subtask hangs under parent; depth 2 rejected; parent delete cascades; ids never reused after delete | unit | `uv run pytest tests/test_store_subtasks.py -q` | Wave 0 |
| STOR-04 | Stale write returns `Stale` with the current board; descendant clause; batch is all or nothing; rejected write bumps nothing and writes no journal row | unit | `uv run pytest tests/test_store_revision.py -q` | Wave 0 |
| STOR-05 | 2 and 4 spawned processes write one board, no lost write, ids unique; two processes race one item, exactly one wins | integration (processes) | `uv run pytest tests/test_race.py -q` | Wave 0 |
| STOR-06 | Alias hit, compression chain (tip and mid resolve to root), `record_compaction`, branch fork copy once (two racing resolves), branch of branch, delegate kind, reset gets empty board, missing session and missing `state.db` write no alias | unit with `FakeSessionReader` | `uv run pytest tests/test_lineage.py -q` | Wave 0 |
| STOR-06 | The fake equals the real `SessionDB` on the seven-row fixture | contract (`hermes`) | `uv run pytest -m hermes tests/test_hermes_contract.py -q` | Wave 0 |
| STOR-08 | Round trip with and without ids over fixed cases and 500 seeded random boards; D-02 moved count; D-08 plain bullets and `[X]`; D-09 empty skipped; D-10 overflow and `too_long`; CRLF and tabs; `#12` escape | unit | `uv run pytest tests/test_markdown.py -q` | Wave 0 |
| DEV-01 | Lint, format, types, tests pass on 3.11 and 3.14 | matrix | `./scripts/check.sh` | Wave 0 |
| DEV-02 | Suite runs with no gateway and no network; two-process test present; `plugin/` has no `pyproject.toml`; core imports only stdlib | guard tests | `uv run pytest tests/test_layout.py -q` | Wave 0 |

### How the two-process test runs

- `multiprocessing.get_context("spawn")`. Workers live in `tests/race_worker.py`. `pythonpath = ["plugin", "tests"]` lets the child import `session_tasks` and `race_worker`.
- Each worker opens its own connection through `paths.connect_path(path)` (default tests) per write and closes it. A `Barrier` releases all workers at once. Parent waits with `q.get(timeout=60)` and `p.join(timeout=30)` and kills survivors in `finally`.
- Asserts: row count, `boards.rev` equals the number of operations, ids `1..N` unique, `PRAGMA journal_mode` is `wal`. The conflict race asserts exactly one `Applied` and one `Stale`.
- Wall time about 1.5 s per interpreter.

### Which tests need the Hermes checkout (marker `hermes`)

Only `tests/test_hermes_contract.py`. `tests/conftest.py` skips them in `pytest_collection_modifyitems` when `HERMES_AGENT_REPO` (default `~/.hermes/hermes-agent`) is not a directory, and skips the subprocess test when `venv/bin/python` is missing. The in-process tests insert the checkout on `sys.path` inside a fixture and remove it afterwards. No marker test needs a running gateway. They are not deselected by default, so Theo's runs exercise them and a clean CI machine skips them with a reason.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_<changed module>.py -q` plus `uv run ruff check . && uv run pyright`.
- **Per wave merge:** `./scripts/check.sh`.
- **Phase gate:** `./scripts/check.sh` green and coverage at or above 80 percent before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore` (`.venv*/`), `scripts/check.sh`
- [ ] `tests/conftest.py` (autouse `HERMES_HOME`, `hermes` skip, injected clock, `connect_path` factory fixture)
- [ ] `tests/race_worker.py`, `tests/fakes.py`
- [ ] Every test file named in the map above
- [ ] `plugin/session_tasks/__init__.py` and the module skeletons so pyright has a target
- [ ] The pin-versus-gateway check script (covers the SUS audit note)

Suggested plan slices (for the planner, not a decision): (1) scaffold and matrix, (2) `model` and `markdown`, (3) `schema`, `db`, `store` and the race tests, (4) `paths`, `aliases`, `lineage`, `events` with the fakes, (5) contract tests and the full matrix. Slices 2 and 3 can run in parallel after slice 1.

## Security Domain

`security_enforcement` is on (ASVS level 1, block on high). The phase has no network surface and no secrets.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 3 routes sit behind the gateway auth. |
| V3 Session Management | no | The session id is an input, not a credential. |
| V4 Access Control | partly | Board key comes from the handler `session_id` keyword only (Phase 2). Phase 1 rejects an empty session id with `InvalidSession`. |
| V5 Input Validation | yes | `sanitize_text`, caps (D-10), parameterized SQL only, `CHECK` constraints on `checked`, `updated_by` and `actor`. |
| V6 Cryptography | no | None used. |
| V8 Data Protection | yes | `~/.hermes` is mode `drwx------`, so the plugin data directory (mode 0755) is not world readable. No extra chmod needed. [VERIFIED: `ls -ld`] |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection through item text or session id | Tampering | `?` parameters on every statement. Table and column names are constants. |
| Item text forges a second checklist line or closes a prompt fence | Tampering | Collapse whitespace and strip control and format characters on write. Newlines cannot survive. |
| Model writes to another session's board | Elevation | Phase 2: `session_id` keyword only. Phase 1: `InvalidSession` on empty. |
| Lost update between agent and pane | Tampering | Revision rule and `BEGIN IMMEDIATE`. |
| Writing to `state.db` | Tampering | Only `SessionDB(read_only=True)`, which opens `mode=ro`. A test asserts the constructor argument. |
| Test writes into the real Hermes home | Tampering | Autouse `HERMES_HOME` fixture (Pitfall 9). |

## Sources

### Primary (HIGH confidence) - read or run this session
- `HA/hermes_state.py:200-203, 533-562, 582-660, 731-770, 1521` - `SessionDB` constructor, default path, row dict, read-only open, close.
- `HA/hermes_state_sessions.py:131-134, 832, 1535-1556` - `get_session`, branch marker comment, raw walker.
- `HA/hermes_state_messages.py:1667-1693, 1745-1749, 1878-1897, 1899-1902` - `_resume_lineage_ids`, `get_conversation_root`, `is_explicit_fork_child`.
- `HA/hermes_state_compression.py:882-948` - `get_compression_chain`, `_is_compression_child_row`, `get_compression_lineage`.
- `HA/hermes_state_common.py:171-179` - `_BRANCH_CHILD_SQL`, `_COMPRESSION_CHILD_SQL`, `_RESET_END_REASONS`.
- `HA/hermes_state_mutation_branch.py:79` - branch creation writes `_branched_from`.
- `HA/hermes_state_holders.py:27-30` - `read_only_db_uri`.
- `HA/plugins/plugin_storage.py`, `HA/hermes_cli/sqlite_util.py:18-67`, `HA/hermes_state_wal.py:254`, `HA/hermes_cli/sqlite_runtime.py:23-29`, `HA/hermes_constants.py:188-195`.
- `HA/hermes_cli/config_defaults.py:700, 1733`, `HA/agent/agent_init.py:1584`, `~/.hermes/config.yaml` (no `in_place`).
- `HA/agent/compaction_events.py:239-256`, `HA/hermes_cli/plugins.py:202`, `HA/hermes_cli/plugins_dispatch.py` (`invoke_hook`), `HA/website/docs/user-guide/features/hooks.md:1118-1139`.
- `HA/agent/tool_executor.py:1719-1727`, `HA/model_tools.py:825-839`, `HA/tools/registry.py:950-960`.
- `HA/tui_gateway/server.py:1609`, `HA/tui_gateway/session_compression.py:313-331`, `HA/tui_gateway/methods_slash.py:420`, `HA/tui_gateway/prompt_turn.py:875-881`.
- `HA/hermes_cli/plugin_validate_private_imports.py:20-60` - public import allowlist.
- `HA/hermes_cli/plugin_events.py:36-92`.
- Live `state.db` read with `mode=ro` through the gateway venv: schema and child-row classification.
- Real `SessionDB` fixture run in a temporary `HERMES_HOME` (gateway venv 3.11.16).
- `proto/` runs: uv sync, matrix script, race tests, pyright, ruff, plugin_db and Hermes imports in clean 3.11.15 and 3.14.6 venvs, schema cascade test.
- `~/.claude/skills/donmor-coding-practices/SKILL.md` and `python/architecture.md`; `~/.hermes/plugins/memory-wiki/conftest.py`; `~/.hermes/plugins/agent-importers/pytest.ini`; `~/local_repo/time-attendance/pyproject.toml` (ruff precedent).
- PyPI JSON for pytest, ruff, pyright, pytest-cov (2026-10-30). `gsd-tools package-legitimacy` seam output.

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md`, `STACK.md`, `PITFALLS.md`, `SUMMARY.md` (this repo, written 2026-10-30). Facts in them that this phase depends on were re-verified above, except the Desktop client behaviour.

### Tertiary (LOW confidence)
- Desktop client handling of `session.info.stored_session_id` after a rotation (not read to the end, not run). See A6.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - installed and run on both interpreters, pins equal the gateway.
- Architecture (store, revision rule, lineage): HIGH for lineage and storage mechanics (fixture and race tests ran). MEDIUM for the exact revision rule clauses, which are design and need the planner's tests to harden.
- Pitfalls: HIGH - nine of ten were hit and fixed in the prototype.
- Live Desktop behaviour: MEDIUM - source only.

**Research date:** 2026-10-30
**Valid until:** 2026-11-06 for Hermes facts (the checkout can change on `hermes update`; the contract test is the guard). 30 days for toolchain facts.
