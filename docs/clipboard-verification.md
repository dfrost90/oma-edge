# Clipboard verification — 2026-10-11

Target: Oma Edge `9176da947bf23b7045d07df96e548b3746014f4b` (0.1.10),
Omarchy 4.0.4, installed Qt base 6.11.2-3 and declarative 6.11.2-1.

The marketplace report is reproducible. An isolated Wayland server advertised
a text clipboard selection, without a paste action. Its provider sent only
128 KiB over four seconds, then closed the pipe. Native editable TextInput /
TextField controls requested the text immediately and stopped their 250 ms
heartbeat for approximately 4.2 seconds. The numeric validator did not prevent
the transfer. No live desktop clipboard or unbounded allocation was used.

A debugger captured this stack in the installed binaries:

```
QMimeData::text()
QQuickTextInput::q_canPasteChanged()
QQuickTextInput::qt_metacall(...)
QQuickTextField::qt_metacall(...)
QPlatformClipboard::emitChanged(...)
... Wayland event dispatch ...
```

An earlier assessment based on other Qt source revisions missed this eager text
read. The installed binary and local reproduction are the relevant evidence.
Memory exhaustion was not attempted; the bounded test confirms the unsolicited
read and event-loop stall, not an observed out-of-memory termination.

Final saved regression result: baseline one read / 4,143 ms maximum heartbeat
gap; patched zero reads / 263 ms maximum gap. The offscreen Quickshell integration
check also passed class/title filtering (including Ukrainian text) and selection.

## Mitigation

Replace the app-weight text control with a 1–10 dropdown. Keep window filtering
using a native-read-only TextInput that handles bounded keyboard text itself.
Its query is limited to 256 UTF-16 code units without splitting surrogate pairs.
Clipboard paste/cut and IME composition are not supported. Native cursor movement
and selection remain available. The picker retains title/class filtering and
keyboard selection. A local copy of the shared picker avoids changing packaged
Omarchy files or reaching into another component's private object tree.

The patched search made zero clipboard read requests, including an explicit
native paste attempt. A separate Quickshell run with the complete patched
WindowPicker and weight Dropdown also made zero requests and maintained its
250 ms heartbeat. This is plugin-level mitigation, not a fix for other editable
controls in the shell or Qt itself.

## Repeat the bounded reproduction

From `tests/clipboard`:

```sh
gcc server.c -o server $(pkg-config --cflags --libs wayland-server)
g++ -fPIC client.cpp -o client $(pkg-config --cflags --libs Qt6Quick Qt6Gui Qt6Qml)
python3 run.py
```

The runner creates a private runtime directory and socket, executes baseline
and patched inputs, checks provider requests and heartbeat gaps, and tears down
the server. The provider is bounded to 128 KiB / four seconds. No real compositor,
clipboard manager, or desktop shell is connected. Newer Qt may no longer
reproduce the baseline. Socket creation must be allowed by the environment.

`scripts/check.sh` runs the existing Python/Node/Lua checks and, when Qt 6's
qmltestrunner is installed, tests typing, selection replacement, deletion,
Unicode bounds, and rejected paste/cut shortcuts.
