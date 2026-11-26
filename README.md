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
2. When the update changed Python code, announce the gateway restart. Then run `hermes gateway restart`.
3. On each Desktop machine that has its own Hermes with this plugin, run `hermes plugins update hermes-session-tasks` there too (PowerShell on Windows). Then reload the plugins in Hermes Desktop.
4. On a Desktop machine with no Hermes of its own, install the pane again from Git with Force reinstall.

Desktop copies the pane from the plugin folder of the Hermes on its own machine. When that folder holds an old copy, Desktop puts the old pane back after a Force reinstall from Git. Step 3 prevents that.

### Automatic update

Hermes can pull new versions on its own. Run this one time on each machine that has a Hermes with this plugin:

```
hermes plugins auto-update on
```

- The switch covers every plugin of that Hermes.
- The Hermes gateway of that machine checks every 24 hours. It must run for the check to happen.
- Hermes Desktop shows the new pane after its next start, or after Rescan under Capabilities, Plugins.
- An update that adds an agent tool or a hook waits for `hermes plugins update hermes-session-tasks`.

## Known behaviour

- Tasks on the status bar shows the pane when it is hidden, behind another tab or in a collapsed column. Right-click the status bar to hide or show the Tasks button.
- Closing the only pane disables the plugin. The Tasks button goes away with it. Turn the plugin on again under Capabilities, Plugins. You can also use Reset layout.
- The pane can show `404 Plugin not found` until the gateway or the Desktop backend restarts.
- Any Desktop that signs in to the host can read and write any board by session id.
- Each item shows its number, for example `#3`, to the right of its text. It is the number the agent uses when it names an item.
- The agent sees your edits on its next turn.

## What the plugin stores and reads

- It stores the boards in its own SQLite file. The file sits in the `plugin-data/hermes-session-tasks/` folder of the active profile.
- It reads the `state.db` file of the active profile read-only, for session titles and lineage.
- It makes no network calls. It runs no shell commands. It holds no credentials. It sends no telemetry.

## Contributing

The dev setup and the fallback pane install are in `CONTRIBUTING.md`.
