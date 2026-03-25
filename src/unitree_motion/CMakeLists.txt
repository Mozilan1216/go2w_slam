cmake_minimum_required(VERSION 3.5)
project(unitree_motion)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# 这是我们刚才为了兼容宇树底层代码，新增的 C++20 标准设置
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 20)
endif()

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(unitree_api REQUIRED)
find_package(unitree_go REQUIRED)

# 包含所有相关的头文件目录
include_directories(
  include
  include/common
  include/nlohmann
)

# 1. 编译状态上报与 TF 发布节点
add_executable(odom_tf_publisher src/odom_tf_publisher.cpp)
ament_target_dependencies(odom_tf_publisher 
  rclcpp 
  geometry_msgs 
  nav_msgs 
  tf2_ros 
  unitree_go
)

# 2. 编译速度指令转换节点 (注意：要把复制过来的 common 源码一起编译)
# 假设 ros2_sport_client.cpp 和 motor_crc.cpp 放在了 src/common/ 目录下
add_executable(cmd_vel_translator 
  src/cmd_vel_translator.cpp 
  src/common/ros2_sport_client.cpp 
  src/common/motor_crc.cpp
)
ament_target_dependencies(
  cmd_vel_translator 
  rclcpp 
  geometry_msgs 
  unitree_go 
  unitree_api
)

add_executable(test_mock_state_pub src/test/test_mock_state_pub.cpp)
ament_target_dependencies(test_mock_state_pub rclcpp unitree_go)

add_executable(test_cmd_vel_pub src/test/test_cmd_vel_pub.cpp)
ament_target_dependencies(test_cmd_vel_pub rclcpp geometry_msgs)

install(TARGETS
  odom_tf_publisher
  cmd_vel_translator
  test_mock_state_pub   # <-- 添加这行
  test_cmd_vel_pub      # <-- 添加这行
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # uncomment the line when a copyright and license is not present in all source files
  #set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # uncomment the line when this package is not in a git repo
  #set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
