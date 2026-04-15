#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from rclpy.qos import qos_profile_sensor_data  # 🔥 解决假死的核心：引入传感器专属 QoS
from cv_bridge import CvBridge
import cv2
import base64
import requests
import json
import threading

class SemanticDetector(Node):
    def __init__(self):
        super().__init__('semantic_detector')
        self.bridge = CvBridge()
        
        # 1. 订阅彩色图像 (修复了话题名和 QoS)
        self.image_sub = self.create_subscription(
            Image,
            '/camera/camera/color/image_raw',
            self.image_callback,
            qos_profile_sensor_data) # 🔥 必须用这个！
            
        # 2. 订阅对齐后的深度图像
        self.depth_sub = self.create_subscription(
            Image,
            '/camera/camera/aligned_depth_to_color/image_raw',
            self.depth_callback,
            qos_profile_sensor_data)
            
        # 3. 订阅相机内参
        self.info_sub = self.create_subscription(
            CameraInfo,
            '/camera/camera/color/camera_info',
            self.info_callback,
            1)

        self.is_processing = False 
        self.latest_depth_image = None
        self.camera_intrinsics = None
        
        self.get_logger().info("👀 满血版视觉语义节点已启动！正在监听真实画面...")

    def info_callback(self, msg):
        # 只需要获取一次相机内参就够了
        if self.camera_intrinsics is None:
            self.camera_intrinsics = {
                'fx': msg.k[0], 'cx': msg.k[2],
                'fy': msg.k[4], 'cy': msg.k[5]
            }
            self.get_logger().info(f"📐 成功获取相机内参: {self.camera_intrinsics}")

    def depth_callback(self, msg):
        # 实时更新最新的深度图矩阵 (通常 D435i 的深度图格式是 16UC1，单位是毫米)
        try:
            self.latest_depth_image = self.bridge.imgmsg_to_cv2(msg, "16UC1")
        except Exception as e:
            pass

    def image_callback(self, msg):
        if self.is_processing or self.latest_depth_image is None or self.camera_intrinsics is None:
            return

        self.is_processing = True
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            # 必须把当前的深度图也传给线程，防止时间戳错位
            current_depth = self.latest_depth_image.copy() 
            threading.Thread(target=self.call_moondream, args=(cv_image, current_depth)).start()
        except Exception as e:
            self.get_logger().error(f"图像转换失败: {e}")
            self.is_processing = False

    def call_moondream(self, cv_image, depth_image):
        self.get_logger().info("📸 截取到画面，正在呼叫大模型锁定目标...")
        
        try:
            _, buffer = cv2.imencode('.jpg', cv_image)
            base64_image = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "model": "moondream",
                "prompt": "You are a coordinate detector. Locate the door in the image. Return ONLY a valid JSON object containing the bounding box with keys 'x', 'y', 'w', 'h'.",
                "images": [base64_image],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0}
            }
            
            response = requests.post("http://127.0.0.1:11434/api/generate", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                box_data = json.loads(result['response'])
                
                height, width, _ = cv_image.shape
                u = int(box_data.get('x', 0) * width)
                v = int(box_data.get('y', 0) * height)
                
                self.get_logger().info(f"🎯 大模型锁定像素: (u={u}, v={v})")
                
                # --- 开始 3D 解算 ---
                # 1. 防止坐标越界
                u = max(0, min(u, width - 1))
                v = max(0, min(v, height - 1))
                
                # 2. 读取深度值 (D435i 默认单位是毫米，转化为米)
                z_mm = depth_image[v, u]
                z_m = z_mm / 1000.0
                
                if z_m <= 0.1 or z_m > 10.0:
                    self.get_logger().warn(f"⚠️ 深度值异常 ({z_m} 米)，可能是反光或超出量程。")
                else:
                    # 3. 针孔相机投影公式
                    fx = self.camera_intrinsics['fx']
                    fy = self.camera_intrinsics['fy']
                    cx = self.camera_intrinsics['cx']
                    cy = self.camera_intrinsics['cy']
                    
                    x_cam = (u - cx) * z_m / fx
                    y_cam = (v - cy) * z_m / fy
                    
                    self.get_logger().info(f"🌌 【解算成功】目标在相机坐标系下的 3D 物理坐标: X={x_cam:.2f}米, Y={y_cam:.2f}米, Z={z_m:.2f}米")
                
            else:
                self.get_logger().error(f"❌ 大模型请求失败: {response.status_code}")
                
        except Exception as e:
            self.get_logger().error(f"❌ 发生意外错误: {e}")
        finally:
            self.is_processing = False

def main(args=None):
    rclpy.init(args=args)
    node = SemanticDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()