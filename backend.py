#!/usr/bin/env python3
"""Oma Edge: event-driven Hyprland controller and local panel RPC."""
import copy
import fcntl
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import socket
import subprocess
import sys
import tempfile
import time

CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'omarchy/edge-strip.json'
RUNTIME = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'omarchy-edge-strip'
DEFAULT = {'version': 1, 'enabled': True, 'profiles': []}

def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    # A unique, private sibling avoids collisions between recovery and daemon writes.
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)

def lua_string(value):
    # Byte escapes are unambiguous in Lua, including quotes/newlines/Unicode.
    return '"' + ''.join('\\%03d' % b for b in str(value).encode()) + '"'

def validate(data):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Unsupported configuration version')
    if type(data.get('enabled')) is not bool or not isinstance(data.get('profiles'), list):
        raise ValueError('Expected enabled flag and profiles list')
    if len(data['profiles']) > 100:
        raise ValueError('Too many profiles')
    result = {'version': 1, 'enabled': data['enabled'], 'profiles': []}
    seen = set()
    ids = set()
    groups = {}
    for p in data['profiles']:
        if not isinstance(p, dict):
            raise ValueError('Each profile must be an object')
        monitor, workspace = p.get('monitor', ''), p.get('workspace', '')
        for value in (monitor, workspace):
            if not isinstance(value, str) or not value or len(value) > 200 or any(c in value for c in ',\n\r\x00'):
                raise ValueError('Choose a valid monitor and workspace')
        if workspace != '*' and not (re.fullmatch(r'[1-9][0-9]*', workspace) or (workspace.startswith('name:') and len(workspace) > 5)):
            raise ValueError('Workspace must be a positive number, name:NAME, or *')
        key = (monitor, workspace)
        if key in seen:
            raise ValueError('Only one profile per monitor/workspace is allowed')
        seen.add(key)
        width = p.get('width', 20)
        if type(width) not in (int, float) or not math.isfinite(width) or not 10 <= width <= 45:
            raise ValueError('Strip width must be between 10% and 45%')
        if p.get('side') not in ('left', 'right'):
            raise ValueError('Choose left or right')
        if type(p.get('enabled')) is not bool or type(p.get('fullBar')) is not bool:
            raise ValueError('Expected enabled and fullBar flags')
        slots = p.get('slots', [])
        if not isinstance(slots, list) or len(slots) > 6:
            raise ValueError('A strip supports up to six app slots')
        clean_slots = []
        for s in slots:
            if not isinstance(s, dict):
                raise ValueError('Each app slot must be an object')
            ident, cls = s.get('id', ''), s.get('class', '')
            if not isinstance(ident, str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}', ident) or ident in ids:
                raise ValueError('App slot IDs must be unique')
            ids.add(ident)
            if not isinstance(cls, str) or not cls or len(cls) > 512:
                raise ValueError('Choose an app window')
            weight = s.get('weight', 1)
            if type(weight) not in (int, float) or not math.isfinite(weight) or not 1 <= weight <= 10:
                raise ValueError('App height weight must be between 1 and 10')
            clean_slots.append({'id': ident, 'class': cls, 'label': str(s.get('label', cls))[:200],
                                'weight': weight, 'preferred': str(s.get('preferred', ''))[:100]})
        result['profiles'].append({'monitor': monitor, 'workspace': workspace, 'enabled': p['enabled'],
                                   'width': width, 'side': p['side'], 'fullBar': p['fullBar'], 'slots': clean_slots})
        if 'group' in p:
            group = p['group']
            if not isinstance(group, str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}', group):
                raise ValueError('Invalid workspace group')
            clean = result['profiles'][-1]
            signature = {k: v for k, v in clean.items() if k not in ('workspace', 'slots')}
            signature['slots'] = [{k: v for k, v in slot.items() if k != 'id'} for slot in clean['slots']]
            if group in groups and groups[group] != signature:
                raise ValueError('Grouped workspaces must share monitor, layout and apps')
            groups[group] = signature
            clean['group'] = group

    return result

