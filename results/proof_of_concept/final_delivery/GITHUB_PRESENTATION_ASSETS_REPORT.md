# GITHUB PRESENTATION ASSETS & AUTHENTICITY AUDIT REPORT
## NEXUSDELIVERY: Project Presentation Assets Verification
**Author:** Chiheb-bt  
**Organization:** Chiheb Robotics Systems Lab  
**Date:** November 5, 2026  

---

## 1. Inventory of Active Presentation Assets

All assets are located in the repository root directory `assets/` and are strictly derived from genuine simulation sessions and the authentic web platform:

### A. Robot Mechanical Structure (`assets/robot/`)
* **`nexus_delivery_robot.png`** (235 KB): Front view rendering of the genuine differential-drive chassis (`rdsim.urdf.xacro`), featuring the aluminum monocoque frame, front RGB-D sensor fascia, cyan LED accents, active drive wheels ($R=0.20\text{ m}$), and cargo compartment.

### B. Gazebo Simulation World (`assets/simulation/`)
* **`gazebo_world_perspective.png`** (2.9 MB): Perspective view from Gazebo Classic 11 showing the genuine robot on the street with pedestrian actors and intersection infrastructure.
* **`gazebo_city_street.png`** (1.9 MB): Full-screen capture of the urban environment (`small_city_dynamic.world`) showing road markings, stop sign, and commercial buildings.
* **`gazebo_robot_top_chassis.png`** (1.8 MB): Angled aerial perspective showing the robot bounding collision box and physical chassis.
* **`gazebo_robot_follow_drive.png`** (1.8 MB): Live follow-camera tracking the robot along the delivery route.
* **`gazebo_rqt_camera_view.png`** (1.7 MB): Direct live output from `/camera/image_raw` displayed in `rqt_image_view`.
* **`gazebo_world_top_view.png`** (258 KB): Ground-truth trajectory plot from `/odom_gt` mapping the 112.21 m delivery mission with zero collisions.

### C. Web Customer & Fleet Operations Platform (`assets/website/`)
* **`customer_portal_landing.png`** (1.8 MB): High-resolution capture of the landing page showing verified TRL 3–4 specifications and power tree.
* **`customer_portal_preview.png`** (1.8 MB): Customer interactive sidewalk pin-drop map showing coordinate placement.
* **`customer_order_menu.png`** (1.9 MB): Real e-commerce ordering catalog.
* **`customer_cart_dispatch.png`** (1.9 MB): Delivery dispatch interface with carbon offset estimation and live address routing.
* **`customer_live_tracking_hud.png`** (1.8 MB): Real-time customer transit tracker featuring the live Gazebo camera stream with obstacle distance bounding box.
* **`customer_doorstep_otp_modal.png`** (1.8 MB): Interactive doorstep handover modal demonstrating successful OTP code validation (`482910`) and motorized hatch opening to 60.1°.
* **`fleet_supervisor_cockpit.png`** (1.9 MB): Comprehensive fleet operations center showing the tactical simulation world map, YOLOv8 perception monitor, and battery telemetry.

---

## 2. Legacy & AI-Generated Asset Removal Log

In accordance with strict academic and engineering authenticity standards, all legacy mockups and AI-generated concepts have been completely removed from active repository folders:
* 🗑️ `docs/assets/gazebo_depot_packaging.jpg` (Uber Eats AI robot mockup) → Archived to `archive_legacy_ai/`
* 🗑️ `docs/assets/gazebo_sidewalk_tracking.jpg` (Legacy concept image) → Archived to `archive_legacy_ai/`
* 🗑️ `docs/assets/gazebo_new_location.jpg` (Legacy mockup) → Archived to `archive_legacy_ai/`
* 🗑️ `docs/assets/poc_1_customer_portal.png` (Deprecated design) → Archived to `archive_legacy_ai/`
* 🗑️ `docs/assets/nexus_poc_showcase_banner.png` (Legacy banner) → Archived to `archive_legacy_ai/`
* 🗑️ `assets/poc_showcase_banner.png` → Deleted.

Every image referenced in the updated `README.md` is 100% genuine and traceable to the real code and simulation.
