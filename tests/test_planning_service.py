import unittest
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from platform_app.services.planning_service import astar_grid, build_v1_plan, evaluate_candidate
from platform_app.services.sample_data_service import get_overview, read_sample_file, list_sample_tasks
from platform_app.services.telemetry_service import enrich_resources
from platform_app.services.task_service import list_tasks
from platform_app.services.dispatch_service import interpolate_position
from platform_app.services import dispatch_service


class PlanningServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overview = get_overview()
        cls.tasks = list_sample_tasks()
        cls.overview["resources"] = enrich_resources(read_sample_file("resources.json"))

    def test_overview_exposes_normalized_telemetry(self):
        robot = next(row for row in self.overview["resources"] if row["type"] == "robot")
        self.assertIsInstance(robot["power_percent"], int)
        self.assertIn("position", robot)
        self.assertIn("rgb_camera", robot["capabilities"])
        self.assertEqual(self.overview["telemetry_contract"]["soc"], "/zj_humanoid/chassis/charge_state")

    def test_low_battery_candidate_is_rejected_with_reason(self):
        task = next(row for row in self.tasks if row["id"] == "xiasha-road")
        robot = next(row.copy() for row in self.overview["resources"] if row["id"] == "ROBOT-02")
        robot["power_percent"] = 10
        result = evaluate_candidate(task, robot, self.overview["environment"])
        self.assertFalse(result.accepted)
        self.assertTrue(any("电量不足" in reason for reason in result.rejected_by))

    def test_bad_weather_rejects_drone(self):
        task = next(row for row in self.tasks if row["type"] == "drone")
        drone = next(row for row in self.overview["resources"] if row["id"] == "DRONE-02")
        environment = {"flight_allowed": True, "weather": {"wind_mps": 12, "precipitation_mm": 0}}
        result = evaluate_candidate(task, drone, environment)
        self.assertFalse(result.accepted)
        self.assertTrue(any("风速" in reason for reason in result.rejected_by))

    def test_astar_avoids_blocked_cells(self):
        blocked = {(5, y) for y in range(0, 10)}
        path = astar_grid((2, 4), (8, 4), blocked)
        self.assertEqual(path[0], (2, 4))
        self.assertEqual(path[-1], (8, 4))
        self.assertFalse(set(path) & blocked)
        self.assertGreater(len(path), 6)

    def test_astar_rejects_unreachable_and_diagonal_corner(self):
        with self.assertRaisesRegex(ValueError, "没有可行路径"):
            astar_grid((0, 0), (2, 2), {(1, 0), (0, 1), (1, 1)})
        with self.assertRaisesRegex(ValueError, "没有可行路径"):
            astar_grid((0, 0), (1, 1), {(1, 0), (0, 1)})

    def test_dispatch_position_uses_saved_route(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        row = {"created_at": (now - timedelta(seconds=5)).isoformat(), "simulation_duration_seconds": 10,
               "planned_route": {"path": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]}}
        self.assertEqual(interpolate_position(row, now), {"x": 5.0, "y": 0.0})

    def test_plan_keeps_two_ready_machines_of_each_type(self):
        plan = build_v1_plan(self.tasks, self.overview["resources"], self.overview["environment"])
        counts = {}
        for row in plan["standby"]:
            counts[row["type"]] = counts.get(row["type"], 0) + 1
        for kind in ("robot", "dog", "drone", "person"):
            self.assertGreaterEqual(counts.get(kind, 0), 2, kind)
        self.assertEqual(plan["unassigned_task_ids"], [])
        gas = [row["resource_id"] for row in plan["assignments"] if row["task_id"] == "xiasha-gas"]
        self.assertGreaterEqual(len(gas), 2)

    def test_plan_assigns_unique_resources_and_routes_every_task(self):
        plan = build_v1_plan(self.tasks, self.overview["resources"], self.overview["environment"])
        resource_ids = [row["resource_id"] for row in plan["assignments"]]
        self.assertEqual(len(resource_ids), len(set(resource_ids)))
        self.assertGreaterEqual(len(plan["assignments"]), 5)
        grouped = {}
        for row in plan["assignments"]:
            grouped.setdefault(row["task_id"], []).append(row)
        self.assertGreaterEqual(len(grouped), 5)
        self.assertTrue(any(len(rows) >= 2 for rows in grouped.values()))
        for row in plan["assignments"]:
            self.assertTrue(row["route"]["path"])
            self.assertTrue(row["route"].get("road_path"))
            self.assertEqual(row["route"]["path"][0], row["route"]["path"][-1])
            task = next(task for task in self.tasks if task["id"] == row["task_id"])
            self.assertEqual(len(row["route"]["waypoint_order"]), len(task["route"]["waypoints"]))
            self.assertTrue(row["reasons"])

    def test_field_constraints_get_a_dispatchable_alternative(self):
        gas = {
            "id": "gas-narrow",
            "name": "紧急巡检 · 气体浓度告警",
            "station": "dispatch-pool",
            "type": "robot",
            "status": "待调度",
            "requirements": {"capabilities": ["gas"], "terrain": "flat", "max_slope_deg": 10, "min_width_m": 0.8},
            "route": {"start": {"x": 50, "y": 50}, "end": {"x": 50, "y": 50}, "waypoints": [{"id": "紧急点", "x": 67, "y": 56}], "distance_m": 900},
        }
        stairs = deepcopy(next(task for task in self.tasks if task["id"] == "xiasha-gas"))
        stairs["route"] = {**stairs["route"], "distance_m": 2938}
        mountain = {
            "id": "relief-rough",
            "name": "碎石坡通行",
            "station": "dispatch-pool",
            "type": "robot",
            "status": "待调度",
            "requirements": {"capabilities": ["rgb_camera", "thermal"], "terrain": "rough", "max_slope_deg": 25, "min_width_m": 0.7},
            "route": {"start": {"x": 50, "y": 50}, "end": {"x": 50, "y": 50}, "waypoints": [{"id": "半山设备", "x": 65, "y": 30}, {"id": "高处监测", "x": 80, "y": 20}], "distance_m": 1800},
        }
        resources = deepcopy(self.overview["resources"])
        for row in resources:
            if row["type"] == "robot":
                row["power_percent"] = 90
                row["status"] = "待命"
            elif row["id"] == "DOG-01":
                row["power_percent"] = 30
                row["status"] = "待命"
            elif row["id"] == "DOG-04":
                row["power_percent"] = 32
                row["status"] = "待命"
            elif row["type"] == "dog":
                row["status"] = "待检修"
            elif row["id"] == "DRONE-03":
                row["power_percent"] = 55
                row["status"] = "待命"
            elif row["type"] == "drone":
                row["power_percent"] = 30
                row["status"] = "待命"
        plan = build_v1_plan([gas, stairs, mountain], resources, self.overview["environment"])
        by_id = {row["task_id"]: row for row in plan["assignments"]}
        self.assertEqual(by_id["gas-narrow"]["resource_type"], "dog")
        self.assertIn("通道", by_id["gas-narrow"]["resolution"])
        self.assertTrue(by_id["gas-narrow"]["route"]["path"])
        self.assertEqual(by_id["xiasha-gas"]["resource_type"], "dog")
        self.assertEqual(by_id["xiasha-gas"]["coverage"], "partial")
        self.assertIn("楼梯", by_id["xiasha-gas"]["resolution"])
        self.assertEqual(by_id["relief-rough"]["resource_type"], "drone")
        self.assertEqual(by_id["relief-rough"]["route"]["flight_agl_m"], 60)
        self.assertEqual(len({row["resource_id"] for row in plan["assignments"]}), 3)
        self.assertEqual(plan["unassigned_task_ids"], [])

    def test_incident_returns_device_and_reopens_task(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        row = {"task_id": "task-1", "task_name": "巡检", "resource_id": "robot-1", "resource_name": "机器人 1",
               "status": dispatch_service.SENT, "created_at": (now-timedelta(seconds=5)).isoformat(),
               "simulation_duration_seconds": 10, "planned_route": {"path": [{"x": 0, "y": 0}, {"x": 10, "y": 0}]},
               "initial_power_percent": 80, "estimated_energy_pct": 20}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dispatches.json"
            path.write_text(json.dumps([row]), encoding="utf-8")
            with patch.object(dispatch_service, "DISPATCHES_FILE", path):
                event = dispatch_service.trigger_random_incident(reason="传感器故障")
                self.assertEqual(event["state"], dispatch_service.RETURNING)
                self.assertEqual(dispatch_service.overlay_dispatches([{"id": "task-1", "status": "执行中"}])[0]["status"], dispatch_service.PENDING)
                resource = dispatch_service.resources_with_dispatches([{"id": "robot-1", "status": "待命", "position": {"x": 0, "y": 0}}])[0]
                self.assertEqual(resource["status"], dispatch_service.RETURNING)
                self.assertEqual(len(dispatch_service.active_dispatches()), 1)
                saved = dispatch_service.list_dispatches()[0]
                after = datetime.fromisoformat(saved["incident_at"]) + timedelta(seconds=46)
                self.assertEqual(dispatch_service.dispatch_state(saved, after), dispatch_service.MAINTENANCE)
                self.assertEqual(dispatch_service.interpolate_position(saved, after), {"x": 0, "y": 0})


if __name__ == "__main__":
    unittest.main()
