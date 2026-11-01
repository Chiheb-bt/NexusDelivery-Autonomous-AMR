#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import subprocess, sys

class DynamicObstacleSpawner(Node):
    def __init__(self):
        super().__init__('dynamic_obstacle_spawner')
        self.sub = self.create_subscription(Odometry, '/odom', self.cb, 10)
        self.spawned = False
        self.get_logger().info('DynamicObstacleSpawner active: monitoring robot position for Test E...')

    def cb(self, msg):
        x = msg.pose.pose.position.x
        if not self.spawned and x > -27.0:
            self.spawned = True
            self.get_logger().info(f'*** ROBOT REACHED x={x:.2f}m! SPAWNING DYNAMIC OBSTACLE AT x=-23.0, y=0.25 ***')
            cmd = [
                'ros2', 'run', 'gazebo_ros', 'spawn_entity.py',
                '-file', '/rdsim/rdsim_gazebo/models/dynamic_obstacle.sdf',
                '-entity', 'road_delivery_obstacle',
                '-x', '-23.0', '-y', '0.25', '-z', '0.25'
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.get_logger().info(f'Spawn result: {res.stdout.strip()}')
            rclpy.shutdown()

def main():
    rclpy.init()
    node = DynamicObstacleSpawner()
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.1)

if __name__ == '__main__':
    main()
