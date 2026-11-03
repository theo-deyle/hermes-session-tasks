---
phase: 06-cross-session-boards
plan: 12
subsystem: live-check
tags: [live-check, cross-session, gateway-restart, own-plan]
status: in_progress

requires:
  - phase: 06-cross-session-boards
    provides: board_sessions, board_read and board_copy (plans 06-01 to 06-10), the pane picker and copy (06-11), the live tools (06-07)
provides:
  - live proof of TOOL-03, TOOL-04 and TOOL-05 with the real model in a test Hermes home (Task 1)
  - the restart announcement and the pre-check record (Task 2)
  - the gateway restart record, the own-plan verdict with four tools and the cleanup table (Task 3)
affects: [06-12 Task 4 Mac checks]

requirements-completed: []

duration: in progress
completed: not yet
---

# Phase 6 Plan 12: Live check of the cross-session boards Summary (DRAFT, Tasks 1 to 3 complete; Task 4 pending)

Task 1 passed: in a test Hermes home the real model listed the boards, read the source board without a seen change, and copied its open items with their subtask on request. Task 2 pre-checks are done and Theo gave his go. Task 3: the gateway restarted on the new code, the own-plan check passed 3 of 3 with the four tools, and the three test chats are deleted; Theo's one script line stopped the two old Desktop backends. Task 4 (Mac checks) has not run.

Hot mount versus restart (decision): no hot reload is tried. Phase 3 measured that the Python half refreshes only on a backend restart and the Desktop half only at app start (03-08 SUMMARY). Phase 5 restarted the owner gateway the same way (05-05).

## Task 1 - test Hermes home run (no restart, no request to Theo)

### Gate lines on HEAD 1bfe33d

| Gate | Line |
|------|------|
| `./scripts/check.sh` | `check: all ok` (1067 passed on Python 3.11, 1067 passed on Python 3.14) |
| `uv run pytest -q -rs -m hermes` | `28 passed, 1039 deselected in 60.86s` (0 skipped) |
| `timeout 120 hermes plugins validate plugin/` | `Validation passed.` |
| `node --check plugin/desktop/plugin.js` | exit 0 |
| `timeout 30 hermes gateway status` | `Gateway is running (PID: 799352)`, real PID P0 = 799352, started Mon Nov 2 10:56:12 2026 (`hermes_cli.main --profile default gateway run --quiet`) |

### Test home

- `make_home.py --out $HOME/.cache/hermes-session-tasks/cross-live/home --with-plugin` printed one JSON line, exit 0. Enabled: `claude-subscription-directsdk-experimental`, `hermes-session-tasks`. Listeners off: api_server, homeassistant, msgraph_webhook, telegram, webhook, proxy, updates.check, plugins.auto_update_check_hours. No secret file was linked.
- Seed: `{"session": "cross-src-1", "title": "Phase 6 source board", "ok": true, "rev": 1, "changed_ids": [1, 2, 3]}`.
- Port check right after L1: `ports exit 0`, test home listens on 127.0.0.1:49903, real listeners 0.0.0.0:8644, 127.0.0.1:47773, [::]:8644, `clash: []`.

### Run table

| Turn | Session id | Exit | Tool calls (real tools) | Pass result | Reply text |
|------|-----------|------|-------------------------|-------------|------------|
| L1 list.txt | `local-1eb762702c8efbc88e1c7523a5edd838022d60b8d5be14dce04bf08a1b647e18` (S) | 0 | `board_sessions {}`, `board_read {session_id: cross-src-1}` (after `tool_describe`) | pass: `board_sessions` called, reply names `Phase 6 source board` | "Only one session has a task board: Phase 6 source board (cross-src-1): open items are #1 Call John and #2 Ask about the quote, which is a sub-item of #1. #3 Book the van is done." |
| L2 read.txt (resume S) | S, same | 0 | `board_read {session_id: cross-src-1}`, no `board_copy` | pass: source board before and after are byte equal (rev 1, agent_seen_rev 0, three items) | board read, open items named |
| L3 copy.txt (resume S) | S, same (no session id change, root = S) | 0 | `board_copy {from_session_id: cross-src-1}` (after `tool_describe`) | pass: see below | "I copied 2 open items from cross-src-1 to this session's board. They are unchecked and have new ids: #1 Call John, #2 Ask about the quote, which is a sub-item of #1. Nothing was skipped. I left out #3 Book the van because it was already done. The source board is unchanged." |
| M1 mention.txt (new chat) | `local-3f1b8da755035851215d3703d1935f52bddc0306d4ea9631545593ac749661a4` | 0 | `tool_search`, `board_read {session_id: cross-src-1}`, no `board_copy` | no copy | read the board, "I changed nothing", noted that nothing mentions a lease |
| M2 mention.txt (new chat) | `local-d58f569c64d30191102977abfc7b79b7a118ab17c692f9e182e003b85b7de7d0` | 0 | `tool_search`, `board_read {session_id: cross-src-1}`, no `board_copy` | no copy | read the board, "I changed nothing" |

