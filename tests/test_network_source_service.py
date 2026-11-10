import unittest

from platform_app.config import NETWORK_ASSETS_DIR
from platform_app.services.network_source_service import network_sources, parse_opendrive, parse_osm


class NetworkSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {item["id"]: item for item in network_sources()}

    def test_geometry_segments_meet_and_elevation_is_sampled(self):
        elevation = parse_opendrive(NETWORK_ASSETS_DIR / "esmini-curves-elevation.xodr")
        self.assertLess(elevation["max_join_error_m"], 1.5)
        self.assertGreater(max(point["z"] for point in elevation["roads"][0]["points"]), 10)
        self.assertGreater(self.sources["esmini-elevation"]["summary"]["max_grade_pct"], 1)
        self.assertEqual(self.sources["esmini-elevation"]["route"]["road_count"], 1)
        self.assertGreater(self.sources["esmini-elevation"]["route"]["length_m"], 1000)

    def test_intersection_route_crosses_connected_roads(self):
        network = self.sources["esmini-intersections"]
        self.assertGreater(network["summary"]["junctions"], 1)
        self.assertGreater(network["summary"]["roads"], 10)
        self.assertGreater(network["route"]["road_count"], 1)
        self.assertGreater(len(network["route"]["path"]), 4)

    def test_city_and_osm_routes_use_the_same_published_frame(self):
        for source_id in ("esmini-fabriksgatan", "osmnx-osm"):
            source = self.sources[source_id]
            self.assertGreater(source["route"]["road_count"], 1)
            self.assertTrue(source["routable"])
            for line in source["lines"]:
                for point in line:
                    self.assertGreaterEqual(point["x"], 5)
                    self.assertLessEqual(point["x"], 95)
                    self.assertGreaterEqual(point["y"], 5)
                    self.assertLessEqual(point["y"], 95)
            route_start = source["route"]["path"][0]
            flattened = [point for line in source["lines"] for point in line]
            self.assertTrue(any(abs(point["x"] - route_start["x"]) < 1.5 and abs(point["y"] - route_start["y"]) < 1.5 for point in flattened))

    def test_osm_graph_preserves_multiple_ways(self):
        parsed = parse_osm(NETWORK_ASSETS_DIR / "osmnx-munich-sample.osm")
        self.assertGreater(len(parsed["roads"]), 3)
        self.assertGreater(len(parsed["route"]["road_ids"]), 1)


if __name__ == "__main__":
    unittest.main()
