---
phase: 05-agent-sees-theo-s-edits
verified: 2026-11-02T17:00:00Z
status: passed
score: 4/4 roadmap success criteria verified (plus all plan truths checked)
covered_files:
  - .planning/phases/05-agent-sees-theo-s-edits/05-01-PLAN.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-01-SUMMARY.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-02-PLAN.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-02-SUMMARY.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-03-PLAN.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-03-SUMMARY.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-04-PLAN.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-04-SUMMARY.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-05-PLAN.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-05-SUMMARY.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-06-PLAN.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-06-SUMMARY.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-07-PLAN.md
  - .planning/phases/05-agent-sees-theo-s-edits/05-07-SUMMARY.md
  - plugin/plugin.yaml
  - plugin/session_tasks/board_tools.py
  - plugin/session_tasks/delta.py
  - plugin/session_tasks/hooks.py
  - plugin/session_tasks/rows.py
  - plugin/session_tasks/store.py
  - plugin/session_tasks/tool_text.py
  - plugin/session_tasks/wiring.py
  - tests/live/delta/delta_live.py
  - tests/test_hermes_session_delete.py
  - tests/test_hermes_thirty_turn.py
  - tests/test_pre_llm_hook.py
  - tests/test_session_delete.py
covered_digest: "v4:sha256:2b228d70980660938edf1c85fc4ac878c4e54c895069a689362188ef2d597adc"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 5: Agent sees Theo's edits - Verification Report

**Phase Goal:** The agent knows what Theo changed on its next turn, at a small token cost. A board lives and dies with its session.
**Verified:** 2026-11-02T17:00:00Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After Theo edits in the pane, the next agent turn carries a short note listing only those changes. | VERIFIED | Code: `hooks.make_pre_llm_call` calls `store.unseen_changes` (Theo rows only, `actor = 'user'`, `rev > agent_seen_rev`), then `delta.delta_note`. Unit test `test_a_theo_edit_in_the_pane_reaches_the_next_turn_once` through `BoardApi.edit`. Live (05-05): the stored user row of a real-model turn held exactly `added #1 Call John` and `added #2 Book the van`; a later check gave `checked #1` only. |
| 2 | A turn with no change since the agent last saw the board gets no injected text. | VERIFIED | `unseen_changes` returns None when `rev <= agent_seen_rev` or no board row; hook returns None and writes nothing. Agent-only changes give None. Live: e2e-3 user row note null; quiet arm of the token test had no note on any of 30 runs. The Phase 3 per-turn nudge and full-board block are gone (`nudge.py` deleted, no `NUDGE`/`board_block` in `plugin/`). |
| 3 | Note stays within about 1000 chars; token cost at turn 30 vs a no-plugin session equals the size of the notes. | VERIFIED | `DELTA_MAX_CHARS = 1000`; over the cap or an uncovered journal gap gives the one-line pointer. Boundary tests at exactly 1000 and 1001. Real-Hermes 30-turn contract test (`test_hermes_thirty_turn.py`) shows char diff = sum(note + 2). I re-derived the live numbers from the raw `edits-/quiet-/bare-N.jsonl` files in `~/.cache/hermes-session-tasks/token-arms`: turn 30 per-turn input tokens 29066 / 28775 / 28259, so notes = 291, plugin fixed cost = 516, sum = 807. Matches the 05-07 SUMMARY. Largest live note 172 chars. Token ratio 0.368 per char (band 0.15 to 0.5). |
| 4 | Hermes delete removes the session's board; archive keeps it. | VERIFIED | `hooks.make_on_session_delete` returns at once for `reason == "archive"`; otherwise `store.delete_boards(ids)` (boards by exact root id, alias rows by id, chunked, one write txn), registered in `wiring.py` and listed in `plugin.yaml`. `test_hermes_session_delete.py` drives the real `SessionDB` delete, chain delete (`deleted_ids` of two ids) and archive paths. Live (05-07): archived chat kept its board (rev 2); four deleted chats had board null and no alias row; board count 25 to 21. |

**Score:** 4/4 roadmap truths verified. No truth is behavior-unverified; every transition and ordering truth has a passing test (seen rules, gap rule, delegate no-mark, archive-keeps).

### Plan truths and prohibitions (spot checks of the code, not the SUMMARY)

