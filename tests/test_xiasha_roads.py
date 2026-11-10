import unittest
from math import hypot

from platform_app.services.planning_service import plan_route
from platform_app.services.xiasha_roads import CENTER_LAT, CENTER_LON, road_path_for_stops, scene_to_lonlat


class XiashaRoadTests(unittest.TestCase):
    def test_scene_origin_is_hdu_xiasha(self):
        lon, lat = scene_to_lonlat(50, 50)
        self.assertAlmostEqual(lon, CENTER_LON, places=5)
        self.assertAlmostEqual(lat, CENTER_LAT, places=5)
        self.assertAlmostEqual(CENTER_LON, 120.3479082, places=5)
        self.assertAlmostEqual(CENTER_LAT, 30.3165737, places=5)

    def test_checkpoints_follow_connected_roads(self):
        path = road_path_for_stops([{"x": 50, "y": 50}, {"x": 72, "y": 36}, {"x": 50, "y": 50}])
        self.assertGreater(len(path), 8)
        self.assertLess(hypot(path[0]["x"] - 50, path[0]["y"] - 50), 4)
        for left, right in zip(path, path[1:]):
            self.assertLess(hypot(right["x"] - left["x"], right["y"] - left["y"]), 12)
            self.assertNotIn("z", left)
        self.assertGreater(path[0]["lon"], 120.2)
        self.assertLess(path[0]["lon"], 120.5)
        self.assertGreater(path[0]["lat"], 30.2)
        self.assertLess(path[0]["lat"], 30.45)

    def test_plan_keeps_demo_altitude_and_adds_road_track(self):
        route = plan_route(
            {"route": {"start": {"x": 50, "y": 50}, "waypoints": [{"id": "P", "x": 80, "y": 20}]}},
            {"type": "drone", "position": {"x": 45, "y": 59}},
        )
        self.assertGreater(len(route["road_path"]), 4)
        self.assertIn("z", route["path"][0])
        self.assertNotIn("z", route["road_path"][0])


if __name__ == "__main__":
    unittest.main()
