import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 你的 RViz 配置文件绝对路径
    rviz_config_path = os.path.join(
        get_package_share_directory('slam_pkg'),
        'rviz',
        'fastlio2_slam.rviz'
    )
    
    # ==========================================
    # 1. 启动底层硬件：Livox Mid-360 驱动
    # ==========================================
    livox_driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('livox_ros_driver2'), 'launch_ROS2', 'msg_MID360_launch.py')
        )
    )

    # ==========================================
    # 2. 启动 3D 核心：FAST-LIO2 (提供绝佳的 3D 点云与里程计)
    # ==========================================
    fast_lio_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('fast_lio'), 'launch', 'mapping.launch.py')
        ),
        # 强行关掉 FAST-LIO2 自带的 RViz
        launch_arguments={'rviz': 'false'}.items()
    )

    # ==========================================
    # 3. 启动 3D 转 2D 投影神器：OctoMap Server
    # ==========================================
    octomap_node = Node(
        package='octomap_server',
        executable='octomap_server_node',
        name='octomap_server',
        output='screen',
        remappings=[
            # 订阅 FAST-LIO2 去畸变后的全局点云
            ('cloud_in', '/cloud_registered_body'), 
            # OctoMap 默认输出的 2D 栅格地图话题是 /projected_map，如果你习惯用 /map，可以在这里映射
            # ('projected_map', '/map') 
        ],
        parameters=[{
            # --- 基础框架 ---
            'frame_id': 'camera_init',     # 全局静态坐标系（跟随 FAST-LIO2）
            'base_frame_id': 'body',       # 机器狗自身坐标系
            'resolution': 0.05,            # 地图分辨率 (5cm，与 Nav2 代价图保持一致)
            
            # --- 传感器与射线追踪 ---
            'sensor_model/max_range': 10.0, # 射线追踪最大距离。太远会吃满 CPU，15米足够铺开校园道路了
            'sensor_model/hit': 0.85,       # 击中障碍物的概率增加步长
            'sensor_model/miss': 0.35,      # 穿透空城区域的概率减少步长（动态剔除移动的人影）
            
            # --- 核心：高度裁剪与投影 ---
            # 这里的 Z 轴是在 frame_id (camera_init) 坐标系下的绝对高度
            # 假设起步时狗的雷达高度是 0，向下切掉地板，向上限制高度
            'occupancy_min_z': 0.15,       # 剔除地面噪声：只保留绝对高度高于 15cm 的点
            'occupancy_max_z': 0.70,        # 剔除高空树枝：只保留绝对高度低于 1.5m 的点
            
            # 点云输入的高低过滤（避免把二楼的墙壁算进来）
            'pointcloud_min_z': 0.0,
            'pointcloud_max_z': 1.0,
        }]
    )

    # ==========================================
    # 4. 启动 RViz 可视化
    # ==========================================
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_path],
        output='screen'
    )

    # ==========================================
    # 编排启动顺序 (加入延迟，让硬件先飞一会)
    # ==========================================
    return LaunchDescription([
        livox_driver_launch,
        # 延迟 6.0 秒启动 FAST-LIO，等雷达初始化完毕
        TimerAction(period=6.0, actions=[fast_lio_launch]),
        # 再延迟 2.0 秒启动 OctoMap 和 RViz，确保点云已经开始发布
        TimerAction(period=8.0, actions=[octomap_node, rviz_node])
    ])