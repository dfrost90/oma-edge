# Promo preview

`preview.png` is the promotional card used by the repository and plugin listing.
The product image is a real Hyprland capture in
[`docs/media/oma-edge-desktop.png`](../media/oma-edge-desktop.png), made on a
separate temporary workspace using the live Oma Edge controller.

All three apps use the self-contained [`demo.html`](demo.html): a fictional code
workspace, focus notes, and an ambient music player. They run in temporary
Chromium profiles. No real documents, chats, accounts, or browser history are
used. The system bar is excluded from the capture, and the desktop image is
reviewed before it is used in the promo.

To refresh the desktop capture on an Omarchy session with Oma Edge running:

```bash
python3 scripts/capture-promo.py
```

The script refuses to use an existing `oma-edge-promo` workspace. It creates only
the demo windows, temporarily adds a right-side strip profile, captures below
the bar, and restores the original configuration, workspace, and focused window.
It closes its own demo browsers afterward.

The promotional card is composed using the built-in image generation tool with
this desktop capture as its reference. The exact prompt is saved in
[`prompt.txt`](prompt.txt). The raw desktop capture remains available so users
can inspect the actual layout independently of the promotional artwork.

The bar and panel icon is drawn directly in QML: one large work area beside two
stacked edge slots. It inherits the current theme and active-state color and
requires no icon font glyph or bitmap asset.
