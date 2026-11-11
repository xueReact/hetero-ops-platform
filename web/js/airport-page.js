/* Same-origin console backed by the shared project and resource services. */
window.AirportConsole = (() => {
  let timer = null, pending = null, generation = 0;
  const $ = selector => document.querySelector(selector);

  async function checkConnection() {
    if (pending || !$('#airportFrame')) return;
    const current = generation;
    const request = new AbortController();
    pending = request;
    const timeout = setTimeout(() => request.abort(), 5000);
    try {
      const response = await fetch('/api/airport/status', {cache:'no-store', signal:request.signal});
      if (!response.ok) throw new Error('unavailable');
      const status = await response.json();
      if(status.connection_error) throw new Error('runtime disconnected');
      if (current !== generation || !$('#airportConnection')) return;
      const online = (status.devices || []).filter(device => device.online).length;
      const label = $('#airportConnection');
      label.textContent = status.paused ? '已连接 · 现场已暂停' : status.ready ? `已连接 · ${status.registry_count||28} 个资源 · ${online} 台设备在线` : '服务已连接 · 场景准备中';
      label.dataset.state = status.ready || status.paused ? 'online' : 'waiting';
      $('#airportUnavailable').hidden = true;
    } catch (_) {
      if (current !== generation || !$('#airportConnection')) return;
      $('#airportConnection').textContent = '机场服务未连接';
      $('#airportConnection').dataset.state = 'offline';
      $('#airportUnavailable').hidden = false;
    } finally {
      clearTimeout(timeout);
      if (pending === request) pending = null;
    }
  }

  function mount() {
    // refreshData() may render again; preserve the iframe and its camera stream.
    if ($('#airportFrame')) return;
    $('#pageActions').className = 'page-actions';
    $('#pageActions').innerHTML = `<span id="airportConnection" role="status">正在连接机场服务…</span>
      <button class="btn" id="airportReconnect">重新连接</button>
      <button class="btn" id="airportFullscreen">全屏控制台</button>
      <a class="btn" href="/airport-console/view/" target="_blank" rel="noopener">独立窗口 ↗</a>`;
    $('#pageContent').innerHTML = `<div class="airport-frame-card">
      <div id="airportUnavailable" role="status" hidden>机场运行服务未连接。请运行项目的启动脚本；连接恢复后会自动更新。</div>
      <iframe id="airportFrame" src="/airport-console/view/" title="机场作业控制台" allow="fullscreen" allowfullscreen></iframe>
    </div>`;
    $('#airportReconnect').onclick = () => {
      $('#airportFrame').src = '/airport-console/view/';
      checkConnection();
    };
    $('#airportFullscreen').onclick = () => $('#airportFrame').requestFullscreen?.().catch(() => {});
    checkConnection();
    timer = setInterval(checkConnection, 5000);
  }

  function unmount() {
    generation++;
    clearInterval(timer);timer = null;
    pending?.abort();pending = null;
    // Removing the iframe closes its polling timer and MJPEG connection.
    $('#airportFrame')?.remove();
  }
  return {mount, unmount};
})();
