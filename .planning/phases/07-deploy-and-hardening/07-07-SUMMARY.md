---
phase: 07-deploy-and-hardening
plan: 07
subsystem: infra
tags: [hermes-cli, plugin-install, catalog-readiness, ssh-probe]
requires:
  - phase: 07-deploy-and-hardening
    provides: 07-06 public repo theo-deyle/hermes-session-tasks at head d39efa9
provides:
  - Proof that one hermes plugins install line installs and enables the plugin from the public repo, in a fresh home on devpc and on a second Hermes host (Windows) that Theo ran himself
  - A read-only probe of the SSH hosts for a second Hermes host
  - The catalog readiness outputs on the pushed head (validate, doctor, catalog validator, catalog test) and the submission checklist line by line
affects: [07-08, 07-09]
requirements: [DEV-04, DEV-06]
status: complete
plan_head_before: 206ec79e0fb38958d0a40abfdb14bcf0154f7b0d
plan_head_after: 009b1e8bc2c3fdb6d6ffce9653c065583cb1dec6
commits: 2
actuals:
  tokens: 4200
  tasks: 3
  commits: 2
---

# Phase 7 Plan 07: Host install proof Summary

One `hermes plugins install` line installs and enables the plugin from the public repo in a fresh Hermes home on devpc and on a second Hermes host that Theo ran himself, and the pushed head passes the four catalog readiness checks.

Note on the commit count: `plan_head_after` is the head before the closing SUMMARY commit. `commits: 2` counts the partial SUMMARY commit (009b1e8) and the closing SUMMARY commit.

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

## Task 2 decision

Theo read the question of Task 2. He chose the second host. The probe found no host that devpc reaches with a key, so he ran the install line himself on his own Hermes host (Windows). devpc has no SSH access to that host. His pasted output, in the next section, is the proof.

Proof host: Theo's own Hermes host (Windows), not devpc

## Task 3: second host and catalog readiness

### Install on the second host (run by Theo)

Theo ran `hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable` in a PowerShell prompt on 2026-11-03. The output below is his paste, word for word. The user name in the path is masked as `<user>`. The prompt line is left out. The box and check mark characters and the em dash are dropped, as in Task 1.

```
Skipping unreadable plugin directory homeassistant: [WinError 5] Access is denied: 'C:\\Users\\<user>\\AppData\\Local\\hermes\\plugins\\homeassistant\\plugin.yaml'
Warning: custom (unreviewed) source - not from the Hermes catalog.
Cloning https://github.com/theo-deyle/hermes-session-tasks.git (subdir: plugin)...
Skipping unreadable plugin directory homeassistant: [WinError 5] Access is denied: 'C:\\Users\\<user>\\AppData\\Local\\hermes\\plugins\\homeassistant\\plugin.yaml'

Installed
Plugin installed: theo-deyle/hermes-session-tasks#plugin
Location: C:\Users\<user>\AppData\Local\hermes\plugins\hermes-session-tasks

Plugin hermes-session-tasks enabled.
```

The two `homeassistant ... Access is denied` lines come from a permission problem of another plugin folder on that host. They have nothing to do with this plugin.

The CLI wrote the enable line itself. Nobody edited a `config.yaml` by hand. Theo was told to restart the gateway of that host himself.

### Diff check (step 7)

`git diff --quiet d39efa9 HEAD -- plugin catalog` exits 0. `plugin/` and `catalog/` at HEAD (009b1e8) equal the public head d39efa98f8568cc3c393e7ebecdf5e20e3a2b9e5 of 07-06. The code on the public repo is the code checked here.

### Catalog readiness outputs (step 8)

`timeout 120 hermes plugins validate plugin --install-deps`, exit 0:

```
  Command helper: applied 2 secrets

 manifest - plugin.yaml parses
 manifest fields - name, version, description present
 requires_hermes - spec '>=0.22.5' parses
 config schema - not declared
 requires_env - all entries UPPER_SNAKE
 oauth - not declared
 loadable - entry: __init__.py, desktop/plugin.js
 python dependencies - none declared
 capability probe - register() ran in isolation
 declared tools - matches registrations
 declared hooks - matches registrations
 declared middleware - matches registrations
 built-in tool collisions - no collisions
 security scan - safe
 no core override - no runtime rebinds of Hermes core
 desktop surface - stays inside the plugin SDK surface
 Isolation - runs in the plugin host (plugins.isolation: host)
   dashboard backend API is served through the plugin host (buffered responses)

Validation passed.
```

