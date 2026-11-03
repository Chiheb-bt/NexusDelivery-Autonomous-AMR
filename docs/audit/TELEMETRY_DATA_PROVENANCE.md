# NexusDelivery — Telemetry Data Provenance & Source Audit (Phase 5)

**Document ID:** DOC-ND-DATA-PROV-004  
**Audit Date:** November 3, 2026  
**Auditing Team:** Backend, Frontend & Product UX Engineering Team  
**Focus:** Exact Data Provenance, Update Frequencies, and Stale Fallback Behaviors  

---

## 1. Executive Summary & Telemetry Truth Policy

In adherence to Project Rule 5 ("Do not fabricate camera feeds, robot positions, GPS, sensor readings, battery levels, delivery events, or customer data"), every single data point served by `/api/telemetry` and displayed across the Corporate, Customer, and Supervisor portals was audited.

This document records the exact provenance of every telemetry parameter, categorizing each as **MEASURED (from ROS/Gazebo)**, **CALCULATED (from mathematical model)**, **SOFTWARE SIMULATED (internal state FSM)**, or **DATABASE BACKED**.

---

## 2. Comprehensive Telemetry Provenance Table

| Telemetry Field | Display Label | Primary Source | Type | Update Rate | Stale / Disconnected Behavior |
|---|---|---|:---:|:---:|---|
| `x`, `y` | Metric Position $(X, Y)$ | `/odom` (`nav_msgs/Odometry`) | **MEASURED** | 50 Hz | Retains last known pose; flagged `is_stale: true` after 2.0s. |
| `actual_v` | Current Linear Velocity | `/odom` (`twist.twist.linear.x`) | **MEASURED** | 50 Hz | **Forced to 0.00 m/s** when `odom_age > 2.0s`. Zero fake drift. |
| `actual_w` | Current Angular Velocity | `/odom` (`twist.twist.angular.z`)| **MEASURED** | 50 Hz | **Forced to 0.00 rad/s** when disconnected. |
| `cmd_v`, `cmd_w` | Commanded Velocities | `/cmd_vel` (`geometry_msgs/Twist`)| **MEASURED** | Event/10Hz| **Forced to 0.00** when disconnected. |
| `gps_lat`, `gps_lng` | Geographic Coordinates | Mathematical projection from $(X, Y)$ | **CALCULATED** | 50 Hz | Projected from metric coordinates onto Tunis datum ($36.8005^\circ\text{N}, 10.1800^\circ\text{E}$). |
| `target_gps_lat/lng` | Target Waypoint GPS | Mathematical projection from target $(X, Y)$ | **CALCULATED** | Event | Derived from snapped destination bay. |
| `battery_voltage_v` | Battery Pack Voltage | Mathematical power depletion model | **CALCULATED** | 10 Hz | Fixed at $25.1\text{V}$ nominal model; $0.0\text{V}$ if offline. |
| `battery_pct` | State of Charge (SOC %) | Model: $\max(80, 98 - (0.4 \times d_{total}))$ | **CALCULATED** | 10 Hz | Decrements by distance; not hardware BMS CAN bus. |
| `obstacle_dist` | Obstacle Clearance | `/camera/depth/image_raw` corridor slice | **MEASURED** | 30 Hz | Retains last reading; resets to $99.0\text{m}$ (clear) on timeout. |
| `obstacle_detected` | Obstacle Warning Flag | Boolean from depth threshold ($< 2.4\text{m}$) | **CALCULATED** | 30 Hz | Falls back to `False` when camera feed offline. |
| `is_pedestrian` | Pedestrian Detection | YOLOv8n inference on host CPU | **MEASURED** | Event/10Hz| Falls back to `False` when detector offline. |
| `hatch_angle` | Hatch Opening Angle | `cargo_controller.hatch_angle` | **SOFTWARE SIMULATED** | Event | Internal Python FSM state; NOT read from `/joint_states`. |
| `hatch_status` | Hatch Latch State | `LOCKED`, `UNLOCKED`, `OPEN` | **SOFTWARE SIMULATED** | Event | Derived from FSM state transitions. |
| `cargo_lift_position_m`| Cargo Lift Height | `cargo_controller.lift_position` | **SOFTWARE SIMULATED** | Event | Internal Python FSM state ($0.0\text{ to }0.12\text{m}$); NOT read from Gazebo. |
| `can_drive` | Drive Interlock Flag | `cargo_controller.can_drive()` | **SOFTWARE SIMULATED** | 10 Hz | Evaluates hatch & lift state; enforces drive inhibition. |
| `mission_state` | Vehicle Mission Phase | `/mission/state` (`std_msgs/String`) | **MEASURED** | Event/10Hz| Displays current state (e.g., `NAVIGATING`, `IDLE_AT_DEPOT`). |
| `safety_state` | Safety Supervisor State | `/safety/state` (`std_msgs/String`) | **MEASURED** | 20 Hz | Displays `NORMAL_OP`, `DECEL_FOR_OBSTACLE`, `ESTOP`. |
| `orders_completed` | Completed Delivery Count | SQLite Database (`nexus_delivery.db`) | **DATABASE** | Event | Verified against database order records. |
| `freshness_status` | System Liveness Badge | Calculated from `time.time() - last_odom` | **CALCULATED** | 10 Hz | `LIVE (50Hz)` ($<0.2\text{s}$), `STALE` ($<10\text{s}$), `SIMULATION DISCONNECTED` ($>10\text{s}$). |

