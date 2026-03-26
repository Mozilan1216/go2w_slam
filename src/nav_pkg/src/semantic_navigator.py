#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
import yaml
import math
import os
from ament_index_python.packages import get_package_share_directory

class SemanticNavigator(Node):
    def __init__(self):
        super().__init__('semantic_navigator')
        
        # 1. 加载语义字典
        self.places = self.load_semantic_map()
        
        # 2. 订阅自然语言文本话题 (比如从语音识别节点发出来的文本)
        self.voice_sub = self.create_subscription(
            String,
            '/recognized_text',  # 假设语音识别把文字发到这里
            self.nlp_callback,
            10
        )
        
        # 3. 发布目标点给 Nav2
        self.goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 10)
        
        # 可选：如果之前写了那个语音播报节点，这里还可以发个语音反馈
        self.voice_feedback_pub = self.create_publisher(String, '/voice_cmd', 10)
        
        self.get_logger().info('🧠 语义导航大脑已启动！等待指令...')

    def load_semantic_map(self):
        # 动态获取 nav_pkg 路径，读取 YAML
        pkg_share = get_package_share_directory('nav_pkg')
        yaml_path = os.path.join(pkg_share, 'config', 'semantic_places.yaml')
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('destinations', {})
        except Exception as e:
            self.get_logger().error(f'读取语义地图失败: {e}')
            return {}

    def nlp_callback(self, msg):
        raw_text = msg.data.strip()
        self.get_logger().info(f'👂 听到指令: "{raw_text}"')
        
        # --- 极其简单的意图提取 (对应原仓库的 nav_intent_router) ---
        target_place = None
        for place_name in self.places.keys():
            # 如果字典里的名字出现在了句子中 (比如 "带我去食堂" 包含 "食堂")
            if place_name in raw_text:
                target_place = place_name
                break
                
        if target_place:
            self.get_logger().info(f'🎯 意图解析成功！目标地点: {target_place}')
            self.publish_goal(target_place)
            self.speak_feedback(f"好的，正在前往{target_place}")
        else:
            self.get_logger().warn('❓ 无法从句子中提取已知目的地。')
            self.speak_feedback("抱歉，我不知道那个地方在哪里。")

    def publish_goal(self, place_name):
        coords = self.places[place_name]
        
        goal = PoseStamped()
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.header.frame_id = 'map'  # Nav2 使用的全局地图坐标系
        
        # 设置 X, Y
        goal.pose.position.x = float(coords['x'])
        goal.pose.position.y = float(coords['y'])
        goal.pose.position.z = 0.0
        
        # 将 Yaw 角 (欧拉角) 转换为四元数
        yaw = float(coords['yaw'])
        goal.pose.orientation.w = math.cos(yaw / 2.0)
        goal.pose.orientation.x = 0.0
        goal.pose.orientation.y = 0.0
        goal.pose.orientation.z = math.sin(yaw / 2.0)
        
        # 下发给 Nav2！
        self.goal_pub.publish(goal)
        self.get_logger().info(f'🚀 已向 Nav2 下发坐标: X={coords["x"]}, Y={coords["y"]}')

    def speak_feedback(self, text):
        msg = String()
        msg.data = text
        self.voice_feedback_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = SemanticNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()