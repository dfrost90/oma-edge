# Oma Edge 0.1.10

Fixes horizontal focus getting stuck beside a floating edge app in Hyprland's
scrolling layout. The bridge uses native column navigation only for tiled
scrolling windows on monitors with an active Oma Edge reservation. Existing
keybindings remain in place. Other layouts, floating windows, special workspaces
with other layouts, and monitors without a strip retain ordinary focus. Disabling
the strip restores ordinary focus automatically.

The bar and panel use a theme-aware work-area-and-strip icon. The preview and
README include a promotional image based on fictional demo apps captured on a
separate workspace. The demo capture script restores the user's configuration,
workspace, and focus and closes only its own browsers.

Includes the 0.1.9 private stdin request transport and the 0.1.8 minimum-width
fixes. Existing profiles require no migration. Manual setup remains required:
update the plugin, then reload the bridge and shell using the explicit installer:

```bash
python3 "${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/io.github.dfrost90.edge-strip/install.py" --check
python3 "${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/io.github.dfrost90.edge-strip/install.py"
```

The installer backs up any changed user configuration and rolls it back on
failure. No root access, package downloads, or network access are required.
Marketplace verification must target the final full commit SHA for this release;
it does not cover later upstream changes or replace a security audit.
