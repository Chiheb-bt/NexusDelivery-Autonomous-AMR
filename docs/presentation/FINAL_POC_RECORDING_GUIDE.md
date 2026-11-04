# NEXORA Final Proof-of-Concept Video Recording Guide

## 1. Objective
This guide provides instructions for the user (Chiheb) to record a high-impact, professional demonstration video of the NEXORA autonomous delivery robot Proof of Concept.

---

## 2. Screen Setup & Recommended Layout
- **Resolution:** 1920x1080 (Full HD)
- **Split Screen Layout:**
  - **Left Half (50%):** Gazebo Classic 3D Window (`small_city_dynamic.world`). Keep camera in bird's-eye chase mode or free orbit around the robot.
  - **Right Half (50%):** Web Browser open to `http://localhost:8080/client` (Light Mode).
- **Tools:** OBS Studio, SimpleScreenRecorder, or GNOME built-in screen recorder (`Ctrl + Alt + Shift + R`).

---

## 3. Step-by-Step Recording Sequence (Total Time: ~2.5 - 3 minutes)

### Scene 1: Introduction & Catalog Exploration (00:00 - 00:30)
1. Show the customer portal at `http://localhost:8080/client`.
2. Scroll through the **Curated Curbside Catalog** showing the real food photos (Pizza, Sushi, Salad, Cold Brew).
3. Click on **Explore Map** to show the interactive Gazebo city vector map.
4. Drag and drop the delivery pin onto `Sophie Laurent Doorstep (North Avenue Curbside Bay 1)`.

### Scene 2: Order Creation & Autonomous Dispatch (00:30 - 01:15)
1. Add **Artisan Margherita Pizza** to the cart ($14.50).
2. Open the slide-out cart and click **Confirm Autonomous Delivery**.
3. Point out the live transition:
   - Order ID `ORD-XXX` created.
   - OTP code issued (e.g. `661923`).
   - In Gazebo (left window), the 2-wheel robot departs the Central Logistics Depot (`-31.5, -0.75`).
4. Watch the robot accelerate smoothly up to $1.15\text{ m/s}$ along Central Boulevard.

### Scene 3: Sidewalk Navigation & Traffic Management (01:15 - 01:50)
1. Highlight that navigation uses **Camera-Only Vision + Wheel Odometry** (Zero LiDAR, Zero GPS).
2. Show the robot approaching the traffic intersection. If the light is RED, it stops smoothly at the stop line, waiting for GREEN before turning onto North Avenue.
3. Show the live camera feed in the web dashboard HUD matching what Gazebo renders in real-time.

### Scene 4: Doorstep Arrival & Curbside OTP Handover (01:50 - 02:25)
1. The robot arrives at the delivery bay (`-14.23, 14.66`) and stops.
2. In the web portal, status becomes `Arrived at Doorstep (OTP Unlock)`.
3. Click **Verify Delivery Code** to open the modal keypad.
4. Click **Autofill Code** (or type the 6 digits).
5. Watch Gazebo: the motorized cargo hatch unlatches and physically swings up to **60.1°** (`cargo_hatch_joint`).
6. The modal displays: `PACKAGE COMPARTMENT UNLOCKED`.

### Scene 5: Explicit Receipt Confirmation & Return to Depot (02:25 - 03:00)
1. Click the green button: `[ 📦 I HAVE RECEIVED MY PACKAGE ]`.
2. Notice the sequence:
   - UI shows `CLOSING CARGO COMPARTMENT...`.
   - In Gazebo, the hatch swings shut to $0.0^\circ$.
   - Sensor feedback confirms closure via `/joint_states`.
   - UI updates to `ROBOT RETURNING TO DEPOT`.
3. The robot executes an autonomous U-turn and navigates back to the depot facility.
4. The robot enters the depot portal (`-27.5, -0.75`) and stops cleanly at the dock (`-31.33, -0.78`).
5. Mission completed!
