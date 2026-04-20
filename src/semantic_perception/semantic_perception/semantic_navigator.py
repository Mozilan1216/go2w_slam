#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped, PointStamped
from rclpy.qos import qos_profile_sensor_data
from cv_bridge import CvBridge
import cv2
import base64
import requests
import json
import threading

# TF2 空间魔法核心库
import tf2_ros
import tf2_geometry_msgs 

class SemanticNavigator(Node):
    def __init__(self):
        super().__init__('semantic_navigator')
        self.bridge = CvBridge()
        
        # 1. 订阅话题 (保持与之前一致)
        self.image_sub = self.create_subscription(Image, '/camera/camera/color/image_raw', self.image_callback, qos_profile_sensor_data)
        self.depth_sub = self.create_subscription(Image, '/camera/camera/aligned_depth_to_color/image_raw', self.depth_callback, qos_profile_sensor_data)
        self.info_sub = self.create_subscription(CameraInfo, '/camera/camera/color/camera_info', self.info_callback, 1)
        
        # 2. 发布者：将目标点发布给 Nav2
        self.goal_pub = self.create_publisher(PoseStamped, '/semantic_goal', 10)
        
        # 3. TF2 监听器：实时获取狗在地图上的位置
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.is_processing = False 
        self.latest_depth_image = None
        self.camera_intrinsics = None
        self.camera_frame_id = 'camera_color_optical_frame' 

        self.get_logger().info("🏁 语义导航闭环节点已启动！正在连接 TF 树...")

    def info_callback(self, msg):
        if self.camera_intrinsics is None:
            self.camera_intrinsics = {'fx': msg.k[0], 'cx': msg.k[2], 'fy': msg.k[4], 'cy': msg.k[5]}
            self.camera_frame_id = msg.header.frame_id 

    def depth_callback(self, msg):
        try:
            self.latest_depth_image = self.bridge.imgmsg_to_cv2(msg, "16UC1")
        except: pass

    def image_callback(self, msg):
        if self.is_processing or self.latest_depth_image is None or self.camera_intrinsics is None:
            return
        self.is_processing = True
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            current_depth = self.latest_depth_image.copy() 
            frame_time = msg.header.stamp # 记录该帧图像捕捉的精确时刻
            threading.Thread(target=self.process_logic, args=(cv_image, current_depth, frame_time)).start()
        except Exception as e:
            self.get_logger().error(f"图像转换失败: {e}")
            self.is_processing = False

    def process_logic(self, cv_image, depth_image, frame_time):
        try:
            # --- 步骤 A: 呼叫 Moondream 获取像素坐标 ---
            _, buffer = cv2.imencode('.jpg', cv_image)
            base64_image = base64.b64encode(buffer).decode('utf-8')
            payload = {
                "model": "moondream",
                "prompt": "Locate the door. Return JSON with x, y, w, h.",
                "images": [base64_image], "stream": False, "format": "json"
            }
            response = requests.post("http://127.0.0.1:11434/api/generate", json=payload)
            
            if response.status_code == 200:
                box = json.loads(response.json()['response'])
                h, w, _ = cv_image.shape
                u, v = int(box['x'] * w), int(box['y'] * h)
                
                # --- 步骤 B: 3D 解算 (相机坐标系) ---
                z_m = depth_image[v, u] / 1000.0
                if 0.2 < z_m < 8.0:
                    x_cam = (u - self.camera_intrinsics['cx']) * z_m / self.camera_intrinsics['fx']
                    y_cam = (v - self.camera_intrinsics['cy']) * z_m / self.camera_intrinsics['fy']
                    
                    # --- 步骤 C: TF2 魔法转换 (相机 -> 地图) ---
                    self.do_spatial_projection(x_cam, y_cam, z_m, frame_time)
            
        except Exception as e:
            self.get_logger().error(f"处理失败: {e}")
        finally:
            self.is_processing = False

    def do_spatial_projection(self, x, y, z, stamp):
        # 1. 构造相机坐标系下的点
        p = PointStamped()
        p.header.frame_id = self.camera_frame_id
        p.header.stamp = stamp 
        p.point.x, p.point.y, p.point.z = float(x), float(y), float(z)

        try:
            # 2. 查询变换：从相机光学系到全局地图系 map
            # 使用 rclpy.time.Time() 表示查询“最新的变换”
            transform = self.tf_buffer.lookup_transform('map', p.header.frame_id, rclpy.time.Time())
            
            # 3. 坐标投影
            p_map = tf2_geometry_msgs.do_transform_point(p, transform)
            
            # 4. 封装并发布导航目标
            goal = PoseStamped()
            goal.header.frame_id = 'map'
            goal.header.stamp = self.get_clock().now().to_msg()
            goal.pose.position = p_map.point
            goal.pose.orientation.w = 1.0 # 默认不改变机器狗的朝向
            
            self.goal_pub.publish(goal)
            self.get_logger().info(f"📍 [地图坐标锁定] X={p_map.point.x:.2f}, Y={p_map.point.y:.2f}. 目标已发送至 Nav2!")
            
        except Exception as e:
            self.get_logger().warn("等待 TF 树链接中 (需要开启 SLAM 节点)...")

def main(args=None):
    rclpy.init(args=args)
    node = SemanticNavigator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()