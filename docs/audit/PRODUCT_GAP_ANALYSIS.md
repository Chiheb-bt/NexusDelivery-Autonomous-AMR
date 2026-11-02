# NexusDelivery — Product Gap Analysis & Transformation Roadmap

**Audit Date:** November 2, 2026  
**Auditor:** Principal Software Architect & Product UX Engineer  
**Objective:** Bridge the gap between existing simulation prototype and the target commercial-grade dual-platform architecture.

---

## 1. Executive Summary

This document contrasts the **Current As-Built Baseline** against the **Target Product Architecture** defined in the Master Engineering Mission. It articulates the exact technical gaps across product separation, geospatial representation, customer experience, fleet management, backend persistence, and security controls, and outlines a phased execution plan to achieve complete engineering integrity.

---

## 2. Detailed Dimension-by-Dimension Gap Analysis

### 2.1 Product Separation & Access Boundaries

| Dimension | Target Specification | Current As-Built Baseline | Engineering Gap |
|:---|:---|:---|:---|
| **Platform Topology** | Two completely independent web applications with separate routes, distinct visual layouts, and isolated authorization domains. | Single web server serving `client.html` and `supervisor.html` on the exact same HTTP port (8080). | **CRITICAL**. No boundary segregation. Anyone accessing the customer site can navigate directly to `/supervisor`. |
| **Authentication Policy** | Public customer realm (email/password with Argon2id, email verification, password reset) vs. Privileged operator realm (MFA, short-lived tokens, RBAC). | In-memory customer dictionary; static shared PIN in environment for operator actions; no session tokens. | **CRITICAL**. Lack of persistent accounts, lack of MFA for operators, plaintext/unsalted credentials. |
| **Authorization & RBAC** | Strict role-based permissions (`SUPER_ADMIN`, `FLEET_MANAGER`, `OPERATOR`, `MAINTENANCE`, `AUDITOR`, `CUSTOMER`). Customer never accesses supervisor APIs. | No RBAC. All endpoints accept open requests except `/api/dispatch_target` and `/api/estop` which check a single static PIN. `/api/orders` leaks all data. | **CRITICAL**. IDOR/BOLA vulnerability. Customers can access and read all fleet orders and private handover OTPs. |

---

### 2.2 Map Architecture & Gazebo Integration (The Core Mandate)

| Dimension | Target Specification | Current As-Built Baseline | Engineering Gap |
|:---|:---|:---|:---|
| **World Source of Truth** | The **actual Gazebo world** (`small_city_dynamic.world`) is the operational map. True metric $(x, y)$ coordinates, buildings, roads, sidewalks, depot, and stopping bays. | Generic real-world Leaflet map (CartoDB Dark Matter / Esri Satellite) centered at Avenue Habib Bourguiba, Tunis (`36.8005° N, 10.1800° E`). | **CRITICAL**. Total decoupling. The web user views Tunisian streets while the robot operates in a synthetic Gazebo city. |
| **Coordinate Transformation** | Direct 1:1 metric correspondence with Gazebo world origin $(0, 0)$ and documented scale, with forward/inverse transformation verification. | Artificial equirectangular formula projecting Gazebo meters into Earth degrees ($1\text{ m} \approx \frac{1}{111139}^\circ$). | **CRITICAL**. Clicking on an Avenue Bourguiba landmark drops a point that has no meaningful relation to Gazebo geometry. |
| **Destination Reachability** | Customer can select destinations on the Gazebo map. The system validates that the coordinate is in bounds, accessible from sidewalks, outside solid buildings, and snaps to safe curbside bays. | `client.js` sent `target_lat`/`lng`, but `create_and_dispatch_order()` completely ignored the pin and read fixed customer profile coordinates (`cust['x']`, `cust['y']`). | **CRITICAL**. Pin drop on the web was decorative; it did not determine the actual robot target. |
| **Live Robot Tracking** | Robot marker driven strictly by `/odom` telemetry. Freezes if Gazebo pauses; resets if Gazebo resets; displays STALE / DISCONNECTED if telemetry halts. | Marker rendered from `/odom`, but falls back to artificial animated coordinates if disconnected. Distance/ETA calculated with geodesic formulas. | **HIGH**. Must eliminate fallback simulation in JS; ground the marker strictly in verifiable Gazebo telemetry. |

---

### 2.3 Routing, Travel Distance & ETA Calculations

| Dimension | Target Specification | Current As-Built Baseline | Engineering Gap |
|:---|:---|:---|:---|
| **Travel Distance** | Actual traveled metric distance computed along the topological sidewalk A* graph in `route_planner.py`. | Straight-line Euclidean distance or Earth geodesic formula ($1.2\text{ km}$, etc.). | **HIGH**. Underestimates actual path length around building blocks; produces false distance metrics. |
| **ETA Calculation** | Dynamic calculation based on route segment lengths, robot acceleration profile ($1.2\text{ m/s}^2$), cruise speed ($0.85\text{ m/s}$), intersection wait times, and depot dwell ($2.0\text{ s}$). | Heuristic approximation (`dist / 0.8`) or static placeholder text (`~3 min`, `12-15 min`). | **MEDIUM**. Inaccurate arrival estimates for customer. |
| **Trajectory Visualization** | Display both planned A* corridor path and executed historical trajectory in Gazebo metric space. | Polylines plotted on the real-world Tunis map. | **HIGH**. Must render directly on the Gazebo vector city map. |

---

### 2.4 Multi-Robot Fleet Dispatch & Intelligence