L3 target board (S): rev 1, agent_seen_rev 1, items `#1 Call John` (unchecked, updated_by agent), `#2 Ask about the quote` (parent 1, unchecked, updated_by agent). Journal `copied` rows: `{rev 1, actor agent, item_id 1, text cross-src-1#1}` and `{rev 1, actor agent, item_id 2, text cross-src-1#2}`. Source board `cross-src-1` after L3 and after M1 and M2: byte equal to the board before L2 (rev 1, agent_seen_rev 0). No `.err` file held a traceback.

unasked copies: 0 of 2

### Cleanup of the test home

- `cross_live.py stop` printed `{"result": "stopped"}`; `hermes gateway status` in the test home reported `Gateway is not running`.
- Measured estimated cost in the test home state.db: 0.154 + 0.019 + 0.012 = 0.185 USD for the three chats (L1 to L3 share one session, M1 and M2 one each).
- Links removed, path prefix checked, `rm -rf` of the test home. `test ! -e $HOME/.cache/hermes-session-tasks/cross-live/home` exits 0. Run files (`l1`, `l2`, `l3`, `m1`, `m2` `.jsonl` and `.err`) are kept in `$HOME/.cache/hermes-session-tasks/cross-live/`.
- Real gateway after the runs: `Gateway is running (PID: 799352)`. P0 before = P0 after = 799352.

## Task 2 - pre-checks and restart announcement (Theo's go: given)

### Pre-check results (read only, nothing changed)

1. `06-01-SUMMARY.md` to `06-11-SUMMARY.md` exist, each `status: complete`.
2. `readlink -f ~/.hermes/plugins/hermes-session-tasks` prints `/home/theo/local_repo/hermes-session-tasks/plugin`. `hermes plugins list` shows `hermes-session…` enabled, version 0.1.0, source user.
3. `hermes gateway status`: `Gateway is running (PID: 799352)`, running manually, not as a service. `ps` line: `799352 Mon Nov 2 10:56:12 2026 .../python3 -m hermes_cli.main --profile default gateway run --quiet`.
4. Desktop backend locks in `~/.hermes/desktop-ssh/*/backend.lock.json` (4 files):

| Lock | pid | Alive | Command line holds `serve --isolated` | Started | Client connections to its port |
|------|-----|-------|----------------------------------------|---------|--------------------------------|
| `dfda277e4fcadaab5b5106d883d97e19` | 2231852 | yes | yes | Sun Nov 1 08:01:44 2026 | yes (port 41199) |
| `4f7a22d87ba7ad12117cd3eb203fc040` | 1040717 | yes | yes | Mon Nov 2 12:45:41 2026 | yes (port 45505) |
| `171430ac64d8497d7edbd7185792d86c` | 1598850 | no | n/a | 2026-10-02 | no |
| `f3619ffc6faed70a5b6d5c9de87e0711` | 1723215 | no | n/a | 2026-11-02 | no |

   Mac backend finding: the lock that matches the 03-08 record (pid 2231852, port 41199) is `/home/theo/.hermes/desktop-ssh/dfda277e4fcadaab5b5106d883d97e19/backend.lock.json`, and the pid is alive with `serve --isolated`. A second live backend, pid 1040717 (lock `4f7a22d87ba7ad12117cd3eb203fc040`, started 12:45 on Nov 2), also serves open Desktop connections. Both started before the first Phase 6 commit (34ac90e, 16:15 on Nov 2), so both hold pre-Phase 6 code and neither has the copy route. The plan rule names only pid 2231852. The announcement below names both.
5. Cost: oneshot sessions in the real state.db, read only: 24 rows, average 0.157 USD, min 0.011, max 0.501. Three own-plan runs average about 0.47 USD and stay under 1.5 USD; the test-home turns cost 0.185 USD. The "about 1 USD" figure stands.

### Announcement as prepared for Theo

