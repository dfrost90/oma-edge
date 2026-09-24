# Capabilities and reporting

Oma Edge runs as the logged-in user. It reads window classes, titles, geometry,
and workspace/monitor state through local Hyprland IPC. It moves/resizes/pins
assigned windows and reserves side space using transparent, input-transparent
Wayland layer surfaces owned by the service. The Lua bridge only emits layout
notifications; monitor configuration is not modified.
The panel and controller communicate through a private Unix socket; runtime
state and configuration files are written with user-only permissions.

Explicit installation edits user Hyprland configuration, with backups and failure
rollback. Upgrades remove legacy Oma Edge adapter blocks from user bar clones;
new installs do not clone or patch bars. Uninstall reverses those integrations.
The plugin does not make network requests, download code, install packages,
request root access, collect analytics, or read application contents.

Report reproducible bugs through the repository's issue tracker after it is
published. Avoid attaching unredacted state.json or status output: they include
window titles and application identifiers. Use GitHub private vulnerability
reporting if enabled; do not post sensitive exploit details publicly.
