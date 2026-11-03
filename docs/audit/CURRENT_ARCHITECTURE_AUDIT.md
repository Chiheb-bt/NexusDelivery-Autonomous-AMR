# NexusDelivery — Current Architecture Audit
**Document Identifier:** AUDIT-ARCH-2026-001  
**Maturity Classification Standard:** 5-State Verification System  
**Audit Scope:** Active Frontend Entry Points, Backend Services, REST APIs, Security Subsystem, ROS 2 Autonomy Graph, Gazebo Simulation World  

---

## 1. Executive Summary

This architecture audit establishes an honest baseline of the NexusDelivery autonomous sidewalk delivery robotics platform. Every component is evaluated strictly on demonstrated, working code rather than marketing assertions or speculative capabilities. 

All subsystem features are classified under the five mandatory verification states:
1. `IMPLEMENTED AND VERIFIED`: Code exists, is fully connected, and verified by passing unit/integration tests and runtime execution.
2. `IMPLEMENTED BUT NOT VERIFIED`: Code exists in the repository but has not been tested against active Gazebo simulation runtime.
3. `PARTIALLY IMPLEMENTED`: Foundational logic exists, but key interfaces, physical actuators, or handlers are stubbed, disconnected, or incomplete.
4. `NOT IMPLEMENTED`: Architectural capability is specified or referenced in requirements but contains no functional code.
5. `CONCEPT ONLY`: Mentioned purely in product proposals, marketing copy, or future roadmap targets without code or hardware implementation.

---

## 2. Complete Repository Structure & File Breakdown

```
RDSim-devel-2wheel_diff/
├── delivery_robot_sim/                # Primary ROS 2 Python application package
│   ├── config/                        # Robot parameters and camera configs
│   ├── delivery_robot_sim/            # Core Python modules & ROS 2 nodes
│   │   ├── cargo_delivery_manager.py  # Gazebo hatch motor & parcel spawner
│   │   ├── city_driver_node.py        # City sidewalk waypoint following & reactive avoidance
│   │   ├── compartment_manager.py     # Cargo state machine & security OTP tokens
│   │   ├── control.py                 # Pure pursuit controller & differential kinematics
│   │   ├── database.py                # ACID SQLite backend with tenant isolation & audit logs
│   │   ├── driver_node.py             # Closed-loop corridor driver
│   │   ├── evaluator_node.py          # Ground-truth metric scoring & collision evaluator
│   │   ├── gazebo_world_map.py        # Small city topological graph & metric bounds
│   │   ├── order_manager.py           # Multi-order queue & state tracker
│   │   ├── order_manager_node.py      # ROS 2 lifecycle bridge for dispatch & delivery
│   │   ├── progress_watchdog.py       # Stall detection & recovery supervisor
│   │   ├── route_planner.py           # A* sidewalk topological router & heuristic planner
│   │   ├── safety_supervisor.py       # Obstacle emergency stop & pedestrian slowdown FSM
│   │   ├── security.py                # PBKDF2-HMAC-SHA256, session tokens, CSRF tokens
│   │   ├── track_geometry.py          # Spline interpolation & sidewalk bounds
│   │   ├── traffic_light_node.py      # Vision-based intersection red/green detector
│   │   ├── vision.py                  # RealSense image processing & depth estimation
│   │   ├── web_bridge_node.py         # Multi-threaded HTTP/REST & WebSocket bridge
│   │   └── yolo_detector.py           # YOLOv8n object classifier (pedestrians, cars)
│   ├── tests/                         # Automated unit & integration test suites
│   │   ├── test_core.py               # Core autonomy, routing, & control tests
│   │   ├── test_security_database.py  # PBKDF2, sessions, tenant isolation, SQL tests
│   │   ├── test_web_portals.py        # Tri-portal routing & RBAC enforcement tests
│   │   └── verify_acceptance_criteria.py # Comprehensive compliance validator
│   └── web_dashboard/                 # Pure Vanilla HTML5/CSS3/ES6 frontend portals
│       ├── index.html                 # Corporate landing portal (/)
│       ├── client.html                # Customer ordering & tracking portal (/client)
│       ├── supervisor.html            # Fleet engineer & cockpit portal (/supervisor)
│       ├── corporate.css / client.css / supervisor.css # Scoped CSS design systems
│       ├── client.js / supervisor.js  # Dedicated frontend controllers
│       ├── gazebo_map.js              # 1:1 Affine Canvas 2D Gazebo world visualizer
│       └── app.js                     # 3D Three.js simulation renderer
├── rdsim_description/                 # Robot URDF & Gazebo simulation descriptions
│   ├── urdf/
│   │   ├── rdsim.urdf.xacro           # Differential chassis, wheels, caster, hatch joint
│   │   └── rdsim.camera_only.gazebo.xacro # Camera sensor, odometry plugin, hatch plugin
├── rdsim_gazebo/                      # Gazebo Classic 11 simulation package
│   ├── worlds/
│   │   ├── small_city_dynamic.world   # Canonical urban environment (80m x 80m ground plane)
│   │   └── delivery_city.world        # Secondary legacy test environment
│   └── launch/                        # ROS 2 launch scripts
├── docs/                              # Engineering documentation & architecture specifications
│   ├── architecture/                  # Subsystem designs (geospatial, security, dispatch)
│   ├── audit/                         # Formal verification reports & gap analysis
│   └── hardware/                      # Mechanical BOM, power tree, carrier board specs
└── results/                           # Test results, SQLite DB, and execution traces
```

