### Repository URL

https://github.com/dfrost90/oma-edge

### Category

Desktop

### Tags

hyprland, workspaces, bar

### Suggest a missing tag

_No response_

### Maintainer notes

Oma Edge 0.1.5 is an initial preview. Reserve a left/right strip for real app windows while native tiling uses the remaining monitor area. Includes workspace profiles, app selection, adjustable width/heights with automatic reflow when apps close/reopen, and an always-full-width horizontal bar. This patch removes asynchronous bar margin compensation and uses an input-transparent height reservation surface, preventing workspace-switch bar flicker. Existing users rerun install.py to upgrade the reversible user-owned bar adapter. Terminal selections remain tied to the selected window, with unique-title matching on reopen.

Manual setup required: after plugin installation, explicitly run install.py. It backs up and edits user Hyprland Lua configuration and adapts a compatible user-owned Omarchy bar clone. No privileged installation, package downloads, remote code execution, or network service is used. Uninstall restores the integration; profiles and backups are retained. See README for capabilities, compatibility requirements, and recovery.

Tested on Omarchy 4.0.4 and Hyprland 0.56.2 with one physical monitor. Multi-monitor geometry has unit coverage; physical hotplug has not been validated. Stable plugin ID: io.github.dfrost90.edge-strip.

### Submission checklist

- [x] The repository is public and contains installation and removal instructions.
- [x] I have documented the plugin license and any external dependencies.
- [x] I confirm that I own or have permission to submit this plugin and its preview assets.
- [x] The plugin does not overwrite user configuration without explicit consent.
- [x] I understand that approval is for listing and is not a security review.
