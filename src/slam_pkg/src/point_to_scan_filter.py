#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, LaserScan
import numpy as np

class FastScanFilter(Node):
    def __init__(self):
        super().__init__('fast_scan_filter')
        # 订阅 FAST-LIO2 的机身坐标系点云
        self.sub = self.create_subscription(PointCloud2, '/cloud_registered_body', self.callback, 10)
        self.pub = self.create_publisher(LaserScan, '/scan', 10)
        self.get_logger().info("点云转换节点 [终极去噪版] 已启动...")

    def callback(self, msg):
        # 1. 动态获取步长
        step = msg.point_step
        num_points = len(msg.data) // step
        
        # 2. 解析原始数据并强制拷贝（解决 C-contiguous 报错）
        raw_data = np.frombuffer(msg.data, dtype=np.uint8).reshape(num_points, step)
        x = raw_data[:, 0:4].copy().view(np.float32).flatten()
        y = raw_data[:, 4:8].copy().view(np.float32).flatten()
        z = raw_data[:, 8:12].copy().view(np.float32).flatten()

        # 3. 🌟 强化去噪过滤
        # 将 MIN_HEIGHT 提升至 0.8m，彻底过滤地面碎屑和重影
        # 将探测距离限制在 0.5m~15m 之间，过滤掉狗头阴影和远处不稳定点
        dist_raw = np.sqrt(x**2 + y**2)
        mask = (z > 0.8) & (z < 1.15) & (dist_raw > 0.5) & (dist_raw < 15.0)
        
        filtered_x = x[mask]
        filtered_y = y[mask]
        
        if len(filtered_x) < 10: # 点太少说明是噪声，直接忽略
            return

        # 4. 极坐标转换
        ranges_raw = np.sqrt(filtered_x**2 + filtered_y**2)
        angles_raw = np.arctan2(filtered_y, filtered_x)

        # 5. 构造并发布 LaserScan
        scan = LaserScan()
        scan.header = msg.header
        scan.header.frame_id = 'body' 
        scan.angle_min, scan.angle_max = -3.14159, 3.14159
        scan.angle_increment = 0.0174 # 1度一个点，大幅减轻 SLAM Toolbox 压力
        scan.range_min, scan.range_max = 0.4, 20.0
        
        num_bins = int((scan.angle_max - scan.angle_min) / scan.angle_increment) + 1
        scan.ranges = [float('inf')] * num_bins
        
        for r, a in zip(ranges_raw, angles_raw):
            bin_idx = int((a - scan.angle_min) / scan.angle_increment)
            if 0 <= bin_idx < num_bins:
                if r < scan.ranges[bin_idx]:
                    scan.ranges[bin_idx] = float(r)
        
        self.pub.publish(scan)

def main(args=None):
    rclpy.init(args=args)
    node = FastScanFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()