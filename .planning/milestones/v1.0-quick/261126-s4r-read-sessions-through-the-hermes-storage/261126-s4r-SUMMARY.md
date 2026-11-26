---
phase: quick-261126-s4r
plan: 01
status: complete
subsystem: hermes-adapter
tags: [hermes, storage, compatibility]
key-files:
  modified:
    - plugin/session_tasks/session_reader.py
    - tests/test_adapters.py
    - tests/test_layout.py
---

# Quick task 261126-s4r summary

## What changed

- `session_reader.open_session_reader` uses the Hermes storage interface (`persistence_assembly.open_persistence_reader`) when Hermes has it. An older Hermes keeps the `SessionDB(read_only=True)` path.
- `_StoreReader` gives the six reader methods on the store handle. No other module changed: `lineage.py` and `titles.py` use the same `SessionReader` protocol.
- A missing store raises `sqlite3.OperationalError` on both paths.

## Verification

- Probe against the newest Hermes source (`origin/main` c8f866c, v0.23.4-86, 2026-11-26) in a temporary home: the reader is `_StoreReader`; session row, title, lineage, fork check, first messages and `TitleLookup` return the expected values; a missing store raises `OperationalError`. The same probe shows the old path fails there with the reported `AttributeError`.
- devpc Hermes (v0.23.1): the reader is `SessionDB`, and `is_explicit_fork_child` answers.
- `plugin_db` and `broadcast_plugin_event` import on the newest Hermes.
- `ruff check`, `ruff format --check`, `pyright`: clean. 905 tests passed on Python 3.11 (pane and catalog tests left out); `tests/test_adapters.py` and `tests/test_layout.py` passed on Python 3.14. `hermes plugins validate plugin`: `Validation passed.`
- Not tested on the gateway that reported the error.

## Notes

- `store.lineage.is_fork_child` also answers true for a `tool`-sourced session. The resolver then finds no branch and no delegate marker and keeps the session as its own board.
