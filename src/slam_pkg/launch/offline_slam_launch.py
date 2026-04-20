import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, SetParameter
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    rviz_config_path = os.path.join(
        get_package_share_directory('slam_pkg'),
        'rviz',
        'fastlio2_slam.rviz'
    )

    # 🌟 核心魔法：全局强制所有节点使用 Bag 的虚拟时间！
    global_sim_time = SetParameter(name='use_sim_time', value=True)

    # ==========================================
    # 1. 硬件驱动 (已移除) —— 因为由 ros2 bag play 提供数据
    # ==========================================

    # ==========================================
    # 2. 启动 3D 核心：FAST-LIO2 (处理 Bag 里的雷达裸数据)
    # ==========================================
    fast_lio_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('fast_lio'), 'launch', 'mapping.launch.py')
        ),
        launch_arguments={
            'rviz': 'false',
            'use_sim_time': 'true' # 强制 FAST-LIO2 进入历史时间
        }.items()
    )

    # ==========================================
    # 3. 启动降维打击：点云转 2D 激光扫描 (LaserScan)
    # ==========================================
    pctls_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[
            ('cloud_in', '/cloud_registered_body'), 
            ('scan', '/scan')                       
        ],
        parameters=[{
            'target_frame': 'body',     
            'transform_tolerance': 0.05,
            'min_height': 0.5,         
            'max_height': 1.5,         
            'angle_min': -3.14159,
            'angle_max': 3.14159,
            'angle_increment': 0.0087,
            'scan_time': 0.1,
            'range_min': 0.5,           
            'range_max': 15.0,          
            'use_inf': True,
            # 🌟 加入这几行核心魔法：强行把发布出去的 /scan 改为 Reliable！
            'qos_overrides': {
                '/scan': {
                    'publisher': {
                        'reliability': 'reliable'
                    }
                }
            }
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
            'odom_frame': 'camera_init',   
            'base_frame': 'body',          
            'map_frame': 'map',            
            'resolution': 0.05,            
            'max_laser_range': 20.0,
            'transform_timeout': 0.5,       
            
            # ==========================================
            # 🌟 暴力闭环核心组 (强行拉扯纠正地图)
            # ==========================================
            'do_loop_closing': True,
            
            # 哪怕当前算出来离起点有 15 米远，也要去尝试匹配闭环！(默认只有几米)
            'loop_search_maximum_distance': 15.0,  
            
            # 降低闭环的相似度门槛，更容易触发吸合
            'loop_match_minimum_chain_size': 2,    
            'loop_match_maximum_variance_coarse': 10.0, 
            'loop_match_minimum_response_coarse': 0.4,
            'loop_match_minimum_response_fine': 0.6,
            
            # 增大对 3D 完美里程计的信任，抑制 2D 瞎匹配
            'distance_variance_penalty': 0.5,
            'angle_variance_penalty': 0.5,
        }]
    )

    # ==========================================
    # 5. 启动 RViz 可视化
    # ==========================================
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_path],
        output='screen'
    )

    return LaunchDescription([
        global_sim_time,
        fast_lio_launch,
        pctls_node, 
        slam_toolbox_node, 
        rviz_node
    ])