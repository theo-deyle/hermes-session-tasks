# Phase 7: Deploy and hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-11-03
**Phase:** 07-deploy-and-hardening
**Areas discussed:** Install path, Repo and catalog readiness, Desktop backends after a restart, Hardening scope

---

## Install path

| Option | Description | Selected |
|--------|-------------|----------|
| devpc-only deploy script | A script for the symlink, enable and version check on devpc | |
| Catalog-ready install | `hermes plugins install owner/repo#plugin` on any host, Install from Git on any Desktop | ✓ |

**User's choice:** Catalog-ready install on any Hermes host and any Desktop app.
**Notes:** "Make this so that we can have it on any of the hosts that I have installed Hermes on, and be able to connect with any of the desktop apps that I have on my machines."

---

## Repo and catalog readiness

| Option | Description | Selected |
|--------|-------------|----------|
| Private org repo, credential per machine | Keep `Don-Mor-Software-Group` private; each host and Desktop signs in to GitHub | |
| Public repo on the personal account | `theo-deyle/hermes-session-tasks`, public, no credential anywhere | ✓ |

**User's choice:** Public repo on the personal account, set up as if submitted to the catalog, no submission.
**Notes:** "Set it up as IF I would submit it, because of the simplicity." Confirmed `theo-deyle`, not the org.

---

## Desktop backends after a restart

| Option | Description | Selected |
|--------|-------------|----------|
| Stop matched backends after Theo's go | Phase 6 procedure, lock file and command line match | ✓ |
| Leave them until Desktop reconnects | Old code keeps running on each backend | |

**User's choice:** Claude's recommendation stood; no objection raised.

---

## Hardening scope

| Option | Description | Selected |
|--------|-------------|----------|
| Three pane warnings, stale spec line, IN-05 | Cheap fixes with no behaviour risk | ✓ |
| All seven review notes | Includes harness and prompt changes | |

**User's choice:** Claude's recommendation stood; no objection raised.

## Claude's Discretion

Neutral string wording, CI workflow content, history scan method, plan order.

## Deferred Ideas

The catalog pull request itself; IN-01 to IN-04, IN-06, IN-07; the org repo after the move.
