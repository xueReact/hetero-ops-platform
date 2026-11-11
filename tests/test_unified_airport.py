"""Exercise project/resource/work-order boundaries without a running simulator."""
import importlib.util
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from platform_app.services import airport_service as airport, project_service as projects, task_service
from platform_app.models.task import Task


class UnifiedAirportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        for target, value in [('platform_app.services.project_service.FILE', folder/'projects.json'),
                              ('platform_app.services.project_service.DATA_DIR', folder),
                              ('platform_app.services.airport_service.JOBS', folder/'jobs.json'),
                              ('platform_app.services.task_service.TASKS_FILE', folder/'tasks.json')]:
            mock = patch(target, value); mock.start(); self.addCleanup(mock.stop)
        spec = importlib.util.spec_from_file_location('fleet_for_tests', Path(__file__).resolve().parents[1]/'simulations/airport-upgrade/fleet_config.py')
        self.fleet = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.fleet)

    def test_shared_registry_and_scene_identity(self):
        canonical = {r['id']:r for r in projects.registry()}
        self.assertEqual(Counter(r['type'] for r in canonical.values()), {'person':7,'robot':7,'dog':7,'drone':7})
        self.assertEqual(len(self.fleet.DEVICES),21)
        self.assertEqual(len(self.fleet.PERSONNEL),7)
        for d in self.fleet.DEVICES.values():
            self.assertEqual(d['name'], canonical[d['platform_id']]['name'])
        self.assertEqual(set(c['id'] for c in self.fleet.CELLS),set('ABCDEFG'))

    def test_offline_resources_never_invent_telemetry(self):
        rows=airport.resources({'devices':[]})
        self.assertEqual(len(rows),28)
        self.assertFalse(any(r['online'] for r in rows))
        self.assertTrue(all(r['position'] is None and r['power_percent'] is None for r in rows))

    def test_profile_edit_reaches_same_id(self):
        projects.update_resource({'id':'DOG-01','name':'机场一号机器狗'})
        self.assertEqual(next(r for r in airport.resources({'devices':[]}) if r['id']=='DOG-01')['name'],'机场一号机器狗')
        self.assertEqual(len(projects.registry()),28)
        with self.assertRaises(ValueError):projects.update_resource({'id':'DOG-08','name':'unsupported'})

    def test_project_persistence_and_running_switch_guard(self):
        result=projects.update_project({'name':'机场二期','kind':'airport','location':'杭州'})
        new=result['projects'][-1]
        self.assertEqual(projects.catalog()['projects'][-1],new)
        self.assertIsNone(new['runtime'])
        with patch.object(airport,'runtime_status',return_value={'mission':{'status':'running'}}):
            with self.assertRaises(ValueError):projects.update_project({'active':'dispatch-pool'})
        self.assertEqual(projects.active_project()['id'],'airport-t1')
        with patch.object(airport,'runtime_status',return_value={}):projects.update_project({'active':new['id']})
        with self.assertRaises(ValueError):Task.from_payload({'station':new['id'],'type':'robot','name':'not configured'})

    def test_task_validation(self):
        base={'station':'airport-t1','type':'joint','name':'联合巡检'}
        for cells in (['A','A'],['Z'],'A',[{}]):
            with self.subTest(cells=cells),self.assertRaises(ValueError):
                Task.from_payload(dict(base,requirements={'cells':cells}))
        with self.assertRaises(ValueError):Task.from_payload(dict(base,type='drone'))
        t=Task.from_payload(dict(base,requirements={'cells':['B','G']})).to_api()
        self.assertEqual(t['requirements']['cells'],['B','G'])

    def test_start_result_correlation_and_feedback(self):
        task=task_service.create_task({'station':'airport-t1','type':'joint','name':'B/G 工单','requirements':{'cells':['B','G']}})
        with patch.object(task_service,'list_tasks',return_value=[task]),patch.object(airport,'runtime_request',return_value={'mission_id':'m-1'}) as request:
            result=airport.start_task({'task_id':task['id']})
        request.assert_called_once_with('/api/mission',{'cells':['B','G'],'platform_task_id':task['id']})
        status={'live':True,'mission':{'id':'m-1','status':'completed','cells':[{'id':'B','phase':'completed'},{'id':'G','phase':'completed'}],
                'evidence':[{'url':'/evidence/one.jpg','label':'双方到位'}]}}
        with patch.object(airport,'runtime_status',return_value=status):
            over=airport.overlay_tasks([task])[0];feed=airport.feedback()
        self.assertEqual((over['status'],over['progress']),('已完成','100%'))
        self.assertEqual(feed[0]['task_id'],result['task_id'])
        self.assertEqual(feed[0]['image'],'/airport-runtime/evidence/one.jpg')
        with patch.object(airport,'runtime_status',return_value={'live':False,'mission':{}}):
            retained=airport.overlay_tasks([task])[0]
        self.assertEqual(retained['status'],'已完成');self.assertFalse(retained['runtime_connected'])

    def test_rejected_start_keeps_pending_order(self):
        with patch.object(airport,'runtime_request',side_effect=ValueError('busy')):
            with self.assertRaises(ValueError):airport.start_task({})
        records=task_service._read_records()
        self.assertEqual(records[0]['status'],'待调度')
        self.assertFalse(airport.JOBS.exists())

    def test_runtime_restart_marks_unfinished_order_interrupted(self):
        airport._save([{'task_id':'t','mission_id':'old','executor':'班组','mission':{'status':'running','cells':[]}}])
        with patch.object(airport,'runtime_status',return_value={'live':True,'mission':{'status':'idle'}}):
            task=airport.overlay_tasks([{'id':'t','station':'airport-t1'}])[0]
        self.assertEqual(task['status'],'异常');self.assertIn('重启',task['runtime_error'])

    def test_grid_reset_preserves_airport_orders(self):
        task=task_service.create_task({'station':'airport-t1','type':'joint','name':'保留机场工单'})
        task_service.create_task({'station':'dispatch-pool','type':'robot','name':'电网工单'})
        task_service.clear_runtime_tasks()
        records=task_service._read_records()
        self.assertEqual([r['task_id'] for r in records],[task['id']])

if __name__=='__main__':unittest.main()
