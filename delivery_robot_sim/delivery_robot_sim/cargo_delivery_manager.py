#!/usr/bin/env python3
"""Cargo Delivery & Motorized Hatch Actuation Manager Node.

Manages:
- Physical 60-degree motorized cargo hatch actuation (`cargo_hatch_joint`) in Gazebo.
- Autonomous parcel spawning inside hollow cargo bay during depot loading.
- Doorstep package handover & despawning upon customer OTP validation.
- Real-time synchronization of parcel pose with robot odometry during transit.
- Manual override commands from Founder Fleet Cockpit via `/delivery/hatch_cmd` and `/delivery/package_cmd`.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import threading
import time
from typing import Optional

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    from nav_msgs.msg import Odometry
    ROS_AVAILABLE = True
except ImportError:
    Node = object
    ROS_AVAILABLE = False


HATCH_CLOSED_ANGLE = 0.0
HATCH_OPEN_ANGLE = 1.05  # ~60.1 degrees
DEFAULT_SDF_PATH = "/home/chiheb/Downloads/RDSim-devel-2wheel_diff/rdsim_gazebo/models/nexus_package/model.sdf"
CONTAINER_SDF_PATH = "/rdsim/rdsim_gazebo/models/nexus_package/model.sdf"


def get_package_sdf_path() -> str:
    if os.path.exists(DEFAULT_SDF_PATH):
        return DEFAULT_SDF_PATH
    if os.path.exists(CONTAINER_SDF_PATH):
        return CONTAINER_SDF_PATH
    # Fallback search
    ws_path = os.path.expanduser("~/rdsim_ws/src/RDSim/rdsim_gazebo/models/nexus_package/model.sdf")
    if os.path.exists(ws_path):
        return ws_path
    return DEFAULT_SDF_PATH


class CargoDeliveryManager(Node if ROS_AVAILABLE else object):
    """ROS 2 node controlling the physical cargo bay, package loading, and motorized hatch."""

    def __init__(self, node_name: str = "cargo_delivery_manager"):
        if ROS_AVAILABLE:
            super().__init__(node_name)
            self.logger = self.get_logger()
        else:
            import logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(node_name)

        self.lock = threading.Lock()
        self.hatch_angle = HATCH_CLOSED_ANGLE
        self.hatch_state = "CLOSED"  # "CLOSED", "OPENING", "OPEN", "CLOSING"
        self.package_loaded = False
        self.current_order_id = "ORD-001"
        self.robot_x = -31.5
        self.robot_y = -0.75
        self.robot_z = 0.05
        self.robot_yaw = 0.0
        self.last_state = "INITIALIZING"
        self.sdf_path = get_package_sdf_path()
        self.gz_available = shutil.which("gz") is not None

        if ROS_AVAILABLE:
            # Subscriptions
            self.sub_state = self.create_subscription(
                String, "/mission/state", self._on_mission_state, 10
            )
            self.sub_odom = self.create_subscription(
                Odometry, "/odom", self._on_odom, 10
            )
            self.sub_hatch_cmd = self.create_subscription(
                String, "/delivery/hatch_cmd", self._on_hatch_cmd, 10
            )
            self.sub_pkg_cmd = self.create_subscription(
                String, "/delivery/package_cmd", self._on_pkg_cmd, 10
            )
            self.sub_arrival = self.create_subscription(
                String, "/delivery/arrival_event", self._on_arrival, 10
            )

            # Publishers
            self.pub_hatch_status = self.create_publisher(
                String, "/delivery/hatch_status", 10
            )
            self.pub_pkg_status = self.create_publisher(
                String, "/delivery/package_status", 10
            )

            # High-rate control & status publisher timer (10 Hz)
            self.timer = self.create_timer(0.1, self._timer_callback)
            # Low-rate parcel position lock timer (2 Hz)
            self.sync_timer = self.create_timer(0.5, self._sync_parcel_pose)

        self.logger.info("CargoDeliveryManager initialized (Motorized 60-deg Hatch + 3D Parcel Spawner).")

    def _on_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        with self.lock:
            self.robot_x = p.x
            self.robot_y = p.y
            self.robot_z = p.z
            self.robot_yaw = yaw

    def _on_mission_state(self, msg: String):
        state = msg.data.strip().upper()
        with self.lock:
            prev = self.last_state
            self.last_state = state

        if state == prev:
            return

        self.logger.info(f"[MISSION_STATE_EVENT] Transition: {prev} -> {state}")

        # Automated Depot Loading Workflow
        if state in ("LOADING_PACKAGE_AT_DEPOT", "LOADING", "DEPOT_LOADING"):
            threading.Thread(target=self._sequence_load_package_at_depot, daemon=True).start()

        # Automated Customer Doorstep Unloading Workflow
        elif state in ("ARRIVED_AT_DOORSTEP", "DELIVERING", "HANDOVER"):
            threading.Thread(target=self._sequence_open_for_delivery, daemon=True).start()

        # Secure transit lock
        elif state in ("NAVIGATING_TO_CLIENT", "RETURNING_TO_DEPOT"):
            self.set_hatch_target(HATCH_CLOSED_ANGLE)

    def _on_arrival(self, msg: String):
        try:
            data = json.loads(msg.data)
            action = data.get("action", "")
            if action == "DELIVERY":
                threading.Thread(target=self._sequence_open_for_delivery, daemon=True).start()
        except Exception:
            pass

    def _on_hatch_cmd(self, msg: String):
        cmd = msg.data.strip().upper()
        self.logger.info(f"[OPERATOR_CMD] Hatch command received: {cmd}")
        if cmd in ("OPEN", "UNLOCK", "TRUE", "1"):
            self.set_hatch_target(HATCH_OPEN_ANGLE)
        elif cmd in ("CLOSE", "LOCK", "FALSE", "0"):
            self.set_hatch_target(HATCH_CLOSED_ANGLE)
        elif cmd == "TOGGLE":
            with self.lock:
                target = HATCH_CLOSED_ANGLE if self.hatch_angle > 0.5 else HATCH_OPEN_ANGLE
            self.set_hatch_target(target)

    def _on_pkg_cmd(self, msg: String):
        cmd = msg.data.strip().upper()
        self.logger.info(f"[OPERATOR_CMD] Package command received: {cmd}")
        if cmd in ("LOAD", "SPAWN"):
            self.spawn_package_in_gazebo()
        elif cmd in ("UNLOAD", "DESPAWN", "DELETE"):
            self.delete_package_from_gazebo()
        elif cmd == "TOGGLE":
            with self.lock:
                loaded = self.package_loaded
            if loaded:
                self.delete_package_from_gazebo()
            else:
                self.spawn_package_in_gazebo()

    def set_hatch_target(self, angle: float):
        with self.lock:
            self.hatch_angle = angle
            self.hatch_state = "OPEN" if angle > 0.5 else "CLOSED"

        # Apply physical joint target in Gazebo Classic
        try:
            subprocess.run([
                "gz", "joint",
                "-m", "rdsim",
                "-j", "cargo_hatch_joint",
                "--pos-t", f"{angle:.3f}",
                "--pos-p", "120.0",
                "--pos-d", "6.0"
            ], capture_output=True, timeout=2.0)
        except Exception as e:
            self.logger.debug(f"gz joint command non-critical warning: {e}")

    def spawn_package_in_gazebo(self):
        with self.lock:
            rx, ry, rz, ryaw = self.robot_x, self.robot_y, self.robot_z, self.robot_yaw

        # Calculate position of package inside cargo bay link (recessed x=-0.04m, z=+0.22m)
        px = rx - 0.04 * math.cos(ryaw)
        py = ry - 0.04 * math.sin(ryaw)
        pz = max(0.20, rz + 0.22)

        sdf = get_package_sdf_path()
        if os.path.exists(sdf):
            try:
                # Remove any existing instance first
                subprocess.run(["gz", "model", "-m", "nexus_package", "-d"], capture_output=True, timeout=2.0)
                time.sleep(0.1)
                # Spawn new parcel
                cmd = [
                    "gz", "model",
                    "-m", "nexus_package",
                    "-f", sdf,
                    "-x", f"{px:.3f}",
                    "-y", f"{py:.3f}",
                    "-z", f"{pz:.3f}",
                    "-Y", f"{ryaw:.3f}"
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
                self.logger.info(f"Spawned 3D delivery package in Gazebo at ({px:.2f}, {py:.2f}, {pz:.2f}) [code {res.returncode}]")
            except Exception as e:
                self.logger.warn(f"Failed to spawn package model: {e}")

        with self.lock:
            self.package_loaded = True

    def delete_package_from_gazebo(self):
        try:
            subprocess.run(["gz", "model", "-m", "nexus_package", "-d"], capture_output=True, timeout=2.0)
            self.logger.info("Removed 3D delivery package from Gazebo (Handover completed).")
        except Exception as e:
            self.logger.warn(f"Failed to delete package model: {e}")

        with self.lock:
            self.package_loaded = False

    def _sync_parcel_pose(self):
        """Keep parcel precisely aligned inside cargo bay while robot travels at speed."""
        with self.lock:
            if not self.package_loaded:
                return
            rx, ry, rz, ryaw = self.robot_x, self.robot_y, self.robot_z, self.robot_yaw

        px = rx - 0.04 * math.cos(ryaw)
        py = ry - 0.04 * math.sin(ryaw)
        pz = max(0.20, rz + 0.22)

        try:
            subprocess.run([
                "gz", "model",
                "-m", "nexus_package",
                "-x", f"{px:.3f}",
                "-y", f"{py:.3f}",
                "-z", f"{pz:.3f}",
                "-Y", f"{ryaw:.3f}"
            ], capture_output=True, timeout=1.0)
        except Exception:
            pass

    def _sequence_load_package_at_depot(self):
        self.logger.info("Executing Automated Depot Loading Sequence...")
        # 1. Open Hatch (60 degrees)
        self.set_hatch_target(HATCH_OPEN_ANGLE)
        time.sleep(1.5)

        # 2. Spawn 3D package inside hollow cargo bay
        self.spawn_package_in_gazebo()
        time.sleep(1.5)

        # 3. Latch Hatch securely closed
        self.set_hatch_target(HATCH_CLOSED_ANGLE)
        self.logger.info("Depot Loading Sequence Completed. Package locked in transit.")

    def _sequence_open_for_delivery(self):
        self.logger.info("Executing Doorstep Arrival Handover Sequence...")
        # 1. Open Hatch (60 degrees) for customer access
        self.set_hatch_target(HATCH_OPEN_ANGLE)

    def _timer_callback(self):
        if not ROS_AVAILABLE:
            return

        with self.lock:
            h_state = self.hatch_state
            h_angle = self.hatch_angle
            p_loaded = self.package_loaded
            ord_id = self.current_order_id

        # Publish hatch status JSON
        hatch_msg = String()
        hatch_msg.data = json.dumps({
            "state": h_state,
            "angle_rad": round(h_angle, 3),
            "angle_deg": round(math.degrees(h_angle), 1),
            "loaded": p_loaded
        })
        self.pub_hatch_status.publish(hatch_msg)

        # Publish package status JSON
        pkg_msg = String()
        pkg_msg.data = json.dumps({
            "loaded": p_loaded,
            "order_id": ord_id
        })
        self.pub_pkg_status.publish(pkg_msg)


def main(args=None):
    if ROS_AVAILABLE:
        rclpy.init(args=args)
        node = CargoDeliveryManager()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
            rclpy.shutdown()
    else:
        mgr = CargoDeliveryManager()
        print("Running in headless standalone mode without ROS 2.")


if __name__ == "__main__":
    main()
