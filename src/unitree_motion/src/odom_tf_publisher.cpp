#include "rclcpp/rclcpp.hpp"
#include "unitree_go/msg/sport_mode_state.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "nav_msgs/msg/odometry.hpp"

class OdomTfPublisher : public rclcpp::Node {
public:
    OdomTfPublisher() : Node("odom_tf_publisher") {
        tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
        odom_pub_ = this->create_publisher<nav_msgs::msg::Odometry>("odom", 10);

        // 核心配置：设置最佳努力 (Best Effort) 的 QoS 以匹配宇树底层 DDS 通信
        rclcpp::QoS qos(rclcpp::KeepLast(10));
        qos.best_effort();

        state_sub_ = this->create_subscription<unitree_go::msg::SportModeState>(
            "lf/sportmodestate", qos,
            std::bind(&OdomTfPublisher::state_callback, this, std::placeholders::_1));

        RCLCPP_INFO(this->get_logger(), "🐕 Odom与TF发布节点已启动，正在监听机器狗状态...");
    }

private:
    void state_callback(const unitree_go::msg::SportModeState::SharedPtr msg) {
        auto now = this->get_clock()->now();

        // 1. 组装并发布 TF 树 (odom -> base_link)
        geometry_msgs::msg::TransformStamped t;
        t.header.stamp = now;
        t.header.frame_id = "odom";
        t.child_frame_id = "base_link";

        t.transform.translation.x = msg->position[0];
        t.transform.translation.y = msg->position[1];
        t.transform.translation.z = msg->position[2];
        t.transform.rotation.w = msg->imu_state.quaternion[0];
        t.transform.rotation.x = msg->imu_state.quaternion[1];
        t.transform.rotation.y = msg->imu_state.quaternion[2];
        t.transform.rotation.z = msg->imu_state.quaternion[3];

        tf_broadcaster_->sendTransform(t);

        // 2. 组装并发布标准的 Odometry 里程计话题
        nav_msgs::msg::Odometry odom_msg;
        odom_msg.header.stamp = now;
        odom_msg.header.frame_id = "odom";
        odom_msg.child_frame_id = "base_link";

        odom_msg.pose.pose.position.x = msg->position[0];
        odom_msg.pose.pose.position.y = msg->position[1];
        odom_msg.pose.pose.position.z = msg->position[2];
        odom_msg.pose.pose.orientation = t.transform.rotation;

        odom_msg.twist.twist.linear.x = msg->velocity[0];
        odom_msg.twist.twist.linear.y = msg->velocity[1];
        odom_msg.twist.twist.angular.z = msg->yaw_speed;

        odom_pub_->publish(odom_msg);
    }

    rclcpp::Subscription<unitree_go::msg::SportModeState>::SharedPtr state_sub_;
    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
    std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
};

int main(int argc, char * argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<OdomTfPublisher>());
    rclcpp::shutdown();
    return 0;
}