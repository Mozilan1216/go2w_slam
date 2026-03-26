import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.actions import IncludeLaunchDescription, TimerAction, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    
    # 1.1 雷达驱动节点 (Mid-360)
    livox_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('livox_ros_driver2'), 
                         'launch_ROS2', 'rviz_MID360_launch.py')
        ),
    )

    # 1.2 3D转2D节点 (将雷达点云压扁成单线激光供2D SLAM使用)
    pc_to_ls = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pc_to_ls',
        parameters=[{
            'target_frame': 'livox_frame', 
            'transform_tolerance': 0.1,    
            'min_height': -0.05,
            'max_height': 0.5,              
            'angle_min': -3.14159,
            'angle_max': 3.14159,
            'range_min': 0.3,
            'range_max': 20.0,
            'use_inf': True,
        }],
        remappings=[('/cloud_in', '/livox/lidar'), ('/scan', '/scan')]
    )
    
    # 2.1 状态上报与 TF 树广播节点 (提供 odom -> base_link)
    unitree_odom_tf_node = Node(
        package='unitree_motion',
        executable='odom_tf_publisher',
        name='odom_tf_publisher',
        output='screen'
    )
    
    # 2.2 速度指令转换节点 (接收 /cmd_vel 并控制底盘)
    unitree_cmd_vel_node = Node(
        package='unitree_motion',
        executable='cmd_vel_translator',
        name='cmd_vel_translator',
        output='screen'
    )
    
    # 2.3 静态 TF 补丁 (机器人本体 base_link 到雷达 livox_frame)
    static_tf_base_lidar = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0.2', '0', '0', '0', 'base_link', 'livox_frame']
    )
    
    # 3. slam_toolbox 异步建图节点
    slam_cmd = Node(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        name='slam_toolbox',
        parameters=[{
            "use_sim_time": False,
            "base_frame": "base_link",    
            "odom_frame": "odom", 
            "map_frame": "map",
            "scan_topic": "/scan",
            "mode": "mapping",
            "use_scan_matching": True,     
            "use_scan_barycenter": True,
            "minimum_travel_distance": 0.1, 
            "minimum_travel_heading": 0.1,
            "scan_matching_threshold": 0.15,
            "map_update_interval": 1.0,
            "resolution": 0.05,
            "max_laser_range": 20.0,          
        }]
    )

    # 4. 启动我们刚刚写的语音接口节点
    voice_node = Node(
        package='slam_pkg',
        executable='semantic_voice_node.py',
        name='semantic_voice_node',
        output='screen'
    )

    # 5. 延迟 3 秒后，通过终端命令向 /voice_cmd 话题发送一条消息
    announce_mapping = TimerAction(
        period=3.0,
        actions=[
            ExecuteProcess(
                cmd=['ros2', 'topic', 'pub', '--once', '/voice_cmd', 'std_msgs/msg/String', '{data: "开始建图"}'],
                output='screen'
            )
        ]
    )

    return LaunchDescription([
        livox_driver,
        pc_to_ls,
        unitree_odom_tf_node,
        unitree_cmd_vel_node,
        static_tf_base_lidar,
        slam_cmd,
    ])