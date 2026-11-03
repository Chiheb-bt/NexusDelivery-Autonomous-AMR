# NexusDelivery: Autonomous Sidewalk Delivery Robot (Simulation-First Prototype Architecture)

**Lead Systems Architect:** Chiheb ([@Chiheb-bt](https://github.com/Chiheb-bt))  
**Organization:** Chiheb Robotics Systems Lab  
**Maturity Level:** **TRL 3 (Experimental Proof of Concept in Simulation)**  
**License:** Apache 2.0 (with Upstream Notices, see [NOTICE](NOTICE))

---

## 1. Project Overview & Scope

NexusDelivery is an open-source autonomous mobile robot (AMR) software architecture engineered for sidewalk logistics research in simulated urban environments. The system evaluates vision-centric perception, topological corridor navigation, and deterministic safety mechanisms using ROS 2 Humble and Gazebo Classic 11.

### Evidence Baseline (TRL 3)
* **Perception Architecture**: Vision-centric active infrared stereo RGB-D perception pipeline (Intel RealSense D435i model in Gazebo). Ray-based LiDAR plugins have been removed from the runtime pipeline (`MESURÉ-SIM`).
* **Active IR Outdoor Feasibility**: *À tester sur matériel*. Based on Intel RealSense technical documentation, direct sunlight ambient solar irradiance (>1,000 W/m²) saturates the 850 nm structured IR pattern, degrading outdoor depth pointclouds on low-texture asphalt. Outdoor deployment will require passive RGB stereo or solid-state radar/ultrasonic augmentation.
* **Localization Backbone**: Odometry and 6-DOF IMU dead-reckoning evaluated over planar Gazebo contact surfaces (`MESURÉ-SIM`). *Estimation* : On outdoor sidewalk surfaces, wheel micro-slip and gyro drift produce unbounded position error (typically 2% to 5% of distance traveled), requiring future integration of Visual SLAM or multi-band GNSS-RTK for drift correction.
* **Edge AI Acceleration Target**: Hailo-8L M.2 AI Module (13 INT8 TOPS @ 2.5W TDP). The reported inference latency of 7.18 ms (138.4 FPS) for YOLOv8s at 640x640 batch 1 represents an external vendor benchmark ([Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)), labeled `DATASHEET / CIBLE — NON MESURÉ SUR HARDWARE PHYSIQUE DANS CE DÉPÔT`.
* **Last-Mile Logistics Cost Context**: Sourced to Capgemini Research Institute (2019 report: "The Last-Mile Delivery Challenge") and Council of Supply Chain Management Professionals (CSCMP), which estimate that last-mile logistics accounts for up to 53% of overall supply chain freight costs (`ESTIMATION`).
* **Mechatronic Chassis**: 4.0mm Aluminum 5052-H32 flat-pack sheet metal design ([2D DXF Blueprint](docs/cad/delivery_robot_chassis_2d_print.dxf)). Labeled `CONCEPT DE CONCEPTION — NON FABRIQUÉ, NON VALIDÉ EN CHARGE`.

---

## 2. Technical Competitive Landscape

| Dimension | Chiheb Robotics NexusDelivery | Starship Technologies | Nuro R2 / R3 | Serve Robotics |
|:---|:---:|:---:|:---:|:---:|
| **Primary Perception** | Active IR RGB-D Vision (Intel RealSense D435i model) | 12x Passive Cameras + Ultrasonic + Radar | 360° Automotive Mechanical LiDAR + Radar + Cams | Ouster 3D LiDAR + Monocular Vision |
| **Localization Method** | Wheel Odometry + 6-DoF IMU dead-reckoning (`MESURÉ-SIM`) | Multi-camera visual odometry + GNSS/IMU | Dual GNSS-RTK + Pre-mapped 3D pointcloud matching | GNSS-RTK + Odometry + Pre-mapped sidewalk maps |
| **Unit Hardware Capex (BOM)** | **$1,274.50 USD** (Parts) / **$1,854.50 USD** (TN Landed) | ~$8,500 – $12,000 USD (Industry estimates) | ~$35,000 – $60,000 USD (Automotive-grade hardware) | ~$9,000 – $15,000 USD (Commercial AMR hardware) |
| **Edge Compute Target** | Raspberry Pi 5 (8GB) + Hailo-8L M.2 HAT+ | Custom x86 / NVIDIA embedded stack | Dual NVIDIA DRIVE Orin | NVIDIA Jetson Xavier / Orin Nano |
| **Object Detection Latency** | 7.18 ms (YOLOv8s 640x640, `DATASHEET / CIBLE`) | ~25 ms (Custom multi-camera network) | ~5 ms (High-power automotive GPU) | ~18 ms (Jetson Orin pipeline) |
| **Cargo Authentication** | HMAC-SHA256 Dynamic 6-digit OTP + Solenoid | Mobile App BLE / Cloud unlock | Pin code / Touchscreen console | Mobile App NFC / Cloud unlock |
| **Software Reproducibility** | Open-source ROS 2 Humble / Docker environment | Proprietary commercial software | Proprietary commercial software | Proprietary commercial software |

---

## 3. Technology Readiness Level (TRL) Breakdown

Evaluated strictly against ISO 16290 / NASA TRL criteria:

| Subsystem | Maturity | Status and Technical Justification |
|:---|:---:|:---|
| **Perception Stack** | **TRL 3** | Pinhole depth geometry, ground plane rejection, and pedestrian bounding box tracking tested on synthetic Gazebo camera topics. Outdoor sunlight IR saturation unmeasured. |
| **Localization & Odometry** | **TRL 3** | Dead-reckoning dead-reckoning fusion (/odom and /imu) tested on ideal planar Gazebo simulation. Slip drift compensation unvalidated on physical pavement. |
| **Navigation & Planning** | **TRL 3** | Topological waypoint network and Liang-Barsky anti-collision corridor verification validated in Gazebo dynamic simulations and unit tests. |
| **System Safety & Faults** | **TRL 3** | 10-state deterministic supervisor with sensor timeout and stall latching tested via automated test suite. Hardware SIL-rated safety relay unbuilt. |
| **Cargo Management** | **TRL 3** | HMAC-SHA256 OTP authentication, rate-limiting, and tamper lockout verified in software unit tests. Physical latch and microswitch feedback unbuilt. |
| **Electronics & Power** | **TRL 2** | Power tree, component selection, and preliminary carrier board schematic concept formulated. PCB unmanufactured. |
| **Mechanical Chassis** | **TRL 3** | 2D DXF flat-pack CAD layout generated. Structural FEA and physical prototype unbuilt. |
| **Energy & BMS** | **TRL 2** | LiFePO4 8S 20Ah pack and Daly Smart BMS specified on paper. Real discharge curves under load unmeasured. |
| **Platform Overall** | **TRL 3** | **Experimental proof of concept demonstrated in laboratory simulation.** |

---

## 4. Software Architecture & Node Graph

```
                            FLEET MISSION CONTROL (PORT 8080)
                       [HTTP REST / MJPEG Video Stream / Telemetry]
                                           │
                                           ▼
+──────────────────────────────────────────────────────────────────────────+
│                    NEXUSDELIVERY AUTONOMY PIPELINE                       │
│                                                                          │
│  +────────────────────+  +────────────────────+  +────────────────────+  │
│  │  Front RGB Camera  │  │ RGB-D Depth Camera │  │ Wheel Odom & IMU   │  │
│  │  /camera/image_raw │  │ /camera/depth/...  │  │ /odom + /imu       │  │
│  +─────────┬──────────+  +─────────┬──────────+  +─────────┬──────────+  │
│            │                       │                       │             │
│            ▼                       ▼                       │             │
│  +────────────────────────────────────────────+            │             │
│  │      Depth Corridor & Vision Processing    │            │             │
│  │  - Vectorized Pinhole Depth Backprojection │            │             │
│  │  - Ground Plane Filtering                  │            │             │
│  │  - Dynamic Actor Distance & TTC Tracking   │            │             │
│  +─────────────────────┬──────────────────────+            │             │
│                        │                                   │             │
│                        ▼                                   ▼             │
│  +────────────────────────────────────────────────────────────────────+  │
│  │                     City Driver & Motion Control                   │  │
│  │  - Corridor Waypoint Tracking      - Differential Dead-Reckoning   │  │
│  │  - Liang-Barsky Obstacle Boundary Avoidance                        │  │
│  │  - Critically Damped IMU Steering Damping                          │  │
│  +─────────────────────┬──────────────────────────────────────────────+  │
│                        │                                                 │
│                        ▼                                                 │
│  +────────────────────────────────────────────+  +────────────────────+  │
│  │        Deterministic Safety Supervisor     │  │ Compartment Security│  │
│  │  - 10 Operational States & Timeout Watchdog│  │ - HMAC-SHA256 OTP  │  │
│  │  - Latched Fault & Recovery Management     │  │ - Tamper Lockout   │  │
│  +─────────────────────┬──────────────────────+  +─────────┬──────────+  │
│                        │                                   │             │
│                        ▼                                   ▼             │
│                 /cmd_vel (Twist)                   Solenoid Actuator     │
+──────────────────────────────────────────────────────────────────────────+
```

---

## 5. Dual Web Applications & Authentic Gazebo Operational Map

NexusDelivery features **two independent, role-isolated web applications** powered by a shared secure backend and a high-performance Retina 2D Canvas vector map engine representing the authentic `small_city_dynamic.world` Gazebo environment:

```
                            NEXUSDELIVERY SHARED SECURE BACKEND
                    [FastAPI / WebBridge HTTP & WebSocket Server :8080]
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             ▼                                                               ▼
   CUSTOMER PLATFORM (/client)                                   SUPERVISOR COCKPIT (/supervisor)
   - Curbside Menu & Order Placement                             - Tactical Multi-Rover Map
   - Authentic Gazebo Doorstep Selector                          - RealSense D435i Perception AI HUD
   - Real-Time AMR Trajectory Tracking                           - Powertrain (ODrive) & BMS (8S LiFePO4)
   - 6-Digit OTP Contactless Hatch Unlock                        - Live Mission Queue & Dispatch Decider
   - Tenant-Isolated Order History                               - Cryptographic Security Audit Trail
                                                                 - Remote Teleoperation & Master E-Stop
```

### Authentic Gazebo Vector Map Engine (`gazebo_world_map.py` & `gazebo_map.js`)
* **Single Source of Truth**: Completely replaces external disconnected tile servers (CartoDB/Esri satellite) with an authentic metric vector rendering of `small_city_dynamic.world` ($X \in [-48.0, 112.0]\text{ m}, Y \in [-48.0, 48.0]\text{ m}$).
* **Curbside Doorstep Snapping**: Customer pin placement validates against building footprints, curbside sidewalks, and the Central Depot physical barrier, calculating exact A* route distances and realistic ETAs.
* **Live Telemetry & Freshness**: Directly visualizes `/odom` $(x, y, \theta)$ at 50 Hz. If Gazebo pauses or disconnects, the UI instantly flips from `LIVE` to `STALE` / `DISCONNECTED`.

---

## 6. Mechatronics Architecture & Reconciled Bill of Materials (BOM)

The Bill of Materials is tracked in the single source of truth: [`delivery_robot_sim/web_dashboard/downloads/BOM.csv`](delivery_robot_sim/web_dashboard/downloads/BOM.csv). The table below is verified mathematically:

| Sous-systeme | Composant | Reference / Specifications | Qte | Cout unitaire (USD) | Total poste (USD) | Statut preuve |
|:---|:---|:---|:---:|:---:|:---:|:---:|
| **Compute Core** | [Raspberry Pi 5 (8GB)](https://www.raspberrypi.com/products/raspberry-pi-5/) | Quad Cortex-A76 @ 2.4GHz 8GB LPDDR4X | 1 | $80.00 | $80.00 | DATASHEET |
| **AI Coprocessor** | [Hailo-8L M.2 AI Module](https://hailo.ai/products/ai-accelerators/hailo-8l-ai-acceleration-module/) | 13 INT8 TOPS @ 2.5W M.2 2242 | 1 | $75.00 | $75.00 | DATASHEET |
| **M.2 Interface HAT** | [Raspberry Pi M.2 HAT+](https://www.raspberrypi.com/products/m2-hat-plus/) | PCIe Gen 3.0 to M.2 Key-M adapter | 1 | $12.00 | $12.00 | DATASHEET |
| **Perception Sensor** | [Intel RealSense D435i](https://www.intelrealsense.com/depth-camera-d435i/) | Active IR Stereo Depth (0.2-5.0m) + RGB + IMU | 1 | $349.00 | $349.00 | DATASHEET |
| **Motor Controller** | [ODrive S1 Motor Driver](https://odriverobotics.com/shop/odrive-s1) | 24V-56V 40A cont FOC motor controller CAN/UART | 1 | $169.00 | $169.00 | DATASHEET |
| **Traction Drive** | 8" Brushless Geared Hub Motors | 24V 250W geared hub with 14-bit Hall encoders | 2 | $95.00 | $190.00 | ESTIMATION |
| **Main Battery** | 24V 20Ah LiFePO4 Pack | 25.6V nom 512Wh Daly Smart BMS I2C/CAN | 1 | $195.00 | $195.00 | ESTIMATION |
| **Power Converter 5V** | Synchronous Buck 5V 5A | 24V to 5.1V 5.0A out for Raspberry Pi 5 & NPU | 1 | $8.50 | $8.50 | ESTIMATION |
| **Power Converter 12V** | Synchronous Buck 12V 3A | 24V to 12.0V 3.0A out for Solenoids & Fans | 1 | $7.00 | $7.00 | ESTIMATION |
| **Hatch Security** | Electronic Deadbolt Solenoids | 12V DC spring latch 1.2A pulse 10mm throw | 2 | $14.00 | $28.00 | ESTIMATION |
| **Lock Relay** | Optocoupler Relay Module | 5V trigger optoisolated with 1N4007 flyback diode | 1 | $3.50 | $3.50 | ESTIMATION |
| **Safety Interlock** | Emergency Stop Switch | 22mm panel mount push-lock twist-release | 1 | $9.00 | $9.00 | ESTIMATION |
| **Status Lighting** | WS2812B RGB NeoPixel Ring | 16 addressable RGB LEDs 5V single-wire | 1 | $6.50 | $6.50 | ESTIMATION |
| **Caster Wheels** | Heavy-Duty Swivel Casters | 75mm diameter polyurethane 4-hole mount | 2 | $11.00 | $22.00 | ESTIMATION |
| **Structural Frame** | Aluminum 5052-H32 Laser-Cut Shell | 4.0mm laser-cut chassis plates and DIN 912 fasteners | 1 | $75.00 | $75.00 | ESTIMATION |
| **Carrier & Wiring** | Carrier Board PCB & Wiring Harness | 4-layer carrier PCB concept and 10 AWG silicone harness | 1 | $45.00 | $45.00 | ESTIMATION |
| **Total pieces brutes** | NexusDelivery AMR (16 postes) | Composants bruts sortie usine | - | - | **$1274.50 USD** | CALCULÉ |
| *Fret et douane Tunisie* | Transport aerien (15kg) + Droits douane/TVA (~30%) | Transit et dedouanement indicatif | - | - | *$580.00 USD* | ESTIMATION - A VERIFIER |
| **Total rendu Tunisie** | NexusDelivery Landed Cost | Cout total indicatif d approvisionnement | - | - | **$1854.50 USD** | ESTIMATION - A VERIFIER |

*Note: All mechanical and carrier board elements are design concepts (non manufactured, non validated under physical load).*

---

## 7. Simulation & Testing Quickstart

### Prerequisites
* Ubuntu 22.04 LTS x86_64
* ROS 2 Humble Hawksbill or Docker Engine

### Running the Automated Regression Test Suite (90 Tests)
Execute all pure-Python unit, integration, and security tests covering kinematics, Liang-Barsky geometry, OTP security, PBKDF2 cryptography, ACID SQLite storage, Gazebo vector map transformations, and safety supervisor states:
```bash
PYTHONPATH=delivery_robot_sim PBKDF2_ITERATIONS=10000 python3 -m unittest discover delivery_robot_sim/tests
```
**Expected Output:**
```text
Ran 90 tests in ~45s
OK
```

### Running the Full Simulation & Web Portals
```bash
# Terminal 1: Launch Gazebo Simulation World
ros2 launch delivery_robot_sim simulation_launch.py

# Terminal 2: Launch Web Bridge & Mission Control Server
export NEXUS_OPERATOR_PIN="nexus2026"
PYTHONPATH=delivery_robot_sim python3 delivery_robot_sim/delivery_robot_sim/web_bridge_node.py
```
Open in browser:
* **Customer Delivery App:** `http://localhost:8080/client`
* **Supervisor Fleet Cockpit:** `http://localhost:8080/supervisor`

---

## 7. Provenance, Licensing & Notices

### Upstream Simulation Foundation: AuTURBO / RDSim
* Upstream Repository: [`https://github.com/AuTURBO/RDSim`](https://github.com/AuTURBO/RDSim) (Branch: `devel/2wheel_diff`, commit: `335fb578ee35db732542c4459f23c8e4ca7716e5`).
* Maintainer: `ggh-png` (`0380089@gmail.com`).
* The foundational URDF differential drive robot model (`rdsim_description`) and simulation world scaffolding (`rdsim_gazebo`) were derived from AuTURBO/RDSim.
* License Notice: The upstream repository lacks an explicit root license file. A formal license clarification inquiry was submitted on November 1, 2026. A 14-day transition period is active. Full details are documented in [NOTICE](NOTICE) and [`third_party/licenses/AUTURBO_RDSIM_LICENSE_STATUS.md`](third_party/licenses/AUTURBO_RDSIM_LICENSE_STATUS.md).

### OSRF Gazebo Models
* Upstream Repository: [`https://github.com/osrf/gazebo_models`](https://github.com/osrf/gazebo_models).
* Authors: Nate Koenig, Cole Biesemeyer, Louise Poubel, Thomas Koletschka, Sebastian Scherer, et al.
* Licenses: Apache License 2.0 and Creative Commons Attribution 2.0 Generic (CC-BY 2.0).
* See [`third_party/licenses/OSRF_GAZEBO_MODELS_LICENSE.txt`](third_party/licenses/OSRF_GAZEBO_MODELS_LICENSE.txt).

### Original Works
All modules under `delivery_robot_sim/` (autonomy stack, dynamic actor tracking, route planning, safety supervisor, OTP authentication), tests, and original tools are licensed under the **Apache License, Version 2.0**.
See [LICENSE](LICENSE).

---

## 8. Academic Citation

```bibtex
@software{chiheb2026nexusdelivery,
  author = {Chiheb, B.},
  title = {NexusDelivery: Autonomous Sidewalk Delivery Robot (Simulation-First Prototype Architecture)},
  year = {2026},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/Chiheb-bt/NexusDelivery-Autonomous-AMR}},
  note = {TRL 3 Simulation Baseline. Chiheb Robotics Systems Lab}
}
```
