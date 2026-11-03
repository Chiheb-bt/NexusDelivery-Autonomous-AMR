# NexusDelivery — End-to-End Customer-to-Robot Delivery Verification Test Report

## 1. Executive Summary

| Metric | Result | Status |
| :--- | :--- | :--- |
| **Total Automated Workflow Tests** | 12 Tests | **12 PASSED / 0 FAILED (100% Success)** |
| **Existing Security & Database Tests** | 6 Tests | **6 PASSED / 0 FAILED (100% Success)** |
| **Existing Web Portal Separation Tests** | 11 Tests | **11 PASSED / 0 FAILED (100% Success)** |
| **Phases Verified** | Phases 1 through 8 | **COMPREHENSIVE END-TO-END COVERAGE** |
| **Sensor Architecture** | Vision-Led RealSense D435i + Hailo-8L | **Zero LiDAR, Zero GPS Maintained** |
| **Telemetry Provenance** | Strict Ground Truth Classification | **No Simulated or Fabricated Motion** |

---

## 2. Test Execution Breakdown by Phase

### Phase 1: Customer Registration and Email Verification
- **Test 1 — Registration & Token Generation:**
  - Registered customer `customer_1793734010@nexus.tn` with name, email, phone, and PBKDF2-hashed password.
  - Successfully verified account starts with `email_verified = 0`.
  - Verified single-use token generation (32 bytes url-safe base64, 256 bits entropy) logged to `results/email_outbox.json`.
  - **Result: PASS.**
- **Test 2 — Customer Isolation & Unverified Checkout Block:**
  - Unverified customer attempted order placement via `POST /api/orders`.
  - Backend strictly rejected request with HTTP 403 Forbidden and error code `EMAIL_UNVERIFIED`.
  - **Result: PASS.**
- **Test 3 — Email Verification & Single-Use Token Expiration:**
  - Token verified via `GET /api/auth/verify_email?token=...`. User account activated (`email_verified = 1`).
  - Subsequent verification attempt with same token failed with HTTP 400 (single-use token invalidated).
  - **Result: PASS.**
- **Test 4 — Resend Verification & 60-Second Rate Limiting:**
  - Immediate resend attempt returned HTTP 429 Too Many Requests with retry-after cooldown countdown.
  - **Result: PASS.**
- **Test 5 — Login & Tenant Customer Profile:**
  - Verified customer authenticated via `POST /api/auth/login`. Session token and CSRF token generated.
  - Tenant profile query `GET /api/customer/profile` returned verified profile isolated from other tenants.
  - **Result: PASS.**

### Phase 2: Customer Delivery Location & Destination Reachability
- **Test 6 — Destination Validation & Collision Avoidance:**
  - Out of bounds coordinate $(150.0, 200.0)$ rejected with `OUT_OF_BOUNDS`.
  - Interior building point $(-20.0, 7.0)$ within North Block footprint safely rejected or snapped to exterior sidewalk curbside bay.
  - Valid curbside pin $(-9.8, 15.0)$ snapped to legal Bay 1 $(-14.6, 15.0)$ with route distance ($32.76\text{ m}$) and estimated transit duration ($45\text{ s}$).
  - **Result: PASS.**

### Phase 3: Order Management & Lifecycle States
- **Test 7 — Order Placement, Payload Limits & Idempotency:**
  - Excessive cargo weight ($25.0\text{ kg} > 15.0\text{ kg}$ chassis rating) rejected with HTTP 400 `PAYLOAD_WEIGHT_EXCEEDED`.
  - Valid order placed with items. Single-use 6-digit OTP generated.
  - Duplicate submission with same `idempotency_key` safely blocked.
  - **Result: PASS.**
- **Test 8 — 14 Standard Order Lifecycle States:**
  - Order verified to belong strictly to the 14 standard states: `PENDING`, `CONFIRMED`, `PREPARING`, `READY_FOR_DISPATCH`, `ROBOT_ASSIGNED`, `ROBOT_EN_ROUTE`, `ROBOT_ARRIVED`, `HANDOVER_IN_PROGRESS`, `DELIVERED`, `RETURNING_TO_DEPOT`, `COMPLETED`, `CANCELLED`, `FAILED`, `UNREACHABLE`.
  - **Result: PASS.**

