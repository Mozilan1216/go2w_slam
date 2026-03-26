#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import os

class SemanticVoiceNode(Node):
    def __init__(self):
        super().__init__('semantic_voice_node')
        # 创建一个订阅者，订阅 /voice_cmd 话题
        self.sub = self.create_subscription(
            String, 
            '/voice_cmd', 
            self.voice_callback, 
            10
        )
        self.get_logger().info('🔊 语义语音播报接口已启动！等待接收文本...')

    def voice_callback(self, msg):
        text = msg.data
        self.get_logger().info(f'🎤 正在播报: {text}')
        
        # 调用系统的 espeak 命令，使用中文 (-v zh) 播报文本
        # 注意：espeak 的中文听起来比较机械，如果后续嫌难听，
        # 你可以换成播放提前录制好的好看的 mp3/wav 文件（例如使用 mpg123 命令）
        os.system(f'espeak -v zh "{text}" &')

def main(args=None):
    rclpy.init(args=args)
    node = SemanticVoiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()