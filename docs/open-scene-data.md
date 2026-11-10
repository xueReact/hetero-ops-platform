# 可复用路网与空间数据（2026-11-06 核验）

调度只使用一张场区图。设备位置、海拔、通道、楼梯、碎石坡和规划路线都画在这张图上，路线按当前设备位置和地形重算。下面的 OpenDRIVE 与 OSM 文件是离线样例，不作为可切换的第二张地图。

| 资源 | 包含内容 | 适用场景 |
| --- | --- | --- |
| [esmini / OpenDRIVE 示例](https://github.com/esmini/esmini/tree/master/resources/xodr) | 参考线几何、车道、连接关系、高程多项式；不同文件完整度不同 | 优先评估三维道路、路口和高程仿真 |
| [OSMnx 示例](https://github.com/gboeing/osmnx-examples) | 从 OSM 提取步行/驾车路网、建筑轮廓、路由；支持接入高程 | 后续将仿真场景对齐真实地理坐标 |

已随项目保存的源文件在 `web/assets/networks/`：`esmini-curves-elevation.xodr`（一条带 15 段高程的弯道）、`multi_intersections.xodr`（路口网络）、`fabriksgatan.xodr`（城市道路），以及 OSMnx 仓库里的慕尼黑 OSM XML 小样例。OSM 图保留 OpenStreetMap 署名。高程样例不是完整山地场景；路口样例的高程系数基本为零，高度主要看弯道那一条。

具体样本：
- [multi_intersections.xodr](https://github.com/esmini/esmini/blob/master/resources/xodr/multi_intersections.xodr)：路口网络。
- [curves_elevation.xodr](https://github.com/esmini/esmini/blob/master/resources/xodr/curves_elevation.xodr)：弯道与高程曲线。
- [fabriksgatan.xodr](https://github.com/esmini/esmini/blob/master/resources/xodr/fabriksgatan.xodr)：城市道路样本。

现场画面里的灰路、海拔和绿色规划路线来自同一张场区图。设备过不去的任务会改派到过得去的平台，并在这张图上画出对应路线。这些样例不含建筑和空域，不能单独当成完整三维现场。

许可：esmini 仓库 [MPL-2.0](https://github.com/esmini/esmini/blob/master/LICENSE)。第三方模型或素材须分别核验许可。OSMnx 是工具，不能把其软件许可当作 OSM 数据许可；使用 OSM 数据应遵守 [ODbL 与署名要求](https://www.openstreetmap.org/copyright)。

## 当前成本假设

所有 SOC、容量、运动轨迹、耗时与耗电系数均为仿真参数。1 度 = 1 kWh。机器人电池容量 1.5kWh，机器狗 0.6kWh，无人机 0.3kWh；按相同的仿真 SOC 计算遥测电量和任务电耗。模型系数随进度产生有限波动，滚动修正剩余耗电预测。任务成本累计所有派发与故障返厂记录，避免重派后丢失已用成本。

## 缺陷图片

[Bianka Passos 路面裂缝与坑洼数据集](https://github.com/biankatpas/Cracks-and-Potholes-in-Road-Images-Dataset)，MIT，保留作者及许可。图片是公开样例，没有执行本地 YOLO 推理，也没有把示例图关联为仿真事件的真实现场证据。
