# NexusDelivery — Gazebo Actuation & Mechanical Physics Verification Report

**Document ID:** DOC-ND-MECH-VERIF-002  
**Audit Date:** November 3, 2026  
**Auditing Team:** Gazebo Classic Simulation & URDF Engineer, Mechanical Design & Controls Team  
**Focus:** Complete Actuation Chain Audit for Cargo Hatch and Prismatic Lift  

---

## 1. Executive Summary & Physics Actuation Mandate

A robot delivery vehicle is not complete until its physical mechanisms physically move in the simulation physics engine and provide closed-loop telemetry feedback. This audit inspects the full mechanical actuation chain:

$$\text{Customer API Request} \longrightarrow \text{Cargo Controller} \longrightarrow \text{ROS 2 Interface} \longrightarrow \text{Gazebo Joint Actuator} \longrightarrow \text{Physical Movement} \longrightarrow \text{Joint State Feedback} \longrightarrow \text{Dashboard Telemetry}$$

---

## 2. Hatch Actuation Analysis (`cargo_hatch_joint`)

### 2.1 Kinematic URDF Definition (`rdsim.urdf.xacro`)
- **Joint Name:** `cargo_hatch_joint`
- **Parent Link:** `base_link` $\to$ **Child Link:** `cargo_hatch_link`
- **Origin:** $X: -0.26\text{ m}, Y: 0.0\text{ m}, Z: 0.165\text{ m}$ (Rear hinge pivot above cargo compartment)
- **Axis:** `[0, -1, 0]` (Pitches upward toward front)
- **Limits:** Lower $0.0\text{ rad}$ ($0^\circ$, sealed closed), Upper $1.05\text{ rad}$ ($60.16^\circ$, open)
- **Effort Limit:** $50.0\text{ N}\cdot\text{m}$
- **Velocity Limit:** $1.5\text{ rad/s}$
- **Dynamics:** Damping $0.5\text{ N}\cdot\text{s/m}$, Friction $0.05\text{ N}\cdot\text{m}$
- **Inertial Mass:** $0.50\text{ kg}$, $I_{xx}=0.008, I_{yy}=0.008, I_{zz}=0.016\text{ kg}\cdot\text{m}^2$

### 2.2 Actuation Interface & Gazebo Plugin
- **Actuation Driver:** `cargo_delivery_manager.py` (executed inside Docker during simulation runs).
- **Actuation Method:** Executes `gz joint -m rdsim -j cargo_hatch_joint --pos-t <angle> --pos-p 120.0 --pos-d 6.0` via subprocess when running inside the Gazebo container environment.
- **Joint State Publisher:** In `rdsim.camera_only.gazebo.xacro`:
  ```xml
  <plugin name="cargo_joint_state_publisher" filename="libgazebo_ros_joint_state_publisher.so">
    <ros><remapping>joint_states:=/joint_states</remapping></ros>
    <update_rate>30</update_rate>
    <joint_name>cargo_hatch_joint</joint_name>
  </plugin>
  ```
- **Physics Actuation Status:** **IMPLEMENTED AND PHYSICALLY VERIFIED** inside Gazebo container when running the full simulation stack (`camera_only.launch.py`).
- **Telemetry Feedback Loop:**  
  While Gazebo publishes the actual hatch joint angle to `/joint_states`, `web_bridge_node.py` on the host currently reads `self.hatch_angle` directly from the local Python controller variable instead of subscribing to `/joint_states`. Therefore, telemetry feedback is **SOFTWARE SIMULATED ONLY** on the host, even though the joint physically exists and rotates in Gazebo.

---

## 3. Prismatic Lift Actuation Analysis (`cargo_lift_joint`)

### 3.1 Kinematic URDF Definition (`rdsim.urdf.xacro`)
- **Joint Name:** `cargo_lift_joint`
- **Parent Link:** `base_link` $\to$ **Child Link:** `cargo_platform_link`
- **Origin:** $X: -0.04\text{ m}, Y: 0.0\text{ m}, Z: 0.02\text{ m}$ (Centered within cargo compartment floor)
- **Joint Type:** `prismatic`
- **Axis:** `[0, 0, 1]` (Pure vertical translation along Z-axis)
- **Limits:** Lower $0.00\text{ m}$ (Stowed at base), Upper $0.12\text{ m}$ ($120\text{ mm}$ vertical elevation)
- **Effort Limit:** $300.0\text{ N}$ (Simulated lead-screw actuator)
- **Velocity Limit:** $0.05\text{ m/s}$ ($2.4\text{ seconds}$ transit time)
- **Dynamics:** Damping $10.0\text{ N}\cdot\text{s/m}$, Friction $1.0\text{ N}$
- **Platform Mass & Inertia:** Mass $1.50\text{ kg}$, $I_{xx}=0.016, I_{yy}=0.016, I_{zz}=0.032\text{ kg}\cdot\text{m}^2$

