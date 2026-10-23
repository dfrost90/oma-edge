"""Exercise deferred save replies against an isolated daemon and fake compositor."""
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from test_model import e, monitor, profile


FAKE_DAEMON = '''
import json
import os
from pathlib import Path
import backend

class FakeHypr(backend.Hypr):
    def read(self, name):
        monitors = json.loads(Path(os.environ['FAKE_MONITORS']).read_text())
        if name == 'monitors': return monitors
        if name == 'clients' or name == 'workspaces': return []
        if name == 'layers':
            return {m['name']: {'levels': {'3': [
                {'namespace': 'omarchy-edge-reserve-left', 'w': m['reserved'][0]},
                {'namespace': 'omarchy-edge-reserve-right', 'w': m['reserved'][2]}
            ]}} for m in monitors}
        raise AssertionError(name)
    def dispatch(self, *args):
        raise AssertionError('No windows in this fixture')

backend.Hypr = FakeHypr
backend.daemon()
'''


class DaemonTests(unittest.TestCase):
    def test_deferred_save_keeps_serving_status_until_acknowledged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event_path = root/'hypr/test-session/.socket2.sock'
            event_path.parent.mkdir(parents=True)
            monitors_path = root/'monitors.json'
            monitors = [monitor(reserved=[0, 30, 0, 0])]
            e.atomic_json(monitors_path, monitors)
            env = dict(os.environ, XDG_RUNTIME_DIR=directory,
                       XDG_CONFIG_HOME=str(root/'config'),
                       HYPRLAND_INSTANCE_SIGNATURE='test-session',
                       FAKE_MONITORS=str(monitors_path))
            with socket.socket(socket.AF_UNIX) as events:
                events.bind(str(event_path))
                events.listen(1)
                events.settimeout(5)
                proc = subprocess.Popen([sys.executable, '-c', FAKE_DAEMON], env=env,
                                        cwd=Path(__file__).parents[1],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    event_conn, _ = events.accept()
                    self.addCleanup(event_conn.close)
                    control_path = root/'omarchy-edge-strip/control.sock'
                    config = {'version': 1, 'enabled': True, 'profiles': [profile(slots=[])]}
                    with socket.socket(socket.AF_UNIX) as saving:
                        saving.settimeout(5)
                        saving.connect(str(control_path))
                        saving.sendall(json.dumps({'action': 'save', 'config': config}).encode()+b'\n')
                        # Wait until the daemon has actually published the reservation.
                        deadline = time.monotonic() + 2
                        reservations = root/'omarchy-edge-strip/reservations.json'
                        while not reservations.exists() and time.monotonic() < deadline:
                            time.sleep(.01)
                        self.assertTrue(reservations.exists())
                        self.assertFalse(select.select([saving], [], [], 0)[0])
                        with socket.socket(socket.AF_UNIX) as status:
                            status.settimeout(1)
                            status.connect(str(control_path))
                            status.sendall(b'{"action":"status"}\n')
                            result = json.loads(status.makefile('rb').readline())
                            self.assertEqual(result['config'], e.validate(config))
                        # A compositor acknowledgement completes the original RPC.
                        monitors[0]['reserved'][2] = 688
                        e.atomic_json(monitors_path, monitors)
                        event_conn.sendall(b'custom>>edge-strip-layout\n')
                        self.assertEqual(json.loads(saving.makefile('rb').readline()), {'ok': True})
                finally:
                    # Release is already acknowledged when shutdown cleanup runs.
                    monitors[0]['reserved'][2] = 0
                    e.atomic_json(monitors_path, monitors)
                    proc.terminate()
                    try:
                        _, errors = proc.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.communicate()
                        raise
                self.assertEqual(proc.returncode, 0, errors.decode())


if __name__ == '__main__':
    unittest.main()
