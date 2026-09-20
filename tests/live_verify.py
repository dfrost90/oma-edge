"""Authorized desktop smoke test. Temporarily changes one monitor; restores config/focus."""
import copy
import importlib.util
from pathlib import Path
import time

spec = importlib.util.spec_from_file_location('edge', Path(__file__).parents[1] / 'backend.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
h = e.Hypr()
original = e.request({'action': 'status'})
monitor = next((m for m in original['monitors'] if m.get('focused')), original['monitors'][0])
name = monitor['name']
original_ws = e.workspace_key(monitor['activeWorkspace'])
original_focus = h.read('activewindow').get('address')
base_left = monitor['reserved'][0] - original['bars'].get(name, {}).get('left', 0)
base_right = monitor['reserved'][2] - original['bars'].get(name, {}).get('right', 0)
probe_ws = str(max([w['id'] for w in original['workspaces'] if w['id'] > 0] + [10]) + 1)

def save(config):
    result = e.request({'action': 'save', 'config': config})
    assert result.get('ok'), result

def focus(ws):
    h.run('eval', 'hl.dispatch(hl.dsp.focus({workspace=' + e.lua_string(ws) + '}))')

def check(label, left=0, right=0, full=True):
    deadline = time.monotonic() + 6
    last = None
    while time.monotonic() < deadline:
        state = e.request({'action': 'status'})
        m = next(m for m in state['monitors'] if m['name'] == name)
        layers = h.read('layers')[name]['levels']
        bar = next((l for group in layers.values() for l in group if l['namespace'] == 'omarchy-bar'), None)
        last = (m['reserved'], bar, state['error'])
        expected_bar = e.logical_size(m)[0] - base_left - base_right - (0 if full else left + right)
        if (not state['error'] and m['reserved'][0] == base_left + left
                and m['reserved'][2] == base_right + right and bar and bar['w'] == expected_bar):
            assert abs(m['refreshRate'] - monitor['refreshRate']) < .1
            print(label + ': PASS', flush=True)
            return
        time.sleep(.15)
    raise AssertionError((label, last))

try:
    cfg = copy.deepcopy(original['config'])
    active = e.active_profile(cfg, monitor)
    profile = copy.deepcopy(active) if active else {'slots': []}
    profile.pop('group', None)
    profile.update(monitor=name, workspace=original_ws, enabled=True, width=20, side='right', fullBar=True)
    cfg['profiles'] = [p for p in cfg['profiles'] if p['monitor'] != name] + [profile]
    cfg['enabled'] = True
    width = round(e.logical_size(monitor)[0] * .2)
    save(cfg)
    check('Right strip / full bar', right=width)
    focus(probe_ws)
    check('Unconfigured workspace releases strip')
    focus(original_ws)
    check('Returning restores strip', right=width)
    profile['side'] = 'left'
    profile['fullBar'] = False
    save(cfg)
    check('Left strip / layout-width bar', left=width, full=False)
    cfg['enabled'] = False
    save(cfg)
    check('Disable releases strip')
finally:
    save(original['config'])
    focus(original_ws)
    if original_focus:
        h.run('eval', 'hl.dispatch(hl.dsp.focus({window=' + e.lua_string('address:' + original_focus) + '}))')
    print('Original configuration and focus restored', flush=True)
