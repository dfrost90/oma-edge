# Oma Edge 0.1.6

Repository: https://github.com/dfrost90/oma-edge
Plugin ID: `io.github.dfrost90.edge-strip`

## Changes

The standard horizontal Omarchy bar stays full-width while Oma Edge reserves
side space through its own transparent, input-transparent Overlay surfaces.
No custom bar clone is required, preserving standard bar service access for
plugins such as OmaChat. The controller waits for compositor confirmation of
reservations before positioning windows. The Lua bridge now only forwards
layout-change events and does not modify monitor rules.

## Upgrade

After updating, rerun `python3 install.py`. Setup keeps the selected bar and
backs up/removes legacy Oma Edge adapters from saved local bar clones. To switch
from a previous clone to the standard bar, run `omarchy plugin enable omarchy.bar`.

## Validation

- 33 Python tests, Node panel tests, Lua bridge tests and syntax checks pass.
- Plugin manifest validation and installer preflight pass.
- Live checks pass for left/right strips, workspace leave/return and disabling;
  the original settings and focus are restored.
- The standard bar remained 3440 pixels wide with unchanged surface identity
  across 81 samples covering both workspace transitions.
- No Hyprland configuration errors. Physical multi-monitor hotplug and arbitrary
  third-party bars using Overlay-layer reservations remain unverified.

## Publication

The source version is 0.1.6. Build the archive and checksum using
`scripts/package.sh` when preparing a GitHub release. The marketplace submission
text is maintained in `release/submission.md`; manual setup remains required.