`timeout 120 hermes plugins doctor plugin --ci`, exit 0:

```
  Command helper: applied 2 secrets
Plugin Doctor: /home/theo/local_repo/hermes-session-tasks/plugin
  manifest: hermes-session-tasks 0.2.0 (standalone)
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 4 tool(s), 4 hook(s)
```

`~/.hermes/hermes-agent/venv/bin/python ~/.hermes/hermes-agent/scripts/validate_plugin_catalog.py catalog/hermes-session-tasks.yaml`, exit 0:

```
OK: 1 file(s) valid
```

`uv run pytest tests/test_catalog_entry.py -q -rs -m hermes`, exit 0:

```
..                                                                       [100%]
2 passed, 7 deselected in 0.27s
```

0 tests skipped.

### Submission checklist (step 9)

Source: `~/.hermes/hermes-agent/website/docs/developer-guide/plugins/catalog-submission.md`. The pull request itself is deferred, as the plan allows.

Before you submit:

1. Public repository - met. `https://github.com/theo-deyle/hermes-session-tasks` is public; the install above cloned it with no login (Task 1 and the second host).
2. Loadable plugin at the pinned commit - met. `plugin/plugin.yaml` plus `__init__.py` and `desktop/plugin.js`; validate check `loadable`; `subdir: plugin` in the catalog entry.
3. Public surfaces only - met. Validate checks `no core override` and `desktop surface` both pass.
4. Validation passes locally - met. `hermes plugins validate plugin --install-deps` prints `Validation passed.`

Opening the PR:

5. One file `plugin-catalog/<name>.yaml` - not applicable now. The pull request is deferred. `catalog/hermes-session-tasks.yaml` is ready and the catalog validator prints `OK: 1 file(s) valid`.
6. Pin `sha` to a full 40-character commit, quote `version` - deferred to submission. The file holds a placeholder `sha` on purpose (marked in its first comment line); `version` is quoted ("0.2.0").
7. PR description with what the plugin does, surfaces and rule 13 disclosures - deferred to submission. The disclosure text already sits in the `description` field of the entry and in `README.md`.
8. Catalog CI green - deferred to submission. The same `hermes plugins validate` check passes locally.
9. Maintainer review - not applicable now.

Admission rules:

1. Human-merged gate - not applicable now; a maintainer step.
2. Exact SHA pin - deferred to submission; placeholder `sha` is set on purpose and replaced at submission.
3. No self-updating code - met. The code has no network call, no downloader and no remote loader (a search of `plugin/` for `urllib`, `requests`, `httpx`, `subprocess`, `socket`, `eval(`, `new Function` and `fetch(` finds nothing).
4. SHA bumps are new PRs - not applicable now.
5. Owner submission - met. `maintainer: theo-deyle` owns the repo `theo-deyle/hermes-session-tasks`.
6. Declared capabilities match - met. Validate checks `declared tools`, `declared hooks` and `declared middleware` all pass; the catalog entry lists the same 4 tools and 4 hooks as `plugin.yaml`.
7. Install scanner at admission - met. Validate `security scan - safe`.
8. Desktop stays inside the SDK surface - met. Validate `desktop surface` passes.
9. No runtime overrides of Hermes core - met. Validate `no core override` passes.
10. Dependency security policy - met, not applicable in effect. `python dependencies - none declared`.
11. Credentials through Hermes - met. The plugin holds no credential and declares no `requires_env`, `config_schema` or `oauth`.
12. Approvals and unattended runs - met. The plugin runs no shell command and spawns no child process; it waits for no person.
13. Risky behaviour disclosed - met. `README.md` lines 57-58 and the entry `description` state: reads `state.db` of the active profile read-only, no network calls, no shell commands, no credentials, no telemetry.
14. Compatibility metadata truthful - met. `requires_hermes: ">=0.22.5"` is a SemVer floor, equal to the running Hermes v0.22.5. `version` 0.2.0 equals `plugin.yaml` and the entry.
15. No skins or forks of bundled plugins - met. The plugin is original work, not a fork or skin.
16. One listing per lineage - met. No other listing of this plugin exists; it is not a fork.
17. No unscannable executable payloads - met. `git ls-files plugin` and `git ls-tree` of d39efa9 list no `.pyc`, `.pyo`, `.so`, `.dll`, `.exe`, `.wasm` or archive file. (Local `__pycache__` folders exist on disk but are untracked.)