def workspace_key(ws):
    return str(ws['id']) if ws['id'] > 0 else (ws['name'] if ws['name'].startswith('special:') else 'name:' + ws['name'])

def active_profile(config, monitor):
    if not config['enabled']:
        return None
    ws = workspace_key(monitor['activeWorkspace'])
    matches = [p for p in config['profiles'] if p['monitor'] == monitor['name']]
    p = next((p for p in matches if p['workspace'] == ws), None)
    if p is None:
        p = next((p for p in matches if p['workspace'] == '*'), None)
    return p if p and p['enabled'] else None

def logical_size(m):
    w, h = m['width'], m['height']
    if m.get('transform', 0) % 2:
        w, h = h, w
    return round(w / m['scale']), round(h / m['scale'])

def geometry(m, p, current=(0, 0)):
    w, h = logical_size(m)
    strip = round(w * p['width'] / 100)
    left, top, right, bottom = m.get('reserved', [0, 0, 0, 0])
    left, right = max(0, left-current[0]), max(0, right-current[1])
    x = m['x'] + (left if p['side'] == 'left' else w-right-strip)
    y = m['y'] + top + 12
    available = h-top-bottom-24 - max(0, len(p['slots'])-1)*14
    if available < len(p['slots'])*100 or strip < 100:
        raise ValueError('Not enough screen space for this many slots')
    total = sum(s['weight'] for s in p['slots']) or 1
    consumed = 0
    boxes = []
    acc = 0
    for i, slot in enumerate(p['slots']):
        acc += slot['weight']
        end = round(available*acc/total)
        height = end-consumed
        boxes.append((x+12, y+consumed+i*14, strip-24, height))
        consumed = end
    return strip, boxes

class Hypr:
    def run(self, *args):
        p = subprocess.run(['hyprctl', *args], capture_output=True, text=True, timeout=5)
        output = p.stdout.strip()
        if p.returncode or 'error' in output.lower() or 'not found' in output.lower() or "can't" in output.lower():
            raise RuntimeError(output or p.stderr.strip() or 'Hyprland command failed')
        return output

    def read(self, name):
        # Window titles may contain the word "error": don't interpret JSON as status.
        p = subprocess.run(['hyprctl', '-j', name], capture_output=True, text=True, timeout=5, check=True)
        return json.loads(p.stdout)

    def reserve(self, name, left, right):
        self.run('eval', 'assert(omarchy_edge_strip, "Oma Edge bridge is not installed"); '
                 f'omarchy_edge_strip.reserve({lua_string(name)}, {int(left)}, {int(right)})')

    def dispatch(self, name, value):
        # Lua-configured Hyprland requires typed dispatchers, including over IPC.
        if name == 'pin':
            method, fields = 'pin', 'action="toggle", window='+lua_string(value)
        elif name in ('setfloating', 'settiled'):
            method, fields = 'float', 'action='+lua_string('set' if name == 'setfloating' else 'unset')+', window='+lua_string(value)
        elif name == 'movetoworkspacesilent':
            ws, window = value.rsplit(',', 1)
            method, fields = 'move', 'workspace='+lua_string(ws)+', follow=false, window='+lua_string(window)
        elif name in ('resizewindowpixel', 'movewindowpixel'):
            coords, window = value.rsplit(',', 1)
            _, x, y = coords.split()
            method = 'resize' if name == 'resizewindowpixel' else 'move'
            fields = f'x={int(x)}, y={int(y)}, relative=false, window='+lua_string(window)
        else:
            raise ValueError('Unsupported window action')
        self.run('eval', 'hl.dispatch(hl.dsp.window.'+method+'({'+fields+'}))')

