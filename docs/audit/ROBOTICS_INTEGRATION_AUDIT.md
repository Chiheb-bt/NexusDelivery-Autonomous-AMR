# NexusDelivery — Robotics, Perception & Simulation Integration Audit

**Audit Date:** November 2, 2026  
**Auditor:** Senior Robotics Systems Engineer & ROS 2 / Gazebo Specialist  
**Target Environment:** ROS 2 Humble | Gazebo Classic 11.10.2 | Ubuntu 22.04 LTS  
**Primary World Target:** `rdsim_gazebo/worlds/small_city_dynamic.world`

---

## 1. Executive Summary

This audit examines the robotics and physics simulation layer of NexusDelivery. The platform is designed under a strict design constraint: **Zero LiDAR, Zero GPS** runtime reliance, depending exclusively on stereo/depth vision (Intel RealSense D435i), wheel encoders, and a 6-DOF IMU for autonomous sidewalk navigation.

The autonomy stack contains robust, unit-tested core algorithms for corridor guidance, topological A* path planning, Liang-Barsky building collision prevention, and safety supervisor state transitions. However, the simulation-to-web bridge has introduced artificial distortions (such as mapping Gazebo metric coordinates into simulated GPS in Tunisia) and has masked the physical limitations of dead reckoning and optical sensors under outdoor lighting.

---

## 2. Gazebo World & Environment Architecture

### 2.1 The Operational Simulation World: `small_city_dynamic.world`
- **File:** `rdsim_gazebo/worlds/small_city_dynamic.world`
- **SDF Version:** 1.6
- **Physics Engine:** ODE (`max_step_size: 0.005`, `real_time_update_rate: 200` $\rightarrow$ 1.0 real-time factor).
- **Physical Extents (Ground Plane):**
  - Minimum Coordinates: $x = -48.0\text{ m}, y = -48.0\text{ m}$
  - Maximum Coordinates: $x = +112.0\text{ m}, y = +48.0\text{ m}$
  - Total World Footprint: $160.0\text{ m}$ (East-West) $\times 96.0\text{ m}$ (North-South) $= 15,360\text{ m}^2$.

### 2.2 Navigable Corridors & Road Network
The physical terrain contains defined street corridors and sidewalks:

| Corridor Name | Axis Orientation | Fixed Coordinate | Span Range | Key Intersections / Landmarks |
|:---|:---:|:---:|:---:|:---|
| **Central Boulevard** | Horizontal ($X$) | $y = 0.0\text{ m}$ (Lane: $-0.75\text{ m}$) | $x \in [-28.0, 108.0]\text{ m}$ | Depot Bay Door ($-27.5\text{m}$), North Ave ($-15.0\text{m}$), East Ave ($45.0\text{m}$) |
| **North Avenue** | Vertical ($Y$) | $x = -15.0\text{ m}$ | $y \in [-45.0, 45.0]\text{ m}$ | Controlled Intersection with Stop Light at $( -15.0, 0.0\text{m} )$ |
| **West Boulevard** | Vertical ($Y$) | $x = -45.0\text{ m}$ | $y \in [-45.0, 45.0]\text{ m}$ | West Commercial Zone, Bistro Patio Bay |
| **East Avenue** | Vertical ($Y$) | $x = +45.0\text{ m}$ | $y \in [-45.0, 45.0]\text{ m}$ | Tech Lab Delivery Bay ($x=43.8\text{m}, y=15.0\text{m}$) |
| **Far East Avenue** | Vertical ($Y$) | $x = +108.0\text{ m}$ | $y \in [-45.0, 45.0]\text{ m}$ | Pier & Marina Bay |
| **North Street** | Horizontal ($X$) | $y = +45.0\text{ m}$ | $x \in [-45.0, 108.0]\text{ m}$ | North Perimeter Sidewalk |
| **South Street** | Horizontal ($X$) | $y = -45.0\text{ m}$ | $x \in [-45.0, 108.0]\text{ m}$ | South Market Perimeter Sidewalk |

