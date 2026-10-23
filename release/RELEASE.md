# Oma Edge 0.1.12

Restores theme colors for the panel's custom labels, header icon and layout
preview and window picker. Failed saves now preserve the selected profile and unsaved edits.
Slot IDs remain stable when apps are reordered, weights change or workspaces
are added and removed.

Unchanged reconciliation uses four compositor queries instead of eight and
skips identical recovery journal writes. Recovery records are still written
before window mutations. Monitor reservations are applied together, with
acknowledgements handled by the event loop so workspace events and status
requests remain responsive. Save replies wait for acknowledgement or rollback.

Profile transformations are extracted into `ProfileModel.js`, and controller
reconciliation is separated into snapshot indexing, constraint tracking,
planning, window updates and recovery stages.

Retains the clipboard-safe weight selector and bounded, native-read-only window
search from 0.1.11, along with the scrolling-focus fix and private stdin transport.

## Verification

- 51 Python tests, including an isolated daemon test for deferred saves and
  status requests, plus simulated multi-monitor acknowledgement and rollback.
- JavaScript checks for profile selection, stable slot IDs and private request
  transport; Lua bridge checks and syntax checks; Qt Quick keyboard-search tests.
- Quickshell execution of the extracted profile model and visual inspection
  of the installed panel.
- Bounded private-Wayland clipboard regression: baseline one unsolicited read
  and a 4,071 ms heartbeat gap; patched zero reads and a 252 ms maximum gap.
  The test does not connect to the desktop clipboard.
- Desktop smoke checks for right/left reservations, workspace switching,
  full-width bar stability, disabling and restoration of configuration/focus.

Physical multi-monitor hotplug and a clean first installation in a separate
Omarchy session remain unverified. Individual compositor commands and incoming
request reads remain synchronous.

## Updating

Existing profiles require no migration. Include `ProfileModel.js` when updating
the plugin; it is included alongside `WindowPicker.qml` and `KeyboardSearch.qml`
in the release archive. Manual setup remains required:

```bash
python3 "${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/io.github.dfrost90.edge-strip/install.py" --check
python3 "${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/io.github.dfrost90.edge-strip/install.py"
```

The installer backs up changed user configuration and rolls it back on failure.
No root access, package downloads or network access are required by the installer.
Marketplace verification must target the final full commit SHA for this release;
it does not cover later upstream changes or replace a security audit.
