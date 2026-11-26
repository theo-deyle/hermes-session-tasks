---
phase: 07-deploy-and-hardening
plan: 09
subsystem: infra
tags: [desktop-install, public-repo, live-test]
requirements: [DEV-04]
status: complete
---

# Phase 7 Plan 09: Desktop install and loop on the Mac and the Windows PC Summary

Task 1 is done. Theo did Task 2 (the Mac) and Task 3 (the Windows PCs, work and home) on his own and reported the result on 2026-11-26.

## Task 1 - the public repo serves the new pane file (2026-11-15)

| Check | Result |
|-------|--------|
| Anonymous clone (`GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=echo`, depth 1) | finished with no prompt, head 7c47337 |
| SHA-256 of `plugin/desktop/plugin.js`, repo | d657c058df2418fc0bbcb9407302195265f68c488d82131c55a293c6bde01b0c |
| SHA-256, clone | d657c058df2418fc0bbcb9407302195265f68c488d82131c55a293c6bde01b0c |
| SHA-256, installed copy on devpc | d657c058df2418fc0bbcb9407302195265f68c488d82131c55a293c6bde01b0c |
| `plugin/plugin.yaml` of the clone | `version: 0.2.0` |
| C (last `plugin/` commit) | 1794336202, Tue Nov 10 13:43:22 2026 -0500 |
| Gateway | `hermes-gateway` service active, pid 2090751, started Sun Nov 15 18:35:36 2026 |
| Live Desktop backend | lock f3619ffc, pid 1865553, started Sun Nov 15 09:14:37 2026, port 40193, route 401 |

The probe clone is removed.

### Deviation

The plan's link check (`readlink -f` equals the repo `plugin` folder) no longer applies. Since 2026-11-13 devpc holds an installed copy from the public repo at revision 7c47337, not the dev link (see 07-08-SUMMARY.md). The check used here: the installed pane file has the same hash as the repo and the clone.

## Task 2 and Task 3 - the Mac and the Windows PCs (reported 2026-11-26)

Theo's report, word for word: "The windows PCs (both work and home) are done, so is the mac."

Theo did the installs and the use on his own between 2026-11-15 and 2026-11-26. He did not send the scripted test messages, so the turn-by-turn record of the plan does not exist. The data on devpc supports his report (read only, 2026-11-26):

| Check | Result |
|-------|--------|
| Boards created after T1 (2026-11-15T23:41:02Z) | 26: 24 from Desktop chats, 1 local, 1 Telegram |
| Items on those boards by last editor | 201 by the agent, 7 by the user |
| Boards with an edit made in the pane | 3 (Nov 18, Nov 20, Nov 23) |
| Installed plugin on devpc | revision 7aa8a25, no difference to the repo `plugin` folder, version 0.2.0 |
| C (last `plugin/` commit) | Mon Nov 23 08:41:04 2026 EST |
| Gateway | `hermes-gateway` service, pid 2139783, started Fri Nov 20 22:16:14 2026 |
| Live Desktop backend | lock dee2694c, pid 2202833, started Tue Nov 24 22:26:21 2026 (after C), route 401 |
| Public repo | `public/main` equals `main` at 7aa8a25 before this commit |

### Deviations

- No scripted test chat exists, so no test chat and no board was deleted.
- Theo pushed the phase commits and two later pane changes (quick tasks 261123-b4n and 261123-c04) to the public repo himself. The plan's "go before the final push" step is closed by that.
- The gateway started on Nov 20, before the two pane changes of Nov 23. Those changes touch the Desktop pane file and the READMEs only. The live Desktop backend started after them.
- The data cannot tell which machine made which edit. The per-machine proof is Theo's report.
