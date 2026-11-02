# NexusDelivery — ROS 2 Humble & Gazebo Integration Specification

**Document Version:** 2.0.0  
**Date:** November 2026  
**Status:** Approved Integration Specification  
**Framework:** ROS 2 Humble Hawksbill | DDS: CycloneDDS / FastDDS | Gazebo Classic 11.10.2

---

## 1. Architectural Integration Boundary

To uphold Rule 9 (*Do not expose ROS 2, Gazebo, Docker sockets, or privileged services directly to public browsers*), the web platforms never communicate with ROS 2 DDS directly. 

All interaction is channeled through a **Controlled Localhost Robot Integration Adapter**:
- Runs as a standard ROS 2 node on the internal robotics network (`127.0.0.1` or Docker bridge).
- Subscribes to telemetry topics, rate-limits serialized JSON state, and pushes updates via WebSockets / SSE.
- Accepts authenticated, pre-validated commands from the web backend and publishes to typed ROS 2 topics.

---

## 2. Topic & Interface Catalog

| Topic Name | Message Type | Rate (Hz) | Direction | Purpose |
|:---|:---|:---:|:---:|:---|
| `/odom` | `nav_msgs/msg/Odometry` | 50.0 | Inbound | Metric robot position $(x, y)$, heading yaw, linear & angular velocity |
| `/camera/image_raw` | `sensor_msgs/msg/Image` | 30.0 | Inbound | Raw front RealSense RGB stream (compressed to MJPEG on demand) |
| `/camera/depth/image_raw`| `sensor_msgs/msg/Image` | 30.0 | Inbound | 32FC1 depth pointcloud for corridor clearance |
| `/imu` | `sensor_msgs/msg/Imu` | 50.0 | Inbound | 6-DOF linear acceleration and angular velocity |
| `/mission/state` | `std_msgs/msg/String` | 10.0 | Inbound | Current autonomous FSM state (`NAVIGATING`, `ARRIVED`, `HOLD`) |
| `/safety/state` | `std_msgs/msg/String` | 10.0 | Inbound | Safety supervisor state (`NORMAL_OP`, `TTC_STOP`, `ESTOP`) |
| `/traffic_light/state`| `std_msgs/msg/String` | 5.0 | Inbound | North Avenue crosswalk signal (`GREEN`, `RED`, `UNKNOWN`) |
| `/delivery/new_order` | `std_msgs/msg/String` | On Event | Outbound | Dispatches new customer order JSON to `order_manager_node` |
| `/delivery/current_target`| `std_msgs/msg/String` | On Event | Outbound | Active waypoint target coordinates and standoff heading |
| `/delivery/hatch_cmd` | `std_msgs/msg/String` | On Event | Outbound | Actuates motorized cargo hatch (`OPEN` $60^\circ$ or `CLOSE` $0^\circ$) |
| `/safety/estop` | `std_msgs/msg/String` | On Event | Outbound | Master Emergency Stop command (`STOP` or `RESUME`) |
| `/cmd_vel` | `geometry_msgs/msg/Twist`| 20.0 | Outbound | Manual teleoperation velocity override |

---

## 3. Simulation Time vs. Wall-Clock Synchronization

1. **Simulation Clock (`use_sim_time: True`):**
   - The robotics adapter strictly subscribes to `/clock` published by Gazebo Classic (`clock_update_rate: 200 Hz`).
   - Timestamps attached to odometry, mission transitions, and evaluation logs are recorded in simulation seconds ($t_{\text{sim}}$).
2. **Wall-Clock Time ($t_{\text{wall}}$):**
   - Customer-facing ETAs, database audit logs, and web session expirations use real UTC wall-clock time.
   - The adapter computes the Real-Time Factor (RTF):
     $$\text{RTF} = \frac{\Delta t_{\text{sim}}}{\Delta t_{\text{wall}}}$$
   - When $\text{RTF} < 0.95$ (simulation slowing due to CPU load), the kinematic ETA engine scales predicted arrival durations automatically:
     $$\text{ETA}_{\text{wall}} = \frac{\text{ETA}_{\text{sim}}}{\text{RTF}}$$

---

## 4. Simulation Liveness, Pause & Reset Watchdog

The integration adapter monitors physics execution continuously:
- **Simulation Pause Detection:** If `/clock` does not advance for $> 1.0\text{ second}$ of wall-clock time, the adapter flags `SIMULATION_PAUSED`. The web frontend halts the robot marker and displays a clear `PAUSED` indicator without accumulating drift.
- **Simulation Reset Detection:** If `/odom` position exhibits an instantaneous discontinuity jumping back to $(-31.5, -0.75)$ while `v == 0`, the adapter detects a Gazebo world reset. It clears the executed trajectory trail, resets order FSM states, and synchronizes the web map to the Depot dock.
- **Command Watchdog:** Any velocity command `/cmd_vel` sent via teleoperation expires after $500\text{ ms}$. If the operator web interface disconnects or fails to send keepalive packets, the robot automatically decelerates to a complete stop.
