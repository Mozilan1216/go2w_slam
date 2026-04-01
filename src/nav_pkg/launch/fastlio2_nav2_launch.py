import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # ==========================================
    # 1. 路径配置 (请核对你的实际文件名)
    # ==========================================
    nav_pkg_dir = '/home/unitree/Workspace/ROS2/ros2_ws/src/nav_pkg'
    # 你的自定义参数文件
    nav2_params_path = os.path.join(nav_pkg_dir, 'config', 'nav2_params.yaml')
    # 你之前保存的地图文件 (请确保文件名正确)
    default_map_path = '/home/unitree/Workspace/ROS2/ros2_ws/src/maps/map_20260331_1125.yaml'
    # 你的 RViz 配置文件绝对路径
    rviz_config_path = '/home/unitree/Workspace/ROS2/ros2_ws/src/nav_pkg/rviz/fastlio2_nav.rviz'



    # 官方包路径获取
    livox_driver_dir = get_package_share_directory('livox_ros_driver2')
    fast_lio_dir = get_package_share_directory('fast_lio')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # ==========================================
    # 2. 节点定义
    # ==========================================
    
    # (A) 底层驱动：Livox Mid-360 (第 0 秒启动)
    livox_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(livox_driver_dir, 'launch_ROS2', 'msg_MID360_launch.py')
        )
    )

    # (B) 3D 定位：FAST-LIO2 (第 10 秒启动，等雷达电机稳定)
    fast_lio = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(fast_lio_dir, 'launch', 'mapping.launch.py')
        ),
        # 添加下面这一行，强行关掉 FAST-LIO2 自带的 RViz！
        launch_arguments={'rviz': 'false'}.items()
    )

    # (C) 降维切片：点云转 2D 激光 (第 13 秒启动)
    pctls_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[('cloud_in', '/cloud_registered_body'), ('scan', '/scan')],
        parameters=[{
            'target_frame': 'body',
            'transform_tolerance': 0.01,
            'min_height': -0.1,
            'max_height': 0.3,
            'angle_min': -3.14159,
            'angle_max': 3.14159,
            'range_max': 15.0,
            'use_inf': True,
        }],
        output='screen'
    )

    # (D) 导航核心：Nav2 Bringup (第 15 秒启动，确保 TF 树已建立)
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': default_map_path,
            'use_sim_time': 'False',
            'params_file': nav2_params_path,
            'autostart': 'True',
            # 👇👇 必须加上这行，强制加载我们的“高智商”剧本！ 👇👇
            'default_bt_xml_filename': '/home/unitree/Workspace/ROS2/ros2_ws/src/nav_pkg/config/smart_nav.xml'
        }.items()
    )

    # (E) 可视化：RViz2 (带导航配置)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_path],
        output='screen'
    )

    # (F) 运动控制桥接：翻译 cmd_vel 给 Go2 底层
    cmd_vel_translator_node = Node(
        package='unitree_motion',
        executable='cmd_vel_translator', # 确保名字和你的 CMakeLists.txt 里一致
        name='cmd_vel_translator',
        output='screen'
    )

    # ==========================================
    # 3. 编排启动时序 (关键！)
    # ==========================================
    return LaunchDescription([
        # 0s: 启动雷达驱动
        livox_driver,

        # 6s: 启动 FAST-LIO2 定位
        TimerAction(period=6.0, actions=[fast_lio]),

        # 6s: 启动点云切片
        TimerAction(period=6.0, actions=[pctls_node]),

        # 10s: 启动 Nav2 导航和 RViz
        TimerAction(period=10.0, actions=[nav2_bringup, rviz_node, cmd_vel_translator_node])
    ])