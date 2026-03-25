#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <tf2_ros/transform_broadcaster.h>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include "unitree_api/msg/request.hpp"
#include "common/ros2_sport_client.h"

class Go2BaseNode : public rclcpp::Node {
public:
    Go2BaseNode() : Node("go2_base_node") {
        sport_client_ = std::make_shared<SportClient>();
        tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
        
        odom_pub_ = this->create_publisher<nav_msgs::msg::Odometry>("/odom", 10);
        sport_pub_ = this->create_publisher<unitree_api::msg::Request>("/api/sport/request", 10);

        // 订阅官方 SLAM 提供的高精度 Odom
        odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>(
            "rt/unitree/slam_mapping/odom", rclcpp::QoS(10).best_effort(),
            std::bind(&Go2BaseNode::odom_callback, this, std::placeholders::_1));

        cmd_vel_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "/cmd_vel", 10,
            std::bind(&Go2BaseNode::cmd_vel_callback, this, std::placeholders::_1));

        RCLCPP_INFO(this->get_logger(), "🐕 Go2 底盘核心节点已启动！等待官方 SLAM 数据...");
    }

private:
    void odom_callback(const nav_msgs::msg::Odometry::SharedPtr msg) {
        geometry_msgs::msg::TransformStamped t;
        t.header.stamp = this->now();
        t.header.frame_id = "odom";
        t.child_frame_id = "base_link";
        
        t.transform.translation.x = msg->pose.pose.position.x;
        t.transform.translation.y = msg->pose.pose.position.y;
        t.transform.translation.z = msg->pose.pose.position.z;
        t.transform.rotation = msg->pose.pose.orientation;
        tf_broadcaster_->sendTransform(t);

        nav_msgs::msg::Odometry odom_msg = *msg;
        odom_msg.header.stamp = t.header.stamp;
        odom_msg.header.frame_id = "odom";
        odom_msg.child_frame_id = "base_link";
        odom_pub_->publish(odom_msg);
    }

    void cmd_vel_callback(const geometry_msgs::msg::Twist::SharedPtr msg) {
        unitree_api::msg::Request req;
        if (msg->linear.x == 0.0 && msg->linear.y == 0.0 && msg->angular.z == 0.0) {
            sport_client_->StopMove(req);
        } else {
            sport_client_->Move(req, msg->linear.x, msg->linear.y, msg->angular.z);
        }
        sport_pub_->publish(req);
    }

    std::shared_ptr<SportClient> sport_client_;
    std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
    rclcpp::Publisher<unitree_api::msg::Request>::SharedPtr sport_pub_;
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<Go2BaseNode>());
    rclcpp::shutdown();
    return 0;
}