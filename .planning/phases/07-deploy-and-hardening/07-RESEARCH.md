# Phase 7: Deploy and hardening - Research

**Researched:** 2026-11-03
**Domain:** Hermes plugin install paths (CLI and Desktop), plugin catalog readiness, public GitHub push, CI, restart procedure, small hardening fixes
**Confidence:** HIGH (most findings were run in this session, not only read)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-47:** Every Hermes host other than devpc installs the plugin with `hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable` and updates it with `hermes plugins update hermes-session-tasks`. The gateway restart after install or update is announced before it happens. devpc keeps the symlink `~/.hermes/plugins/hermes-session-tasks -> <repo>/plugin`, because a linked package is the documented dev mode with pane hot reload. No custom deploy script. - **Reversibility:** reversible - one documented command per host.
- **D-48:** Every Desktop machine installs the pane from Capabilities, Plugins, Install from Git, with the identifier `theo-deyle/hermes-session-tasks#plugin` and the Desktop target checked. When Hermes and Desktop run on the same machine, the package copy happens on its own and no Git install is needed. `scripts/install-desktop.ps1` stays in the repo as the fallback and is documented as such; it is no longer the primary path. - **Reversibility:** reversible.
- **D-49:** The repo layout stays: `plugin/` is the package, `pyproject.toml` and `tests/` stay at the repo root. The catalog entry points `subdir` at `plugin`. Both the Hermes CLI and the Desktop app accept the `#plugin` form (`hermes_cli/plugins_cmd_git.py:193-215`, `apps/desktop/electron/desktop-plugin-install.ts:56-104`). - **Reversibility:** costly - a move of `plugin.yaml` to the root would make the dev `pyproject.toml` count as the plugin's runtime dependency list.
- **D-50:** The code moves to a new public GitHub repo `theo-deyle/hermes-session-tasks` on Theo's personal account, full history, no squash. Before the first push, Claude scans the whole history for secrets, tokens, customer data and internal host names, and reports the result in the plan summary. The org repo `Don-Mor-Software-Group/hermes-session-tasks` is left as it is in this phase. - **Reversibility:** one-way - a public push publishes the history; a later takedown does not unpublish copies. The planner puts a `checkpoint:decision` before the push task.
- **D-51:** The repo holds a ready catalog entry file (the `plugin-catalog/<name>.yaml` shape from `catalog-submission.md`, with `repo`, `subdir: plugin`, quoted `version`, `capabilities`, and a `sha` placeholder named as such) under `catalog/hermes-session-tasks.yaml`. It is not submitted. Research names the exact entry schema from `plugin-catalog/README.md` in the Hermes repo.
- **D-52:** `hermes plugins validate plugin --install-deps` is the pass rule for catalog readiness, and `hermes plugins doctor` runs against the installed package. Both run in the plan and their output is recorded. A GitHub Actions workflow runs `./scripts/check.sh` on push, following the precedent `~/.hermes/plugins/hermes-memory-ui/.github/workflows/ci.yml`.
- **D-53:** Every user-facing string loses the name "Theo" and the host name "devpc": `plugin.yaml` description, the tool descriptions and system prompt text in `plugin/session_tasks/tool_text.py`, `plugin/skills/board-rules/SKILL.md`, the one string in `plugin/desktop/plugin.js`, and the README. "Theo" becomes "the user". The behaviour rules stay word for word otherwise. Pass rule: the Phase 2 and Phase 5 headless own-plan check still scores 3 of 3 with the new wording, and the ask-before-destroy live rule still holds. - **Reversibility:** reversible.
- **D-54:** The README becomes the catalog page: what the plugin is in one sentence, install on a host, install the pane, update, known behaviour (the line "closing the only pane disables the plugin" stays). The devpc dev setup, the symlink, the gateway restart rule and the PowerShell fallback move to `CONTRIBUTING.md`. Plain language, no em dash or en dash.
- **D-55:** A gateway restart on devpc does not restart the Desktop SSH backends (`serve --isolated`). The plan reuses the Phase 6 procedure: list every `~/.hermes/desktop-ssh/*/backend.lock.json`, match each pid to its lock and to a `serve --isolated` command line, and stop only matched pids, after Theo's go. Desktop starts a new backend with the new code on its next connect. The `/meta` version check then runs against every live backend port.
- **D-56:** In scope: the three pane review warnings from `06-UI-REVIEW.md` (notice `role: 'status'`, focus back to the picker trigger after Back, `rounded-md` on the banner), the stale layout line 94 of `06-UI-SPEC.md`, and review note IN-05 (`SESSION_ID_MAX` in one place). Out of scope, stay deferred: IN-01, IN-02, IN-03, IN-04, IN-06, IN-07.
- **D-57:** The full loop runs once on the Mac and once on a Windows PC through the new install path, four steps each: the agent lists items, the pane shows them live, Theo edits one, the agent sees the edit on its next turn. Each machine gets one request per turn, in plain words, and the result is recorded word for word.

### Claude's Discretion

- The exact neutral wording of each string, as long as the behaviour rules stay.
- The CI workflow file content, the Python versions matrix (3.11 and 3.14), and the badge.
- The history scan method and the list of patterns it checks.
- The order of the plans.

### Deferred Ideas (OUT OF SCOPE)

- The actual catalog pull request to `NousResearch/hermes-agent`. Theo opens it when he wants the listing.
- Review notes IN-01, IN-02, IN-03, IN-04, IN-06, IN-07 (see D-56).
- What to do with the org repo `Don-Mor-Software-Group/hermes-session-tasks` after the move.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEV-04 | The plugin installs on any Hermes host with `hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable` and its pane on any Desktop machine from the Plugins page. devpc keeps the symlink as the dev mode. The gateway restart is announced before it happens. (REQUIREMENTS.md:67) | Sections "CLI install", "Desktop install", "Restart procedure". The CLI form works as written. The Desktop form `owner/repo#plugin` does NOT work (see Correction 1). |
| DEV-06 | The repo is pushed to the public GitHub repo `theo-deyle/hermes-session-tasks` with a plain-language README, a CONTRIBUTING file, a ready catalog entry file and CI, and `hermes plugins validate` passes. (REQUIREMENTS.md:69) | Sections "Catalog entry", "History scan", "GitHub push", "CI", "Neutral wording", "Hardening fixes". |
</phase_requirements>

## Summary

The install path works as designed on the Hermes CLI side. I ran the real command against a copy of the repo in a scratch `HERMES_HOME` and it installed to `<home>/plugins/hermes-session-tasks`, wrote `plugins.enabled`, recorded the source and revision, passed `plugins doctor`, and `plugins update` pulled a new commit. `hermes plugins validate plugin --install-deps` passes 16 of 16 checks today. The history holds no token, key, JWT or private IP. It holds the personal and host names that the success criteria call out, mostly in `.planning/`.

Four findings change the plan. (1) The Desktop app does NOT accept `owner/repo#plugin`; it needs `owner/repo/plugin` or a full URL. (2) `GET /meta` cannot prove which code a backend runs: it reads `plugin.yaml` from disk on every request, and a Desktop backend's token file is deleted at start. Use process start time against the last `plugin/` commit instead. (3) With `subdir: plugin`, the catalog page renders `plugin/README.md`, not the root `README.md`. (4) Strings with "Theo" reach the model in two more files than CONTEXT lists: `delta.py` and `guard.py`.

**Primary recommendation:** Keep `plugin/` as the package. Fix the identifier text for Desktop to `https://github.com/theo-deyle/hermes-session-tasks#plugin`. Bump the version to one new value so the pane banner can tell old from new. Put a `checkpoint:decision` before the public push that names what goes public (all of `.planning/`, `.claude/CLAUDE.md`, `handoff/`, the work email in 426 commits).

## Corrections to CONTEXT.md (the planner must apply these)

