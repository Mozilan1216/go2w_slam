import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # ==========================================
    # 1. 路径配置 
    # ==========================================
    workspace_dir = '/home/ubuntu/ros2_ws/src'
    nav_pkg_dir = os.path.join(workspace_dir, 'nav_pkg')

    # Nav2 2D 栅格地图和配置 (供路径规划避障使用)
    nav2_params_path = os.path.join(nav_pkg_dir, 'config', 'nav2_open3d_params.yaml')
    default_2d_map_path = os.path.join(workspace_dir, 'maps', 'map_20260413_0820.yaml')
    rviz_config_path = os.path.join(nav_pkg_dir, 'rviz', 'fastlio2_nav.rviz') 

    # 官方及自定义包路径获取
    livox_driver_dir = get_package_share_directory('livox_ros_driver2')
    fast_lio_dir = get_package_share_directory('fast_lio')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    
    # 新增：获取深瞳 3D 重定位包的路径
    open3d_loc_dir = get_package_share_directory('open3d_loc') 

    # ==========================================
    # 2. 节点定义
    # ==========================================
    
    # (A) 底层驱动：Livox Mid-360
    livox_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(livox_driver_dir, 'launch_ROS2', 'msg_MID360_launch.py')
        )
    )

    # (B) 3D 里程计：FAST-LIO2 (提供 odom -> body 的局部里程计和实时去畸变点云)
    fast_lio = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(fast_lio_dir, 'launch', 'mapping.launch.py')
        ),
        launch_arguments={'rviz': 'false'}.items()
    )

    # (C) 降维切片：点云转 2D 激光 (提供 /scan 供 Nav2 避障)
    pctls_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[('cloud_in', '/cloud_registered_body'), ('scan', '/scan')],
        parameters=[{
            'target_frame': 'body',
            'transform_tolerance': 0.01,
            'min_height': 0.15,
            'max_height': 0.5,
            'angle_min': -3.14159,
            'angle_max': 3.14159,
            'range_max': 15.0,
            'use_inf': True,
        }],
        output='screen'
    )

    # (D) 新增：3D 全局重定位 (提供 map -> odom 的绝对定位坐标转换)
    open3d_localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            # 指向你刚才千辛万苦调通的 launch 文件
            os.path.join(open3d_loc_dir, 'launch', 'localization_3d_g1.launch.py')
        )
    )

    # (E) 导航核心：Nav2 Bringup
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': default_2d_map_path,
            'use_sim_time': 'False',
            'params_file': nav2_params_path,
            'autostart': 'True',
        }.items()
    )

    # (F) 可视化：RViz2
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_path],
        output='screen'
    )

    # (G) 运动控制桥接：翻译 cmd_vel 给 Go2 底层
    cmd_vel_translator_node = Node(
        package='unitree_motion',
        executable='cmd_vel_translator',
        name='cmd_vel_translator',
        output='screen'
    )

    # ==========================================
    # 3. 编排启动时序 (极度关键)
    # ==========================================
    return LaunchDescription([
        # 0s: 启动雷达驱动
        livox_driver,

        # 6s: 启动 FAST-LIO2 和点云切片 (等待雷达电机稳定)
        TimerAction(period=6.0, actions=[fast_lio, pctls_node]),

        # 10s: 启动全局 3D 重定位 (等待 FAST-LIO2 开始输出高频里程计 /Odometry)
        TimerAction(period=10.0, actions=[open3d_localization]),

        # 14s: 启动 Nav2 导航、RViz、底层运动控制 (等待 map -> odom 的 TF 树建立完毕)
        TimerAction(period=14.0, actions=[nav2_bringup, rviz_node, cmd_vel_translator_node])
    ])