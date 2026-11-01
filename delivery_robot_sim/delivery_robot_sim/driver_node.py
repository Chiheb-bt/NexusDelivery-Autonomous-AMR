try:
    from rclpy._rclpy_pybind11 import RCLError
except ImportError:
    RCLError = Exception
"""Nœud principal : perception (caméra) + machine à états + PID -> /cmd_vel.

Mesure aussi la latence : (heure de publication de la commande) - (horodatage de l'image),
en temps de simulation, et le temps de calcul réel du nœud. Journal CSV dans log_path.
Garantit la sécurité : arrêt immédiat sur timeout de la caméra ou perte prolongée de perception.
"""
import csv
import json
import os
import time

import cv2
import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from delivery_robot_sim import vision
from delivery_robot_sim.control import PID, MissionFSM, Perception
from delivery_robot_sim.yolo_detector import (
    YOLODetector,
    apply_overrides,
    is_forward_obstacle,
)


def image_to_bgr(msg):
    arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, -1)
    if msg.encoding == "rgb8":
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    if msg.encoding == "bgr8":
        return arr.copy()
    raise ValueError(f"encodage non géré : {msg.encoding}")


class Driver(Node):
    def __init__(self):
        super().__init__("driver_node")
        d = self.declare_parameter
        d("use_clahe", True); d("kp", 0.012); d("ki", 0.0); d("kd", 0.0)
        d("v_base", 0.25); d("x_target", 162.0); d("line_threshold", 170)
        d("roi_line", [110, 200, 0, 320]); d("roi_line_narrow", [110, 200, 60, 260])
        d("roi_obstacle", [90, 200, 60, 260])
        d("thr_obstacle", 2500); d("thr_red", 150); d("thr_green", 40)
        d("traffic_lights_enabled", True)
        d("obstacle_mode", "avoid")  # "avoid" or "stop"
        d("max_fill", 0.6); d("yolo_every_n", 3); d("yolo_enabled", False); d("yolo_model", "yolov8n.pt"); d("yolo_conf", 0.25)
        d("w_avoid", 0.6); d("t_left", 0.55); d("t_straight", 4.5)
        d("t_right", 1.0); d("t_reacquire", 8.0); d("lockout", 12.0)
        d("log_path", "/tmp/driver_log.csv")
        d("watchdog_timeout_s", 0.6)
        g = lambda n: self.get_parameter(n).value

        self.use_clahe = g("use_clahe")
        self.x_target = g("x_target")
        self.thresh = g("line_threshold")
        self.traffic_lights_enabled = g("traffic_lights_enabled")
        self.roi = list(g("roi_line")); self.roi_narrow = list(g("roi_line_narrow"))
        self.roi_obs = list(g("roi_obstacle"))
        self.max_fill = g("max_fill")
        self.yolo_every_n = max(1, int(g("yolo_every_n")))
        self.watchdog_timeout_s = float(g("watchdog_timeout_s"))
        self.n_frames, self.yolo_cache = 0, []
        self.yolo_detector = None

        if g("yolo_enabled"):
            try:
                model_path = g("yolo_model")
                if not os.path.isabs(model_path):
                    model_path = os.path.join(
                        get_package_share_directory("delivery_robot_sim"), model_path
                    )
                if not os.path.isfile(model_path):
                    self.get_logger().warning(
                        f"Configured YOLO model not found: {model_path}. Gracefully falling back to classical perception."
                    )
                else:
                    self.yolo_detector = YOLODetector(model_path=model_path, conf=g("yolo_conf"))
                    if not self.yolo_detector.available():
                        self.get_logger().warning(
                            "YOLO could not be initialized (ultralytics missing). Falling back to classical perception."
                        )
                        self.yolo_detector = None
                    else:
                        warmup_started = time.perf_counter()
                        self.yolo_detector.detect(np.zeros((240, 320, 3), dtype=np.uint8))
                        warmup_ms = (time.perf_counter() - warmup_started) * 1000.0
                        self.get_logger().info(f"YOLO active with model {model_path} (warmed up in {warmup_ms:.0f} ms)")
            except Exception as exc:
                self.get_logger().warning(f"Optional YOLO loading error: {exc}. Continuing with classical vision.")
                self.yolo_detector = None
        else:
            self.get_logger().info("YOLO is disabled; using classical camera perception only")

        self.pid = PID(g("kp"), g("ki"), g("kd"))
        self.fsm = MissionFSM(
            v_base=g("v_base"), t_left=g("t_left"), t_straight=g("t_straight"),
            t_right=g("t_right"), t_reacquire=g("t_reacquire"), lockout=g("lockout"),
            w_avoid=g("w_avoid"), thr_obstacle=g("thr_obstacle"),
            thr_red=g("thr_red"), thr_green=g("thr_green"),
            obstacle_mode=g("obstacle_mode")
        )
        self.v_base = g("v_base")
        self.last_t = None
        self.last_img_time = None
        self.watchdog_tripped = False
        self.last_logged_state = None

        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.state_pub = self.create_publisher(String, "/mission/state", 10)
        self.dbg = self.create_publisher(Image, "/perception/debug", 1)
        self.objects_pub = self.create_publisher(String, "/perception/objects", 10)
        self.create_subscription(Image, "/camera/image_raw", self.on_image, qos_profile_sensor_data)

        # Watchdog timer to ensure robot stops if camera feed stalls
        self.watchdog_timer = self.create_timer(0.2, self.check_watchdog)

        self.f = open(g("log_path"), "w", newline="")
        self.csv = csv.writer(self.f)
        self.csv.writerow(["t_sim", "state", "line_x", "err_px", "v", "w",
                           "red", "green", "obstacle", "latency_sim_s", "proc_ms", "yolo_labels", "yolo_ms"])
        self.get_logger().info("driver_node prêt : en attente d'images sur /camera/image_raw")

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def check_watchdog(self):
        if not rclpy.ok() or not self.context.ok():
            return
        now = self.now_s()
        if self.last_img_time is not None and (now - self.last_img_time > self.watchdog_timeout_s):
            if not self.watchdog_tripped:
                try:
                    self.get_logger().error(
                        f"Watchdog triggered: no camera frames for {now - self.last_img_time:.2f} s. Stopping robot."
                    )
                except Exception:
                    pass
                self.watchdog_tripped = True
            try:
                if rclpy.ok() and self.context.ok():
                    self.pub.publish(Twist())
                    self.state_pub.publish(String(data="CAMERA_TIMEOUT_STOP"))
            except (RCLError, rclpy.executors.ExternalShutdownException, Exception):
                pass

    def on_image(self, msg):
        if not rclpy.ok() or not self.context.ok():
            return
        try:
            self._process_image(msg)
        except (RCLError, rclpy.executors.ExternalShutdownException):
            return

    def _process_image(self, msg):
        t0 = time.perf_counter()
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        now = self.now_s()
        dt = 0.15 if self.last_t is None else max(now - self.last_t, 1e-3)
        self.last_t = now
        self.last_img_time = now
        if self.watchdog_tripped:
            self.get_logger().info("Camera stream resumed. Resuming autonomous pipeline.")
            self.watchdog_tripped = False

        camera_bgr = image_to_bgr(msg)
        img = vision.preprocess(camera_bgr, self.use_clahe)
        yolo_detections, yolo_ms = [], 0.0
        if self.yolo_detector is not None:
            if self.n_frames % self.yolo_every_n == 0:
                ty = time.perf_counter()
                self.yolo_cache = self.yolo_detector.detect(camera_bgr)
                yolo_ms = (time.perf_counter() - ty) * 1000.0
            self.n_frames += 1
            yolo_detections = self.yolo_cache

        roi = self.roi_narrow if self.fsm.state == "REACQUIRE" else self.roi
        x_hat, _ = vision.line_barycentre(img, roi, self.thresh, max_fill=self.max_fill)
        red, green = (
            vision.traffic_light_areas(img)
            if self.traffic_lights_enabled
            else (0, 0)
        )
        obs = vision.orange_density(img, self.roi_obs)
        yolo_names = [d.label.lower() for d in yolo_detections]
        red, green, obs = apply_overrides(
            yolo_detections,
            img,
            red,
            green,
            obs,
            vision.traffic_light_areas,
            traffic_lights_enabled=self.traffic_lights_enabled,
        )
        cmd = self.fsm.update(now, Perception(x_hat, obs, red, green))

        if cmd.state != self.last_logged_state:
            self.get_logger().info(f"Transition état mission : {self.last_logged_state} -> {cmd.state}")
            self.last_logged_state = cmd.state

        self.state_pub.publish(String(data=cmd.state))
        self.objects_pub.publish(String(data=json.dumps({
            "stamp": stamp,
            "frame_id": msg.header.frame_id,
            "detections": [
                {
                    "label": detection.label,
                    "confidence": round(detection.confidence, 3),
                    "bbox_xyxy": [
                        round(detection.x1, 1),
                        round(detection.y1, 1),
                        round(detection.x2, 1),
                        round(detection.y2, 1),
                    ],
                    "forward_obstacle": is_forward_obstacle(detection, img.shape),
                }
                for detection in yolo_detections
            ],
        })))

        err = None
        if cmd.mode == "lane":
            if x_hat is not None:
                err = x_hat - self.x_target
                w = self.pid.update(err, dt)
                v = cmd.v * max(0.4, 1.0 - min(abs(err) / 200.0, 0.6))
            else:
                v, w = cmd.v, 0.0
        else:
            v, w = cmd.v, cmd.w
            self.pid.reset()

        tw = Twist()
        tw.linear.x, tw.angular.z = float(v), float(w)
        self.pub.publish(tw)

        lat = self.now_s() - stamp
        proc = (time.perf_counter() - t0) * 1000.0
        self.csv.writerow([f"{now:.3f}", cmd.state, x_hat, err, f"{v:.3f}", f"{w:.3f}",
                           red, green, obs, f"{lat:.3f}", f"{proc:.1f}", ",".join(yolo_names), f"{yolo_ms:.1f}"])
        self.f.flush()
        self.publish_debug(img, roi, x_hat, cmd, msg)

    def publish_debug(self, img, roi, x_hat, cmd, msg):
        out = img.copy()
        r0, r1, c0, c1 = roi
        cv2.rectangle(out, (c0, r0), (c1, r1), (0, 255, 255), 1)
        if x_hat is not None:
            cv2.line(out, (int(x_hat), r0), (int(x_hat), r1), (0, 0, 255), 2)
        cv2.line(out, (int(self.x_target), r0), (int(self.x_target), r1), (0, 255, 0), 1)
        for detection in self.yolo_cache:
            x1, y1, x2, y2 = (int(v) for v in (
                detection.x1, detection.y1, detection.x2, detection.y2
            ))
            obstacle = is_forward_obstacle(detection, out.shape)
            color = (0, 0, 255) if obstacle else (255, 180, 0)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                out,
                f"{detection.label} {detection.confidence:.2f}",
                (x1, max(y1 - 4, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
            )
        cv2.putText(out, cmd.state, (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        m = Image()
        m.header = msg.header
        m.height, m.width, m.encoding = out.shape[0], out.shape[1], "bgr8"
        m.step = out.shape[1] * 3
        m.data = out.tobytes()
        if rclpy.ok() and self.context.ok():
            try:
                self.dbg.publish(m)
            except (RCLError, rclpy.executors.ExternalShutdownException, Exception):
                pass

    def destroy_node(self):
        try:
            if hasattr(self, "watchdog_timer") and self.watchdog_timer is not None:
                self.watchdog_timer.cancel()
            if rclpy.ok() and self.context.ok():
                self.pub.publish(Twist())
        except (RCLError, rclpy.executors.ExternalShutdownException, Exception):
            pass
        finally:
            if hasattr(self, "f") and not self.f.closed:
                self.f.close()
            super().destroy_node()


def main():
    rclpy.init()
    node = Driver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException, RCLError):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.try_shutdown()
