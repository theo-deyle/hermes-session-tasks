# Phase 7: Deploy and hardening - Context

**Gathered:** 2026-11-03
**Status:** Ready for planning

<domain>
## Phase Boundary

The plugin becomes catalog-ready: it installs on any Hermes host with one `hermes plugins install` line, its pane installs on any Hermes Desktop machine from the Plugins page, and the repo holds everything the Hermes plugin catalog asks of a submission. The repo moves to a public GitHub repo on Theo's personal account. The deferred review items that are cheap get fixed. Theo decided on 2026-11-03 that this replaces the earlier devpc-only deploy goal. The catalog pull request itself is not opened: the phase makes the repo ready "as if" it were submitted.

</domain>

<decisions>
## Implementation Decisions

### Install path (replaces the devpc-only deploy)
- **D-47:** Every Hermes host other than devpc installs the plugin with `hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable` and updates it with `hermes plugins update hermes-session-tasks`. The gateway restart after install or update is announced before it happens. devpc keeps the symlink `~/.hermes/plugins/hermes-session-tasks -> <repo>/plugin`, because a linked package is the documented dev mode with pane hot reload. No custom deploy script. - **Reversibility:** reversible - one documented command per host.
- **D-48:** Every Desktop machine installs the pane from Capabilities, Plugins, Install from Git, with the identifier `theo-deyle/hermes-session-tasks#plugin` and the Desktop target checked. When Hermes and Desktop run on the same machine, the package copy happens on its own and no Git install is needed. `scripts/install-desktop.ps1` stays in the repo as the fallback and is documented as such; it is no longer the primary path. - **Reversibility:** reversible.
- **D-49:** The repo layout stays: `plugin/` is the package, `pyproject.toml` and `tests/` stay at the repo root. The catalog entry points `subdir` at `plugin`. Both the Hermes CLI and the Desktop app accept the `#plugin` form (`hermes_cli/plugins_cmd_git.py:193-215`, `apps/desktop/electron/desktop-plugin-install.ts:56-104`). - **Reversibility:** costly - a move of `plugin.yaml` to the root would make the dev `pyproject.toml` count as the plugin's runtime dependency list.

### Repo and catalog readiness
- **D-50:** The code moves to a new public GitHub repo `theo-deyle/hermes-session-tasks` on Theo's personal account, full history, no squash. Before the first push, Claude scans the whole history for secrets, tokens, customer data and internal host names, and reports the result in the plan summary. The org repo `Don-Mor-Software-Group/hermes-session-tasks` is left as it is in this phase. - **Reversibility:** one-way - a public push publishes the history; a later takedown does not unpublish copies. The planner puts a `checkpoint:decision` before the push task.
- **D-51:** The repo holds a ready catalog entry file (the `plugin-catalog/<name>.yaml` shape from `catalog-submission.md`, with `repo`, `subdir: plugin`, quoted `version`, `capabilities`, and a `sha` placeholder named as such) under `catalog/hermes-session-tasks.yaml`. It is not submitted. Research names the exact entry schema from `plugin-catalog/README.md` in the Hermes repo.
- **D-52:** `hermes plugins validate plugin --install-deps` is the pass rule for catalog readiness, and `hermes plugins doctor` runs against the installed package. Both run in the plan and their output is recorded. A GitHub Actions workflow runs `./scripts/check.sh` on push, following the precedent `~/.hermes/plugins/hermes-memory-ui/.github/workflows/ci.yml`.

### Neutral wording for a public plugin
- **D-53:** Every user-facing string loses the name "Theo" and the host name "devpc": `plugin.yaml` description, the tool descriptions and system prompt text in `plugin/session_tasks/tool_text.py`, `plugin/skills/board-rules/SKILL.md`, the one string in `plugin/desktop/plugin.js`, and the README. "Theo" becomes "the user". The behaviour rules stay word for word otherwise. Pass rule: the Phase 2 and Phase 5 headless own-plan check still scores 3 of 3 with the new wording, and the ask-before-destroy live rule still holds. - **Reversibility:** reversible.
- **D-54:** The README becomes the catalog page: what the plugin is in one sentence, install on a host, install the pane, update, known behaviour (the line "closing the only pane disables the plugin" stays). The devpc dev setup, the symlink, the gateway restart rule and the PowerShell fallback move to `CONTRIBUTING.md`. Plain language, no em dash or en dash.

### Desktop backends after a restart
- **D-55:** A gateway restart on devpc does not restart the Desktop SSH backends (`serve --isolated`). The plan reuses the Phase 6 procedure: list every `~/.hermes/desktop-ssh/*/backend.lock.json`, match each pid to its lock and to a `serve --isolated` command line, and stop only matched pids, after Theo's go. Desktop starts a new backend with the new code on its next connect. The `/meta` version check then runs against every live backend port.

### Hardening scope
- **D-56:** In scope: the three pane review warnings from `06-UI-REVIEW.md` (notice `role: 'status'`, focus back to the picker trigger after Back, `rounded-md` on the banner), the stale layout line 94 of `06-UI-SPEC.md`, and review note IN-05 (`SESSION_ID_MAX` in one place). Out of scope, stay deferred: IN-01, IN-02, IN-03, IN-04, IN-06, IN-07.

