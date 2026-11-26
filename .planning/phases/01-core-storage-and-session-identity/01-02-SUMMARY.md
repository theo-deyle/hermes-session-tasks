---
phase: 01-core-storage-and-session-identity
plan: 02
subsystem: storage
tags: [sqlite, schema-v1, lineage, alias-table, markdown, tracer]

requires:
  - phase: 01-01
    provides: uv toolchain, check.sh matrix, test harness, FakeSessionReader and FakeReaderFactory
provides:
  - Schema v1 (boards, items, aliases, changes) with a user_version migration and SchemaTooNew
  - BoardStore.get_board and BoardStore.apply (top-level AddItem path, one BEGIN IMMEDIATE transaction)
  - SessionResolver.resolve with alias lookup, compression walk and alias write
  - markdown.render for the agent view and the clipboard view
  - paths.connect (Hermes plugin_db) and paths.connect_path (test twin)
  - conftest fixtures connect, store and resolver_for
affects: [01-03, 01-04, 01-05, phase-2]

plan_head_before: 371da4e2fc4f6a1aaeecf7a1bbe0ff3864dc83fa
plan_head_after: 78985738af3720b8fb17583e2180cd1a9826e54c

actuals:
  tokens: 7900
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "One connection per operation: open_db is a context manager that migrates and always closes"
    - "Every write runs in write_txn (BEGIN IMMEDIATE, COMMIT, guarded ROLLBACK) on an autocommit connection"
    - "Alias row and board row are created in the same write transaction"

key-files:
  created:
    - plugin/session_tasks/model.py
    - plugin/session_tasks/db.py
    - plugin/session_tasks/schema.py
    - plugin/session_tasks/rows.py
    - plugin/session_tasks/aliases.py
    - plugin/session_tasks/store.py
    - plugin/session_tasks/markdown.py
    - plugin/session_tasks/lineage.py
    - plugin/session_tasks/paths.py
    - tests/test_tracer.py
  modified:
    - tests/conftest.py

key-decisions:
  - "clean_text measures the 500 character cap on the sanitised text, because that is the stored text."
  - "An empty op batch returns Applied with the current rev and writes nothing, so no board row appears."
  - "SessionResolver.resolve opens the data file on every call, so an alias miss on a new file runs the migration (DDL only, no rows)."

patterns-established:
  - "Core modules use relative imports and no module-level mutable state (frozenset constants only)"
  - "Tests build the store and resolver from the shared fixtures, never in the test module"

requirements-completed: [STOR-01, STOR-02, STOR-06, STOR-08, DEV-02]

coverage:
  - id: D1
    description: "A session id resolves to a board root, an AddItem write lands in SQLite and the board renders as agent markdown (with id) and clipboard markdown (no id)"
    requirement: STOR-01
    verification:
      - kind: integration
        ref: "tests/test_tracer.py#test_plain_session_write_reads_back_as_agent_and_clipboard_markdown"
        status: pass
    human_judgment: false
  - id: D2
    description: "A compression tip reads the root board, and a known tip resolves through the alias table with no reader"
    requirement: STOR-06
    verification:
      - kind: integration
        ref: "tests/test_tracer.py#test_compression_tip_reads_the_root_board"
        status: pass
      - kind: integration
        ref: "tests/test_tracer.py#test_compression_tip_resolves_through_the_alias_after_the_first_walk"
        status: pass
    human_judgment: false
  - id: D3
    description: "First write creates the board row and alias row in one transaction; a rejected batch leaves no row"
    requirement: STOR-02
    verification:
      - kind: integration
        ref: "tests/test_tracer.py#test_first_write_creates_the_board_row_and_the_alias_row_in_one_transaction"
        status: pass
    human_judgment: false
  - id: D4
    description: "Blank, whitespace and non-string session ids raise InvalidSession; an unknown root reads an empty board and creates no row"
    requirement: STOR-01
    verification:
      - kind: unit
        ref: "tests/test_tracer.py#test_blank_or_non_string_session_id_raises_invalid_session"
        status: pass
      - kind: unit
        ref: "tests/test_tracer.py#test_unknown_root_reads_empty_board_and_creates_no_rows"
        status: pass
    human_judgment: false
  - id: D5
    description: "Migration is idempotent, a newer file raises SchemaTooNew, timestamps are UTC text ending in Z, the file runs in WAL mode"
    requirement: DEV-02
    verification:
      - kind: unit
        ref: "tests/test_tracer.py#test_migrate_twice_changes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_tracer.py#test_newer_schema_raises_schema_too_new"
        status: pass
      - kind: unit
        ref: "tests/test_tracer.py#test_written_timestamps_are_utc_text_ending_in_z"
        status: pass
      - kind: unit
        ref: "tests/test_tracer.py#test_data_file_runs_in_wal_mode"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-10-30
status: complete
---

# Phase 1 Plan 02: First end to end path and alias table Summary

