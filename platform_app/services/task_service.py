import json
import random
from threading import RLock

from platform_app.config import TASKS_FILE
from platform_app.models.task import Task
from platform_app.services.sample_data_service import list_sample_tasks
from platform_app.services.dispatch_service import overlay_dispatches
from platform_app.services.planning_service import spatial_point


_lock = RLock()


def _read_records() -> list[dict]:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text("[]\n", encoding="utf-8")
    try:
        data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("tasks.json 格式错误，请修复 JSON 后重启") from exc
    if not isinstance(data, list):
        raise RuntimeError("tasks.json 顶层必须是数组")
    return data


def clear_runtime_tasks(project_id='dispatch-pool') -> None:
    with _lock:
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        keep = [r for r in _read_records() if r.get('station') != project_id]
        temporary = TASKS_FILE.with_suffix('.tmp')
        temporary.write_text(json.dumps(keep, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        temporary.replace(TASKS_FILE)


def list_tasks() -> list[dict]:
    with _lock:
        records = _read_records()
    tasks = (
        [Task.from_record(record).to_api() for record in records]
        + list_sample_tasks()
    )
    for task in tasks:
        route = task.get('route')
        if route:
            for field in ('start', 'end'):
                if route.get(field): route[field] = spatial_point(route[field])
            route['waypoints'] = [spatial_point(p) for p in route.get('waypoints', [])]
    from platform_app.services.cost_service import task_costs
    from platform_app.services.airport_service import overlay_tasks
    grid = task_costs(overlay_dispatches([t for t in tasks if t['station'] != 'airport-t1']))
    return overlay_tasks([t for t in tasks if t['station'] == 'airport-t1']) + grid


def create_task(payload: dict) -> dict:
    task = Task.from_payload(payload)
    with _lock:
        records = _read_records()
        records.insert(0, task.to_record())
        temporary = TASKS_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(TASKS_FILE)
    return task.to_api()


EMERGENCY_SCENARIOS = (
    ("实验楼气体异常", "gas", {"x": 46, "y": 44}),
    ("教学楼通道受阻", "rgb_camera", {"x": 48, "y": 44}),
    ("学源街路面异常", "rgb_camera", {"x": 62, "y": 50}),
    ("屋顶设施复核", "aerial_camera", {"x": 62, "y": 38}),
)


def create_emergency_task(task_type=None) -> dict:
    scenarios=[s for s in EMERGENCY_SCENARIOS if task_type is None or (s[1]=='aerial_camera')==(task_type=='drone')]
    title, capability, site = random.choice(scenarios)
    kind='drone' if capability=='aerial_camera' else 'robot'
    site = spatial_point(site)
    route = {
        "route_id": "emergency-demo",
        "name": title,
        "start": {"x": 50, "y": 50},
        "end": {"x": 50, "y": 50},
        "waypoints": [{"id": "紧急点", **site}],
        "distance_m": 900,
    }
    return create_task({
        "name": "紧急" + title,
        "station": "dispatch-pool",
        "type": kind,
        "points": f"紧急点 ({site['x']}, {site['y']})",
        "requirements": {"capabilities": [capability], "terrain": "outdoor" if kind=='drone' else "flat", "max_slope_deg": 10, "min_width_m": 1.2},
        "route": route,
    })
