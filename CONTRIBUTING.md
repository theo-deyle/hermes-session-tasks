# Contributing

This file holds the dev setup and the fallback pane install. The user pages are `README.md` and `plugin/README.md`.

## Set up on devpc

1. Run `uv sync` from the repo root.
2. Run `./scripts/check.sh`. It runs the pin check, ruff, the format check, pyright and pytest on Python 3.11 and on Python 3.14. The 3.11 run holds a coverage gate of 80 percent.
3. Run `HERMES_AGENT_REPO=/nonexistent/hermes-agent ./scripts/check.sh` to run the suite the way CI does. The tests marked `hermes` then skip.

## Link the plugin on devpc

1. Run `ln -s "$PWD/plugin" ~/.hermes/plugins/hermes-session-tasks` from the repo root.
2. Run `hermes plugins enable hermes-session-tasks`.

Never edit `config.yaml` by hand. A linked package is the dev mode. Desktop on the same machine reloads the pane on its own.

## Restart rule

Announce the gateway restart before it happens. The restart drops live Desktop connections. The command is `hermes gateway restart`.

The gateway restart does not restart the Desktop SSH backends (`serve --isolated`). A change to `plugin/dashboard/plugin_api.py` needs a new backend. To stop a backend:

1. Read the lock file `~/.hermes/desktop-ssh/<id>/backend.lock.json` of the backend.
2. Check that the pid in the lock file is alive and that its command line holds `serve --isolated`.
3. Get the go of the person who uses that Desktop.
4. Send SIGTERM to that pid. Send no stronger signal.

Desktop starts a new backend with the new code at its next connect.

Never use `hermes serve --stop`, because it stops every dashboard process of the home. Never read or print a backend token file.

## Version

Bump these four values together:

1. `version` in `plugin/plugin.yaml`.
2. `version` in `pyproject.toml`.
3. `PLUGIN_VERSION` in `plugin/desktop/plugin.js`.
4. `version` in the catalog entry.

Then run `uv lock`. The pane shows a version line when its copy differs from the backend.

## Catalog entry

The file `catalog/hermes-session-tasks.yaml` is ready and not submitted. Its `sha` is a quoted placeholder. At submission, set `sha` to the pinned 40-character commit and keep it quoted.

The catalog page reads `plugin/README.md`. The file `README.md` repeats it.

## Repos

The public repo `https://github.com/theo-deyle/hermes-session-tasks` is the install source. The project rules for Claude live in `.claude/CLAUDE.md`.

The boundary rule: the plugin never reads, writes, wraps or replaces `todo_list`.

## Fallback: install the pane by script

The main path is Install from Git in Hermes Desktop (see `README.md`). The script `scripts/install-desktop.ps1` is the fallback.

### How the script installs the pane

The Python half runs on devpc. A symlink in `~/.hermes/plugins/` delivers it.

The Desktop half is one file, `plugin/desktop/plugin.js`. Each Desktop machine needs its own copy on its own disk. The script copies the file from devpc over SSH.

`-RemotePath <path on devpc>` installs another file, for example a frozen test build.

### Install the pane on the Mac

Use PowerShell 7 (`pwsh`).

1. Run `Set-Location ~`.
2. Fetch the script. The SSH config of the Mac names devpc `devbox`. The `-O` flag comes first because Tailscale SSH can have no SFTP subsystem. The plain `scp` runs when the local `scp` does not know `-O`.

   ```powershell
   scp -O devbox:/home/theo/local_repo/hermes-session-tasks/scripts/install-desktop.ps1 install-desktop.ps1; if ($LASTEXITCODE) { scp devbox:/home/theo/local_repo/hermes-session-tasks/scripts/install-desktop.ps1 install-desktop.ps1 }
   ```

3. Run the script. Use the same SSH name for `-DevpcHost`.

   ```powershell
   pwsh -NoProfile -File ./install-desktop.ps1 -DevpcHost devbox
   ```

4. Open Hermes Desktop. When the pane is missing, run `Reload desktop plugins` from the command palette. Then open the Session tasks pane on the right.

The script writes `~/.hermes/desktop-plugins/hermes-session-tasks/plugin.js`. It prints that path and the SHA-256 of the file.

### Install the pane on the Windows PC

Use PowerShell 7 (`pwsh`).

1. Run `Set-Location $HOME`.
2. Fetch the script. The SSH config of the Windows PC names devpc `devpc-ts`.

   ```powershell
   scp -O devpc-ts:/home/theo/local_repo/hermes-session-tasks/scripts/install-desktop.ps1 install-desktop.ps1; if ($LASTEXITCODE) { scp devpc-ts:/home/theo/local_repo/hermes-session-tasks/scripts/install-desktop.ps1 install-desktop.ps1 }
   ```

3. Run the script. Use the same SSH name for `-DevpcHost`.

   ```powershell
   pwsh -NoProfile -File .\install-desktop.ps1 -DevpcHost devpc-ts
   ```

4. Open Hermes Desktop. When the pane is missing, run `Reload desktop plugins` from the command palette. Then open the Session tasks pane on the right.

The script writes `%LOCALAPPDATA%\hermes\desktop-plugins\hermes-session-tasks\plugin.js`. It finds the home the way Desktop does and prints it on the `home:` line. Check that line when the pane does not appear.

### Check before you install

Add `-DryRun` to the script command. The script prints the home, the slot and the source. It writes nothing.

The script tries `scp -O` first and plain `scp` second. This is the same order as the fetch line in step 2. On the Mac and on the Windows PC, `scp -O` worked on the first try.

### Update by script

Run the same script command again. The script replaces `plugin.js` in one move. Then run `Reload desktop plugins` from the command palette. Desktop loads the new file with no backend restart. The pane shows a version line when its copy differs from the backend.

### Known behaviour of the pane

Closing the only pane disables the plugin. Turn it on again under Capabilities, Plugins. You can also use Reset layout.
