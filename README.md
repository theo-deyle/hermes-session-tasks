# Session Tasks

The agent adds what you must do, decide or remember to a per-session board. You check, edit and delete the items in a Hermes Desktop side pane.

## Install on a Hermes host

1. Run this command on the host:

   ```
   hermes plugins install theo-deyle/hermes-session-tasks#plugin --enable
   ```

   In zsh, put the identifier in quotes, because `#` starts a comment there.

   The command prints "custom (unreviewed) source". This is normal for an install outside the catalog.

2. Announce the gateway restart to the people who use the host. The restart drops live Desktop connections.
3. Run `hermes gateway restart`.

After `--enable`, the hooks are live at once. The board tools reach new chats. The pane routes need the gateway restart. Until the restart, the pane can show `404 Plugin not found`.

## Install the pane in Hermes Desktop

1. Open Capabilities, Plugins in Hermes Desktop.
2. Choose Install from Git.
3. Paste `https://github.com/theo-deyle/hermes-session-tasks#plugin`. The path form `theo-deyle/hermes-session-tasks/plugin` also works.
4. Press Install.
5. When the plugin shows as off, turn it on.
6. Open the Session tasks pane on the right. To bring it into view at any time, click Tasks on the status bar at the bottom, or run Show Session tasks from the command palette.

The short form with `#` does not work in this dialog. Desktop turns it into a wrong URL.

When Hermes and Desktop run on the same machine, Desktop copies the pane from the installed package. No Git install is needed.

When the Hermes half on the host is already installed, the dialog reports it as already installed. The pane half still installs.

When an older hand-installed pane copy exists, the dialog says `Desktop plugin 'hermes-session-tasks' already exists. Enable force reinstall to replace it.` Then tick Force reinstall under Advanced.

The pane can stay off after the install. Turn it on under Capabilities, Plugins.

## Update

1. Run `hermes plugins update hermes-session-tasks` on the host.
2. Announce the gateway restart. Then run `hermes gateway restart`.
3. In Hermes Desktop, the pane shows a version line when its copy differs from the host. Then install the pane again from Git with Force reinstall.

## Known behaviour

- Tasks on the status bar shows the pane when it is hidden, behind another tab or in a collapsed column. Right-click the status bar to hide or show the Tasks button.
- Closing the only pane disables the plugin. The Tasks button goes away with it. Turn the plugin on again under Capabilities, Plugins. You can also use Reset layout.
- The pane can show `404 Plugin not found` until the gateway or the Desktop backend restarts.
- Any Desktop that signs in to the host can read and write any board by session id.
- The agent sees your edits on its next turn.

## What the plugin stores and reads

- It stores the boards in its own SQLite file. The file sits in the `plugin-data/hermes-session-tasks/` folder of the active profile.
- It reads the `state.db` file of the active profile read-only, for session titles and lineage.
- It makes no network calls. It runs no shell commands. It holds no credentials. It sends no telemetry.

## Contributing

The dev setup and the fallback pane install are in `CONTRIBUTING.md`.
