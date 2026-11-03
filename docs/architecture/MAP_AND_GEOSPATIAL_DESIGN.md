# NexusDelivery — Gazebo World Geospatial Mapping & Service-Area Validation Design

**Document Version:** 2.0.0  
**Date:** November 2026  
**Status:** Approved Geospatial Specification  
**Core Requirement:** The Gazebo World is the Single Source of Truth for Delivery Mapping.

---

## 1. Executive Summary

This specification addresses the critical requirement: **The simulation world created in Gazebo is the primary operational environment for NexusDelivery.** Generic global map providers (such as OpenStreetMap or Mapbox rendering Paris or Tunis) are decoupled from the simulation physics and are strictly superseded by an **authentic 2D Vector Map Engine** derived directly from `small_city_dynamic.world`.

The web interface visualizes the exact metric geometry of the Gazebo city, validates customer doorstep selections against physical building footprints and sidewalk corridors, and drives the robot marker using genuine ROS 2 odometry.

---

## 2. Gazebo World Geometry Specification

### 2.1 Geographic Extents & Reference Frame
- **World Origin $(0, 0)$:** The central intersection of Central Boulevard and North Avenue.
- **Minimum Bounds:** $X_{\min} = -48.0\text{ m}, \quad Y_{\min} = -48.0\text{ m}$
- **Maximum Bounds:** $X_{\max} = +112.0\text{ m}, \quad Y_{\max} = +48.0\text{ m}$
- **Total Span:** $\Delta X = 160.0\text{ m}, \quad \Delta Y = 96.0\text{ m}$
- **Coordinate System:** Right-handed Cartesian (ENU: $+X$ East, $+Y$ North, $+Z$ Up).

### 2.2 Navigable Street Corridors & Sidewalk Meshes

```
Y (+North)
45.0m +---------------------+---------------------+---------------------+  North Street
      |                     |                     |                     |
      |   BLOCK NW          |   BLOCK NC          |   BLOCK NE          |
      |   [-42.5,-17.5]     |   [-12.5,42.5]      |   [47.5,105.0]      |
      |   x [3.0, 42.5]     |   x [3.0, 42.5]     |   x [3.0, 42.5]     |
      |                     |                     |                     |
 0.0m +--[DEPOT]--[BAY]-----+---------------------+---------------------+  Central Blvd
      |  (-31.5)  (-27.5)   |                     |                     |  (Lane: y = -0.75)
      |                     |   BLOCK SC          |   BLOCK SE          |
      |   BLOCK SW          |   [-12.5,42.5]      |   [47.5,105.0]      |
      |   [-42.5,-17.5]     |   x [-42.5,-3.0]    |   x [-42.5,-3.0]    |
      |   x [-42.5,-3.0]    |                     |                     |
-45.0m+---------------------+---------------------+---------------------+  South Street
    -45.0m               -15.0m                 45.0m                108.0m     X (+East)
    West Blvd           North Ave             East Ave             Far East Ave
```

### 2.3 Predefined Curbside Delivery Bays

| Bay Identifier | Customer / Location | Gazebo Door $(x, y)$ | Stopping Bay $(x, y)$ | Approach Heading | Sidewalk Corridor |
|:---|:---|:---:|:---:|:---:|:---|
| `CLIENT_1_NORTH_AVENUE` | Sophie Laurent (Residence) | $(-9.8, 15.0)$ | $(-14.6, 15.0)$ | $0.0\text{ rad} (0^\circ)$ | North Avenue East Sidewalk |
| `CLIENT_2_NORTH_AVENUE` | Marc Dubois (Bakery Storefront)| $(-9.8, 28.0)$ | $(-14.6, 28.0)$ | $0.0\text{ rad} (0^\circ)$ | North Avenue East Sidewalk |
| `CLIENT_3_NORTH_PLAZA` | Elena Rostova (Apartment) | $(-13.4, 38.0)$ | $(-14.6, 38.0)$ | $0.0\text{ rad} (0^\circ)$ | North Avenue North Sidewalk |
| `CLIENT_4_WEST_BOULEVARD`| Lucas Vance (Bistro Patio) | $(-46.5, 15.0)$ | $(-43.8, 15.0)$ | $\pi\text{ rad} (180^\circ)$ | West Boulevard West Sidewalk |
| `CLIENT_5_CENTRAL_SQUARE`| Amira Khan (Central Square) | $(-5.0, 2.5)$ | $(-6.0, 0.0)$ | $\frac{\pi}{2}\text{ rad} (90^\circ)$| Central Boulevard North Sidewalk|
| `CLIENT_6_EAST_AVENUE` | David Kim (Tech Innovation Lab)| $(46.5, 15.0)$ | $(43.8, 15.0)$ | $0.0\text{ rad} (0^\circ)$ | East Avenue East Sidewalk |
| `CLIENT_7_SOUTH_MARKET` | Marcus Brody (Marketplace) | $(-13.4, -25.0)$ | $(-14.6, -25.0)$| $0.0\text{ rad} (0^\circ)$ | South Market Sidewalk |
| `CLIENT_8_FAR_EAST_MARINA`| Chloe Dubois (Marina Pier) | $(108.0, 2.5)$ | $(106.0, 0.0)$ | $0.0\text{ rad} (0^\circ)$ | Far East Marina Pier |
| `DEPOT_POST_OFFICE` | Central Logistics Facility | $(-27.5, -0.75)$| $(-31.5, -0.75)$| $0.0\text{ rad} (0^\circ)$ | Indoor Charging Bay |

