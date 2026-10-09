# Oma Edge 0.1.8

Repository: https://github.com/dfrost90/oma-edge
Plugin ID: `io.github.dfrost90.edge-strip`

## Changes

Apps such as Telegram can refuse a narrow strip width on scaled laptop screens.
The controller now learns minimum widths from settled resize responses and
expands the reservation and app geometry together. The saved percentage stays
unchanged and remains the preferred minimum; closing the constrained app lets
the strip shrink again. Constraints are tied to window identity and reset when
the window closes. A minimum wider than the available monitor produces an error.

The profile selector now shows “No profiles” on first run and “New profile”
while creating a profile, instead of exposing the internal -1 index.

## Upgrade

Update the plugin and run `omarchy restart shell` to ensure the new controller
and panel code are loaded. Existing profiles require no migration. First-time
installations still require the explicit `python3 install.py` setup step.

## Validation

- Full Python suite, Node panel checks, Lua bridge checks, syntax checks and
  Omarchy manifest validation pass.
- Regression coverage includes left/right strips at 125% scaling, asynchronous
  resize acknowledgement, app closure and window identity replacement.
- Live laptop check: 1920×1080 at 125% scaling, preferred width 20%, Telegram
  minimum width 323 logical pixels. Reservation expanded from 307 to 347 pixels;
  Telegram occupies x=1201 through 1524 on a 1536-pixel logical screen, leaving
  the expected 12-pixel right margin. Controller reported no error.
- Physical multi-monitor hotplug and arbitrary Overlay-layer bars were not
  tested for this release. The shell's plugin hot-reload issue is not addressed.

## Publication

Build the archive and checksum with `scripts/package.sh`. Release assets are
published under the `v0.1.8` tag as a prerelease, matching the preview status
of earlier Oma Edge releases.
