---
phase: 06-cross-session-boards
plan: 03
subsystem: session-titles
tags: [titles, session-reader, read-only, hermes-contract]
status: complete

requires:
  - phase: 01-foundation
    provides: read-only SessionDB door (session_reader.open_session_reader), SessionReader Protocol, FakeReaderFactory
provides:
  - titles.TitleLookup (titles, title_of) and no_titles for the agent side
  - SessionReader Protocol widened with get_session_title and get_messages
  - fake reader title and messages, TITLE_FIXTURE
  - real SessionDB parity test for titles and first messages
affects: [06-05 board_copy result, 06-08 board_sessions and cross read, 06-10 wiring]

actuals:
  tokens: 4900
  tasks: 3
  commits: 6

plan_head_before: c04f126a0035e3fe26947f0ea353bb441fbf9a71
plan_head_after: 510e5bee6d34bc88745cfa3a6d6985f6575dea14
commits: 6

tech-stack:
  added: []
  patterns:
    - "one reader per call, closed in finally; every fault gives a fallback label and one WARNING"
    - "contract snippet seeds message rows with plain SQL in a scratch HERMES_HOME"

key-files:
  created:
    - plugin/session_tasks/titles.py
    - tests/test_titles.py
  modified:
    - plugin/session_tasks/lineage.py
    - tests/fakes.py
    - tests/hermes_contract_snippet.py
    - tests/test_hermes_contract.py

key-decisions:
  - "Label chain: Hermes title, then first user message among the first 5 (sanitised, cut to 60 characters, trailing space stripped), then Untitled session (D-39)."
  - "A fault in close() logs one WARNING and never raises; titles() never raises."

requirements-completed: [TOOL-03]

coverage:
  - id: D1
    description: "TitleLookup gives each board root a title, a first message label, or Untitled session through one read-only reader that is closed after the call"
    requirement: "TOOL-03"
    verification:
      - kind: unit
        ref: "tests/test_titles.py (18 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The fake reader and TitleLookup agree with the real SessionDB, and state.db is unchanged after the reads"
    requirement: "TOOL-03"
    verification:
      - kind: integration
        ref: "tests/test_hermes_contract.py::test_fake_reader_titles_and_messages_match_the_real_session_db"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-11-02
---

# Phase 6 Plan 03: Session titles for the agent Summary

**TitleLookup labels each board root with its Hermes title, else its first user message (first 5 messages, 60 characters), else `Untitled session`, through one read-only SessionDB reader, and never raises.**

## Performance

- **Duration:** about 22 min
- **Tasks:** 3 of 3
- **Commits:** 6 task commits (test, feat for each task)

## Accomplishments

- `plugin/session_tasks/titles.py`: `UNTITLED`, `FIRST_MESSAGES`, `MESSAGE_TITLE_CHARS`, `TitleLookup.titles`, `TitleLookup.title_of`, `no_titles`. Every label goes through `sanitize_text` (T-6-08). A missing state.db gives `Untitled session` for every id and one WARNING. A fault on one id gives that id `Untitled session` and one WARNING, and the other ids keep their titles (T-6-09).
- `SessionReader` Protocol now has six methods (`get_session_title`, `get_messages` added). No new Hermes import: `titles.py` has no `hermes_state` reference.
- Fake reader gained `title`, `messages`, `get_session_title`, `get_messages` (it records each `limit`), and `TITLE_FIXTURE` (`titled`, `worded`, `blank`).
- 18 title tests (plan asked for 14 or more). The hermes marker test pins the fake and `TitleLookup` to the real `SessionDB`, with the state.db digest unchanged (T-6-07).
- `./scripts/check.sh` ends with `check: all ok` (914 passed on Python 3.14, coverage gate passed on 3.11).

## Task Commits

1. Task 1 RED: `f9d7446` test(06-03): add failing test for a session title lookup
2. Task 1 GREEN: `ca691b0` feat(06-03): read session titles through the read-only session door
3. Task 2 RED: `48343cd` test(06-03): add title chain and fault tests
4. Task 2 GREEN: `6053346` feat(06-03): title fallbacks and fault handling
5. Task 3 RED: `1f02a96` test(06-03): add real SessionDB parity test for titles
6. Task 3 GREEN: `510e5be` feat(06-03): pin the title reads to the real SessionDB

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Contract snippet seeds messages with plain SQL, not `append_message`**
- **Found during:** Task 3
- **Issue:** The plan said to call `db.append_message(...)` in the snippet. In a scratch HERMES_HOME the first `append_message` call imports the agent loop. Hermes then syncs dependencies for that data root and relaunches the script, and the relaunched interpreter fails with `No module named 'ruamel'`. This broke the existing contract test too. The session-delete snippet already documents the same behaviour.
- **Fix:** `insert_messages` in `tests/hermes_contract_snippet.py` inserts rows with `INSERT INTO messages (session_id, role, content, timestamp)` on the scratch `state.db`. `set_session_title` still goes through `SessionDB`. The reads under test (`get_session_title`, `get_messages`) are the real ones.
- **Files modified:** tests/hermes_contract_snippet.py
- **Commit:** 510e5be

**2. [Rule 1 - Test detail] Parity test compares the four named ids of `titles`**
- **Issue:** The snippet resolves titles for every fixture id (seven lineage ids plus the title ids plus `missing`). The plan's expected dict has four keys.
- **Fix:** The test compares the `titled`, `worded`, `blank` and `missing` entries with the plan's expected dict. The existing test now shares a `run_snippet` helper that runs the combined fixture.
- **Commit:** 1f02a96, 510e5be

**3. Fake reader records `message_limits`**
- The plan says "the fake records `limit=5`". The fake gained a `message_limits` list for that assertion (commit 48343cd).

## Auth gates

None.

## Issues Encountered

- During the failed contract runs (about 16:23 to 16:37 on 2026-11-02) Hermes ran its own dependency sync from the snippet launch. That sync touched the shared Hermes tools store: `~/.hermes/tools/facts.json` and the `~/.hermes/tools/python-3.14.9+20261021-linux-x64` directory have a modified time of 16:23. The 3.14.9 interpreter still runs (SQLite 3.53.1). No file in the plugin repo or in `state.db` was written by this plan. Theo may want to know that a foreign HERMES_HOME plus `append_message` triggers that sync; the snippet no longer does it.

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path or schema change.

## Flagged assumptions

- RESEARCH A5: the first user message sits among the first 5 messages of the board root. When it does not, the label is `Untitled session`. The agent label and the pane label can differ by Hermes's `#N` title suffix on a compressed chain; both name the same session.

## Self-Check: PASSED

- Files: titles.py, test_titles.py, lineage.py, fakes.py, hermes_contract_snippet.py, test_hermes_contract.py exist.
- Commits f9d7446, ca691b0, 48343cd, 6053346, 1f02a96, 510e5be are ancestors of HEAD.
- `uv run pytest tests/test_hermes_contract.py -q -rs -m hermes`: 4 passed, 0 skipped.
- `./scripts/check.sh`: `check: all ok`.
- The first 06-03 commit is a test commit.
