# Chiheb Robotics — Operator & Mission Control Guide

**Platform:** Chiheb Robotics NexusDelivery Autonomous Platform  
**Lead Robotics Architect:** Chiheb  
**Interface:** Gazebo Classic 3D GUI + Web Mission Control (`http://localhost:8080`)

---

## 1. Quick Launch Commands

### 1.1 Graphical 3D Simulation (Gazebo + Web Control)
Runs the full visual simulation on your local desktop X11 display:
```bash
./run_visual_simulation.sh
```
- Spawns the autonomous delivery robot inside the Central Logistics Depot.
- Opens Gazebo Classic GUI with 3D camera follow mode.
- Serves the **Mission Control HUD** at [http://localhost:8080](http://localhost:8080).
- Simulation continues running until Gazebo is closed or `Ctrl+C` is pressed.

### 1.2 Headless Mission Benchmark
Runs an automated batch evaluation without GUI overhead:
```bash
./run_headless_simulation.sh 180 small_city_dynamic.world
```
- Executes headless at accelerated simulation time.
- Emits real-time trajectory logs, order transition events, and final JSON evaluation summary.

---

## 2. Web Mission Control Interface (`http://localhost:8080`)

### 2.1 Live Computer Vision HUD
- **Augmented Reality (AR) Corridor:** Dynamic perspective road guidance overlay projected onto the front camera feed with curvature responding to turning rate $\omega$.
- **Range Grid:** Transverse range markers at $1\text{m}, 2\text{m}, 3\text{m}$.
- **Radar Reticle:** Target distance crosshair measuring forward clearance.
- **AI Perception Brackets:** Bounding boxes identifying pedestrians and static obstacles with classification, metric distance, and confidence.
- **Traffic Light Status:** Live indicator displaying `[TRAFFIC: GO (GREEN)]` or `[TRAFFIC: STOP (RED)]`.

### 2.2 Live Interactive City Map
- **Depot Hub:** Central facility footprint, bay door egress portal, and interior charging dock.
- **Traffic Lights:** Dynamic intersection signal markers at North Avenue.
- **Target Route:** Active A* street corridor route with waypoint flags.
- **Trajectory Trail:** Color-coded historical path of robot navigation.

### 2.3 Customer Handover Modal
- Pops up automatically when the robot arrives at a customer delivery location (`CLIENT_1` or `CLIENT_2`).
- Displays customer name, destination, package contents, and 6-digit one-time password (OTP).
- Simulates customer authentication and cargo compartment hatch release.

---

## 3. REST API Reference

The embedded Mission Control server exposes REST endpoints on port 8080:

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Main Web Mission Control Single Page Application |
| `/api/telemetry` | `GET` | Real-time robot coordinates, velocities, safety states, obstacle distances, and planned routes |
| `/api/customers` | `GET` | List of registered delivery customers and sidewalk drop-off coordinates |
| `/api/orders` | `GET` | Active manifest of queued, in-transit, and completed orders |
| `/api/orders` | `POST` | Dispatch a new dynamic delivery order with custom coordinates |
| `/api/reachability`| `POST` | Check if candidate drop-off coordinates are within navigable sidewalk corridors |
| `/stream/camera.mjpg` | `GET` | High-performance 20 FPS MJPEG video stream with computer vision overlays |

---

## 4. Troubleshooting & Operational Tips

1. **Port 8080 Conflict:**
   If port 8080 is already occupied by another service:
   ```bash
   lsof -i :8080
   ```
2. **Display Authorization:**
   If Gazebo fails to launch with an X11 error:
   ```bash
   xhost +local:$(whoami)
   ```
3. **Inspect Active Run Logs:**
   ```bash
   tail -f results/run.log
   ```
