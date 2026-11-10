import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from platform_app.services.cost_service import execution_metrics, task_costs
from platform_app.services.planning_service import plan_route
from platform_app.services.terrain_service import terrain_at

class CostAndTerrainTests(unittest.TestCase):
    def row(self,now):
        return {'task_id':'t','resource_id':'ROBOT-01','resource_name':'R','resource_type':'robot','status':'已派发','created_at':(now-timedelta(seconds=60)).isoformat(),'simulation_duration_seconds':120,'estimated_energy_pct':20,'initial_power_percent':90,'planned_route':{'path':[{'x':0,'y':0,'z':30},{'x':10,'y':0,'z':50}]}}

    def test_forecast_responds_to_simulated_energy_rate(self):
        now=datetime.now(timezone.utc);row=self.row(now)
        a=execution_metrics(row,now);row['consumption_factor']=1.2;b=execution_metrics(row,now)
        self.assertGreater(b['forecast']['energy_kwh'],a['forecast']['energy_kwh'])
        self.assertAlmostEqual(a['used']['distance_m']*2,a['baseline']['distance_m'])

    def test_interrupted_attempt_freezes_forward_distance_and_adds_return(self):
        now=datetime.now(timezone.utc);row=self.row(now)
        row.update({'incident_at':now.isoformat(),'interrupted_progress':.5,'return_duration_seconds':45,'return_route':{'path':[{'x':5,'y':0,'z':40},{'x':0,'y':0,'z':30}]}})
        a=execution_metrics(row,now);b=execution_metrics(row,now+timedelta(seconds=45))
        self.assertGreater(b['used']['distance_m'],a['used']['distance_m'])
        self.assertEqual(b['remaining']['distance_m'],0)
        with patch('platform_app.services.dispatch_service.list_dispatches',return_value=[row,row]):
            cost=task_costs([{'id':'t'}])[0]['cost']
            self.assertEqual(cost['reassignments'],1)
            self.assertGreater(cost['forecast']['energy_kwh'],a['forecast']['energy_kwh'])

    def test_water_is_blocked_and_gravel_has_cost(self):
        self.assertIsNone(terrain_at(20,28)['multiplier'])
        self.assertGreater(terrain_at(75,25)['multiplier'],1)
        with self.assertRaises(ValueError):
            plan_route({'route':{'start':{'x':50,'y':50},'waypoints':[{'id':'water','x':20,'y':28}]}},{'type':'robot','position':{'x':50,'y':50}})