1. Next I restart the Hermes gateway on devpc and the Hermes backends your Desktop uses, so they all run the new board code. After it, the agent can list your other chats' boards, read one, and copy items from it when you ask; the task pane gets a chat picker.
2. The restart drops every live Desktop connection and stops any chat turn that runs at that moment. Two Desktop backends are connected right now (one started on 1 November, one on 2 November at 12:45). I stop both. Your Desktop gets a fresh backend the next time it connects.
3. After it I run three short test chats on my own (about 1 USD of estimated use on your Claude subscription), then I delete those test chats and their boards. No other chat or board changes.

Please finish or pause any Desktop work you want to keep, then tell me to go ahead.

### Theo's reply (word for word)

"Go ahead." (2026-11-02, after the announcement above)

## Task 3 - restart, own-plan re-check, cleanup

### Restart record

| Item | Value |
|------|-------|
| T0 | 2026-11-03T01:06:03Z (20:06 local, Nov 2) |
| Command | `timeout 180 hermes gateway restart --yes --detach`, exit 0: `Stopped gateway for this profile`, `Started the gateway in the background` |
| PID before | 799352 (started Mon Nov 2 10:56:12 2026) |
| PID after | 1942229 (started Mon Nov 2 20:06:12 2026); `hermes gateway status`: `Gateway is running (PID: 1942229)`, running manually, not as a service |
| Plugin check after | `Validation passed.` (`hermes plugins validate plugin/`, plugin host isolation) |
| Proof the new gateway loaded the plugin | every own-plan run below called `board_edit` through the restarted gateway |

### Desktop backend stop (step 2): owner check, then Theo's one script line

Lock files re-read at 01:05Z, before the restart. Each live pid was matched to its lock: alive, `serve --isolated` in the command line, and the `--ssh-session-token-file` path inside the lock's own folder.

| Lock | pid | Alive | `serve --isolated` | Token path in the lock folder | Started | Connections on its port |
|------|-----|-------|--------------------|-------------------------------|---------|-------------------------|
| `dfda277e4fcadaab5b5106d883d97e19` | 2231852 | yes | yes | yes (`fd26df8d34535a6a.token`) | Sun Nov 1 08:01:44 2026 | yes (port 41199, 4 established) |
| `4f7a22d87ba7ad12117cd3eb203fc040` | 1040717 | yes | yes | yes (`bc97d5a2238d3beb.token`) | Mon Nov 2 12:45:41 2026 | yes (port 45505, 3 established) |
| `f3619ffc6faed70a5b6d5c9de87e0711` | 1933828 (Task 2 read 1723215, dead) | yes | yes | yes (`0ab7c49cebac5520.token`) | Mon Nov 2 20:02:35 2026 (01:02:36Z) | yes (port 39937, 4 established) |
| `171430ac64d8497d7edbd7185792d86c` | 1598850 | no | n/a | n/a | 2026-10-02 | no |

Findings:

1. A third backend, pid 1933828, started at 20:02:35 local, after the last code commit (1bfe33d, 18:18:30 local). It loaded the Phase 6 Python half at start, so it needs no stop. It is not on the stop list.
2. Both pre-Phase 6 backends (pid 2231852 and pid 1040717) passed the owner check. The `kill <pid>` from this session was blocked by the auto mode safety check ("Interfere With Workloads"). No signal was sent. Both pids were still alive at 01:11Z.
3. Per house rule 29 the stop moved into one non-interactive script that prints no secret: `/tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/232eb971-43c2-4e72-a1b6-67dce37c62cd/scratchpad/stop-desktop-backends.ps1`. It repeats the owner check per pid, sends SIGTERM with `/bin/kill -TERM`, waits up to 30 s, and sends no stronger signal. Theo's one line: `! timeout 90 pwsh -NoProfile -File /tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/232eb971-43c2-4e72-a1b6-67dce37c62cd/scratchpad/stop-desktop-backends.ps1`. Pass lines: `pid 2231852 : stopped at <time>`, `pid 1040717 : stopped at <time>`, `backend-stop: done`. Fail line: `FAIL: pid <n> still alive after 30 s`.

Result of the stop: Theo ran the line. Output word for word:

```
pid 2231852 : owner check ok (lock dfda277e4fcadaab5b5106d883d97e19), sending SIGTERM at 01:14:29Z
pid 2231852 : stopped at 01:14:30Z
pid 1040717 : owner check ok (lock 4f7a22d87ba7ad12117cd3eb203fc040), sending SIGTERM at 01:14:30Z
pid 1040717 : stopped at 01:14:31Z
backend-stop: done
```

Check from this session, verified at 01:14:58Z: both pids gone (test ! -e /proc/2231852 and test ! -e /proc/1040717 exit 0). Pid 1933828 (the backend that already holds the Phase 6 code) was not touched. Task 3 is complete.

### Own-plan re-check (step 3)

