# NexusDelivery — Physical Integration & Runtime Truth Audit

**Document ID:** DOC-ND-TRUTH-001  
**Audit Date:** November 3, 2026  
**Auditing Team:** Senior ROS 2 Humble, Gazebo Classic 11, Robotics Controls, Mechanical Integration & Verification Team  
**Authoritative Source Repository:** `/home/chiheb/Downloads/RDSim-devel-2wheel_diff`  
**ROS Build Workspace:** `/home/chiheb/rdsim_ws`  
**Virtualization Container:** `ros-humble-gazebo:latest`  

---

## 1. Executive Summary & Audit Mandate

The primary objective of this audit is to determine the exact engineering reality of the NexusDelivery project. In accordance with strict engineering standards:
- We distinguish unequivocally between **PHYSICAL GAZEBO INTEGRATION** and **SOFTWARE/API STATE SIMULATION**.
- We document where the software architecture is fully realized, where interfaces connect to Gazebo physics, and where mock fallbacks or decoupled simulations are currently operating.
- We never claim physical actuation or hardware certification based solely on unit tests, mock sockets, or internal Python state transitions.

---

## 2. Environment & Source Consistency Audit

### 2.1 Host Environment vs Docker Container Architecture
An architectural split exists between the host operating system and the simulation runtime:

| Inspection Item | Host Operating System | Docker Container (`ros-humble-gazebo:latest`) | Engineering Finding |
|---|---|---|---|
| **OS / Distribution** | Linux (Ubuntu 6.5.0-35-generic) | Ubuntu 22.04 LTS (Jammy Jellyfish) | Host runs lightweight daemon; Docker encapsulates simulation stack. |
| **Python Version** | Python 3.14.4 (`/usr/bin/python3`) | Python 3.10.12 (`/usr/bin/python3`) | Host Python 3.14 runs test runners & Web Bridge; Docker runs ROS 2 Humble. |
| **ROS 2 Installation** | **NOT INSTALLED** (`which ros2` $\to \emptyset$) | **INSTALLED** (`/opt/ros/humble/bin/ros2`) | ROS 2 commands must be executed within Docker. |
| **Gazebo Simulator** | **NOT INSTALLED** (`which gzserver` $\to \emptyset$) | **INSTALLED** (Gazebo Classic 11.10.2) | Physical physics engine resides exclusively in Docker image. |
| **Ultralytics YOLO** | Installed (`8.4.175`) | **NOT INSTALLED** (ModuleNotFoundError) | Edge AI runs on host CPU for testing; Docker simulation uses depth corridor obstacle filtering. |
| **Hailo-8L NPU Hardware** | **NOT ATTACHED** (`lspci`/`lsusb` $\to \emptyset$) | **NOT ATTACHED** | Hailo-8L is a target commercial specification, not physical host hardware. |

### 2.2 Source Packages vs Workspace Packages
- **Authoritative Source Directory:** `/home/chiheb/Downloads/RDSim-devel-2wheel_diff`
- **Docker Workspace Directory:** `/home/chiheb/rdsim_ws/src`
- **Symlink Check:** `/home/chiheb/rdsim_ws/src/RDSim` points to `/home/chiheb/Downloads/RDSim-devel-2wheel_diff`.
- **Physical Package Synchronization:**
  - `rdsim_description`: Byte-identical across both locations.
  - `delivery_robot_sim`: Byte-identical across both locations (verified by `diff -rq`).
  - `rdsim_gazebo`: Byte-identical across both locations.
  - `rdsim_interfaces`: Byte-identical across both locations.
- **Reproducible Build Verification:**
  - Executed inside `ros-humble-gazebo:latest`:
    ```bash
    docker run --rm -v /home/chiheb/rdsim_ws:/ws ros-humble-gazebo:latest \
      bash -c "source /opt/ros/humble/setup.bash && cd /ws && colcon build --packages-select rdsim_description delivery_robot_sim rdsim_gazebo"
    ```
  - **Result:** 3 packages finished cleanly in **3.06 seconds** without warnings or errors.

