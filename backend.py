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
        if type(p.get('enabled')) is not bool:
            raise ValueError('Expected enabled flag')
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
                                'weight': weight, 'preferred': str(s.get('preferred', ''))[:100],
                                'windowTitle': str(s.get('windowTitle', ''))[:4096]})
        result['profiles'].append({'monitor': monitor, 'workspace': workspace, 'enabled': p['enabled'],
                                   'width': width, 'side': p['side'], 'slots': clean_slots})
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

def geometry(m, p, current=(0, 0), minimums=None, minimum_width=0):
    w, h = logical_size(m)
    strip = max(round(w * p['width'] / 100), minimum_width + 24 if minimum_width else 0)
    left, top, right, bottom = m.get('reserved', [0, 0, 0, 0])
    left, right = max(0, left-current[0]), max(0, right-current[1])
    if strip > w-left-right:
        raise ValueError('App minimum width does not fit this monitor. Use a wider monitor or reduce app scaling.')
    x = m['x'] + (left if p['side'] == 'left' else w-right-strip)
    y = m['y'] + top + 12
    available = h-top-bottom-24 - max(0, len(p['slots'])-1)*14
    if available < len(p['slots'])*100 or strip < 100:
        raise ValueError('Not enough screen space for this many slots')
    floors = minimums or [0] * len(p['slots'])
    if sum(floors) > available:
        raise ValueError('App minimum heights do not fit this strip. Remove an app or use a taller monitor.')
    # Weighted water-filling: fix apps at their minimum, then divide the rest.
    heights = [0] * len(p['slots'])
    remaining = set(range(len(heights)))
    budget = available
    while remaining:
        total = sum(p['slots'][i]['weight'] for i in remaining)
        constrained = [i for i in remaining if budget * p['slots'][i]['weight'] / total < floors[i]]
        if not constrained:
            accumulated = 0
            consumed = 0
            for i in sorted(remaining):
                accumulated += p['slots'][i]['weight']
                end = round(budget * accumulated / total)
                heights[i] = end - consumed
                consumed = end
            break
        for i in constrained:
            heights[i] = floors[i]
            budget -= floors[i]
            remaining.remove(i)
    boxes = []
    for height in heights:
        boxes.append((x+12, y, strip-24, height))
        y += height + 14
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

    def reserve(self, desired):
        """Publish all outputs together; the controller observes acknowledgements."""
        atomic_json(RUNTIME/'reservations.json', {
            'session': os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', ''),
            'monitors': desired,
        })

    def reservations(self):
        result = {}
        for name, output in self.read('layers').items():
            widths = [0, 0]
            for group in output.get('levels', {}).values():
                for layer in group:
                    namespace = layer.get('namespace')
                    if namespace in ('omarchy-edge-reserve-left', 'omarchy-edge-reserve-right'):
                        widths[namespace.endswith('right')] += int(layer['w'])
            result[name] = tuple(widths)
        return result

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
        self.saved_bindings = {}
        self.minimum_heights = {}
        self.minimum_widths = {}
        self.size_requests = {}
        self.settle_at = None
        self.error = ''
        self.config_error = ''
        self.last_state = None
        self.last_journal = None
        self.pending_reservation = None
        self.pending_save = None
        self.save_result = None
        self.waiting = False
        self.mutations = 0
        self.monitors = []
        self.clients = []
        self.workspaces = []
        self.journal_path = RUNTIME/'journal.json'
        if self.journal_path.exists():
            saved = json.loads(self.journal_path.read_text())
            if saved.get('session') == os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
                self.managed = saved.get('managed', {})
                self.saved_bindings = saved.get('slot_bindings', {})
                self.reservations = {k: tuple(v) for k, v in saved.get('reservations', {}).items()}

    def load(self):
        config = validate(json.loads(CONFIG.read_text())) if CONFIG.exists() else copy.deepcopy(DEFAULT)
        changed = config != self.config
        if changed:
            self.set_config(config)
        self.config_error = ''
        return changed

    @staticmethod
    def slot_key(profile, slot):
        # Selection-based fallback preserves bindings from older panels that
        # regenerated slot IDs. Stable IDs alone must not retain a replaced app.
        return json.dumps([profile['monitor'], profile['workspace'], slot['class'],
                           slot['preferred'], slot.get('windowTitle', '')])

    def binding_selections(self):
        return {self.slot_key(p, s): self.bindings[s['id']]
                for p in self.config['profiles'] for s in p['slots']
                if s['id'] in self.bindings}

    def set_config(self, config):
        previous = {**self.saved_bindings, **self.binding_selections()}
        self.saved_bindings = {}
        self.bindings = {s['id']: previous[self.slot_key(p, s)]
                         for p in config['profiles'] for s in p['slots']
                         if self.slot_key(p, s) in previous}
        self.config = config

    def journal(self, reservations=None):
        data = {'session': os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'),
                'managed': self.managed,
                'reservations': self.reservations if reservations is None else reservations,
                'slot_bindings': self.binding_selections()}
        if data != self.last_journal:
            atomic_json(self.journal_path, data)
            self.last_journal = copy.deepcopy(data)

    def dispatch(self, name, value):
        self.hypr.dispatch(name, value)
        self.mutations += 1

    def identity(self, c):
        return str(c.get('stableId', '')) + ':' + str(c['pid']) + ':' + c['class']

    def slot_candidates(self, slot, candidates, workspace):
        # An explicit selection beats a stale binding after slots are reordered
        # or replaced (the panel reuses positional slot IDs on save).
        preferred = [c for c in candidates if slot['preferred'] and
                     str(c.get('stableId', '')) == slot['preferred']]
        bound = [c for c in candidates if c['address'] == self.bindings.get(slot['id']) and
                 self.managed.get(c['address'], {}).get('identity') == self.identity(c)]
        terminal = slot['class'].lower() in {
            'kitty', 'alacritty', 'foot', 'footclient', 'ghostty',
            'com.mitchellh.ghostty', 'wezterm', 'org.wezfurlong.wezterm',
            'org.gnome.terminal', 'gnome-terminal', 'konsole', 'xterm', 'urxvt'}
        if terminal:
            if preferred:
                return preferred
            if bound:
                return bound
            # A closed terminal must not hand its slot to an unrelated shell.
            title = slot.get('windowTitle', '')
            matching = [c for c in candidates if title and c.get('title') == title]
            return matching if len(matching) == 1 else []
        return sorted(candidates, key=lambda c: (
            c not in preferred, c not in bound,
            workspace_key(c['workspace']) != workspace, c['address']))

    def restore(self, address, c):
        original = self.managed.get(address)
        if not original:
            return
        if c and self.identity(c) == original['identity']:
            target = 'address:' + address
            if c['pinned']:
                self.dispatch('pin', target)
            self.dispatch('movetoworkspacesilent', original['workspace']+','+target)
            if original['floating']:
                self.dispatch('setfloating', target)
                self.dispatch('resizewindowpixel', f"exact {original['size'][0]} {original['size'][1]},{target}")
                self.dispatch('movewindowpixel', f"exact {original['at'][0]} {original['at'][1]},{target}")
                if original['pinned']:
                    self.dispatch('pin', target)
            else:
                self.dispatch('settiled', target)
        self.managed.pop(address, None)
        self.journal()

    def refresh(self):
        self.monitors = self.hypr.read('monitors')
        self.clients = self.hypr.read('clients')
        self.workspaces = self.hypr.read('workspaces')
        self.reservations = self.hypr.reservations()

    def profile_minimum_width(self, profile):
        return max((self.minimum_widths.get((address, self.identity(self.by_address[address])), 0)
                    for slot in profile['slots']
                    if (address := self.bindings.get(slot['id'])) in self.by_address), default=0)

    def index_snapshot(self):
        self.by_address = {c['address']: c for c in self.clients}
        self.by_class = {}
        for client in self.clients:
            if client['mapped'] and (client['address'] in self.managed or
                    not (client.get('fullscreen') or client.get('grouped'))):
                self.by_class.setdefault(client['class'], []).append(client)
        self.by_workspace = {workspace_key(w): w for w in self.workspaces}

    def update_constraints(self, now):
        def alive(key):
            client = self.by_address.get(key[0])
            return client and self.identity(client) == key[1]
        self.minimum_widths = {key: width for key, width in self.minimum_widths.items() if alive(key)}
        self.minimum_heights = {key: height for key, height in self.minimum_heights.items() if alive(key)}
        self.size_requests = {key: value for key, value in self.size_requests.items() if alive(key)}
        # Infer constraints only from a recent resize, not a window's initial size.
        for (address, identity, requested_width), (_, requested_at) in self.size_requests.items():
            client = self.by_address[address]
            if (not client.get('fullscreen') and .12 <= now - requested_at <= 2
                    and client['size'][0] > requested_width + 1):
                key = (address, identity)
                self.minimum_widths[key] = max(self.minimum_widths.get(key, 0), client['size'][0])

    def plan_profiles(self):
        active = {m['name']: active_profile(self.config, m) for m in self.monitors}
        contexts, desired = {}, {}
        for monitor in self.monitors:
            name = monitor['name']
            profile = active[name]
            current = self.reservations.get(name, (0, 0))
            width = geometry(monitor, profile, current,
                             minimum_width=self.profile_minimum_width(profile))[0] if profile else 0
            desired[name] = (width, 0) if profile and profile['side'] == 'left' else (0, width)
            for p in self.config['profiles']:
                if not (self.config['enabled'] and p['enabled'] and p['monitor'] == name):
                    continue
                workspace = self.by_workspace.get(p['workspace'])
                # Do not pull a workspace back from another display.
                if workspace and workspace.get('monitor') != name:
                    continue
                contexts[id(p)] = (monitor, current)
        profiles = [p for p in self.config['profiles'] if id(p) in contexts]
        profiles.sort(key=lambda p: active.get(p['monitor']) is not p)
        return active, contexts, profiles, desired

    def ensure_reservations(self, desired, now):
        pending = self.pending_reservation
        if desired == self.reservations and (pending is None or pending['desired'] == desired):
            self.pending_reservation = None
            return True
        if pending is None or pending['desired'] != desired:
            before = dict(self.reservations)
            self.journal(reservations=desired)  # Recovery record precedes mutation.
            try:
                self.hypr.reserve(desired)
            except Exception:
                self.journal()
                self.settle_at = now + 2
                raise
            self.pending_reservation = {'desired': desired, 'before': before, 'deadline': now + 2}
            self.mutations += 1
            # One immediate observation also handles already-acknowledged surfaces.
            self.reservations = self.hypr.reservations()
            if self.reservations == desired:
                self.pending_reservation = None
                return True
        elif now >= pending['deadline']:
            self.pending_reservation = None
            self.hypr.reserve(pending['before'])
            self.settle_at = now + 2
            raise RuntimeError('Oma Edge reservation surface did not become ready; retrying automatically')
        self.settle_at = now + .05
        return False

    def match_slots(self, profile, used):
        matched = []
        for slot in profile['slots']:
            candidates = [c for c in self.by_class.get(slot['class'], []) if c['address'] not in used]
            candidates = self.slot_candidates(slot, candidates, profile['workspace'])
            if not candidates:
                continue
            client = candidates[0]
            address = client['address']
            known = self.managed.get(address, {}).get('identity') == self.identity(client)
            if not known and (client.get('fullscreen') or client.get('grouped')):
                continue
            self.bindings[slot['id']] = address
            used.add(address)
            matched.append((slot, client))
        return matched

    def plan_geometry(self, profile, matched, monitor, current, now):
        occupied = dict(profile, slots=[slot for slot, _ in matched])
        minimum_width = self.profile_minimum_width(profile)
        target_width = geometry(monitor, occupied, current, minimum_width=minimum_width)[0] - 24
        keys = [(c['address'], self.identity(c), target_width) for _, c in matched]
        for key, (_, client) in zip(keys, matched):
            request = self.size_requests.get(key)
            if request and .12 <= now - request[1] <= 2 and not client.get('fullscreen'):
                if client['size'][1] > request[0] + 1:
                    self.minimum_heights[key] = client['size'][1]
        floors = [self.minimum_heights.get(key, 0) for key in keys]
        return geometry(monitor, occupied, current, floors, minimum_width)[1]

    def apply_window(self, profile, client, box, monitor, visible):
        address = client['address']
        identity = self.identity(client)
        if self.managed.get(address, {}).get('identity') != identity:
            self.managed[address] = {'identity': identity, 'at': client['at'], 'size': client['size'],
                                     'floating': client['floating'], 'pinned': client['pinned'],
                                     'workspace': workspace_key(client['workspace'])}
            self.journal()
        target_ws = profile['workspace']
        if target_ws == '*':
            target_ws = workspace_key(monitor['activeWorkspace']) if visible else 'special:edge-strip'
        pin = visible and profile['workspace'] == '*'
        target = 'address:' + address
        moving = workspace_key(client['workspace']) != target_ws
        if client['pinned'] and (not pin or moving):
            self.dispatch('pin', target)
            client['pinned'] = False
        if moving:
            self.dispatch('movetoworkspacesilent', target_ws+','+target)
        if not client['floating']:
            self.dispatch('setfloating', target)
        if pin and not client['pinned']:
            self.dispatch('pin', target)
        if client.get('fullscreen'):
            return  # Don't fight user-requested fullscreen.
        x, y, width, height = box
        if client['size'] != [width, height]:
            key = (address, identity, width)
            previous = self.size_requests.get(key)
            if previous is None or previous[0] != height:
                self.size_requests[key] = (height, time.monotonic())
                self.settle_at = time.monotonic() + .2
            self.dispatch('resizewindowpixel', f'exact {width} {height},{target}')
        if client['at'] != [x, y]:
            self.dispatch('movewindowpixel', f'exact {x} {y},{target}')

    def release_unused(self, used):
        self.size_requests = {key: value for key, value in self.size_requests.items() if key[0] in used}
        self.minimum_heights = {key: value for key, value in self.minimum_heights.items() if key[0] in used}
        for address in list(self.managed):
            if address not in used:
                self.restore(address, self.by_address.get(address))
        self.bindings = {key: address for key, address in self.bindings.items() if address in used}

    def reconcile(self):
        self.waiting = False
        before = self.mutations
        try:
            self.refresh()
            self.index_snapshot()
            now = time.monotonic()
            if self.settle_at is not None and now >= self.settle_at:
                self.settle_at = None
            self.update_constraints(now)
            active, contexts, profiles, desired = self.plan_profiles()
            if not self.ensure_reservations(desired, now):
                self.waiting = True
            else:
                used = set()
                for profile in profiles:
                    matched = self.match_slots(profile, used)
                    monitor, current = contexts[id(profile)]
                    boxes = self.plan_geometry(profile, matched, monitor, current, now)
                    for (_, client), box in zip(matched, boxes):
                        self.apply_window(profile, client, box, monitor, active[profile['monitor']] is profile)
                self.release_unused(used)
                self.journal()
                self.error = ''
                if self.mutations != before:
                    self.refresh()
        except Exception as exc:
            self.error = str(exc)
        if not self.waiting:
            self.finish_save()
        self.publish()

    def finish_save(self):
        transaction = self.pending_save
        if transaction is None:
            return
        if self.error and 'failure' not in transaction:
            transaction['failure'] = self.error
            self.config = transaction['config']
            self.bindings = transaction['bindings']
            atomic_json(CONFIG, self.config)
            self.reconcile()
            return
        if 'failure' in transaction:
            recovery = ('; recovery failed: ' + self.error) if self.error else ' (previous settings restored)'
            self.save_result = {'ok': False, 'error': transaction['failure'] + recovery}
        else:
            self.config_error = ''
            self.save_result = {'ok': True}
        self.pending_save = None

    def publish(self):
        bars = {}
        for m in self.monitors:
            left, right = self.reservations.get(m['name'], (0, 0))
            bars[m['name']] = {'left': left, 'right': right}
        state = {'config': self.config, 'monitors': self.monitors, 'clients': self.clients,
                 'workspaces': self.workspaces, 'bars': bars, 'error': self.config_error or self.error, 'bindings': self.bindings}
        if state != self.last_state:
            atomic_json(RUNTIME/'state.json', state)
            self.last_state = copy.deepcopy(state)
        return state

    def cleanup(self):
        if self.pending_save is not None:
            self.config = self.pending_save['config']
            atomic_json(CONFIG, self.config)
        self.pending_save = None
        self.config['enabled'] = False
        self.reconcile()
        # Shutdown has no event loop left; allow bounded reservation release.
        deadline = time.monotonic() + 2.5
        while self.waiting and time.monotonic() < deadline:
            time.sleep(.05)
            self.reconcile()

    def request(self, req):
        action = req.get('action')
        if action == 'status':
            self.refresh()
            return self.publish()
        if action == 'save':
            if self.pending_save is not None:
                return {'ok': False, 'error': 'Another configuration is still being applied'}
            config = validate(req['config'])
            self.refresh()
            # Reject impossible geometry before writing or moving anything.
            for p in config['profiles']:
                m = next((m for m in self.monitors if m['name'] == p['monitor']), None)
                if config['enabled'] and p['enabled'] and m:
                    geometry(m, p, self.reservations.get(m['name'], (0, 0)))
            previous = copy.deepcopy(self.config)
            previous_bindings = dict(self.bindings)
            if CONFIG.exists():
                atomic_json(CONFIG.with_suffix('.json.previous'), self.config)
            atomic_json(CONFIG, config)
            self.pending_save = {'config': previous, 'bindings': previous_bindings}
            self.save_result = None
            self.set_config(config)
            self.reconcile()
            # None defers the RPC reply until surface acknowledgement or rollback.
            return self.save_result
        if action == 'reapply':
            self.reconcile()
            return {'ok': not self.error, 'error': self.error, 'pending': self.waiting}
        raise ValueError('Unknown action')

