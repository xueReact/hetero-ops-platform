import unittest

from platform_app.services.neural_dispatch import choose_team, feature_vector, forward, score_candidates, suggest_schemes
from platform_app.services.planning_service import evaluate_candidate
from platform_app.services.sample_data_service import list_sample_tasks
from platform_app.services.telemetry_service import enrich_resources
from platform_app.services.sample_data_service import read_sample_file


CALM = {"flight_allowed": True, "weather": {"wind_mps": 3.2, "precipitation_mm": 0}}
STORM = {"flight_allowed": True, "weather": {"wind_mps": 12, "precipitation_mm": 4}}


def _resource(resource_id, kind, power, status="待命"):
    return enrich_resources([{"id": resource_id, "name": resource_id, "type": kind, "status": status, "power": power, "station": "dispatch-pool"}])[0]


FLAT = {
    "id": "flat",
    "name": "厂区设备巡检",
    "station": "dispatch-pool",
    "type": "robot",
    "status": "待调度",
    "requirements": {"capabilities": ["rgb_camera", "thermal"], "terrain": "flat", "min_width_m": 0.9, "max_slope_deg": 10},
    "route": {"start": {"x": 50, "y": 50}, "end": {"x": 50, "y": 50}, "waypoints": [{"id": "P", "x": 60, "y": 40}], "distance_m": 800},
}


class NeuralDispatchTests(unittest.TestCase):
    def test_fixed_weights_pick_two_ready_ground_units(self):
        resources = [
            _resource("ROBOT-HI", "robot", "92%"),
            _resource("ROBOT-LOW", "robot", "35%"),
            _resource("DOG-HI", "dog", "88%"),
            _resource("ROBOT-OFF", "robot", "100%", "离线"),
        ]
        team = [row["resource"]["id"] for row in choose_team(FLAT, resources, CALM)]
        self.assertEqual(team, ["ROBOT-HI", "DOG-HI"])
        schemes = suggest_schemes(FLAT, resources, CALM)
        self.assertGreaterEqual(len(schemes), 1)
        self.assertEqual([member["id"] for member in schemes[0]["members"]], ["ROBOT-HI", "DOG-HI"])
        self.assertEqual(schemes, sorted(schemes, key=lambda item: -item["score"]))

    def test_wind_blocks_drones_and_low_battery_leaves_one_ground_unit(self):
        task = {
            "id": "air",
            "name": "高空设施航拍",
            "station": "dispatch-pool",
            "type": "drone",
            "status": "待调度",
            "requirements": {"capabilities": ["aerial_camera", "thermal"], "terrain": "outdoor", "max_wind_mps": 8},
            "route": {"start": {"x": 50, "y": 50}, "end": {"x": 50, "y": 50}, "waypoints": [{"id": "P", "x": 70, "y": 30}], "distance_m": 900},
        }
        drones = [
            _resource("DRONE-HI", "drone", "94%"),
            _resource("DRONE-MID", "drone", "82%"),
            _resource("DRONE-LOW", "drone", "47%"),
        ]
        calm = [row["resource"]["id"] for row in choose_team(task, drones, CALM)]
        self.assertEqual(calm, ["DRONE-HI"])
        storm = choose_team(task, drones, STORM)
        self.assertEqual(storm, [])
        blocked = evaluate_candidate(task, drones[0], STORM)
        self.assertTrue(any("风速" in reason or "降水" in reason for reason in blocked.rejected_by))

    def test_forward_is_deterministic(self):
        resource = _resource("ROBOT-HI", "robot", "92%")
        result = evaluate_candidate(FLAT, resource, CALM)
        features = feature_vector(FLAT, resource, CALM, result)
        self.assertEqual(round(forward(features), 6), round(forward(list(features)), 6))
        self.assertGreater(forward(features), 0.9)

    def test_energy_and_terrain_are_hard_masked(self):
        low = _resource("ROBOT-LOW", "robot", "10%")
        blocked = score_candidates(FLAT, [low], CALM)[0]
        self.assertEqual(blocked["probability"], 0)
        self.assertTrue(blocked["mask"]["energy_return_reserve"])
        self.assertTrue(any("电量不足" in reason for reason in blocked["hard_blocked"]))

    def test_sample_tasks_include_a_pair_and_a_single_drone(self):
        resources = enrich_resources(read_sample_file("resources.json"))
        environment = {"flight_allowed": True, "weather": {"wind_mps": 3.2, "precipitation_mm": 0}}
        tasks = {task["id"]: task for task in list_sample_tasks()}
        yard = [row["resource"]["id"] for row in choose_team(tasks["xiasha-road"], resources, environment)]
        aerial = [row["resource"]["id"] for row in choose_team(tasks["xiasha-roof"], resources, environment)]
        self.assertEqual(yard, ["ROBOT-02", "DOG-02"])
        self.assertEqual(aerial, ["DRONE-02", "DRONE-04"])
        gas = [row["resource"]["id"] for row in choose_team(tasks["xiasha-gas"], resources, environment)]
        self.assertGreaterEqual(len(gas), 2)
        self.assertTrue(all(item.startswith("DOG-") for item in gas))


if __name__ == "__main__":
    unittest.main()
