"""Canonical resource IDs mapped to stable ROS/Gazebo model names."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
catalog=ROOT/'resources.json'
if not catalog.exists():catalog=ROOT.parent.parent/'sample_data/resources.json'
REGISTRY={r['id']:r for r in json.loads(catalog.read_text(encoding='utf-8'))}
CELLS=[];DEVICES={}
for i,(zone,x,title,alarm,cargo) in enumerate([
 ('A',145.,'配电设备','温升告警','绝缘检测工具箱'),
 ('B',135.,'行李输送','振动告警','输送机维护工具箱'),
 ('C',125.,'安防设施','设备离线','备用通信模块'),
 ('D',120.,'消防设施','压力复核','压力检测工具'),
 ('E',130.,'登机服务','闸机复核','闸机维护组件'),
 ('F',140.,'环境监测','通风复核','环境采样组件'),
 ('G',150.,'通信机柜','信号复核','通信维护工具')]):
 suffix='' if i==0 else '_'+str(i+1)
 dog='inspection_dog'+suffix;drone='inspection_drone'+suffix
 CELLS.append(dict(id=zone,name=zone+'区 · '+title,kind=alarm,x=x,y=-35.5,
  dog=dog,drone=drone,person=f'PERSON-{i+1:02}',inspect='inspect_'+zone.lower(),
  delivery='delivery_'+zone.lower(),altitude=5.+i*.4,cargo=cargo))
 for kind,name,ns,home,fleet,dock in [
  ('dog',dog,'dog'+('' if i==0 else str(i+1)),[x+2.,-36.5,.62],'inspectionDog','dog_dock'+suffix),
  ('drone',drone,'drone'+('' if i==0 else str(i+1)),[x,-30.5,.40],None,None)]:
  pid=f'{"DOG" if kind=="dog" else "DRONE"}-{i+1:02}'
  DEVICES[name]=dict(platform_id=pid,label=pid,type=kind,name=REGISTRY[pid]['name'],
   namespace=ns,home=home,dock=dock,fleet=fleet,cell=zone)
# Main-lane indices 8/9 remain the sensor-controlled blocked segment.
POINTS=[(130.,-41.5,'amr_dock'),(133.,-41.5,'amr_dock_2'),(125.,-39.5,'lane_c'),(130.,-39.5,'lane_w'),
 (133.,-39.5,'lane_m'),(135.,-39.5,'lane_b'),(138.,-39.5,'lane_e'),(145.,-39.5,'lane_a'),(148.,-39.5,'lane_end'),
 (130.,-42.8,'detour_w'),(142.,-42.8,'detour_e')]
EDGES=[(0,3),(1,4),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(0,9),(1,9),(9,10),(10,7)]
# Park on the unobstructed apron beside the main lane. Farther south the
# original terminal mesh includes walls that intersect a route at y=-44.8.
for i,(x,y) in enumerate([(130.,-41.5),(133.,-41.5),(125.,-41.5),(138.,-41.5),(141.,-41.5),(145.,-41.5),(151.,-41.5)]):
 pid=f'ROBOT-{i+1:02}';dock='amr_dock'+('' if i==0 else '_'+str(i+1))
 DEVICES['logistics_'+str(i+1)]=dict(platform_id=pid,label=pid,type='amr',name=REGISTRY[pid]['name'],home=[x,y,0.],dock=dock,fleet='logistics')
 if i>=2:
  start=len(POINTS);POINTS += [(x,y,dock),(x,-39.5,'dock_exit_'+str(i+1))]
  lane=min(range(2,9),key=lambda k:abs(POINTS[k][0]-x))
  # Reuse an existing lane vertex when the x coordinate matches exactly.
  if POINTS[lane][0] == x:
   POINTS.pop();EDGES += [(start,lane)]
  else:
   EDGES += [(start,start+1),(start+1,lane)]
for cell in CELLS:
 dev=DEVICES[cell['dog']];base=len(POINTS)
 lane=min(range(2,9),key=lambda k:abs(POINTS[k][0]-cell['x']))
 POINTS += [(dev['home'][0],dev['home'][1],dev['dock']),(cell['x'],cell['y'],cell['inspect']),(cell['x'],-38.,cell['delivery'])]
 EDGES += [(base,lane),(base,base+1),(base+2,lane)]
PERSONNEL=[dict(id=c['person'],name=REGISTRY[c['person']]['name'],type='person',cell=c['id'],home=[c['x'],-26.,0.],source='roster_anchor') for c in CELLS]
LOCATIONS={n:[x,y] for x,y,n in POINTS}
CAMERA=dict(position=[136.,-69.,29.],pitch=.75,yaw=1.57,width=960,height=540,hfov=1.1)
