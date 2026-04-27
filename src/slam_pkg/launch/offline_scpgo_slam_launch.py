import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, SetParameter
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 路径配置
    save_data_dir = "/home/ubuntu/ros2_ws/save_data/"
    
    # 🌟 核心魔法：强制全局使用仿真时间 (处理 Bag 数据的关键)
    global_sim_time = SetParameter(name='use_sim_time', value=True)

    # ==========================================
    # 1. 启动 3D 核心：FAST-LIO2 (前端)
    # ==========================================
    fast_lio_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('fast_lio'), 'launch', 'mapping.launch.py')
        ),
        launch_arguments={
            'rviz': 'false',
            'use_sim_time': 'true'
        }.items()
    )

    # ==========================================
    # 2. 启动降维打击：点云转 2D 激光扫描 (LaserScan)
    # ==========================================
    pcloud_to_scan_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pcloud_to_scan',
        remappings=[
            ('cloud_in', '/cloud_registered_body'),
            ('scan', '/scan'),
        ],
        parameters=[{
            'target_frame': 'body',
            'min_height': 0.2,   # 过滤高度：切掉地面
            'max_height': 1.0,   # 过滤高度：保留墙体
            'angle_min': -3.1415,
            'angle_max': 3.1415,
            'range_min': 0.5,
            'range_max': 30.0,
            'use_inf': True
        }]
    )

    # ==========================================
    # 3. 启动后端优化：SC-PGO (回环检测与 TF 纠偏)
    # ==========================================
    scpgo_node = Node(
        package='sc_pgo',
        executable='alaserPGO',
        name='alaserPGO',
        output='screen',
        parameters=[{
            'save_directory': save_data_dir,
            'publish_tf': True,                # 🌟 由 SC-PGO 负责发布 map -> camera_init
            'keyframe_meter_gap': 1.0,
            'keyframe_deg_gap': 10.0,
            'sc_dist_thres': 0.2,
            'sc_max_radius': 40.0,
            'use_sim_time': True
        }],
        remappings=[
            ('/aft_mapped_to_init', '/Odometry'),             #
            ('/velodyne_cloud_registered_local', '/cloud_registered_body'), #
        ]
    )

    # ==========================================
    # 4. 启动 2D 建图：Slam Toolbox (异步模式)
    # ==========================================
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'odom_frame': 'camera_init',   # 对接 FAST-LIO 的里程计坐标系
            'base_frame': 'body',          # 机器狗自身坐标系
            'map_frame': 'map',
            
            # 🌟 关键：关闭自身的 TF 发布，避免与 SC-PGO 冲突
            'publish_tf': False,           
            
            'mode': 'mapping',
            'resolution': 0.05,
            'max_laser_range': 20.0,
            'transform_timeout': 0.5,
            'do_loop_closing': True,       # 开启 slam_toolbox 自身的 2D 闭环辅助
        }]
    )

    # ==========================================
    # 5. RViz 可视化
    # ==========================================
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        # 使用你之前的配置文件路径
        arguments=['-d', os.path.join(get_package_share_directory('slam_pkg'), 'rviz', 'fastlio2_slam.rviz')]
    )

    return LaunchDescription([
        global_sim_time,
        fast_lio_launch,
        pcloud_to_scan_node,
        scpgo_node,
        slam_toolbox_node,
        rviz_node
    ])