| # | CONTEXT says | Evidence | Fix |
|---|--------------|----------|-----|
| 1 | D-48/D-49: the Desktop app accepts `theo-deyle/hermes-session-tasks#plugin` | The Desktop parser has no `#` branch for the shorthand form. I ran lines 49-125 of `desktop-plugin-install.ts` in node. Result: `theo-deyle/hermes-session-tasks#plugin => {"gitUrl":"https://github.com/theo-deyle/hermes-session-tasks#plugin.git","subdir":null}`. That clones a wrong URL. [VERIFIED: apps/desktop/electron/desktop-plugin-install.ts:49-100, run in node 24.19.0] | In the Desktop dialog use `https://github.com/theo-deyle/hermes-session-tasks#plugin` or `theo-deyle/hermes-session-tasks/plugin`. Both gave `subdir: "plugin"` in the same run. The CLI accepts all three forms (run below). Put the Desktop form in README and CONTRIBUTING. |
| 2 | D-48: "the Desktop target checked" | In Desktop source (commit date 2026-10-22) the install dialog has no checkbox. It lists "This package includes: Agent plugin / Desktop UI" and installs every half the repo has. The words "Desktop target" appear only in the docs and in an i18n tooltip. [VERIFIED: apps/desktop/src/app/settings/plugin-install-details.tsx:104-150, src/i18n/en.ts:2109] | Write the README step as "paste the URL, press Install". The Mac and Windows app versions may differ from this source. Record what the dialog shows on each machine in the live pass. |
| 3 | D-55 and success criterion 2: read `/meta` on every backend port | `meta()` reads `plugin.yaml` from disk at request time, so a stale backend reports the new version once the file changes. [VERIFIED: plugin/session_tasks/version.py:44-51] The route needs the session header, and the token file is read and unlinked at backend start. [VERIFIED: hermes_cli/main_dashboard.py:744-745 docstring "Read and unlink a Desktop SSH token"; I ran a check and the token file for pid 1960156 was already gone] | Prove "new code" by process start time after the last `plugin/` commit time (the method Phase 3 and Phase 6 used). The pane's own version banner on each Desktop is the live `/meta` check. An unauthenticated GET returns 401, which proves only that the route is mounted. |
| 4 | D-53 lists the files that name "Theo" | Also user-visible to the model: `plugin/session_tasks/delta.py:16-17` (`DELTA_NOTE`, `POINTER_TEXT`) and `plugin/session_tasks/guard.py:62-63` (tool error text). Docstrings and comments with "Theo" sit in `hooks.py`, `store.py`, `rows.py`, `board_api.py`, `guard.py`, `delta.py`, `plugin.js:4`. `tool_text.py` has 17 hit lines, not 12. [VERIFIED: grep, see "Neutral wording"] | Include all of `plugin/` in the wording plan. Tests pin these strings (`tests/test_delta.py`, `test_guard.py`, `test_tool_text.py`), so the plan updates tests with the strings. |
| 5 | D-51: file at `catalog/hermes-session-tasks.yaml` is the only catalog-page artefact | With `subdir` set, the docs build reads `<subdir>/README.md` only. [VERIFIED: website/scripts/extract-plugins.py:86-95] | Add `plugin/README.md` (the user page). A test keeps it equal to the user part of the root README, or the root README becomes a short pointer. |
| 6 | D-51: "sha placeholder" | An all-digit placeholder parses as the YAML integer 0 and the loader rejects it. [VERIFIED: ran `entry_from_mapping`: "sha must be a full 40-character hex commit SHA (got 0)"] A quoted `"0000000000000000000000000000000000000001"` passes both validators. | Quote `sha` always. Use a quoted 40-hex dummy plus a `# PLACEHOLDER` comment. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Install the Python half and enable it | Hermes CLI on the host (`hermes plugins install`) | Gateway RPC from Desktop (`installAgentPlugin`) | The CLI owns `plugins/` and `plugins.enabled`. [VERIFIED: hermes_cli/plugins_cmd_install.py:683-708] |
| Install the pane (Desktop half) | Electron main process on each Desktop machine | Package copy from a local `plugins/` folder | Remote backend cannot be read as a filesystem, so Desktop clones the half itself. [CITED: desktop-plugin-sdk.md:1766-1773] |
| Catalog entry and its checks | Repo `catalog/` file | Hermes `validate_plugin_catalog.py`, `entry_from_mapping` | Submission is deferred, so the file only has to pass the same validators. |
| Version proof after restart | Process table on devpc | Pane banner on each Desktop | `/meta` reads disk, not loaded code. |
| History scan and public push | Developer box (git, gh) | GitHub | One-way step with a decision checkpoint. |
| CI | GitHub Actions runner | `scripts/check.sh` | Same gate as local. |

## Standard Stack

No new runtime package. The plugin stays stdlib plus fastapi and pydantic. [VERIFIED: pyproject.toml `dependencies = []`; `hermes plugins validate` "python dependencies - none declared"]

### Core (tools used by this phase)

| Tool | Version | Purpose | Source |
|------|---------|---------|--------|
| `hermes` CLI | v0.22.5 (2026.9.24) | install, update, validate, doctor | [VERIFIED: `hermes --version`] |
| `gh` | signed in as `theo-deyle`, scopes `admin:org, admin:public_key, gist, project, repo` | create repo, API checks | [VERIFIED: `gh auth status`] |
| `git` over SSH | `ssh -T git@github.com` answers `Hi theo-deyle!` | push | [VERIFIED: run] |
| uv | 0.11.26 | `scripts/check.sh` | [VERIFIED: `uv --version`] |
| node | 24.19.0 on devpc | `node --check`, VM harness in tests | [VERIFIED: PROJECT.md stack table] |

### CI actions (the only external code the phase adds)

| Action | Pin to | Evidence |
|--------|--------|----------|
| `actions/checkout` | `@v7` | latest release `v7.0.1`; ref `v7` exists [VERIFIED: gh api repos/actions/checkout] |
| `actions/setup-node` | `@v7` | latest release `v7.1.0`; ref `v7` exists [VERIFIED: gh api] |
| `astral-sh/setup-uv` | `@v10.3.3` (exact) | latest release `v10.3.3`; NO floating `v10` ref (404). The precedent also pins an exact tag (`v8.3.2`). [VERIFIED: gh api] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib history scan script | gitleaks, trufflehog, detect-secrets | None is installed here (`command -v` found none of gitleaks, trufflehog, detect-secrets, git-secrets, ggshield, semgrep). The stdlib scan below covers the pattern list. Adding a scanner is a new tool; skip it. |

**Installation:** none.

## Package Legitimacy Audit

No external package is installed by this phase. The three GitHub Actions above are first-party (`actions/*`) or the uv vendor (`astral-sh`), and the memory-ui precedent uses the same three. Package gate: not applicable.

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| (none) | - | - | - |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### Install paths (data flow)

```
                      public GitHub repo theo-deyle/hermes-session-tasks
                      (plugin/ = package, catalog/ = entry file, README, CI)
                         |                         |                        |
        CLI on a host    |                         | Desktop dialog         | catalog PR (deferred)
 hermes plugins install  |                         | "Install from Git"     |
   theo-deyle/...#plugin |                         |  paste URL + #plugin   v
        --enable         v                         v                 plugin-catalog/<name>.yaml
  blobless sparse clone of plugin/     probe (Electron main, own git clone)
  -> <HERMES_HOME>/plugins/<name>               |
  -> plugins.enabled += name                    +-- agent half --> gateway RPC --> same CLI code
  -> activation line (hooks live now,           |   (on devpc the symlink already exists: expect
     tools next session)                        |    "already installed" for this half)
         |                                      +-- desktop half --> <app home>/desktop-plugins/<name>/
         v                                          (local copy when Hermes is on the same machine,
  restart gateway (announced)                        git clone when the backend is remote)
                                                         |
                                         pane loads, opt-in toggle may be needed
```

### Recommended repo additions

