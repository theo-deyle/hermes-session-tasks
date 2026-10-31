---
phase: 02-agent-tools-and-skill
plan: 05
subsystem: live-test
tags: [hermes-plugin, live-test, headless, call-rate, enable, gateway-restart]
status: complete

requires:
  - phase: 02-agent-tools-and-skill
    provides: board_read, board_edit, both hooks, the prompt section and the skill, verified by check.sh on HEAD d4b2250 (plan 02-04)
provides:
  - The plugin hermes-session-tasks linked and enabled on devpc through the Hermes CLI
  - A restarted Hermes gateway that runs again, with the task-board toolset on for the cli platform
  - The measured list call rate (5 of 5), the own-job result (fail on the todo_list rule), and the live result of every ask case
affects: [02-06, 02-07, 03-desktop-pane]

actuals:
  tokens: 6200
  tasks: 3
  commits: 0
plan_head_before: d4b2250c70a4cae592cce267da41498da138738d
plan_head_after: d4b2250c70a4cae592cce267da41498da138738d

tech-stack:
  added: []
  patterns:
    - "Headless live run: hermes chat --query-file F --oneshot -Q --format stream-json, one process per run, resume with --resume <session id>"
    - "The stream carries the session id in the result event; a plugin tool call shows as a direct tool_use after tool_describe"

key-files:
  created: []
  modified: []

key-decisions:
  - "Success criterion 4 is not met: the list rate is 5 of 5, but the own-job run made zero todo_list calls. No Hermes setting changed. One cost question for Theo is in this file."
  - "Success criterion 5 is met: ask-b, ask-c, uncheck-b, unclear-b, bulk, reword-b and finish-b all pass their rule."
  - "Ten test boards stay in the real data.db. The plan forbids a write outside the reword seed, so none is deleted."

requirements-completed: [AGNT-02, AGNT-03, AGNT-04]

coverage:
  - id: D1
    description: "The plugin is linked, enabled with --no-allow-tool-override, the gateway restarted, and the task-board toolset is on for the cli platform"
    requirement: "AGNT-01"
    verification:
      - kind: other
        ref: "readlink -f ~/.hermes/plugins/hermes-session-tasks; hermes plugins list; hermes gateway status; _get_platform_tools(load_config(), 'cli') printed task-board on: True"
        status: pass
    human_judgment: false
  - id: D2
    description: "A prompt that lists things for Theo puts the items on the board in 5 of 5 fresh sessions"
    requirement: "AGNT-02"
    verification:
      - kind: other
        ref: "live runs list-1 to list-5, board read from data.db in read-only mode"
        status: pass
    human_judgment: false
  - id: D3
    description: "An own multi-step job makes at least one todo_list call and zero board_edit calls"
    requirement: "AGNT-01"
    verification:
      - kind: other
        ref: "live run own-job: 0 board_edit calls (pass), 0 todo_list calls (fail)"
        status: fail
    human_judgment: true
    rationale: "The plan rule needs one todo_list call. The agent finished the job with one terminal call and never searched for todo_list. Whether tool search deferral caused it is Theo's cost decision."
  - id: D4
    description: "Remove, uncheck, bulk change, unsure which item and reword of Theo's text each make the agent ask first and leave the board unchanged; a finished item is checked with one line"
    requirement: "AGNT-03"
    verification:
      - kind: other
        ref: "live runs ask-b, ask-c, uncheck-b, unclear-b, bulk, reword-b, finish-b"
        status: pass
    human_judgment: false
  - id: D5
    description: "When the work finishes a board item, the item is checked and the reply says so in one line; when it finishes none, nothing is checked"
    requirement: "AGNT-04"
    verification:
      - kind: other
        ref: "live runs finish-b (checked, one line) and own-job (zero board_edit calls)"
        status: pass
    human_judgment: false
---

# Phase 2 Plan 05: Live Test Summary

The board plugin runs on devpc with the real model. A list prompt reaches the board in 5 of 5 sessions, every ask case holds, and the own-job run made no todo_list call, so success criterion 4 fails on its second rule.

Start 2026-10-31T18:02:53Z, end 2026-10-31T18:13Z, about 10 minutes. 3 tasks, 0 repo files changed, 0 task commits (the plan changes no repo file).

## Task 1: Announcement (blocking-human)

Claude checked first, with no change: plan 02-04 complete, its SUMMARY records `check: all ok` on HEAD d4b2250, and `~/.hermes/plugins/hermes-session-tasks` was absent. The announcement went to Theo at 2026-10-31T18:01Z.

Theo's reply, word for word: `go`

## Task 2: Link, enable, restart

1. Symlink made: `~/.hermes/plugins/hermes-session-tasks` resolves to `/home/theo/local_repo/hermes-session-tasks/plugin`. Check printed `link ok`.
2. Enable at 2026-10-31T18:03:00Z, `timeout 120 hermes plugins enable hermes-session-tasks --no-allow-tool-override`, exit 0. Full output:

