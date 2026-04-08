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
    # 2. 启动 3D 核心：FAST-LIO2
    # ==========================================
    fast_lio_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('fast_lio'), 'launch', 'mapping.launch.py')
        ),
        # 强行关掉 FAST-LIO2 自带的 RViz
        launch_arguments={'rviz': 'false'}.items()
    )

    # ==========================================
    # 3. 启动降维打击：点云转 2D 激光扫描 (LaserScan)
    # ==========================================
    pctls_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[
            ('cloud_in', '/cloud_registered_body'), # 订阅 FAST-LIO2 洗干净的点云
            ('scan', '/scan')                       # 输出标准的 2D 激光数据
        ],
        parameters=[{
            'target_frame': 'body',     # 锁定在机器狗躯干
            'transform_tolerance': 0.01,
            'min_height': -0.1,         # 狗背往下 10cm (避开地板)
            'max_height': 0.3,          # 狗背往上 30cm (抓取墙体)
            'angle_min': -3.14159,
            'angle_max': 3.14159,
            'angle_increment': 0.0087,
            'scan_time': 0.1,
            'range_min': 0.5,           # 忽略狗自己身上的反光
            'range_max': 15.0,          # 视距 15 米
            'use_inf': True,
        }],
        output='screen'
    )

    # ==========================================
    # 4. 启动 2D 终极大 Boss：SLAM Toolbox
    # ==========================================
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': False,         # 强制使用真实系统时间，绝不能错！
            'odom_frame': 'camera_init',   # 完美对接 FAST-LIO2 的里程计原点
            'base_frame': 'body',          # 机器狗自身坐标系
            'map_frame': 'map',            # 最终生成的 2D 地图坐标系
            'resolution': 0.05,            # 地图精度 5cm
            'max_laser_range': 15.0,
            'transform_timeout': 0.5       # 给 TF 树 0.5 秒的容错等待时间，防止乱丢包！
        }]
    )

    # ==========================================
    # 5. 启动rviz可视化
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
        # 启动 2D 转换和 SLAM Toolbox
        TimerAction(period=6.0, actions=[pctls_node, slam_toolbox_node, rviz_node])
    ])