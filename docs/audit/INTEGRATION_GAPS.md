# NexusDelivery — Integration Gaps & Discrepancy Analysis
**Document Identifier:** AUDIT-GAP-2026-004  
**Maturity Classification Standard:** 5-State Verification System  
**Audit Scope:** Gaps Between Website Claims, Backend Logic, ROS 2 Autonomy Graph, and Gazebo Physics  

---

## 1. Executive Summary

This document formalizes every identified integration gap between the high-level product presentation (customer web application, supervisor cockpit) and the low-level robotics execution layer (ROS 2 nodes, Gazebo Classic physics, URDF joint actuators).

By cataloging these discrepancies, engineering can systematically bridge each gap without relying on cosmetic fixes or simulated illusions.

---

## 2. Identified Gap Matrix & Resolution Roadmap

| Gap ID | Subsystem | Description of Gap | Severity | Previous State | Target / Resolution State |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **GAP-01** | Telemetry | Web dashboard displayed $0.82\text{ m/s}$ and live stats while Gazebo simulation was disconnected. | High | `PARTIALLY IMPLEMENTED` | `IMPLEMENTED AND VERIFIED` |
| **GAP-02** | Visual Assets | Stock demo images (`street_camera_frame.jpg`) showed unrepresentative human legs and manufactured hardware claims. | High | `CONCEPT ONLY` | `IMPLEMENTED AND VERIFIED` (Archived & Replaced) |
| **GAP-03** | Geospatial | Website mapped Gazebo coordinates into simulated GPS in Tunis, confusing users when simulation coordinates didn't match real street maps. | Medium | `PARTIALLY IMPLEMENTED` | `IMPLEMENTED AND VERIFIED` (Gazebo-native canvas) |
| **GAP-04** | Dispatching | Orders were dispatched in simple arrival order without considering route proximity, payload capacity, or multi-drop batching. | High | `PARTIALLY IMPLEMENTED` | `IMPLEMENTED AND VERIFIED` (Intelligent Multi-Order Dispatcher) |
| **GAP-05** | Mechanical | Robot URDF included motorized hatch (`hatch_joint`), but lacked an enclosed cargo platform and vertical lift prismatic actuator. | High | `NOT IMPLEMENTED` | `IMPLEMENTED AND VERIFIED` (URDF + Controller) |
| **GAP-06** | Handover FSM | Handover flow lacked formal interlocks ensuring the robot cannot drive away while hatch is open or lift is elevated. | Critical | `PARTIALLY IMPLEMENTED` | `IMPLEMENTED AND VERIFIED` (11-State FSM) |
| **GAP-07** | Security | Shared session state allowed potential tenant order leakage; unauthenticated visitors could observe customer orders. | Critical | `PARTIALLY IMPLEMENTED` | `IMPLEMENTED AND VERIFIED` (Tenant isolation + RBAC) |
| **GAP-08** | E-Stop Safety | E-Stop endpoint was coupled to the web UI without a standalone hardware/process supervisory watchdog. | High | `PARTIALLY IMPLEMENTED` | `IMPLEMENTED AND VERIFIED` (`/safety/estop` dual-path) |

---

## 3. Deep Dive Analysis by Engineering Domain

### 3.1 Geospatial & Map Coordinate Mapping (GAP-03)
- **The Discrepancy:** The Gazebo simulation world (`small_city_dynamic.world`) is a metric Cartesian space ($[-48, 48]\text{ m} \times [-48, 48]\text{ m}$). Previously, frontend code translated metric coordinates $(x, y)$ into geographic coordinates in Tunis ($36.8^\circ\text{ N}, 10.18^\circ\text{ E}$) and attempted to render them on standard Leaflet/OpenStreetMap tiles. Because the simulated world is an artificial test city, the robot appeared to drive through real-world buildings, canals, and highways in Tunis.
- **Resolution:** Replaced third-party street maps with an affine 1:1 Canvas 2D engine (`gazebo_map.js`) that renders the exact geometry of `small_city_dynamic.world`:
  - Depots at $(-32.0, -0.75)$
  - Sidewalk corridors and zebra crossings
  - Building footprints ($B_1$ to $B_8$)
  - Verified delivery target bays
- **State:** `IMPLEMENTED AND VERIFIED`

### 3.2 Multi-Order Dispatch & Route Optimization (GAP-04)
- **The Discrepancy:** In early versions, customer orders were executed FIFO. If Customer 1 ordered at North Avenue and Customer 2 ordered at North Avenue two minutes later, the robot completed Customer 1, returned all the way to depot, and then drove back to North Avenue for Customer 2.
- **Resolution:** Built an intelligent multi-order dispatch engine:
  - Groups compatible sidewalk destinations along topological corridors.
  - Enforces payload volume ($22.5\text{ L}$) and mass limits ($15.0\text{ kg}$).
  - Evaluates topological reachability and battery consumption before accepting orders.
  - Generates transparent dispatch decision logs accessible via `/api/dispatch/decision_log`.
- **State:** `IMPLEMENTED AND VERIFIED`

### 3.3 Mechanical Vertical Lift & Cargo Bay Integration (GAP-05 & GAP-06)
- **The Discrepancy:** While documentation claimed a "smart delivery compartment", the URDF model had only a single revolute joint (`hatch_joint`) and no vertical lift platform. Customers were expected to reach deep inside the low chassis ($200\text{ mm}$ deep) to retrieve items.
- **Resolution:**
  1. Modeled `cargo_platform_link` with prismatic joint `cargo_lift_joint` ($0.0\text{ m}$ to $0.12\text{ m}$ vertical stroke) in `rdsim.urdf.xacro`.
  2. Implemented dedicated Gazebo joint controller plugin in `rdsim.camera_only.gazebo.xacro`.
  3. Created dedicated 11-state FSM controller (`cargo_controller.py`) with strict drive inhibition interlocks.
- **State:** `IMPLEMENTED AND VERIFIED`

---

## 4. Verification & Sign-Off Criteria

Before closing any gap in the repository, the following gates must pass:
1. Automated unit test verification in `delivery_robot_sim/tests/`.
2. No mock or hardcoded fallback data masquerading as live telemetry.
3. Affine visual coherence across 2D Canvas map and Gazebo runtime.
4. Security and authorization verified with negative test cases (401/403 rejections).
