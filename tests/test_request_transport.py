import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

BACKEND = Path(__file__).parents[1] / 'backend.py'


class RequestTransportTests(unittest.TestCase):
    def test_private_payload_round_trips_without_argv_or_eof(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / 'omarchy-edge-strip'
            runtime.mkdir(mode=0o700)
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(str(runtime / 'control.sock'))
                server.listen(1)
                server.settimeout(5)
                payload = {'action': 'save', 'config': {'title': 'Private document — Київ\nSecond line'}}
                proc = subprocess.Popen([sys.executable, str(BACKEND), 'request-stdin'],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env=dict(os.environ, XDG_RUNTIME_DIR=directory))
                try:
                    proc.stdin.write(json.dumps(payload).encode() + b'\n')
                    proc.stdin.flush()  # Keep stdin open, as Quickshell does.
                    with server.accept()[0] as connection:
                        connection.settimeout(5)
                        data = b''
                        while not data.endswith(b'\n'):
                            data += connection.recv(65536)
                        self.assertEqual(json.loads(data), payload)
                        argv = Path(f'/proc/{proc.pid}/cmdline').read_bytes().split(b'\0')
                        self.assertEqual(argv[:-1], [os.fsencode(sys.executable), os.fsencode(BACKEND), b'request-stdin'])
                        connection.sendall(b'{"ok":true}\n')
                    proc.wait(timeout=5)
                    self.assertEqual(proc.returncode, 0)
                    self.assertEqual(json.loads(proc.stdout.read()), {'ok': True})
                    self.assertEqual(proc.stderr.read(), b'')
                finally:
                    if proc.poll() is None:
                        proc.kill()
                    proc.wait()
                    for stream in (proc.stdin, proc.stdout, proc.stderr):
                        stream.close()

    def test_invalid_and_oversized_requests_fail_without_echoing_payload(self):
        for payload in (b'PRIVATE malformed\n', b'', b'x' * 1000001):
            result = subprocess.run([sys.executable, str(BACKEND), 'request-stdin'],
                                    input=payload, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)['ok'])
            self.assertNotIn(b'PRIVATE', result.stdout + result.stderr)
