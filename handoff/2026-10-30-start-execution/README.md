# Handoff: start phase 1 execution

Date: 2026-10-30. Written by Hermes for Theo's own Claude Code session.

## Where the project is

- The project, research, requirements (43 v1 items) and a 7-phase roadmap are committed in `.planning/`.
- Phase 1 (core, storage and session identity) is discussed and planned. It has 6 plans in
  `.planning/phases/01-core-storage-and-session-identity/`. The plan checker passed after 2 revision rounds.
- No code exists yet. Execution has not started.
- `main` is at the last planning commit. Nothing runs in the background: the Hermes tmux session
  `session-tasks` and its watcher are stopped.

## Start

```
cd ~/local_repo/hermes-session-tasks
claude --model claude-fable-5-1 --effort high
```

Then run:

```
/gsd-execute-phase 1
```

## Phases after phase 1

Use discuss before plan on every phase.

1. Core, storage and session identity (planned, ready to execute)
2. Agent tools and skill
3. REST router and client install check (a placeholder pane on the Mac and the Windows PC)
4. Pane
5. Agent sees Theo's edits
6. Cross-session boards (can run in parallel with phase 5)
7. Deploy and hardening

## Decisions already made

Source: `hermes-session-tasks-brief.md` and `.planning/PROJECT.md`.

- The board is separate from the built-in Hermes `todo_list` tool. Do not read, write or wrap `todo_list`.
- One board per session. The pane has a session picker. The agent can read or copy items from another
  session's board. A global board is a v2 idea.
- The pane opens on the right side, stacked with the other right-side panes.
- v2, not v1: reordering items, and pasting a markdown list into the pane. The agent can still add a list
  you paste in chat.
- The devpc symlink delivers only the Python half. A copy script installs `desktop/plugin.js` on the Mac
  and the Windows PC. The pane shows a banner when its version does not match the backend.

Phase 1 discuss answers (all the recommended options, recorded in `01-CONTEXT.md`):

- One subtask level only. Deeper pasted lines move up to the subtask level, and the count is reported.
- Each item has a per-board number that is never reused, shown to the agent as `- [ ] #3 Call John`.
  Your clipboard copy has no numbers.
- A branched session starts with a copy of the parent board, taken the first time the branch uses it.
  After that the two boards change separately.
- A plain bullet becomes an unchecked item. Headings and paragraphs are ignored. Limits: 100 items and
  500 characters per item.

## Things to know

- The Hermes gateway runs Python 3.11. The plans test on 3.11 and 3.14.
- Enabling the plugin on devpc needs a gateway restart (phase 7). That drops open Desktop connections,
  so announce it first. Plugin backend routes mount only when `hermes serve` starts.
- Use `hermes config set` or `hermes plugins enable` for `~/.hermes/config.yaml`. Never edit it by hand.
