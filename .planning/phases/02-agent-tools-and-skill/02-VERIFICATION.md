---
phase: 02-agent-tools-and-skill
verified: 2026-10-31T23:59:00Z
status: gaps_found
score: 8/10 must-haves verified
covered_files:
  - ".planning/phases/02-agent-tools-and-skill/02-01-PLAN.md"
  - ".planning/phases/02-agent-tools-and-skill/02-01-SUMMARY.md"
  - ".planning/phases/02-agent-tools-and-skill/02-02-PLAN.md"
  - ".planning/phases/02-agent-tools-and-skill/02-02-SUMMARY.md"
  - ".planning/phases/02-agent-tools-and-skill/02-03-PLAN.md"
  - ".planning/phases/02-agent-tools-and-skill/02-03-SUMMARY.md"
  - ".planning/phases/02-agent-tools-and-skill/02-04-PLAN.md"
  - ".planning/phases/02-agent-tools-and-skill/02-04-SUMMARY.md"
  - ".planning/phases/02-agent-tools-and-skill/02-05-PLAN.md"
  - ".planning/phases/02-agent-tools-and-skill/02-05-SUMMARY.md"
  - ".planning/phases/02-agent-tools-and-skill/02-06-PLAN.md"
  - ".planning/phases/02-agent-tools-and-skill/02-06-SUMMARY.md"
  - ".planning/phases/02-agent-tools-and-skill/02-07-PLAN.md"
  - ".planning/phases/02-agent-tools-and-skill/02-07-SUMMARY.md"
  - "plugin/__init__.py"
  - "plugin/plugin.yaml"
  - "plugin/session_tasks/__init__.py"
  - "plugin/session_tasks/aliases.py"
  - "plugin/session_tasks/board_tools.py"
  - "plugin/session_tasks/db.py"
  - "plugin/session_tasks/edit_args.py"
  - "plugin/session_tasks/fork.py"
  - "plugin/session_tasks/guard.py"
  - "plugin/session_tasks/hooks.py"
  - "plugin/session_tasks/lineage.py"
  - "plugin/session_tasks/markdown.py"
  - "plugin/session_tasks/model.py"
  - "plugin/session_tasks/paths.py"
  - "plugin/session_tasks/results.py"
  - "plugin/session_tasks/revision.py"
  - "plugin/session_tasks/rows.py"
  - "plugin/session_tasks/schema.py"
  - "plugin/session_tasks/session_reader.py"
  - "plugin/session_tasks/store.py"
  - "plugin/session_tasks/tool_text.py"
  - "plugin/session_tasks/wiring.py"
  - "plugin/skills/board-rules/SKILL.md"
  - "tests/test_board_tools.py"
  - "tests/test_edit_args.py"
  - "tests/test_guard.py"
  - "tests/test_hermes_dispatch.py"
  - "tests/test_hooks.py"
  - "tests/test_register.py"
  - "tests/test_results.py"
  - "tests/test_tool_text.py"
covered_digest: "v4:sha256:e06d0778b633d4515641ff0dd0e2489f89788b4186a983dd7b3479d878cb9e74"
behavior_unverified: 1
overrides_applied: 0
gaps:
  - truth: "The agent keeps its own plan in todo_list (ROADMAP success criterion 4, sentence 2; phase goal sentence 2)"
    status: failed
    reason: "Plan 02-05 own-job run made 0 todo_list calls and 0 board_edit calls. The plan's pass rule needs at least 1 todo_list call. The raw stream own-job.jsonl confirms one terminal call and nothing else. The board boundary half held. The todo_list half was never shown."
    artifacts:
      - path: "plugin/session_tasks/tool_text.py"
        issue: "The rule text exists (description, prompt section, skill) but no live run shows the agent following the todo_list half."
    missing:
      - "A stronger own-job probe: the 02-05 prompt (four counting steps) was solved with one shell call, so it never needed a plan. Re-measure with a job that needs a real multi-step plan, at least 3 runs."
      - "Or a recorded override from Theo that accepts the boundary (zero board writes on an own job) as the intent, because the plugin cannot make the model call todo_list."