```
catalog/hermes-session-tasks.yaml   # entry file, quoted dummy sha
CONTRIBUTING.md                      # devpc dev setup, symlink, restart rule, PowerShell fallback
LICENSE                              # see Open Question 3
README.md                            # catalog page, no personal or host names
plugin/README.md                     # what the docs page renders when subdir is set
.github/workflows/ci.yml             # runs ./scripts/check.sh
scripts/history_scan.py              # stdlib scan, counts only (draft in "History scan")
```

### Pattern 1: CLI install (verified end to end)

I ran these in a scratch home (`HERMES_HOME=<scratch>/home1`) against `file://` clones of this repo. Nothing touched the real `~/.hermes`.

```bash
HERMES_HOME=<scratch> hermes plugins install "file:///<repo>#plugin" --enable
```

Observed:
- Output: `Warning: custom (unreviewed) source`, `Cloning ... (subdir: plugin)`, `Installed`, `Plugin hermes-session-tasks enabled.`
- Landed in `<home>/plugins/hermes-session-tasks` with no `.git` folder. The folder name is the manifest `name`, not `plugin`.
- `config.yaml` got `plugins: enabled: [hermes-session-tasks]` from the CLI.
- `.install-metadata.json` holds `"pinned": false`, the full revision, and `"source": "file://...#plugin"`.
- `hermes plugins doctor hermes-session-tasks` (installed id) printed `OK: runtime discovery, manifest parsing, import, and registration passed` and `registrations: 4 tool(s), 4 hook(s)`.
- After a new commit in the source repo, `hermes plugins update hermes-session-tasks` printed `Plugin hermes-session-tasks updated. Re-installed from ...#plugin: 1c0f7244..bff83821` and the file changed on disk. With no new commit it printed `already up to date`.

[VERIFIED: ran in this session; code at hermes_cli/plugins_cmd.py:292-330 and plugins_cmd_git.py:207-258]

Identifier forms the CLI resolver accepted, all returning `('https://github.com/theo-deyle/hermes-session-tasks[.git]', 'plugin')`: `owner/repo#plugin`, `owner/repo/plugin`, `https://github.com/owner/repo#plugin`, `https://github.com/owner/repo/tree/main/plugin`. [VERIFIED: ran `_resolve_git_url`]

Private repos work in the CLI: it tries anonymous first, then `GITHUB_TOKEN`, then `gh auth token`. [CITED: hermes_cli/git_credentials.py:1-25] The Desktop app runs git with `GIT_TERMINAL_PROMPT=0, GIT_ASKPASS=echo` and no credential fallback. [VERIFIED: desktop-plugin-install.ts:257-264] So the repo must be public before the Mac and Windows live pass.

Install side effects the planner must know:
- The command prints "custom (unreviewed) source" for any non-catalog install. This is normal.
- Dependency consent is fail-closed in non-interactive sessions. This plugin declares no Python dependencies, so no `--yes-deps` is needed. [VERIFIED: validate output "python dependencies - none declared"]
- `--enable` calls `report_activation`, which prints what is live now and what waits for the next session. Hooks go live at once; Python tools and prompt sections wait for the next session. [CITED: hermes_cli/plugins_activation.py:1-12] The dashboard routes still need a backend restart (Phase 3 measurement, 03-08 SUMMARY).

### Pattern 2: Desktop install against a remote backend

Flow in `plugin-install-run.ts:176-216` [VERIFIED]:
1. The dialog probes the repo through Electron main (`probePluginRepo`) with the pasted text. A bad identifier fails here.
2. The agent half installs on the backend through the gateway (`installAgentPlugin`), which uses the Python resolver.
3. With a remote backend, `desktopHalfFromPackage` is false, so Desktop clones the desktop half into `<app home>/desktop-plugins/hermes-session-tasks/` and writes a `.hermes-package.json` marker.
4. If the agent half was enabled, `enablePackageDesktopHalf` turns the pane on.

Consequences for the live pass on the Mac and the Windows PC (both connect to devpc over SSH):
- devpc holds the symlink, so the agent half answers "already installed". The desktop half still installs, but the dialog ends in a failed state with that message. Expect it; record it word for word. [VERIFIED by reading the control flow: `installDesktopHalf` runs after a failed agent result; final `report.errors` gives `status: failed`.] Do not tick Force on devpc: Force would replace the dev symlink install. [ASSUMED: Force replaces the symlink target; not run]
- The desktop half then stays opt-in (disabled). The user turns it on under Capabilities, Plugins. [CITED: desktop-plugin-sdk.md:1745-1760]
- If `install-desktop.ps1` ran on that machine earlier, a marker-less `desktop-plugins/hermes-session-tasks/plugin.js` exists. Install from Git then says `Desktop plugin 'hermes-session-tasks' already exists. Enable force reinstall to replace it.` Tick Force reinstall (Advanced) on the Mac and the Windows PC, or delete that folder first. [VERIFIED: desktop-plugin-install.ts:443-452; script path from scripts/install-desktop.ps1 `$PluginId`]
- Desktop needs `git` on PATH on each machine. [ASSUMED: present on the Mac and Windows PC; the code runs `git --version` first, desktop-plugin-install.ts:493-498]

A real second Hermes host does not exist in this setup (the Mac and Windows PC attach to devpc). Prove criterion 1 by a scratch-home install from the public GitHub URL on devpc after the push (same command, `HERMES_HOME=<scratch>`). Say so in the plan; a true second host is Theo's call.

### Pattern 3: Catalog entry (draft, passes both validators)

I validated this draft with `scripts/validate_plugin_catalog.py` (`OK: 1 file(s) valid`) and with `hermes_cli.plugin_catalog.entry_from_mapping` (returned `install_identifier = https://github.com/theo-deyle/hermes-session-tasks#plugin`). [VERIFIED: ran both]

```yaml
# PLACEHOLDER: replace sha with the pinned commit when the entry is submitted.
name: hermes-session-tasks
title: Session Tasks
repo: https://github.com/theo-deyle/hermes-session-tasks
sha: "0000000000000000000000000000000000000001"
subdir: plugin
version: "0.1.0"
description: "A per-session task board. The agent adds the things you must do, decide or remember; you check, edit and delete them in a Hermes Desktop side pane. Disclosure - stores boards in its own SQLite file under the active profile's plugin-data folder; reads the active profile's state.db read-only for session titles and lineage; no network calls, no shell commands, no credentials, no telemetry."
maintainer: theo-deyle
tier: community
category: desktop
requires_hermes: ">=0.22.5"
docs_url: https://github.com/theo-deyle/hermes-session-tasks#readme
platforms: []
capabilities:
  provides_tools:
    - board_read
    - board_edit
    - board_sessions
    - board_copy
  provides_hooks:
    - pre_tool_call
    - post_compaction
    - pre_llm_call
    - on_session_delete
  provides_middleware: []
  requires_env: []
```

Schema facts, all from `plugin-catalog/README.md:156-187` and `hermes_cli/plugin_catalog.py:43-58,130-160` [VERIFIED: read]:
- Required by the loader: `name` (`[a-z0-9_-]{1,64}`), `repo` (https), `sha` (40 hex), `tier` in `official|verified|community`, `category` in the nine shelves. `description` and `maintainer` are plain strings the validators expect.
- `subdir` is a real, optional field: `[A-Za-z0-9._/-]+`, no `..`, no empty segments. `install_identifier` is `repo#subdir`.
- `version` matches `^[A-Za-z0-9][A-Za-z0-9._+-]{0,31}$`; quote it. Cosmetic only.
- `sha` is pinned to a commit; a branch, tag or short sha is rejected (rule 2). Quote it: an unquoted hash can parse as a number.
- `image` and `screenshots` must be https on `raw.githubusercontent.com`, `github.com` or `*.githubusercontent.com`, pinned to the commit sha.
- `known_issues` shows at the install prompt. Candidate text: "Closing the only pane disables the plugin."
- Rule 13 wants disclosure in the description and the README: reads `state.db` read-only, no network, no shell, no credentials. [VERIFIED: plugin/session_tasks/session_reader.py:9-16 reads `SessionDB(read_only=True)`; grep for `requests|urllib|subprocess|socket` in `plugin/session_tasks` found none]
- Name collision check: no catalog file named `*session-tasks*` exists. [VERIFIED: `ls plugin-catalog | grep -i session-tasks` empty] Near neighbours (`hermes-board`, `boardstate`, `duty-board`, `git-tasks`, `next-steps`) are different plugins, so rule 16 is not in play.
- Rules that apply and pass today: rule 6 (capabilities match, `validate` "declared tools/hooks - matches registrations"), rule 7 (`security scan - safe`), rule 8 (`desktop surface - stays inside the plugin SDK surface`), rule 9 (`no core override`), rule 14 (`requires_hermes >=0.22.5` equals the current release), rule 17 (no tracked `.pyc`: `git ls-files | grep -c pyc` = 0). [VERIFIED: validate run 2026-11-03]