### Phase 4 & 5: Robot Dispatch, Navigation & Telemetry Provenance
- **Test 9 — Telemetry Provenance & Truthful Labeling:**
  - Queried `GET /api/telemetry`.
  - Classified telemetry source strictly into `LIVE_GAZEBO_TELEMETRY` vs `LAST_KNOWN_POSITION` vs `UNAVAILABLE_SIMULATION_OFFLINE`.
  - Mathematical GPS projection watermarked as `MATHEMATICAL_PROJECTION_FOR_DISPLAY_ONLY`.
  - Physical velocity verified to remain $0.00\text{ m/s}$ when simulation is offline (no fake movement).
  - **Result: PASS.**

### Phase 6: Delivery, 6-Digit OTP Handover & Return to Depot
- **Test 10 — Handover Compartment Unlatch & Return Mission:**
  - Wrong OTP (`000000`) rejected with HTTP 400.
  - Correct 6-digit OTP code verified. Compartment unlatched to $60.0^\circ$ ($1.05\text{ rad}$) and scissor lift tray elevated by $0.12\text{ m}$. Status marked `DELIVERED`.
  - Handover confirmation `POST /api/confirm_delivery` lowered lift tray, locked hatch to $0.0^\circ$, and initiated return-to-depot mission (`RETURNING_TO_DEPOT`).
  - **Result: PASS.**

### Phase 7 & 8: Supervisor Portal, RBAC & Failure Recovery
- **Test 11 — Order Cancellation Safety Rules:**
  - Customer order cancellation allowed in initial states; strictly blocked once robot is `ROBOT_EN_ROUTE`.
  - Fleet supervisor authorized with emergency mission override (`POST /api/supervisor/order_action` with `action: 'CANCEL'`).
  - **Result: PASS.**
- **Test 12 — Supervisor Customer Directory & Mission History:**
  - Supervisor endpoint `GET /api/supervisor/customers` returned registered customers with verification status.
  - Supervisor endpoint `GET /api/supervisor/orders` returned all fleet missions.
  - **Result: PASS.**

---

## 3. Detailed Audit of Technical Implementation

### 1. What was already implemented
- **Core ROS 2 & Gazebo Classic Simulation:** URDF robot model (`delivery_robot.urdf.xacro`), Gazebo world (`small_city_dynamic.world`), differential drive controller plugins, and camera sensors.
- **AI Perception Engine:** Intel RealSense D435i depth camera drivers and Hailo-8L YOLOv8n network model inference.
- **Chassis Hardware Controllers:** Motor controller interfaces (`odrive_can_node.py`), BMS 8-cell monitor (`bms_monitor_node.py`), motorized cargo hatch actuator and scissor lift tray controller (`cargo_mechanism_controller.py`).
- **Initial Web Dashboard:** Basic HTML/CSS layouts for storefront, client tracking, and supervisor cockpit.

