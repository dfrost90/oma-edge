# Oma Edge 0.1.5

Repository: https://github.com/dfrost90/oma-edge
Plugin ID: `io.github.dfrost90.edge-strip`

## Changes

Horizontal bars stay full-width. A transparent, input-transparent surface reserves
bar height independently of the visible bar, removing the state watcher and
negative-margin compensation. The panel no longer offers a full-width toggle.
Older profile settings are accepted and normalized without `fullBar`.

## Upgrade

Existing users must rerun `python3 install.py` after updating to migrate their
local bar adapter. Setup backs up the clone and uninstall removes the adapter.

## Validation

- 31 Python tests, Node panel tests, Lua bridge tests and syntax checks pass.
- Adapter upgrade is idempotent and exactly reversible against a legacy fixture.
- Live desktop checks pass for right and left strips, workspace leave/return,
  and disabling the strip; original settings and focus restored.
- The same full-width bar surface and geometry persisted across 86 samples
  spanning both workspace transitions. No Hyprland configuration errors.
- Physical multi-monitor hotplug remains unverified.

## Publication

Publish the tested commit as preview tag `v0.1.5` with the archive and checksum
from `scripts/package.sh`. Keep the marketplace issue body synchronized with
`release/submission.md`; manual setup still requires maintainer review.
