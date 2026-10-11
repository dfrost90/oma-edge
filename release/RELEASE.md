# Oma Edge 0.1.11

Fixes the clipboard-read issue reported by HANCORE-linux on marketplace #10880.
On the tested Qt 6.11.2 build, editable native text controls request clipboard
text on clipboard changes, even without paste, before field validation.

App weights now use a 1–10 dropdown. Window search retains title/class filtering,
selection, cursor movement, and deletion through a bounded keyboard-only field
that remains native-read-only. Search paste/cut and IME composition are unavailable.
This mitigates Oma Edge's controls, not unrelated shell inputs or Qt itself.

A bounded provider on a private Wayland server reproduced one unsolicited read
and a 4,143 ms event-loop stall before the fix. Patched inputs made zero reads,
with a maximum heartbeat gap of 263 ms. The provider sent only 128 KiB over four
seconds; memory exhaustion was not attempted. The desktop clipboard was untouched.
See [verification and reproduction instructions](../docs/clipboard-verification.md).

Validation: 44 Python tests, Node panel checks, Lua bridge/syntax checks, Omarchy
manifest validation, Qt Quick keyboard tests, isolated clipboard regression,
and Quickshell picker filtering/selection checks passed locally. Packaging includes
both new QML components and excludes compiled reproduction binaries.

Retains the 0.1.10 scrolling-focus fix and 0.1.9 private stdin transport.
Existing profiles require no migration. Manual setup remains required:

```sh
python3 "${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/io.github.dfrost90.edge-strip/install.py" --check
python3 "${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/io.github.dfrost90.edge-strip/install.py"
```

The installer backs up changed user configuration and rolls it back on failure.
Marketplace verification must target the new exact commit. Older release tags
remain unchanged. This prerelease does not claim marketplace approval or a
security audit; manual-setup metadata and approval require maintainer review.
