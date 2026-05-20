#!/bin/bash

# 1. 自动生成时间戳 (格式: 年月日_时分，例如 20260413_1125)
TIME_STAMP=$(date +%Y%m%d_%H%M)
MAP_NAME="map_${TIME_STAMP}"
SAVE_DIR="/home/ubuntu/ros2_ws/src/maps"

echo "======================================"
echo "🚀 开始一键保存多模态地图"
echo "📂 目标目录: ${SAVE_DIR}"
echo "🏷️ 地图前缀: ${MAP_NAME}"
echo "======================================"

# 2. 保存 2D 栅格地图 (用于 Nav2)
echo "[1]正在提取 2D 栅格地图..."
ros2 run nav2_map_server map_saver_cli -t /projected_map -f ${SAVE_DIR}/${MAP_NAME}

# # 3. 保存 3D OctoMap 体素地图 (可选备份)
# echo "[2/2] 正在提取 3D OctoMap 体素..."
# ros2 run octomap_server octomap_saver -f ${SAVE_DIR}/${MAP_NAME}_octomap.bt

echo "======================================"
echo "✅ 实时内存地图提取完毕！"
echo "======================================"
echo "⚠️ 注意：原始 3D 点云 (.pcd) 将在你 Ctrl+C 关闭建图终端时自动生成。"