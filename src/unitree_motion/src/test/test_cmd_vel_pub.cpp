// 文件路径: unitree_motion/src/test/test_cmd_vel_pub.cpp
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"

class MockCmdVelPublisher : public rclcpp::Node {
public:
    MockCmdVelPublisher() : Node("mock_cmd_vel_publisher") {
        pub_ = this->create_publisher<geometry_msgs::msg::Twist>("cmd_vel", 10);
        
        // 10Hz 频率发布控制指令
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(100), 
            std::bind(&MockCmdVelPublisher::timer_callback, this));
            
        RCLCPP_INFO(this->get_logger(), "🧪 模拟上层导航控制节点已启动！正在发送测试 Twist 速度...");
    }

private:
    void timer_callback() {
        auto msg = geometry_msgs::msg::Twist();
        
        msg.linear.x = 0.1;  // 线速度 0.1 m/s (前进)
        msg.linear.y = 0.0;  // 横向速度 0
        msg.angular.z = 0.2; // 角速度 0.2 rad/s (左转)

        pub_->publish(msg);
    }

    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char * argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MockCmdVelPublisher>());
    rclcpp::shutdown();
    return 0;
}