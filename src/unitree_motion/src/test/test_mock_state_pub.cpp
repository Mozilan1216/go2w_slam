// 文件路径: unitree_motion/src/test/test_mock_state_pub.cpp
#include "rclcpp/rclcpp.hpp"
#include "unitree_go/msg/sport_mode_state.hpp"
#include <cmath>

class MockStatePublisher : public rclcpp::Node {
public:
    MockStatePublisher() : Node("mock_state_publisher"), count_(0) {
        // 必须也是 Best Effort 才能和你的订阅者匹配
        rclcpp::QoS qos(rclcpp::KeepLast(10));
        qos.best_effort();

        pub_ = this->create_publisher<unitree_go::msg::SportModeState>("lf/sportmodestate", qos);
        
        // 50Hz 频率发布测试数据
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(20), 
            std::bind(&MockStatePublisher::timer_callback, this));
            
        RCLCPP_INFO(this->get_logger(), "🧪 模拟机器狗状态发布节点已启动！正在发送伪造的画圆运动数据...");
    }

private:
    void timer_callback() {
        auto msg = unitree_go::msg::SportModeState();
        
        // 模拟机器狗在做半径为 1 米的画圆运动
        float time_sec = count_ * 0.02f; 
        msg.position[0] = std::sin(time_sec); // X 坐标
        msg.position[1] = std::cos(time_sec); // Y 坐标
        msg.position[2] = 0.3;                // 机器狗站立高度

        // 模拟姿态：四元数 (这里简单设为无旋转 w=1)
        msg.imu_state.quaternion[0] = 1.0; 
        msg.imu_state.quaternion[1] = 0.0;
        msg.imu_state.quaternion[2] = 0.0;
        msg.imu_state.quaternion[3] = 0.0;

        // 模拟速度
        msg.velocity[0] = std::cos(time_sec); // vx
        msg.velocity[1] = -std::sin(time_sec); // vy
        msg.yaw_speed = 0.0;

        pub_->publish(msg);
        count_++;
    }

    rclcpp::Publisher<unitree_go::msg::SportModeState>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
    uint64_t count_;
};

int main(int argc, char * argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MockStatePublisher>());
    rclcpp::shutdown();
    return 0;
}