import unittest
from datetime import datetime, timedelta, timezone

from platform_app.services.planning_service import elevation_m, plan_route
from platform_app.services.dispatch_service import interpolate_position, travel_duration_seconds, path_distance_m
from platform_app.services.telemetry_service import enrich_resources


class SpatialTelemetryTests(unittest.TestCase):
    def test_drone_path_has_ground_endpoints_and_clearance(self):
        route = plan_route({'route': {'start': {'x': 50, 'y': 50}, 'waypoints': [{'id': 'P', 'x': 80, 'y': 20}]}},
                           {'type': 'drone', 'position': {'x': 45, 'y': 59}})
        path = route['path']
        for p in (path[0], path[-1]):
            self.assertEqual(p['z'], elevation_m(p['x'], p['y']))
        for p in path[1:-1]:
            self.assertEqual(p['z']-elevation_m(p['x'], p['y']), 60)

    def test_vertical_motion_uses_z_in_interpolation(self):
        now = datetime.now(timezone.utc)
        row = {'created_at': (now-timedelta(seconds=5)).isoformat(), 'simulation_duration_seconds': 10,
               'resource_type': 'drone', 'planned_route': {'path': [{'x': 50, 'y': 50, 'z': 30}, {'x': 50, 'y': 50, 'z': 90}]}}
        self.assertEqual(interpolate_position(row, now)['z'], 60)

    def test_idle_ground_units_stay_on_the_ground_and_drones_hold_clearance(self):
        for kind in ('dog', 'robot', 'person'):
            device = enrich_resources([{'id': kind+'-1', 'type': kind, 'power': '80%'}])[0]
            self.assertEqual(device['position']['z'], device['ground_elevation_m'])
            self.assertEqual(device['altitude_agl_m'], 0)
        drone = enrich_resources([{'id': 'drone-1', 'type': 'drone', 'power': '80%'}])[0]
        self.assertEqual(drone['altitude_agl_m'], 60)
        self.assertEqual(drone['position']['z'], drone['ground_elevation_m'] + 60)

    def test_duration_uses_nominal_speed_and_explicit_demo_multiplier(self):
        route = {'execution_path': [{'x': 0, 'y': 0}, {'x': 20, 'y': 0}], 'meters_per_unit': 70, 'waypoint_order': ['A']}
        slow = travel_duration_seconds(route, {'type': 'robot', 'speed_mps': 1.2})
        fast = travel_duration_seconds(route, {'type': 'drone', 'speed_mps': 6.0})
        self.assertEqual(path_distance_m(route['execution_path'], 70), 1400)
        self.assertGreater(slow, fast)
        self.assertGreaterEqual(fast, 24)


if __name__ == '__main__':
    unittest.main()