| Dimension | Target Specification | Current As-Built Baseline | Engineering Gap |
|:---|:---|:---|:---|
| **Fleet Representation** | Reflects actual simulated or physical robots. Honest distinction between active Gazebo rovers and future planned fleet units. | Displays 3 rovers (`NEXUS-01`, `NEXUS-02`, `NEXUS-03`), but Rovers 02 and 03 are static hardcoded dictionaries with zero physical presence. | **CRITICAL**. Violates Rule 6 (inventing robot locations). Must honestly state `NEXUS-01` is the active Gazebo AMR, while Rovers 02/03 are fleet models/targets. |
| **Dispatch Logic** | Order validation, reachability check, battery reserve evaluation, single-robot assignment, concurrency-safe transitions. | Sequential FIFO queue in `order_manager.py`. Web API creates an order and sends a ROS message, but doesn't track multi-drop manifest concurrently. | **MEDIUM**. Needs clean multi-order queueing and state reconciliation between backend and ROS 2. |

---

### 2.5 Backend Architecture & Observability

| Dimension | Target Specification | Current As-Built Baseline | Engineering Gap |
|:---|:---|:---|:---|
| **Backend Framework** | Modular backend (FastAPI / structured Python service) with clean API documentation and async capabilities. | Python standard library `http.server.BaseHTTPRequestHandler` embedded inside a ROS 2 node class. | **HIGH**. Inflexible routing, no automatic OpenAPI specs, difficult to test outside ROS 2 environment. |
| **Data Persistence** | Relational database (SQLite / PostgreSQL) with schema migrations, relational constraints, and audit logging. | Volatile in-memory Python lists (`self.orders = []`, `self.customers = []`). | **CRITICAL**. Zero persistence. System state is destroyed upon process restart. |
| **Telemetry Freshness** | Defined heartbeat timeouts, explicit STALE / OFFLINE badges, correlation IDs on all dispatch requests. | Polls every 250ms; if polling fails, local JS retains last values without explicit stale warning flags. | **MEDIUM**. Must display clear freshness indicators with timestamps. |

---

## 3. Transformation Roadmap (Phases A through J)

```
+-------------------------------------------------------------------------------+
| PHASE A: Complete Repository Audit & Baseline Verification (CURRENT PHASE)     |
| - Produce REPOSITORY_AUDIT.md, SECURITY_AUDIT.md, ROBOTICS_INTEGRATION_AUDIT.md|
| - Produce PRODUCT_GAP_ANALYSIS.md and answer all 13 core inspection questions. |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PHASE B: Target Architecture, Data Model & Threat Mitigation Strategy         |
| - Formalize dual-portal separation (Customer on :8000, Supervisor on :8001).  |
| - Design relational schema (Users, Roles, Addresses, Orders, AuditLogs).      |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PHASE C: Secure Identity, RBAC & Backend Persistence Foundation               |
| - Implement SQLite/PostgreSQL database with password hashing (Argon2id/PBKDF2)|
| - Build authentication API with session cookies, CSRF protection & RBAC.      |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PHASE D: Authentic Gazebo World Geospatial Vector Mapping Engine              |
| - Extract 2D geometry of small_city_dynamic.world:                            |
|   Streets, sidewalks, building blocks (NW, SW, NC, SC, NE, SE), depot, bays.  |
| - Build interactive Canvas/SVG vector renderer with pan/zoom & coordinate sync.|
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PHASE E: Dedicated Customer Platform                                          |
| - Modern, responsive storefront and interactive Gazebo map destination picker.|
| - Address reachability validator (snaps to curbside bays, rejects buildings). |
| - Real order tracking bound to genuine Gazebo /odom with dynamic A* ETA.      |
| - OTP handover modal with Web Audio feedback.                                 |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PHASE F: Dedicated Supervisor Fleet Cockpit                                   |
| - Secure employee login with mandatory operator authorization.                |
| - Gazebo tactical map showing live robot pose, heading, and planned route.    |
| - Honest fleet status (NEXUS-01 Active Simulation, Fleet Expansion targets).  |
| - Hardware diagnostics (simulated power budget model, Hailo datasheet specs). |
| - Teleoperation override with safety checks and immutable audit logging.      |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PHASE G: Multi-Robot Fleet Dispatch & Route Engine                            |
| - Wire web orders directly to route_planner.py and order_manager.py.          |
| - Implement reachability rejection with explicit user feedback.               |
| - Calculate true Manhattan/corridor distance and kinematic travel time.       |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PHASE H: End-to-End Simulation & Failure Testing (Acceptance Tests 1 to 10)   |
| - Validate landmark coordinate alignment, pause/reset sync, building rejection|
| - Execute verified missions in Gazebo with trajectory recording.              |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
| PHASE I: Documentation Hardening & Truth in Engineering                       |
| - Update README and project status to reflect authentic TRL 3-4 maturity.     |
| - Ensure 100% of unit and integration tests pass with recorded evidence.      |
+-------------------------------------------------------------------------------+
```

---

## 4. Acceptance Criteria for Phase A Completion

1. Complete audit documents written to `docs/audit/`:
   - `REPOSITORY_AUDIT.md` (Complete inventory, dependency map, reusability matrix)
   - `SECURITY_AUDIT.md` (Vulnerability assessment, CWE classification, threat model)
   - `ROBOTICS_INTEGRATION_AUDIT.md` (SDF world analysis, sensor pipelines, reality gaps)
   - `PRODUCT_GAP_ANALYSIS.md` (Dimension-by-dimension comparison and roadmap)
2. All 13 specific inspection questions answered with file citations and line numbers.
3. Zero destructive changes to existing working code.
4. All 84 existing unit tests remain 100% passing.