---

## 3. Disconnected System Integrity & Zero-Fake-Telemetry Policy

### 3.1 What Happens When Simulation Is Offline?
Prior iterations of the project contained cosmetic fallbacks that created an illusion of movement when Gazebo was disconnected. Under the current verified baseline:
1. **Velocity Clamping:**  
   `actual_v` and `actual_w` immediately clamp to `0.00 m/s` and `0.00 rad/s` if `/odom` messages are absent for $> 2.0\text{ seconds}$.
2. **Freshness Latching:**  
   The UI prominently displays `SIMULATION DISCONNECTED` and sets the telemetry badge to an amber/red warning color.
3. **Camera Standby Canvas:**  
   The video stream replaces camera imagery with a gray/black standby indicator:
   `SIMULATION DISCONNECTED • AWAITING /camera/image_raw`.
   No pre-recorded loop, stock image, or AI-generated street photo is displayed as live video.

---

## 4. Website Asset & Portal Verification

| Portal Interface | URL Path | Verification Status | Functional Scope |
|---|---|:---:|---|
| **Corporate Website** | `http://127.0.0.1:8080/` | **VERIFIED (200 OK)** | Serves real product photography (`nexus_amr_hero.jpg`), interactive CAD visualizer (`poc_4_cad_blueprint.png`), Gazebo simulation evidence, specs, and auth modal. |
| **Customer Storefront** | `http://127.0.0.1:8080/client` | **VERIFIED (200 OK)** | Serves product catalog, cart drawer with payload calculation ($\le 15.0\text{kg}$), Gazebo vector map, and 6-digit OTP delivery status. |
| **Supervisor Cockpit** | `http://127.0.0.1:8080/supervisor` | **VERIFIED (200 OK)** | Serves 50 Hz telemetry HUD, audit logs, authenticated E-Stop controls, and mission recovery buttons. |
| **REST APIs (`/api/*`)** | `http://127.0.0.1:8080/api/*` | **VERIFIED (200 OK)** | Serves telemetry, products, orders, auth, dispatch logs, and cargo status. |

---

## 5. Telemetry Provenance Sign-Off

- **Empirical Robot Motion:** Derived genuinely from ROS 2 `/odom` when Gazebo is active.
- **GPS Telemetry:** Truthfully documented as mathematical coordinate projection, not physical GPS hardware.
- **Battery Telemetry:** Truthfully documented as calculated linear power consumption model, not hardware BMS CAN bus.
- **Cargo Mechanism Telemetry:** Truthfully documented as internal Python software FSM states, pending closed-loop `/joint_states` integration.
