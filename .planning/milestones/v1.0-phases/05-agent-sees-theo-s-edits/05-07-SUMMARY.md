---
phase: 05-agent-sees-theo-s-edits
plan: 07
subsystem: live-test
tags: [hermes-plugin, live-test, token-test, archive, delete, cleanup, AGNT-05, STOR-07]
status: complete

requires:
  - phase: 05-agent-sees-theo-s-edits
    provides: the live tools (05-02), the delete hook (05-04), the four test sessions (05-05), the reminder decision (05-06)
provides:
  - SC3 live - three measured token numbers over 30 turns with the real model, against a no-plugin session
  - SC4 live - an archived chat keeps its board, a deleted chat loses its board
  - Every test chat, test board, test home and test gateway of the phase is gone
affects: []

actuals:
  tokens: 1200
  tasks: 3
  commits: 1
plan_head_before: d7a52c80db399f4789f3aabe5c8ef75ad6ff4014
plan_head_after: 8d9a2e0e68294a1049f0717b62b31bce91637624
commits: 1

tech-stack:
  added: []
  patterns:
    - "The result event of a headless run holds the session total of input tokens. Judge per turn by taking the difference between runs."

key-files:
  created:
    - .planning/phases/05-agent-sees-theo-s-edits/05-07-SUMMARY.md
  modified:
    - tests/live/delta/delta_live.py
    - tests/test_live_delta.py

key-decisions:
  - "Token counts in the judge are per turn (difference between runs). The session total stays in the report as session_total_input_tokens."

requirements-completed: [AGNT-05, STOR-07]

coverage:
  - id: D1
    description: "SC3 live: over 30 turns the note adds 291 input tokens per turn at turn 30 for 790 characters, the plugin itself adds 516 per turn, and no note sits on a quiet or bare run"
    requirement: AGNT-05
    verification:
      - kind: e2e
        ref: "delta_live.py arms (90 headless turns), arms-report.json pass true"
        status: pass
    human_judgment: false
  - id: D2
    description: "SC4 live: the archived chat keeps its board; the four deleted chats have board null and no alias row; the board count fell from 25 to 21"
    requirement: STOR-07
    verification:
      - kind: e2e
        ref: "hermes sessions archive --yes, hermes sessions delete --yes, delta_live.py rows"
        status: pass
    human_judgment: false

duration: 23min
completed: 2026-11-02
---

# Phase 5 Plan 07: Token test, archive and delete, cleanup Summary

**The token test with the real model shows the plugin costs 516 input tokens per turn and Theo's notes add 291 more at turn 30 (5 notes, 780 characters), and on Theo's real Hermes an archived chat keeps its board while a deleted chat loses it.**

## Performance

- **Duration:** 23 min (2026-11-02T16:12Z to 16:35Z)
- **Tasks:** 3
- **Files modified:** 2 (the token judge and its tests, one fix)

## Task 1: second restart

no second restart needed

05-06-SUMMARY.md holds `hooks.py changed: no`. The gateway PID stayed 799352 from the start to the end of this plan.

## Task 2: token test

Test homes: two twin homes from `make_home.py` (key names only printed). Home with the plugin: `claude-subscription-directsdk-experimental` and `hermes-session-tasks`. Bare home: the model provider only. No secret file, no key and no Infisical step was used. Both probes exited 0 with a result event and the text `ok`. `hermes plugins list` showed the board plugin enabled in the plugin home and absent in the bare home.

Port check after the probes: exit 0, no clash.

| Home | Listener |
|------|----------|
| test home with plugin | 127.0.0.1:50603 |
| test home bare | 127.0.0.1:49285 |
| real gateway | 0.0.0.0:8644, 127.0.0.1:47773, [::]:8644 |

Arms: `arms --runs 30`, about 7 minutes. Sessions: edits `local-65da0f2a4ea8...`, quiet `local-6aadb166f026...`, bare `local-2adf4e5be585...`. All three sessions lived in the test homes, which are removed.

### Checks

| Check | Result |
|-------|--------|
| reminder_runs_match | true |
| notes_only_on_edit_runs | true (runs 5, 10, 15, 20, 25) |
| every_note_within_cap | true (largest 172 characters, cap 1000) |
| user_char_diff_equals_notes | true (790 = 780 + 5 x 2) |
| token_growth_ratio_in_band | true after the fix below, 0.368 tokens per character (band 0.15 to 0.5) |
| bare_arm_has_no_note | true |
| fixed_user_chars_match_reminder | true |
| fixed_cost_positive | true |

### The three measured numbers

| Number | At turn 1 | At turn 30 (that turn alone) | Session total after 30 turns |
|--------|-----------|------------------------------|------------------------------|
| Notes size (edits minus quiet) | 0 | 291 tokens for 790 characters (780 characters of notes plus 2 per note) | 4741 tokens |
| Plugin fixed cost (quiet minus bare) | 516 tokens | 516 tokens | 15480 tokens (516 x 30) |
| Sum against the no-plugin session (edits minus bare) | 516 tokens | 807 tokens (516 + 291) | 20221 tokens |

Session totals of input tokens: edits 857549, quiet 852808, bare 837328. The plugin session with Theo's edits used 2.4 percent more input tokens in total than the session without the plugin.