### Live pass
- **D-57:** The full loop runs once on the Mac and once on a Windows PC through the new install path, four steps each: the agent lists items, the pane shows them live, Theo edits one, the agent sees the edit on its next turn. Each machine gets one request per turn, in plain words, and the result is recorded word for word.

### Claude's Discretion
- The exact neutral wording of each string, as long as the behaviour rules stay.
- The CI workflow file content, the Python versions matrix (3.11 and 3.14), and the badge.
- The history scan method and the list of patterns it checks.
- The order of the plans.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Hermes plugin catalog and install
- `~/.hermes/hermes-agent/website/docs/developer-guide/plugins/catalog-submission.md` - the submission checklist, the PR shape, the admission rules 1 to 13
- `~/.hermes/hermes-agent/plugin-catalog/README.md` - the entry schema for the catalog file (D-51)
- `~/.hermes/hermes-agent/website/docs/developer-guide/plugins/index.md` lines 44 to 110 - standalone plugin repos, `hermes plugins install owner/repo`, validate as the CI gate
- `~/.hermes/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md` lines 1690 to 1780 - one package with both halves, the linked dev mode, the remote backend note and Install from Git with the Desktop target
- `~/.hermes/hermes-agent/hermes_cli/plugins_cmd_git.py` - the Git install, the `#subdir` form, credential handling
- `~/.hermes/hermes-agent/apps/desktop/electron/desktop-plugin-install.ts` - the Desktop Git install and its identifier parser

### This repo
- `.planning/PROJECT.md` - constraints: stdlib plus fastapi and pydantic, one plain ESM pane file, no `todo_list`, commit identity
- `.planning/REQUIREMENTS.md` - DEV-04 and DEV-06 (reworded for this phase)
- `.planning/phases/06-cross-session-boards/06-UI-REVIEW.md` - the three warnings in scope (D-56)
- `.planning/phases/06-cross-session-boards/06-REVIEW-DISPOSITION.md` - IN-01 to IN-07
- `.planning/phases/06-cross-session-boards/06-12-SUMMARY.md` - the Phase 6 restart and backend stop procedure (D-55)
- `.planning/phases/03-rest-router-and-client-install-spike/03-CONTEXT.md` - D-26 (install script), D-29 (version banner and `/meta`)
- `README.md`, `scripts/install-desktop.ps1`, `scripts/check.sh`
- `~/.hermes/plugins/hermes-memory-ui/.github/workflows/ci.yml` - CI precedent

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/check.sh`: the full house gate (ruff, format, pyright, pytest on 3.11 and 3.14, coverage 80). CI calls it as is.
- `scripts/install-desktop.ps1`: stays as the fallback pane install.
- `tests/live/cross/cross_live.py`: the Phase 6 live harness with the real-home refusal; the backend stop procedure lives in 06-12-SUMMARY.md.
- `GET /meta` in `plugin/dashboard/plugin_api.py:109`: returns `backend_version` and `api_version`; the version check after a restart reads it on every backend port.

### Established Patterns
- `hermes plugins validate plugin` passes 16 of 16 checks today (run 2026-11-03).
- The plugin is enabled through `plugins.enabled` in `~/.hermes/config.yaml`, set by the Hermes CLI, never by hand.
- Version strings: `plugin.yaml` `version` and `PLUGIN_VERSION` in `plugin.js` move together; a test fails when they drift (D-29).
- The 4 live Desktop backends on devpc on 2026-11-03: pids 1598850, 1960156, 1960055, 2890841, from the lock files under `~/.hermes/desktop-ssh/`.

### Integration Points
- Strings with "Theo": `plugin/plugin.yaml:3`, `plugin/session_tasks/tool_text.py` (12 lines), `plugin/skills/board-rules/SKILL.md` (14 lines), `plugin/desktop/plugin.js` (1 line), `README.md`.
- The git remote `origin` points at the org repo over SSH; the gh CLI is signed in as `theo-deyle` with the `repo` scope.

</code_context>

<specifics>
## Specific Ideas

- "We need to make this so that we can have it on any of the hosts that I have installed Hermes on, and be able to connect with any of the desktop apps that I have on my machines."
- "I would like this to be able to be compliant with the hermes plugin system as if I was submitting it to them for inclusion."
- "Set it up as IF I would submit it, because of the simplicity and all that." Public repo on the personal account `theo-deyle`.

</specifics>

<deferred>
## Deferred Ideas

- The actual catalog pull request to `NousResearch/hermes-agent`. Theo opens it when he wants the listing.
- Review notes IN-01, IN-02, IN-03, IN-04, IN-06, IN-07 (see D-56).
- What to do with the org repo `Don-Mor-Software-Group/hermes-session-tasks` after the move.

</deferred>

---

*Phase: 07-deploy-and-hardening*
*Context gathered: 2026-11-03*
