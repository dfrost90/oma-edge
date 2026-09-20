# Oma Edge 0.1.0 release preparation

Status: initial preview release; see GitHub and the marketplace issue for current publication status.
Repository: `https://github.com/dfrost90/oma-edge`.
Keep plugin ID `io.github.dfrost90.edge-strip` stable for existing installations.

## Validation completed

- 20 Python tests: geometry, validation, restoration, save rollback, install preflight and rollback.
- Node tests: grouped profile persistence, unique slots, deselection, All, empty selection, conflicts.
- Lua bridge tests and parser check.
- Omarchy manifest validation and installer `--check`.
- Live desktop smoke test: right/full-width bar, workspace leave/return, left/layout-width bar, disable; original settings restored.
- Panel loaded after refactor; preview captured with no other application content.
- Hyprland reports no configuration errors.

GitHub Actions runs Python, Node, and Lua checks. Omarchy manifest validation and
live desktop checks require an Omarchy session and are not claimed by generic CI.

## Before publishing

1. Confirm the public repository name and review the README, MIT license, preview,
   and submission checklist. `preview.png` contains only the panel.
2. Create/push the public repository and run its CI. Tag the tested commit `v0.1.0`
   and describe it as an initial preview release. Do not claim multi-monitor hardware validation.
3. Verify a clean installation on Omarchy: plugin add, explicit `install.py --check`,
   `install.py`, UI launch, disable/re-enable, `uninstall.py`. Setup performs user
   configuration edits and needs a **manual-setup** marketplace listing.
4. Use `release/submission.md` as the issue body and `[Plugin]: Oma Edge` as title.
   Replace the proposed URL if needed and confirm every unchecked statement.
5. After owner approval, submit to `omacom/omarchy-plugin-marketplace` using the
   exact issue format. Wait for exact-commit validation and maintainer approval.

The local archive is a convenience artifact. The marketplace validates the public
GitHub repository commit, not this archive.

## References

- https://plugins.omarchy.org/publish.html
- https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md
