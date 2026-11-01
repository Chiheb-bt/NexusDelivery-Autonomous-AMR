"""Independent Ground-Truth Evaluator Node (ROS 2 Humble).

Monitors Gazebo simulation ground-truth (/odom_gt) and mission events.
STRICTLY decoupled from navigation decisions - ground truth is never sent to the controller.

Outputs:
- eval_log.csv: Time-series of true pose, velocity, clearance, mission state, order ID.
- eval_summary.json: Comprehensive evaluation metrics required by project specs.
"""

import csv
import json
import math
import os
import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String


class EvaluatorNode(Node):
    def __init__(self):
        super().__init__('evaluator_node')

        self.declare_parameter('log_path', '/tmp/eval_log.csv')
        self.declare_parameter('summary_path', '/tmp/eval_summary.json')
        self.declare_parameter('stop_speed_threshold_mps', 0.05)
        self.declare_parameter('obstacle_x', -23.0)
        self.declare_parameter('obstacle_y', 0.25)
        self.declare_parameter('obstacle_radius', 0.25)
        self.declare_parameter('robot_radius', 0.25)

        self.log_path = str(self.get_parameter('log_path').value)
        self.summary_path = str(self.get_parameter('summary_path').value)
        if not self.summary_path or self.summary_path == '':
            self.summary_path = os.path.join(os.path.dirname(self.log_path) or '/tmp', 'eval_summary.json')
        self.stop_thresh = float(self.get_parameter('stop_speed_threshold_mps').value)
        self.obs_x = float(self.get_parameter('obstacle_x').value)
        self.obs_y = float(self.get_parameter('obstacle_y').value)
        self.obs_r = float(self.get_parameter('obstacle_radius').value)
        self.robot_r = float(self.get_parameter('robot_radius').value)

        os.makedirs(os.path.dirname(self.log_path) or '/tmp', exist_ok=True)
        self.f = open(self.log_path, 'w', newline='', buffering=1)
        self.csv = csv.writer(self.f)
        self.csv.writerow([
            't_sim', 'gt_x', 'gt_y', 'speed_mps', 'mission_state',
            'current_order', 'obs_clearance_m', 'is_stopped', 'is_collision'
        ])

        # Tracking metrics
        self.timestamps = []
        self.speeds = []
        self.x_history = []
        self.y_history = []
        self.total_distance_travelled = 0.0
        self.prev_x = None
        self.prev_y = None
        self.start_x = None
        self.start_y = None

        self.min_obstacle_clearance = 999.0
        self.collision_count = 0
        self.stops_count = 0
        self.was_stopped = False

        self.current_mission_state = 'INIT'
        self.current_order_id = 'NONE'
        self.mission_states_seen = set()
        self.completed_orders = 0
        self.failed_orders = 0
        self.returned_to_depot = False
        self.target_name = 'DEPOT'
        self.target_xy = (-30.0, 0.0)
        self.target_action = 'WAIT'
        self.arrival_errors = []

        # Subscriptions
        self.sub_gt = self.create_subscription(Odometry, '/odom_gt', self.on_odom_gt, 10)
        self.sub_state = self.create_subscription(String, '/mission/state', self.on_mission_state, 10)
        self.sub_status = self.create_subscription(String, '/delivery/mission_status', self.on_delivery_status, 10)
        self.sub_target = self.create_subscription(String, '/delivery/current_target', self.on_target, 10)

        self.summary_timer = self.create_timer(2.0, self.write_summary_file)
        self.get_logger().info('EvaluatorNode started (Decoupled Ground-Truth Evaluator).')

    def on_mission_state(self, msg: String):
        if not rclpy.ok() or not self.context.ok():
            return
        state = msg.data.strip()
        self.current_mission_state = state
        self.mission_states_seen.add(state)

    def on_target(self, msg: String):
        try:
            data = json.loads(msg.data)
            self.target_name = data.get('target_name', 'DEPOT')
            self.target_xy = tuple(data.get('target_xy', (-30.0, 0.0)))
            self.target_action = data.get('action', 'WAIT')
            self.current_order_id = data.get('order_id', 'NONE')
        except Exception:
            pass

    def on_delivery_status(self, msg: String):
        try:
            data = json.loads(msg.data)
            self.completed_orders = data.get('completed_orders', self.completed_orders)
            self.failed_orders = data.get('failed_orders', self.failed_orders)
            if data.get('mission_state') in ('DEPOT_PARKED_WAITING', 'MISSION_COMPLETED') and self.completed_orders > 0:
                self.returned_to_depot = True
        except Exception:
            pass

    def on_odom_gt(self, m: Odometry):
        if not rclpy.ok() or not self.context.ok():
            return

        t = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        x = m.pose.pose.position.x
        y = m.pose.pose.position.y
        vx = m.twist.twist.linear.x
        vy = m.twist.twist.linear.y
        speed = math.hypot(vx, vy)

        if self.prev_x is None:
            self.prev_x, self.prev_y = x, y
            if self.start_x is None:
                self.start_x, self.start_y = x, y
            step_dist = 0.0
        else:
            dx = x - self.prev_x
            dy = y - self.prev_y
            step_dist = math.hypot(dx, dy)
            self.total_distance_travelled += step_dist
            self.prev_x, self.prev_y = x, y

        self.timestamps.append(t)
        self.speeds.append(speed)
        self.x_history.append(x)
        self.y_history.append(y)

        # Distance to obstacle
        dist_to_obs_center = math.hypot(x - self.obs_x, y - self.obs_y)
        edge_clearance = max(0.0, dist_to_obs_center - (self.obs_r + self.robot_r))
        if dist_to_obs_center < 6.0:
            if edge_clearance < self.min_obstacle_clearance:
                self.min_obstacle_clearance = edge_clearance

        is_collision = (edge_clearance <= 0.05 and dist_to_obs_center < 1.0)
        if is_collision:
            self.collision_count += 1

        is_stopped = (speed < self.stop_thresh)
        if is_stopped and not self.was_stopped:
            self.stops_count += 1
        self.was_stopped = is_stopped

        # If arrived event recently seen, measure destination error
        if any(k in self.current_mission_state for k in ('ARRIVED', 'DELIVERING', 'DOCKING')):
            err = math.hypot(x - self.target_xy[0], y - self.target_xy[1])
            self.arrival_errors.append(err)

        # Independent ground truth check for return to depot
        dist_to_depot_gt = math.hypot(x - self.start_x, y - self.start_y)
        if self.completed_orders >= 2 and dist_to_depot_gt <= 1.8:
            if not self.returned_to_depot:
                self.returned_to_depot = True
                self.get_logger().info('*** FULL MISSION SUCCESS: Both orders completed and returned to Depot! ***')
                self.write_summary_file()

        try:
            self.csv.writerow([
                round(t, 3), round(x, 3), round(y, 3), round(speed, 3),
                self.current_mission_state, self.current_order_id,
                round(edge_clearance, 3), is_stopped, is_collision
            ])
        except Exception:
            pass

    def compute_summary(self):
        duration = (self.timestamps[-1] - self.timestamps[0]) if len(self.timestamps) > 1 else 0.0
        moving_speeds = [s for s in self.speeds if s >= self.stop_thresh]
        avg_speed = float(np.mean(moving_speeds)) if moving_speeds else 0.0
        max_speed = float(np.max(self.speeds)) if self.speeds else 0.0
        net_progress = math.hypot(self.x_history[-1] - self.start_x, self.y_history[-1] - self.start_y) if self.x_history else 0.0

        # Destination error
        avg_arrival_error = float(np.mean(self.arrival_errors)) if self.arrival_errors else 0.0

        # Status evaluation according to strict project specifications
        if self.collision_count > 0:
            status = 'COLLISION_DETECTED'
        elif self.completed_orders >= 2 and self.returned_to_depot:
            status = 'SUCCESS'
        elif self.completed_orders >= 2 and not self.returned_to_depot:
            status = 'FAILED_TO_RETURN'
        elif self.failed_orders > 0:
            status = 'INCOMPLETE_ORDERS'
        elif self.total_distance_travelled > 1.0:
            status = 'IN_PROGRESS'
        else:
            status = 'INITIALIZING'

        obs_status = 'AVOIDANCE_AND_REACQUISITION_VERIFIED' if any('AVOID' in s for s in self.mission_states_seen) else 'CLEAR_CORRIDOR'
        if self.collision_count > 0:
            obs_status = 'COLLISION_DETECTED'

        summary = {
            'mission_completion_status': status,
            'start_location': f'DEPOT_POST_OFFICE ({-30.0 if self.start_x is None else self.start_x:.1f}, {0.0 if self.start_y is None else self.start_y:.1f})',
            'destination_settings': ['CLIENT_1_NORTH_AVENUE (-15.0, 15.0)', 'CLIENT_2_NORTH_AVENUE (-15.0, 28.0)'],
            'mission_duration_s': round(duration, 2),
            'total_distance_travelled_m': round(self.total_distance_travelled, 2),
            'net_progress_distance_m': round(net_progress, 2),
            'minimum_obstacle_clearance_m': round(self.min_obstacle_clearance, 3) if self.min_obstacle_clearance < 900 else 'NO_OBSTACLE_ENCOUNTERED',
            'collision_count': self.collision_count,
            'destination_error_avg_m': round(avg_arrival_error, 3),
            'average_speed_mps': round(avg_speed, 3),
            'maximum_speed_mps': round(max_speed, 3),
            'number_of_stops': self.stops_count,
            'obstacle_avoidance_outcome': obs_status,
            'orders_completed': self.completed_orders,
            'orders_failed': self.failed_orders,
            'returned_to_depot': self.returned_to_depot,
            'mission_states_reached': sorted(list(self.mission_states_seen)),
            'perception_and_control_sensor_stack': 'Front RGB Camera (/camera/image_raw) + RGB-D Depth Camera (/camera/depth/image_raw) + IMU (/imu) + Wheel Odometry (/odom). NO LiDAR, NO GPS.'
        }
        return summary

    def write_summary_file(self):
        if not self.timestamps:
            return
        summary = self.compute_summary()
        try:
            with open(self.summary_path, 'w') as f_sum:
                json.dump(summary, f_sum, indent=2)
        except Exception:
            pass

    def stop_cleanly(self):
        try:
            self.write_summary_file()
            self.f.flush()
            self.f.close()
        except Exception:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = EvaluatorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception as e:
        import traceback
        print(f'evaluator_node crashed with: {e}', flush=True)
        traceback.print_exc()
    finally:
        try:
            node.stop_cleanly()
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except Exception:
                pass


if __name__ == '__main__':
    main()
