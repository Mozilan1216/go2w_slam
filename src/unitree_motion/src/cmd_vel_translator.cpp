#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "ros2_sport_client.h"
#include "unitree_api/msg/request.hpp" // 引入 Request 消息

class CmdVelTranslator : public rclcpp::Node {
public:
    CmdVelTranslator() : Node("cmd_vel_translator") {
        sport_client_ = std::make_shared<SportClient>(this);

        cmd_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "cmd_vel", 10,
            std::bind(&CmdVelTranslator::cmd_vel_callback, this, std::placeholders::_1));

        RCLCPP_INFO(this->get_logger(), "🕹️ cmd_vel 转换节点已启动，等待上层导航指令...");
    }

private:
    void cmd_vel_callback(const geometry_msgs::msg::Twist::SharedPtr msg) {
        float vx = msg->linear.x;
        float vy = msg->linear.y;
        float vyaw = msg->angular.z;

        // 修复：传入底层的 req_ 对象作为第一个参数
        sport_client_->Move(req_, vx, vy, vyaw);
    }

    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_sub_;
    std::shared_ptr<SportClient> sport_client_;
    unitree_api::msg::Request req_;  // 新增：用于承载宇树底层通信请求头
};

int main(int argc, char * argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<CmdVelTranslator>());
    rclcpp::shutdown();
    return 0;
}