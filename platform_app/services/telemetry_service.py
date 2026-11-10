"""Deterministic simulation telemetry with published ZJ Humanoid ROS topic names."""

from __future__ import annotations

import re
from platform_app.services.planning_service import elevation_m
from platform_app.services.cost_service import CAPACITY_KWH


TYPE_PROFILES = {
    "person": {
        "capabilities": ["manual_inspection", "rgb_camera"],
        "terrain": ["flat", "stairs", "rough", "narrow"],
        "max_slope_deg": 35,
        "min_width_m": 0.5,
        "speed_mps": 1.2,
        "reserve_pct": 0,
    },
    "robot": {
        "capabilities": ["rgb_camera", "thermal", "gas", "lidar"],
        "terrain": ["flat", "indoor"],
        "max_slope_deg": 12,
        "min_width_m": 0.9,
        "speed_mps": 1.2,
        "reserve_pct": 20,
    },
    "dog": {
        "capabilities": ["rgb_camera", "thermal", "gas", "lidar"],
        "terrain": ["flat", "stairs", "rough", "narrow"],
        "max_slope_deg": 35,
        "min_width_m": 0.65,
        "speed_mps": 1.4,
        "reserve_pct": 20,
    },
    "drone": {
        "capabilities": ["rgb_camera", "thermal", "aerial_camera"],
        "terrain": ["air", "outdoor"],
        "max_slope_deg": 90,
        "min_width_m": 0,
        "speed_mps": 6.0,
        "reserve_pct": 25,
    },
}


POSITION_SEEDS = {
    "person": [(44, 54), (47, 57), (53, 56), (56, 53), (43, 48), (50, 51), (41, 51)],
    "robot": [(42, 45), (46, 43), (51, 44), (55, 46), (58, 43)],
    "dog": [(40, 50), (44, 48), (52, 49), (57, 51), (60, 48)],
    "drone": [(45, 59), (49, 61), (54, 60), (58, 57), (61, 61)],
}


TELEMETRY_CONTRACT = {
    "soc": "/zj_humanoid/chassis/charge_state",
    "odom": "/zj_humanoid/chassis/odom_info",
    "state": "/zj_humanoid/chassis/agv_state",
    "motor": "/zj_humanoid/chassis/motor_info",
    "navigation": "/zj_humanoid/navigation/navigation_status",
    "mode": "仿真遥测 · ROS1 接口参考",
    "reference": "ZJ-Humanoid Navi02 ROS1 SDK",
}


def parse_power(value) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return max(0, min(100, int(match.group()))) if match else None


def enrich_resources(resources: list[dict]) -> list[dict]:
    enriched = []
    for item in resources:
        row = dict(item)
        resource_type = row.get("type", "person")
        profile = TYPE_PROFILES.get(resource_type, TYPE_PROFILES["person"])
        match = re.search(r"(\d+)$", str(row.get("id", "")))
        index = max(0, (int(match.group()) - 1) if match else 0)
        positions = POSITION_SEEDS.get(resource_type, POSITION_SEEDS["person"])
        x, y = positions[index % len(positions)]
        power = parse_power(row.get("power"))
        ground = elevation_m(x, y)
        clearance = 60 if resource_type == "drone" else 0
        row.update(
            {
                "power_percent": power,
                "battery_applicable": power is not None,
                "battery_capacity_kwh": CAPACITY_KWH.get(resource_type,0),
                "position": {"x": x, "y": y, "z": ground + clearance},
                "ground_elevation_m": ground,
                "altitude_agl_m": clearance,
                "capabilities": list(profile["capabilities"]),
                "terrain": list(profile["terrain"]),
                "max_slope_deg": profile["max_slope_deg"],
                "min_width_m": profile["min_width_m"],
                "speed_mps": profile["speed_mps"],
                "simulation_speed_multiplier": 12,
                "reserve_pct": profile["reserve_pct"],
                "signal_percent": max(58, 96 - index * 7),
                "last_seen_seconds": 3 + index * 2,
                "telemetry_state": "在线" if row.get("status") != "离线" else "断连",
            }
        )
        enriched.append(row)
    return enriched
