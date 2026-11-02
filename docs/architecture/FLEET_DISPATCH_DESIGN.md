# NexusDelivery — Fleet Dispatch & Multi-Robot Assignment Architecture

**Document Version:** 2.0.0  
**Date:** November 2026  
**Status:** Approved Dispatch Specification  
**Scope:** Order Management, Fleet Allocation, Kinematic Routing & State Lifecycle

---

## 1. Fleet Composition & Truth in Modeling

To maintain rigorous engineering honesty, the system defines two tiers of fleet entities:
1. **Active Simulation AMR (`NEXUS-01` / `rdsim`):**
   - **Status:** Fully spawned and simulated in Gazebo Classic 11 with complete ROS 2 autonomy graph, camera perception, Pure Pursuit driver, and physics interaction.
   - **Source of Truth:** `/odom`, `/camera/depth/image_raw`, `/mission/state`, `/safety/state`.
2. **Fleet Expansion Units (`NEXUS-02`, `NEXUS-03`):**
   - **Status:** Fleet architecture models designed for multi-agent expansion and load-balancing demonstrations.
   - **Clear Disclosure:** Explicitly labeled on dashboards as *Fleet Standby / Model Expansion* until multi-robot Gazebo world spawning is enabled. Zero fake telemetry is synthesized.

---

## 2. Order Lifecycle State Machine

An order traverses a strict, unidirectional state machine with automated fallback transitions:

```
[Customer Checkout]
        |
        v
    (QUEUED) -------------------------> (REJECTED) [Out of bounds / Inside building]
        |
        v [Destination Validated]
   (VALIDATING)
        |
        v [Robot Eligible & Route Verified]
    (ASSIGNED)
        |
        v [Robot Acknowledges Mission]
    (ACCEPTED)
        |
        v [Depot Package Loading Complete (2.0s dwell)]
    (EN_ROUTE)
        |
        v [Arrived at Curbside Bay (Distance < 1.2m)]
    (ARRIVED)
        |
        v [HMAC-SHA256 OTP Generated]
(HANDOVER_PENDING) -------------------> (BLOCKED / TIMEOUT) [3 incorrect attempts]
        |
        v [Correct OTP Entered -> Hatch Opens (60 deg)]
   (DELIVERED)
        |
        v [Package Retrieved & Hatch Closed]
   (RETURNING)
        |
        v [Docked at Depot (-31.5, -0.75m)]
   (COMPLETED)
```

---

## 3. Cost-Based Multi-Robot Fleet Assignment Algorithm

When an order arrives, the dispatch engine evaluates candidate robots using a multi-criteria cost function:

$$C_i = w_d \cdot D_{\text{route}}(R_i, P_{\text{pickup}}, P_{\text{drop}}) + w_t \cdot T_{\text{wait}} + w_b \cdot (100 - \text{SOC}_i) + P_{\text{penalty}}$$

### Assignment Criteria:
1. **True Route Distance ($D_{\text{route}}$):** Evaluated strictly via topological A* path search in `route_planner.py`. Straight-line Euclidean distance is never used.
2. **Battery Reserve Verification:**
   - Energy consumption rate: $\approx 1.8\text{ Wh/km}$ during nominal sidewalk cruising ($0.85\text{ m/s}$).
   - Safe return threshold: The robot must possess sufficient SOC to complete the outbound journey, potential detour, and full return to the Central Logistics Depot:
     $$\text{SOC}_{\text{required}} = \frac{(D_{\text{out}} + D_{\text{return}}) \times 1.8\text{ Wh/km}}{512\text{ Wh}} \times 1.30\text{ (safety margin)} \times 100\%$$
   - If $\text{SOC}_{\text{current}} < \text{SOC}_{\text{required}} + 15\%$, the candidate robot is rejected.
3. **Payload Capacity:** Maximum payload $15.0\text{ kg}$; volume limit $0.035\text{ m}^3$ ($35\text{ Liters}$).
4. **Safety Interlock:** Robots with an active latched safety fault (`SAFETY_FAULT_EMERGENCY_STOP`, `SAFETY_FAULT_OBSTACLE_STALL`) are excluded from assignment until cleared by an authorized operator.

---

## 4. Idempotency & Concurrency Safety

To prevent duplicate dispatches and race conditions:
1. **Client Idempotency Key:** Every checkout request generates a UUIDv4 idempotency key. Resubmissions within 60 seconds return the cached order record without dispatching duplicate ROS 2 target messages.
2. **Transactional State Locks:** The dispatch assignment engine executes inside an atomic database transaction. Order states are locked during assignment to prevent two parallel background threads from claiming the same idle robot.
