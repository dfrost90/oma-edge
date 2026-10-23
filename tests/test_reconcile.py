import copy
import json
import unittest
from unittest.mock import patch

import test_controller as fixtures
from test_controller import FakeHypr, client
from test_model import e, monitor, profile


class DelayedHypr(FakeHypr):
    def __init__(self):
        super().__init__()
        self.requests = []

    def reserve(self, desired):
        self.requests.append(copy.deepcopy(desired))

    def acknowledge(self, names=None):
        for m in self.monitors:
            if names is None or m['name'] in names:
                left, right = self.requests[-1][m['name']]
                m['reserved'] = [left, 30, right, 0]


class ReconcileTests(unittest.TestCase):
    setUp = fixtures.ControllerTests.setUp

    def test_no_change_uses_one_snapshot_and_no_disk_writes(self):
        self.controller.config = e.validate({'version': 1, 'enabled': True,
            'profiles': [profile(slots=[{'id': 'chat', 'class': 'chat', 'weight': 1}])]})
        self.hypr.clients = [client('chat', 1)]
        self.controller.reconcile()
        self.hypr.clients[0].update(at=[2764, 42], size=[664, 1386])
        self.controller.reconcile()
        with patch.object(self.hypr, 'read', wraps=self.hypr.read) as read, \
                patch.object(self.hypr, 'reservations', wraps=self.hypr.reservations) as layers, \
                patch.object(self.hypr, 'dispatch') as dispatch, \
                patch.object(e, 'atomic_json', wraps=e.atomic_json) as write:
            self.controller.reconcile()
            self.assertEqual([c.args[0] for c in read.call_args_list], ['monitors', 'clients', 'workspaces'])
            layers.assert_called_once()
            dispatch.assert_not_called()
            write.assert_not_called()

    def test_journal_is_written_before_first_window_mutation(self):
        self.controller.config = e.validate({'version': 1, 'enabled': True,
            'profiles': [profile(slots=[{'id': 'chat', 'class': 'chat', 'weight': 1}])]})
        self.hypr.clients = [client('chat', 1)]
        def check_journal(*_):
            saved = json.loads(self.controller.journal_path.read_text())
            self.assertEqual(saved['managed']['0x1']['workspace'], '1')
            self.assertEqual(saved['managed']['0x1']['size'], [100, 100])
        with patch.object(self.hypr, 'dispatch', side_effect=check_journal) as dispatch:
            self.controller.reconcile()
        self.assertGreater(dispatch.call_count, 0)


class AsyncReservationTests(unittest.TestCase):
    def setUp(self):
        fixtures.ControllerTests.setUp(self)
        self.hypr = DelayedHypr()
        self.controller = e.Controller(self.hypr)
        self.config = e.validate({'version': 1, 'enabled': True,
            'profiles': [profile(slots=[{'id': 'chat', 'class': 'chat', 'weight': 1}])]})
        self.hypr.clients = [client('chat', 1)]

    def test_save_waits_for_ack_and_status_remains_available(self):
        with patch.object(e.time, 'monotonic', return_value=10), patch.object(e.time, 'sleep') as sleep:
            self.assertIsNone(self.controller.request({'action': 'save', 'config': self.config}))
            self.assertTrue(self.controller.waiting)
            self.assertEqual(self.hypr.actions, [])
            self.assertIn('monitors', self.controller.request({'action': 'status'}))
            busy = self.controller.request({'action': 'save', 'config': self.config})
            self.assertFalse(busy['ok'])
            sleep.assert_not_called()
        self.hypr.acknowledge()
        with patch.object(e.time, 'monotonic', return_value=10.1):
            self.controller.reconcile()
        self.assertEqual(self.controller.save_result, {'ok': True})
        self.assertIsNone(self.controller.pending_save)
        self.assertEqual(len(self.hypr.requests), 1)
        self.assertIn(('movewindowpixel', 'exact 2764 42,address:0x1'), self.hypr.actions)

    def test_timeout_restores_config_without_moving_windows(self):
        previous = copy.deepcopy(self.controller.config)
        with patch.object(e.time, 'monotonic', return_value=10):
            self.controller.request({'action': 'save', 'config': self.config})
        with patch.object(e.time, 'monotonic', return_value=12.1):
            self.controller.reconcile()
        self.assertFalse(self.controller.save_result['ok'])
        self.assertIn('previous settings restored', self.controller.save_result['error'])
        self.assertEqual(json.loads(e.CONFIG.read_text()), previous)
        self.assertEqual(self.hypr.requests[-1], {'DP-1': (0, 0)})
        self.assertEqual(self.hypr.actions, [])

    def test_partial_multimonitor_ack_waits_for_rollback(self):
        self.hypr.monitors.append(monitor(name='DP-2', x=3440, reserved=[0, 30, 0, 0]))
        self.config['profiles'].append(profile(monitor='DP-2', slots=[]))
        with patch.object(e.time, 'monotonic', return_value=10):
            self.controller.request({'action': 'save', 'config': self.config})
        self.assertEqual(len(self.hypr.requests), 1)
        self.assertEqual(set(self.hypr.requests[0]), {'DP-1', 'DP-2'})
        self.hypr.acknowledge(['DP-1'])
        with patch.object(e.time, 'monotonic', return_value=12.1):
            self.controller.reconcile()
        self.assertIsNone(self.controller.save_result)
        self.assertTrue(self.controller.waiting)
        self.hypr.acknowledge()
        with patch.object(e.time, 'monotonic', return_value=12.2):
            self.controller.reconcile()
        self.assertFalse(self.controller.save_result['ok'])
        self.assertEqual(self.controller.reservations, {'DP-1': (0, 0), 'DP-2': (0, 0)})
        self.assertEqual(self.hypr.actions, [])

    def test_workspace_switch_cancels_unacknowledged_request(self):
        self.controller.config = self.config
        with patch.object(e.time, 'monotonic', return_value=10):
            self.controller.reconcile()
        self.hypr.monitors[0]['activeWorkspace'] = {'id': 2, 'name': '2'}
        with patch.object(e.time, 'monotonic', return_value=10.1):
            self.controller.reconcile()
        self.assertEqual(self.hypr.requests[-1], {'DP-1': (0, 0)})
        self.assertFalse(self.controller.waiting)

    def test_polling_does_not_extend_ack_deadline(self):
        self.controller.config = self.config
        for now in (10, 10.1, 11, 11.9, 12.1):
            with patch.object(e.time, 'monotonic', return_value=now):
                self.controller.reconcile()
        self.assertIn('did not become ready', self.controller.error)
        self.assertEqual(len(self.hypr.requests), 2)  # Initial request, then rollback.
        self.assertEqual(self.controller.settle_at, 14.1)


if __name__ == '__main__':
    unittest.main()
