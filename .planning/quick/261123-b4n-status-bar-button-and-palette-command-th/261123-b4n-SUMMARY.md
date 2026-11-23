---
phase: quick-261123-b4n
plan: 01
status: complete
subsystem: desktop-pane
tags: [desktop, status-bar, palette]
provides:
  - status bar item `Tasks` that reveals the Session tasks pane
  - palette command `Show Session tasks` with the same action
key-files:
  modified:
    - plugin/desktop/plugin.js
    - tests/desktop_pane_harness.mjs
    - tests/test_desktop_plugin.py
    - README.md
---

# Quick task 261123-b4n summary

## What changed

- `plugin/desktop/plugin.js` registers two more contributions after the pane:
  - `show` in `statusBar.right`, order 90: checklist codicon, label `Tasks`, title `Show the Session tasks pane`, toggle label `Session tasks`, variant `action`. A click calls `host.revealPane('hermes-session-tasks:pane')`.
  - `show-command` in the palette: `Show Session tasks`, same action.
- `showPane()` checks `typeof host.revealPane === 'function'` first. A Desktop without it does nothing.
- PLUGIN_VERSION and API_VERSION are unchanged. No route or body changed.
- The harness records every contribution, stubs `Codicon`, `PALETTE_AREA` and `host.revealPane`, and has `select`, `run` and `noReveal`.
- The README names the button and the palette command, and says that the pane's Close still turns the plugin off, and the button with it.

## Verification

- `node --check plugin/desktop/plugin.js` passes.
- `tests/test_desktop_plugin.py`: 44 passed on Python 3.11, with 5 new tests for the button shape, the command shape, both reveal paths and the no-reveal Desktop.
- `scripts/check.sh` stops at its first step on a clean `main` too: `scripts/check_pins.py` reports `ruff pin 0.15.10 but hermes pins 0.15.22`. That drift comes from the Hermes update and is not part of this task. The other gate steps ran by hand on Python 3.11: ruff check, ruff format and pyright are clean, and pytest gives 1145 passed, 25 skipped, 2 failed.
- The 2 failures are `tests/test_catalog_entry.py::test_hermes_validator_accepts_the_entry` and `::test_hermes_loader_gives_the_install_identifier`. They fail the same way on a clean `main`: `/home/theo/.hermes/hermes-agent/venv/bin/python` does not exist on this host.
- Python 3.14: ruff check and pyright are clean, and `tests/test_desktop_plugin.py` plus `tests/test_docs.py` give 63 passed.
- `plugin/README.md` got the same two lines as the root README, so `test_root_readme_starts_with_the_plugin_readme` passes.
- Not tested in a live Desktop: the status bar render and the reveal run only in the node harness.

## Limit

The tab's Close on the only pane of a plugin turns the plugin off (`closeTreePane`, `apps/desktop/src/components/pane-shell/tree/store.ts`). The status bar item unregisters with it.
