---
phase: "04"
review: 04-REVIEW.md
fix_report: 04-REVIEW-FIX.md
recorded: "2026-11-02"
---

# Phase 04 - Review Disposition

One row per finding in 04-REVIEW.md. Severity counts: 1 blocker, 5 warning, 4 info.

| Finding | Severity | Disposition | Evidence |
|---------|----------|-------------|----------|
| CR-01 | blocker | fixed | commits a6a588f and c1077fc: the edit record carries its session id; a save after a focus change sends nothing and reopens only on its own session's board; test in tests/test_pane_edit_delete.py |
| WR-01 | warning | fixed | commits 6bed7b8 and 65df9fd: the write queue ends in `.catch`, `onOutcome` runs in `finally`, busy flags always reset; test in tests/test_pane_writes.py |
| WR-02 | warning | fixed | commits 9ba239c and e9a7e3e: a visit counter per focus change; late callbacks from an old visit return; focus change resets addBusy, subBusy and the load notice |
| WR-03 | warning | fixed | commits c5e12df and 7bf8911: the render writes no ref; the `[sid]` effect sets the session; no code deletes a rev |
| WR-04 | warning | fixed | commits 820af8e and ccbe507: a failed save reopens the edit when it can, else keeps the text by session and item for the next edit of that item |
| WR-05 | warning | fixed | commits 6c2e0c7 and 4fc2877: `isMismatch` guards `!meta` |
| IN-01 | info | open | `-RemotePath` allows `..` segments; the export default check limits the damage; only the person at the keyboard supplies the value |
| IN-02 | info | open | the test rig records the poll interval but never fires it; the event path covers reload; a `tick` step is a Phase 5 test improvement |
| IN-03 | info | open | two source-text tests from the Mac fix; a harness assertion on the checkbox class is a later improvement |
| IN-04 | info | open | `Pane` is one long function because hooks must stay in it; the one-file rule limits the options |

Not in the review, recorded by the fixer: a reload reply is dropped while any write runs, for any session; after a focus change during a write the new board loads on the next event, poll or failed write. Unsent add-line text is dropped on a focus change (the test `test_focus_change_drops_edit_and_typing` pins it).