deferred: []
behavior_unverified_items:
  - truth: "Under the amended D-17 and D-18, the agent asks on its own initiative, and acts at once when Theo's message names an uncheck, a reword or a bulk change"
    test: "In a fresh Desktop or headless session with items on the board, (a) send a message that names an uncheck, then a reword, then a bulk change, and (b) send a task whose natural step is to drop an item and see whether the agent asks first."
    expected: "(a) Each named change runs at once with confirmed true and no question. (b) The agent asks one plain question before it removes, unchecks or rewords on its own decision."
    why_human: "Only a named remove was measured live under the new text (02-07 turn 4). The 02-05 ask runs measured the old rule. The own-initiative branch has no live run. The hard guard is proven by unit tests, but the question itself is model behaviour."
---

# Phase 2: Agent tools and skill - Verification Report

**Phase Goal:** The agent writes the things Theo must do, decide or remember to the board. The agent keeps its own plan in `todo_list`.
**Verified:** 2026-10-31
**Status:** gaps_found
**Re-verification:** No - initial verification

## Goal Achievement

The first sentence of the goal is achieved: the agent writes Theo's items to the board, the code is real and wired, and the live list rate is 5 of 5. The second sentence ("the agent keeps its own plan in `todo_list`") is not shown by any live run, and the single run built to show it failed.

### Observable Truths

Roadmap success criteria 1 to 5 are the contract. Criteria 4 and 5 are split so each sentence gets its own verdict. Items in the plans that describe the OLD ask rule are judged against amended D-17, D-18 and plan 02-07, as the caller instructed.

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | SC1: the agent reads the board as markdown with ids and the rev, and adds, renames, checks, unchecks and removes items in one call with a list of ops | VERIFIED | `board_tools.py` handlers call `BoardStore.apply`. `tool_text.BOARD_EDIT_SCHEMA` has `ops` with enum add, set_text, set_checked, remove. `tests/test_hermes_dispatch.py` dispatches through the real Hermes registry (passes). Desktop pass 02-06 and 02-07: add, rename, check, remove ran live and the read after /compress held ids and rev. Uncheck is covered by unit tests and the headless `uncheck-a` seed, not by a live Desktop turn. |
| 2  | SC2: no replace-all write exists; every write returns the rev and a one-line summary; a stale write returns the current board | VERIFIED | The schema enum holds four item-level ops only. `grep -rn "replace_all\|\"replace\"" plugin` returns nothing. Live stream `list-1.jsonl`: `{"ok": true, "rev": 1, "summary": "rev 1: added 3 items", "changed": [...]}`. Stale path: `test_stale_write_returns_the_current_board`, `test_stale_result_always_holds_the_current_board`, `tests/test_race.py` (two processes, one applied, one stale). |
| 3  | SC3: the session comes from the handler `session_id`; tool names share one prefix and avoid "todo"; `todo_list` stays untouched | VERIFIED | `board_read` and `board_edit` read only the `session_id` keyword (`board_tools.py`); `test_read_ignores_a_session_id_in_the_arguments` and `test_edit_ignores_a_session_id_in_the_arguments` pass. Names are `board_read` and `board_edit`. `grep todo plugin/session_tasks/*.py` finds the word only inside `tool_text.py`, and only inside the token `todo_list` as a boundary statement (`test_each_description_names_todo_list_once_and_holds_no_other_todo`). No code reads, writes or wraps `todo_list`. |
| 4  | SC4 sentence 1: a live test sends 5 prompts that list things for Theo; in all 5 the agent adds the items to the board | VERIFIED | 02-05 runs list-1 to list-5, each with one `board_edit` add and items on the board. I re-read the raw stream `list-1.jsonl`: `tool_describe` then `board_edit` add of 3 items, result rev 1. Rate 5 of 5. |
| 5  | SC4 sentence 2: the agent keeps its own plan in `todo_list` | FAILED | Run own-job: 0 `todo_list` calls, 0 `board_edit` calls. Raw stream `own-job.jsonl` shows a single `terminal` call and no other tool. The plan's pass rule (`02-05-PLAN.md` line 23 and line 178) needs at least one `todo_list` call, so success criterion 4 is not met as measured. See Gaps Summary for why the probe was weak. |
| 6  | SC4 sentence 3: the tool descriptions carry the rule, so the agent needs no skill load | VERIFIED | `BOARD_EDIT_DESCRIPTION` holds the trigger ("When you list things Theo must do, decide or remember, add them here in the same turn") and the boundary ("Keep your own working plan in todo_list, not here"). `BOARD_READ_DESCRIPTION` holds the boundary. `PROMPT_SECTION_TEXT` repeats both (949 chars, reached a new Desktop session, agent.log line in 02-07). In the list runs the agent called `tool_describe` then `board_edit` with no skill load. |
| 7  | SC5 first part, amended rule: a remove, uncheck or reword of Theo's text is guarded; the agent asks when unsure which item Theo means; Theo's own message that names the change is his answer | VERIFIED | `hooks.py` and `guard.py`: the `pre_tool_call` hook blocks remove, any uncheck, and a reword of an item Theo wrote or touched (CR-01 fix reads the journal through `user_touched_ids`), unless `confirmed` is true; it fails closed on a fault. `block_message`, the schema `confirmed` text, the prompt section and `SKILL.md` all carry the amended rule. Live: unclear-b passed (asked which item); 02-07 turn 4: "Remove the winter tires item from my board" ran `board_edit` remove with `confirmed` true and no question. 444 tests pass. |
| 8  | SC5 first part, own-initiative branch: the agent asks one plain question before it removes, unchecks or rewords on its own decision, and acts at once on a Theo-named uncheck, reword or bulk change | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | The texts are present and the hard guard is tested. No live run measures the own-initiative ask under the new text, and only a named remove was measured at once. The 02-05 ask runs (ask-b, uncheck-b, bulk, reword-b) measured the old rule. 02-07 itself records "Not run live" for the multi-op call under the new rule. |
| 9  | SC5 second part (AGNT-04, ordering): when the agent's work finishes an item, the agent checks it and says so in one line | VERIFIED | Backstop truth with explicit live evidence. `finish-b.jsonl`: the agent ran `search_files`, then `board_edit` `set_checked` item 1 (rev 2, "checked 1 item"), after the work in the same turn, and the reply ends with the line "I checked off board item #1." Single sample, recorded here as observed behaviour, not as a statistical rate. |
| 10 | AGNT-04 (empty case): when the work finishes no board item, the agent checks nothing and writes no done line | VERIFIED | Backstop truth with explicit live evidence. Run own-job: 0 `board_edit` calls, board has no row. Single sample. |

