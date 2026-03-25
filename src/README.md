## 📁 `src` 目录功能包说明

为了保持工程清晰，本工作空间将底层通信、自定义控制、传感器驱动及仿真环境进行了分离。以下是各功能包的详细说明：

### 1. 核心底盘与通信层 (Unitree)

- **`unitree_api`**: (官方) 宇树机器人底层通信核心协议与 API 接口。提供 Request/Response 基础消息封装。
- **`unitree_go`**: (官方) 宇树 Go2 机器狗专属的 ROS 2 消息类型定义。包含机器狗的 `SportModeState` (高级状态)、`LowState` (底层状态) 等关键 `.msg` 文件。
- **`unitree_ros2_example`**: (官方) 宇树提供的原始 ROS 2 示例代码库。包含基础的网卡绑定脚本 (`setup.sh`) 和基础收发示例。

### 2. 硬件抽象与控制层 (Custom)

- **`unitree_motion`**: (自定义核心包) 作为导航算法与底盘通信的桥梁 (HAL层)。
    - **向下**：通过 CycloneDDS 协议与 `unitree_api`/`unitree_go` 交互。
    - **向上**：监听标准 `/cmd_vel` 话题并转化为机器狗速度指令；读取底层运动状态并发布标准的 `/odom` 话题及 `odom -> base_link` 的 TF 坐标树。
    - *包含测试节点，可独立模拟状态发布与指令下发。*
    

### 3. 感知与传感器层 (Sensors)

- **`livox_ros_driver2`**: (外部驱动) 大疆 Livox Mid-360 激光雷达的官方 ROS 2 驱动包。负责接入雷达硬件，输出用于 3D SLAM 建图的高精度点云数据 (`CustomMsg` 或 `PointCloud2`)。

### 4. 仿真环境层 (Simulation)

- **`wpr_simulation2`**: (仿真) Waterplus 机器人的 ROS 2 仿真包。包含前期学习与算法验证所需的虚拟地图和仿真环境模型。

### 5. 机器人描述与模型层 (Robot Description)

- **`GO2_URDF`**: (描述包) 包含 Unitree Go2 机器狗的 3D 运动学模型文件（URDF/XACRO）。它的核心作用是在 RViz 中可视化机器狗的真实姿态，并发布从机器狗中心 (`base_link`) 到各个腿部关节以及外挂传感器（Mid-360、D435i）的静态 TF 坐标树。这是确保雷达点云和相机画面能够准确对齐到底盘的物理基石。

### 6. 建图与导航层 (SLAM & Navigation)

- **`slam_pkg`**: (自定义包) 专属的建图配置中心。存放用于真实园区场景的 SLAM 算法参数与 Launch 文件（如 FAST-LIO 或 RTAB-Map）。它负责将底层 Odom、雷达点云与视觉数据进行多传感器融合，构建出用于全局路径规划的三维/二维环境地图。
- **`pointcloud_to_laserscan`**: (数据转换包) 关键的算力降维工具。专门用于将 Mid-360 输出的稠密 3D 点云 (`PointCloud2`) 实时切片并投影为 2D 激光扫描数据 (`LaserScan`)。这能大幅降低避障计算量，为后续的代价地图提供轻量级的高频数据源。
- **`nav_pkg`**: (自定义包) 核心的语义导航控制大脑。包含完整的 ROS 2 Nav2 框架配置（代价地图参数、路径规划器、控制器与行为树）。它将主导机器狗在已知地图中，顺利完成从园区食堂到1号楼的全局路径规划、动态避障以及最终的语义目标点抵达。