**A session id now reaches a SQLite board through the resolver and store, and comes back as markdown in the agent view (`- [ ] #1 Call John`) and the clipboard view (`- [ ] Call John`), with known sessions routed through an alias table that opens no reader.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-30T23:17:48Z
- **Completed:** 2026-10-30T23:21:30Z
- **Tasks:** 2
- **Files modified:** 11 (10 created, 1 modified)

## Accomplishments

- Schema v1 and the `user_version` migration. `migrate` re-reads the version inside the write lock, so two processes that open an empty file together apply the DDL once. A newer file raises `SchemaTooNew` and stays unchanged.
- `BoardStore.apply` handles a batch of top-level `AddItem` ops in one `BEGIN IMMEDIATE` transaction. Item ids come from `boards.next_item_id` and start at 1 (D-03). Text goes through `clean_text`. Every timestamp is UTC text that ends in `Z`.
- `sanitize_text` maps whitespace to a space, drops categories Cc, Cf, Cs and Co, then collapses runs. Checked by hand: a man-ZWJ-woman emoji is stored as its two parts, a single emoji is unchanged, and a second pass changes nothing.
- `SessionResolver.resolve` reads the alias first (no reader on a hit), walks `get_compression_lineage` on a miss, and writes the alias only for a compression tip whose root has a board. A plain session with no board writes no alias.
- Shared fixtures `connect`, `store` and `resolver_for` for the wave 3 plans.

## Task Commits

1. **Task 1 RED** - `2b338b7` (test): end to end test file. Red summary line: `ERROR tests/test_tracer.py ... Interrupted: 1 error during collection` (`ImportError: cannot import name 'paths'`).
2. **Task 1 GREEN** - `72f2930` (feat): model, db, schema, rows, store, markdown, lineage, paths. 12 passed.
3. **Task 2 RED** - `23cfeb8` (test): fixtures and alias tests. Red summary line: `4 failed, 12 passed`.
4. **Task 2 GREEN** - `7898573` (feat): aliases, store alias write, resolver alias lookup. 16 passed.

**Plan metadata:** the docs commit that holds this file, STATE.md, ROADMAP.md and REQUIREMENTS.md.

## Test Results

- `uv run pytest tests/test_tracer.py -q`: 16 passed (plan floor: 14).
- `./scripts/check.sh`: `check: python 3.11 ok`, `check: python 3.14 ok`, `check: all ok`. 35 tests per interpreter, ruff, format and pyright clean. No `real Hermes home gained` line.
- Tracer gate (`HUMAN_VERIFY_MODE=end-of-phase`, automated verify only): re-ran the tracer tests after Task 1, they passed, and expansion continued.

## Decisions Made

- The 500 character cap counts the sanitised text, not the raw input. A raw string of blanks gives `EmptyText`, not `TextTooLong`.
- An empty ops batch returns `Applied(board, board.rev, ())` and writes nothing. Plan 01-03 can keep or change this when it adds the revision rule.
- `BoardFull` and the journal prune (`JOURNAL_KEEP`) are not applied here. Plan 01-03 owns both.

## Deviations from Plan

None - plan executed exactly as written.

The commit trailer uses `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, the attribution line from the harness, as plan 01-01 did. The dispatch prompt named `Claude Fable 5.1`. This is a message trailer only and changes no file.

## Issues Encountered

- A first draft of `store.py` held a stub helper that raised `NotImplementedError`. I removed it before the first commit. No committed code carries it.

## Known Stubs

None. `BoardStore.apply` raises `NotImplementedError` for `SetText`, `SetChecked`, `RemoveItem` and a parent on `AddItem`. This is the plan's stated boundary. Plan 01-03 replaces that branch. `SessionResolver` has no fork, delegate, missing-row or missing-state.db handling. Plan 01-05 adds it.

## Threat Flags

None. No new network endpoint, auth path or file access beyond the plugin SQLite file the plan names. T-01-01 (`?` parameters only), T-01-02 (sanitise), T-01-03 (`InvalidSession`) and T-01-05 (`SchemaTooNew`) are implemented and tested.

## Next Phase Readiness

- Plan 01-03 can add the revision rule to `BoardStore._apply` and `rows.py` (update, delete, count, prune).
- Plan 01-04 adds the markdown escape rule and the parser to `markdown.py`.
- Plan 01-05 adds `fork.py`, `session_reader.py` and the lineage branch, delegate and missing-state handling.
- Code review item: no module caches a connection, a path or a reader. Every open sits in a context manager or `try/finally`. `filterwarnings = error` on Python 3.14 found no `ResourceWarning`.

## Self-Check: PASSED

- Created files exist: model.py, db.py, schema.py, rows.py, aliases.py, store.py, markdown.py, lineage.py, paths.py, tests/test_tracer.py.
- Commits found in HEAD history: 2b338b7, 72f2930, 23cfeb8, 7898573.
- Commit order check: the oldest 01-02 commit is `test(01-02)`.
- All acceptance greps exit 0. `./scripts/check.sh` ended with `check: all ok`.

---
*Phase: 01-core-storage-and-session-identity*
*Completed: 2026-10-30*