**Score:** 8/10 truths verified, 1 failed (truth 5), 1 present but behavior-unverified (truth 8).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `plugin/plugin.yaml` | name, version, tools and hooks declared | VERIFIED | `hermes plugins validate plugin/` printed "declared tools - matches registrations", "declared hooks - matches registrations", "Validation passed." |
| `plugin/__init__.py` | exports `register` | VERIFIED | Imports `register` from `session_tasks.wiring`. |
| `plugin/session_tasks/wiring.py` | registers both tools, two hooks, prompt section, skill | VERIFIED | `register()` makes 2 `register_tool`, 2 `register_hook`, 1 `register_system_prompt_section`, 1 `register_skill` call. `test_hermes_dispatches_board_edit_guard_hooks_prompt_and_skill` proves it through real Hermes. |
| `plugin/session_tasks/board_tools.py` | `board_read` and `board_edit` handlers | VERIFIED | Substantive: session check, delegate refusal (D-20), parse, apply, stale and error results. |
| `plugin/session_tasks/edit_args.py` | argument parser | VERIFIED | WR-01 fix bounds integers to 0 to 2**63-1. Tests present. |
| `plugin/session_tasks/guard.py`, `hooks.py` | hard guard and `post_compaction` alias | VERIFIED | Real logic, tested. `post_compaction` calls `resolver.record_compaction`; /compress kept the board in the 02-06 Desktop pass. |
| `plugin/session_tasks/results.py` | success, stale and error results | VERIFIED | WR-02 fix counts distinct journaled changes. |
| `plugin/session_tasks/tool_text.py` | schemas, descriptions, prompt section | VERIFIED | Carries trigger, boundary and amended ask rule. |
| `plugin/skills/board-rules/SKILL.md` | bundled skill | VERIFIED | Has trigger, "Keep your own working plan in todo_list", amended ask rule, finish rule, subagent rule. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `__init__.py` | `wiring.register` | import | WIRED | Hermes loads it as the plugin entry (validate: loadable). |
| `wiring.register` | `BoardTools.board_read` / `board_edit` | `ctx.register_tool` | WIRED | Real dispatch test returns the board. |
| `wiring.register` | `hooks.make_pre_tool_call` | `ctx.register_hook("pre_tool_call")` | WIRED | Dispatch test shows the guard blocks an unconfirmed remove. |
| `wiring.register` | `hooks.make_post_compaction` | `ctx.register_hook("post_compaction")` | WIRED | Live /compress kept the same board (02-06). |
| `wiring.register` | skill and prompt section | `register_skill`, `register_system_prompt_section` | WIRED | agent.log line `chars=949` on a new Desktop session; skill loaded in Desktop. |
| `board_tools` | `BoardStore.apply` | actor `agent` | WIRED | Journal rows show actor agent. |
| `BoardTools.after_write` | any listener | default `_no_listener` | NOT_WIRED (by design) | IN-01 to IN-04 review item IN-02. A Phase 3 hook point. It touches no Phase 2 truth. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `board_read` result | board markdown, rev | `BoardStore.get_board` over SQLite `data.db` | Yes - live rev 1 board with 3 items in `list-1.jsonl`; Desktop board read after /compress | FLOWING |
| `board_edit` result | rev, summary, changed lines | `BoardStore.apply` journal entries | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `uv run pytest -q -p no:cacheprovider` | 444 passed in 16.72s | PASS |
| Plugin loads in real Hermes | `env -u HERMES_HOME hermes plugins validate plugin/` | "Validation passed." | PASS |
| Dispatch, register, guard, hooks | `uv run pytest -q tests/test_hermes_dispatch.py tests/test_register.py tests/test_guard.py tests/test_hooks.py` | all passed | PASS |
| Live model rate | read `live-02-05/list-1.jsonl`, `finish-b.jsonl`, `own-job.jsonl` | list-1 adds 3 items; finish-b checks after work; own-job has 1 `terminal` call only | PASS for list and finish, confirms FAIL for own-job |

