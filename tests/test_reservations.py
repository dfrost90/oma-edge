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

    def test_publish_all_outputs_without_polling_or_sleeping(self):
        desired = {'DP-1': (0, 688), 'DP-2': (300, 0)}
        with tempfile.TemporaryDirectory() as directory, patch.object(e, 'RUNTIME', Path(directory)), \
                patch.object(e.Hypr, 'read') as read, patch.object(e.time, 'sleep') as sleep:
            e.Hypr().reserve(desired)
            data = json.loads((Path(directory)/'reservations.json').read_text())
            self.assertEqual(data['monitors'], {'DP-1': [0, 688], 'DP-2': [300, 0]})
            read.assert_not_called()
            sleep.assert_not_called()
