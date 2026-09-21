#!/usr/bin/env python3
"""Install the plugin and a reversible adapter for Omarchy's local bar clone."""
import argparse
import datetime
import json
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

def render_bar_adapter(text):
    # Normalize old adapters too, so rerunning setup upgrades installed clones.
    text = remove_bar_adapter(text)
    if 'component BarPanel: PanelWindow' not in text:
        raise SystemExit('This custom bar is not compatible with the Omarchy bar adapter. No changes made.')
    left = '      left: root.barHidden && root.position === "left" ? -root.barSize : 0'
    right = '      right: root.barHidden && root.position === "right" ? -root.barSize : 0'
    exclusion = '    exclusionMode: root.barHidden ? ExclusionMode.Ignore : ExclusionMode.Auto'
    if (text.count(left) != 1 or text.count(right) != 1 or text.count('  id: root\n') != 1
            or text.count(exclusion) != 1 or text.count('    id: barWindow\n') != 1):
        raise SystemExit('Bar source has changed; adapter needs review. No bar changes made.')
    reservation = '''
    // EDGE STRIP RESERVATION BEGIN
    // Drawing ignores exclusion zones; this input-transparent surface reserves
    // the bar height independently, so strip changes cannot resize the bar.
    PanelWindow {
      screen: barWindow.screen
      visible: !root.vertical && !root.barHidden && barWindow.visible
      anchors.top: root.position === "top"
      anchors.bottom: root.position === "bottom"
      anchors.left: true
      anchors.right: true
      implicitHeight: root.barSize
      color: "transparent"
      mask: Region {}
      exclusionMode: ExclusionMode.Auto
      WlrLayershell.namespace: "omarchy-edge-bar-reservation"
      WlrLayershell.layer: WlrLayer.Top
    }
    // EDGE STRIP RESERVATION END
'''
    text = text.replace('    id: barWindow\n', '    id: barWindow\n'+reservation, 1)
    text = text.replace(exclusion, '    exclusionMode: root.barHidden || !root.vertical ? ExclusionMode.Ignore : ExclusionMode.Auto // EDGE STRIP EXCLUSION')
    return text

def remove_bar_adapter(text):
    text = re.sub(r'\n  // EDGE STRIP BAR BEGIN.*?  // EDGE STRIP BAR END\n', '', text, flags=re.S)
    text = re.sub(r'\n    // EDGE STRIP RESERVATION BEGIN.*?    // EDGE STRIP RESERVATION END\n', '', text, flags=re.S)
    text = text.replace('    exclusionMode: root.barHidden || !root.vertical ? ExclusionMode.Ignore : ExclusionMode.Auto // EDGE STRIP EXCLUSION',
                        '    exclusionMode: root.barHidden ? ExclusionMode.Ignore : ExclusionMode.Auto')
    for side in ('left', 'right'):
        text = text.replace('root.edgeStripMargin(barWindow.screen, "'+side+'") // EDGE STRIP MARGIN', '0')
    return text

def bar_adapter(bar_path):
    write(bar_path, render_bar_adapter(bar_path.read_text()))

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
    shell = json.loads(shell_file.read_text())
    bar_id = shell.get('bar', {}).get('id', 'omarchy.bar')
    bar_path = (Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy'))/'shell/plugins/bar/Bar.qml'
                if bar_id == 'omarchy.bar' else CFG/'omarchy/plugins'/bar_id/'Bar.qml')
    if not bar_path.is_file():
        raise SystemExit('Requires an Omarchy-compatible bar')
    render_bar_adapter(bar_path.read_text())  # Validate before touching any configuration.
    return hypr, shell_file, shell, bar_id

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check compatibility without changing files')
    args = parser.parse_args()
    hypr, shell_file, shell, bar_id = preflight()
    if args.check:
        print('Oma Edge installation preflight passed; no files changed.')
        return
    remember(shell_file)
    if bar_id == 'omarchy.bar':
        backup(shell_file)
        run('omarchy', 'plugin', 'clone', 'omarchy.bar')
        shell = json.loads(shell_file.read_text())
        bar_id = shell['bar']['id']
    bar_dir = CFG/'omarchy/plugins'/bar_id
    bar_path = bar_dir/'Bar.qml'
    if not bar_path.exists():
        raise SystemExit('Full-width bar support requires an Omarchy-compatible local bar clone')
    bar_adapter(bar_path)
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
            # Keep any newly cloned bar files, but restore the prior bar selection.
            for command in (('hyprctl', 'reload'), ('omarchy', 'restart', 'shell')):
                try:
                    run(*command)
                except (OSError, subprocess.SubprocessError):
                    pass
            print('Installation failed; prior configuration restored. Backups:', BACKUP)
        raise

if __name__ == '__main__': install_safely()
