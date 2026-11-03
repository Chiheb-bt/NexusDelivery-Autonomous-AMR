# NEXUSDELIVERY — PROOF-OF-CONCEPT VIDEO SCENE BREAKDOWN

**Output File:** `results/proof_of_concept/nexus_delivery_poc.mp4`  
**Teaser File:** `results/proof_of_concept/nexus_delivery_teaser.mp4`  
**Resolution:** 1920 × 1080 (Full HD, 16:9)  
**Frame Rate:** 30.0 FPS  
**Total Target Duration:** 300 Seconds (5 Minutes 00 Seconds)  

---

## Complete 10-Scene Shot List

| Scene # | Scene Title | Timecode | Key Visual Assets | On-Screen Graphic Overlays | Technical Focus |
|:---:|---|:---:|---|---|---|
| **1** | **Introduction & Urban Problem Statement** | `00:00 – 00:30` | `nexus_amr_hero.jpg`, `nexus_poc_showcase_banner.png` | `NexusDelivery™ Autonomous Mobile Robot`<br>`TRL 3–4 Simulation Baseline`<br>`Zero LiDAR • Zero GPS` | Urban last-mile delivery economics, sidewalk AMRs vs delivery vans & aerial drones. |
| **2** | **Gazebo Physics Simulation Environment** | `00:30 – 01:05` | `gazebo_sidewalk_tracking.jpg`, `gazebo_depot_packaging.jpg` | `World: small_city_dynamic.world (160m × 96m)`<br>`2-Wheel Differential Drive Platform`<br>`Passive Caster Balancing` | Physics simulation, friction modeling, zero-turn radius maneuverability, motorized cargo hatch. |
| **3** | **Technical Architecture: Vision-Led Autonomy** | `01:05 – 01:45` | `rqt_web_side_by_side.jpg`, `poc_4_cad_blueprint.png` | `ROS 2 Humble Node Network`<br>`Relative RGB-D Depth Segmentation`<br>`Deterministic State Machine` | Why camera-only was selected over LiDAR/GPS: cost, multi-path GNSS denial, semantic perception. |
| **4** | **Customer Registration & Verification** | `01:45 – 02:15` | `poc_1_customer_portal.png`, Registration UI | `PBKDF2 Password Hashing (HMAC-SHA256)`<br>`Single-Use 24h Verification Token`<br>`Email Outbox (Dev Mode Honest Reporting)` | Honest account verification, CSRF tokens, anti-spam ordering barriers. |
| **5** | **Interactive Destination Map & Validation** | `02:15 – 02:50` | `poc_1_customer_portal.png`, Vector Map Canvas | `Gazebo small_city Vector Map Engine`<br>`Building No-Go Zones: REJECTED`<br>`Curbside Stopping Bay Snapping` | Mathematical reachability checks, collision avoidance against solid structures, ETA estimation. |
| **6** | **Fleet Dispatch & Telemetry Provenance** | `02:50 – 03:25` | `poc_2_fleet_cockpit.png`, Live Tracking View | `Provenance: LIVE GAZEBO TELEMETRY`<br>`Payload Check: 15.0 kg / 22.5 L Max`<br>`Depot Door Exit: (-27.5, -0.75)` | Data provenance truthfulness, supervisor cockpit vs customer portal multi-tenant isolation. |
| **7** | **Autonomous Sidewalk Navigation & Obstacle Avoidance** | `03:25 – 04:05` | `gazebo_sidewalk_tracking.jpg`, `nexus_delivery_poc_trajectory.png` | `Obstacle Detection: Relative Depth Segmentation`<br>`Lateral Corridor Bypass: 0.65m Offset`<br>`Bay Arrival Tolerance: 0.50m Strict` | Diagnosed simulation fixes: depot door coordinate correction, 640x480 resolution adaptation, smooth stopping. |
| **8** | **Doorstep Handover & Secure OTP Actuation** | `04:05 – 04:40` | `poc_5_doorstep_unlocked.png`, OTP Keypad UI | `State: WAITING_FOR_CUSTOMER`<br>`6-Digit OTP Cryptographic Validation`<br>`Hatch Actuation: 60.1° Revolute Joint` | Elimination of auto-dwell U-turn bug; genuine customer-present physical handover. |
| **9** | **Return to Depot & Mission Completion** | `04:40 – 05:05` | `gazebo_depot_packaging.jpg`, `poc_2_fleet_cockpit.png` | `Hatch State: LOCKED (0.0°)`<br>`Depot Dock Target: (-31.5, -0.75)`<br>`Mission State: MISSION_COMPLETED` | Return-to-depot transit, persistent order history update, complete audit logging. |
| **10** | **Technical Conclusion & Hardware Roadmap** | `05:05 – 05:35` | `poc_4_cad_blueprint.png`, `poc_3_hardware_simulator.png` | `132 / 132 Tests Passing (100% Success)`<br>`Next Phase: Physical Hardware Integration`<br>`Hailo-8L NPU & RealSense D435i Roadmap` | Transparent distinction between TRL 3–4 simulation and future physical hardware deployment. |

---

## Visual Branding & Overlay Specifications

- **Primary Canvas Dimensions:** 1920 × 1080 pixels (Full HD)  
- **Color Palette:**
  - Background Fill: Solid Deep Charcoal (`#090d16` / `rgb(9, 13, 22)`)
  - Accent Color: Azure Cyan (`#00e5ff` / `rgb(0, 229, 255)`)
  - Status Emerald: (`#10b981` / `rgb(16, 185, 129)`)
  - Typography Header: White (`#ffffff` / `rgb(255, 255, 255)`)
  - Typography Sub: Slate Silver (`#94a3b8` / `rgb(148, 163, 184)`)
- **Transitions:** 1.0-second smooth linear cross-dissolve between scenes.
- **Lower Thirds:** Clean semi-transparent dark banner (`rgba(15, 23, 42, 0.88)`) with cyan accent line displaying scene title, telemetry badge, and key engineering takeaways.
