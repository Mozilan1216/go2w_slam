import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class SimpleCommandParser(Node):
    def __init__(self):
        super().__init__('simple_command_parser')
        
        # 1. 定义你的坐标字典 (你需要把 0.0 换成你在 RViz 里测出的真实坐标)
        self.rooms = {
            "main_gate": [10.5, 2.3, 0.0],       # 正大门
            "northwest_gate": [-5.2, 12.0, 1.57],  # 西北门
            "building_4": [45.0, -10.5, -1.57],    # 四号楼
            "building_7": [80.2, 33.1, 3.14],      # 七号楼
            "building_5": [60.0, 15.0, 0.0]        # 五号楼
        }

        # 2. 定义“同义词”词库 (把用户可能说的词都填进去)
        self.keywords_map = {
            "main_gate": ["正大门", "大门", "主大门", "去正门"],
            "northwest_gate": ["西北门", "西门", "北门"],
            "building_4": ["四号楼", "4号楼", "四教", "4栋"],
            "building_7": ["七号楼", "7号楼", "七教", "7栋"],
            "building_5": ["五号楼", "5号楼", "五教", "5栋"]
        }

        # 模拟接收用户语音/文本的话题
        self.sub = self.create_subscription(String, '/user_voice_text', self.parse_text, 10)

    def parse_text(self, msg):
        user_text = msg.data.lower() # 转小写，方便匹配
        self.get_logger().info(f"收到用户原始指令: '{user_text}'")

        target_id = None
        target_coords = None

        # 3. 核心逻辑：遍历词库进行模糊匹配
        for room_id, aliases in self.keywords_map.items():
            for alias in aliases:
                if alias in user_text:
                    target_id = room_id
                    target_coords = self.rooms[room_id]
                    break # 找到了就跳出内层循环
            if target_id:
                break # 找到了就跳出外层循环

        # 4. 执行结果
        if target_id:
            self.get_logger().info(f"✅ 解析成功！目的地: {target_id}, 坐标: {target_coords}")
            self.go_to_pose(target_coords) # 调用导航函数
        else:
            self.get_logger().warn("❌ 没听懂要去哪里，请再说一遍。")

    def go_to_pose(self, coords):
        # 在这里调用 Nav2 的 API 发送目标点
        print(f"正在驱动机器狗前往 X:{coords[0]}, Y:{coords[1]}, Yaw:{coords[2]}...")

def main():
    rclpy.init()
    node = SimpleCommandParser()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()