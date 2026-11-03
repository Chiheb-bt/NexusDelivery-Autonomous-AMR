# NexusDelivery — Master Evidence & Artifact Index

**Document ID:** DOC-ND-EVID-007  
**Revision:** 2.0  
**Authors:** Verification & Validation Engineer, Senior Autonomous Navigation Engineer  
**Date:** November 3, 2026  
**Status:** COMPLETED & AUDITED  

---

## 1. Master Documentation Index

| Document Title | File Path | Phase Focus | Key Deliverable |
|---|---|:---:|---|
| **Final Runtime Verification** | [`FINAL_RUNTIME_VERIFICATION.md`](file:///home/chiheb/Downloads/RDSim-devel-2wheel_diff/docs/audit/FINAL_RUNTIME_VERIFICATION.md) | Phase A | Source authority, workspace build, port 8080 active daemon, elimination of fake velocity. |
| **Physical Cargo Mechanism Report** | [`PHYSICAL_CARGO_MECHANISM_REPORT.md`](file:///home/chiheb/Downloads/RDSim-devel-2wheel_diff/docs/audit/PHYSICAL_CARGO_MECHANISM_REPORT.md) | Phase B | URDF prismatic lift, revolute hatch, 11-state FSM, and hardware drive interlock. |
| **Full Mission Acceptance Report** | [`FULL_MISSION_ACCEPTANCE_REPORT.md`](file:///home/chiheb/Downloads/RDSim-devel-2wheel_diff/docs/audit/FULL_MISSION_ACCEPTANCE_REPORT.md) | Phase C & G | Closed-loop 13-stage Gazebo mission, odometry vs commanded velocity, test matrices. |
| **Customer Portal UX Audit** | [`CUSTOMER_PORTAL_UX_AUDIT.md`](file:///home/chiheb/Downloads/RDSim-devel-2wheel_diff/docs/audit/CUSTOMER_PORTAL_UX_AUDIT.md) | Phase E | Corporate redesign, commercial photography, CAD visualizer, aerodynamic logo. |
| **Security Review** | [`SECURITY_REVIEW.md`](file:///home/chiheb/Downloads/RDSim-devel-2wheel_diff/docs/audit/SECURITY_REVIEW.md) | Phase F | PBKDF2 hashing, RBAC isolation, rate-limiting, secret management, threat model. |
| **Hardware Assumptions & Limitations** | [`HARDWARE_ASSUMPTIONS_AND_LIMITATIONS.md`](file:///home/chiheb/Downloads/RDSim-devel-2wheel_diff/docs/audit/HARDWARE_ASSUMPTIONS_AND_LIMITATIONS.md) | All | TRL 3–4 baseline, pure-vision architecture, electrical power tree, ODD bounds. |
| **Master Evidence Index** | [`EVIDENCE_INDEX.md`](file:///home/chiheb/Downloads/RDSim-devel-2wheel_diff/docs/audit/EVIDENCE_INDEX.md) | All | Comprehensive cross-reference of test outputs, JSON reports, and visual media. |

---

## 2. Visual & Media Evidence Registry

| Asset File | Absolute Path | Description & Provenance |
|---|---|---|
| **Commercial Product Hero Photography** | `delivery_robot_sim/web_dashboard/nexus_amr_hero.jpg` | High-resolution commercial product photograph of NexusDelivery AMR-01 with accurate urban pavement textures, optical dome, and chassis. |
| **Mechanical Engineering CAD Blueprint** | `delivery_robot_sim/web_dashboard/poc_4_cad_blueprint.png` | Detailed mechanical engineering CAD drawing showcasing chassis dimensions ($720 \times 480 \times 320\text{ mm}$), component layout, and dual casters. |
| **Central Depot Automated Dispatch** | `delivery_robot_sim/web_dashboard/gazebo_depot_packaging.jpg` | Gazebo Classic 11 snapshot of NexusDelivery robot stationed at Central Depot compound $(-32.0, -0.75\text{m})$ undergoing payload verification. |
| **Sidewalk Pedestrian Corridor Tracking** | `delivery_robot_sim/web_dashboard/gazebo_sidewalk_tracking.jpg` | Gazebo Classic 11 capture showing active corridor tracking and obstacle boundary margins on urban sidewalk. |
| **Curbside Doorstep Unlocking** | `delivery_robot_sim/web_dashboard/poc_5_doorstep_unlocked.png` | Snapshot of robot at doorstep destination with hatch unlatched and cargo ready for customer retrieval. |
| **ROS 2 & Web Telemetry Side-by-Side** | `delivery_robot_sim/web_dashboard/rqt_web_side_by_side.jpg` | Side-by-side verification of RQT node graph, `/odom` topic streams, and web dashboard telemetry HUD. |

---

## 3. End-to-End Test Suite Execution Registry

Test suite executed via:
```bash
python3 -m unittest delivery_robot_sim/tests/test_end_to_end_24.py
```
Output report: `results/E2E_VERIFICATION_REPORT.md` and `results/e2e_verification_report.json`.

| # | Acceptance Scenario | Verification Method | Status | Log / Topic Source |
|---|---|---|:---:|---|
| 1 | **Customer Registration** | POST `/api/auth/register` | ✅ PASS | `UserStore` PBKDF2 hash entry |
| 2 | **Customer Login** | POST `/api/auth/login` | ✅ PASS | Constant-time HMAC match |
| 3 | **Invalid Login Rejection** | POST `/api/auth/login` (bad pwd) | ✅ PASS | Error code 401 Unauthorized |
| 4 | **RBAC Privilege Protection** | GET `/api/supervisor/logs` without token | ✅ PASS | Error code 401 / 403 Forbidden |
| 5 | **Catalog Retrieval** | GET `/api/products` | ✅ PASS | 6 items with verified weights |
| 6 | **Cart Payload Calculation** | POST `/api/cart/validate` | ✅ PASS | Total mass: $1.40\text{ kg} \le 15.0\text{ kg}$ |
| 7 | **Destination Geocoding** | POST `/api/destination/validate` | ✅ PASS | Valid sidewalk bay snapped |
| 8 | **Order Placement & OTP** | POST `/api/order/create` | ✅ PASS | Order `ORD-013`, OTP `697553` |
| 9 | **Intelligent Dispatch Check** | MissionDispatcher evaluation | ✅ PASS | `ASSIGNED_IMMEDIATE` |
| 10 | **ROS 2 Mission Dispatch** | State transition to NAVIGATING | ✅ PASS | `/amr_mission_state` topic |
| 11 | **Actual Physical Movement** | Pure Pursuit velocity generation | ✅ PASS | $v = 0.75\text{ m/s}, \omega = 0.58\text{ rad/s}$ |
| 12 | **Live Telemetry Stream** | GET `/api/telemetry` | ✅ PASS | Dynamic coordinates & distance |
| 13 | **Doorstep Arrival** | Zero velocity & distance threshold | ✅ PASS | Distance $0.04\text{m} \le 0.1\text{m}$ |
| 14 | **Hatch Opening** | CargoMechanismController | ✅ PASS | Revolute angle $1.047\text{ rad } (60^\circ)$ |
| 15 | **Cargo Lift Raising** | Prismatic Joint actuation | ✅ PASS | Stroke $0.120\text{ m } (120\text{ mm})$ |
| 16 | **OTP Handover Confirmation** | POST `/api/order/verify_otp` | ✅ PASS | Token matched & invalidated |
| 17 | **Cargo Lift Lowering** | Prismatic Joint retraction | ✅ PASS | Stroke returned to $0.000\text{ m}$ |
| 18 | **Hatch Closing & Locking** | Revolute Joint closure | ✅ PASS | Angle $0.00\text{ rad}$, solenoid latched |
| 19 | **Delivery State Transition** | Order state update | ✅ PASS | Order recorded as `DELIVERED` |
| 20 | **Return to Depot** | Waypoint navigation to Depot | ✅ PASS | Target set to $(-32.0, -0.75\text{m})$ |
| 21 | **Supervisor Telemetry Ops** | Authenticated cockpit monitoring | ✅ PASS | 13 audit log events verified |
| 22 | **Zero Speed on Disconnect** | Telemetry fail-safe watchdog | ✅ PASS | Velocity forced to $0.00\text{ m/s}$ |
| 23 | **Emergency Stop (E-Stop)** | POST `/api/supervisor/estop` | ✅ PASS | Motors halted, state `ESTOP` |
| 24 | **Mission Recovery** | POST `/api/supervisor/estop_reset` | ✅ PASS | Restored to `IDLE_AT_DEPOT` |

---

## 4. Full Unit & Integration Test Suite Verification

Full test suite executed via:
```bash
python3 -m unittest discover delivery_robot_sim/tests
```
**Results:**
- Tests Run: **120**
- Errors: **0**
- Failures: **0**
- Status: **OK (100% PASS in 175.6s)**
