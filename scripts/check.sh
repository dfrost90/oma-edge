#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
node tests/test_panel.js
lua tests/test_bridge.lua
luac -p bridge.lua
python3 -m py_compile backend.py install.py uninstall.py
if command -v omarchy >/dev/null 2>&1; then
  omarchy plugin validate .
fi

# Qt Quick behavior checks are optional on backend-only CI environments.
if command -v qmake6 >/dev/null 2>&1; then
  qml_test_runner="$(qmake6 -query QT_INSTALL_BINS)/qmltestrunner"
  if [[ -x "$qml_test_runner" ]]; then
    QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME= QT_IM_MODULE= \
      QT_QUICK_BACKEND=software QT_FORCE_STDERR_LOGGING=1 \
      "$qml_test_runner" -input tests/tst_keyboard_search.qml
  fi
fi
