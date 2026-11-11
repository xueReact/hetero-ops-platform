# Hetero Ops Platform

Fire × Open-RMF 异构作业平台。项目、设备台账、机场任务和运行结果共用业务数据；机场场景由 ROS 2 / Open-RMF / Gazebo 持续运行。

仓库：<https://github.com/xueReact/hetero-ops-platform>。上游平台：`junshanxu/fire@42613f4`。

## 快速启动

Windows：启动 Docker Desktop，等待引擎就绪，然后双击 **start-demo.cmd**。

- 平台：<http://localhost:8001>
- 机场控制台：<http://localhost:8001/airport-console>
- 停止：双击 **stop-demo.cmd**，数据卷保留。

也可以在项目目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-windows.ps1
```

脚本统一启动项目自带的 21 台设备机场服务，不再自动复用旧 8094 场景。首次构建会下载 ROS/RMF 依赖。若本机已有兼容基础镜像 `rmf-airport-sim:humble`，脚本会复用底层依赖。场景初始化及车队发现通常还需约 1–2 分钟，以页面“系统就绪”为准。

## 如何演示

1. 选择“杭州萧山机场 · 航站楼作业项目”。
2. 设备管理中核对 **28 个资源：7 名人员、7 台机器人、7 台机器狗、7 架无人机**。编辑资源名称后，控制台同步更新。
3. 机场控制台可切换全景、设备相机、二维路网、区域地图、卫星图。绿色动态标记和“正在运行”显示实际运动设备。
4. 点击“启动联合任务”，或在任务管理创建机场工单、选择 A–G 作业区后点击“启动”。计划时间仅作记录，当前需要手动启动。
5. 观察机器狗初检 → 无人机到点复核 → 运输车配送 → 双方驻留交接 → 归位。每次最多并行三个作业区，七区分批完成。
6. 任务管理显示进度、逐区结果、相机证据；控制台可导出工单和轨迹。页面刷新保留工单。
7. 可操作暂停/继续和围挡事件。机场任务结束前禁止切换项目，避免同一编组被两个调度入口占用。

“新增项目”保存项目档案；新地点需配置地图、导航图和运行服务后才能执行任务。不会把当前机场自动当作任意新项目的场景。

## 地图与运行边界

- **三维**：保留 Open-RMF 航站楼，扩展七区、21 台 Gazebo 设备及七个人员工位标记。名称取自平台台账；模型不是对应厂商硬件的精确数字孪生。
- **二维**：使用与 RMF 相同的导航顶点/边，显示实际位置、规划路径、轨迹和封路事件，单位为米。
- **区域地图**：定位杭州萧山机场，道路使用 OpenStreetMap（不可达时切换 Esri World Street Map），卫星使用 Esri World Imagery 在线瓦片。当前航站楼没有与萧山机场测绘坐标配准，因此不把室内设备投影成虚假的卫星定位。
- **人员**：七人名册与配置工位，尚未接入人员定位或电子签收终端。
- **任务**：告警由场景条件触发；空中复核是实际到点/驻留检查，不是 AI 故障识别。交接基于实际位姿和连续驻留，没有机械臂搬运。
- **运行**：当前是电脑三维仿真，尚未接入实体机器人。GitHub Pages 不能运行 Gazebo / ROS 2。

## Linux / 服务器部署

```bash
docker compose --profile airport up -d --build
docker compose ps
```

建议 Docker 至少 8 GB 内存，软件渲染持续使用 CPU。默认只暴露 `127.0.0.1:8001`；公网部署需配置 HTTPS、身份验证和反向代理，相机流需关闭代理缓冲并设置长连接超时。仓库未自动部署公网服务。

兼容基础镜像可由 `AIRPORT_RUNTIME_IMAGE=rmf-airport-sim:humble` 指定。默认完整构建使用 Dockerfile 固定的 Open-RMF 版本；本次本机验证复用了已安装的 ROS/RMF 基础镜像。

## 开发与数据

```powershell
python run.py
python -m unittest discover -s tests -p "test_*airport*.py" -v
```

平台要求 Python 3.10+，仅用标准库。单独运行 `run.py` 时，通过 `AIRPORT_UPSTREAM` 指定兼容机场服务；默认仍是历史开发地址 `http://127.0.0.1:8094`。Compose 自动覆盖为 `http://airport:8080`。不要与 Docker 同时占用 8001。

| 文件 / 目录 | 用途 |
| --- | --- |
| `platform_app/services/project_service.py` | 项目与资源档案 |
| `platform_app/services/airport_service.py` | 统一台账、任务关联、结果保存 |
| `sample_data/resources.json` | 28 个资源的初始台账 |
| `web/` | 项目、设备、任务管理界面 |
| `simulations/airport-upgrade/` | 场景、车队、协作流程及控制台 |
| `compose.yml` | 服务与持久化数据卷 |
| `docs/集成说明.md` | 接口、扩展方法及来源 |
| `docs/集成验证记录.md` | 本轮实测记录 |

`platform-data` 保存项目、资源档案、任务和机场任务快照；机场证据、报告和事件各有独立卷。运行服务重启后未完成旧工单标为异常，检查设备后新建工单。日常停止不要使用 `docker compose down -v`，它会删除数据卷。
