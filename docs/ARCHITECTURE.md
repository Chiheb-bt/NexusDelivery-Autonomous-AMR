# Chiheb Robotics — NexusDelivery Architecture & Systems Design

**Platform:** Chiheb Robotics NexusDelivery Autonomous Urban Delivery Platform  
**Lead Robotics Architect:** Chiheb  
**Framework:** ROS 2 Humble | Gazebo Classic 11.10.2 | Python 3.10  
**Sensor Constraints:** Strictly Front RGB Camera + RGB-D Depth Camera + Odometry + IMU (**Zero LiDAR, Zero GPS**)

---

## 1. Executive System Overview

The **NexusDelivery** platform is an autonomous urban ground delivery platform developed by **Chiheb Robotics**. Designed specifically for complex urban streetscapes and sidewalk environments, the system operates completely independently of LiDAR and satellite GPS, relying exclusively on fused monocular/depth computer vision, wheel odometry, and an inertial measurement unit (IMU).

```
                      +---------------------------------------+
                      |      CHIHEB ROBOTICS FLEET CONTROL    |
                      |   Web Dashboard (HTTP / MJPEG: 8080)  |
                      +-------------------+-------------------+
                                          |
                                          v  /delivery/new_order
+-----------------------------------------------------------------------------------------+
|                                ROS 2 AUTONOMY STACK                                     |
|                                                                                         |
|  +---------------------+        +--------------------+        +----------------------+  |
|  |   RGB-D Camera      |        |   Wheel Odometry   |        |      6-DOF IMU       |  |
|  |  /camera/image_raw  |        |       /odom        |        |        /imu          |  |
|  | /camera/depth/...   |        |                    |        |                      |  |
|  +----------+----------+        +---------+----------+        +----------+-----------+  |
|             |                             |                              |              |
|             v                             v                              v              |
|  +---------------------+        +----------------------------------------------------+  |
|  | Computer Vision     |        | Dead-Reckoning Localization & Pose Tracking        |  |
|  | - Corridor Obstacle |        +-------------------------+--------------------------+  |
|  | - Pedestrian Model  |                                  |                             |
|  | - Traffic Light Det |                                  v                             |
|  +----------+----------+        +----------------------------------------------------+  |
|             |                   |   Topological Road Graph & A* Route Planner        |  |
|             |                   +-------------------------+--------------------------+  |
|             |                                             |                             |
|             v                                             v                             |
|  +-----------------------------------------------------------------------------------+  |
|  |                        City Driver Node (Motion Engine)                           |  |
|  |  - Pure Pursuit Corridor Guidance       - Smooth Velocity Ramping (1.20 m/s^2)   |  |
|  |  - Latched Dynamic Obstacle Bypass       - Turn-in-Place Heading Re-alignment     |  |
|  +-----------------------------------------------------------------------------------+  |
|             ^                                             ^                             |
|             |                                             |                             |
|  +----------+----------+                        +---------+----------+                  |
|  |  Safety Supervisor  |                        |   Order Manager    |                  |
|  |  - Latched Faults   |                        |   - Multi-drop FSM |                  |
|  |  - TTC Stop / Slow  |                        |   - Customer OTP   |                  |
|  +---------------------+                        +--------------------+                  |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Sensor Perception Stack (Camera-Only)

### 2.1 Front RGB Camera (`/camera/image_raw`)
- **Resolution:** $320 \times 240$ pixels @ 30 FPS.
- **Preprocessing:** Contrast Limited Adaptive Histogram Equalization (CLAHE) for illumination invariance across varying shadows and urban building façades.
- **Traffic Light Detection:** Real-time HSV color segmentation with contour area filtering and multi-frame temporal confirmation for red/green signaling at urban intersections.

### 2.2 Depth Sensing (`/camera/depth/image_raw`)
- **Format:** 32-bit floating point depth (meters) or 16-bit integer millimeter encoding.
- **Corridor Fusion:** Isolates the robot's projected $0.90\text{m}$ clearance envelope.
- **Pedestrian Classification:** Evaluates vertical variance $\sigma_y$ and depth density to identify human pedestrians versus static street furniture, automatically calculating Time-to-Collision (TTC).

---

## 3. Localization & Road Navigation Graph

### 3.1 Zero-GPS Dead Reckoning
- The system forbids GPS coordinates (`/gps/fix`) during runtime.
- High-rate wheel encoder odometry (`/odom`) is fused with 6-DOF IMU yaw angular rates (`/imu`) to provide drift-compensated metric localization across the entire city grid.

### 3.2 Topological Road Network
- Navigable city avenues are modeled as metric corridor segments:
  - **Central Boulevard:** $y = 0.0\text{m}, x \in [-45.5, 108.0]\text{m}$
  - **North Avenue:** $x = -15.0\text{m}, y \in [-45.0, 45.0]\text{m}$
  - **East Avenue:** $x = 45.0\text{m}, y \in [-45.0, 45.0]\text{m}$
- Pure Python A* graph search plans optimal paths between arbitrary street locations, snapping off-road customer drop-off points to sidewalk access portals.

---

## 4. Indoor Logistics Depot Hub & Round-Trip Docking

- **Central Depot Coordinates:** $x \in [-34.5, -29.0]\text{m}, y \in [-2.8, 1.2]\text{m}, z \in [0, 3.2]\text{m}$.
- **Access Bay Door:** Open portal at $x = -29.0\text{m}, y \in [-1.85, 0.35]\text{m}$.
- **Interior Docking Station:** Centered at $(-31.5, -0.75)\text{m}$ with optical charging contact pad.
- **Lifecycle:**
  1. The robot initializes *inside* the facility on the charging dock.
  2. Cargo manifest is loaded during a $2.0\text{s}$ loading dwell.
  3. The robot rolls out through the bay door onto Central Boulevard.
  4. Completes all customer delivery stops along the urban avenue.
  5. Navigates back, enters through the bay door, and docks inside the facility.

---

## 5. Safety Supervisor & Motion Control

- **Safety Supervisor FSM:** 10 verified safety states:
  - `NORMAL_DRIVING`, `CAUTION_SLOWDOWN`, `STOP_OBSTACLE`, `STOP_CROSSING_PEDESTRIAN`, `EMERGENCY_STOP`, `ESTOP_COMMANDED`, `SENSOR_TIMEOUT_ESTOP`, `DEPTH_CORRUPTION_ESTOP`, `RED_TRAFFIC_LIGHT`, `RECOVERY_MANEUVER`.
- **Latched Obstacle Avoidance:** When a dynamic obstacle blocks the path, the planner latches a $\pm 0.65\text{m}$ lateral offset, holds the bypass lane for $6.5\text{m}$, and merges smoothly back to the corridor centerline without oscillations.
- **Motion Profiling:** Linear acceleration limited to $1.20\text{m/s}^2$ with cubic velocity blending and critically damped yaw rates to prevent wheel slip.