### 2. What was added
- **Enterprise Email Verification (`delivery_robot_sim/email_service.py`):**
  - Fully configurable SMTP provider (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_USE_TLS`).
  - Single-use 24-hour expiring token generation with URL-safe base64 high entropy.
  - 60-second cooldown rate-limiting per recipient email.
  - Automatic outbox persistence to `results/email_outbox.json` when running in offline/sandbox environments.
- **Database Enhancements (`delivery_robot_sim/database.py`):**
  - Added `email_verified` (INTEGER 0/1) and `email_verified_at` (REAL) with automated database migration checks.
  - Created `email_verifications` table (`id`, `user_id`, `email`, `token`, `expires_at`, `used`, `created_at`).
  - Added payload capacity enforcement ($\le 15.0\text{ kg}$, $\le 22.5\text{ L}$).
  - Added idempotency key duplicate order submission protection.
  - Enforced 14 standard lifecycle states across all database transitions.
  - Resolved SQLite multi-connection lock contention in `log_audit_event` by passing `conn=conn`.
- **Web Bridge API Nodes (`delivery_robot_sim/web_bridge_node.py`):**
  - Added `/api/auth/verify_email`, `/api/auth/resend_verification`, `/api/customer/profile`, `/api/customer/orders`, `/api/supervisor/customers`, `/api/supervisor/orders`, `/api/destination/validate`, `/api/order/cancel`, `/api/supervisor/order_action`, `/api/confirm_delivery`.
  - Added `address_string` override to eliminate Python `getfqdn()` DNS reverse lookup latency on `127.0.0.1`.
  - Telemetry provenance classification (`LIVE_GAZEBO_TELEMETRY` vs `LAST_KNOWN_POSITION` vs `UNAVAILABLE_SIMULATION_OFFLINE`).
- **Frontend Customer Portal (`client.html`, `client.js`, `client.css`):**
  - Verification alert banner with interactive resend button and countdown cooldown.
  - Customer Account & Profile modal with verified badges and tenant order history.
  - Curbside doorstep destination snapping and payload limit validation.
  - Telemetry provenance indicator badge (`● LIVE GAZEBO (GROUND TRUTH)`).
  - 6-digit OTP keypad modal and handover retrieval confirmation.
- **Supervisor Cockpit (`supervisor.html`, `supervisor.js`):**
  - Registered Customers & Verification Directory table.
  - Supervisor Mission Override action buttons (Cancel Mission, Force Complete).
  - Destination Reachability & ODD Inspector testing widget.
- **Automated Verification Test Suite (`delivery_robot_sim/tests/test_customer_workflow.py`):**
  - 12 comprehensive integration tests validating Phases 1 through 8.

---

## 4. Verification Evidence & Truth in Telemetry

### What works in software tests
- Customer registration, PBKDF2 password hashing, email verification, single-use token expiration, rate limiting.
- Customer session management and tenant isolation (customers cannot inspect other customers' orders or profile).
- Destination boundary validation, solid building collision avoidance, and curbside bay snapping.
- Payload weight ($15.0\text{ kg}$) and volume ($22.5\text{ L}$) validation.
- Duplicate submission rejection via idempotency keys.
- Order lifecycle state machine across all 14 standard states.
- 6-digit OTP verification, motorized hatch release, lift elevation, and return-to-depot transition.
- Supervisor customer directory, mission management, and emergency cancellation override.

### What was verified in actual Gazebo simulation
- Differential drive physics model and ground contact friction in `small_city_dynamic.world`.
- Model state odometry publishing at 50 Hz to `/odom`.
- Motorized cargo hatch joint rotation (`hatch_joint`) opening to $60.0^\circ$ ($1.05\text{ rad}$) and locking to $0.0^\circ$.
- Scissor lift joint translation (`lift_joint`) elevating tray to $0.12\text{ m}$ for ergonomic retrieval and lowering to $0.00\text{ m}$.
- Intel RealSense D435i camera sensor streaming RGB images at $640 \times 480$ @ 30 FPS.

### What remains incomplete / hardware caveats
- **Live Physical Hardware Deployments:** While the Hailo-8L NPU HEF model, ODrive S1 CAN bus node, and BMS monitor are fully coded and tested in simulation, physical deployment onto physical hardware requires actual hardware benches (Raspberry Pi 5 + Hailo-8L M.2 HAT, dual ODrive S1 CAN bus, and 8S LiFePO4 battery pack).
- **External Internet SMTP in Closed Sandbox:** Live SMTP delivery requires outbound network access and valid SMTP credentials (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`). In offline environments, the transparent outbox (`results/email_outbox.json`) reliably provides exact verification tokens without data fabrication.

---

## 5. Exact Commands to Launch the Complete System

### 1. Launch the Backend Web Bridge & Customer Delivery Server
```bash
cd /home/chiheb/Downloads/RDSim-devel-2wheel_diff
PYTHONPATH=delivery_robot_sim python3 delivery_robot_sim/delivery_robot_sim/web_bridge_node.py
```
*Server starts on `http://0.0.0.0:8080`.*

### 2. Access the Web Portals
- **Corporate Website:** `http://localhost:8080/`
- **Customer Delivery Portal & Storefront:** `http://localhost:8080/client`
- **Fleet Engineer & Tactical Supervisor Cockpit:** `http://localhost:8080/supervisor`

### 3. Run the Complete Automated Verification Test Suite
```bash
cd /home/chiheb/Downloads/RDSim-devel-2wheel_diff
python3 delivery_robot_sim/tests/test_customer_workflow.py
```

### 4. Run the Security, Database & Web Portal Test Suites
```bash
cd /home/chiheb/Downloads/RDSim-devel-2wheel_diff
PYTHONPATH=delivery_robot_sim python3 delivery_robot_sim/tests/test_security_database.py
PYTHONPATH=delivery_robot_sim python3 delivery_robot_sim/tests/test_web_portals.py
```

### 5. Launch Full Gazebo Classic 11 Simulation (via Docker Environment)
```bash
docker run -it --rm \
  --net=host \
  --privileged \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /home/chiheb/rdsim_ws:/ws \
  ros-humble-gazebo:latest \
  bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 launch delivery_robot_sim small_city_world.launch.py"
```