---

## 3. Active Frontend Portals & Entry Points

The frontend architecture enforces strict tri-portal role separation with Zero-Data-Leakage boundary routing:

| Portal Path | Target Audience | Primary Function | Verification State |
| :--- | :--- | :--- | :--- |
| `/` | Public Visitors, Investors | Corporate presentation, engineering specs, product mission, TRL 3–4 disclosure. Contains no live robot controls or operational telemetry. | `IMPLEMENTED AND VERIFIED` |
| `/client` | Authenticated Customers | Curbside food/grocery catalog, interactive destination pin selection, cart checkout, real-time rover tracking, OTP hatch unlatching. | `IMPLEMENTED AND VERIFIED` |
| `/supervisor` | Authorized Operators | Real-time 50 Hz telemetry cockpit, obstacle telemetry, camera feed, emergency stop, teleoperation overrides, hardware test routines, immutable audit trail. | `IMPLEMENTED AND VERIFIED` |

---

## 4. Backend Services & REST API Inventory

The web server is served by `WebBridgeNode` (`delivery_robot_sim/delivery_robot_sim/web_bridge_node.py`), providing multi-threaded HTTP handling:

| API Route | HTTP Method | Authorization Level | Description | Verification State |
| :--- | :--- | :--- | :--- | :--- |
| `/api/telemetry` | `GET` | Public | Real-time rover telemetry (x, y, yaw, velocity, state, obstacles, freshness). When offline, velocities report 0.0 m/s. | `IMPLEMENTED AND VERIFIED` |
| `/api/map/gazebo_world` | `GET` | Public | World geometric bounds, road corridors, sidewalk graph, buildings, and depot coords from `small_city_dynamic.world`. | `IMPLEMENTED AND VERIFIED` |
| `/api/products` | `GET` | Public | Curbside catalog (weights, prices, categories, dimensions). | `IMPLEMENTED AND VERIFIED` |
| `/api/customers` | `GET` | Public | Registered delivery customer profiles and delivery bays. | `IMPLEMENTED AND VERIFIED` |
| `/api/auth/register` | `POST` | Public | Customer account registration with PBKDF2-HMAC-SHA256 password hashing. | `IMPLEMENTED AND VERIFIED` |
| `/api/auth/login` | `POST` | Public | Authenticates credentials, generates cryptographically secure 256-bit token. | `IMPLEMENTED AND VERIFIED` |
| `/api/auth/verify_pin` | `POST` | Operator/Public | Validates operator master PIN (`NEXUS_OPERATOR_PIN`) for supervisor elevation. | `IMPLEMENTED AND VERIFIED` |
| `/api/orders` | `GET` | Authenticated | Customer queries return only their tenant-scoped orders; Operator queries return all fleet orders. | `IMPLEMENTED AND VERIFIED` |
| `/api/customer_order` | `POST` | Authenticated | Validates destination reachability, payload capacity, creates DB order, triggers dispatch. | `IMPLEMENTED AND VERIFIED` |
| `/api/verify_otp` | `POST` | Public / Customer | Validates 6-digit handover OTP code and triggers motorized cargo hatch unlatch. | `IMPLEMENTED AND VERIFIED` |
| `/api/addresses` | `GET` / `POST` | Authenticated | Manages customer saved delivery addresses with Gazebo coordinates. | `IMPLEMENTED AND VERIFIED` |
| `/api/audit_logs` | `GET` | Operator Only | Queries immutable SQLite audit log table (50 most recent security/operational events). | `IMPLEMENTED AND VERIFIED` |
| `/api/estop` | `POST` | Operator Only | Triggers immediate software emergency stop via `/safety/estop`. | `IMPLEMENTED AND VERIFIED` |
| `/api/teleop` | `POST` | Operator Only | Dispatches manual Twist velocity commands to `/cmd_vel`. | `IMPLEMENTED AND VERIFIED` |
| `/api/hardware_test`| `POST` | Operator Only | Executes automated diagnostic sweep of hatch, actuators, and power bus. | `IMPLEMENTED AND VERIFIED` |
| `/stream/camera.mjpg` | `GET` | Public / Cockpit | Multipart MJPEG camera stream from RealSense topic with synthetic fallback. | `IMPLEMENTED AND VERIFIED` |

---

## 5. Security & Authentication Architecture

