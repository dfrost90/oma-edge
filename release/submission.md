### Repository URL

https://github.com/dfrost90/oma-edge

### Category

Desktop

### Tags

hyprland, workspaces, bar

### Suggest a missing tag

_No response_

### Maintainer notes

Oma Edge 0.1.6 is a preview. Reserve a left/right strip for real app windows while native tiling uses the remaining monitor area. Includes workspace profiles, app selection, adjustable width/heights with automatic reflow when apps close/reopen, and a full-width standard horizontal bar. The plugin now owns transparent side-reservation surfaces; it no longer requires a custom bar clone or patches the active bar. Existing users rerun install.py to reload the new bridge and remove legacy adapters from saved clones. Terminal selections remain tied to the selected window, with unique-title matching on reopen.

Manual setup required: after plugin installation, explicitly run install.py. It backs up and edits user Hyprland Lua configuration for layout notifications and removes legacy Oma Edge bar adapters when present. The selected bar is preserved. No privileged installation, package downloads, remote code execution, or network service is used. Uninstall removes the integration; profiles and backups are retained. See README for capabilities, compatibility requirements, and recovery.

Tested on Omarchy 4.0.4 and Hyprland 0.56.2 with one physical monitor. Multi-monitor geometry has unit coverage; physical hotplug has not been validated. Stable plugin ID: io.github.dfrost90.edge-strip.

### Submission checklist

- [x] The repository is public and contains installation and removal instructions.
- [x] I have documented the plugin license and any external dependencies.
- [x] I confirm that I own or have permission to submit this plugin and its preview assets.
- [x] The plugin does not overwrite user configuration without explicit consent.
- [x] I understand that approval is for listing and is not a security review.
