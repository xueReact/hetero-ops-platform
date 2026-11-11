"""Join Gazebo telemetry and work orders to the platform's canonical IDs.

Only measured robot state is treated as online. Personnel are roster records,
not invented GPS reports. Persist results so refresh/restart retains work orders.
"""
import copy
import json
import time
from datetime import datetime, timezone
from threading import RLock
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from platform_app.config import AIRPORT_UPSTREAM, DATA_DIR
from platform_app.services.project_service import registry

LOCK = RLock()
JOBS = DATA_DIR / 'airport-jobs.json'
_cache = {'time': 0, 'data': {}}

def runtime_request(path, payload=None):
    req = Request(AIRPORT_UPSTREAM.rstrip('/') + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=5) as response:
            return json.load(response)
    except HTTPError as exc:
        try: message = json.load(exc).get('error', str(exc))
        except ValueError: message = str(exc)
        raise ValueError(message) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError('机场服务未连接，请检查运行服务') from exc

def runtime_status(force=False):
    with LOCK:
        if not force and time.monotonic() - _cache['time'] < 1:
            return copy.deepcopy(_cache['data'])
        try:
            value = runtime_request('/api/status')
        except (RuntimeError, ValueError):
            value = {'live': False, 'ready': False, 'devices': [], 'mission': {}, 'connection_error': True}
        _cache.update(time=time.monotonic(), data=value)
        return copy.deepcopy(value)

def resources(status=None):
    status = runtime_status() if status is None else status
    runtime = {d.get('platform_id', d.get('label')): d for d in status.get('devices', [])}
    rows = []
    for record in registry():
        r = dict(record, station='airport-t1', project_id='airport-t1', motion=None,
                 power='—', power_percent=None, task='待命', online=False)
        d = runtime.get(r['id'])
        if r['type'] == 'person':
            r.update(status='待命', task='现场核验 / 工单签收', telemetry_source='人员名册 · 无实时定位',
                     position=None)
        elif d:
            phase = d.get('phase', 'idle')
            r.update(status='离线' if not d['online'] else '已暂停' if status.get('paused') else '执行中' if phase in ('running','servicing','waiting') else '待命',
                online=d['online'], runtime_id=d['id'], task=d.get('action', '待命'),
                position=d.get('pose') or None, moving=d.get('moving', False),
                telemetry_source=(d.get('pose') or {}).get('source', 'Gazebo'))
        else:
            r.update(status='离线', telemetry_source='等待 Gazebo 遥测', position=None)
        rows.append(r)
    return rows

def unified_status():
    s = runtime_status()
    s['resources'] = resources(s)
    profiles = {r['id']:r for r in s['resources']}
    for d in s.get('devices', []):
        d['name'] = profiles.get(d.get('platform_id'), {}).get('name', d['name'])
    for person in s.get('scene', {}).get('personnel', []):
        person['name'] = profiles.get(person['id'], {}).get('name', person['name'])
    s['project_id'] = 'airport-t1'
    s['registry_count'] = len(s['resources'])
    s['person_count'] = sum(r['type'] == 'person' for r in s['resources'])
    return s

def _jobs():
    return json.loads(JOBS.read_text(encoding='utf-8')) if JOBS.exists() else []

def _save(rows):
    JOBS.parent.mkdir(parents=True, exist_ok=True)
    temp = JOBS.with_suffix('.tmp')
    temp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(JOBS)

def sync_jobs():
    s = runtime_status()
    mission = s.get('mission', {})
    with LOCK:
        rows = _jobs(); changed = False
        for row in rows:
            previous = copy.deepcopy(row)
            row['connected'] = s.get('live', False)
            if row['mission_id'] == mission.get('id'):
                row['mission'] = mission
            elif s.get('live') and row.get('mission', {}).get('status') == 'running':
                row['mission'].update(status='interrupted', error='运行服务已重启或任务已切换，请检查设备后创建新工单')
            changed |= previous != row
        if changed: _save(rows)
        return rows

def overlay_tasks(tasks):
    jobs = {j['task_id']: j for j in sync_jobs()}
    for task in tasks:
        if task.get('station') != 'airport-t1': continue
        task['project_id'] = 'airport-t1'
        job = jobs.get(task['id'])
        if not job: continue
        m = job.get('mission', {})
        phases = {'queued':0, 'inspect':15, 'air':35, 'queue':50, 'transport':60, 'handoff':75, 'return':90, 'completed':100}
        cells = m.get('cells') or []
        task.update(status={'running':'执行中','completed':'已完成','failed':'异常','interrupted':'异常'}.get(m.get('status'), '待调度'),
                    progress=str(round(sum(phases.get(c.get('phase'),0) for c in cells)/max(1,len(cells))))+'%',
                    executor='机场联合班组 · '+str(len(cells) or len(task.get('requirements', {}).get('cells') or list('ABCDEFG')))+' 个作业区', mission_id=job['mission_id'], evidence=m.get('evidence', []),
                    runtime_connected=job.get('connected', False), runtime_error=m.get('error'),
                    workcells=cells)
    return tasks

def start_task(payload):
    from platform_app.services.project_service import active_project
    from platform_app.services.task_service import list_tasks, create_task
    if active_project()['id'] != 'airport-t1': raise ValueError('请先切换至机场作业项目')
    with LOCK:
        task_id = payload.get('task_id')
        task = next((t for t in list_tasks() if t['id'] == task_id), None) if task_id else None
        if task_id and (not task or task['station'] != 'airport-t1'):
            raise ValueError('机场任务不存在')
        if task and task['status'] != '待调度': raise ValueError('该任务已执行，请创建新工单')
        cells = (task.get('requirements') or {}).get('cells') if task else payload.get('cells')
        if not task:
            task = create_task({'name': '航站楼七区联合巡检', 'station':'airport-t1', 'type':'joint',
                                'requirements': {'cells': cells or []}, 'points':'地面初检 → 空中复核 → 物资配送 → 交接归位'})
        # Keep a pending order if the runtime rejects the command. An accepted
        # runtime mission always carries the platform ID for result correlation.
        result = runtime_request('/api/mission', {'cells': cells, 'platform_task_id': task['id']})
        names = '机场联合班组 · ' + str(len(cells or list('ABCDEFG'))) + ' 个作业区'
        rows = _jobs()
        rows.append({'task_id':task['id'], 'mission_id':result['mission_id'], 'executor':names,
                     'created_at':datetime.now(timezone.utc).isoformat(), 'mission':{'status':'running','cells':[]}})
        _save(rows); _cache['time'] = 0
        return {'success':True, 'task_id':task['id'], 'mission_id':result['mission_id']}

def feedback():
    rows = []
    for job in sync_jobs():
        m = job.get('mission', {})
        for index, item in enumerate(m.get('evidence', [])):
            rows.append({'id':job['mission_id']+'-'+str(index),'task_id':job['task_id'], 'project_id':'airport-t1',
                'task_name':'航站楼联合巡检','device':'机场作业班组','kind':'完成反馈',
                'message':item['label'],'image':'/airport-runtime'+item['url'],
                'source':'Gazebo 相机 · '+job['mission_id'],'created_at':job['created_at']})
    return list(reversed(rows))
