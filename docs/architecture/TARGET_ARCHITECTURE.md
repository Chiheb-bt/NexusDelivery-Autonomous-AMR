# NexusDelivery — Target System Architecture Specification

**Document Version:** 2.0.0  
**Date:** November 2026  
**Status:** Approved Target Architecture  
**System Classification:** Autonomous Mobile Robotics (AMR) Urban Delivery Platform  
**Target TRL:** TRL 4 (Simulation Validated) $\rightarrow$ TRL 6 (Hardware-in-the-Loop Prototype)

---

## 1. Architectural Vision & Core Principles

The NexusDelivery target architecture transforms the prototype into a production-grade, secure, multi-tier autonomous delivery platform. It is engineered under five non-negotiable principles:

1. **Single Source of Truth (The Gazebo World):** The actual Gazebo simulation environment (`small_city_dynamic.world`) is the operational delivery map. The web application does not render decorative, disconnected external cities; it renders the authentic 3D simulation environment mapped directly into high-fidelity 2D vector coordinate space.
2. **Strict Dual-Product Isolation:** The Customer Experience Platform and the Supervisor Fleet Cockpit are built as two independent applications with distinct visual layouts, separate route trees, independent authentication realms, and strict authorization boundaries.
3. **Defense-in-Depth & Zero-Trust Control:** Every backend endpoint validates authorization independently of frontend visibility. Actuator commands require cryptographic operator verification and produce immutable audit logs.
4. **Honest Telemetry & Ground Truth Separation:** Ground truth from physics simulation is explicitly segregated from the robot's onboard dead-reckoning state. Hardware metrics are labeled with their true evidence tier (Measured vs. Model vs. Datasheet).
5. **Deterministic Robotics Integration:** ROS 2 Humble communication remains isolated on the host/container network. Web clients never interact directly with ROS 2 DDS. A controlled Python integration adapter handles protocol translation, rate limiting, and command validation.

---

## 2. High-Level System Topology

```
+===================================================================================================+
|                                        PUBLIC INTERNET CLIENTS                                    |
+===================================================================================================+
                    |                                                    |
         HTTPS / WebSockets (:8000)                           HTTPS / WebSockets (:8001)
                    |                                                    |
                    v                                                    v
+---------------------------------------+            +---------------------------------------+
|      CUSTOMER DELIVERY PLATFORM       |            |       SUPERVISOR FLEET COCKPIT        |
|  - Landing Page & Onboarding          |            |  - Privileged Employee Authentication |
|  - Argon2id Customer Auth             |            |  - Mandatory MFA & RBAC               |
|  - Interactive Gazebo World Map       |            |  - Multi-Rover Tactical Live Map      |
|  - Doorstep Picker & Reachability API |            |  - Hardware Model Diagnostics         |
|  - Real A* Corridor ETA               |            |  - Audited Teleop & Safe Intervention |
|  - HMAC-SHA256 OTP Compartment Unlock |            |  - Master E-Stop & Incident Records   |
+---------------------------------------+            +---------------------------------------+
                    |                                                    |
                    +--------------------------+-------------------------+
                                               |
                                               v
+===================================================================================================+
|                               NEXUSDELIVERY SHARED SECURE BACKEND                                 |
|                                                                                                   |
|  +---------------------------+  +---------------------------+  +-------------------------------+  |
|  |   Identity & RBAC Engine  |  |  Geospatial & Map Service |  |    Order & Fleet Dispatcher   |  |
|  |   - Argon2id Password Hash|  |  - Gazebo World Boundary  |  |    - Validated Route Distance  |  |
|  |   - HttpOnly Cookie Sess  |  |  - Sidewalk Corridor Mesh |  |    - Multi-Drop Queue FSM      |  |
|  |   - CSRF Token Validation |  |  - Building Collision Box |  |    - Reachability Verification |  |
|  |   - Tenant-Scoped Queries |  |  - Curbside Standoff Bays |  |    - Kinematic ETA Model       |  |
|  +---------------------------+  +---------------------------+  +-------------------------------+  |
|                                              |                                                    |
|  +-------------------------------------------+-------------------------------------------------+  |
|  |                      Relational Persistence Layer (SQLite / PostgreSQL)                     |  |
|  |  - users (id, email, password_hash, role, mfa_secret, created_at)                          |  |
|  |  - addresses (id, customer_id, gazebo_x, gazebo_y, stopping_bay, reachability_status)       |  |
|  |  - orders (id, customer_id, robot_id, items, status, otp_hash, created_at, completed_at)    |  |
|  |  - fleet_robots (id, name, state, battery_model, last_heartbeat, telemetry_freshness)       |  |
|  |  - audit_log (id, actor_id, role, action, target_entity, details, ip_address, timestamp)    |  |
|  +-------------------------------------------+-------------------------------------------------+  |
+==============================================+====================================================+
                                               |
                                Localhost Unix Socket / IPC / ROS 2 Adapter
                                               |
                                               v
+===================================================================================================+
|                                ROS 2 HUMBLE AUTONOMY & SIMULATION                                 |
|                                                                                                   |
|  +---------------------------+  +---------------------------+  +-------------------------------+  |
|  |    Order Manager Node     |  |     City Driver Node      |  |       Safety Supervisor       |  |
|  |    - /delivery/new_order  |  |     - Pure Pursuit Path   |  |       - 10 Deterministic FSM  |  |
|  |    - /delivery/mission_st |  |     - Depth Corridor Scan |  |       - Timeout Latching      |  |
|  |    - /delivery/cur_target |  |     - Collision Avoidance |  |       - /safety/state         |  |
|  +---------------------------+  +---------------------------+  +-------------------------------+  |
|               ^                              ^                                 ^                  |
|               |                              |                                 |                  |
|               v                              v                                 v                  |
|  +---------------------------------------------------------------------------------------------+  |
|  |                       Gazebo Classic 11 Simulation (small_city_dynamic.world)                |  |
|  |  - Operational Footprint: [-48.0, 112.0]m x [-48.0, 48.0]m (15,360 m^2)                    |  |
|  |  - Differential Drive AMR Model (rdsim) with RealSense D435i, IMU, Encoders, 60-deg Hatch  |  |
|  +---------------------------------------------------------------------------------------------+  |
+===================================================================================================+
```

