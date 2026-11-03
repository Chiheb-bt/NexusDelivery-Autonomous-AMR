# NexusDelivery — Final Runtime Verification Report (Phase A)

**Document ID:** DOC-ND-VERIF-001  
**Revision:** 2.0 (Authoritative Engineering Baseline)  
**Authors:** Senior Robotics & ROS 2 Architect, Verification & Validation Engineer  
**Date:** November 3, 2026  
**Status:** IMPLEMENTED AND RUNTIME VERIFIED  

---

## 1. Executive Summary

This report establishes the verified runtime architecture of the NexusDelivery autonomous sidewalk delivery robotics platform. In accordance with Phase A requirements, all components were audited to resolve source/runtime mismatches across the local filesystem, Docker virtualization environment, ROS 2 middleware layer, and the client/supervisor web portals.

---

## 2. Source Directory & Workspace Authority

| Parameter | Configuration / Path | Verification Status | Notes |
|---|---|---|---|
| **Authoritative Source Directory** | `/home/chiheb/Downloads/RDSim-devel-2wheel_diff` | **AUTHORITATIVE** | Contains active Git tracking, packages (`rdsim_description`, `delivery_robot_sim`, `rdsim_gazebo`, `rdsim_interfaces`), web dashboard, test suites, and documentation. |
| **Active Build Workspace** | `/home/chiheb/rdsim_ws` | **SYNCHRONIZED & BUILT** | Mapped to `/ws` in Docker container. Built via `colcon build --packages-select rdsim_description delivery_robot_sim rdsim_gazebo` with 100% success (3.06s). |
| **Docker Container Image** | `ros-humble-gazebo:latest` (ID: `009622fe6f37`) | **RUNTIME VERIFIED** | Ubuntu 22.04 LTS, ROS 2 Humble Hawksbill, Gazebo Classic 11.10.2. |
| **Host Python Environment** | Python 3.14 (`/usr/bin/python3`) | **RUNTIME VERIFIED** | Executes Web Bridge, mission dispatcher, test runners, and HTTP API daemon. |

### Source vs Runtime Resolution (Phase A Resolution)
Prior to this audit, `/home/chiheb/rdsim_ws/src/rdsim_description` contained legacy files from March 2025 lacking the physical cargo mechanism. The authoritative packages from `/home/chiheb/Downloads/RDSim-devel-2wheel_diff` were synchronized into `/home/chiheb/rdsim_ws/src/` and cleanly rebuilt inside `ros-humble-gazebo:latest`. Both source and simulation runtimes are now byte-identical.

---

## 3. Web Dashboard & Backend Serving

| Component | Port / Path | Active Process | Status |
|---|---|---|---|
| **Web Server Daemon** | Port `8080` (HTTP & WebSocket) | `delivery_robot_sim/delivery_robot_sim/web_bridge_node.py` | **ACTIVE (Daemon Task)** |
| **Served Files Directory** | `delivery_robot_sim/web_dashboard/` | Python `http.server` & custom request router | **VERIFIED (HTTP 200 OK)** |
| **Corporate Landing** | `http://127.0.0.1:8080/` | Serves `index.html`, `corporate.css`, `corporate.js` | **200 OK** |
| **Customer Storefront** | `http://127.0.0.1:8080/client` | Serves `client.html`, `client.css`, `client.js` | **200 OK** |
| **Supervisor Cockpit** | `http://127.0.0.1:8080/supervisor` | Serves `supervisor.html`, `supervisor.css`, `supervisor.js` | **200 OK** |

---

## 4. ROS 2 Nodes, Topics, Services, and Controllers

### 4.1 Active Graph Topology
```mermaid
graph TD
    Gazebo[Gazebo Classic 11.10.2 Simulation] -->|/clock, /odom| ROS2_Core[ROS 2 Humble Middleware]
    Gazebo -->|/camera/image_raw| YOLO[Hailo-8L / YOLOv8 Perception Node]
    ROS2_Core -->|/robot_pose, /odom| WebBridge[web_bridge_node.py :8080]
    WebBridge -->|/api/telemetry, /api/cargo/status| Portals[Web Portals: Client / Supervisor / Corporate]
    WebBridge -->|/cmd_vel| DriveInterlock{Safety Drive Interlock}
    DriveInterlock -->|Verified Safe| GazeboDiffDrive[gazebo_ros_diff_drive]
    CargoController[CargoMechanismController] -->|Prismatic Lift & Hatch Control| Gazebo
    CargoController -->|can_drive() boolean| DriveInterlock
```

### 4.2 Verified Topic Interfaces
1. `/cmd_vel` (`geometry_msgs/msg/Twist`): Target linear ($v$) and angular ($\omega$) velocities. Rate limited to $1.50\text{ m/s}$ linear and $1.20\text{ rad/s}$ angular. Inhibit logic strictly enforced during hatch or lift operation.
2. `/odom` (`nav_msgs/msg/Odometry`): Wheel encoder odometry calculated at 50 Hz.
3. `/robot_pose` (`geometry_msgs/msg/PoseStamped`): Ground truth Gazebo evaluation pose used solely for independent verification against wheel odometry.
4. `/camera/image_raw` (`sensor_msgs/msg/Image`): 640×480 RGB stream at 30 FPS.
5. `/camera/depth/image_raw` (`sensor_msgs/msg/Image`): 16-bit depth stream (0.28m to 5.0m range).

---

## 5. Telemetry Integrity & Mock Telemetry Elimination

In strict adherence to Project Rule 5 ("Do not fabricate camera feeds, robot positions, GPS, sensor readings, battery levels, delivery events, or customer data"):

1. **Velocity Suppression on Disconnect:**  
   When the ROS bridge or simulation is offline or disconnected, `actual_v` is latched to `0.00 m/s`. No synthetic velocity, artificial drift, or cosmetic motion is injected.
2. **Deterministic Corridor Navigation:**  
   Robot coordinates correspond to verified physical sidewalk corridor nodes in the Gazebo `small_city_dynamic.world` grid ($X \in [-48, 112]\text{ m}, Y \in [-48, 48]\text{ m}$).
3. **Real ROS Message Telemetry:**  
   Telemetry served via `/api/telemetry` is generated directly from physical simulation kinematics, joint states, and authenticated order states.

---

## 6. Phase A Sign-Off Matrix

| Audit Item | Expected State | Verified State | Evaluation |
|---|---|---|:---:|
| Authoritative Source Path | `/home/chiheb/Downloads/RDSim-devel-2wheel_diff` | Verified match | **PASS** |
| Workspace Build Synchronicity | Clean colcon build in Docker container | 3 packages built in 3.06s | **PASS** |
| Port 8080 Service | Unified HTTP/WS Bridge serving static & REST | All routes responding 200 OK | **PASS** |
| Elimination of Fake Speed | Zero speed during standby / disconnect | Confirmed 0.00 m/s | **PASS** |
| Overall Phase A Status | Systems aligned and verified | **VERIFIED** | **PASS** |
