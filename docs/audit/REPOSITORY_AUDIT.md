# NexusDelivery — Comprehensive Repository Audit & Engineering Baseline

**Audit Date:** November 2, 2026  
**Auditor:** Principal Robotics & Systems Engineering Team  
**Repository Target:** `Chiheb-bt/NexusDelivery-Autonomous-AMR`  
**Current Baseline Git Commit:** `32b108a`  
**Target Standard:** Commercial Robotics Readiness & Simulation-to-Hardware Verifiability

---

## 1. Executive Summary

This repository implements an autonomous sidewalk delivery robot simulation platform using **ROS 2 Humble** and **Gazebo Classic 11** on Ubuntu 22.04 LTS (Jammy Jellyfish). The core robotics stack relies on differential-drive kinematics, vision-based depth obstacle detection, a 10-state safety supervisor, a topological road network with A* routing, and an order management state machine.

All **84 unit tests** in `delivery_robot_sim/tests` pass in under 3.0 seconds.

However, an exhaustive audit reveals substantial architectural, geospatial, security, and integrity discrepancies between the declared marketing claims and the actual codebase. Most critically, the existing web dashboards have used decorative external maps (CartoDB Dark Matter / Esri Satellite centered on Tunis or other global cities) which are **completely decoupled from the actual Gazebo simulation world** where the robot physically operates.

---

## 2. Inventory of Repository Components

### 2.1 ROS 2 Packages & Interfaces

| Package Name | Type | Directory | Declared Dependencies | Status |
|:---|:---:|:---|:---|:---:|
| `delivery_robot_sim` | `ament_python` | `delivery_robot_sim/` | `rclpy`, `std_msgs`, `nav_msgs`, `sensor_msgs`, `geometry_msgs`, `cv_bridge`, `opencv-python`, `ultralytics` | **Active & Functional** |
| `rdsim_gazebo` | `ament_cmake` | `rdsim_gazebo/` | `gazebo_ros`, `gazebo_plugins`, `geometry_msgs`, `nav_msgs`, `rclcpp`, `sensor_msgs`, `std_msgs` | **Active & Functional** |
| `rdsim_description` | `ament_cmake` | `rdsim_description/` | `urdf`, `xacro`, `robot_state_publisher` | **Active & Functional** |
| `rdsim_interfaces` | `ament_cmake` | `rdsim_interfaces/` | `rosidl_default_generators`, `std_msgs`, `builtin_interfaces` | **Active (Custom Msgs)** |

### 2.2 Robot Description & URDF Model

- **File:** `rdsim_description/urdf/rdsim.urdf.xacro`
- **Kinematics:** Differential drive (two active drive wheels with radius $r = 0.098\text{ m}$, wheel separation $L = 0.43\text{ m}$, and passive front/rear support casters).
- **Sensors Modeled in URDF:**
  - Intel RealSense D435i (`camera_link`): Gazebo camera plugin outputting `/camera/image_raw` (RGB $320\times 240$) and `/camera/depth/image_raw` (32FC1 depth pointcloud).
  - IMU (`imu_link`): Outputting `/imu` at 50 Hz.
  - Wheel Encoders: Gazebo differential drive plugin publishing `/odom` and broadcasting `odom` $\rightarrow$ `base_link` TF.
  - Motorized Cargo Hatch: Joint `hatch_joint` (revolute, limit $0.0$ to $1.05\text{ rad} \approx 60^\circ$) controlled via gazebo position controller plugin.
- **Removed Sensors:** 2D/3D LiDAR ray plugins were deliberately disabled/removed to enforce the "Camera-Only / Zero-LiDAR" design constraint.

### 2.3 Gazebo Simulation Worlds

- **Primary Active World:** `rdsim_gazebo/worlds/small_city_dynamic.world` (176 KB, 5,949 lines of SDF 1.6).
  - Ground Plane & Terrain: `model://city_terrain` covering $[-48.0, 112.0]\text{ m} \times [-48.0, 48.0]\text{ m}$.
  - Features: Multi-block urban street grid, sidewalks, crosswalks, controlled intersections with traffic lights, building blocks, and an indoor logistics depot at $[-35.0, -28.0]\text{ m} \times [-2.5, 4.5]\text{ m}$.
  - Dynamic Actors: Includes walking pedestrian via `libgazebo_ros_actor.so` and stop lights via `traffic_light_node`.
