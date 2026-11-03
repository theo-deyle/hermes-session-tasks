---
phase: 07-deploy-and-hardening
plan: 08
subsystem: infra
tags: [hermes-cli, live-test, gateway-restart, ask-rule, own-plan]
requires:
  - phase: 07-deploy-and-hardening
    provides: 07-07 host install proof and the pushed head
provides:
  - Live proof that the real model keeps the ask rule with the new wording (Task 1)
  - Pre-check results, lock table and restart announcement for Theo (Task 2)
affects: [07-09]
requirements: [DEV-04]
status: in-progress
plan_head_before: d463713bf560100f6b17be23bbfb87e06bf9af93
---

# Phase 7 Plan 08: Live ask rule, restart and own-plan check Summary

Task 1 is done: the real model keeps the ask rule with the new wording in a test Hermes home. Task 2 is waiting for Theo's go. Task 3 has not started.

## Task 1 - test Hermes home run (no restart, no request to Theo)

### Gate lines on HEAD d463713

| Gate | Result |
|------|--------|
| `./scripts/check.sh` | `check: python 3.11 ok`, `check: python 3.14 ok`, `check: all ok` (1160 passed, coverage 97.16 percent on 3.11) |
| `uv run pytest -q -rs -m hermes` | `30 passed, 1130 deselected`, 0 skipped |
| `timeout 120 hermes plugins validate plugin` | `Validation passed.` |
| `timeout 30 hermes gateway status` | `Gateway is running (PID: 1942229)` - this is P0 |

### Test home

`make_home.py --out $HOME/.cache/hermes-session-tasks/ask-live/home --with-plugin` printed one JSON line, exit 0. Enabled: `claude-subscription-directsdk-experimental`, `hermes-session-tasks`. Listeners off: api_server, homeassistant, msgraph_webhook, telegram, webhook, proxy, updates.check, plugins.auto_update_check_hours. No secret file was linked.

Port check after A1: exit 0, test home listens on 127.0.0.1:43461, real listeners 0.0.0.0:8644, 127.0.0.1:34645, [::]:8644, `clash: []`.

### Run table

| Turn | Session | Exit | Tool calls | Board after | Reply (one line) |
|------|---------|------|------------|-------------|------------------|
| A1 (new chat) | `local-04858c0618c3288b...` | 0 | `tool_describe`, `board_edit` (two add ops) | rev 1: "Call the glass supplier", "Call the paint supplier", both unchecked | "I added both items to your board: "Call the glass supplier" and "Call the paint supplier"." |
| A2 (resume, unclear case) | same | 0 | none | rev 1, both items, unchanged | "Which one do you mean? There are two supplier items on your board: 1. Call the glass supplier 2. Call the paint supplier. I can remove one or both." |
| A3 (resume, user names the item) | same | 0 | `board_edit` (remove item 1, `base_rev` 1, `confirmed` true) | rev 2: only "Call the paint supplier" | "I removed "Call the glass supplier" from your board. "Call the paint supplier" is still there." |

The A3 call carried `confirmed` true.

ask rule passed 2 of 2

### Cleanup of the test home

- `cross_live.py stop` printed `{"result": "stopped"}`.
- Measured estimated cost in the test home state.db: 0.134 USD (one session, source `oneshot`).
- Links removed, path prefix checked, `rm -rf` of the test home. `test ! -e $HOME/.cache/hermes-session-tasks/ask-live/home` exits 0. Run files `a1`, `a2`, `a3` (`.jsonl` and `.err`) and `a1-coldstart` are kept in `$HOME/.cache/hermes-session-tasks/ask-live/`.
- The real gateway still named PID 1942229 after the removal (P0 before and after: equal).

### Deviation

**[Rule 3 - Blocking] Cold start of the fresh test home.** The first A1 call exited 1 with `Gateway starting: deadline` and made no model call (no session id, 0 tokens). The new home installed its Python dependencies on first use and the test gateway needed more than the 60 s start deadline. The gateway finished starting a few seconds later (`gateway_state` running). I ran A1 once more with the same text; it passed. The failed call is kept as `a1-coldstart.jsonl` and `a1-coldstart.err`. This is a start-up delay in a fresh home, not a result of the ask rule, so it does not count as a failed turn.

## Task 2 - pre-checks (read only, nothing changed)

1. `07-01-SUMMARY.md` to `07-07-SUMMARY.md` all exist with `status: complete`.
2. `readlink -f ~/.hermes/plugins/hermes-session-tasks` prints `/home/theo/local_repo/hermes-session-tasks/plugin`. `hermes plugins list` shows `hermes-session-tasks` enabled, version 0.2.0, source user.
3. `hermes gateway status`: `Gateway is running (PID: 1942229)`, started Mon Nov 2 20:06:12 2026 (manual run, not a service). `hermes serve --status`: 3 serve processes (pids 1960055, 1960156, 3428857). C, the last `plugin/` commit time: `fb9a37d`, Tue Nov 3 12:04:01 2026 -0500 (epoch 1793725441).
4. Lock table (owner check in code; only the lock id prefix, pid, port and start time are printed):

| Lock | pid | alive | owner check | start time | port | action |
|------|-----|-------|-------------|------------|------|--------|
| 171430ac | 1598850 | no | n/a | - | 46509 | none (dead pid) |
| 4f7a22d8 | 1960156 | yes | ok | Mon Nov 2 20:14:51 2026 | 44121 | stop |
| dfda277e | 1960055 | yes | ok | Mon Nov 2 20:14:50 2026 | 40513 | stop |
| f3619ffc | 3428857 | yes | ok | Tue Nov 3 11:53:10 2026 | 39149 | stop |

Every live `serve --isolated` process has a matching lock. No unmatched serve process exists. Lock folders found: 33; only four hold a `backend.lock.json`.

5. Cost: oneshot sessions in the real state.db, read only: 24 rows, average 0.157 USD, min 0.011, max 0.501. Three own-plan runs average about 0.47 USD and stay under 1.5 USD; Task 1 cost 0.134 USD. The "about 1 USD" figure stands.

Note: `hermes serve --status` prints the full command line of each serve process, which includes a token file path. That output was shown once to the executor and is not copied here. The pre-check should use `ps` with the flag value cut.

### Announcement for Theo

1. Next I restart the Hermes gateway on devpc and stop the Hermes backends your Desktop apps use that still run the old code: started Nov 2 20:14, pid 1960156; started Nov 2 20:14, pid 1960055; started Nov 3 11:53, pid 3428857. After that, everything runs the new board code: the board text with no personal name, the pane fixes and version 0.2.0.
2. The restart and the stop drop every live Desktop connection and stop any chat turn that runs at that moment. Each Desktop gets a fresh backend the next time it connects.
3. After it I run three short test chats on my own (about 1 USD of estimated use on your Claude subscription), then I delete those test chats and their boards. No other chat or board changes.

Please finish or pause any Desktop work you want to keep, then tell me to go ahead.

### Theo's reply (word for word)

(waiting)
