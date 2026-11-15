---
phase: 07-deploy-and-hardening
plan: 09
subsystem: infra
tags: [desktop-install, public-repo, live-test]
requirements: [DEV-04]
status: in-progress
---

# Phase 7 Plan 09: Desktop install and loop on the Mac and the Windows PC Summary

Task 1 is done. Task 2 (the Mac) waits for Theo's first step. Task 3 (the Windows PC) has not started.

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