- **Secondary World:** `rdsim_gazebo/worlds/small_city.world` (static version without animated actors).
- **Minimal Test World:** `rdsim_gazebo/worlds/camera_delivery.world` (single corridor test track).

### 2.4 Autonomy & Navigation Stack (`delivery_robot_sim`)

| Module | File | Lines | Primary Responsibility | Truth Source |
|:---|:---|:---:|:---|:---:|
| `city_driver_node.py` | `delivery_robot_sim/city_driver_node.py` | 1,120 | Pure Pursuit corridor follower, obstacle avoidance, speed ramp ($1.2\text{ m/s}^2$) | `/odom`, `/camera/depth/image_raw` |
| `route_planner.py` | `delivery_robot_sim/route_planner.py` | 539 | Topological road network graph, A* search, Liang-Barsky building collision check | Predefined city geometry |
| `order_manager_node.py`| `delivery_robot_sim/order_manager_node.py`| 372 | Multi-drop order queue, dwell timer, OTP emission | Simulation clock `/clock` |
| `order_manager.py` | `delivery_robot_sim/order_manager.py` | 338 | Order FSM, priority sorting, HMAC-SHA256 OTP generation | Python standard library |
| `safety_supervisor.py` | `delivery_robot_sim/safety_supervisor.py` | 248 | 10-state deterministic safety FSM, sensor timeout latching | Periodic watchdog checks |
| `vision.py` | `delivery_robot_sim/vision.py` | 490 | Depth corridor isolation ($0.9\text{ m}$ envelope), HSV traffic light detection | OpenCV |
| `cargo_delivery_manager.py`| `delivery_robot_sim/cargo_delivery_manager.py`| 285 | Gazebo parcel spawn/despawn, motorized hatch actuation | Gazebo ROS services |
| `evaluator_node.py` | `delivery_robot_sim/evaluator_node.py` | 260 | Mission distance, collision counter, summary generator | `/odom`, `/gazebo/model_states` |
| `web_bridge_node.py` | `delivery_robot_sim/web_bridge_node.py` | 1,457 | HTTP server (port 8080), telemetry serializer, order gateway | ROS 2 topics + in-memory store |

---

## 3. Detailed Audit Findings Against Engineering Rules

### Finding 1: Disconnection Between Web Map and Gazebo Simulation
- **Current State:** The web dashboards (`client.js`, `supervisor.js`) initialize Leaflet with real-world tile providers (CartoDB Dark Matter, Esri Satellite) centered at Avenue Habib Bourguiba in Tunis (`36.8005° N, 10.1800° E`) or preset world cities.
- **Root Cause:** A mathematical equirectangular projection was used to translate Gazebo $(x, y)$ coordinates into simulated GPS $(lat, lng)$.
- **Engineering Reality:** The customer sees satellite imagery of buildings and streets in Tunis that have **zero correlation** with the 3D structures, sidewalk corridors, and obstacles in the Gazebo `small_city_dynamic.world`. Clicking a doorstep on Avenue Bourguiba could correspond to the middle of a solid building in Gazebo.
- **Severity:** **CRITICAL**. Violates the Single Source of Truth rule.

### Finding 2: Synthetic Multi-Rover Fleet Data
- **Current State:** `/api/fleet` returns data for three rovers: `NEXUS-01`, `NEXUS-02`, and `NEXUS-03`.
- **Root Cause:** `NEXUS-02` and `NEXUS-03` are hardcoded Python dictionaries inside `get_fleet()` in `web_bridge_node.py` (lines 1096–1120).
- **Engineering Reality:** Only `NEXUS-01` exists in Gazebo and ROS 2. `NEXUS-02` and `NEXUS-03` have no URDF, no Gazebo models, no ROS 2 topics, and no autonomous controllers.
- **Severity:** **HIGH**. Violates Rule 6 ("Never invent robot locations, detections, routes...").

### Finding 3: In-Memory, Unsecured Backend Architecture
- **Current State:** `web_bridge_node.py` embeds a Python standard library `http.server.HTTPServer` inside a ROS 2 node.
- **Security Deficits:**
  1. No persistent database (all orders, customers, and credentials vanish on node restart).
  2. Plaintext or unsalted passwords in volatile memory.
  3. No role-based access control (RBAC): `/api/orders` leaks all customer orders across the entire system.
  4. Both customer and supervisor interfaces share the same unauthenticated port (8080).
  5. Operator security relies on a single static environment PIN (`NEXUS_OPERATOR_PIN`) without MFA, rate-limiting, or cryptographic sessions.
