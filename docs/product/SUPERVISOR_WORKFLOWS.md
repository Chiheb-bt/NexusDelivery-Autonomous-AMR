# NexusDelivery — Supervisor & Fleet Operations Cockpit Workflows
## Industrial Teleoperation, Multi-Rover Fleet Management, Diagnostics & Safety Intervention

**Document Version:** 2.0.0  
**Target Roles:** Fleet Operations Managers, Field Robotics Engineers, Safety Supervisors  
**Access Tier:** Authenticated Enterprise Supervisor Platform (`/supervisor`)  
**Security Policy:** Least-Privilege RBAC with Mandatory Operator PIN Authentication

---

## 1. Cockpit Architecture & Operational Layout

The Supervisor Cockpit provides a mission-critical tactical interface divided into five coordinated decks:

```text
+-----------------------------------------------------------------------------------------------+
|  1. MISSION CONTROL HEADER: Status Ribbon (ROS 2, Battery, Hailo NPU, FSM, Freshness, E-STOP) |
+-----------------------------------------------+-----------------------------------------------+
|  PANE 1: AI Perception & RealSense HUD        |  PANE 2: Gazebo Tactical Simulation World Map |
|  - Intel RealSense D435i Live Camera Stream   |  - Authentic small_city_dynamic Vector Engine |
|  - YOLOv8n Bounding Boxes & Distance Metric   |  - Layer Toggles: Footprints, Zebra, Bays     |
|  - Ground Plane Corridor & TTC Warning        |  - Dynamic Waypoint Dispatch & Trajectory     |
+-----------------------------------------------+-----------------------------------------------+
|  PANE 3: Powertrain & Hardware Diagnostics   |  PANE 4: Remote Teleop & Terminal Console     |
|  - 25.6V 8S LiFePO4 Cell Voltages (C1-C8)     |  - Directional D-Pad & Keyboard Drive (WASD)  |
|  - Dual ODrive S1 CAN 2.0B Telemetry          |  - Motorized Cargo Hatch Manual Override      |
|  - RPi 5 CPU & Hailo-8L Compute Deck Metrics  |  - Streaming ROS 2 Telemetry Terminal Logs    |
+-----------------------------------------------+-----------------------------------------------+
|  PANE 5: FLEET OPERATIONS DECK: Live Mission Queue & Cryptographic Security Audit Log         |
|  - Real-time Active Orders from Customers (Assigned AMR, Route Dist, ETA, OTP)               |
|  - Append-Only Audit Trail of All Privileged Actions and Safety Interventions                 |
+-----------------------------------------------------------------------------------------------+
```

---

## 2. Standard Operating Procedures (SOPs)

### Workflow 1: Operator Security Authorization
- **Precondition:** Supervisor visits `http://localhost:8080/supervisor`.
- **Default State:** Cockpit opens in **Read-Only Inspection Mode**. Manual teleoperation, waypoint override, and hatch toggle buttons are locked to prevent accidental intervention.
- **Elevation Steps:**
  1. Click the "Operator Locked 🛡️" badge in the header.
  2. Modal prompts for the operator security PIN / token.
  3. Enter valid PIN (read from environment `NEXUS_OPERATOR_PIN` or click "Use Session Token").
  4. Backend validates token via `/api/auth/verify`.
  5. UI unlocks teleoperation controls and updates badge to **"OPERATOR SECURE ✓"** (emerald).
  6. Action is recorded in audit logs.

---

### Workflow 2: Fleet Health & Connectivity Inspection
- **Honest Fleet Designation:**
  - `NEXUS-01`: **SIMULATION ACTIVE** (Gazebo Classic 11.10.2 / ROS 2 Humble). Telemetry is driven live by `/odom` and `/camera`.
  - `NEXUS-02` & `NEXUS-03`: **STANDBY / FLEET TARGET** (Explicitly designated as fleet expansion targets for multi-robot dispatch; zero fabricated movement).
- **Freshness Sentinel:**
  - Header displays `TELEMETRY: LIVE (50 Hz)` when updates arrive within 200 ms.
  - If simulation is paused, crashes, or network drops for $> 2.5\text{ s}$, badge automatically switches to `TELEMETRY: STALE (> 2.5s)` with amber visual alert.

---

