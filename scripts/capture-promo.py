#!/usr/bin/env python3
"""Capture fictional demo apps on a temporary workspace; restore desktop state."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('edge', ROOT / 'backend.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
h = e.Hypr()
original = e.request({'action': 'status'})
monitor = next(m for m in original['monitors'] if m.get('focused'))
original_ws = e.workspace_key(monitor['activeWorkspace'])
original_focus = h.read('activewindow').get('address')
workspace = 'name:oma-edge-promo'
if any(e.workspace_key(w) == workspace for w in original['workspaces']):
    raise SystemExit('Promo workspace already exists; refusing to disturb it.')
output = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'docs/media/oma-edge-desktop.png').resolve()
output.parent.mkdir(parents=True, exist_ok=True)
processes = []
titles = {'work': 'Workspace — Demo', 'notes': 'Focus notes — Demo', 'music': 'Now playing — Demo'}
original_addresses = {c['address'] for c in original['clients']}

def focus(ws):
    h.run('eval', 'hl.dispatch(hl.dsp.focus({workspace=' + e.lua_string(ws) + '}))')

def save(config):
    result = e.request({'action': 'save', 'config': config})
    if not result.get('ok'): raise RuntimeError(result)

try:
    with tempfile.TemporaryDirectory(prefix='oma-edge-promo-') as profiles:
        focus(workspace)
        for mode in ('work', 'notes', 'music'):
            args = ['chromium', '--no-first-run', '--no-default-browser-check',
                    '--disable-background-networking', '--disable-component-update', '--disable-sync',
                    '--user-data-dir=' + str(Path(profiles)/mode), '--class=oma-edge-demo-' + mode,
                    '--app=' + (ROOT/'docs/promo/demo.html').as_uri() + '?mode=' + mode]
            processes.append(subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            clients = h.read('clients')
            demo = {mode: c for mode, title in titles.items() for c in clients
                    if c['title'] == title and c['address'] not in original_addresses}
            if len(demo) == 3: break
            time.sleep(.2)
        else: raise RuntimeError('Demo apps did not open')
        # Move only newly opened fictional demo windows if the workspace changed.
        for c in demo.values():
            h.dispatch('movetoworkspacesilent', workspace+',address:'+c['address'])
        config = copy.deepcopy(original['config'])
        config['enabled'] = True
        config['profiles'].append({'monitor': monitor['name'], 'workspace': workspace,
            'enabled': True, 'width': 27, 'side': 'right', 'slots': [
                {'id': 'promo-'+mode, 'class': demo[mode]['class'],
                 'label': label, 'weight': weight, 'preferred': demo[mode].get('stableId',''),
                 'windowTitle': demo[mode]['title']}
                for mode,label,weight in [('notes','Focus notes',4),('music','Now playing',6)]]})
        save(config)
        focus(workspace)
        h.run('eval','hl.dispatch(hl.dsp.focus({window='+e.lua_string('address:'+demo['work']['address'])+'}))')
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            status = e.request({'action':'status'})
            if status.get('error'): raise RuntimeError(status['error'])
            managed = [c for c in status['clients'] if c['address'] in (demo['notes']['address'],demo['music']['address'])]
            if len(managed) == 2 and all(c['floating'] for c in managed): break
            time.sleep(.2)
        else: raise RuntimeError('Strip apps were not placed')
        time.sleep(2)
        m = next(m for m in h.read('monitors') if m['name']==monitor['name'])
        if e.workspace_key(m['activeWorkspace']) != workspace or m.get('specialWorkspace', {}).get('id', 0):
            raise RuntimeError('Workspace changed before capture; refusing to capture other content')
        demo_addresses = {c['address'] for c in demo.values()}
        for client in h.read('clients'):
            if client['mapped'] and not client.get('hidden') and client['monitor'] == m['id']:
                if (e.workspace_key(client['workspace']) == workspace or client.get('pinned')) and client['address'] not in demo_addresses:
                    raise RuntimeError('Non-demo window present; refusing to capture')
        w,height = e.logical_size(m)
        # Omit the global system bar, including all user widgets and clock.
        top = max(30, m['reserved'][1])
        region = f"{m['x']},{m['y']+top} {w}x{height-top}"
        subprocess.run(['grim','-s','1','-g',region,str(output)],check=True)
        print('Captured fictional demo workspace:',output)
        save(original['config'])
        for process in processes:
            process.terminate()
        for process in processes:
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
finally:
    save(original['config'])
    for process in processes:
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
    focus(original_ws)
    if original_focus:
        h.run('eval','hl.dispatch(hl.dsp.focus({window='+e.lua_string('address:'+original_focus)+'}))')
    print('Original configuration, workspace, and focus restored.')
