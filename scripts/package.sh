#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
version=$(python3 -c 'import json; print(json.load(open("manifest.json"))["version"])')
mkdir -p dist
tar --exclude='__pycache__' --exclude='*.pyc' -czf "dist/oma-edge-$version.tar.gz" \
  manifest.json Panel.qml Service.qml backend.py bridge.lua install.py uninstall.py \
  README.md LICENSE CHANGELOG.md SECURITY.md preview.png tests scripts release .github .gitignore
(cd dist && sha256sum "oma-edge-$version.tar.gz" > "oma-edge-$version.tar.gz.sha256")
printf 'Created dist/oma-edge-%s.tar.gz\n' "$version"