---

## 3. Product Boundary Definitions

### 3.1 Product A: Customer Delivery Platform
- **Audience:** External consumers ordering food, grocery, or healthcare deliveries.
- **Port / Endpoint:** Dedicated port `:8000` (or reverse-proxy route `/customer`).
- **Core Functionality:**
  - Responsive marketing landing page explaining zero-emission sidewalk autonomy.
  - Registration with email verification and secure login.
  - Interactive **Gazebo World Delivery Map**: customers pick their doorstep directly on the authentic simulation map.
  - **Service-Area Validation:** Confirms whether selected point is within operating bounds, reachable from sidewalks, and snaps to a safe curbside delivery bay.
  - Real-time order progress tracking with actual A* route-based ETA.
  - Delivery handover confirmation using dynamic 6-digit OTP codes.
- **Security Boundary:** Customers can never access fleet telemetry, teleoperation controls, supervisor APIs, or orders belonging to other customers.

### 3.2 Product B: Private Supervisor Fleet Cockpit
- **Audience:** Robotics engineers, fleet dispatchers, and field operators.
- **Port / Endpoint:** Dedicated privileged port `:8001` (or reverse-proxy route `/supervisor`).
- **Core Functionality:**
  - Secure employee login with mandatory multi-factor authentication (MFA) for privileged accounts.
  - Role-based access control (`SUPER_ADMIN`, `FLEET_MANAGER`, `OPERATOR`, `MAINTENANCE`, `AUDITOR`).
  - **Gazebo Tactical Fleet Map:** Displays the full city grid, building blocks, active rover location, planned vs. executed route, and stopping bays.
  - Real-time telemetry freshness indicator (`ACTIVE`, `STALE > 2.0s`, `DISCONNECTED`).
  - Powertrain and battery monitoring (transparently labeled as simulation models).
  - Audited manual teleoperation override with operator signing and safety supervisor interlocks.
  - Master Emergency Stop (E-Stop) with hardware contactor simulation.
  - Exportable incident logs and compliance reports.

---

## 4. Coordinate Reference Frame & Transformation

The Gazebo world `small_city_dynamic.world` establishes the single spatial ground truth.

| Frame | Origin $(0, 0)$ | Coordinate System | Boundaries |
|:---|:---:|:---:|:---|
| **Gazebo World Frame** | Intersection of Central Blvd & Central Square | Metric Cartesian (ENU: $+X$ East, $+Y$ North, $+Z$ Up) | $X \in [-48.0, 112.0]\text{ m}, Y \in [-48.0, 48.0]\text{ m}$ |
| **Robot Odom Frame** | Spawn location at Depot $(-31.5, -0.75)$ | Metric Odometry Frame | Integrated wheel encoder counts + IMU yaw |
| **Web Vector Map Frame** | Top-left of rendering canvas / SVG viewport | Normalized Screen Pixels $[0, W] \times [0, H]$ | Computed via affine transformation |

### Affine Coordinate Transformation Equation
To render any Gazebo point $(x_g, y_g)$ onto a web canvas of width $W$ and height $H$ with margin padding $M$:
$$x_{\text{norm}} = \frac{x_g - X_{\min}}{X_{\max} - X_{\min}}, \quad y_{\text{norm}} = \frac{Y_{\max} - y_g}{Y_{\max} - Y_{\min}}$$
$$u = M + x_{\text{norm}} \cdot (W - 2M), \quad v = M + y_{\text{norm}} \cdot (H - 2M)$$

**Inverse Transformation (Web Click to Gazebo):**
$$x_g = X_{\min} + \left(\frac{u - M}{W - 2M}\right) \cdot (X_{\max} - X_{\min})$$
$$y_g = Y_{\max} - \left(\frac{v - M}{H - 2M}\right) \cdot (Y_{\max} - Y_{\min})$$

This formulation guarantees **zero distortion, zero arbitrary GPS offsets, and exact mathematical alignment** with Gazebo physics.