class Controller:
    def __init__(self, hypr=None):
        self.hypr = hypr or Hypr()
        self.config = copy.deepcopy(DEFAULT)
        self.reservations = {}
        self.managed = {}
        self.bindings = {}
        self.error = ''
        self.config_error = ''
        self.last_state = None
        self.monitors = []
        self.clients = []
        self.workspaces = []
        self.journal_path = RUNTIME/'journal.json'
        if self.journal_path.exists():
            saved = json.loads(self.journal_path.read_text())
            if saved.get('session') == os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
                self.managed = saved.get('managed', {})
                self.reservations = {k: tuple(v) for k, v in saved.get('reservations', {}).items()}

    def load(self):
        self.config = validate(json.loads(CONFIG.read_text())) if CONFIG.exists() else copy.deepcopy(DEFAULT)
        self.config_error = ''

    def journal(self):
        atomic_json(self.journal_path, {'session': os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'),
                                     'managed': self.managed, 'reservations': self.reservations})

    def identity(self, c):
        return str(c.get('stableId', '')) + ':' + str(c['pid']) + ':' + c['class']

    def restore(self, address, c):
        original = self.managed.get(address)
        if not original:
            return
        if c and self.identity(c) == original['identity']:
            target = 'address:' + address
            if c['pinned']:
                self.hypr.dispatch('pin', target)
            self.hypr.dispatch('movetoworkspacesilent', original['workspace']+','+target)
            if original['floating']:
                self.hypr.dispatch('setfloating', target)
                self.hypr.dispatch('resizewindowpixel', f"exact {original['size'][0]} {original['size'][1]},{target}")
                self.hypr.dispatch('movewindowpixel', f"exact {original['at'][0]} {original['at'][1]},{target}")
                if original['pinned']:
                    self.hypr.dispatch('pin', target)
            else:
                self.hypr.dispatch('settiled', target)
        self.managed.pop(address, None)
        self.journal()

    def refresh(self):
        self.monitors = self.hypr.read('monitors')
        self.clients = self.hypr.read('clients')
        self.workspaces = self.hypr.read('workspaces')

    def reconcile(self, config_reload=False):
        try:
            self.refresh()
            if config_reload:
                self.reservations = {}
            active = {m['name']: active_profile(self.config, m) for m in self.monitors}
            boxes = {}
            for m in self.monitors:
                p = active[m['name']]
                current = self.reservations.get(m['name'], (0, 0))
                width = geometry(m, p, current)[0] if p else 0
                desired = (width, 0) if p and p['side'] == 'left' else (0, width)
                if desired != current:
                    # Journal before mutation for recovery if the controller stops mid-apply.
                    self.reservations[m['name']] = desired
                    self.journal()
                    try:
                        self.hypr.reserve(m['name'], *desired)
                    except Exception:
                        self.reservations[m['name']] = current
                        self.journal()
                        raise
                for profile in self.config['profiles']:
                    if self.config['enabled'] and profile['enabled'] and profile['monitor'] == m['name']:
                        workspace = next((w for w in self.workspaces if workspace_key(w) == profile['workspace']), None)
                        # A profile is tied to a monitor: don't pull a workspace
                        # back from another display merely because it has apps.
                        if workspace and workspace.get('monitor') != m['name']:
                            continue
                        boxes[id(profile)] = geometry(m, profile, current)[1]
            used = set()
            by_address = {c['address']: c for c in self.clients}
            by_class = {}
            for client in self.clients:
                if client['mapped'] and (client['address'] in self.managed or
                        not (client.get('fullscreen') or client.get('grouped'))):
                    by_class.setdefault(client['class'], []).append(client)
            profiles = [p for p in self.config['profiles'] if id(p) in boxes]
            # Visible profiles get first claim if several profiles match the same app.
            profiles.sort(key=lambda p: active.get(p['monitor']) is not p)
            for p in profiles:
                visible = active.get(p['monitor']) is p
                for slot, box in zip(p['slots'], boxes[id(p)]):
                    candidates = [c for c in by_class.get(slot['class'], []) if c['address'] not in used]
                    candidates.sort(key=lambda c: (c['address'] != self.bindings.get(slot['id']),
                                                    str(c.get('stableId', '')) != slot['preferred'],
                                                    workspace_key(c['workspace']) != p['workspace'], c['address']))
                    if not candidates:
                        continue
                    c = candidates[0]
                    address = c['address']
                    self.bindings[slot['id']] = address
                    used.add(address)
                    if address in self.managed and self.managed[address]['identity'] != self.identity(c):
                        self.managed.pop(address)
                    if address not in self.managed:
                        if c.get('fullscreen') or c.get('grouped'):
                            used.remove(address)
                            continue
                        self.managed[address] = {'identity': self.identity(c), 'at': c['at'], 'size': c['size'],
                                                 'floating': c['floating'], 'pinned': c['pinned'],
                                                 'workspace': workspace_key(c['workspace'])}
                        self.journal()
                    # Per-workspace windows live on that workspace and naturally disappear.
                    # All-workspace windows are parked while an explicit override is active.
                    target_ws = p['workspace']
                    if target_ws == '*':
                        target_ws = workspace_key(next(m for m in self.monitors if m['name'] == p['monitor'])['activeWorkspace']) if visible else 'special:edge-strip'
                    pin = visible and p['workspace'] == '*'
                    target = 'address:' + address
                    moving = workspace_key(c['workspace']) != target_ws
                    if c['pinned'] and (not pin or moving):
                        self.hypr.dispatch('pin', target)
                        c['pinned'] = False
                    if moving:
                        self.hypr.dispatch('movetoworkspacesilent', target_ws+','+target)
                    if not c['floating']:
                        self.hypr.dispatch('setfloating', target)
                    if pin and not c['pinned']:
                        self.hypr.dispatch('pin', target)
                    if c.get('fullscreen'):
                        continue  # Don't fight user-requested fullscreen.
                    x, y, w, h = box
                    if c['size'] != [w, h]:
                        self.hypr.dispatch('resizewindowpixel', f'exact {w} {h},{target}')
                    if c['at'] != [x, y]:
                        self.hypr.dispatch('movewindowpixel', f'exact {x} {y},{target}')
            for address in list(self.managed):
                if address not in used:
                    self.restore(address, by_address.get(address))
            self.error = ''
            self.refresh()
        except Exception as exc:
            self.error = str(exc)
        self.publish()

    def publish(self):
        bars = {}
        for m in self.monitors:
            p = active_profile(self.config, m)
            left, right = self.reservations.get(m['name'], (0, 0))
            bars[m['name']] = {'left': left, 'right': right, 'fullBar': bool(p and p['fullBar'])}
        state = {'config': self.config, 'monitors': self.monitors, 'clients': self.clients,
                 'workspaces': self.workspaces, 'bars': bars, 'error': self.config_error or self.error, 'bindings': self.bindings}
        if state != self.last_state:
            atomic_json(RUNTIME/'state.json', state)
            self.last_state = copy.deepcopy(state)
        return state

    def cleanup(self):
        self.config['enabled'] = False
        self.reconcile()
        # Reconcile only releases connected outputs; reloads clear disconnected output rules.

    def request(self, req):
        action = req.get('action')
        if action == 'status':
            self.refresh()
            return self.publish()
        if action == 'save':
            config = validate(req['config'])
            self.refresh()
            # Reject impossible geometry before writing or moving anything.
            for p in config['profiles']:
                m = next((m for m in self.monitors if m['name'] == p['monitor']), None)
                if config['enabled'] and p['enabled'] and m:
                    geometry(m, p, self.reservations.get(m['name'], (0, 0)))
            previous = copy.deepcopy(self.config)
            if CONFIG.exists():
                atomic_json(CONFIG.with_suffix('.json.previous'), self.config)
            atomic_json(CONFIG, config)
            self.config = config
            self.reconcile()
            if self.error:
                error = self.error
                self.config = previous
                atomic_json(CONFIG, previous)
                self.reconcile()
                return {'ok': False, 'error': error + ' (previous settings restored)'}
            self.config_error = ''
            return {'ok': True}
        if action == 'reapply':
            self.reconcile()
            return {'ok': not self.error, 'error': self.error}
        raise ValueError('Unknown action')