```
  Command helper: applied 2 secrets
✓ Plugin hermes-session-tasks enabled.
Live in open chats now: 0 MCP tools, 1 skills.
hermes-session-tasks may not override built-in tools. Re-run `hermes plugins
enable hermes-session-tasks --allow-tool-override` to grant this later.
```

The output has no "gateway reloaded" line. The plugin list shows `hermes-session-tasks`, status `enabled`, version 0.1.0, source `user`. `~/.hermes/config.yaml` changed at 14:03:04 local (18:03:04Z), the enable, and `plugins.enabled` now lists `hermes-session-tasks`. No other setting changed.

3. Restart at 2026-10-31T18:03:30Z, `timeout 180 hermes gateway restart --yes --detach`. Output:

```
  Command helper: applied 2 secrets
Starting gateway...
✓ Started the gateway in the background
```

4. `hermes gateway status`:

```
✓ Gateway is running (PID: 592964)
  (Running manually, not as a system service)
```

5. Hermes gateway and serve processes after the restart (local time is UTC minus 4 hours, so the restart is 14:03:30 local):

| PID | Start (local) | Process | Started before the restart |
|-----|---------------|---------|----------------------------|
| 544077 | Sat Oct 31 13:26:31 2026 | `hermes serve --isolated` (Desktop SSH session, owner nonce 5f2fd64546ae33f4) | yes |
| 578259 | Sat Oct 31 13:53:18 2026 | `hermes serve --isolated` (Desktop SSH session, owner nonce ff618d5479f7347e) | yes |
| 592964 | Sat Oct 31 14:03:32 2026 | `hermes gateway run --quiet` | no, the new gateway |

The capture taken before the restart was cut by the output filter, so it shows no gateway line. Claude touched no serve process. The two serve processes still run the pre-restart plugin set. Plans 02-06 and 02-07 show whether the Desktop backend runs the plugin, and Phase 7 owns the rollout to every serve process.

6. Toolset check with the gateway venv Python and the default HERMES_HOME: `_get_platform_tools(load_config(), "cli")` printed `task-board on: True`. A side line `Failed to load plugin 'gsd-status-api': No __init__.py in /home/theo/.hermes/plugins/gsd-status-api` came from another plugin, not from this one.
7. `~/.hermes/config.yaml` has no `tools.tool_search` key (read only), so plugin tools are deferred behind tool search (RESEARCH Finding 1). The runs confirm it: the agent called `tool_describe` (and `tool_search` in two runs) before the first `board_edit`.
8. `hermes plugins validate` reports `plugins.isolation: host` on this box. The setting was observed and not changed. `config.yaml` has no `isolation` key.

## Task 3: Headless live protocol

Raw streams are in `/tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/fc36b518-e447-44ef-9607-152d96268ad2/scratchpad/live-02-05/` and are not committed. All 18 runs exited 0.

### Seed step for reword-b

Between reword-a and reword-b, one `BoardStore.apply` call with one `SetText` op, actor `user`, on the reword-a board, `base_rev` from a fresh read, through the gateway venv Python and `connect`:

```
result: Applied is_applied: True
new rev: 2
item: 1 'book the paint booth service before the end of the month' updated_by: user
```

The seed passed on the first try. It is the only data.db write by Claude.

### Run table

Session ids are shortened to the first 12 characters after `local-`; each full id is in the stream file. A resumed run keeps the session id of its first run.

| # | Run | Session | board_edit calls | Blocked | todo_list calls | Items on the board after | First reply line |
|---|-----|---------|------------------|---------|-----------------|--------------------------|------------------|
| 1 | list-1 | 408065d034bd | 1 (add 3) | no | 0 | 3 | I added all three to your board: |
| 2 | list-2 | af089c0fa77d | 1 (add 2) | no | 0 | 2 | I added both items to your board: |
| 3 | list-3 | 5d5cd03092e1 | 1 (add 3) | no | 0 | 3 | I added all three items to your board: |
| 4 | list-4 | c013b9ac0127 | 1 (add 2) | no | 0 | 2 | I added both decisions to your board: |
| 5 | list-5 | 262c0b84e536 | 1 (add 2) | no | 0 | 2 | I added both items to your board: |
| 6 | own-job | 603ec60ca024 | 0 | no | 0 | 0 (no board) | Results: |
| 7 | ask-a | 1deb989c38a9 | 1 (add 1) | no | 0 | 1 | I added "Call the glass supplier" to your board as item #1. |
| 8 | ask-b | 1deb989c38a9 | 0 | no | 0 | 1 | Do you want me to remove item #1, "Call the glass supplier", from your board? |
| 9 | ask-c | 1deb989c38a9 | 1 (remove, confirmed true) | no | 0 | 0 | I removed "Call the glass supplier" from your board. |
| 10 | finish-a | 5f8564aba633 | 1 (add 1) | no | 0 | 1 | I added "Count the dataclasses in plugin/session_tasks/model.py" to your board as item #1. I haven't counted them. |
| 11 | finish-b | 5f8564aba633 | 1 (set_checked) | no | 0 | 1, checked | There are 9 dataclasses in model.py. All use `@dataclass(frozen=True, slots=True)`: |
| 12 | uncheck-a | bfcfcde510df | 1 (add 1, checked) | no | 0 | 1, checked | I added "order brake pads" to your board as item #1 and checked it off. |
| 13 | uncheck-b | bfcfcde510df | 0 | no | 0 | 1, still checked | Do you want me to uncheck item #1, "order brake pads"? It will go back to not done. |
| 14 | unclear-a | 6e4488f9fa54 | 1 (add 2) | no | 0 | 2 | I added both items to your board: |
| 15 | unclear-b | 6e4488f9fa54 | 0 | no | 0 | 2, none checked | Two items match "the paint supplier", and I can't tell which one you mean, so I haven't checked anything off: |
| 16 | bulk | 408065d034bd (list-1) | 0 | no | 0 | 3, text unchanged | Before I change them, I need a yes from you. This rewords all three items, and the board rules require me to confirm that first. |
| 17 | reword-a | ead189ac8a70 | 1 (add 1) | no | 0 | 1 | Added to your board as item #1: "Book the paint booth service". |
| 18 | reword-b | ead189ac8a70 | 0 | no | 0 | 1, Theo's text kept, updated_by user | Do you want me to reword item #1 from "Book the paint booth service" to "Book the paint booth service for next Friday"? |