| Item | Status | Evidence |
|------|--------|----------|
| D-35 line forms, tag, `<` escape, 1000 cap, pointer line | VERIFIED | `delta.py` read in full; `test_delta.py` covers each op, fence escape, 1000/1001 boundary. |
| Gap rule `count < JOURNAL_KEEP or oldest_rev <= seen_rev` | VERIFIED | `store.unseen_changes`; tests for exactly 100 rows above and at seen rev. |
| Seen never moves down; an agent batch advances only when seen equalled the pre-batch rev | VERIFIED | `rows.mark_seen` (`agent_seen_rev < ?`), `rows.advance_seen` (`agent_seen_rev = ?`), called in `store._apply` for actor agent only. Prohibition "no seen mark hides an unseen Theo change" backed by `test_agent_edit_after_a_theo_edit_keeps_the_theo_change`. |
| `board_read` and stale reply mark seen; delegate does not | VERIFIED | `board_tools.py`; prohibition "delegate never marks delegator seen" backed by tests. |
| D-36 nudge and board block dropped | VERIFIED | grep: none left. Own-plan gate re-run live with the prompt section as the only carrier: 3 of 3 (05-05); 05-06 correctly took "branch none". |
| D-37 archive does nothing; other reasons remove; never raises | VERIFIED | `hooks.py` read; bad-payload and store-fault tests. A blank or non-string `reason` removes nothing (plan 05-04 chose this; D-37 text says "every other reason", Hermes always sends one). |
| Live tools and test homes: no secret, no other board touched (test-tier prohibitions) | VERIFIED | `test_live_delta.py` passes (hermes-marked tests ran, no skips). |
| Judgment prohibitions (05-05, 05-07 no foreign session changed; 05-06 question) | VERIFIED (judgment) | 05-07 records dry runs, the read-only id check and board counts 25 to 21 (exactly 4). 05-06 asked no question (gate passed). Low risk; flagged only as judgment-tier. |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `plugin/session_tasks/delta.py` | VERIFIED | 60 lines, pure, used by hooks. |
| `plugin/session_tasks/hooks.py` | VERIFIED | `make_pre_llm_call`, `make_on_session_delete` real, registered in `wiring.py`. |
| `plugin/session_tasks/store.py`, `rows.py` | VERIFIED | `unseen_changes`, `mark_seen`, `delete_boards`, `advance_seen`, `prune_changes` real SQL. |
| `plugin/session_tasks/nudge.py` | REMOVED as planned | file absent. |
| `tests/live/delta/{theo_edit,delta_live,make_home}.py` | VERIFIED | present, tested, used for the live record. |

### Key Links

| From | To | Status |
|------|----|--------|
| `wiring.register` | `hooks.make_pre_llm_call`, `make_on_session_delete` | WIRED (`register_hook` lines; `plugin.yaml` lists both). |
| `hooks.pre_llm_call` | `store.unseen_changes` / `delta.delta_note` / `store.mark_seen` | WIRED |
| `BoardTools.board_read`, stale `board_edit` | `store.mark_seen` | WIRED |
| Hermes `hermes sessions delete` | plugin `on_session_delete` | WIRED, proven live and by real `SessionDB` snippet. |

### Data-Flow Trace

The note is built from the `changes` journal rows written by the pane write path (`BoardApi.edit`, actor user). Live record shows the real stored user row holding the text. FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 5 tests (hook, delta, seen, delete, 30-turn, dispatch, tools, register, live tools) | `uv run --python 3.11 pytest -q -rs` on 10 files | 158 passed, no skips | PASS |
| Full suite on Python 3.11 | `uv run --python 3.11 pytest -q -rs` | 832 passed, no skips (includes Phase 1 to 4 regression) | PASS |
| Plugin gate | `hermes plugins validate plugin/` | "Validation passed." | PASS |
| Raw token arithmetic | python over `token-arms/*-29/30.jsonl` | 291 / 516 / 807 as claimed | PASS |
| `arms-report.json` | read | `pass: true`, all 8 checks true | PASS |

I did not restart the gateway, run headless chats, or delete or archive any session.

### Probe Execution

No probe scripts declared. Skipped.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
|-------------|--------------|--------|----------|
| AGNT-05 | 05-01, 05-02, 05-03, 05-05, 05-06, 05-07 | SATISFIED | Truths 1 to 3 above. |
| STOR-07 | 05-02, 05-04, 05-07 | SATISFIED | Truth 4 above. |

No orphaned requirement: REQUIREMENTS.md maps only AGNT-05 and STOR-07 to Phase 5, and both appear in plan frontmatter. Both are marked Complete.

### Anti-Patterns Found

None. No TBD/FIXME/XXX in phase files. The one "TODO" hit is test input text in `tests/test_tool_text.py`. No em or en dash in the phase files.

### Decisions D-35, D-36, D-37

All honored. D-36's contingency (reminder line) was not needed because the re-gate passed 3 of 3 with the prompt section alone.

### Notes (not gaps)

1. The first judge run of the token test failed the ratio check because the tool read session totals as per-turn counts (05-07 deviation). The fix is in the test tool only (`per_turn_tokens`), the first report is kept beside the new one, and I re-derived the per-turn figures from the raw files independently. The fix is sound.
2. Token counts come from the provider's `tokens.input` field. The system prompt length was not stored for one-shot sessions (report holds null); this does not affect the three measured numbers.
3. A fixed plugin cost of 516 tokens per turn exists (tool schemas and prompt section). It is reported, and the roadmap criterion concerns the note difference.

### Human Verification Required

None.

### Gaps Summary

No gaps. The agent receives only Theo's unseen changes as a capped note, quiet turns inject nothing, the token cost matches the note size in measured data, and Hermes delete removes a board while archive keeps it.

---

_Verified: 2026-11-02T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