### 3.2 Actuation Chain & Gap Analysis
1. **API Trigger:** REST request `POST /api/cargo/lift` receives target height (e.g., $0.12\text{ m}$).
2. **Controller Logic:** `CargoMechanismController._actuate_lift()` in `cargo_controller.py` sets internal Python variables `self.lift_position = target_height` and updates limit switch flags (`switch_lift_upper = True`).
3. **Missing Gazebo Actuator Interface:**
   - Lines 337–348 in `cargo_controller.py` attempt to execute:
     ```bash
     gz joint -m rdsim -j cargo_lift_joint --pos-t 0.120 --pos-p 300.0 --pos-d 15.0
     ```
   - On the host environment, `gz` does not exist (`shutil.which("gz") == None`), so the command is skipped.
   - In `rdsim_gazebo/launch/camera_only.launch.py`, `cargo_controller.py` is not launched as a ROS 2 node. Instead, the legacy node `cargo_delivery_manager.py` is launched, which contains no logic for `cargo_lift_joint`.
   - In `rdsim.camera_only.gazebo.xacro`, `cargo_joint_state_publisher` does **not** include `cargo_lift_joint` in its `<joint_name>` tag.
4. **Physical Actuation Reality:**
   - `cargo_platform_link` and `cargo_lift_joint` are **fully modeled in URDF**, allowing the link to exist in the Gazebo model tree.
   - However, **no active controller applies force or position to `cargo_lift_joint` in Gazebo Classic**.
   - As a result, in Gazebo physics, the lift platform remains seated at $z=0.00\text{ m}$.
   - The reported lift position ($0.12\text{ m}$) on the dashboard originates solely from the Python internal state variable.
- **Truth Classification:** **PARTIALLY IMPLEMENTED** (URDF geometry and mass verified; software FSM verified; Gazebo ROS 2 actuation plugin not configured).

---

## 4. Drive Interlock Verification

### 4.1 Interlock Implementation Logic
The safety interlock is implemented in `cargo_controller.py`:
```python
def can_drive(self) -> bool:
    with self.lock:
        if self.state not in (CargoMechanismState.LOCKED_STOWED, CargoMechanismState.LOCKED_SAFE):
            return False
        if self.hatch_angle > 0.05:
            return False
        if self.lift_position > 0.005:
            return False
        return True
```

### 4.2 Interlock Evaluation
- When the hatch is commanded to open ($\theta = 1.05\text{ rad}$) or the lift is commanded to elevate ($h = 0.12\text{ m}$), `can_drive()` immediately returns `False`.
- In `web_bridge_node.py` and `test_end_to_end_24.py`, all velocity commands are clamped to $(0.0, 0.0)$ while `can_drive() == False`.
- **Truth Classification:** **IMPLEMENTED AND SOFTWARE VERIFIED ONLY**. The interlock functions deterministically at the software supervision level, but is not yet backed by physical joint state feedback from Gazebo sensors.

---

## 5. Actuation Chain Verification Matrix

| Component / Step | Expected Behavior | Actual Behavior | Truth Classification |
|---|---|---|:---:|
| **REST API `/api/cargo/lift`** | Accept height target $[0.0, 0.12]$ | Accurately accepts & validates JSON payload | **IMPLEMENTED AND RUNTIME VERIFIED** |
| **Cargo FSM Transitions** | 11-state deterministic transitions | Transitions through `OPENING`, `LIFTING`, `LOCKED` | **IMPLEMENTED AND SOFTWARE VERIFIED ONLY** |
| **Gazebo URDF Lift Joint** | Prismatic joint with 120mm travel | Modeled in `rdsim.urdf.xacro` with mass/inertias | **IMPLEMENTED AND RUNTIME VERIFIED** |
| **Gazebo Joint Actuator Plugin** | Apply torque/position to lift joint | Missing from `rdsim.camera_only.gazebo.xacro` | **NOT IMPLEMENTED** |
| **Gazebo Joint State Publisher** | Publish `cargo_lift_joint` on `/joint_states` | Not included in publisher plugin joint list | **NOT IMPLEMENTED** |
| **Gazebo Hatch Joint Actuator** | Actuate `cargo_hatch_joint` to 60 deg | Actuated via `gz joint` inside container | **IMPLEMENTED AND PHYSICALLY VERIFIED** |
| **Drive Interlock Enforcement** | Clamp `/cmd_vel` to zero when open/raised | Software clamps command; verified in unit tests | **IMPLEMENTED AND SOFTWARE VERIFIED ONLY** |

---

## 6. Exact Engineering Gap & Minimal Safe Correction

To bridge the gap between software simulation and physical Gazebo actuation without breaking the existing architecture:

1. **Add `cargo_lift_joint` to `cargo_joint_state_publisher`:**  
   Update `rdsim_description/urdf/rdsim.camera_only.gazebo.xacro` to publish both joints:
   ```xml
   <joint_name>cargo_hatch_joint</joint_name>
   <joint_name>cargo_lift_joint</joint_name>
   ```
2. **Implement Gazebo Actuator via ROS 2 Topic or Plugin:**  
   Configure either `gazebo_plugins` joint trajectory controller or integrate the `gz joint` command within the containerized node execution.
3. **Close the Telemetry Loop in `web_bridge_node.py`:**  
   Subscribe directly to `/joint_states` and set `self.hatch_angle` and `self.lift_position` from actual Gazebo feedback instead of internal FSM state variables.
