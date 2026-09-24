#!/usr/bin/env python3
"""Install Oma Edge without replacing or modifying the active bar."""
import argparse
import datetime
import os
import re
from pathlib import Path
import shutil
import subprocess

ID = 'io.github.dfrost90.edge-strip'
ROOT = Path(__file__).resolve().parent
CFG = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))
STAMP = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
BACKUP = CFG/'omarchy/edge-strip-backups'/STAMP
ORIGINALS = {}

def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=30).stdout

def backup(path):
    BACKUP.mkdir(parents=True, exist_ok=True)
    dest = BACKUP/path.relative_to(CFG)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)

def remember(path):
    if path not in ORIGINALS:
        ORIGINALS[path] = path.read_bytes() if path.exists() else None

def write(path, text):
    if path.exists() and path.read_text() == text:
        return
    remember(path)
    if path.exists(): backup(path)
    path.write_text(text)

def remove_bar_adapter(text):
    text = re.sub(r'\n  // EDGE STRIP BAR BEGIN.*?  // EDGE STRIP BAR END\n', '', text, flags=re.S)
    text = re.sub(r'\n    // EDGE STRIP RESERVATION BEGIN.*?    // EDGE STRIP RESERVATION END\n', '', text, flags=re.S)
    text = text.replace('    exclusionMode: root.barHidden || !root.vertical ? ExclusionMode.Ignore : ExclusionMode.Auto // EDGE STRIP EXCLUSION',
                        '    exclusionMode: root.barHidden ? ExclusionMode.Ignore : ExclusionMode.Auto')
    for side in ('left', 'right'):
        text = text.replace('root.edgeStripMargin(barWindow.screen, "'+side+'") // EDGE STRIP MARGIN', '0')
    return text

def remove_legacy_bar_adapters():
    # Upgrade only user-owned files carrying our exact integration markers.
    for path in (CFG/'omarchy/plugins').glob('*/Bar.qml'):
        text = path.read_text()
        clean = remove_bar_adapter(text)
        if clean != text:
            write(path, clean)

def preflight():
    for command in ('hyprctl', 'omarchy', 'omarchy-shell'):
        if not shutil.which(command):
            raise SystemExit(f'Required command not found: {command}')
    target = CFG/'omarchy/plugins'/ID
    if (target.exists() or target.is_symlink()) and target.resolve() != ROOT:
        raise SystemExit(f'{target} already exists; refusing to overwrite another installation')
    if ']]' in str(target/'bridge.lua'):
        raise SystemExit('Unsupported path')
    hypr = CFG/'hypr/hyprland.lua'
    shell_file = CFG/'omarchy/shell.json'
    if not hypr.is_file() or not shell_file.is_file():
        raise SystemExit('Requires Omarchy 4 with Hyprland Lua configuration')
    return hypr, shell_file

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check compatibility without changing files')
    args = parser.parse_args()
    hypr, shell_file = preflight()
    if args.check:
        print('Oma Edge installation preflight passed; no files changed.')
        return
    remember(shell_file)
    remove_legacy_bar_adapters()
    target = CFG/'omarchy/plugins'/ID
    if target.exists() and target.resolve() != ROOT:
        raise SystemExit(f'{target} already exists; refusing to overwrite another installation')
    if not target.exists():
        target.symlink_to(ROOT, target_is_directory=True)
    marker = '-- Edge Strip monitor bridge (must precede monitor configuration)'
    text = hypr.read_text()
    if marker not in text:
        # Lua long strings avoid shell/string interpolation of the path.
        bridge = str(target/'bridge.lua')
        if ']]' in bridge:
            raise SystemExit('Unsupported path')
        write(hypr, marker+'\ndo local f = io.open([['+bridge+']], "r"); if f then f:close(); dofile([['+bridge+']]) end end\n\n'+text)
    run('hyprctl', 'reload')
    errors = run('hyprctl', 'configerrors').strip()
    if errors: raise SystemExit(errors)
    run('omarchy-shell', 'shell', 'rescanPlugins')
    run('omarchy', 'plugin', 'enable', ID)
    run('omarchy', 'restart', 'shell')
    print('Installed Oma Edge. Backups:', BACKUP)

def install_safely():
    target = CFG/'omarchy/plugins'/ID
    created_link = not (target.exists() or target.is_symlink())
    try:
        main()
    except (Exception, SystemExit) as exc:
        if isinstance(exc, SystemExit) and exc.code in (None, 0):
            raise
        for path, original in reversed(list(ORIGINALS.items())):
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
        if created_link and target.is_symlink() and target.resolve() == ROOT:
            target.unlink()
        if ORIGINALS:
            # Reload restored integration files and the prior bar selection.
            for command in (('hyprctl', 'reload'), ('omarchy', 'restart', 'shell')):
                try:
                    run(*command)
                except (OSError, subprocess.SubprocessError):
                    pass
            print('Installation failed; prior configuration restored. Backups:', BACKUP)
        raise

if __name__ == '__main__': install_safely()