### Probe Execution

Step 7c: SKIPPED. No `scripts/*/tests/probe-*.sh` file exists and no plan declares a probe. The project gate is `scripts/check.sh`, whose pytest part I ran.

### Requirements Coverage

All nine IDs appear in PLAN frontmatter and in REQUIREMENTS.md under Phase 2. No orphans.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TOOL-01 | 02-01, 02-07 | Agent reads the board as markdown with ids and rev | SATISFIED | Truth 1; dispatch test; Desktop read after /compress. |
| TOOL-02 | 02-02, 02-03, 02-04, 02-06, 02-07 | add, rename, check, uncheck, remove in one call; no replace-all | SATISFIED | Truths 1 and 2. |
| TOOL-06 | 02-01, 02-04 | Session from the handler `session_id`, never the arguments | SATISFIED | Two unit tests plus the Hermes dispatch spoof test for `board_read`. The `board_edit` spoof proof is the unit test and the hook test (noted in 02-SECURITY.md). |
| TOOL-07 | 02-04 | Write returns rev, one-line summary, board content; stale returns the current board | SATISFIED | Truth 2. |
| TOOL-08 | 02-01, 02-03, 02-04 | One prefix, no "todo" in names, never touches `todo_list` | SATISFIED | Truth 3. |
| AGNT-01 | 02-03, 02-05 | Bundled skill says add on list, keep own plan in `todo_list` | SATISFIED as written (the skill says it). The behaviour half is truth 5 and FAILED. REQUIREMENTS.md marks this Complete; that mark rests on the skill text only. |
| AGNT-02 | 02-03, 02-05, 02-06 | Descriptions carry trigger and boundary | SATISFIED | Truth 6; 5 of 5 list rate; prompt section on Desktop. |
| AGNT-03 | 02-02, 02-03, 02-04, 02-05, 02-07 | Ask rule, amended 2026-10-31 | SATISFIED for the guard and the texts; the own-initiative live branch is behavior-unverified (truth 8). |
| AGNT-04 | 02-03, 02-05 | Check the finished item and say so in one line | SATISFIED | Truths 9 and 10, single live samples. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `plugin/**` | - | TBD, FIXME, XXX, TODO, HACK scan | none found | Debt-marker gate passes. |
| `plugin`, `tests`, phase dir | - | em dash or en dash scan | none found | House rule holds. |
| `plugin/session_tasks/board_tools.py` | 26-34 | `after_write` never wired (review IN-02) | Info | Phase 3 hook point. No Phase 2 truth depends on it. |
| `plugin/session_tasks/results.py` | 105-110 | Stale message wrong when `base_rev` is ahead of the board (IN-01) | Info | Open, accepted in 02-REVIEW-DISPOSITION.md. |
| `plugin/session_tasks/tool_text.py` | 35-42, 66 | Ask rule has three hand-written copies; `maxItems` 100 duplicates `MAX_OPS` (IN-03) | Info | Drift risk. |
| `plugin/session_tasks/guard.py` | 37-40 | Unreachable `board is None` branch (IN-04) | Info | Dead defensive code. |

