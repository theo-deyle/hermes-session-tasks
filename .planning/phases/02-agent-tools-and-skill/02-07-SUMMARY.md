---
phase: 02-agent-tools-and-skill
plan: 07
subsystem: live-test
tags: [hermes-plugin, live-test, desktop, ask-rule, prompt-section, compress]
status: complete

requires:
  - phase: 02-agent-tools-and-skill
    provides: Desktop session 20261031_145115_8eca46 with three agent items, compressed in place, check time 2026-10-31T19:13:57Z (plan 02-06)
provides:
  - Proof that the agent reads the board with ids and the rev after /compress in a Desktop session
  - Proof that the agent renames, checks and removes items on the Desktop path
  - Proof that the board-rules prompt section reaches a Desktop session created after the backend has the plugin (AGNT-02 on Desktop)
  - Live proof of the new ask rule - Theo's explicit instruction is executed at once with confirmed true and no question
  - The finding that Desktop sessions store a NULL system_prompt column
affects: [03-desktop-pane, 04-board-pane, 07-rollout]

actuals:
  tokens: 4500
  tasks: 3
  commits: 0
plan_head_before: ef654845fabdc1cdc8eeab3b43a2ba93050bef5f
plan_head_after: ef654845fabdc1cdc8eeab3b43a2ba93050bef5f

key-files:
  created: []
  modified: []

key-decisions:
  - "The ask rule changed on 2026-10-31 by Theo's decision: Theo's own message naming a change is the permission. The agent asks only on its own initiative or when it is unsure which item Theo means. The guard logic is unchanged; confirmed true now means Theo named this change."
  - "The sessions.system_prompt column is NULL for Desktop sessions (only system_prompt_hash is stored). A check that reads that column reports a false 'section absent'. The agent.log line 'Session plugin prompt section' is the proof of the prompt section on the Desktop path."

requirements-completed: [TOOL-01, TOOL-02, AGNT-03]

coverage:
  - id: D1
    description: "After /compress, the agent read the board with item ids and the rev (success criterion 1 read, tool half of the /compress carry-over)"
    requirement: "TOOL-01"
    verification:
      - kind: other
        ref: "state.db and data.db read by the orchestrator, session 20261031_145115_8eca46 (UI id 53e82110), about 19:15Z: board_read after the 02-06 check time, result held ids and rev"
        status: pass
    human_judgment: false
  - id: D2
    description: "The agent renamed the van item, checked the John item and removed the paint item on the Desktop path (success criterion 1 rename, check and remove)"
    requirement: "TOOL-02"
    verification:
      - kind: other
        ref: "data.db root 20261031_145115_8eca46, final board at 19:15:38Z: #1 checked, #2 renamed to book the van for Saturday, #3 removed; journal add 1, add 2, add 3, text 2, check 1, remove 3, all actor agent"
        status: pass
    human_judgment: false
  - id: D3
    description: "Under the new ask rule the agent removes an item at once when Theo names it, with confirmed true and no question (success criterion 5 on Desktop)"
    requirement: "AGNT-03"
    verification:
      - kind: other
        ref: "data.db root 20261031_191523_093c62: rev 2, no items, changes add 1 then remove 1, both actor agent; board_edit ops [remove item 1], base_rev 1, confirmed true; no question in the reply"
        status: pass
    human_judgment: false
  - id: D4
    description: "The board-rules prompt section reaches a Desktop session created after the backend has the plugin (AGNT-02 on Desktop)"
    requirement: "AGNT-02"
    verification:
      - kind: other
        ref: "agent.log 19:15:28 local: Session plugin prompt section id=hermes-session-tasks.board-rules plugin=hermes-session-tasks position=after_memory chars=949"
        status: pass
    human_judgment: false
  - id: D5
    description: "One board_edit call that renames, checks and removes under the new rule"
    requirement: "AGNT-03"
    verification:
      - kind: other
        ref: "Not run live. The 02-05 headless runs and the unit tests cover the multi-op call."
        status: none
    human_judgment: true
    rationale: "No live Desktop turn sent rename plus check plus remove under the new rule. Recorded as a limit."
---

# Phase 2 Plan 07: Desktop Pass Part 2 Summary

The Desktop agent read the board with ids after /compress, renamed, checked and removed items, and under the new ask rule it removed an item at once on Theo's explicit instruction with no question. The prompt section is proven on a new Desktop session. The orchestrator ran every data check; Theo was asked for messages only.

## Sessions and boards

| Session | Desktop UI id | Board root | Rule in force |
|---------|---------------|------------|---------------|
| `20261031_145115_8eca46` | `53e82110` | `20261031_145115_8eca46` | old ask rule |
| `20261031_191523_093c62` (started 23:15:27Z) | not recorded | `20261031_191523_093c62` | new ask rule |

Local time is UTC minus 4 hours. The Desktop backend for both sessions was `hermes serve` PID 678209 for the first and PID 1013517 (started 19:05:42 local, 23:05:42Z) for the second.

## Turn 1: the original Task 1, old rule, session 20261031_145115_8eca46

Theo sent at about 19:15Z: "Read my board, then rename the van item to book the van for Saturday, check off the John item, and remove the paint supplier item."

- The agent read the board with ids after /compress. This is the tool half of the /compress carry-over check, and the read held ids and the rev.
- The agent applied the rename and the check in one call (rev 2).
- The agent then asked Theo before the remove, although his message named it. After Theo said yes, it removed the paint item (rev 3).
- Final board of that root at 19:15:38Z: #1 "Call John about the quote" checked, #2 "Book the van for Saturday" unchecked. Journal: add 1, add 2, add 3, text 2, check 1, remove 3, all actor agent.