---

## 3. Mathematical Coordinate Transformation Engine

The web canvas maps directly to Gazebo using an analytical affine transform.

### Forward Transformation (Gazebo $\rightarrow$ Canvas Screen Space)
Given canvas dimensions width $W$, height $H$, and margin padding $M = 24\text{ px}$:
$$\text{scale}_x = \frac{W - 2M}{X_{\max} - X_{\min}}, \quad \text{scale}_y = \frac{H - 2M}{Y_{\max} - Y_{\min}}$$
$$\text{scale} = \min(\text{scale}_x, \text{scale}_y)$$
$$u = M + (x_g - X_{\min}) \cdot \text{scale}$$
$$v = M + (Y_{\max} - y_g) \cdot \text{scale}$$

### Inverse Transformation (Screen Click $(u, v) \rightarrow$ Gazebo Metric Point $(x_g, y_g)$)
$$x_g = X_{\min} + \frac{u - M}{\text{scale}}$$
$$y_g = Y_{\max} - \frac{v - M}{\text{scale}}$$

*Verification Benchmark:*  
- Center Intersection $(0.0, 0.0\text{m})$ maps to $(u_0, v_0)$ exactly at $30.0\%$ horizontal and $50.0\%$ vertical canvas center.
- Depot Door $(-27.5, -0.75\text{m})$ maps precisely to the East portal of the Depot building.

---

## 4. Multi-Stage Service-Area Reachability Engine

When a customer taps or drops a marker on the map, the backend runs an automated 5-stage validation pipeline:

```
[Customer Map Click (u, v)]
             |
             v Inverse Affine Transform
[Gazebo Point Query: (x_g, y_g)]
             |
             v
+-------------------------------------------------------+
| STAGE 1: Geographic World Boundary Verification       |
| - Condition: X_min <= x <= X_max and Y_min <= y <= Y_max
+-------------------------------------------------------+
             | PASS
             v
+-------------------------------------------------------+
| STAGE 2: Solid Building Footprint Collision Test      |
| - Liang-Barsky check against 6 solid building blocks   |
| - If inside: Check distance to outer perimeter         |
|   * If > 8.0m deep inside: REJECT (Inside Building)    |
|   * If <= 8.0m: Snap to outer perimeter curbside      |
+-------------------------------------------------------+
             | PASS / SNAPPED
             v
+-------------------------------------------------------+
| STAGE 3: Sidewalk Proximity & Snap                    |
| - Find nearest street corridor segment                |
| - If distance > 8.0m from road network:                |
|   REJECT (Unreachable: No Sidewalk Access)            |
+-------------------------------------------------------+
             | PASS
             v
+-------------------------------------------------------+
| STAGE 4: Designated Standoff Bay Matching             |
| - If within 4.0m of known customer door:              |
|   Snap to designated curbside stopping standoff       |
|   (1.20m to 1.50m from wall, approach heading set)   |
+-------------------------------------------------------+
             | PASS
             v
+-------------------------------------------------------+
| STAGE 5: A* Navigability & Path Existence             |
| - Verify topological path exists from Depot Door to bay|
+-------------------------------------------------------+
             | PASS
             v
[SUCCESS: Order Destination Locked with Verified Route]
```

### Rejection Status Codes & Explanations:
- `REJECTED_OUTSIDE_CITY_BOUNDS`: Selected point lies outside the simulated municipality perimeter ($[-48, 112]\text{m} \times [-48, 48]\text{m}$).
- `REJECTED_INSIDE_RESTRICTED_BUILDING`: Target is positioned deep inside private structural walls with no exterior street access.
- `REJECTED_UNREACHABLE_NO_ROAD_ACCESS`: Location is isolated by terrain boundaries without sidewalk connectivity.

---

## 5. Live Telemetry & Visual Status Rendering

### 5.1 Telemetry Freshness Watchdog
Every telemetry frame transmitted to the web interface includes a UTC timestamp and monotonically increasing sequence ID.

| State | Condition | Visual Indicator | System Action |
|:---|:---|:---:|:---|
| **ACTIVE (50 Hz)** | $\Delta t < 1.0\text{ s}$ | Glowing Emerald Dot | Real-time pose updates, active route progress |
| **STALE DATA** | $1.0\text{ s} \le \Delta t \le 3.0\text{ s}$ | Amber Pulse Warning | Disables dispatch buttons, alerts operator |
| **SIMULATION DISCONNECTED** | $\Delta t > 3.0\text{ s}$ | Solid Red Badge | Freezes robot marker, displays reconnecting overlay |

### 5.2 Simulation State Synchronization
- **Gazebo Pause:** When Gazebo physics pause, `/odom` message publication halts; the web map marker stops moving immediately without drift or synthetic interpolation.
- **Gazebo Reset (`Ctrl+R`):** The robot position jumps to spawn coordinates $(-31.5, -0.75)$; the web map clears the active trail and centers the marker on the charging dock.