### 2.3 Central Logistics Depot Facility
- **Bounding Box:** $x \in [-35.0, -28.0]\text{ m}, y \in [-2.5, 4.5]\text{ m}$.
- **Robot Spawn & Charging Dock:** $(-31.5, -0.75)\text{ m}$ (Interior Dock).
- **Bay Door Exit/Entrance:** $(-27.5, -0.75)\text{ m}$ (East Portal).
- **Physical Wall Constraint:** The Central Depot building physically blocks Central Boulevard through-traffic between $x = -34.5\text{m}$ and $x = -28.0\text{m}$. Therefore, `WEST_CENTRAL` ($-45.0, 0.0$) is strictly disconnected from `NORTH_AVE_CENTRAL` ($-15.0, 0.0$). Any west-to-east trip must route via North Street ($y=45\text{m}$) or South Street ($y=-45\text{m}$).

### 2.4 Solid Building Blocks (Restricted No-Go Zones)
The world defines 6 major multi-story building blocks where navigation is physically impossible:
1. **Block NW:** $[-42.5, -17.5]\text{ m} \times [3.0, 42.5]\text{ m}$
2. **Block SW:** $[-42.5, -17.5]\text{ m} \times [-42.5, -3.0]\text{ m}$
3. **Block NC:** $[-12.5, 42.5]\text{ m} \times [3.0, 42.5]\text{ m}$
4. **Block SC:** $[-12.5, 42.5]\text{ m} \times [-42.5, -3.0]\text{ m}$
5. **Block NE:** $[47.5, 105.0]\text{ m} \times [3.0, 42.5]\text{ m}$
6. **Block SE:** $[47.5, 105.0]\text{ m} \times [-42.5, -3.0]\text{ m}$

---

## 3. Sensor Pipelines & Perception Stack

### 3.1 RGB Camera Pipeline (`/camera/image_raw`)
- **Resolution:** $320 \times 240$ pixels, 8-bit BGR @ 30 Hz.
- **Processing:**
  - CLAHE (Contrast Limited Adaptive Histogram Equalization) applied to luminance channel.
  - HSV Color Segmentation for traffic lights: detects Red (Hue 0–10 & 170–180) vs Green (Hue 40–85).
  - Multi-frame confirmation: requires 3 consecutive matching classifications before signaling a state change.

### 3.2 Depth Camera Pipeline (`/camera/depth/image_raw`)
- **Format:** 32-bit floating point depth in meters.
- **Corridor Envelope:** Projects a virtual bounding cylinder with width $0.90\text{ m}$ centered along the robot's heading.
- **Obstacle Detection:** Isolates points within the corridor between $0.3\text{ m}$ and $4.5\text{ m}$.
- **TTC Calculation:** $\text{TTC} = \frac{d_{\text{obstacle}}}{\max(0.1, v_{\text{actual}})}$. If $\text{TTC} < 2.5\text{ s}$, initiates deceleration; if $\text{TTC} < 1.2\text{ s}$, engages emergency stop.

### 3.3 Reality Gaps in Perception (Simulation vs. Real World)
1. **Solar IR Washout:** In Gazebo, depth frames are computed geometrically from the z-buffer without noise. On physical hardware (Intel RealSense D435i), outdoor sunlight (>80,000 lux) saturates the 850 nm IR projector, causing depth pointclouds to drop out on asphalt sidewalks. The stack needs a passive RGB visual fallback (e.g., monocular depth estimation or optical flow).
2. **Hailo-8L Edge AI:** The current simulation runs CPU-based mock or OpenCV classification. The reported 7.18 ms (138.4 FPS) YOLO latency represents Hailo datasheet benchmarks, not measured edge execution on a Raspberry Pi 5 + Hailo-8L M.2 HAT.

---

## 4. Localization, Odometry & Navigation Stack

### 4.1 Differential Drive Odometry (`/odom`)
- **Kinematic Model:**
  $$v = \frac{v_r + v_l}{2}, \quad \omega = \frac{v_r - v_l}{L}$$
- **Dead-Reckoning In Gazebo:** The simulation has zero wheel slip, zero surface tilt, and near-zero encoder drift.
- **Real-World Reality Check:** Real sidewalks have lateral drainage slopes (1%–2%), expansion joints, pebbles, and wheel slippage. Over a 100 m delivery route, pure dead reckoning drifts by 2%–8% ($2\text{ m}$ to $8\text{ m}$), which causes the robot to miss narrow sidewalk curb ramps. A physical deployment requires Visual Odometry / Visual SLAM (e.g., RTAB-Map or ORB-SLAM3) or low-cost GNSS-RTK for periodic drift correction.

