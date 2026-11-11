/* Leaflet is vendored (BSD-2-Clause). Indoor coordinates remain meters in the
 * Gazebo frame; a regional satellite image is NEVER used as a false georeference.
 * The same scene.points/edges drive RMF and the 2D road overlay. */
window.AirportMaps = (() => {
  let map, mode, geometry, state, lastScene, markers = new Map(), trails, routes, base;
  const host=()=>document.querySelector('#airportMap');
  const colors={dog:'#bc821b',drone:'#0a9b8b',amr:'#387bce',person:'#896ac2'};
  const clean=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const coord=p=>[p[1],p[0]];
  function notice(text){const n=document.querySelector('#mapNotice');n.textContent=text;n.hidden=!text;}
  function setMode(next){
    const visible=['plan','road','satellite'].includes(next);
    host().hidden=!visible;
    if(!visible){notice('');return;}
    if(!window.L){notice('地图组件未载入，请刷新页面');return;}
    if(mode===next&&map){map.invalidateSize();return;}
    if(map){map.remove();map=null;}mode=next;markers.clear();lastScene=null;
    map=L.map(host(),{crs:next==='plan'?L.CRS.Simple:L.CRS.EPSG3857,attributionControl:true,
      minZoom:next==='plan'?2:10,maxZoom:next==='plan'?7:19,zoomSnap:.25});
    if(next==='plan'){
      map.fitBounds([[-48,114],[-22,155]],{padding:[15,20]});
      geometry=L.layerGroup().addTo(map);routes=L.layerGroup().addTo(map);trails=L.layerGroup().addTo(map);
      map.attributionControl.addAttribution('Open-RMF · WORLD / 米');
      notice('');if(state)update(state);
    }else{
      map.setView([30.2361,120.4344],14);
      const satellite=next==='satellite';
      base=L.tileLayer(satellite?'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}':'https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
        maxZoom:19,attribution:satellite?'Tiles © Esri · Maxar, Earthstar Geographics':'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}).addTo(map);
      let failed=0,loaded=0,usingFallback=false;const instance=map;
      const fallback=()=>{
        if(map!==instance||mode!==next||loaded)return;
        if(!satellite&&!usingFallback){
          usingFallback=true;base.remove();
          base=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Tiles © Esri · HERE, Garmin, OpenStreetMap contributors'}).addTo(map);
          base.on('tileload',()=>{loaded++;notice('杭州萧山机场 · 区域道路参考（Esri）；室内作业图独立定位');});
          base.on('tileerror',()=>notice('在线道路底图不可达 · 请切换二维路网'));
        }else notice('在线底图暂不可达 · 可切换二维路网继续作业');
      };
      base.on('tileload',()=>loaded++);
      base.on('tileerror',()=>{if(++failed>=3)fallback();});
      setTimeout(fallback,10000);
      L.circleMarker([30.2361,120.4344],{radius:9,color:'#fff',weight:3,fillColor:'#1c8b8b',fillOpacity:1}).addTo(map)
       .bindTooltip('杭州萧山国际机场',{permanent:true,direction:'top'}).bindPopup('<b>机场作业项目</b><br>区域位置参考；室内设备在二维作业图中查看。');
      notice('杭州萧山机场 · 区域底图；航站楼作业模型未做测绘配准');
    }
    setTimeout(()=>map?.invalidateSize(),0);
  }
  function update(s){
    state=s;if(!map||mode!=='plan'||!s?.scene)return;
    const scene=s.scene;
    if(!lastScene){
      lastScene=scene;geometry.clearLayers();
      L.rectangle([[-47,115],[-22,155]],{color:'#8b9fa6',weight:2,fillColor:'#eaf1f2',fillOpacity:1}).addTo(geometry);
      for(const [a,b] of scene.edges){
        const points=[coord(scene.points[a]),coord(scene.points[b])];
        L.polyline(points,{color:'#c4d2d7',weight:14}).addTo(geometry);
        L.polyline(points,{color:'#fff',weight:1,dashArray:'5 6'}).addTo(geometry);
      }
      for(const c of scene.cells){
        L.rectangle([[-34.6,c.x-1.8],[-32.6,c.x+1.8]],{color:'#7c99a8',weight:1,fillColor:'#dce7eb',fillOpacity:1}).addTo(geometry)
          .bindTooltip(clean(c.name),{permanent:true,direction:'top',className:'zone-label'});
        L.circleMarker([c.y,c.x],{color:'#bc821b',radius:5,weight:2}).addTo(geometry).bindTooltip(c.id+' 区初检点');
        L.circleMarker([-38,c.x],{color:'#387bce',radius:5,weight:2}).addTo(geometry).bindTooltip(c.id+' 区交接点');
      }
      for(const p of scene.personnel||[]){L.circleMarker(coord(p.home),{color:colors.person,radius:5,dashArray:'2 2',fillOpacity:.2}).addTo(geometry)
          .bindTooltip(clean(p.name)+' · '+p.id+' · 名册工位（非实时定位）');}
      const label=(p,text)=>L.marker(p,{icon:L.divIcon({className:'map-area-label',html:clean(text),iconSize:[160,20],iconAnchor:[80,10]})}).addTo(geometry);
      label([-24,135],'航站楼服务柜台 / 人员值守区');label([-46.2,134],'设备保障区 · 共享配送与充电仓位');
    }
    const ids=new Set();
    for(const d of s.devices||[]){
      const p=d.pose;if(!p||!d.online)continue;ids.add(d.id);
      let marker=markers.get(d.id);
      if(!marker){marker=L.circleMarker([p.y,p.x],{radius:6,color:'#fff',weight:2,fillColor:colors[d.type],fillOpacity:1}).addTo(map);
        marker.on('click',()=>window.selectDevice?.(d.id));markers.set(d.id,marker);}
      marker.setLatLng([p.y,p.x]).setStyle({radius:d.moving?8:6,weight:d.moving?3:2,color:d.moving?'#bce970':'#fff'});
      const label=clean(d.label)+(d.moving?' ●':'');
      if(marker.getTooltip())marker.setTooltipContent(label);else marker.bindTooltip(label,{permanent:true,direction:'top',className:'device-map-label'});
    }
    for(const [id,marker] of markers){if(!ids.has(id)){marker.remove();markers.delete(id);}}
    routes.clearLayers();trails.clearLayers();
    if(document.querySelector('#show-routes')?.checked){
      for(const p of Object.values(s.paths||{}))if(p.points?.length>1)L.polyline(p.points.map(coord),{color:colors[(s.devices||[]).find(d=>d.id===p.robot)?.type]||'#1f8b91',weight:2,dashArray:'6 5',opacity:.8}).addTo(routes);
      for(const p of Object.values(s.trails||{}))if(p.length>1)L.polyline(p.map(coord),{color:'#5e8390',weight:1,opacity:.35}).addTo(trails);
    }
    if(s.obstacle?.active)L.rectangle([[-40.1,133.6],[-38.9,134.4]],{color:'#dc6457',fillOpacity:.8}).addTo(routes).bindTooltip('维护围挡 · '+(s.obstacle.closed?'已封路':'感知中'));
  }
  return {setMode,update};
})();