Code-derived fixed cost, next to the measured one: `PROMPT_SECTION_TEXT` 960 characters, `json.dumps` of the two tool schemas 398 + 2359 characters, `SKILL_DESCRIPTION` 103 characters. Total 3820 characters, divided by 4 gives about 955 tokens per turn. No reminder text exists any more (`NUDGE_LINE` removed in 05-06). The measured fixed cost is 516 tokens, 54 percent of the estimate: characters divided by 4 overstates JSON and the tool schema text, and the model provider may carry the skill description outside the counted input. The system prompt length in state.db was not stored for the one-shot sessions (the report holds null for both homes).

SC3 line: At turn 30 the session with Theo's edits used 807 more input tokens in that turn than the session without the plugin: 516 for the plugin itself (measured) and 291 for the notes (780 characters in 5 notes, largest 172). Over all 30 turns the total is 20221 more input tokens: 15480 for the plugin and 4741 for the notes, because each note stays in the history and each later turn sends it again.

SC3 reading (as the plan required): the no-plugin arm is the twin bare home. Quiet minus bare is the plugin alone. Edits minus quiet is the notes. Edits minus bare is their sum. The cost of the three arm sessions: edits 0.1053 USD, quiet 0.1016 USD, bare 0.1016 USD, total 0.3085 USD (Claude subscription).

### Cleanup of the token test

`stop_test_gateway` report: both homes `stopped`. `hermes gateway status` named no running gateway for either home. Links removed first with `find -type l -delete` (the plugin links and the uv cache links under each home, targets untouched, both plugin directories checked afterwards), then `rm -rf` of both homes after the path check. Neither home exists. The real gateway PID is 799352 before the probes, after the probes and after the arms.

## Task 3: archive and delete on the real home

Read-only session check, before any change: all four ids have source `oneshot` and a start time after the 05-05 restart (15:56Z). Board count before: 25.

Archive: the live note session `local-3f176b25ba38...` (board rev 2) got the title `hst-p5-archive-0e5fbcff`. The first dry run listed no session (the chat counted as open: "1 matching session still open"). The second dry run with `--include-open` listed exactly that one session. The real run with `--yes --include-open` archived 1 session. `rows` still showed the board: rev 2, agent_seen_rev 2. Archive keeps the board.

Delete (`hermes sessions delete <id> --yes`), then `rows`:

| Session id | Source | Had board | Board after delete | Cost USD (read before) |
|------------|--------|-----------|--------------------|------------------------|
| `local-3f176b25ba38...` (archived first) | oneshot | yes, rev 2 | null | 0.4161 |
| `local-1088e52556fb...` | oneshot | yes, rev 2 | null | 0.1329 |
| `local-814f492ba6e3...` | oneshot | yes, rev 2 | null | 0.1258 |
| `local-c387390becf8...` | oneshot | yes, rev 2 | null | 0.1683 |

Board count after: 21 (25 minus 4). The alias table holds no row for any of the four ids. Cost of the four test chats: 0.8431 USD. With the three token arm sessions (0.3085 USD) the plan cost 1.1516 USD (Claude subscription).

Final gate lines: `./scripts/check.sh` ended `check: python 3.14 ok` and `check: all ok` (832 passed on 3.11), after the fix commit. `hermes plugins validate plugin/` ended `Validation passed.`

Test sessions deleted: the four ids above. No other id was deleted or archived.

## Deviations from Plan

**1. [Rule 1 - Bug] The token judge read session totals as per-turn counts**
- **Found during:** Task 2, first arms run (exit 1)
- **Issue:** One check failed: `token_growth_ratio_in_band`, ratio 6.0 (4741 tokens for 790 characters). The result event holds the session total of input tokens (bare arm: 27561 after turn 1, 55148 after turn 2). The measured fixed cost was 516 x 30 = 15480 at turn 30, which showed the total. A note stays in the history, so its cost in the total repeats once per later turn. The band 0.15 to 0.5 is a per-turn size. The other seven checks passed. No plugin fault: the notes are small and correct.
- **Fix:** Added `per_turn_tokens` (difference between runs) in `tests/live/delta/delta_live.py`, used it before the judge runs, and added the session totals to the report. Two tests pin it in `tests/test_live_delta.py`. I judged the same 90 runs again from the files on disk and the test home state databases (no new model call, no second round), and kept the first report as `arms-report-first-judge.json` next to the new `arms-report.json`.
- **Files modified:** `tests/live/delta/delta_live.py`, `tests/test_live_delta.py`
- **Verification:** `./scripts/check.sh` all ok; `arms-report.json` pass true with the keys the plan names.
- **Commit:** `8d9a2e0`

**Total deviations:** 1 auto-fixed (Rule 1). **Impact:** the plan said "no repo file changes"; the fix touches the test tool only, no plugin code. The numbers are the measured ones, now judged per turn.

## Issues Encountered

None beyond the deviation. The `tests/home_guard.py` noise did not fire in the check run.

## Known Stubs

None.

## Threat Flags

None.

## Phase state

Plan 07 is the last plan of phase 5. STOR-07 and AGNT-05 are complete. The real gateway PID 799352 is unchanged. No test chat, test board, test home or test gateway of this phase is left on devpc.

## Self-Check: PASSED

- FOUND: commit 8d9a2e0 is an ancestor of HEAD.
- FOUND: `arms-report.json` with pass true, both test homes gone, real gateway PID 799352.
- No em dash or en dash in this file.
