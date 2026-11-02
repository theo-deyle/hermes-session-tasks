# hermes-session-tasks

A Hermes Desktop plugin that gives each Hermes session a task board in a side pane. The agent writes items to the board when it lists things to do or remember. You add, edit, check off and delete items in the pane.

## How it is installed

The Python half runs on devpc. A symlink in `~/.hermes/plugins/` delivers it.

The Desktop half is one file, `plugin/desktop/plugin.js`. Each Desktop machine needs its own copy on its own disk. The script `scripts/install-desktop.ps1` copies the file from devpc over SSH.

`-RemotePath <path on devpc>` installs another file, for example a frozen test build.

## Install the pane on the Mac

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

## Install the pane on the Windows PC

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

## Check before you install

Add `-DryRun` to the script command. The script prints the home, the slot and the source. It writes nothing.

The script tries `scp -O` first and plain `scp` second. This is the same order as the fetch line in step 2. On the Mac and on the Windows PC, `scp -O` worked on the first try.

## Update

Run the same script command again. The script replaces `plugin.js` in one move. Then run `Reload desktop plugins` from the command palette. Desktop loads the new file with no backend restart. The pane shows a version banner when its copy differs from the backend.

## Known behavior

- Closing the only pane disables the plugin. Turn it on again under Capabilities, Plugins. You can also use Reset layout.
- A change to `plugin/dashboard/plugin_api.py` needs a restart of each Desktop backend on devpc. The restart drops the live Desktop connection, so announce it first.
- Any Desktop that signs in to devpc can read and write any board by session id. Devpc serves one user.
- When the pane reports `404 Plugin not found`, Desktop is attached to a backend on another host. Switch Desktop to devpc, then run `Reload desktop plugins`.