def daemon():
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = open(RUNTIME/'lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    path = RUNTIME/'control.sock'
    path.unlink(missing_ok=True)
    server = socket.socket(socket.AF_UNIX)
    server.bind(str(path))
    os.chmod(path, 0o600)
    server.listen(4)
    stop = False
    def stopping(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    controller = Controller()
    events = None
    pending = time.monotonic()
    reload_pending = False
    event_buffer = b''
    last_signature = None
    last_poll = 0
    try:
        try:
            controller.load()
        except Exception as exc:
            controller.config_error = str(exc)
        while not stop:
            now = time.monotonic()
            if events is None:
                try:
                    events = socket.socket(socket.AF_UNIX)
                    events.connect(str(Path(os.environ['XDG_RUNTIME_DIR'])/'hypr'/os.environ['HYPRLAND_INSTANCE_SIGNATURE']/'.socket2.sock'))
                    events.setblocking(False)
                    pending = now
                except OSError:
                    if events:
                        events.close()
                    events = None
            if now-last_poll > 1:
                last_poll = now
                signature = CONFIG.stat().st_mtime_ns if CONFIG.exists() else None
                if signature != last_signature:
                    last_signature = signature
                    try:
                        controller.load()
                        pending = now
                    except Exception as exc:
                        controller.config_error = str(exc)
                        controller.publish()
            if pending is not None and now >= pending:
                controller.reconcile(reload_pending)
                reload_pending = False
                pending = None
            readers, _, _ = select.select([server] + ([events] if events else []), [], [], .15)
            if events in readers:
                chunk = events.recv(65536)
                if not chunk:
                    events.close()
                    events = None
                    event_buffer = b''
                else:
                    event_buffer += chunk
                    lines = event_buffer.split(b'\n')
                    event_buffer = lines.pop()
                    names = [line.decode(errors='replace').split('>>', 1)[0] for line in lines]
                    if 'configreloaded' in names:
                        reload_pending = True
                    if any(n in ('workspace', 'workspacev2', 'focusedmon', 'openwindow', 'closewindow',
                                 'movewindow', 'movewindowv2', 'monitoradded', 'monitorremoved',
                                 'monitoraddedv2', 'configreloaded', 'changefloatingmode', 'pin', 'fullscreen') for n in names) or b'custom>>edge-strip-layout' in lines:
                        if pending is None:
                            pending = time.monotonic() + .06
            if server in readers:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(2)
                    try:
                        buf = b''
                        while b'\n' not in buf:
                            part = conn.recv(65536)
                            if not part:
                                break
                            buf += part
                            if len(buf) > 1000000:
                                raise ValueError('Request too large')
                        response = controller.request(json.loads(buf.split(b'\n')[0]))
                    except Exception as exc:
                        response = {'ok': False, 'error': str(exc)}
                    try:
                        conn.sendall(json.dumps(response).encode()+b'\n')
                    except (BrokenPipeError, ConnectionResetError, socket.timeout):
                        pass  # A panel reload must not take down the controller.
    finally:
        controller.cleanup()
        server.close()
        path.unlink(missing_ok=True)
        if events:
            events.close()

def request(req):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(15)
        sock.connect(str(RUNTIME/'control.sock'))
        sock.sendall(json.dumps(req).encode()+b'\n')
        data = b''
        while not data.endswith(b'\n'):
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
        return json.loads(data)

def release_if_disabled():
    def enabled():
        try:
            shell = json.loads((CONFIG.parent/'shell.json').read_text())
        except (OSError, ValueError):
            return True  # Don't tear down a live strip during a partial write.
        ident = 'io.github.dfrost90.edge-strip'
        entries = shell.get('plugins', [])
        entries += [entry for section in shell.get('bar', {}).get('layout', {}).values() for entry in section]
        return any((entry if isinstance(entry, str) else entry.get('id')) == ident for entry in entries)

    if enabled():
        return
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(RUNTIME/'lock', 'w') as lock:
        # Wait briefly for Quickshell to finish terminating its owned worker.
        for _ in range(40):
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                time.sleep(.05)
        else:
            return
        if not enabled():
            controller = Controller()
            controller.cleanup()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'daemon':
        daemon()
    elif len(sys.argv) > 1 and sys.argv[1] == 'release-if-disabled':
        release_if_disabled()
    else:
        try:
            req = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {'action': 'status'}
            print(json.dumps(request(req)))
        except Exception as exc:
            print(json.dumps({'ok': False, 'error': str(exc)}))
            sys.exit(1)
