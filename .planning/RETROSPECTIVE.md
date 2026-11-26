# Retrospective

## Milestone: v1.0 - Session task board

Shipped 2026-11-26. 7 phases, 62 plans, 4 quick tasks.

### What Was Built

- A board for each Hermes session in plugin-owned SQLite, which follows the session through compression and branches.
- Agent tools (`board_read`, `board_edit`, `board_sessions`, `board_copy`) and a hook that shows the agent the user's edits.
- A Desktop pane: checkboxes, subtasks, edit, delete, a session picker, a copy from another board, item numbers.
- A public, catalog-ready repo with CI, and an install line for every host.

### What Worked

- One adapter module for each Hermes import. The Hermes storage change of v0.24 needed a change in one file.
- Tests that run with no Hermes, plus probes against the real Hermes source.

### What Was Inefficient

- Each pane update failed on the Desktop machines until 2026-11-26. The cause: Desktop copies the pane from the Hermes on its own machine, and the update steps named only the host.
- The devpc test paths went stale when Hermes moved from its venv to its own Python.
- The plan for the live pass on the Mac and Windows asked for five scripted turns. Theo did the installs on his own and reported the result.

### Patterns Established

- Update: push to `public`, then `hermes plugins update hermes-session-tasks` on each machine with its own Hermes.
- A change in the org repo goes through a pull request.

### Key Lessons

- Read the Desktop source before writing install or update steps for a Desktop machine.
- Probe a new Hermes build before `hermes update` on a host: the plugin API can lose names.
