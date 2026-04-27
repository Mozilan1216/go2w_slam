# 这个代码还没有测试过
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 路径配置
    save_data_dir = "/home/ubuntu/ros2_ws/save_data/"
    
    # ==========================================
    # 1. 启动底层硬件：Livox Mid-360 驱动
    # ==========================================
    livox_driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('livox_ros_driver2'), 'launch_ROS2', 'msg_MID360_launch.py')
        )
    )

    # ==========================================
    # 2. 启动前端 3D LIO：FAST-LIO2
    # ==========================================
    fast_lio_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('fast_lio'), 'launch', 'mapping.launch.py')
        ),
        launch_arguments={'rviz': 'false'}.items()
    )

    # ==========================================
    # 3. 启动降维：点云转 2D 激光扫描 (用于 slam_toolbox)
    # ==========================================
    pcloud_to_scan_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pcloud_to_scan',
        remappings=[
            ('cloud_in', '/cloud_registered_body'), # 订阅 FAST-LIO2 输出的点云
            ('scan', '/scan'),
        ],
        parameters=[{
            'target_frame': 'body',
            'transform_timeout': 0.01,
            'min_height': 0.2,   # 切片起始高度（避开地面噪点）
            'max_height': 1.0,   # 切片截止高度（保留墙体轮廓）
            'angle_min': -3.1415,
            'angle_max': 3.1415,
            'range_min': 0.5,
            'range_max': 30.0,
            'use_inf': True,
            'inf_epsilon': 1.0
        }]
    )

    # ==========================================
    # 4. 启动后端优化：SC-PGO (回环检测与纠偏)
    # ==========================================
    scpgo_node = Node(
        package='sc_pgo',
        executable='alaserPGO',
        name='alaserPGO',
        output='screen',
        parameters=[{
            'save_directory': save_data_dir,   # 你之前配置的目录
            'publish_tf': True,                # 必须开启，负责 map -> camera_init 的变换
            'keyframe_meter_gap': 1.0,
            'keyframe_deg_gap': 10.0,
            'sc_dist_thres': 0.2,
            'sc_max_radius': 40.0
        }],
        remappings=[
            ('/aft_mapped_to_init', '/Odometry'),
            ('/velodyne_cloud_registered_local', '/cloud_registered_body'),
        ]
    )

    # ==========================================
    # 5. 启动 2D 建图：Slam Toolbox (异步绘图模式)
    # ==========================================
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'odom_frame': 'camera_init',   # FAST-LIO 的里程计原点
            'base_frame': 'body',          # 机器人基坐标系
            'map_frame': 'map',            # 由 SC-PGO 发布的全局地图坐标系
            'publish_tf': False,           # 重要：关闭其 TF 发布，改用 SC-PGO 的 TF
            'mode': 'mapping',
            'resolution': 0.05,
            'max_laser_range': 20.0,
            'minimum_time_interval': 0.1,
            'transform_timeout': 0.5
        }]
    )

    # ==========================================
    # 6. RViz 可视化
    # ==========================================
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(get_package_share_directory('sc_pgo'), 'rviz_cfg', 'aloam_velodyne.rviz')]
    )

    return LaunchDescription([
        livox_driver_launch,
        fast_lio_launch,
        pcloud_to_scan_node,
        scpgo_node,
        slam_toolbox_node,
        rviz_node
    ])