### 2.3 Running Web Server Inspection
- **Active Process:** PID `247267`, executing `/usr/bin/python3.14 delivery_robot_sim/delivery_robot_sim/web_bridge_node.py` on port `8080`.
- **Process Working Directory:** `/home/chiheb/Downloads/RDSim-devel-2wheel_diff` (Authoritative Source).
- **CRITICAL DISTINCTION:**  
  The web server responding with HTTP 200 on `http://127.0.0.1:8080/` demonstrates that the HTTP daemon and REST API router are functioning. **It does NOT indicate that Gazebo Classic 11 or ROS 2 Humble nodes are active.** When Gazebo is not running, the Web Bridge operates in standalone software mode with fallback telemetry.

---

## 3. High-Level Integration Matrix

| Subsystem Component | Claimed Feature | Actual Operational Status | Truth Classification |
|---|---|---|:---:|
| **Web Server & Portals** | Multi-portal dashboard (Corporate, Client, Supervisor) | Functional on port 8080 via Python HTTP & WebSocket server | **IMPLEMENTED AND RUNTIME VERIFIED** |
| **Chassis Kinematics (URDF)** | Differential drive, 460mm track, 380mm wheelbase | Accurately modeled in `rdsim.urdf.xacro` with mass & inertia | **IMPLEMENTED AND PHYSICALLY VERIFIED** |
| **Diff-Drive Actuation (Gazebo)** | Wheel velocity control from `/cmd_vel` | `libgazebo_ros_diff_drive.so` active in `camera_only.gazebo.xacro` | **IMPLEMENTED AND PHYSICALLY VERIFIED** |
| **Sidewalk Waypoint Navigation** | Autonomous corridor pure pursuit navigation | `city_driver_node` follows topological sidewalk corridors | **IMPLEMENTED AND PHYSICALLY VERIFIED** |
| **Prismatic Cargo Lift (URDF)** | Vertical lift link & joint ($0.0\text{ to }0.12\text{ m}$) | Modeled in `rdsim.urdf.xacro` with prismatic joint & limits | **IMPLEMENTED AND RUNTIME VERIFIED** |
| **Prismatic Cargo Lift (Actuation)** | Physical joint motion in Gazebo physics engine | No Gazebo ROS controller; calls missing host `gz joint` CLI | **PARTIALLY IMPLEMENTED** |
| **Revolute Cargo Hatch (URDF)** | Motorized hatch link & joint ($0^\circ\text{ to }60^\circ$) | Modeled in `rdsim.urdf.xacro` with revolute limits ($1.05\text{ rad}$) | **IMPLEMENTED AND PHYSICALLY VERIFIED** |
| **Revolute Cargo Hatch (Actuation)**| Physical joint rotation in Gazebo physics engine | Actuated via `cargo_delivery_manager` calling `gz joint` inside Docker | **IMPLEMENTED AND PHYSICALLY VERIFIED** |
| **Hatch State Feedback** | `/joint_states` topic for hatch angle | `libgazebo_ros_joint_state_publisher.so` publishes `cargo_hatch_joint` | **IMPLEMENTED AND PHYSICALLY VERIFIED** |
| **Lift State Feedback** | `/joint_states` topic for lift position | NOT listed in joint state publisher; software variable only | **IMPLEMENTED AND SOFTWARE VERIFIED ONLY** |
| **Drive Interlock** | Disable movement while hatch/lift deployed | `can_drive()` clamps `/cmd_vel` to $(0.0, 0.0)$ in software controller | **IMPLEMENTED AND SOFTWARE VERIFIED ONLY** |
| **Visual RGB-D Perception** | Front camera image and depth pointcloud | `libgazebo_ros_camera.so` streams $640 \times 480$ RGB @ 30 FPS + depth | **IMPLEMENTED AND PHYSICALLY VERIFIED** |
| **YOLO Obstacle Detection** | AI bounding boxes on dynamic obstacles | `ultralytics` installed on host; missing inside Docker image | **PARTIALLY IMPLEMENTED** |
| **Hailo-8L NPU Acceleration** | 13 TOPS edge AI coprocessor execution | No physical Hailo hardware attached; target spec only | **HARDWARE REQUIRED** |
| **Battery BMS Telemetry** | LiFePO4 pack cell voltage & SOC | Calculated mathematical power model based on odometer | **IMPLEMENTED AND SOFTWARE VERIFIED ONLY** |
| **Delivery OTP Handover** | Single-use 6-digit cryptographic verification | Hash matched and order marked delivered in SQLite store | **IMPLEMENTED AND RUNTIME VERIFIED** |
