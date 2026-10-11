"""Bounded reproduction on a private Wayland socket; never uses the desktop.

Build server.c and client.cpp beside this file, then run `python3 run.py`.
This requires permission to create local Unix sockets, Qt 6, and libwayland.
"""
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time

root = Path(__file__).resolve().parent


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


for patched in (False, True):
    mode = 'patched' if patched else 'baseline'
    with tempfile.TemporaryDirectory(prefix='edge-private-wayland-') as runtime:
        env = dict(os.environ, XDG_RUNTIME_DIR=runtime,
                   WAYLAND_DISPLAY='clipboard-test', QT_QPA_PLATFORM='wayland',
                   QT_QUICK_BACKEND='software', QT_FORCE_STDERR_LOGGING='1',
                   QT_QPA_PLATFORMTHEME='', QT_IM_MODULE='',
                   EDGE_PLUGIN_DIR=str(root.parent.parent))
        env.pop('SAFE_INPUTS', None)
        env.pop('PATCHED_INPUTS', None)
        if patched:
            env['PATCHED_INPUTS'] = '1'
        with tempfile.TemporaryFile(mode='w+') as slog, tempfile.TemporaryFile(mode='w+') as clog:
            server = subprocess.Popen([str(root / 'server')], env=env,
                                      stdout=slog, stderr=slog, preexec_fn=limits)
            try:
                for _ in range(100):
                    if server.poll() is not None:
                        raise RuntimeError('Private Wayland server failed to start')
                    if Path(runtime, 'clipboard-test').exists():
                        break
                    time.sleep(.02)
                else:
                    raise RuntimeError('Private Wayland socket was not created')
                # No paste call: isolate the automatic clipboard-change path.
                subprocess.run([str(root / 'client')], env=env, stdout=clog,
                               stderr=clog, timeout=11, check=True, preexec_fn=limits)
            finally:
                server.terminate()
                server.wait(timeout=3)
            slog.seek(0)
            clog.seek(0)
            server_log, client_log = slog.read(), clog.read()
        beats = [int(line.split()[1]) for line in client_log.splitlines()
                 if line.startswith('HEARTBEAT ')]
        assert 'SELECTION 1' in server_log and 'CHANGED ' in client_log
        assert len(beats) >= 5
        gap = max(b - a for a, b in zip(beats, beats[1:]))
        requests = server_log.count('RECEIVE ')
        print(f'{mode}: clipboard requests={requests}, maximum heartbeat gap={gap}ms')
        if patched:
            assert requests == 0, server_log
            assert gap < 1000, client_log
        else:
            # Newer/fixed Qt may legitimately stop reproducing the baseline.
            print('Baseline reproduces' if requests and gap >= 3000
                  else 'Baseline did not reproduce on this Qt build')
