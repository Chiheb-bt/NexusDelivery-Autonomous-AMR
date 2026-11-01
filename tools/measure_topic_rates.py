#!/usr/bin/env python3
"""Measure actual publishing rates of key simulation topics in ROS 2."""

import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock


class TopicRateMonitor(Node):
    def __init__(self, duration_s=10.0):
        super().__init__('topic_rate_monitor')
        self.duration_s = duration_s
        self.counts = {
            '/clock': 0,
            '/camera/image_raw': 0,
            '/camera/depth/image_raw': 0,
            '/odom': 0,
        }
        self.sub_clock = self.create_subscription(Clock, '/clock', lambda m: self._inc('/clock'), 100)
        self.sub_rgb = self.create_subscription(Image, '/camera/image_raw', lambda m: self._inc('/camera/image_raw'), qos_profile_sensor_data)
        self.sub_depth = self.create_subscription(Image, '/camera/depth/image_raw', lambda m: self._inc('/camera/depth/image_raw'), qos_profile_sensor_data)
        self.sub_odom = self.create_subscription(Odometry, '/odom', lambda m: self._inc('/odom'), 10)

    def _inc(self, topic):
        self.counts[topic] += 1


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    rclpy.init()
    node = TopicRateMonitor(duration)
    t_start = time.time()
    while (time.time() - t_start) < duration and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.1)

    t_elapsed = time.time() - t_start
    print("=== Topic Publishing Rates (Wall-Clock Measurement) ===")
    for topic, count in node.counts.items():
        hz = count / max(0.001, t_elapsed)
        print(f"  {topic:28s}: {hz:6.2f} Hz ({count} msgs in {t_elapsed:.1f}s)")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
