# NEXUSDELIVERY — CURRENT SYSTEM BASELINE & ARCHITECTURAL AUDIT
**Authoritative Repository:** `/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY`  
**ROS 2 Workspace:** `/home/chiheb/rdsim_ws`  
**Target Environment:** ROS 2 Humble • Gazebo Classic 11.10.2 • Ubuntu 22.04 LTS (Docker Container `rdsim_sim_container`)  
**Evaluation Date:** November 4, 2026  
**Engineering Team:** Senior Robotics Software Architect, Controls Engineer, Full-Stack Web Engineer, QA Lead  

---

## 1. System Architecture Baseline

### 1.1 Mobile Platform Kinematics & Mechanics
* **Configuration:** Differential-drive 2-wheel ground mobile platform with passive front and rear castor stabilization.
* **Actuation:** Dual independent DC hub motors commanded via `/cmd_vel` (`geometry_msgs/msg/Twist`).
* **Wheel Base & Radius:** Wheel track separation $L = 0.52\,\text{m}$, wheel radius $r = 0.165\,\text{m}$.
* **Payload Bay:** Sealed rear motorized cargo compartment with single-axis revolute hatch joint (`cargo_hatch_joint`) actuating between $0.0^\circ$ ($0.0\,\text{rad}$, locked) and $60.1^\circ$ ($1.05\,\text{rad}$, unlatched).
* **Hardware Verification Status:** URDF/Xacro verified in [`rdsim.urdf.xacro`](file:///home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY/rdsim_description/urdf/rdsim.urdf.xacro) and [`rdsim.camera_only.gazebo.xacro`](file:///home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY/rdsim_description/urdf/rdsim.camera_only.gazebo.xacro).

### 1.2 Sensor Suite (Zero LiDAR, Zero GPS)
* **RGB-D Vision:** Front-facing depth camera mounted at $(x=+0.32\,\text{m}, z=+0.38\,\text{m})$ relative to base footprint.
  - Optical resolution: $640 \times 480$ pixels.
  - Configured update rate: $30\,\text{Hz}$.
  - ROS 2 topics: `/camera/image_raw` (`sensor_msgs/msg/Image`), `/camera/depth/image_raw` (`sensor_msgs/msg/Image`), `/camera/camera_info`.
* **Inertial Measurement Unit:** 6-DOF IMU mounted at chassis center.
  - Update rate: $50\,\text{Hz}$ (`sensor_msgs/msg/Imu` on `/imu`).
* **Wheel Odometry:** Encoders publishing wheel odometry at $50\,\text{Hz}$ (`nav_msgs/msg/Odometry` on `/odom`).
* **Hatch Joint Feedback:** Gazebo joint state publisher (`libgazebo_ros_joint_state_publisher.so`) publishing `cargo_hatch_joint` state on `/joint_states`.
* **Zero LiDAR / Zero GPS Mandate:** Confirmed. The navigation stack strictly computes corridor tracking from `/odom`, `/imu`, and vision obstacle depth. GPS coordinates displayed on the UI are mathematical projections strictly for client visualization.

---

## 2. Process & Execution Topology

```
+-----------------------------------------------------------------------------------+
|                            ROS 2 HUMBLE COMPUTATIONAL GRAPH                       |
|                                                                                   |
|  [Gazebo gzserver / gzclient] <---> [libgazebo_ros_diff_drive]                    |
|             |                                   |                                 |
|             +--> /camera/image_raw              +--> /odom (50 Hz)                |
|             +--> /camera/depth/image_raw        +--> /joint_states                |
|             +--> /imu (50 Hz)                   ^                                 |
|                         |                       | /cmd_vel                        |
|                         v                       |                                 |
|             +-------------------------+         |                                 |
|             |    driver_node          |---------+                                 |
|             |    (city_driver_node)   |<--------+                                 |
|             +-------------------------+         | /delivery/current_target        |
|                         ^                       |                                 |
|                         | /mission/state        |                                 |
|                         v                       v                                 |
|             +---------------------------------------+                             |
|             |          order_manager_node           |                             |
|             +---------------------------------------+                             |
|                         ^                       ^                                 |
|       /delivery/new_order|                       | /delivery/confirm_handover      |
|                         v                       v                                 |
|             +---------------------------------------+                             |
|             |            web_bridge_node            |                             |
|             |      (REST API & Static Web Server)   |                             |
|             +---------------------------------------+                             |
|                                 | HTTP:8080                                       |
|                                 v                                                 |
|             [ Customer Portal: http://localhost:8080/client ]                     |
|             [ Fleet Cockpit:   http://localhost:8080/supervisor ]                 |
+-----------------------------------------------------------------------------------+
```

---

## 3. Active Workspace and Synchronisation Audit

* **Repository Directory:** `/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY` (Authoritative Git repo).
* **Workspace Directory:** `/home/chiheb/rdsim_ws` (ROS 2 build directory).
* **Container Mapping:**
  - `/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY` is mounted to `/rdsim` inside Docker.
  - `/home/chiheb/rdsim_ws` is mounted to `/ws` inside Docker.
* **Launch Pipeline:** [`run_visual_simulation.sh`](file:///home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY/run_visual_simulation.sh) executes `run_demo.sh` inside Docker container `rdsim_sim_container`, launching Gazebo Classic with `small_city_dynamic.world` and [`camera_only.launch.py`](file:///home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY/rdsim_gazebo/launch/camera_only.launch.py).

---

## 4. Initial Issue Baseline Summary

| Issue Area | Baseline Symptom | Engineering Severity |
|---|---|---|
| **Customer Portal** | White-on-white text, split zigzag hero layout, low contrast, unpolished navigation. | **CRITICAL (UX)** |
| **Hatch Handover** | Customer entering OTP opens hatch, but does not close and return to depot; missing explicit receipt confirmation step. | **CRITICAL (Functional)** |
| **Closed-Loop Feedback** | `web_bridge_node` did not subscribe to `/joint_states` to physically verify hatch angle before driving. | **HIGH (Safety/FSM)** |
| **Simulation FPS** | Shadow mapping and 50-iteration ODE solver throttled Gazebo to 0.80 Real Time Factor and 15-20 GUI FPS. | **HIGH (Performance)** |
| **Robot Speed Profile** | Over-conservative 3.2m proximity caution limit constantly throttled robot to 0.35-0.65 m/s. | **MEDIUM (Motion Dynamics)** |

