# Gazebo Verification: Doorstep Handover & Return to Depot

## 1. Test Setup & Ground Truth Parameters
- **World:** `small_city_dynamic.world`
- **Depot Hub Coordinates:** `(-31.5, -0.75)`
- **Doorstep Target Coordinates:** `(-14.60, 15.00)` (`CLIENT_1_NORTH_AVENUE`)
- **Odometry & Sensor Source:** Gazebo wheel encoders (`/odom`), IMU (`/imu`), Front RGB-D camera (`/camera/image_raw`).
- **Cargo Joint State Source:** `libgazebo_ros_joint_state_publisher.so` (`/joint_states`) monitoring `cargo_hatch_joint`.

---

## 2. Test Execution Log (Live Order ORD-031)

### Phase 1: Order Dispatch & Doorstep Arrival
- **Timestamp:** $t = 0.0\text{s}$
- **Action:** Customer submits order via web UI.
- **Decision:** `IntelligentMissionDispatcher` assigns immediate transit along Central Boulevard $\rightarrow$ North Avenue.
- **Physical Transit:** Rover cruises at up to $1.15\text{ m/s}$ along sidewalk corridors, negotiating the Eastbound stop line and turning onto North Avenue.
- **Arrival Condition:** At $t = 38.4\text{s}$, rover reaches `(-14.23, 14.66)` ($d < 0.5\text{m}$).
- **State Transition:** Enters `WAITING_FOR_CUSTOMER`. `cmd_v = 0.0`, `cmd_w = 0.0`.

### Phase 2: OTP Validation & Motorized Hatch Actuation
- **Timestamp:** $t = 42.1\text{s}$
- **Action:** User enters OTP `661923` into the portal keypad.
- **Actuator Command:** Subprocess executes `gz joint -m rdsim -j cargo_hatch_joint --pos-t 1.05`.
- **Sensor Verification:**
  - Topic: `/joint_states`
  - Joint: `cargo_hatch_joint`
  - Measured Angle: $1.046\text{ rad}$ ($59.93^\circ$)
  - Telemetry: `hatch_angle: 1.05`, `hatch_closed: false`, `hatch_feedback_source: GAZEBO_JOINT_STATES`.
- **Safety Interlock:** `city_driver_node` reports `hatch_is_open = True`. Rover motion locked.

### Phase 3: Explicit Customer Receipt & Hatch Latching
- **Timestamp:** $t = 51.3\text{s}$
- **Action:** User clicks `[ 📦 I HAVE RECEIVED MY PACKAGE ]`.
- **Actuator Command:** Subprocess executes `gz joint -m rdsim -j cargo_hatch_joint --pos-t 0.00`.
- **Sensor Verification:**
  - Measured Angle: $-0.001\text{ rad}$ ($0.0^\circ$)
  - Telemetry: `hatch_angle: 0.00`, `hatch_closed: true`.
- **Safety Release:** Interlock clears; driver node receives `action: 'PARK'` to `(-31.5, -0.75)`.

### Phase 4: Autonomous Return Transit to Depot
- **Route Planning:** A* road planner decomposes trajectory into 4 corridor waypoints:
  1. `WP0: (-15.0, 1.5)` (Southbound North Avenue)
  2. `WP1: (-15.0, -0.75)` (Central Blvd Intersection)
  3. `WP2: (-27.5, -0.75)` (Depot Entrance Portal)
  4. `WP3: (-31.5, -0.75)` (Depot Central Dock)
- **Obstacle Clearance:** Dynamic pedestrian tracker and depth obstacle sensor verify clear path.
- **Cruising Speed:** $0.95 - 1.20\text{ m/s}$ along straight corridors.

### Phase 5: Depot Portal Entry, Docking & Mission Completion
- **Portal Entry:** Rover traverses `(-27.5, -0.75)` without clipping door frame.
- **Final Docking Pose:**
  - $x = -31.33\text{ m}$
  - $y = -0.78\text{ m}$
  - Error to Goal: $0.17\text{ m}$ (within $0.50\text{m}$ arrival tolerance)
  - Speed: $0.00\text{ m/s}$
- **Final Mission State:** `WAITING_FOR_ORDER` (Mission completed cleanly; rover parked in standby for subsequent dispatches).

---

## 3. Idempotency & Fault Injection Tests

| Test Case | Injected Condition | Expected Behavior | Actual Observed Outcome | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Test 1** | Correct OTP (`661923`) | Unlatch hatch to $60^\circ$ | Joint actuated to $1.046\text{ rad}$ | **PASS** |
| **Test 2** | Incorrect OTP (`999999`) | Reject with error | HTTP 400 `INVALID_OTP`; hatch remains locked | **PASS** |
| **Test 3** | Hatch Open Motion Attempt | Rover receives goal while open | Chassis locked at $0.0\text{ m/s}$, `CARGO_DOOR_AJAR` | **PASS** |
| **Test 4** | Customer Receipt Confirmation | Hatch closes, returns to depot | Hatch closed ($0.0\text{ rad}$), drives to depot | **PASS** |
| **Test 5** | Duplicate Confirmation Request | Repeated POST to `/api/confirm_delivery` | Returns idempotent response; no redundant goals | **PASS** |
| **Test 6** | Final Docking Accuracy | Stop at Central Depot Dock | Docked at `(-31.33, -0.78)` ($\Delta = 0.17\text{m}$) | **PASS** |
