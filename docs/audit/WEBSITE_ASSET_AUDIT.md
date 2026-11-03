# NexusDelivery — Website Asset & Visual Evidence Audit
**Document Identifier:** AUDIT-ASSET-2026-002  
**Maturity Classification Standard:** 5-State Verification System  
**Audit Scope:** Visual Assets, Camera Frames, Renders, Marketing Imagery, Authenticity Verification  

---

## 1. Executive Summary & Problem Resolution

An exhaustive audit of all visual assets across `delivery_robot_sim/web_dashboard/` and `docs/` was conducted to eliminate misleading imagery, unverified AI concept renders, and fabricated hardware assertions.

Every asset has been evaluated against physical reality in Gazebo Classic (`small_city_dynamic.world`) and the actual ROS 2 perception stack.

---

## 2. Investigation of the Four Visual Evidence Defects

### Defect A: Illustrated Concept Robot on Corporate Page
- **Observation:** The hero illustration on the original landing page depicted a fictional, stylized concept rover with wheel and sensor proportions that did not match the physical URDF/SDF model in `rdsim_description`.
- **Root Cause:** A generic marketing illustration was used rather than a genuine render of the physics model.
- **Resolution:** Replaced in public hero sections with verified orthographic and operational captures from Gazebo (`gazebo_sidewalk_tracking.jpg` and `rqt_web_side_by_side.jpg`). Explicitly labeled as:
  > **TRL 3–4 SIMULATION BASELINE — Gazebo Classic 11 Physics Model**
- **Classification:** `IMPLEMENTED AND VERIFIED`

### Defect B: Telemetry Displaying 0.82 m/s While Idle or Disconnected
- **Observation:** The customer and supervisor dashboards displayed a running speed of $0.82\text{ m/s}$, active power bus metrics, and proximity readings even when Gazebo physics was disconnected or when the rover was standing still at the depot.
- **Root Cause:** 
  1. `web_bridge_node.py` initialized fallback variables with `actual_v = 0.82`, `cmd_v = 0.85`, and updated `last_odom_stamp = time.time()` when ROS was unavailable.
  2. Frontend cache objects in `client.js` and `supervisor.js` hardcoded `actual_v: 0.82`.
  3. Static HTML in `client.html` contained hardcoded `0.82 m/s`.
- **Resolution:**
  1. Default fallback telemetry in `web_bridge_node.py` initialized to $0.00\text{ m/s}$, $x = -32.0$, $y = -0.75$ (Depot coordinates), `last_odom_stamp = 0.0`.
  2. In `get_telemetry()`, when odometry is stale ($>2.0\text{ s}$ or disconnected), reported velocities are strictly forced to $0.00\text{ m/s}$.
  3. Reset frontend JavaScript telemetry caches to $0.00\text{ m/s}$ and replaced hardcoded HTML values with live binding defaults (`0.00 m/s`).
- **Classification:** `IMPLEMENTED AND VERIFIED`

### Defect C: Map Showing "SIMULATION DISCONNECTED" While Telemetry Appeared Live
- **Observation:** The 2D map displayed `SIMULATION DISCONNECTED` badge in red, yet the speed metric showed $0.82\text{ m/s}$ and the robot appeared active in route.
- **Root Cause:** The map canvas evaluated `odom_age` independently while dashboard metric cards displayed stale or hardcoded cached values without checking freshness status.
- **Resolution:** Synchronized the freshness lifecycle across all UI widgets. When `telemetry_freshness` is `DISCONNECTED`, the rover marker enters a grayed standby pulse mode, velocity is forced to $0.00\text{ m/s}$, and status is displayed as `SIMULATION DISCONNECTED - STANDBY AT DEPOT`.
- **Classification:** `IMPLEMENTED AND VERIFIED`

### Defect D: Misleading Camera Frame Showing Human Leg / Blue-Yellow Objects
- **Observation:** Public camera views showed a synthetic, unrepresentative stock image depicting a cropped human leg with blue and yellow objects, coupled with unverified claims of "Intel RealSense D435i + HALO-8L NPU active".
- **Root Cause Identified:** The files `street_camera_frame.jpg` and `intersection_camera_frame.jpg` were static, synthetic mockups saved in `delivery_robot_sim/web_dashboard/` and `docs/assets/`.
- **Actions Taken:**
  1. **Backed up** original files to `docs/assets/archive_misleading/` for audit traceability:
     - `docs/assets/archive_misleading/street_camera_frame.jpg`
     - `docs/assets/archive_misleading/intersection_camera_frame.jpg`
  2. **Permanently deleted** active public files:
     - `delivery_robot_sim/web_dashboard/street_camera_frame.jpg` (DELETED)
     - `docs/assets/street_camera_frame.jpg` (DELETED)
     - `docs/assets/intersection_camera_frame.jpg` (DELETED)
  3. **Replaced web bridge fallback:** `web_bridge_node.py` now dynamically generates an authentic OpenCV synthetic standby frame with explicit status:
     `NEXUSDELIVERY VISION SUBSYSTEM: Awaiting ROS 2 Camera Stream (/camera/color/image_raw)`
  4. **Replaced frontend fallbacks:** Replaced `handleClientCamFallback` and `handleStreamFallback` with authentic Gazebo simulation capture `gazebo_sidewalk_tracking.jpg`.
  5. **Cleaned documentation:** Updated `docs/NEXUS_DELIVERY_PROOF_OF_CONCEPT.md` to reference verified Gazebo simulation captures only.
- **Classification:** `IMPLEMENTED AND VERIFIED`

---

## 3. Comprehensive Asset Inventory & Verification Table

| File Path | Description | Authenticity Source | Verification State |
| :--- | :--- | :--- | :--- |
| `docs/assets/gazebo_sidewalk_tracking.jpg` | Authentic camera frame from Gazebo rover tracking sidewalk lane. | Gazebo Classic runtime capture | `IMPLEMENTED AND VERIFIED` |
| `docs/assets/rqt_web_side_by_side.jpg` | Side-by-side verification of RQT image view and Web Bridge dashboard. | Linux Desktop live session | `IMPLEMENTED AND VERIFIED` |
| `docs/assets/gazebo_new_location.jpg` | Gazebo rover positioned at urban sidewalk waypoint. | Gazebo Classic runtime capture | `IMPLEMENTED AND VERIFIED` |
| `delivery_robot_sim/web_dashboard/gazebo_sidewalk_tracking.jpg` | Web dashboard camera fallback asset. | Gazebo Classic runtime capture | `IMPLEMENTED AND VERIFIED` |
| `docs/assets/archive_misleading/street_camera_frame.jpg` | Archived unauthentic demo screenshot (human leg / objects). | Archived (Non-Active) | `CONCEPT ONLY` (ARCHIVED) |
| `docs/assets/archive_misleading/intersection_camera_frame.jpg`| Archived unauthentic demo screenshot (traffic intersection). | Archived (Non-Active) | `CONCEPT ONLY` (ARCHIVED) |
| `delivery_robot_sim/web_dashboard/favicon.ico` | Standard SVG-derived portal icon. | SVG Vector | `IMPLEMENTED AND VERIFIED` |

---

## 4. Policy for Future Assets

1. **Zero Decorative Deception:** Every screenshot must be a direct screen capture from either Gazebo Classic runtime or the running web dashboard.
2. **Honest Labeling:** All simulation screenshots must be captioned with the exact Gazebo world (`small_city_dynamic.world`) and ROS 2 topic source.
3. **Hardware Transparency:** Concept CAD renderings or prototype carrier board schematics must be explicitly labeled as **CAD Prototype Concept (TRL 3)** and never captioned as a manufactured physical product.
