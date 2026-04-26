import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, SetParameter
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    rviz_config_path = os.path.join(
        get_package_share_directory('slam_pkg'), 'rviz', 'octomap_box.rviz'
    )
    
    global_sim_time = SetParameter(name='use_sim_time', value=True)

    # ==========================================
    # 1. 3D 大脑：FAST-LIO2
    # ==========================================
    fast_lio_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('fast_lio'), 'launch', 'mapping.launch.py')
        ),
        launch_arguments={'rviz': 'false', 'use_sim_time': 'true'}.items()
    )

    # ==========================================
    # 🌟 2. 物理正骨节点：凭空创造一个绝对水平的 level_map，并把歪掉的 camera_init 挂在下面
    # ==========================================
    tilt_correction_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='tilt_correction',
        # arguments 顺序: x, y, z, yaw, pitch, roll, parent_frame, child_frame
        # 这里的 -0.15 就是我们要试的 Pitch (俯仰) 角度，约等于低头 8.5 度。
        arguments=['0', '0', '0', '0', '0.25', '0.0', 'level_map', 'camera_init']
    )

    # ==========================================
    # 3. 3D 空间建造者：OctoMap Server
    # ==========================================
    octomap_server_node = Node(
        package='octomap_server',
        executable='octomap_server_node',
        name='octomap_server',
        output='screen',
        remappings=[
            ('cloud_in', '/cloud_registered_body') 
        ],
        parameters=[{
            'use_sim_time': True,          
            # 🌟 核心：认准新地基！
            'frame_id': 'level_map',       
            'base_frame_id': 'body',       
            'resolution': 0.10,            
            'sensor_model/max_range': 8, 
            
            'sensor_model/hit': 0.7,
            'sensor_model/miss': 0.4,
            'sensor_model/min': 0.12,
            'sensor_model/max': 0.97,

            'occupancy_min_z': 0.4,   
            'occupancy_max_z': 1.2,   
            
            'pointcloud_min_z': 0.0,
            'pointcloud_max_z': 3.0,
        }]
    )

    # ==========================================
    # 4. 启动 RViz2
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
        tilt_correction_node,   # 🌟 必须在这里把正骨节点加进去！
        octomap_server_node, 
        rviz_node
    ])