def reply(conn, response):
    with conn:
        try:
            conn.sendall(json.dumps(response).encode()+b'\n')
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass  # A panel reload must not take down the controller.


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
    deferred = None
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
            if now-last_poll > 1 and controller.pending_save is None:
                last_poll = now
                signature = CONFIG.stat().st_mtime_ns if CONFIG.exists() else None
                if signature != last_signature:
                    last_signature = signature
                    try:
                        had_error = bool(controller.config_error)
                        if controller.load():
                            pending = now
                        elif had_error:
                            controller.publish()
                    except Exception as exc:
                        controller.config_error = str(exc)
                        controller.publish()
            if pending is not None and now >= pending:
                controller.reconcile()
                pending = controller.settle_at
            if pending is None and controller.settle_at is not None:
                pending = controller.settle_at
            if deferred is not None and controller.save_result is not None:
                reply(deferred, controller.save_result)
                deferred = None
            timeout = min(.15, max(0, pending - time.monotonic())) if pending is not None else .15
            readers, _, _ = select.select([server] + ([events] if events else []), [], [], timeout)
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
                    if any(n in ('workspace', 'workspacev2', 'focusedmon', 'openwindow', 'closewindow',
                                 'movewindow', 'movewindowv2', 'monitoradded', 'monitorremoved',
                                 'monitoraddedv2', 'configreloaded', 'changefloatingmode', 'pin', 'fullscreen') for n in names) or b'custom>>edge-strip-layout' in lines:
                        event_at = time.monotonic() + .06
                        pending = min(pending, event_at) if pending is not None else event_at
            if server in readers:
                conn, _ = server.accept()
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
                if response is None:
                    deferred = conn
                else:
                    reply(conn, response)
                if controller.settle_at is not None:
                    pending = min(pending, controller.settle_at) if pending is not None else controller.settle_at
    finally:
        if deferred is not None:
            reply(deferred, {'ok': False, 'error': 'Service stopped before apply completed'})
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
            if len(sys.argv) > 1 and sys.argv[1] == 'request-stdin':
                payload = sys.stdin.buffer.readline(1000001)
                if len(payload) > 1000000:
                    raise ValueError('Request too large')
                try:
                    req = json.loads(payload)
                except (ValueError, UnicodeError):
                    raise ValueError('Invalid request JSON') from None
            else:
                req = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {'action': 'status'}
            print(json.dumps(request(req)))
        except Exception as exc:
            print(json.dumps({'ok': False, 'error': str(exc)}))
            sys.exit(1)
