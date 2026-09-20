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
