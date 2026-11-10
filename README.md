# Hetero Ops Platform

Fire × Open-RMF 异构设备作业平台。基于 `junshanxu/fire`，已同步上游更新至 `42613f4`，并增加「机场作业控制台」页面，接入当前机场三维运行服务。原平台的设备、任务、调度等页面保留。

公开仓库：<https://github.com/xueReact/hetero-ops-platform>

## 这是什么

项目由两个可独立运行的部分组成：

- **Fire 平台**：设备、任务、统一调度、运行监控和反馈接口。
- **Airport OPS**：Open-RMF + ROS 2 + Gazebo 机场场景，包含 3 台机器狗、3 架无人机和 2 台运输机器人。

机场控制台通过 `/airport-runtime/` 网关接入实时状态、相机流、任务命令、证据图片和轨迹导出。浏览器只需打开一个平台地址。

## Windows 启动

1. 启动 Docker Desktop，等待引擎就绪。
2. 双击本目录的 **`start-demo.cmd`**。
3. 打开 **http://localhost:8001**，点击导航中的 **机场作业控制台**。
   也可直接访问 **http://localhost:8001/airport-console**。

脚本优先连接本机已运行的 `8094` 机场服务。如没有运行，会构建并启动本项目自带的机场服务。第一次完整构建需下载 ROS/RMF 依赖，时间较长。需要独立运行一套机场时：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-windows.ps1 -Standalone
```

停止新项目：双击 `stop-demo.cmd`。停止脚本仅停止 `fire-integrated` 容器，不会停止独立的 `8094` 机场实例，数据卷也会保留。

## 本次合并内容

- 修复反馈接口调用 `operation_feed` 时缺失导入的问题。
- 修复原静态媒体处理使用 `os.environ` 时漏导入 `os` 的问题。
- 新增机场控制台导航、可直接访问的页面路径、连接状态、重连和全屏入口。
- 实时连接 3 台机器狗、3 架无人机、2 台运输机器人；支持联合任务、暂停/继续、围挡事件、相机视角、工单/轨迹下载和证据图片。
- 使用同一网站的 `/airport-runtime/` 代理，浏览器不需要直接访问另一端口，接口命名不与原平台冲突。
- 将当前机场升级版源码和场景资源归档在 `simulations/airport-upgrade/`，与原仓库的旧场景区分。

这是**平台页面与运行入口的集成**。原平台的电网任务和机场联合任务仍由各自后端管理，并未自动合并两套设备台账或调度策略。机场数据来自当前 Gazebo / ROS 2 / Open-RMF 实例，尚未接入实体设备。原总览中的旧机场回放入口按原样保留；实时操作使用新增的「机场作业控制台」。

## 部署方式

### 复用已有机场服务

```powershell
$env:AIRPORT_UPSTREAM = 'http://host.docker.internal:8094'
docker compose up -d --build platform
```

### Linux 服务器：独立完整运行

```bash
AIRPORT_UPSTREAM=http://airport:8080 docker compose --profile airport up -d --build
```

默认只将 `8001` 绑定到本机回环地址。公网演示时，在服务器上通过 Nginx/Caddy 配置 HTTPS、登录保护并反向代理 `127.0.0.1:8001`；相机流需要关闭代理缓冲、设置长连接超时。完整运行不能只部署到 GitHub Pages 或 Vercel 静态托管。现有 `vercel.json` 是原平台的配置，不是新增实时机场服务的部署方式。

已有兼容 ROS/RMF 镜像时可指定 `AIRPORT_RUNTIME_IMAGE=rmf-airport-sim:humble` 避免重复构建底层依赖。完整环境需要 Docker Linux containers，建议至少为 Docker 分配 8 GB 内存。两套机场同时运行会增加资源占用。

### 本地 Python 开发

```powershell
python run.py
```

要求 Python 3.10+，平台仅用标准库。默认监听 `127.0.0.1:8001`，连接 `127.0.0.1:8094`。不要与 Docker 版同时占用 `8001`。`FIRE_PORT`、`FIRE_HOST`、`AIRPORT_UPSTREAM`、`FIRE_RUNTIME_DATA_DIR` 可通过环境变量覆盖。

## 目录说明

- `platform_app/`：Fire 平台后端和机场同源网关。
- `web/`：Fire 平台页面；`/airport-console` 是实时机场入口。
- `simulations/airport-upgrade/`：当前机场场景、车队控制器、portal、网页和 Gazebo 插件。
- `compose.yml`：平台容器，以及可选的独立机场容器。
- `start-windows.ps1` / `start-demo.cmd`：Windows 一键启动入口。
- `docs/集成说明.md`：架构、接口和部署边界。
- `docs/集成验证记录.md`：实际运行验证和已知测试说明。

## 公开仓库与账号资料

仓库为公开仓库，但实时运行仍需要服务器或本地 Docker，不能仅靠 GitHub Pages 运行 Gazebo。GitHub 个人资料显示名可以设置为 `ZYYYY`；登录名仍为 `xueReact`，所以仓库地址不会改变。

## 验证与维护

```powershell
python -m unittest discover -s tests -v
docker compose ps
docker compose logs --tail 50 platform
```

检查 `/api/health`、`/api/feedback` 和 `/airport-runtime/api/status`。机场刚启动时，页面会显示「场景准备中」；服务未启动时显示断连提示，不会用录像替代实时连接。

目录与修改说明见 [docs/集成说明.md](docs/集成说明.md)。实测结果及原项目的 4 项已知测试失败见 [docs/集成验证记录.md](docs/集成验证记录.md)。
