import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('edge', Path(__file__).parents[1]/'backend.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)

def profile(**kw):
    p = {'monitor': 'DP-1', 'workspace': '1', 'enabled': True, 'width': 20, 'side': 'right', 'fullBar': True,
         'slots': [{'id': 'a', 'class': 'app', 'weight': 1}, {'id': 'b', 'class': 'chat', 'weight': 1}]}
    p.update(kw)
    return p

def monitor(**kw):
    m = {'name': 'DP-1', 'width': 3440, 'height': 1440, 'scale': 1, 'transform': 0,
         'x': 0, 'y': 0, 'reserved': [0, 30, 688, 0], 'activeWorkspace': {'id': 1, 'name': '1'}}
    m.update(kw)
    return m

class ModelTests(unittest.TestCase):
    def test_workspace_groups_round_trip_and_select(self):
        first = profile(group='group_demo')
        second = profile(workspace='3', group='group_demo')
        for slot in second['slots']:
            slot['id'] += '_3'
        cfg = e.validate({'version': 1, 'enabled': True, 'profiles': [first, second]})
        self.assertEqual([p['group'] for p in cfg['profiles']], ['group_demo', 'group_demo'])
        self.assertEqual(e.active_profile(cfg, monitor(activeWorkspace={'id': 3, 'name': '3'}))['workspace'], '3')

    def test_reject_inconsistent_group_before_ui_can_merge_it(self):
        first = profile(group='same')
        second = profile(group='same', workspace='2', width=30, slots=[])
        with self.assertRaisesRegex(ValueError, 'Grouped workspaces'):
            e.validate({'version':1, 'enabled':True, 'profiles':[first, second]})

    def test_reject_non_object_profiles_and_slots(self):
        for profiles in ([None], [profile(slots=[None])]):
            with self.assertRaises(ValueError):
                e.validate({'version':1, 'enabled':True, 'profiles':profiles})

    def test_app_minimum_height_preserves_gaps_and_total(self):
        p = profile(slots=[{'weight':1}, {'weight':1}, {'weight':1}])
        _, boxes = e.geometry(monitor(), p, (0,688), [0,504,0])
        self.assertEqual([b[3] for b in boxes], [427,504,427])
        self.assertEqual(boxes[1][1] - (boxes[0][1] + boxes[0][3]), 14)
        self.assertEqual(boxes[2][1] - (boxes[1][1] + boxes[1][3]), 14)
        self.assertEqual(boxes[-1][1] + boxes[-1][3], 1428)

    def test_impossible_app_minimums_fail(self):
        with self.assertRaisesRegex(ValueError, 'minimum heights'):
            e.geometry(monitor(), profile(), (0,688), [900,900])

    def test_original_geometry(self):
        strip, boxes = e.geometry(monitor(), profile(), (0, 688))
        self.assertEqual(strip, 688)
        self.assertEqual(boxes, [(2764, 42, 664, 686), (2764, 742, 664, 686)])

    def test_existing_reservation_preserved(self):
        m = monitor(reserved=[80, 40, 700, 20])
        _, boxes = e.geometry(m, profile(), (0, 688))
        self.assertEqual(boxes[0][0], 2752)
        self.assertEqual(boxes[-1][1]+boxes[-1][3], 1408)

    def test_scaling_rotation_and_negative_position(self):
        m = monitor(width=2160, height=3840, scale=1.5, transform=1, x=-2560, y=100, reserved=[0,30,0,0])
        width, boxes = e.geometry(m, profile(side='left'))
        self.assertEqual(width, 512)
        self.assertEqual(boxes[0][:2], (-2548,142))
        self.assertEqual(boxes[-1][1]+boxes[-1][3], 1528)

    def test_weighted_slots_fit(self):
        p = profile(slots=[{'weight':1}, {'weight':3}, {'weight':2}])
        _, boxes = e.geometry(monitor(), p, (0,688))
        self.assertEqual(boxes[-1][1]+boxes[-1][3],1428)
        self.assertEqual(boxes[1][1]-(boxes[0][1]+boxes[0][3]),14)
        self.assertAlmostEqual(boxes[1][3]/boxes[0][3],3,delta=.02)

    def test_workspace_override_and_release(self):
        cfg = {'enabled':True, 'profiles':[profile()]}
        m = monitor()
        self.assertIsNotNone(e.active_profile(cfg,m))
        m['activeWorkspace']={'id':2,'name':'2'}
        self.assertIsNone(e.active_profile(cfg,m))
        cfg['profiles'].append(profile(workspace='*'))
        self.assertIsNotNone(e.active_profile(cfg,m))
        cfg['profiles'].append(profile(workspace='2',enabled=False))
        self.assertIsNone(e.active_profile(cfg,m))

    def test_named_workspaces(self):
        m=monitor(activeWorkspace={'id':-1337,'name':'work'})
        cfg={'enabled':True,'profiles':[profile(workspace='name:work')]}
        self.assertIsNotNone(e.active_profile(cfg,m))

    def test_reject_ambiguous_profiles_and_unsafe_workspaces(self):
        for ps in ([profile(),profile()], [profile(workspace='1,address:foo')], [profile(width=float('nan'))]):
            with self.assertRaises(ValueError): e.validate({'version':1,'enabled':True,'profiles':ps})

    def test_lua_string_is_data(self):
        self.assertEqual(e.lua_string('"\n'), '"\\034\\010"')
        self.assertNotIn('os.execute',e.lua_string('";os.execute("evil")'))

if __name__ == '__main__': unittest.main()
