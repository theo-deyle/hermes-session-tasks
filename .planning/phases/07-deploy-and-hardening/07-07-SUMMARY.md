---
phase: 07-deploy-and-hardening
plan: 07
subsystem: infra
tags: [hermes-cli, plugin-install, catalog-readiness, ssh-probe]
requires:
  - phase: 07-deploy-and-hardening
    provides: 07-06 public repo theo-deyle/hermes-session-tasks at head d39efa9
provides:
  - Proof that one hermes plugins install line installs and enables the plugin from the public repo (fresh home on devpc)
  - A read-only probe of the SSH hosts for a second Hermes host
affects: [07-08, 07-09]
requirements: [DEV-04, DEV-06]
status: in-progress
plan_head_before: 206ec79e0fb38958d0a40abfdb14bcf0154f7b0d
---

# Phase 7 Plan 07: Host install proof Summary (partial - Task 1 done, Task 2 open)

Status: in progress. Task 1 passed. Task 2 (Theo names a host or keeps the devpc result) is open. Task 3 has not started.

## Task 1: fresh Hermes home on devpc

Scratch home: `<scratchpad>/07-07/home-public`. `HERMES_HOME` pointed at it. The guard refused any path equal to `~/.hermes`. Hermes: `Hermes Agent v0.22.5 (2026.9.24)`.

### Install

Command: `HERMES_HOME="$H" timeout 300 hermes plugins install 'theo-deyle/hermes-session-tasks#plugin' --enable`. Exit 0.

```
hermes: preparing dependencies for this data root (the checkout's updates belong to /home/theo/.hermes)...
Preparing the isolated Hermes runtime...
  -> Installing Python dependencies...
  OK Installing Python dependencies
  -> Installing Python dependencies...
  OK Installing Python dependencies
Warning: custom (unreviewed) source - not from the Hermes catalog.
Cloning https://github.com/theo-deyle/hermes-session-tasks.git (subdir: plugin)...

Installed
Plugin installed: theo-deyle/hermes-session-tasks#plugin
Location: <scratch home>/plugins/hermes-session-tasks

Plugin hermes-session-tasks enabled.
```

The raw output used box and check mark characters. The text above keeps the words and drops those characters.

### Install record

- `plugin.yaml` is present in `<home>/plugins/hermes-session-tasks`.
- `<home>/plugins/.install-metadata.json`:
  `{"hermes-session-tasks": {"pinned": false, "revision": "d39efa98f8568cc3c393e7ebecdf5e20e3a2b9e5", "source": "https://github.com/theo-deyle/hermes-session-tasks.git#plugin"}}`
- The revision equals `git rev-parse public/main` and `git ls-remote public refs/heads/main` (d39efa98f8568cc3c393e7ebecdf5e20e3a2b9e5).
- `<home>/config.yaml` (written by the CLI): `plugins:` with `enabled:` holding `hermes-session-tasks`, and `disabled: []`.

### Doctor

```
Plugin Doctor: <scratch home>/plugins/hermes-session-tasks
  manifest: hermes-session-tasks 0.2.0 (standalone)
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 4 tool(s), 4 hook(s)
```

Exit 0.

### List

`HERMES_HOME="$H" hermes plugins list --json`, the entry of the plugin:

```
{"name":"hermes-session-tasks","status":"enabled","version":"0.2.0","description":"A per-session task board. The agent adds what the user must do, decide or remember; the user edits the items in a Hermes Desktop pane.","source":"user","removed":null}
```

### Update

```
Updating hermes-session-tasks...
Plugin hermes-session-tasks is already up to date.
```

Exit 0. The raw line starts with a check mark.

### Real Hermes home on devpc, before and after

| Check | Before | After |
|-------|--------|-------|
| `hermes plugins list --json` entry | `["hermes-session-tasks","enabled","0.2.0","user"]` | same |
| `readlink -f ~/.hermes/plugins/hermes-session-tasks` | `/home/theo/local_repo/hermes-session-tasks/plugin` | same |

`diff` of the two records printed no difference. The scratch home is removed (`test ! -e "$H"` passed).

### Host probe (read only)

Aliases probed: 9 (every `Host` line of `~/.ssh/config` without a wildcard). Probe: `ssh -o BatchMode=yes -o ConnectTimeout=10`, then `command -v hermes`, `~/.local/bin/hermes`, version, plugin slot, gateway status.

Hosts where Hermes answered: 0.

| Result | Number of aliases |
|--------|------------------:|
| Reachable, no Hermes (no `hermes` on the path, none in `~/.local/bin`, no `~/.hermes` folder) | 3 |
| Git servers that refuse a shell command | 3 |
| BatchMode refused: host key not yet trusted on this machine | 2 |
| Connection timed out | 1 |

No change was made on any host. No IP address and no alias is recorded here, per threat T-07-26.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Revision compared to the public head, not local main**
- **Found during:** Task 1, step 4
- **Issue:** The plan compares the install revision to `git rev-parse main`. Local `main` is 206ec79, four planning commits ahead of the pushed head. The public repo serves d39efa9.
- **Fix:** Compared to `git rev-parse public/main` and `git ls-remote public refs/heads/main`. Both print d39efa98f8568cc3c393e7ebecdf5e20e3a2b9e5. Task 3 step 7 already compares `plugin/` and `catalog/` between d39efa9 and HEAD, so the installed code and the local code stay linked.
- **Files modified:** none

**2. [Rule 3 - Blocking] Install record path**
- **Found during:** Task 1, step 4
- **Issue:** The plan reads `<home>/plugins/hermes-session-tasks/.install-metadata.json`. The CLI writes one file for all plugins at `<home>/plugins/.install-metadata.json` (`hermes_cli/plugins_cmd_git.py:33-34`). The `source` value is `https://github.com/theo-deyle/hermes-session-tasks.git#plugin`, which holds `theo-deyle/hermes-session-tasks`.
- **Fix:** Read the file at the real path. Task 3 must read `~/.hermes/plugins/.install-metadata.json` on the named host.
- **Files modified:** none

**3. [Note] `hermes plugins list` table**
The table view truncates plugin names, so a grep for `session-tasks` found nothing. The `--json` form was used for every record.

**Total deviations:** 2 auto-fixed (Rule 3), 1 note. **Impact:** none on the result.

## Tasks 2 and 3

Open. Task 2 awaits Theo's answer. Task 3 starts after the continuation agent records the `Proof host:` line.