A hermes-marked test should check: entry `name` equals the manifest name, `version` equals `plugin.yaml` version, `capabilities` equal `provides_tools` and `provides_hooks`, and `entry_from_mapping` returns a value. Add a non-hermes test that runs the same checks with stdlib only (parse the YAML lines the test needs, or use the dummy sha pattern).

### Anti-Patterns to Avoid

- **Unquoted `sha`:** parses as a number when it is all digits or looks like a float. Always quote.
- **A README only at the repo root:** the docs page then shows nothing (reads `plugin/README.md`).
- **Trusting `/meta` after a restart:** it reports the disk file.
- **`hermes serve --stop` to restart backends:** it stops every dashboard process of the home with a SIGTERM-then-SIGKILL path. [CITED: hermes_cli/main.py:2481-2493] Phase 6 used an owner-checked SIGTERM only. Keep that.
- **Force reinstall on devpc from Desktop:** can replace the dev symlink install.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Install, enable, update on a host | A deploy script | `hermes plugins install ... --enable` / `update` | Verified above; D-47 forbids a custom script. |
| Catalog schema check | A schema validator | `scripts/validate_plugin_catalog.py` and `entry_from_mapping` from the Hermes checkout | They are the CI twins. The script runs standalone with `ruamel.yaml`; it printed `OK` from the Hermes venv. |
| Secret scanning | A new scanner | The stdlib scan below plus manual read of the counts | No scanner is installed; the patterns are few. |
| Desktop half copy | Custom copy code | Desktop's own Install from Git | Writes the marker file the Plugins page needs. |
| Backend stop | `hermes serve --stop` | Owner-checked SIGTERM in a script | Matches the Phase 6 procedure. |

## History scan (item 5)

