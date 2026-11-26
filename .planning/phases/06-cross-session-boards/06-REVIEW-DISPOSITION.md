# Phase 06 - Review disposition

One row per finding in 06-REVIEW.md. Status fixed names the fix commit. Status deferred means the finding stays open for a later phase.

| Finding | Severity | File | Status | Reason |
|---------|----------|------|--------|--------|
| WR-01: the `copied` journal rows evict the `add` rows of the same copy | warning | `plugin/session_tasks/rows.py`, `plugin/session_tasks/store.py` | fixed | 969b12d (test 285514b) |
| WR-02: `cross_live.py stop` accepts the real Hermes home | warning | `tests/live/cross/cross_live.py` | fixed | d11c5e9 (test 34c134e) |
| IN-01: `_cross_read` says "no store write" but a branch id creates a board | info | `plugin/session_tasks/board_tools.py` | deferred | info, no behaviour risk, left for a later phase |
| IN-02: `base_rev` on the copy path is parsed and never used | info | `plugin/session_tasks/copy_args.py` | deferred | info, no behaviour risk, left for a later phase |
| IN-03: before the first board reply the picker treats the session id as the root | info | `plugin/desktop/plugin.js` | deferred | info, no behaviour risk, left for a later phase |
| IN-04: the system prompt section names two of the four tools | info | `plugin/session_tasks/tool_text.py` | deferred | info, no behaviour risk, left for a later phase |
| IN-05: `SESSION_ID_MAX` lives in two files | info | `plugin/dashboard/plugin_api.py` | deferred | info, no behaviour risk, left for a later phase |
| IN-06: `cross_live.py seed` crashes on a second run and trusts `~/.hermes` as the only real home | info | `tests/live/cross/cross_live.py` | deferred | info, no behaviour risk, left for a later phase |
| IN-07: a refused copy shows the "save" notice and keeps the gone board on screen | info | `plugin/desktop/plugin.js` | deferred | info, no behaviour risk, left for a later phase |