CR-01 (reword guard bypass), WR-01 and WR-02 are fixed in HEAD with test-first commits (6b34185, dfc941d, cf0a0a6, 52459ad, a9913ba, d080e0a). I confirmed the fixed behaviour through the 444-test run.

### Human Verification Required

#### 1. Own-initiative ask and Theo-named changes under the amended rule

**Test:** With items on a board, send three messages that name an uncheck, a reword and a bulk change. Then give the agent a job where it would naturally drop or reword an item without being told.
**Expected:** The three named changes run at once with `confirmed` true and no question. The unprompted case produces one plain question before any remove, uncheck or reword.
**Why human:** Model behaviour. The agent's choice to ask has no unit test, and the only live proof under the new text is one named remove.

### Gaps Summary

One gap blocks the goal as written: the second sentence of the phase goal and of success criterion 4, "the agent keeps its own plan in `todo_list`", is measured as not met.

Facts that bear on the decision:

- The board boundary held. The own-job run wrote nothing to the board, and no code touches `todo_list`.
- The 0 todo_list calls may reflect a weak probe, not a defect in the text. The prompt asked for four counting steps, and the agent did them in one shell command. A task like that does not call for a plan in any tool. The 02-05 SUMMARY itself says a tool search change may not alter the result.
- The text that tells the agent to use `todo_list` for its plan is in the tool descriptions, the prompt section and the skill, so the plugin side is done. Whether the model then calls `todo_list` is outside plugin code.
- The sample is one run. The plan's own pass rule requires the call, so the measured verdict is fail, not uncertain.
- The 02-07 SUMMARY (finding 3) describes this failure as "the agent did not write its own list to the board". That wording is wrong. The failure is zero `todo_list` calls, not a board write.

Recommended closure: re-measure with a job that needs a real plan (for example a task with several files to change and check), at least 3 runs. If the agent still makes no `todo_list` call there, Theo accepts the boundary as the intent through an override. Suggested override text, to be added to this file's frontmatter only by Theo:

```yaml
overrides:
  - must_have: "The agent keeps its own plan in todo_list"
    reason: "The boundary held (zero board writes on an own job) and the plugin cannot make the model call todo_list; the rule text is in descriptions, prompt section and skill."
    accepted_by: "Theo Deyle"
    accepted_at: "<ISO timestamp>"
```

Open for Theo, not a gap: the 02-05 cost question on `tools.tool_search.enabled`. No setting changed.

Process notes with no status effect: 02-VALIDATION.md is `nyquist_compliant: false` with 2 escalated items, which agrees with this report. 02-SECURITY.md reports `threats_open: 0`. The 10 test boards from the live runs stay in the real `data.db` (02-05 decision). Review items IN-01 to IN-04 stay open as Info.

---

_Verified: 2026-10-31_
_Verifier: Claude (gsd-verifier)_