Tools on this box: none of `gitleaks`, `trufflehog`, `detect-secrets`, `git-secrets`, `ggshield`, `semgrep` is installed. [VERIFIED: `command -v`] I wrote a stdlib scan that streams `git log --all -p -U0` and prints counts only, never the matched text. Draft at `/tmp/claude-1002/-home-theo-local-repo-hermes-session-tasks/b90ca352-0e70-4460-b331-69cd5b3ffe2a/scratchpad/histscan.py` (the plan copies it to `scripts/history_scan.py` or keeps it out of the repo; Claude's discretion).

Scope: 426 commits, one branch (`main`), no tags, 72,057 added or removed diff lines, 311 tracked files. Author and committer on every commit: `Theo Deyle <theo.deyle@donmor.ca>`. [VERIFIED: `git rev-list --all --count`, `git log --format`]

Results, pattern by pattern (lines / commits / files):

| Pattern | Lines | Commits | Files | Meaning |
|---------|-------|---------|-------|---------|
| GitHub tokens (`ghp_`, `gho_`, `ghs_`, `github_pat_`) | 0 | 0 | 0 | clean |
| GitLab `glpat-` | 0 | 0 | 0 | clean |
| `sk-` keys | 0 | 0 | 0 | clean |
| AWS `AKIA` | 0 | 0 | 0 | clean |
| Slack `xox` | 0 | 0 | 0 | clean |
| Private key block | 0 | 0 | 0 | clean |
| JWT | 0 | 0 | 0 | clean |
| Authorization header literal | 0 | 0 | 0 | clean |
| Secret-like assignment with a 12+ char literal | 0 | 0 | 0 | clean |
| GUID | 10 | 7 | 6 | All 10 are session scratchpad folder ids inside `/tmp/claude-1002/...` paths in SUMMARY files. No tenant or app id. |
| `@donmor.ca` address | 7 | 7 | 7 | Only `theo.deyle@donmor.ca`, the commit identity, quoted in docs. |
| Other email-like text | 6 | 4 | 2 | `@anthropic.com` (the Co-Authored-By trailer address) and decorators such as `@pytest.fixture` matched. No third-party address. |
| Host `devpc` | 554 | 76 | 93 | `.planning/` mostly |
| `donmor` or `Don-Mor` | 72 | 20 | 24 | `.planning/config.json` (33, the skill name `global:donmor-stack`), plans, README |
| Host `legion` | 0 | 0 | 0 | clean |
| Host `vm-ts-router` | 0 | 0 | 0 | clean |
| `tailnet`, `ts.net`, `tailscale` | 20 | 11 | 10 | README, Phase 3 docs |
| `*.donmor.ca` host names | 0 | 0 | 0 | clean |
| Internal IP (10/8, 172.16/12, 192.168/16, 100.64/10) | 0 | 0 | 0 | clean |
| `/home/theo` path | 186 | 42 | 52 | `.planning/` mostly |
| `/Users/` or `C:\Users\` path | 12 | 4 | 4 | Phase 3 SUMMARY files |
| Name `Theo` | 1979 | 142 | 162 | `.planning/` (ROADMAP 71, plans), plugin strings, tests |
| Name `Deyle` | 9 | 9 | 8 | docs quoting the commit identity |
| Infisical, Entra, Azure, Key Vault, Cloudflare, Syncro, Rippling | 26 | 17 | 22 | words in docs, a sketch and tests (for example "no secret"); no value |
| Org name `Don-Mor-Software-Group` | 10 | 5 | 7 | REQUIREMENTS, ROADMAP, CONTEXT |
| `customer`, `dealer`, `dealership` | 24 | 11 | 10 | tests use "customer" as sample item text (`tests/test_board_cross.py`, `test_pane_readonly.py`, `test_pane_picker.py`); not real customer data. [ASSUMED: a read of those 24 lines was not done; the plan should read them] |

File-level checks: no file ever added with a name like `.env`, `*.pem`, `*.key`, `*.pfx`, `*.sqlite`, `*.db`, `*.log`, archive or image. Largest blobs are `uv.lock` (81 KB) and Phase 1 and 6 RESEARCH files (77 KB). `uv.lock` lists 25 packages all from `https://pypi.org/simple`. [VERIFIED: `git log --all --diff-filter=A --name-only`, `git rev-list --objects`, `grep registry uv.lock`]

What this means for the decision before the push:
- No credential is in history. [VERIFIED for the listed patterns only; a custom-format secret would not match.]
- What goes public: all of `.planning/` (the work log, with the name "Theo" 1,979 times, the host name `devpc`, `/home/theo` paths and the Don-Mor org name), `.claude/CLAUDE.md`, `handoff/2026-10-30-start-execution/README.md`, `hermes-session-tasks-brief.md`, and the work email `theo.deyle@donmor.ca` as author of every commit. Success criterion 4 asks for "no personal or host names" in the README only, and for the full history. So history keeps these names unless Theo chooses a rewrite.
- `.planning/config.json` and `.planning/state.json` are modified and uncommitted right now (git status). Commit or restore them before the scan is final.
- Recommendation for the checkpoint (one line to Theo): publish `.planning/` as is, keep the full history (matches D-50), and accept the work email in commit metadata. Ask only if he wants a rewrite. GitHub can refuse the push with error GH007 when the account blocks pushes that expose a private email; `gh api user/emails` needs the `user` scope that the token lacks, so this is untested. If GH007 appears, the fix is a GitHub account setting, not a history rewrite. [ASSUMED: GH007 behaviour]
- Run the scan again on the final tree right before the push. New commits (README, CONTRIBUTING, workflow) add text.

## GitHub push (item 8)

State: `gh auth status` shows `theo-deyle` with `repo`; SSH auth answers `theo-deyle`; `theo-deyle/hermes-session-tasks` does not exist (HTTP 404); `theo-deyle` has 0 public repos; the org repo is private with branch `main` only. [VERIFIED: gh api, ssh -T]

Commands (bash is fine for `gh` and `git`; the PowerShell rule is for `az`):

```bash
gh repo create theo-deyle/hermes-session-tasks --public \
  --description "A per-session task board for Hermes Desktop. The agent lists items; you edit them in a side pane."
git remote add public git@github.com:theo-deyle/hermes-session-tasks.git
git push public main
git ls-remote public          # the head must equal `git rev-parse main`
```

- `gh repo create ... --public` with the `owner/name` form is correct. Do not use `--source . --push` if the plan wants the scan to run between create and push; create first, push after the scan and the decision.
- `git push public main` sends every commit of `main` with no squash. There are no tags and no other branches. Keep `origin` pointing at the org repo (D-50 leaves it alone) and name the new remote `public`. Update the "Repo" line of `.claude/CLAUDE.md` and the CONTRIBUTING text to name both remotes.
- Rule 25 does not apply (no pull request here).
- Verify after the push: `gh api repos/theo-deyle/hermes-session-tasks --jq .private` prints `false`, and an anonymous `git ls-remote https://github.com/theo-deyle/hermes-session-tasks` works.

## CI (item 7)

Precedent: `~/.hermes/plugins/hermes-memory-ui/.github/workflows/ci.yml` (checkout, setup-node 22, setup-uv, whitespace check, `node --check`, VM harness, pytest). This repo's gate is `./scripts/check.sh`, which already runs pins, ruff, format, pyright and pytest on 3.11 and 3.14 and needs `uv` and `node` (the pane tests run `node --experimental-vm-modules`, `tests/pane_rig.py:36-37`).

I cloned the repo into a scratch folder and ran `HERMES_AGENT_REPO=/nonexistent/hermes-agent ./scripts/check.sh` to mimic a runner with no Hermes checkout. Result for Python 3.11 (about 4 minutes each version): `1044 passed, 28 skipped in 236.29s`, `check: python 3.11 ok`. The 28 skipped are the `hermes`-marked tests. `check_pins.py` printed `skip: hermes checkout not found` and exited ok. Pyright printed `venv .venv subdirectory not found in venv path` and still ended `0 errors`: the config names `.venv` but check.sh uses `.venv-py3.11`. Python 3.14 also passed: `1044 passed, 28 skipped in 212.17s`, then `check: python 3.14 ok` and `check: all ok`, exit 0. [VERIFIED: ran in scratch clone]

Draft workflow (Claude's discretion on the rest):

```yaml
name: CI
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: actions/setup-node@v7
        with:
          node-version: "22"
      - uses: astral-sh/setup-uv@v10.3.3
        with:
          version: "0.11.26"
          enable-cache: false
      - run: ./scripts/check.sh
```

- 3.11 took about 4 minutes locally, so allow about 8 for both versions plus downloads. `timeout-minutes: 25` is safe. [ASSUMED: runner speed]
- `uv sync` downloads managed Pythons 3.11 and 3.14 because `python-preference = "only-managed"`. The runner has network, so this works. [ASSUMED: not run on a runner]
- Node 22 matches the memory-ui precedent; devpc uses 24. The harness uses `--experimental-vm-modules`, which exists in both. [ASSUMED for 22]
- Optional README badge: `![CI](https://github.com/theo-deyle/hermes-session-tasks/actions/workflows/ci.yml/badge.svg)`.
- CI cannot run `hermes plugins validate` (needs Hermes). Run it by hand and record the output; the catalog CI runs it later at submission.
- The "committed whitespace" step of the precedent is optional.

## Restart procedure (item 6)

Phase 6 commands, from `06-12-PLAN.md:97-98,155,183` and `06-12-SUMMARY.md:82-141` [VERIFIED: read]:

| Step | Command |
|------|---------|
| Gateway state | `timeout 30 hermes gateway status` |
| Restart the gateway (announce first, wait for Theo's go) | `timeout 180 hermes gateway restart --yes --detach` (printed `Stopped gateway for this profile`, `Started the gateway in the background`) |
| List processes | `ps -eo pid,lstart,args \| grep -E 'gateway run\|serve --isolated' \| grep -v grep` |
| Lock files | `~/.hermes/desktop-ssh/<id>/backend.lock.json` |
| Owner check per pid | pid alive, `serve --isolated` in the command line, and the `--ssh-session-token-file` path inside that lock's own folder |
| Stop | `/bin/kill -TERM <pid>`, wait up to 30 s with `timeout 30 sh -c 'while kill -0 <pid> 2>/dev/null; do sleep 1; done'`, no stronger signal without a new go |
| Blocked-step route | The auto mode check blocked the `kill` from the executor in Phase 6. House rule 29: put the owner check and the SIGTERM in one non-interactive PowerShell script in the scratchpad that prints no secret, and give Theo one line `! timeout 90 pwsh -NoProfile -File <script>`. Pass lines: `pid N : stopped at <time>` and `backend-stop: done`. Fail line: `FAIL: pid N still alive after 30 s`. |

A stop is safe because Desktop starts a new backend with the current code at its next connect. [CITED: 06-12-PLAN.md:61]

Live state on 2026-11-03 (read-only, run in this session): the lock lists show 4 locks. Pid 1598850 (profile `router`, port 46509) is dead. Live: pid 1960055 (port 40513, started 2026-11-02 20:14:50 local), pid 1960156 (port 44121, 20:14:51), pid 2890841 (port 43611, 2026-11-03 08:24:17). The gateway is pid 1942229 (started 2026-11-02 20:06:12). `hermes serve --status` listed 3 serve processes. The last `plugin/` commit is `969b12d` at 2026-11-02 21:34:42 -05:00 (WR-01). So the gateway and the two backends started 20:06 to 20:14 predate that commit and already run older code than HEAD; pid 2890841 started after it. Every Phase 7 code change will make all of them stale again. [VERIFIED: `ps`, `git log -1 -- plugin`]

The `serve` command line is a long `-I -c` bootstrap that ends with `serve --isolated --host 127.0.0.1 --port 0 --ssh-session-token-file <desktop-ssh>/<id>/<16 hex>.token --ssh-owner-nonce <16 hex>`. Match on the tail, never print the token path of a live file into a log that leaves the box. [VERIFIED: `hermes serve --status` output, filtered]

Version proof after the restart (replaces the `/meta` read, Correction 3):
1. `hermes gateway status` names a new pid; `ps -o lstart` for it is later than the last `plugin/` commit time.
2. Every live `serve --isolated` pid has `lstart` later than that commit, or the backend was stopped and Desktop started a new one.
3. An unauthenticated `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:<port>/api/plugins/hermes-session-tasks/meta` prints `401` on each port (route mounted). [CITED: 03-08-SUMMARY.md:247]
4. The pane on each Desktop shows no version banner. The banner compares the pane's `PLUGIN_VERSION` and `API_VERSION` with the answer of `/meta` (`plugin.js:335`).
5. Bump `plugin.yaml` `version` and `PLUGIN_VERSION` to the same new value in the same commit (a test fails on drift, D-29). A bump makes the banner appear on any pane copy that has not been refreshed, which gives the user-visible check that `/meta` alone cannot give. Suggested value: `0.2.0` (first public release). [ASSUMED: the number is Theo's or the planner's call] `tests/test_version.py:45` and `tests/test_desktop_plugin.py:120` hold `0.1.0` and need the new value.

## Neutral wording (item 10)

`grep -rn -i 'theo\|devpc' plugin README.md` (hit lines per file) [VERIFIED: run]:

| File | Hit lines | Kind |
|------|-----------|------|
| `plugin/plugin.yaml` | 1 (line 3) | description, shown in catalog |
| `plugin/session_tasks/tool_text.py` | 17 (lines 18, 19, 43, 44, 47, 50, 53, 58, 110, 143, 175, 176, 181, 184, 190, 196, 197) | tool descriptions and prompt section, model-visible |
| `plugin/skills/board-rules/SKILL.md` | 14 (lines 3, 8, 12, 18, 20, 26, 28, 30, 32, 39, 41, 43, 47, 64) | skill text, model-visible, includes the heading `## Theo's message is his answer` |
| `plugin/session_tasks/delta.py` | 4 (lines 1, 4, 16, 17) | lines 16-17 are model-visible (`DELTA_NOTE`, `POINTER_TEXT`) |
| `plugin/session_tasks/guard.py` | 7 (lines 1, 3, 4, 52, 60, 62, 63) | lines 62-63 are model-visible tool error text |
| `plugin/session_tasks/rows.py` | 3 (lines 41, 183, 199) | docstrings |
| `plugin/session_tasks/store.py` | 3 (lines 236, 238, 246) | docstrings |
| `plugin/session_tasks/hooks.py` | 1 (line 8) | docstring |
| `plugin/session_tasks/board_api.py` | 1 (line 142) | docstring |
| `plugin/desktop/plugin.js` | 1 (line 4) | header comment |
| `README.md` | 14 (lines 7, 9, 11, 18, 21, 24, 27, 39, 42, 45, 48, 68, 69, 70) | `devpc`, `devbox`, `devpc-ts`, `/home/theo` paths |
| `scripts/install-desktop.ps1` | 25 lines with `devpc` or the default `-RemotePath '/home/theo/local_repo/...'` (line 38) | Not in CONTEXT's list. It stays as the fallback, so its defaults need generic values (a required host parameter, no `/home/theo` default) or the script is documented as a dev tool. `tests/test_install_script.py` pins it. |

Other tracked files with these names: `.claude/CLAUDE.md`, `handoff/2026-10-30-start-execution/README.md`, `hermes-session-tasks-brief.md`, and test fixtures in `tests/`. These are not part of the plugin install, but they are public once pushed.

Rule for the rewrite: "Theo" becomes "the user", "he" becomes "they" or a repeat of "the user". Keep each behaviour rule word for word otherwise. Strings are pinned by tests (`tests/test_tool_text.py`, `test_delta.py`, `test_guard.py`, `test_board_tools.py`, `test_pre_llm_hook.py`, `test_hooks.py`); update both sides in one commit. The model-visible text is cache-stable prompt text; re-run the headless own-plan check afterwards: `OWN_JOB_OUT=$HOME/.cache/hermes-session-tasks/own-job tests/live/own_job/run.sh own7-N` (Phase 6 used this form; pass is 3 of 3) plus the ask-before-destroy live rule. [CITED: 06-12-SUMMARY.md own-plan lines] The job prompt `tests/live/own_job/job.txt` and `tests/live/delta/*` also name "Theo"; they are test inputs, so neutralise them if the repo goes public, but the headless pass rule does not need them changed.

## Hardening fixes (item 9)

Exact locations, read from `plugin/desktop/plugin.js` and the review files on 2026-11-03. Line numbers in the review drifted by a few lines.

| # | Fix | File and line now | Source of the finding |
|---|-----|-------------------|-----------------------|
| W1 | `role: 'status'` on the notice `div`. Both `jsx('div', ...)` and `jsxs('div', ...)` in `Notice` need it. | `plugin/desktop/plugin.js:363-369` (`function Notice`; review said 366-367) | `06-UI-REVIEW.md:27,127` |
| W2 | After Back, focus the picker trigger. `back()` sets `picked` to null and unmounts the Back button that holds focus. Put a ref on the trigger `Button` inside `DropdownMenuTrigger` (`PickerRow`, `plugin.js:498-504`) and call `focus()` in a `useEffect` keyed on `picked`. `useRef` and `useEffect` are already imported (`plugin.js:26`). | `back()` at `plugin.js:~1186-1192`; trigger at `plugin.js:498-504`; Back button `aria-label` at `plugin.js:530` | `06-UI-REVIEW.md:28,128` |
| W3 | Add `rounded-md` to `BANNER_CLASS`. | `plugin/desktop/plugin.js:102-103` | `06-UI-REVIEW.md:29,64` |
| W4 | Fix the stale layout line: the read-only row is checkbox first, then text, then the chevron only when subtasks exist (as built, 04-08-SUMMARY.md). Edit the line that starts `1. Top-level row: chevron column 24px ...`. | `.planning/phases/06-cross-session-boards/06-UI-SPEC.md:94` | `06-UI-REVIEW.md:29,65` |
| W5 | IN-05: one home for `SESSION_ID_MAX = 256`. Today it sits in `plugin/dashboard/plugin_api.py:22` and `plugin/session_tasks/copy_args.py:15` (and a third copy in `tests/test_api_copy.py:21`). `plugin_api.py` already has `load_core()` and `core_module()` at lines 48-70, so move those two functions above the pydantic models and set `SESSION_ID_MAX = core_module("copy_args").SESSION_ID_MAX`. The layout test only forbids module-level `import` statements in the dashboard file (`tests/test_layout.py:130-139`), and a function call is not an import. The review's other option (a test that asserts the two values are equal) is the fallback if the module-level load causes trouble. | files above | `06-REVIEW.md:123-128`, `06-REVIEW-DISPOSITION.md:13` |

After W1 to W3 the Desktop half changed, so the version bump (see Restart procedure step 5) is required for the banner to flag stale copies. W2 needs a pane harness test (the repo has `tests/test_pane_picker.py` and `tests/pane_rig.py` for this). W1 and W3 are assertable by string in the harness.

## Common Pitfalls

### Pitfall 1: Desktop rejects `owner/repo#plugin`
**What goes wrong:** the probe clones `https://github.com/owner/repo#plugin.git`, fails, and the dialog shows a git error.
**Why:** the TypeScript resolver handles `#` only for full URLs. [VERIFIED: ran]
**How to avoid:** Desktop text uses the full URL with `#plugin`. Add a README test that the Desktop line contains `https://github.com/theo-deyle/hermes-session-tasks#plugin`.
**Warning signs:** "Plugin subdirectory ... does not exist" or a git "repository not found" error in the dialog.

### Pitfall 2: Old hand-installed pane copy blocks Install from Git
**What goes wrong:** `Desktop plugin 'hermes-session-tasks' already exists. Enable force reinstall to replace it.`
**Why:** `install-desktop.ps1` created a marker-less `desktop-plugins/hermes-session-tasks/`.
**How to avoid:** tick Force reinstall on the Mac and the Windows PC, or remove that folder. Never tick Force on devpc (agent half).

### Pitfall 3: The `/meta` check passes on stale code
**What goes wrong:** a backend that never restarted reports the new version.
**Why:** `read_backend_version` reads `plugin.yaml` per request.
**How to avoid:** use start time against the last `plugin/` commit, plus the pane banner.

### Pitfall 4: Unquoted `sha` in the catalog file
**What goes wrong:** YAML reads the all-digit placeholder as the integer 0; both validators fail.
**How to avoid:** quote it; test with `entry_from_mapping`.

### Pitfall 5: Docs page empty with `subdir`
**What goes wrong:** no README renders on the future catalog page.
**How to avoid:** `plugin/README.md`.

### Pitfall 6: Public repo needed before the live pass
**What goes wrong:** Desktop's git has no credential fallback; a private repo fails on the Mac and Windows PC.
**How to avoid:** push first (after the checkpoint), then run the live pass. The plan order is: wording and fixes, docs and CI, scan, decision, push, install proofs, restart, live pass.

### Pitfall 7: The scan passes but the tree changed
**How to avoid:** run the scan again on the final head right before `git push public main`, and commit or restore `.planning/config.json` and `.planning/state.json` first.

### Pitfall 8: Install on another host does not mount the routes at once
**What goes wrong:** the pane says `404 Plugin not found` until the backend restarts.
**How to avoid:** the README "Known behaviour" keeps that line (neutral wording: "restart the Hermes backend or gateway"), and the plan announces the restart before it runs.

## Code Examples

### Install proof in a scratch home (reuse for the public URL after the push)

```bash
SP=<scratchpad>; mkdir -p $SP/home-public
HERMES_HOME=$SP/home-public timeout 200 hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable
HERMES_HOME=$SP/home-public hermes plugins doctor hermes-session-tasks
HERMES_HOME=$SP/home-public hermes plugins list --json     # status enabled, version, source user
HERMES_HOME=$SP/home-public hermes plugins update hermes-session-tasks   # "already up to date"
```
[VERIFIED: same flow ran with a `file://` source]. In zsh, quote the identifier because of `#`. Delete the scratch home afterwards (it holds an isolated runtime the install created).

### Desktop identifier (Pane install text)

```
https://github.com/theo-deyle/hermes-session-tasks#plugin
```

### Owner check core (for the restart script; token never printed)

```python
# per lock: alive, serve --isolated in the command line, token path inside the lock folder
argv = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace").replace("\0", " ")
ok = "--isolated" in argv and re.search(r"\bserve\b", argv) and lock_dir in argv
```
[VERIFIED: draft ran read-only in this session, `scratchpad/backends_check.py`; it found 3 live backends that pass the check]

## State of the Art

| Old approach | Current approach | Impact |
|--------------|------------------|--------|
| `install-desktop.ps1` copy over SSH (Phase 3) | Desktop Install from Git, or package copy on the same machine | Script becomes a documented fallback (D-48). |
| devpc symlink only | `hermes plugins install owner/repo#subdir --enable` | One line per host (D-47). |
| Catalog by pull request only | Same, plus the live catalog JSON | The entry file is ready; submission is deferred. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Force reinstall from Desktop on devpc would replace the symlink install | Desktop install | Low: the plan says "do not tick Force on devpc" either way |
| A2 | `git` is on PATH on the Mac and the Windows PC | Desktop install | Medium: the dialog fails at probe; install Git first |
| A3 | GitHub may refuse the push with GH007 because of the work email | History scan | Medium: needs a GitHub account setting change by Theo |
| A4 | CI wall time is under 25 minutes and node 22 runs the harness | CI | Low |
| A5 | `uv sync` can download managed Python 3.11 and 3.14 on a runner | CI | Low; the fix is `python-preference` or a setup step |
| A6 | The 24 `customer/dealer` lines are sample text, not real data | History scan | Medium: read them before the push |
| A7 | The Mac and Windows Desktop builds behave like the 2026-10-22 source (no Desktop checkbox; same parser) | Corrections 1-2 | Medium: record what each dialog shows |
| A8 | Version `0.2.0` for the first public release | Restart | Low: any new value works |

## Open Questions

1. **Does `check.sh` pass in a clean clone with no Hermes checkout?**
   - Answered: yes, both versions (see CI). The plan still reruns it in a fresh clone of the final head before the push.
2. **Pyright `venv .venv subdirectory not found` warning in a clean clone.**
   - Known: it is a message, not an error (`0 errors`). `pyproject.toml` sets `venvPath = "."`, `venv = ".venv"`, but check.sh passes `--pythonpath`.
   - Recommendation: leave it; or drop `venv`/`venvPath` from `[tool.pyright]` if the message is noise in CI.
3. **License.** No `LICENSE` file exists. Hermes is MIT (Nous Research); the memory-ui precedent ships a `LICENSE`. [VERIFIED: `~/.hermes/hermes-agent/LICENSE`, `~/.hermes/plugins/hermes-memory-ui/LICENSE` exist] A public repo with no license grants no rights. Recommendation: MIT, copyright holder Theo's choice (a personal name or the company). This is Theo's decision; the plan carries one checkpoint line for it.
4. **Where does a user find the pane after install on a remote backend?** Whether the desktop half arrives enabled when the agent half fails with "already installed" is untested on the Mac. The live pass records it.
5. **Commit identity on the public repo.** All 426 commits carry the work email. Keep (matches the PROJECT.md constraint) unless Theo says otherwise at the checkpoint.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| hermes CLI | install, validate, doctor | yes | v0.22.5 | - |
| git | clone, push | yes | - | - |
| gh | repo create, checks | yes | signed in `theo-deyle` | - |
| ssh to github.com | push | yes | answers `theo-deyle` | https with the gh token |
| uv | check.sh, CI | yes | 0.11.26 | - |
| node | pane tests | yes | 24.19.0 | - |
| pwsh | restart script (house rule 29) | yes per house notes | 7.6 | - |
| gitleaks, trufflehog, detect-secrets | scan | no | - | stdlib scan |
| ruamel.yaml | `validate_plugin_catalog.py` | yes, in the Hermes venv | - | `entry_from_mapping` |
| GitHub `user` token scope | read emails | no | - | skip; accept GH007 risk |
| Mac, Windows PC with Desktop and git | live pass | not checked from here | - | Theo's hands |

**Missing with no fallback:** none for the code work. The live pass needs Theo on the Mac and the Windows PC.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (+ pytest-cov 7.1.0), ruff 0.15.10, pyright 1.1.414, node VM harness [VERIFIED: pyproject.toml] |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, markers `hermes`) |
| Quick run command | `uv run pytest -q tests/test_<module>.py` |
| Full suite command | `./scripts/check.sh` (3.11 with coverage 80, then 3.14; about 4 minutes per version) |
| Hermes-marked tests | `uv run pytest -q -rs -m hermes` (28 tests; skipped when no checkout) |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEV-04 | Install, enable, doctor, update in a scratch home from the public URL | integration (live, scripted) | `HERMES_HOME=<scratch> hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable` then `plugins doctor`, `plugins update` | no, Wave 0 script or recorded commands |
| DEV-04 | README and CONTRIBUTING hold the right identifier forms | unit | `uv run pytest -q tests/test_docs.py` | no, Wave 0 |
| DEV-04 | Version drift: `plugin.yaml` equals `PLUGIN_VERSION` | unit | `uv run pytest -q tests/test_version.py tests/test_desktop_plugin.py` | yes (update the values) |
| DEV-04 | Restart proof: start time after last plugin commit, 401 on each port | live script | read-only `ps` and `curl` per port (draft `backends_check.py` pattern) | no, scratchpad draft |
| DEV-06 | Catalog entry shape and match with `plugin.yaml` | unit (+ hermes) | `uv run pytest -q tests/test_catalog_entry.py` and `-m hermes` | no, Wave 0 |
| DEV-06 | Catalog validators | tool | `python3 ~/.hermes/hermes-agent/scripts/validate_plugin_catalog.py catalog/hermes-session-tasks.yaml` (needs ruamel.yaml: use `~/.hermes/hermes-agent/venv/bin/python`) | tool exists |
| DEV-06 | Plugin validate and doctor | tool | `timeout 120 hermes plugins validate plugin --install-deps` (expect 16 of 16 and `Validation passed.`), `hermes plugins doctor plugin --ci` | tool exists |
| DEV-06 | No "Theo" or "devpc" in plugin and docs | unit | `uv run pytest -q tests/test_neutral_wording.py` (grep `plugin/` and `README.md`, `CONTRIBUTING.md`) | no, Wave 0 |
| DEV-06 | CI file exists and calls check.sh | unit | `uv run pytest -q tests/test_ci_file.py` | no, Wave 0 |
| DEV-06 | History scan has zero token hits | script | `python3 -I scripts/history_scan.py .` | draft exists in scratchpad |
| D-53 | Own-plan 3 of 3 with new wording | live headless | `OWN_JOB_OUT=$HOME/.cache/hermes-session-tasks/own-job tests/live/own_job/run.sh own7-N` | yes |
| D-56 W1-W3 | role status, focus after Back, rounded banner | pane harness | `uv run pytest -q tests/test_pane_picker.py tests/test_pane_view.py` | yes (extend) |
| D-56 W5 | one `SESSION_ID_MAX` | unit | `uv run pytest -q tests/test_copy_args.py tests/test_api_copy.py tests/test_layout.py` | yes (extend) |
| D-57 | Full loop on Mac and Windows PC | manual, human | one request per turn, result recorded word for word | manual only: needs the physical machines |

### Sampling Rate

- **Per task commit:** the quick command for the touched module plus `uv run ruff check . && uv run ruff format --check .`
- **Per wave merge:** `./scripts/check.sh`
- **Phase gate:** `./scripts/check.sh` green, `hermes plugins validate plugin --install-deps` passes, `node --check plugin/desktop/plugin.js` exit 0, scan clean, then the live pass.

### Wave 0 Gaps

- [ ] `tests/test_catalog_entry.py` - entry matches manifest and passes the validator
- [ ] `tests/test_docs.py` - identifier forms, the "closing the only pane disables the plugin" line, no personal or host names
- [ ] `tests/test_neutral_wording.py` - no `Theo` or `devpc` under `plugin/` (except none allowed) and in README and CONTRIBUTING
- [ ] `tests/test_ci_file.py` - workflow calls `./scripts/check.sh`, pins action versions
- [ ] `scripts/history_scan.py` - counts only; decide whether it ships in the public repo

## Security Domain

`security_enforcement` is enabled in `.planning/config.json`. [VERIFIED: config.json:50]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | The plugin adds no sign-in; Desktop session token stays Hermes-owned |
| V3 Session Management | no | same |
| V4 Access Control | partly | Known behaviour already says any Desktop that signs in can read any board by session id; keep this line in the README in neutral words |
| V5 Input Validation | yes | Unchanged; IN-05 keeps one `SESSION_ID_MAX` for the route and the parser |
| V6 Cryptography | no | none used |
| V14 Config / supply chain | yes | Pinned dev tools, `uv.lock` from `pypi.org` only (verified), pinned CI actions, no committed binaries (rule 17) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret or personal data in a public history | Information disclosure | Stdlib history scan, decision checkpoint, scan again at head before the push |
| Tag or branch moves under a catalog pin | Tampering | Catalog pins a 40-hex sha (rule 2); the file holds a quoted placeholder until submission |
| Supply-chain drift in CI | Tampering | `permissions: contents: read`, pinned action versions, `uv sync --locked` (already in check.sh) |
| Killing the wrong process in the restart | Denial of service | Owner check per pid (alive, `serve --isolated`, token path inside the lock folder), SIGTERM only, Theo's go first |
| Printing a Desktop session token | Information disclosure | Never read or print token files; the files are deleted at backend start anyway |
| Force reinstall replaces the dev symlink | Tampering | No Force on devpc |

## Project Constraints (from .claude/CLAUDE.md)

- Stack: uv, ruff, pyright, pytest; plugin code runs on Python 3.11 and 3.14 and imports only the standard library plus fastapi and pydantic.
- Desktop: plain ESM, one file, no build step, SDK imports only.
- Small modules with one responsibility each.
- No secrets in the repo; a needed secret comes from Infisical.
- Docs: plain language, no em dash or en dash anywhere, spaced hyphen instead.
- Commit identity: Theo Deyle <theo.deyle@donmor.ca>.
- Deploy: symlink the package into `~/.hermes/plugins/`, enable, restart the gateway; announce the restart first because it drops live Desktop connections.
- Never read, write, wrap or replace `todo_list`.
- GSD workflow for every edit (global rule 32).
- Global house rules that touch this phase: one request per turn in the live pass (rule 6); no reply words (rule 19); no dev speak in replies to Theo (rule 22); production-style one-line ask before a one-way step such as the public push (D-50); write for Theo as a non-developer; no pull request is opened here (rule 25 does not apply).

## Sources

### Primary (HIGH confidence)
- `~/.hermes/hermes-agent/plugin-catalog/README.md:156-187` - entry schema; rules 1-17 at lines 14-150
- `~/.hermes/hermes-agent/website/docs/developer-guide/plugins/catalog-submission.md` - submission steps and checks
- `~/.hermes/hermes-agent/hermes_cli/plugin_catalog.py:31-180` - loader rules (name, sha, version, image hosts, categories)
- `~/.hermes/hermes-agent/scripts/validate_plugin_catalog.py` - standalone validator (ran)
- `~/.hermes/hermes-agent/website/scripts/extract-plugins.py:84-95` - README source path with `subdir`
- `~/.hermes/hermes-agent/hermes_cli/plugins_cmd.py:292-330`, `plugins_cmd_git.py:182-258`, `plugins_cmd_install.py:542-722,782-890` - CLI install, subdir clone, enable
- `~/.hermes/hermes-agent/hermes_cli/git_credentials.py:1-25` - private repo credentials
- `~/.hermes/hermes-agent/hermes_cli/plugins_activation.py:1-12` - what is live at install
- `~/.hermes/hermes-agent/hermes_cli/plugin_dev.py:330-420` - what `plugins doctor` checks (registration, hook kwargs, manifest v2, stale Desktop copy warning)
- `~/.hermes/hermes-agent/apps/desktop/electron/desktop-plugin-install.ts` - parser (ran), clone, marker, force
- `~/.hermes/hermes-agent/apps/desktop/src/app/settings/plugin-install-run.ts`, `plugin-install-details.tsx`, `plugin-install-modal.tsx` - install flow and dialog
- `~/.hermes/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md:1688-1790` - one package, remote backend note
- `~/.hermes/hermes-agent/hermes_cli/main_dashboard.py:744-780` - token file read and unlink
- This repo: `plugin/session_tasks/version.py:44-51`, `plugin/dashboard/plugin_api.py:22-112`, `plugin/desktop/plugin.js`, `scripts/check.sh`, `scripts/check_pins.py`, `pyproject.toml`
- `.planning/phases/06-cross-session-boards/06-12-SUMMARY.md`, `06-12-PLAN.md`, `06-UI-REVIEW.md`, `06-REVIEW.md`, `06-REVIEW-DISPOSITION.md`, `06-UI-SPEC.md:94`
- `~/.hermes/plugins/hermes-memory-ui/.github/workflows/ci.yml` - CI precedent
- Commands run 2026-11-03: `hermes plugins validate plugin --install-deps`, `hermes plugins doctor`, scratch-home install and update, `gh auth status`, `gh api` (repo, releases, refs), `ssh -T git@github.com`, `ps`, `hermes serve --status`, history scan, clean-clone `check.sh` (3.11 pass)

### Secondary (MEDIUM confidence)
- `~/.hermes/hermes-agent/website/docs/user-guide/features/plugin-catalog.md:36-70,185-200` - field table and update behaviour

### Tertiary (LOW confidence)
- None used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new package; tools probed
- Architecture and install paths: HIGH for the CLI (ran end to end); MEDIUM for Desktop on the Mac and Windows (source read, parser run, dialog not run)
- Pitfalls: HIGH for 1, 3, 4, 5 (run or read in code); MEDIUM for 2 and 8
- History scan: HIGH for the listed patterns, no claim about unlisted formats

**Research date:** 2026-11-03
**Valid until:** 2026-11-10 (Hermes and Desktop move fast; re-check the Desktop parser if `hermes update` runs before the live pass)