### Workflow 3: AI Vision & Obstacle Perception Inspection
- **Modes:**
  - `AI YOLO HUD`: Displays color RGB video stream with synthetic/real YOLOv8n object bounding boxes, confidence score, distance to obstacle, and Ground Plane Corridor lines.
  - `Raw RGB`: Unprocessed $640 \times 480$ camera feed.
  - `Active IR Depth`: Depth-mapped visualization from Intel RealSense infrared stereo sensors.
- **Collision Avoidance Metrics:**
  - **TTC (Time-To-Collision):** Computed as $d / \max(0.1, v)$. If $\text{TTC} < 3.0\text{ s}$, banner warns in red.
  - **Corridor Clearance:** Highlights whether the $2.4\text{ m}$ forward sidewalk corridor is unobstructed.

---

### Workflow 4: Powertrain & Hardware Diagnostics
- **Battery Management System (BMS):**
  - Monitors total pack voltage ($25.6\text{ V}$) and State of Charge ($98\%$, $502\text{ Wh} / 512\text{ Wh}$).
  - Live 8-cell voltage grid: verifies cell balancing (all cells between $3.20\text{ V}$ and $3.22\text{ V}$).
  - Alerts if cell imbalance exceeds $30\text{ mV}$.
- **ODrive S1 Controllers:**
  - Dual axis monitoring over CAN 2.0B bus.
  - Left Drive (Axis 0) & Right Drive (Axis 1): Phase current (A), coil temperature ($^\circ\text{C}$), and wheel velocity ($\text{rad/s}$).
- **Compute Health:**
  - Raspberry Pi 5 Quad-Core Cortex-A76 CPU utilization and thermal dissipation.
  - Hailo-8L M.2 AI Acceleration module temperature and inference FPS.

---

### Workflow 5: Interactive Tactical Waypoint Dispatch
- **Gazebo Vector Map Controls:**
  - Supervisor inspects building polygons, crosswalks, curbside bays, and active AMR trajectory.
  - Toggle layers: `🏢 Buildings`, `🦓 Crosswalks`, `📍 Bays`.
  - Re-center button immediately flies viewport to current robot location.
- **Dispatching Waypoints:**
  1. Click any sidewalk or roadway coordinate on the Gazebo map.
  2. System validates point reachability.
  3. Dispatches coordinate to `/api/dispatch_target` with operator bearer token.
  4. ROS 2 Nav2 / Route Planner recomputes A* trajectory and commands robot.
  5. Terminal logs output: `[DISPATCH] Waypoint acknowledged by ROS 2 Nav2 stack`.

---

### Workflow 6: Manual Remote Teleoperation Override
- **Scenario:** Autonomous robot is blocked by an unmodeled dynamic obstacle or customer requests remote parking assistance.
- **Drive Controls:**
  - Keyboard: `W` (Forward $0.65\text{ m/s}$), `S` (Reverse $-0.45\text{ m/s}$), `A` (Left turn $0.65\text{ rad/s}$), `D` (Right turn $-0.65\text{ rad/s}$).
  - Directional D-Pad: Click and hold buttons on screen.
  - Releasing key or button immediately sends zero velocity (`v=0.0, w=0.0`).
- **Safety Envelope:**
  - Teleop commands are clamped to safe velocities ($v \le 1.0\text{ m/s}$, $|w| \le 1.2\text{ rad/s}$).
  - If obstacle distance $< 0.4\text{ m}$, safety supervisor FSM rejects forward drive commands.

---

### Workflow 7: Master Emergency Stop (E-STOP) Execution & Recovery
- **Triggering E-STOP:**
  - Press the prominent red **"E-STOP"** button in header or hit `Spacebar`.
  - Cockpit Web Audio synthesizer triggers pulsed acoustic alarm.
  - Red flashing banner covers screen: **"EMERGENCY STOP ENGAGED: ALL MOTOR POWER CUT OFF"**.
  - Backend immediately publishes zero velocity clamp to `/cmd_vel` and flips safety FSM to `EMERGENCY_STOP`.
- **Resetting E-STOP:**
  1. Verify simulation or field environment is safe.
  2. Click "RESET E-STOP" in the flashing banner.
  3. Action sends `RESUME` state to `/api/estop`.
  4. System returns to `NORMAL_OPERATION` standby.
  5. Incident is logged with operator timestamp in `audit_logs`.