## Verify results

1. `grep -c "Plugin hermes-session-tasks enabled."` on this file - prints a number above 0 (fresh home and second host both hold the line).
2. `grep -c "already up to date"` on this file - prints a number above 0 (fresh home).
3. `readlink -f ~/.hermes/plugins/hermes-session-tasks` equals `$(pwd)/plugin` - passes.
4. First automated verify of Task 3 (a `grep` for the devpc-proof line or for a host-update line) - does not apply. Theo named a second host, so the first pattern is not present. The second host's update step did not run from devpc, so no host-update line exists. See deviation 4.
5. `timeout 120 hermes plugins validate plugin --install-deps` - exit 0, `Validation passed.`
6. `timeout 120 hermes plugins doctor plugin --ci` - exit 0.
7. Catalog validator - exit 0, `OK: 1 file(s) valid`.
8. `uv run pytest tests/test_catalog_entry.py -q -rs -m hermes` - exit 0, 2 passed, 0 skipped.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Revision compared to the public head, not local main**
- **Found during:** Task 1, step 4
- **Issue:** The plan compares the install revision to `git rev-parse main`. Local `main` is 206ec79, four planning commits ahead of the pushed head. The public repo serves d39efa9.
- **Fix:** Compared to `git rev-parse public/main` and `git ls-remote public refs/heads/main`. Both print d39efa98f8568cc3c393e7ebecdf5e20e3a2b9e5. The Task 3 diff check confirms `plugin/` and `catalog/` are the same at d39efa9 and HEAD.
- **Files modified:** none

**2. [Rule 3 - Blocking] Install record path**
- **Found during:** Task 1, step 4
- **Issue:** The plan reads `<home>/plugins/hermes-session-tasks/.install-metadata.json`. The CLI writes one file for all plugins at `<home>/plugins/.install-metadata.json` (`hermes_cli/plugins_cmd_git.py:33-34`). The `source` value is `https://github.com/theo-deyle/hermes-session-tasks.git#plugin`, which holds `theo-deyle/hermes-session-tasks`.
- **Fix:** Read the file at the real path.
- **Files modified:** none

**3. [Note] `hermes plugins list` table**
The table view truncates plugin names, so a grep for `session-tasks` found nothing. The `--json` form was used for every record.

**4. [Rule 3 - Blocking] Second host cannot be reached from devpc; Theo ran the install himself**
- **Found during:** Task 2 and Task 3
- **Issue:** devpc has no SSH access to the second Hermes host (Windows) that Theo chose. Steps 2, 4, 5 and 6 of Task 3 (the pre-check, the install record check, doctor, list, update and the gateway restart on that host) could not run from devpc.
- **Fix:** Theo ran the install line on that host himself. The `Installed` box and the `Plugin hermes-session-tasks enabled.` line of the CLI are the proof of DEV-04 on a second host. Theo was told to restart that host's gateway himself. No doctor, list, update or install record output exists for that host.
- **Effect on verify:** No host-update line exists, so the first automated verify of Task 3 does not apply (see verify result 4).
- **Files modified:** none

**Total deviations:** 3 auto-fixed (Rule 3), 1 note. **Impact:** the second host proves the install and enable lines only. The doctor, list and update checks are proven on the fresh home of devpc.

## Threat flags

None. No file other than this SUMMARY changed.

## Known Stubs

None. The placeholder `sha` in `catalog/hermes-session-tasks.yaml` is intentional (marked in the file) and is set at submission.

## Self-Check: PASSED

- SUMMARY file exists.
- Commit 009b1e8 is an ancestor of HEAD.
- Verify lines 1 to 3 and 5 to 8 pass. Verify line 4 does not apply (deviation 4).
- The tree was clean before this SUMMARY changed.