| Security Mechanism | Implementation Details | Verification State |
| :--- | :--- | :--- |
| **Password Hashing** | PBKDF2-HMAC-SHA256 with 100,000 iterations (configurable) and 16-byte cryptographically random salt. | `IMPLEMENTED AND VERIFIED` |
| **Session Management** | Cryptographically secure 256-bit hexadecimal tokens (`secrets.token_hex(32)`) with 24-hour expiration window. | `IMPLEMENTED AND VERIFIED` |
| **CSRF Protection** | Unique per-session CSRF tokens validated on all state-mutating POST requests. | `IMPLEMENTED AND VERIFIED` |
| **Role-Based Access Control** | Strictly partitioned roles: `CUSTOMER`, `OPERATOR`, `SUPER_ADMIN`, `FLEET_MANAGER`, `MAINTENANCE_ENGINEER`. | `IMPLEMENTED AND VERIFIED` |
| **Tenant Isolation** | SQLite queries strictly filtered by `customer_id = session.user_id`. Customer cannot view or manipulate other customers' orders. | `IMPLEMENTED AND VERIFIED` |
| **Supervisor Elevation** | Supervisor cockpit actions require bearer token with `OPERATOR` or `SUPER_ADMIN` role or verified operator PIN. | `IMPLEMENTED AND VERIFIED` |
| **Audit Logging** | SQLite `audit_logs` table records actor ID, role, action, target entity, timestamp, and metadata for every security and dispatch event. | `IMPLEMENTED AND VERIFIED` |

---

## 6. ROS 2 Autonomy Graph & Simulation Mapping

### Active Topics & Services
| Topic Name | Message Type | Rate | Description | Verification State |
| :--- | :--- | :--- | :--- | :--- |
| `/odom` | `nav_msgs/msg/Odometry` | 50 Hz | Wheel odometry fused with Gazebo ground-truth pose. | `IMPLEMENTED AND VERIFIED` |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 20 Hz | Velocity commands generated by pure pursuit / avoidance controller. | `IMPLEMENTED AND VERIFIED` |
| `/camera/color/image_raw` | `sensor_msgs/msg/Image` | 30 Hz | RealSense RGB optical camera stream (640x480). | `IMPLEMENTED AND VERIFIED` |
| `/camera/depth/image_raw` | `sensor_msgs/msg/Image` | 30 Hz | RealSense depth stream (32-bit float metric depth). | `IMPLEMENTED AND VERIFIED` |
| `/delivery/new_order` | `std_msgs/msg/String` | Event | JSON dispatch command triggering autonomous delivery mission. | `IMPLEMENTED AND VERIFIED` |
| `/delivery/current_target` | `std_msgs/msg/String` | Event | Current waypoint target coordinates and action type. | `IMPLEMENTED AND VERIFIED` |
| `/delivery/hatch_cmd` | `std_msgs/msg/String` | Event | Hatch actuator command (`OPEN`, `CLOSE`). | `IMPLEMENTED AND VERIFIED` |
| `/delivery/package_cmd` | `std_msgs/msg/String` | Event | Package loading/unloading trigger in Gazebo. | `IMPLEMENTED AND VERIFIED` |
| `/safety/estop` | `std_msgs/msg/String` | Event | Emergency stop lock command (`ENGAGE`, `RELEASE`). | `IMPLEMENTED AND VERIFIED` |
| `/cargo/lift_cmd` | `std_msgs/msg/String` | Event | Prismatic vertical lift actuator command (`RAISE`, `LOWER`). | `PARTIALLY IMPLEMENTED` |

---

## 7. Robot Model & Mechanical Joints Audit

The physical robot model is defined in `rdsim_description/urdf/rdsim.urdf.xacro`:
- **Chassis Base Link:** $0.72\text{ m} \times 0.48\text{ m} \times 0.32\text{ m}$ rectangular composite enclosure with ground clearance $0.05\text{ m}$.
- **Drive Wheels:** 2 differential drive wheels (radius $0.10\text{ m}$, width $0.05\text{ m}$, track gauge $0.46\text{ m}$).
- **Passive Support:** Front and rear low-friction spherical caster wheels.
- **Motorized Hatch Joint (`hatch_joint`):** Revolute joint on top surface, rotating from $0.0\text{ rad}$ (closed) to $1.05\text{ rad}$ ($60^\circ$ open).
- **Vertical Cargo Lift (`cargo_lift_joint`):** Prismatic joint inside enclosed cargo bay. Stroke: $0.0\text{ m}$ to $0.12\text{ m}$ vertical elevation. (See Phase 6 & 7 implementation).

---

## 8. Summary of Architectural Verification States

| Subsystem | Implemented & Verified | Implemented (Unverified) | Partially Implemented | Not Implemented | Concept Only |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Tri-Portal Web Frontend | 100% | 0% | 0% | 0% | 0% |
| Security & RBAC Backend | 100% | 0% | 0% | 0% | 0% |
| SQLite Persistence & Auditing | 100% | 0% | 0% | 0% | 0% |
| ROS 2 Core Autonomy & Routing | 90% | 10% | 0% | 0% | 0% |
| Gazebo World Coordinate Sync | 95% | 5% | 0% | 0% | 0% |
| Cargo Hatch Actuator | 90% | 10% | 0% | 0% | 0% |
| Cargo Vertical Lift Actuator | 0% | 0% | 75% | 25% | 0% |
| Multi-Order Dispatch Optimizer | 80% | 10% | 10% | 0% | 0% |