- **Severity:** **CRITICAL**. Violates Rule 9 and Rule 10.

### Finding 4: Inaccurate Distance and ETA Calculations
- **Current State:** `client.js` displays doorstep distance using straight-line Euclidean or geodesic formulas (`1.2 km`, `~3 min`).
- **Engineering Reality:** The simulated city is approximately $160\text{ m} \times 96\text{ m}$. Straight-line distance ignores building blocks and required 90-degree street turns. The actual travel distance must be computed along the topological A* sidewalk graph in `route_planner.py`.
- **Severity:** **MEDIUM**. Misleads users on arrival estimation.

### Finding 5: Unsupported Hardware & Operational Claims
- **Hardware Claims:** Advertised $1,065 BOM omitted wiring harnesses, power distribution boards, structural casters, custom carrier board fabrication, and international tariffs.
- **Autonomy Claims:** "Level 4 Autonomy" and "Zero GPS Reliance via Dead-Reckoning" are scientifically invalid for real outdoor Mediterranean sidewalks without visual loop closure (VSLAM) or GNSS ground truth.
- **NPU Metrics:** Hailo-8L 138.4 FPS is a vendor datasheet benchmark, not measured on physical edge silicon in this repository.

---

## 4. Reusability Matrix

| Component | Assessment | Recommendation |
|:---|:---:|:---|
| `route_planner.py` | **High Value** | **Reuse & Extend**. The topological graph, building bounding boxes, and Liang-Barsky collision checks represent the true Gazebo world geometry. |
| `order_manager.py` / `order_manager_node.py` | **High Value** | **Reuse & Connect**. The FSM lifecycle and OTP HMAC verification are structurally sound. Connect directly to persistent backend. |
| `safety_supervisor.py` | **High Value** | **Reuse**. Deterministic 10-state FSM with latched fault transitions is effective. |
| `city_driver_node.py` | **High Value** | **Reuse**. Proven Pure Pursuit controller and depth corridor obstacle detection. |
| `rdsim_gazebo` / `small_city_dynamic.world` | **High Value** | **Reuse as Single Ground Truth World**. Primary operational environment for all mapping and routing. |
| `web_bridge_node.py` | **Refactor Required** | **Modularize**. Split HTTP server into a dedicated FastAPI/PostgreSQL service; retain ROS 2 bridge as a decoupled adapter. |
| `web_dashboard` HTML/JS | **Redesign Required** | **Replace World Map**. Replace generic external satellite map with the authentic 2D vector Gazebo World Map. Separate Customer and Supervisor platforms with genuine authentication. |

---

## 5. Architectural Dependency Map (Current State)

```
[Gazebo Classic 11: small_city_dynamic.world]
       |
       v (Sensor Plugins: /odom, /camera/image_raw, /camera/depth/image_raw, /imu)
+-------------------------------------------------------------------------+
| ROS 2 Humble Autonomy Graph                                             |
|                                                                         |
|  [traffic_light_node] ----> /traffic_light/state                        |
|                                     |                                   |
|  [order_manager_node] <---> /delivery/current_target <--> [city_driver] |
|        ^                           |                            |       |
|        | /delivery/new_order       v                            v       |
|        |                   /mission/state                   /cmd_vel    |
|        |                   /safety/state                        |       |
|        |                           |                            v       |
|  [web_bridge_node] <---------------+------------------ [Gazebo diff]    |
|  (In-Memory Store)                                                      |
+--------+----------------------------------------------------------------+
         |
         | HTTP (Port 8080) - Single unauthenticated origin
         v
+-------------------------------------------------------------------------+
| Web Browser (Shared Origin: http://localhost:8080)                      |
|                                                                         |
|  /client  --> client.html (Leaflet: Tunis CartoDB Dark Matter)          |
|  /supervisor --> supervisor.html (Leaflet: Tactical view with mock rovers)
+-------------------------------------------------------------------------+
```

---

## 6. Audit Conclusion & Roadmap

The repository possesses a functional, unit-tested ROS 2 autonomy core and a detailed Gazebo simulation world. To achieve commercial and scientific credibility, the web tier must be grounded in the **actual Gazebo world coordinates**, the backend must be transitioned to a secure architecture with strict customer/supervisor isolation, and all marketing assertions must be calibrated to verifiable **TRL 3–4** simulation evidence.