`OWN_JOB_OUT=$HOME/.cache/hermes-session-tasks/own-job tests/live/own_job/run.sh own6-N`, the Phase 5 prompt `job.txt`, the plugin on HEAD 1bfe33d with the four tools (`board_edit`, `board_sessions`, `board_read`, `board_copy`). Every run: hermes exit 0, no `hook failed` and no traceback line in the `.err` file, analyzer exit 0.

| Run | Session id | hermes exit | board_edit calls | Adds (one batch) | Checks (add_batch, check_after_add, all_checked) | Final checked / total | todo_list calls | Analyzer exit | Verdict |
|-----|-----------|-------------|------------------|------------------|--------------------------------------------------|-----------------------|-----------------|---------------|---------|
| own6-1 | `local-dc8182cb395896e7acfaa4e77f0cc793b84c8843031059b095136546ab885982` | 0 | 2 | 7 | true, true, true | 7 / 7 | 0 | 0 | pass |
| own6-2 | `local-de8c87d98fdda40d565d637223f32360118edaa9c3044ee714596e3e16f09530` | 0 | 2 | 6 | true, true, true | 6 / 6 | 0 | 0 | pass |
| own6-3 | `local-31eb95b81f8ae3b4058de5d665b95ee8b3a23cccc328b47b0002492c9a85a57d` | 0 | 2 | 6 | true, true, true | 6 / 6 | 0 | 0 | pass |

own-plan passed 3 of 3

RESEARCH A8 holds: four tools keep the own-plan rate. Every board ended at rev 2 with every item updated by the agent.

### Cleanup of the test chats (step 4)

Read-only check in `~/.hermes/state.db` (`mode=ro`) before any delete: all three ids have source `oneshot` and `started_at` after T0. Board count in the data file: 18 before the runs, 21 after the runs, 18 after the delete. Alias count: 18, 21, 18.

| Session id | Source | started_at (UTC) | After T0 | Had board (items) | Cost USD (read before) | `hermes sessions delete <id> --yes` | Board rows after | Alias rows after | Session row after |
|------------|--------|------------------|----------|-------------------|------------------------|--------------------------------------|------------------|------------------|-------------------|
| `local-dc8182cb3958...` (own6-1) | oneshot | 2026-11-03T01:06:41Z | yes | yes (7) | 0.5697 | `Deleted session` | 0 | 0 | 0 |
| `local-de8c87d98fdd...` (own6-2) | oneshot | 2026-11-03T01:08:23Z | yes | yes (6) | 0.1176 | `Deleted session` | 0 | 0 | 0 |
| `local-31eb95b81f8a...` (own6-3) | oneshot | 2026-11-03T01:09:15Z | yes | yes (6) | 0.1468 | `Deleted session` | 0 | 0 | 0 |

Cost of the three own-plan chats: 0.8341 USD. With the test home turns (0.185 USD) the plan cost 1.019 USD of estimated use on the Claude subscription, in line with the "about 1 USD" announced. No other session or board was read for content, changed or deleted.

### Final gate lines and the devpc hash (step 5)

- `timeout 120 hermes plugins validate plugin/`: `Validation passed.`
- `timeout 30 hermes gateway status`: `Gateway is running (PID: 1942229)`.
- `sha256sum plugin/desktop/plugin.js`: `719920126b0e930eba50bfef2d119fe8b4ddb4eade58a5ce46ec6cb17afa4cae` (the devpc hash for the Mac install check).

## Task 4 - Mac checks (pending)

Precondition met: the two old Desktop backends are stopped, the gateway runs the new code, and the devpc hash is on record.

| # | Check | Result |
|---|-------|--------|
| 1 | Install line on the Mac prints a sha256 equal to `719920126b0e930eba50bfef2d119fe8b4ddb4eade58a5ce46ec6cb17afa4cae` | pending |
| 2 | Quit and reopen Hermes Desktop, new chat, send "hi": the Session tasks pane shows this chat with the picker row at the top | pending |
| 3 | Open the chat picker: this chat first as "this session", then the other chats with a board, real titles, "N of M open" and a time, all inside the pane | pending |
| 4 | Pick another chat with items: yellow "Read only. Viewing another session." notice with Back, greyed boxes, no add line, Copy on hover, "Copy all open to" in the header | pending |
| 5 | Copy one item, then Back: "Copied 1 to (this chat). 0 skipped, already on the board.", the item on this chat's board unchecked, the other board unchanged | pending |

The Mac test chat and its board are deleted only after Theo answers one plain question.

## Self-Check

(pending, written when the plan completes)
