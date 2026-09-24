import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from test_model import e


class ReservationTests(unittest.TestCase):
    def test_only_plugin_surfaces_count_toward_our_reservation(self):
        layers = {'DP-1': {'levels': {'2': [
            {'namespace': 'omarchy-bar', 'w': 3440},
            {'namespace': 'another-side-panel', 'w': 80},
        ], '3': [
            {'namespace': 'omarchy-edge-reserve-left', 'w': 688},
        ]}}, 'DP-2': {'levels': {'3': [
            {'namespace': 'omarchy-edge-reserve-right', 'w': 400},
        ]}}}
        with patch.object(e.Hypr, 'read', return_value=layers):
            self.assertEqual(e.Hypr().reservations(), {'DP-1': (688, 0), 'DP-2': (0, 400)})

    def test_request_preserves_other_outputs_and_waits_for_surface(self):
        before = {'DP-1': (0, 0), 'DP-2': (300, 0)}
        applied = dict(before, **{'DP-1': (0, 688)})
        with tempfile.TemporaryDirectory() as directory, patch.object(e, 'RUNTIME', Path(directory)), \
                patch.object(e.Hypr, 'reservations', side_effect=[before, before, applied]), \
                patch.object(e.time, 'sleep') as sleep:
            e.Hypr().reserve('DP-1', 0, 688)
            data = json.loads((Path(directory)/'reservations.json').read_text())
            self.assertEqual(data['monitors'], {'DP-1': [0, 688], 'DP-2': [300, 0]})
            sleep.assert_called_once()

    def test_surface_timeout_restores_previous_request(self):
        before = {'DP-1': (0, 0)}
        with tempfile.TemporaryDirectory() as directory, patch.object(e, 'RUNTIME', Path(directory)), \
                patch.object(e.Hypr, 'reservations', return_value=before), \
                patch.object(e.time, 'monotonic', side_effect=[0, 3]):
            with self.assertRaisesRegex(RuntimeError, 'did not become ready'):
                e.Hypr().reserve('DP-1', 0, 688)
            data = json.loads((Path(directory)/'reservations.json').read_text())
            self.assertEqual(data['monitors'], {'DP-1': [0, 0]})