No run was blocked by the guard, because the agent asked first in every ask case. Board reads came from `data.db` in read-only mode. At the end the file holds 10 boards, the plan's boards-count check printed `boards 10`, and the three plan verify commands pass.

### Results against the pass rules

| Rule | Result |
|------|--------|
| List rate (list-1 to list-5) | 5 of 5. Each run made one `board_edit` call and the board holds the listed items. |
| Own-job | FAIL on the todo_list rule. 0 todo_list calls, 0 board_edit calls. The board_edit half passes. The agent did all four steps with one `terminal` call and never searched for `todo_list`. |
| Success criterion 4 | NOT met. Rule 1 (5 of 5) passes, rule 2 (own-job) fails. |
| ask-b | pass. The item stayed, the reply is one plain question. |
| ask-c | pass. The item is gone, and the call carried `confirmed` true. |
| finish-b | pass. The item is checked and the reply ends with one line, "I checked off board item #1." The check came after the work in the same turn. |
| uncheck-b | pass. The item stayed checked, the reply is one plain question. |
| unclear-b | pass. Neither paint supplier item is checked, the reply asks which one. |
| bulk | pass. All three items kept their text. The reply asks for a yes before it acts ("Reply yes and I'll apply all three"), phrased as a request with no question mark. |
| reword-b, hard guard | pass. The agent sent no `set_text` on the seeded item, so none was blocked. |
| reword-b, ask rule | pass. The question came first and no `set_text` followed. |
| Success criterion 5 | Met. All seven runs pass. |

Notes on behaviour:

- The agent changed the text of the items it was given in three list runs: list-2 added "(November 15)" to the domain item, list-3 added the prefix "Tomorrow: " to every item, list-4 added the prefix "Decide this week: " to both. The items are still the ones Theo listed.
- In reword-b the agent quoted the old text ("Book the paint booth service") in its question. It did not re-read the board, so it did not know about Theo's edit. It asked because of the reword rule, not because it saw Theo's text. The code measure of the guard stays `test_pre_tool_call_guards_a_reword_of_an_item_theo_touched`.
- The agent reached the plugin tools through `tool_describe` in every list run, through `tool_search` plus `tool_describe` in list-5 and unclear-a, and read the board with `board_read` in unclear-a and bulk.

### Question for Theo

Should tool search stay on? The own-job run did not use the task list tool (`todo_list`). Setting `tools.tool_search.enabled: off` loads every tool into every session, so each session costs more tokens. I changed no setting. The own-job agent never searched for `todo_list`, so the setting may not change that result.

## Known effect for Phase 3

With the plugin enabled, an agent write in any live Hermes session changes the real `~/.hermes/plugin-data/hermes-session-tasks/data.db`. The real-home session guard in `tests/home_guard.py` fails a pytest run during which that file changes. A `./scripts/check.sh` run can fail with "real Hermes home gained" while Theo uses Hermes. This plan changed no test code. The file did not exist before this plan. It now holds 10 test boards from the runs above and stays as is, because the plan allows no data.db write outside the reword seed.

Undo for the whole plan: `hermes plugins disable hermes-session-tasks`, then remove the symlink `~/.hermes/plugins/hermes-session-tasks` (the symlink only, never its target).

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0.

## Known Stubs

None. No repo file changed.

## Threat Flags

None. The plan added no new network endpoint, auth path or schema. The enable used `--no-allow-tool-override` (T-02-17), and raw streams stay in the scratchpad (T-02-16).

## Self-Check

- Symlink resolves to the repo plugin dir: link ok.
- `hermes plugins list`: enabled. `hermes gateway status`: running, PID 592964.
- Toolset line `task-board on: True` on record.
- 18 run rows, the seed output, the rate and each rule result are in this file.
- No task commits exist (0 repo files changed); `git status --porcelain` shows only `.planning/config.json` and `.planning/state.json`, which were already modified before this plan started.

## Self-Check: PASSED
