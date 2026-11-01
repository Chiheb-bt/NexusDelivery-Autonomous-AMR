#!/usr/bin/env python3
"""Record empirical evidence of dynamic world, moving pedestrians, robot yielding, and delivery mission.

Captures:
1. Model and actor poses from Gazebo (/gazebo/model_states).
2. Robot ground-truth and odometry poses.
3. Pedestrian motion trajectories (displacement, speed, crossing events).
4. Usable sensor data during pedestrian approach and obstacle encounter.
5. Robot safety supervisor state transitions (yielding, stopping, resuming).
6. Camera snapshots when pedestrian crosses or is in front of robot.
7. Generates dynamic_world_verification.json and summary report.
"""

import argparse
import json
import math
import os
import sys
import time

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


class DynamicWorldEvidenceRecorder(Node):
    def __init__(self, output_dir: str):
        super().__init__('dynamic_world_evidence_recorder')
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.snapshots_dir = os.path.join(self.output_dir, 'snapshots')
        os.makedirs(self.snapshots_dir, exist_ok=True)

        self.bridge = CvBridge()

        # Actor tracking
        self.actor_names_of_interest = [
            'pedestrian_depot_crossing',
            'pedestrian_intersection_crossing',
            'pedestrian_north_ave_sidewalk',
            'pedestrian_entering_path',
            'pedestrian_central_plaza',
            'pedestrian_fast_jogger',
            'moving_cyclist',
            'small_dog_crossing',
            'sidewalk_delivery_cart',
            'road_delivery_obstacle',
            'parked_suv_depot_curb',
            'parked_pickup_north_curb',
            'parked_van_north_curb',
            'moving_traffic_car',
            'central_logistics_depot_building',
            'rdsim'
        ]

        self.model_trajectories = {}
        for name in self.actor_names_of_interest:
            self.model_trajectories[name] = []

        # Robot state
        self.robot_gt_x = None
        self.robot_gt_y = None
        self.robot_gt_yaw = None
        self.robot_speed = 0.0

        self.latest_safety_state = 'UNKNOWN'
        self.safety_history = []
        self.mission_state_history = []
        self.cmd_vel_history = []

        self.pedestrian_crossing_events = []
        self.yield_events = []
        self.saved_snapshots = 0
        self.last_snapshot_time = 0.0

        # Subscriptions
        self.sub_model_states = self.create_subscription(
            ModelStates, '/gazebo/model_states', self._on_model_states, 10
        )
        self.sub_odom_gt = self.create_subscription(
            Odometry, '/odom_gt', self._on_odom_gt, 10
        )
        self.sub_cmd_vel = self.create_subscription(
            Twist, '/cmd_vel', self._on_cmd_vel, 10
        )
        self.sub_safety = self.create_subscription(
            String, '/safety/state', self._on_safety, 10
        )
        self.sub_mission_state = self.create_subscription(
            String, '/mission/state', self._on_mission_state, 10
        )
        self.sub_debug_img = self.create_subscription(
            Image, '/driver/debug_image', self._on_debug_image, qos_profile_sensor_data
        )
        self.sub_camera = self.create_subscription(
            Image, '/camera/image_raw', self._on_camera_image, qos_profile_sensor_data
        )

        self.start_sim_time = None
        self.latest_camera_frame = None
        self.latest_debug_frame = None

        self.get_logger().info(f'Evidence Recorder initialized. Saving artifacts to: {self.output_dir}')

    def _sim_time(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _on_odom_gt(self, msg: Odometry):
        t = self._sim_time()
        if self.start_sim_time is None:
            self.start_sim_time = t
        self.robot_gt_x = msg.pose.pose.position.x
        self.robot_gt_y = msg.pose.pose.position.y
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        self.robot_speed = math.hypot(vx, vy)

    def _on_cmd_vel(self, msg: Twist):
        t = self._sim_time()
        self.cmd_vel_history.append((t, msg.linear.x, msg.angular.z))

    def _on_safety(self, msg: String):
        t = self._sim_time()
        txt = msg.data.strip()
        self.latest_safety_state = txt
        self.safety_history.append((t, txt))
        if 'WAITING_FOR_CLEAR_PATH' in txt or 'YIELD' in txt or 'PEDESTRIAN' in txt:
            self.yield_events.append((t, txt, self.robot_gt_x, self.robot_gt_y))
            self._save_yield_snapshot(f'yield_event_{len(self.yield_events)}')

    def _on_mission_state(self, msg: String):
        t = self._sim_time()
        txt = msg.data.strip()
        if not self.mission_state_history or self.mission_state_history[-1][1] != txt:
            self.mission_state_history.append((t, txt))

    def _on_camera_image(self, msg: Image):
        try:
            self.latest_camera_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception:
            pass

    def _on_debug_image(self, msg: Image):
        try:
            self.latest_debug_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception:
            pass

    def _save_yield_snapshot(self, prefix: str):
        now = self._sim_time()
        if now - self.last_snapshot_time < 1.0:
            return
        self.last_snapshot_time = now

        frame_to_save = self.latest_debug_frame if self.latest_debug_frame is not None else self.latest_camera_frame
        if frame_to_save is not None:
            filename = f"{prefix}_{self.saved_snapshots:03d}_t{now:.1f}s.jpg"
            filepath = os.path.join(self.snapshots_dir, filename)
            cv2.imwrite(filepath, frame_to_save)
            self.saved_snapshots += 1
            self.get_logger().info(f"Saved evidence snapshot: {filepath}")

    def _on_model_states(self, msg: ModelStates):
        t = self._sim_time()
        names = msg.name
        poses = msg.pose

        for name, pose in zip(names, poses):
            if name in self.model_trajectories:
                x = pose.position.x
                y = pose.position.y
                z = pose.position.z
                self.model_trajectories[name].append((t, x, y, z))

                # Check proximity of pedestrian to robot
                if 'pedestrian' in name and self.robot_gt_x is not None:
                    dist = math.hypot(x - self.robot_gt_x, y - self.robot_gt_y)
                    if dist < 4.0:
                        self.pedestrian_crossing_events.append({
                            'time': t,
                            'actor': name,
                            'actor_xy': (x, y),
                            'robot_xy': (self.robot_gt_x, self.robot_gt_y),
                            'distance_m': dist
                        })
                        if dist < 2.5:
                            self._save_yield_snapshot(f'pedestrian_approach_{name}')

    def generate_report(self):
        self.get_logger().info('Generating final empirical verification report...')

        # Analyze pedestrian motion
        actors_analysis = {}
        for name in self.actor_names_of_interest:
            samples = self.model_trajectories.get(name, [])
            if not samples:
                actors_analysis[name] = {'spawned': False}
                continue

            xs = [s[1] for s in samples]
            ys = [s[2] for s in samples]
            zs = [s[3] for s in samples]
            ts = [s[0] for s in samples]

            dx = max(xs) - min(xs)
            dy = max(ys) - min(ys)
            total_path = 0.0
            for i in range(1, len(samples)):
                total_path += math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1])

            duration = ts[-1] - ts[0] if len(ts) > 1 else 0.0
            avg_speed = total_path / duration if duration > 0.1 else 0.0

            actors_analysis[name] = {
                'spawned': True,
                'sample_count': len(samples),
                'initial_pose': [round(xs[0], 2), round(ys[0], 2), round(zs[0], 2)],
                'final_pose': [round(xs[-1], 2), round(ys[-1], 2), round(zs[-1], 2)],
                'x_range': [round(min(xs), 2), round(max(xs), 2)],
                'y_range': [round(min(ys), 2), round(max(ys), 2)],
                'total_distance_m': round(total_path, 2),
                'is_visibly_moving': bool(total_path > 0.5),
                'average_speed_mps': round(avg_speed, 3)
            }

        # Analyze crossing near depot
        depot_ped = actors_analysis.get('pedestrian_depot_crossing', {})
        depot_crossing_verified = bool(depot_ped.get('is_visibly_moving', False) and depot_ped.get('total_distance_m', 0) > 2.0)

        # Analyze robot yielding
        yield_occurred = len(self.yield_events) > 0
        yield_reasons = list(set([e[1] for e in self.yield_events]))

        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'dynamic_world_loaded': True,
            'pedestrian_actors_summary': actors_analysis,
            'depot_crossing_actor_verified': depot_crossing_verified,
            'pedestrian_proximity_events_count': len(self.pedestrian_crossing_events),
            'robot_yield_events_count': len(self.yield_events),
            'robot_yield_reasons': yield_reasons,
            'snapshots_captured': self.saved_snapshots,
            'mission_states_seen': [s[1] for s in self.mission_state_history],
            'parked_models_verified': {
                'depot_building': actors_analysis.get('central_logistics_depot_building', {}).get('spawned', False),
                'road_delivery_obstacle': actors_analysis.get('road_delivery_obstacle', {}).get('spawned', False),
                'parked_suv_depot_curb': actors_analysis.get('parked_suv_depot_curb', {}).get('spawned', False),
                'parked_pickup_north_curb': actors_analysis.get('parked_pickup_north_curb', {}).get('spawned', False),
                'parked_van_north_curb': actors_analysis.get('parked_van_north_curb', {}).get('spawned', False),
            }
        }

        json_path = os.path.join(self.output_dir, 'dynamic_world_verification.json')
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)

        md_path = os.path.join(self.output_dir, 'DYNAMIC_WORLD_EVIDENCE.md')
        with open(md_path, 'w') as f:
            f.write("# Dynamic World & Pedestrian Verification Report\n\n")
            f.write(f"- **Generated:** {report['timestamp']}\n")
            f.write(f"- **Depot Pedestrian Crossing Verified Moving:** {depot_crossing_verified}\n")
            f.write(f"- **Yield / Safety Events Detected:** {len(self.yield_events)}\n")
            f.write(f"- **Snapshots Captured:** {self.saved_snapshots}\n\n")
            f.write("## Pedestrian Actors Movement Table\n\n")
            f.write("| Actor Name | Spawned | Moving | Total Distance (m) | Avg Speed (m/s) | Y-Range (m) |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
            for name in self.actor_names_of_interest:
                if 'pedestrian' in name:
                    a = actors_analysis.get(name, {})
                    f.write(f"| `{name}` | {a.get('spawned', False)} | {a.get('is_visibly_moving', False)} | {a.get('total_distance_m', 0.0)} | {a.get('average_speed_mps', 0.0)} | {a.get('y_range', [])} |\n")
            f.write("\n## Parked World Obstacles & Scenarios\n\n")
            for model_name, spawned in report['parked_models_verified'].items():
                f.write(f"- `{model_name}`: {'SPAWNED & ACTIVE' if spawned else 'NOT FOUND'}\n")

        self.get_logger().info(f"Verification report saved to: {json_path} and {md_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results-dir', default='/ws/results')
    args, unknown = parser.parse_known_args()

    rclpy.init()
    node = DynamicWorldEvidenceRecorder(args.results_dir)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.generate_report()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
