import os
from launch import LaunchDescription
from launch_ros.actions import Node, SetParameter
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 强制开启仿真时间
    use_sim_time = SetParameter(name='use_sim_time', value=True)

    # 1. 启动 FAST-LIO2
    fast_lio_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('fast_lio'), 'launch', 'mapping.launch.py'
        )),
        launch_arguments={'rviz': 'false'}.items()
    )

    # 2. 启动数据清洗节点
    filter_node = Node(
        package='slam_pkg',
        executable='point_to_scan_filter.py',
        name='point_to_scan_filter',
        output='screen'
    )

    # 3. 启动 SLAM Toolbox
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'odom_frame': 'camera_init',
            'base_frame': 'body',
            'scan_topic': '/scan',
            'mode': 'mapping',
            'resolution': 0.1,           # 10cm分辨率，最适合园区导航
            'transform_timeout': 1.0,    # 容忍计算延迟
            'minimum_time_interval': 0.2 # 🌟 强制降低处理频率，缓解 CPU 压力
        }]
    )

    # 4. 可视化
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(get_package_share_directory('slam_pkg'), 'rviz', 'fastlio2_slam.rviz')]
    )

    return LaunchDescription([
        use_sim_time,
        fast_lio_launch,
        filter_node,
        slam_toolbox_node,
        rviz_node
    ])