Theo's words: "It removed it, however, it still asked me whether to remove the paint item because I told it that it has to ask before deleting something.... But literally had it in the message to delete it! How much more permission would it need?"

The outcome of the board is correct. The question before the remove was a defect of the rule text, not of the guard.

## Turn 2: Theo's decision, quick task 261031-lbp

Theo changed the rule. Quick task 261031-lbp (commits `acd5390` to `db25d56`, docs commit `ef65484`) reworded D-17 and D-18, the tool text, the prompt section (949 characters), the skill, the guard block message, AGNT-03 and this plan. The new rule: Theo's own message naming the change is the permission. The agent asks only on its own initiative or when it is unsure which item Theo means. The guard logic is unchanged; `confirmed` true now means Theo named this change. 426 tests passed and `hermes plugins validate` passed.

## Turn 3: new backend and a new session

Theo quit and reopened Hermes Desktop. The new backend `hermes serve` PID 1013517 started at 19:05:42 local. Theo's reply: "go".

Theo opened a new Desktop session `20261031_191523_093c62` (started 23:15:27Z) and sent: "Read my board, then uncheck the John item, add 'order the winter tires', and remove the van item."

- That session has its own empty board root. The agent searched tool search for `board_read` and `board_edit` by name and read an empty board.
- The agent added "order the winter tires" as #1 (rev 1). It replied that no John or van item existed to change. It invented no items.
- agent.log at 19:15:28 local: `Session plugin prompt section: id=hermes-session-tasks.board-rules plugin=hermes-session-tasks position=after_memory chars=949`.

Theo's note: "The list is not being shown like the last session." The built-in todo widget above the input is not shown because the agent used the board and not `todo_list`. The board pane is Phase 4. Until then the board has no pane in Desktop.

## Turn 4: the live measure of the new rule

Theo sent: "Remove the winter tires item from my board."

Tool calls in order:

1. `board_read` with args `{}` returned rev 1 with `- [ ] #1 order the winter tires`.
2. `board_edit` with ops `[{"op":"remove","item_id":1}]`, `base_rev` 1, `confirmed` true returned rev 2, "removed 1 item".

Reply (first line): "I removed "order the winter tires" (#1). Your board is empty now." No question was asked.

data.db root `20261031_191523_093c62`: rev 2, no items, changes add 1 then remove 1, both actor agent. Under the new rule an explicit instruction is executed at once with `confirmed` true.

## Plan verify command

The plan Task 3 verify command (agent removes on the newest board, at least 1) holds: the newest board `20261031_191523_093c62` has one agent remove.

## Findings

1. **AGNT-02 on Desktop.** The prompt section reaches a Desktop session created after the backend has the plugin. The agent.log line above is the proof. This closes the 02-06 D2 caveat.
2. **sessions.system_prompt is NULL for Desktop sessions.** Only `system_prompt_hash` is stored. A check that reads the column reports a false "section absent". Use the agent.log line for any prompt section check on a Desktop session.
3. **AGNT-01 own-job rule.** The 02-05 headless run failed the own-job rule (the agent did not write its own list to the board on its own job). That result stays recorded as a measurement. It does not block this plan.

## Deviations from Plan

**1. [Rule 4 - Design change decided by Theo] The ask rule changed during the pass**
- **Found during:** Task 1 (Turn 1)
- **Issue:** Under the old rule the agent asked before a remove that Theo's message already named. Theo judged that more permission than needed.
- **Fix:** Theo decided to change the rule. Quick task 261031-lbp implemented it (commits `acd5390`, `02e1be6`, `f26421d`, `30fb202`, `30ac918`, `db25d56`, `ef65484`). Plan 02-07 and AGNT-03 were aligned to the new rule.
- **Files modified:** plugin text, skill, guard block message, D-17, D-18, AGNT-03 and this plan (all inside the quick task, none inside this plan)
- **Verification:** 426 tests pass; `hermes plugins validate` passes; Turn 4 above is the live proof.

**2. [Process] The orchestrator ran the data checks without `desktop_check.py`**
- **Found during:** Tasks 2 and 3
- **Issue:** The plan wrote a check script with modes `read` and `final`. The orchestrator checked state.db and data.db directly with read-only queries and the agent.log. This summary holds the observed values, not a script JSON object.
- **Fix:** none needed. Every check used read-only opens and wrote nothing.

**3. [Process] The plan's one-turn check was split across two sessions**
- **Found during:** Task 1
- **Issue:** The plan asked for one message that does rename, check and remove under the new rule in the same session after /compress. The rename, check and remove ran under the old rule in the first session. The new rule was proven in a second session with a single remove.
- **Fix:** none. See the limit below.

**Total deviations:** 3 (1 design change decided by Theo, 2 process). **Impact:** all three success criteria hold on Desktop. One combination is not proven live (see Limit).

## Limit

No live Desktop turn sent rename plus check plus remove in one message under the new rule. The first session did rename and check in one call and the remove in a second call after the question (old rule). The new rule was proven with a single remove. The multi-op call under the new rule is covered by the 02-05 headless runs and the unit tests.

## Authentication Gates

None.

## Known Stubs

None. No repo file changed in this plan.

## Threat Flags

None.

## Self-Check

- The SUMMARY holds Theo's words for each turn and the tool call evidence from the orchestrator's checks.
- `git status --porcelain` shows only `.planning/config.json` and `.planning/state.json`, modified before this plan started.
- The commits named above exist in the log (`git log --oneline` shows `acd5390` to `ef65484`).

## Self-Check: PASSED
