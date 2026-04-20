import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, SetParameter
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    rviz_config_path = os.path.join(
        get_package_share_directory('slam_pkg'), 'rviz', 'fastlio2_slam.rviz'
    )
    global_sim_time = SetParameter(name='use_sim_time', value=True)

    # ==========================================
    # 1. 3D 大脑：FAST-LIO2 (提供绝不漂移的完美位姿)
    # ==========================================
    fast_lio_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('fast_lio'), 'launch', 'mapping.launch.py')
        ),
        launch_arguments={'rviz': 'false', 'use_sim_time': 'true'}.items()
    )

    # ==========================================
    # 2. 相对高度切片刀：永远跟着机器狗的胸口切！
    # ==========================================
    pctls_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[('cloud_in', '/cloud_registered_body'), ('scan', '/scan')],
        parameters=[{
            'use_sim_time': True,
            'target_frame': 'body',     # 🌟 核心：绑定在机器狗身上！
            'transform_tolerance': 0.05,
            
            # 🌟 核心动态高度：从狗背上方 0.2米 切到 1.5米。
            # 这样无论狗怎么上下楼梯，切割面永远平行于狗的身体，完美抓取实体墙壁！
            'min_height': 0.2,          
            'max_height': 1.5,          
            'angle_min': -3.14159,
            'angle_max': 3.14159,
            'angle_increment': 0.0087,
            'scan_time': 0.1,
            'range_min': 0.5,
            'range_max': 20.0,
            'use_inf': True,
            'qos_overrides': {'/scan': {'publisher': {'reliability': 'reliable'}}}
        }],
        output='screen'
    )

    # ==========================================
    # 3. 2D 拼图工：SLAM Toolbox (极度信任 3D Odometry)
    # ==========================================
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'odom_frame': 'camera_init',
            'base_frame': 'body',
            'map_frame': 'map',
            'resolution': 0.05,
            'max_laser_range': 20.0,
            
            # 因为数据已经被切片刀清理得极其干净（去除了杂草和台阶），
            # 加上 FAST-LIO2 的完美辅助，这次直接加上暴力吸合参数！
            'do_loop_closing': True,
            'loop_search_maximum_distance': 15.0,
            'loop_match_minimum_chain_size': 2,
            
            # 🌟 提高惩罚，让它乖乖听 FAST-LIO2 的话，不再自己瞎漂移
            'distance_variance_penalty': 0.5,
            'angle_variance_penalty': 0.5,
        }]
    )

    rviz_node = Node(
        package='rviz2', executable='rviz2', name='rviz2',
        arguments=['-d', rviz_config_path], output='screen'
    )

    return LaunchDescription([
        global_sim_time, fast_lio_launch, pctls_node, slam_toolbox_node, rviz_node
    ])