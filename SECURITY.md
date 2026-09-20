# Capabilities and reporting

Oma Edge runs as the logged-in user. It reads window classes, titles, geometry,
and workspace/monitor state through local Hyprland IPC. It moves/resizes/pins
assigned windows and adjusts monitor reserved areas through the Lua bridge.
The panel and controller communicate through a private Unix socket; runtime
state and configuration files are written with user-only permissions.

Explicit installation edits user Hyprland configuration and a local Omarchy bar
clone, with backups and failure rollback. Uninstall reverses those integrations.
The plugin does not make network requests, download code, install packages,
request root access, collect analytics, or read application contents.

Report reproducible bugs through the repository's issue tracker after it is
published. Avoid attaching unredacted state.json or status output: they include
window titles and application identifiers. Use GitHub private vulnerability
reporting if enabled; do not post sensitive exploit details publicly.