### 4.2 Route Planning & Collision Prevention
- **Algorithm:** Pure Python A* on the topological intersection graph (`route_planner.py`).
- **Safety Guarantee:** Every computed edge is verified using Liang-Barsky parametric line clipping against all building footprint bounding boxes. If an edge intersects a solid building block, it is rejected with cost $\infty$.
- **Curbside Standoff:** Customer delivery bays specify a standoff distance ($1.2\text{ m}$ to $1.5\text{ m}$) from the physical building wall to ensure the robot parks safely on the sidewalk without obstructing storefront doorways.

---

## 5. Order Management & Hardware Actuation

### 5.1 Order FSM (`order_manager.py`)
- **Lifecycle States:**
  $$\text{PENDING} \longrightarrow \text{ASSIGNED} \longrightarrow \text{IN\_TRANSIT} \longrightarrow \text{ARRIVED} \longrightarrow \text{DELIVERED} \longrightarrow \text{COMPLETED}$$
- **Dwell Timer:** $2.0\text{ s}$ dwell at depot for package loading, $2.0\text{ s}$ dwell at customer bay.
- **Cryptographic OTP:** HMAC-SHA256 generates a 6-digit code validated against the order ID, simulation timestamp, and secret salt. Enforces a 3-strike lockout and $180\text{ s}$ expiration window.

### 5.2 Cargo Hatch & Parcel Spawner
- **Hatch Joint:** Revolute joint actuated via Gazebo position controller plugin (`/delivery/hatch_cmd`: `OPEN` $\rightarrow 1.05\text{ rad} \approx 60^\circ$, `CLOSE` $\rightarrow 0.0\text{ rad}$).
- **Parcel Spawner (`cargo_delivery_manager.py`):** Calls `/gazebo/spawn_sdf_entity` to spawn a realistic $0.2\text{m} \times 0.2\text{m} \times 0.15\text{m}$ cardboard box inside the robot's compartment upon depot pickup, and deletes it upon customer retrieval.

---

## 6. Discrepancy Analysis: Simulated vs. Declared Capabilities

| Feature | Simulation Reality (TRL 3) | Declared Marketing Claim (TRL 7+) | Required Alignment |
|:---|:---|:---|:---|
| **Fleet Size** | Exactly 1 robot (`rdsim` in Gazebo) | "Multi-rover autonomous fleet (Alpha, Bravo, Charlie)" | Clearly label additional rovers as "Fleet Simulation / Future Units". Do not synthesize fake telemetry. |
| **Delivery Map** | Gazebo metric grid $[-48, 112] \times [-48, 48]\text{ m}$ | Real-world global map (Tunis, Paris, Silicon Valley) | **Replace external map with the authentic 2D Gazebo World Map**. Ground truth must be Gazebo. |
| **Battery BMS** | Estimated software formula ($12.4\text{W} + 42\text{W} \cdot \frac{v}{0.8}$) | "25.6V 8S LiFePO4 with active Daly BMS cell telemetry" | Label battery metric as "Simulated Power Budget Model". |
| **NPU Inference** | CPU OpenCV classification | "Hailo-8L 138.4 FPS hardware inference" | Note: "Hailo-8L Datasheet Benchmark (Hardware Edge Deployment Target)". |
| **Localization** | Wheel odometry + IMU (Zero slip in sim) | "Zero GPS Reliance over unlimited urban distances" | Acknowledge: "Simulation validated under ideal friction; physical deployment requires Visual SLAM integration." |

---

## 7. Robotics Action Items for Target Architecture

1. **Direct Gazebo Map Representation:** Generate an exact 2D vector coordinate map of `small_city_dynamic.world` containing all sidewalks, roads, buildings, depot, and stopping bays.
2. **True Coordinate Synchronization:** Map website clicks directly to Gazebo $(x, y)$ world coordinates with zero artificial GPS transformations.
3. **Live ROS 2 Telemetry Binding:** Bind the web robot marker strictly to `/odom` and `/mission/state`. If Gazebo pauses or resets, the web marker must freeze or synchronize instantly.
4. **Valid Destination Validation:** Run all destination clicks through `route_planner.py::validate_and_snap_destination()`. Reject out-of-bounds or building clicks with explicit geometric explanations.
