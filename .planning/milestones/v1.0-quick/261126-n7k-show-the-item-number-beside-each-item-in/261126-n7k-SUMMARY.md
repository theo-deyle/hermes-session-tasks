---
phase: quick-261126-n7k
plan: 01
status: complete
subsystem: desktop-pane
tags: [desktop, pane]
key-files:
  modified:
    - plugin/desktop/plugin.js
    - tests/test_pane_view.py
---

# Quick task 261126-n7k summary

## What changed

- Each saved row of the pane shows the item number (`#3`) to the right of the item text. It is the item id, the same number the agent uses.
- The number is 10px, in the tertiary text colour, with tabular digits. A text selection skips it. A row that is not saved yet shows no number.
- Two comments are one line each now, so the file stays at the 1400 line ceiling.

## Verification

- `node --check plugin/desktop/plugin.js` passes.
- `ruff check`, `ruff format --check` and `pyright`: clean.
- The pane tests (`tests/test_desktop_plugin.py`, `tests/test_pane_*.py`): 213 passed on Python 3.11.
- `hermes plugins validate plugin`: `Validation passed.`
- Not seen in a live Desktop.

## Findings outside this task

- `scripts/check.sh` stops at its pin check: the repo pins ruff 0.15.10 and Hermes v0.23.1 pins 0.15.22.
- Two tests in `tests/test_catalog_entry.py` fail because `~/.hermes/hermes-agent/venv/bin/python` no longer exists.
