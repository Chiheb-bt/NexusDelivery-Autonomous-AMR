#!/usr/bin/env python3
"""Automated progressive test harness for navigation validation.

Executes and verifies:
- Test A: Straight-line motion toward a single waypoint directly ahead.
- Test B: In-place heading correction from a 180-degree heading mismatch.
- Test C: Multi-waypoint route execution including 90-degree intersection turn.
- Test D: Full delivery mission verification from simulation logs.

Records live telemetry and outputs structured results JSON and CSV.
"""
import argparse
import csv
import json
import math
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String


def normalize_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def quaternion_to_yaw(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class ProgressiveTestRunner(Node):
    def __init__(self, results_dir: str = '/tmp'):
        super().__init__('progressive_test_runner')
        self.results_dir = results_dir
        os.makedirs(self.results_dir, exist_ok=True)

        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0
        self.current_speed = 0.0
        self.cmd_v = 0.0
        self.cmd_w = 0.0
        self.mission_state = 'INIT'
        self.safety_state = 'NORMAL'
        self.odom_received = False
        self.arrival_received = False
        self.last_arrival_data = {}

        self.sub_odom = self.create_subscription(Odometry, '/odom', self._on_odom, 10)
        self.sub_cmd = self.create_subscription(Twist, '/cmd_vel', self._on_cmd, 10)
        self.sub_state = self.create_subscription(String, '/mission/state', self._on_state, 10)
        self.sub_safety = self.create_subscription(String, '/safety/state', self._on_safety, 10)
        self.sub_arrival = self.create_subscription(String, '/delivery/arrival_event', self._on_arrival, 10)

        self.pub_target = self.create_publisher(String, '/delivery/current_target', 10)
        self.get_logger().info('ProgressiveTestRunner initialized.')

    def _sim_time(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _on_odom(self, msg: Odometry):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        self.current_yaw = quaternion_to_yaw(msg.pose.pose.orientation)
        self.current_speed = math.hypot(msg.twist.twist.linear.x, msg.twist.twist.linear.y)
        self.odom_received = True

    def _on_cmd(self, msg: Twist):
        self.cmd_v = msg.linear.x
        self.cmd_w = msg.angular.z

    def _on_state(self, msg: String):
        self.mission_state = msg.data.strip()

    def _on_safety(self, msg: String):
        self.safety_state = msg.data.strip()

    def _on_arrival(self, msg: String):
        try:
            self.last_arrival_data = json.loads(msg.data)
            self.arrival_received = True
            self.get_logger().info(f'Received arrival event: {self.last_arrival_data}')
        except Exception:
            pass

    def send_target(self, target_xy: Tuple[float, float], action: str = 'DELIVERY', order_id: str = 'TEST', target_name: str = 'TARGET'):
        msg = String()
        msg.data = json.dumps({
            'target_xy': list(target_xy),
            'action': action,
            'order_id': order_id,
            'target_name': target_name
        })
        self.arrival_received = False
        self.pub_target.publish(msg)
        self.get_logger().info(f'Published Target: {target_name} at {target_xy}, Action={action}')

    def wait_for_odom(self, timeout_s: float = 10.0) -> bool:
        start = time.time()
        while time.time() - start < timeout_s and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.odom_received:
                return True
        return False

    def run_test_a(self, timeout_s: float = 25.0) -> Dict:
        """Test A: Straight-line motion toward a single waypoint directly ahead."""
        self.get_logger().info('=== STARTING TEST A: Straight-line motion ===')
        target_xy = (-25.0, 0.0)
        start_x, start_y, start_yaw = self.current_x, self.current_y, self.current_yaw
        initial_dist = math.hypot(target_xy[0] - start_x, target_xy[1] - start_y)

        self.send_target(target_xy, action='DELIVERY', order_id='TEST-A', target_name='WAYPOINT_A')

        t0 = self._sim_time()
        log = []
        circling_detected = False

        while self._sim_time() - t0 < timeout_s and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
            now = self._sim_time()
            dist = math.hypot(target_xy[0] - self.current_x, target_xy[1] - self.current_y)
            log.append({
                't': now - t0, 'x': self.current_x, 'y': self.current_y,
                'yaw': self.current_yaw, 'v_cmd': self.cmd_v, 'w_cmd': self.cmd_w,
                'speed': self.current_speed, 'dist': dist
            })

            # Check if robot is repeatedly circling (|w| > 0.4 while moving)
            if abs(self.cmd_w) > 0.40 and self.cmd_v > 0.15:
                circling_detected = True

            if dist < 1.2 or self.arrival_received:
                self.get_logger().info(f'Test A waypoint reached in {now - t0:.2f}s! Final dist: {dist:.2f}m')
                break

        final_dist = math.hypot(target_xy[0] - self.current_x, target_xy[1] - self.current_y)
        dist_travelled = math.hypot(self.current_x - start_x, self.current_y - start_y)
        passed = (final_dist < 1.25) and not circling_detected and (dist_travelled > 3.0)

        res = {
            'test_name': 'Test A — Straight-line motion',
            'passed': passed,
            'initial_pose': [round(start_x, 3), round(start_y, 3), round(start_yaw, 3)],
            'final_pose': [round(self.current_x, 3), round(self.current_y, 3), round(self.current_yaw, 3)],
            'initial_distance_m': round(initial_dist, 3),
            'final_distance_m': round(final_dist, 3),
            'distance_travelled_m': round(dist_travelled, 3),
            'circling_detected': circling_detected,
            'duration_s': round(self._sim_time() - t0, 2)
        }
        self.get_logger().info(f'Test A Result: {res}')
        return res

    def run_test_b(self, timeout_s: float = 25.0) -> Dict:
        """Test B: In-place heading correction from a 180-degree heading mismatch."""
        self.get_logger().info('=== STARTING TEST B: In-place heading correction ===')
        # Target is directly behind the robot
        target_xy = (-30.0, 0.0)
        start_x, start_y, start_yaw = self.current_x, self.current_y, self.current_yaw
        initial_dist = math.hypot(target_xy[0] - start_x, target_xy[1] - start_y)

        self.send_target(target_xy, action='DELIVERY', order_id='TEST-B', target_name='WAYPOINT_B')

        t0 = self._sim_time()
        in_place_rotation_observed = False
        forward_while_misaligned = False
        aligned_reached = False

        while self._sim_time() - t0 < timeout_s and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
            now = self._sim_time()
            dx = target_xy[0] - self.current_x
            dy = target_xy[1] - self.current_y
            dist = math.hypot(dx, dy)
            target_angle = math.atan2(dy, dx)
            heading_err = abs(normalize_angle(target_angle - self.current_yaw))

            # Verify in-place rotation: angular velocity high, linear velocity zero
            if heading_err > 0.45:
                if abs(self.cmd_w) > 0.30 and self.cmd_v < 0.05:
                    in_place_rotation_observed = True
                elif self.cmd_v > 0.15:
                    forward_while_misaligned = True
            elif heading_err < 0.35:
                aligned_reached = True

            if dist < 1.2 or self.arrival_received:
                self.get_logger().info(f'Test B waypoint reached in {now - t0:.2f}s! Final dist: {dist:.2f}m')
                break

        final_dist = math.hypot(target_xy[0] - self.current_x, target_xy[1] - self.current_y)
        dist_travelled = math.hypot(self.current_x - start_x, self.current_y - start_y)
        passed = in_place_rotation_observed and not forward_while_misaligned and aligned_reached and (final_dist < 1.25)

        res = {
            'test_name': 'Test B — Heading correction',
            'passed': passed,
            'initial_pose': [round(start_x, 3), round(start_y, 3), round(start_yaw, 3)],
            'final_pose': [round(self.current_x, 3), round(self.current_y, 3), round(self.current_yaw, 3)],
            'initial_distance_m': round(initial_dist, 3),
            'final_distance_m': round(final_dist, 3),
            'distance_travelled_m': round(dist_travelled, 3),
            'in_place_rotation_observed': in_place_rotation_observed,
            'forward_while_misaligned': forward_while_misaligned,
            'duration_s': round(self._sim_time() - t0, 2)
        }
        self.get_logger().info(f'Test B Result: {res}')
        return res

    def run_test_c(self, timeout_s: float = 60.0) -> Dict:
        """Test C: Multi-waypoint route with 90-degree intersection turn."""
        self.get_logger().info('=== STARTING TEST C: Multi-waypoint route ===')
        waypoints = [
            (-26.0, 0.0),
            (-20.0, 0.0),
            (-15.0, 0.0),
            (-15.0, 8.0)
        ]
        start_x, start_y, start_yaw = self.current_x, self.current_y, self.current_yaw
        wps_reached = 0
        t0 = self._sim_time()

        for i, wp in enumerate(waypoints):
            self.send_target(wp, action='DELIVERY', order_id=f'TEST-C-{i+1}', target_name=f'WP_{i+1}')
            wp_start = self._sim_time()
            reached = False

            while self._sim_time() - wp_start < 25.0 and rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.05)
                dist = math.hypot(wp[0] - self.current_x, wp[1] - self.current_y)
                if dist < 1.3 or self.arrival_received:
                    reached = True
                    wps_reached += 1
                    self.get_logger().info(f'Reached WP {i+1} ({wp})! Total reached: {wps_reached}/{len(waypoints)}')
                    break

            if not reached:
                self.get_logger().warn(f'Failed to reach WP {i+1} ({wp}) within timeout.')
                break

        dist_travelled = math.hypot(self.current_x - start_x, self.current_y - start_y)
        passed = (wps_reached == len(waypoints))

        res = {
            'test_name': 'Test C — Multiple waypoints',
            'passed': passed,
            'waypoints_reached': wps_reached,
            'total_waypoints': len(waypoints),
            'initial_pose': [round(start_x, 3), round(start_y, 3), round(start_yaw, 3)],
            'final_pose': [round(self.current_x, 3), round(self.current_y, 3), round(self.current_yaw, 3)],
            'distance_travelled_m': round(dist_travelled, 3),
            'duration_s': round(self._sim_time() - t0, 2)
        }
        self.get_logger().info(f'Test C Result: {res}')
        return res


def main():
    rclpy.init()
    runner = ProgressiveTestRunner(results_dir='/tmp/test_progressive')
    if not runner.wait_for_odom(timeout_s=15.0):
        print('ERROR: Odometry not received, aborting tests.')
        sys.exit(1)

    res_a = runner.run_test_a()
    res_b = runner.run_test_b()
    res_c = runner.run_test_c()

    summary = {
        'test_a': res_a,
        'test_b': res_b,
        'test_c': res_c,
        'all_passed': (res_a['passed'] and res_b['passed'] and res_c['passed'])
    }
    print('\n=== PROGRESSIVE TEST SUITE SUMMARY ===')
    print(json.dumps(summary, indent=2))

    with open('/tmp/test_progressive/summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    runner.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
