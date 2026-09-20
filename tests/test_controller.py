import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from test_model import e, monitor, profile


class FakeHypr:
    def __init__(self):
        self.monitors = [monitor(reserved=[0,30,0,0])]
        self.clients = []
        self.actions = []
        self.fail_reserve = False

    def read(self, what):
        return copy.deepcopy({'monitors': self.monitors, 'clients': self.clients, 'workspaces': []}[what])

    def reserve(self, name, left, right):
        if self.fail_reserve:
            self.fail_reserve = False
            raise RuntimeError('reservation failed')
        self.monitors[0]['reserved'] = [left,30,right,0]

    def dispatch(self, name, value):
        self.actions.append((name,value))


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = patch.multiple(e, CONFIG=Path(self.tmp.name)/'config.json', RUNTIME=Path(self.tmp.name))
        self.paths.start()
        self.addCleanup(self.paths.stop)
        self.hypr = FakeHypr()
        self.controller = e.Controller(self.hypr)

    def test_failed_reservation_retries_without_corrupting_baseline(self):
        self.controller.config = e.validate({'version':1,'enabled':True,'profiles':[profile()]})
        self.hypr.fail_reserve = True
        self.controller.reconcile()
        self.assertEqual(self.controller.reservations['DP-1'],(0,0))
        self.assertIn('reservation failed',self.controller.error)
        self.controller.reconcile()
        self.assertEqual(self.hypr.monitors[0]['reserved'],[0,30,688,0])
        self.assertEqual(self.controller.error,'')

    def test_failed_save_rolls_back_disk_and_runtime(self):
        e.atomic_json(e.CONFIG,self.controller.config)
        before=copy.deepcopy(self.controller.config)
        self.hypr.fail_reserve=True
        result=self.controller.request({'action':'save','config':{'version':1,'enabled':True,'profiles':[profile()]}})
        self.assertFalse(result['ok'])
        self.assertEqual(self.controller.config,before)
        self.assertEqual(self.hypr.monitors[0]['reserved'],[0,30,0,0])
        self.assertEqual(__import__('json').loads(e.CONFIG.read_text()),before)

    def test_impossible_slot_geometry_rejected_before_mutation(self):
        self.hypr.monitors[0]['height']=150
        with self.assertRaises(ValueError):
            self.controller.request({'action':'save','config':{'version':1,'enabled':True,'profiles':[profile()]}})
        self.assertFalse(e.CONFIG.exists())
        self.assertEqual(self.hypr.monitors[0]['reserved'],[0,30,0,0])

    def test_reused_address_is_not_restored_to_old_window(self):
        c={'stableId':'new','pid':22,'class':'chat','pinned':False}
        self.controller.managed['0x123']={'identity':'old:21:chat'}
        self.controller.restore('0x123',c)
        self.assertEqual(self.hypr.actions,[])
        self.assertEqual(self.controller.managed,{})

    def test_restoring_tiled_window_unpins_and_returns_original_workspace(self):
        c={'stableId':'a','pid':22,'class':'chat','pinned':True}
        self.controller.managed['0x123']={'identity':'a:22:chat','workspace':'3','floating':False,'pinned':False}
        self.controller.restore('0x123',c)
        self.assertEqual(self.hypr.actions,[('pin','address:0x123'),('movetoworkspacesilent','3,address:0x123'),('settiled','address:0x123')])

if __name__=='__main__': unittest.main()
