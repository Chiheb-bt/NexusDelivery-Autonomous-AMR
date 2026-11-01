#!/usr/bin/env python3
"""GPS waypoint following with conservative camera-based city hazard stops."""

import csv
import json
import math
import os

import cv2
import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, NavSatFix
from std_msgs.msg import String

from gps_navigation_math import (
    OBSTACLE_LABELS,
    gps_to_world_xy,
    is_near_forward_obstacle,
    quaternion_yaw,
    waypoint_velocity,
)


def signal_color(image, box):
    height, width = image.shape[:2]
    x1, y1, x2, y2 = (int(v) for v in box)
    x1, x2 = clamp(x1, 0, width), clamp(x2, 0, width)
    y1, y2 = clamp(y1, 0, height), clamp(y2, 0, height)
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, np.array([0, 90, 70]), np.array([12, 255, 255]))
    red |= cv2.inRange(hsv, np.array([168, 90, 70]), np.array([180, 255, 255]))
    green = cv2.inRange(hsv, np.array([35, 70, 60]), np.array([95, 255, 255]))
    red_pixels, green_pixels = cv2.countNonZero(red), cv2.countNonZero(green)
    if max(red_pixels, green_pixels) < 3:
        return None
    return "red" if red_pixels > green_pixels else "green"


class GpsCameraController(Node):
    def __init__(self):
        super().__init__("gps_camera_controller")
        self.declare_parameter("route_xy", [0.0, 0.0, 45.0, 0.0, 100.0, 0.0])
        self.declare_parameter("start_x", -30.0)
        self.declare_parameter("start_y", 0.0)
        self.declare_parameter("world_heading_deg", 180.0)
        self.declare_parameter("max_linear_speed", 0.35)
        self.declare_parameter("max_angular_speed", 0.8)
        self.declare_parameter("waypoint_radius", 1.5)
        self.declare_parameter("lookahead_distance", 2.0)
        self.declare_parameter("gps_timeout_s", 2.0)
        self.declare_parameter("odom_timeout_s", 1.0)
        self.declare_parameter("camera_timeout_s", 1.0)
        self.declare_parameter("yolo_every_n", 3)
        self.declare_parameter("yolo_confidence", 0.35)
        self.declare_parameter("obstacle_clearance_y", 0.52)
        self.declare_parameter("obstacle_corridor_fraction", 0.30)
        self.declare_parameter("obstacle_clear_hold_s", 1.5)
        self.declare_parameter("log_path", "/tmp/city_navigation.csv")

        route = [float(v) for v in self.get_parameter("route_xy").value]
        if len(route) < 2 or len(route) % 2:
            raise ValueError("route_xy must contain at least one x,y waypoint pair")
        self.route = list(zip(route[::2], route[1::2]))
        self.start_x = float(self.get_parameter("start_x").value)
        self.start_y = float(self.get_parameter("start_y").value)
        self.world_heading_deg = float(self.get_parameter("world_heading_deg").value)
        self.max_linear_speed = float(self.get_parameter("max_linear_speed").value)
        self.max_angular_speed = float(self.get_parameter("max_angular_speed").value)
        self.waypoint_radius = float(self.get_parameter("waypoint_radius").value)
        self.lookahead_distance = float(self.get_parameter("lookahead_distance").value)
        self.yolo_every_n = max(1, int(self.get_parameter("yolo_every_n").value))
        self.obstacle_clearance_y = float(
            self.get_parameter("obstacle_clearance_y").value
        )
        self.obstacle_corridor_fraction = float(
            self.get_parameter("obstacle_corridor_fraction").value
        )
        self.obstacle_clear_hold_s = float(
            self.get_parameter("obstacle_clear_hold_s").value
        )
        self.gps_timeout_s = float(self.get_parameter("gps_timeout_s").value)
        self.odom_timeout_s = float(self.get_parameter("odom_timeout_s").value)
        self.camera_timeout_s = float(self.get_parameter("camera_timeout_s").value)

        model_path = os.path.join(
            get_package_share_directory("rdsim_gazebo"),
            "models",
            "yolov8n.pt",
        )
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"YOLO model is missing: {model_path}")
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "GPS/camera navigation requires Ultralytics; install it in the ROS environment"
            ) from exc
        self.model = YOLO(model_path)
        self.bridge = CvBridge()

        self.origin_lat = None
        self.origin_lon = None
        self.position_xy = None
        self.yaw = None
        self.last_gps_s = None
        self.last_odom_s = None
        self.last_camera_s = None
        self.image_count = 0
        self.latest_image = None
        self.latest_detections = []
        self.obstacle_active = False
        self.obstacle_clear_until = 0.0
        self.red_light_latched = False
        self.stop_sign_until = 0.0
        self.waypoint_index = 0
        self.completed = False

        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.state_pub = self.create_publisher(String, "/mission/state", 10)
        self.objects_pub = self.create_publisher(String, "/perception/objects", 10)
        self.debug_pub = self.create_publisher(Image, "/perception/debug", 1)
        self.create_subscription(
            NavSatFix, "/gps/gps/data", self.on_gps, qos_profile_sensor_data
        )
        self.create_subscription(Odometry, "/odom", self.on_odom, qos_profile_sensor_data)
        self.create_subscription(
            Image, "/camera/image_raw", self.on_image, qos_profile_sensor_data
        )

        log_path = str(self.get_parameter("log_path").value)
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        self.log_file = open(log_path, "w", newline="")
        self.csv = csv.writer(self.log_file)
        self.csv.writerow([
            "time_s", "state", "gps_x", "gps_y", "yaw_rad",
            "waypoint_index", "goal_x", "goal_y", "linear_x", "angular_z",
            "detections",
        ])
        self.create_timer(0.1, self.control_tick)
        self.get_logger().info(
            f"GPS waypoint navigation ready: {len(self.route)} map-frame waypoints; "
            "camera hazards fail safe by stopping"
        )

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def on_gps(self, msg):
        if msg.status.status < 0 or not math.isfinite(msg.latitude) or not math.isfinite(msg.longitude):
            return
        if self.origin_lat is None:
            self.origin_lat, self.origin_lon = msg.latitude, msg.longitude
        self.position_xy = gps_to_world_xy(
            msg.latitude,
            msg.longitude,
            self.origin_lat,
            self.origin_lon,
            self.start_x,
            self.start_y,
            self.world_heading_deg,
        )
        self.last_gps_s = self.now_s()

    def on_odom(self, msg):
        self.yaw = quaternion_yaw(msg.pose.pose.orientation)
        self.last_odom_s = self.now_s()

    def on_image(self, msg):
        try:
            image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except CvBridgeError as exc:
            self.get_logger().error(f"Could not convert camera frame: {exc}")
            return
        self.latest_image = image
        self.last_camera_s = self.now_s()
        self.image_count += 1
        if self.image_count % self.yolo_every_n:
            return

        results = self.model.predict(
            image,
            imgsz=320,
            conf=float(self.get_parameter("yolo_confidence").value),
            iou=0.45,
            device="cpu",
            verbose=False,
        )
        detections = []
        self.obstacle_active = False
        traffic_states = []
        for result in results:
            names = result.names
            for box in result.boxes or []:
                class_id = int(box.cls[0].item())
                label = str(names.get(class_id, class_id))
                confidence = float(box.conf[0].item())
                coords = tuple(float(v) for v in box.xyxy[0].cpu().tolist())
                detections.append({
                    "label": label,
                    "confidence": round(confidence, 3),
                    "bbox_xyxy": [round(v, 1) for v in coords],
                })
                if is_near_forward_obstacle(
                    label,
                    coords,
                    image.shape,
                    self.obstacle_clearance_y,
                    self.obstacle_corridor_fraction,
                ):
                    self.obstacle_active = True
                if label.lower() == "traffic light":
                    color = signal_color(image, coords)
                    if color is not None:
                        traffic_states.append(color)
                if label.lower() == "stop sign" and coords[3] >= image.shape[0] * 0.45:
                    self.stop_sign_until = self.now_s() + 2.0

        if "red" in traffic_states:
            self.red_light_latched = True
        elif "green" in traffic_states:
            self.red_light_latched = False
        self.latest_detections = detections
        if self.obstacle_active:
            self.obstacle_clear_until = (
                self.now_s() + self.obstacle_clear_hold_s
            )
        self.objects_pub.publish(String(data=json.dumps({
            "stamp": msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            "frame_id": msg.header.frame_id,
            "traffic_light": traffic_states[-1] if traffic_states else "unknown",
            "forward_obstacle": self.obstacle_active,
            "detections": detections,
        })))

    def publish_stop(self, state, now, goal=None):
        self.cmd_pub.publish(Twist())
        self.state_pub.publish(String(data=state))
        self.write_log(now, state, 0.0, 0.0, goal)
        self.publish_debug(state, goal)

    def write_log(self, now, state, linear, angular, goal):
        x, y = self.position_xy if self.position_xy is not None else ("", "")
        gx, gy = goal if goal is not None else ("", "")
        self.csv.writerow([
            f"{now:.3f}", state, x, y, self.yaw if self.yaw is not None else "",
            self.waypoint_index, gx, gy, f"{linear:.3f}", f"{angular:.3f}",
            json.dumps(self.latest_detections, separators=(",", ":")),
        ])
        self.log_file.flush()

    def publish_debug(self, state, goal):
        if self.latest_image is None:
            return
        image = self.latest_image.copy()
        cv2.putText(image, f"GPS route: {state}", (6, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        cv2.putText(image, f"Waypoint {self.waypoint_index + 1}/{len(self.route)}",
                    (6, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        if goal is not None:
            cv2.putText(image, f"Goal map XY: {goal[0]:.1f}, {goal[1]:.1f}",
                        (6, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        for detection in self.latest_detections:
            x1, y1, x2, y2 = (int(v) for v in detection["bbox_xyxy"])
            is_obstacle = detection["label"].lower() in OBSTACLE_LABELS
            color = (0, 0, 255) if is_obstacle else (255, 180, 0)
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            cv2.putText(image, detection["label"], (x1, max(12, y1 - 3)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        try:
            message = self.bridge.cv2_to_imgmsg(image, encoding="bgr8")
        except CvBridgeError as exc:
            self.get_logger().error(f"Could not encode debug frame: {exc}")
            return
        self.debug_pub.publish(message)

    def control_tick(self):
        now = self.now_s()
        if self.position_xy is None or self.last_gps_s is None or now - self.last_gps_s > self.gps_timeout_s:
            self.publish_stop("WAIT_GPS", now)
            return
        if self.yaw is None or self.last_odom_s is None or now - self.last_odom_s > self.odom_timeout_s:
            self.publish_stop("WAIT_ODOMETRY", now)
            return
        if self.latest_image is None or self.last_camera_s is None or now - self.last_camera_s > self.camera_timeout_s:
            self.publish_stop("WAIT_CAMERA", now)
            return

        if self.completed:
            self.publish_stop("DELIVERY_COMPLETE", now)
            return
        if self.red_light_latched:
            self.publish_stop("STOP_RED_LIGHT", now)
            return
        if self.obstacle_active or now < self.obstacle_clear_until:
            self.publish_stop("STOP_CAMERA_OBSTACLE", now)
            return
        if now < self.stop_sign_until:
            self.publish_stop("STOP_SIGN", now)
            return

        x, y = self.position_xy
        while self.waypoint_index < len(self.route):
            goal_x, goal_y = self.route[self.waypoint_index]
            if math.hypot(goal_x - x, goal_y - y) > self.waypoint_radius:
                break
            self.waypoint_index += 1
        if self.waypoint_index >= len(self.route):
            self.completed = True
            self.publish_stop("DELIVERY_COMPLETE", now)
            return

        goal = self.route[self.waypoint_index]
        linear, angular, _ = waypoint_velocity(
            x,
            y,
            self.yaw,
            goal[0],
            goal[1],
            self.max_linear_speed,
            self.max_angular_speed,
            self.lookahead_distance,
        )

        command = Twist()
        command.linear.x = linear
        command.angular.z = angular
        self.cmd_pub.publish(command)
        self.state_pub.publish(String(data="GPS_WAYPOINT_FOLLOW"))
        self.write_log(now, "GPS_WAYPOINT_FOLLOW", linear, angular, goal)
        self.publish_debug("GPS_WAYPOINT_FOLLOW", goal)

    def destroy_node(self):
        if rclpy.ok():
            self.cmd_pub.publish(Twist())
        self.log_file.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = GpsCameraController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
