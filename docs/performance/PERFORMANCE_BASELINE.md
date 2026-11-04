# Simulation Performance Baseline: Gazebo Classic 11 & ROS 2 Humble

## 1. Baseline Hardware & Simulation Environment
- **Host System:** Linux x86_64
- **Container Environment:** Docker (`ros-humble-gazebo:latest`)
- **Display Server:** X11 (`:0`) with OpenGL hardware acceleration passthrough (`/dev/dri`)
- **Simulation Engine:** Gazebo Classic 11.10.2
- **World File:** `small_city_dynamic.world`
- **Robotic Platform:** RDSim 2-Wheel Differential Drive AMR (`rdsim.urdf.xacro`)

---

## 2. Pre-Optimization Performance Bottlenecks

### 2.1 Dynamic Shadow Mapping & CPU Starvation
- **Original Configuration:**
  - `<scene><shadows>true</shadows></scene>`
  - `<light name='sun'><cast_shadows>true</cast_shadows></light>`
- **Impact:** Dynamic stencil shadow maps computed for every building facade, curb edge, and dynamic obstacle polygon. `gzserver` consumed up to 151% CPU, causing severe rendering frame drops and dragging physics throughput down.

### 2.2 Sub-Optimal ODE Physics Solver Parameters
- **Original Configuration:**
  - Solver: `quick`
  - Iterations: 50 iterations per time step ($dt = 0.005\text{s}$)
  - Update Rate: Hardcoded fixed throttle (`<real_time_update_rate>200</real_time_update_rate>`)
- **Impact:**
  - Measured Real Time Factor (RTF): **0.80x** (1 second of real time simulated only 0.8 seconds of physics).
  - The simulation ran in sluggish slow-motion, producing perceived lag and delaying sensor callbacks.

### 2.3 Narrow Corridor Speed Throttling
- **Original Configuration in `city_driver_node.py`:**
  - `reduced_speed_clearance_m = 3.2m`
  - `v_limit = 0.35 if d < 2.0 else min(0.65, nominal_speed * 0.70)`
- **Impact:**
  - Sidewalk corridors in `small_city_dynamic.world` are typically 2.5m wide.
  - Curbs, lamp posts, and building walls were constantly detected within $2.2 - 2.8\text{m}$.
  - The robot was permanently trapped in `CAUTION_PROXIMITY` state, capping linear velocity to $0.35 - 0.65\text{ m/s}$, creating an excessively slow transit experience.
