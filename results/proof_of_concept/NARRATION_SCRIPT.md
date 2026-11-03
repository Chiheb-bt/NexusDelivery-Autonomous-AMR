# NEXUSDELIVERY — PROOF-OF-CONCEPT NARRATION SCRIPT
## Autonomous Sidewalk Delivery Robotics Platform (TRL 3–4 Baseline)
**Target Audience:** University Evaluator, Robotics Professor, Engineering Review Board  
**Language:** Professional English (Natural, Fluent, Technically Articulate)  
**Total Target Duration:** ~5 Minutes (300 Seconds)  
**Tone:** Confident, objective, engineering-focused, candid about current simulation status and future hardware roadmap.

---

### SCENE 1 — INTRODUCTION & URBAN PROBLEM STATEMENT
**Timing:** `00:00 – 00:30` (30 seconds)  
**Visuals:** Title card, NexusDelivery AMR identity, high-altitude perspective of the simulated urban environment (`small_city_dynamic.world`).

> **Narration:**  
> "Welcome to this technical presentation of NexusDelivery, an autonomous sidewalk mobile robotics platform engineered for last-mile urban logistics.
>
> Last-mile delivery accounts for over fifty percent of total shipping costs in urban environments. Traditional delivery vans cause road congestion, produce significant carbon emissions, and frequently struggle with curbside parking. While aerial drones face strict regulatory airspace restrictions in densely populated areas, ground-based sidewalk autonomous mobile robots offer a practical, zero-emission alternative.
>
> However, navigating pedestrian sidewalks introduces formidable engineering challenges: narrow shared corridors, static infrastructure like street lamps and walls, unpredictable pedestrians, curb boundaries, and the strict requirement for secure parcel handover.
>
> In this project, we have developed a complete end-to-end robotics software stack—spanning perception, navigation, fleet mission dispatching, and secure customer handover—validated inside the Gazebo physics simulation environment."

---

### SCENE 2 — THE SIMULATION ENVIRONMENT & PHYSICAL ROBOT MODEL
**Timing:** `00:30 – 01:05` (35 seconds)  
**Visuals:** Orbit around Gazebo small city; view of central logistics depot, sidewalk network, asphalt roadways, pedestrian crosswalks, traffic lights, and 3D differential-drive robot model (`rdsim`).

> **Narration:**  
> "Here, we observe the physics-based Gazebo Classic simulation environment. The urban world spans one hundred sixty meters by ninety-six meters, featuring indoor logistics facilities, outdoor asphalt streets, paved sidewalks, regulated intersections with traffic signal lights, and static pedestrian obstacles.
>
> The simulated robot is a two-wheel differential drive autonomous mobile robot with passive front and rear caster stabilization. Differential drive was specifically selected for its mechanical simplicity, high reliability, and zero-radius in-place rotation capability—allowing the robot to maneuver smoothly through narrow sidewalk corners where Ackermann-steered vehicles would require complex multi-point turns.
>
> The physical model features accurate mass properties, inertia tensors, wheel traction friction parameters, and a dedicated motorized top cargo hatch actuated by a revolute joint capable of unlatching to sixty degrees."

---

### SCENE 3 — TECHNICAL ARCHITECTURE: VISION-LED AUTONOMY
**Timing:** `01:05 – 01:45` (40 seconds)  
**Visuals:** Architectural block diagram, ROS 2 rqt computation graph, node interaction matrix (CityDriverNode, OrderManagerNode, CargoDeliveryManager, WebBridgeNode).

> **Narration:**  
> "Under the hood, the system is architected entirely around ROS 2 Humble, providing a modular, distributed, and deterministic communication framework.
>
> A foundational design decision of this first-version baseline is camera-led autonomy: the robot relies strictly on simulated RGB-D vision, wheel odometry from wheel encoders, and an inertial measurement unit. We deliberately avoided LiDAR sensors and satellite GPS navigation in this initial phase.
>
> Why? Three reasons: First, high-resolution 3D LiDAR sensors remain cost-prohibitive for mass commercial AMR fleets. Second, dense urban canyons create severe satellite multipath interference and GPS signal shadowing, making raw GPS unreliable near tall multi-story buildings. Third, camera vision captures rich semantic visual information—such as road markings, traffic light states, and obstacle contours—at a fraction of the cost.
>
> The ROS 2 computation graph connects the vision processing pipeline to the city driver node, the cargo actuation controller, and our web bridge node, ensuring complete real-time synchronization between the robot and external web interfaces."

---

### SCENE 4 — CUSTOMER REGISTRATION & VERIFICATION WORKFLOW
**Timing:** `01:45 – 02:15` (30 seconds)  
**Visuals:** Browser screen capture of the newly redesigned Customer Portal (`http://localhost:8080/client`), customer registration form, PBKDF2 credential generation, email verification notification.

> **Narration:**  
> "Now, let us examine the customer-facing delivery workflow.
>
> Unlike simple prototype dashboards that display simulated missions without user authentication, NexusDelivery implements a full commercial customer portal backed by a persistent relational SQLite database.
>
> When a new customer registers, their password is securely hashed using PBKDF2 with HMAC-SHA256 and unique per-user cryptographic salts. The backend generates a cryptographically secure, single-use, twenty-four-hour email verification token.
>
> In development and testing mode without an active SMTP gateway, the platform honestly registers that external email delivery is offline and persists the activation payload into a local verification outbox. Only after verifying the account can the customer dispatch deliveries, preventing unauthorized spam orders."

---

### SCENE 5 — VISUAL DESTINATION SELECTION & MAP VALIDATION
**Timing:** `02:15 – 02:50` (35 seconds)  
**Visuals:** Interactive Gazebo vector map in the browser, customer clicking destinations, rejection of solid building blocks, snapping to designated curbside stopping bays, route computation.

> **Narration:**  
> "Next, the customer selects their delivery location using our interactive vector map.
>
> Rather than relying on arbitrary real-world GPS coordinates that do not match the simulation, the customer map renders the actual topological geometry of the Gazebo city.
>
> When a customer drops a delivery pin, the backend immediately validates the location against the city's topological graph. If a user attempts to select a point inside a solid building mesh or an unreachable zone, the system rejects the destination with a clear explanation.
>
> For valid sidewalk locations, the system snaps the target to the nearest approved curbside delivery bay, computes the optimal collision-free route from the depot, and calculates an accurate estimated distance and time of arrival based on the robot's actual cruise speed."

---

### SCENE 6 — FLEET DISPATCH & SYNCHRONIZED TELEMETRY
**Timing:** `02:50 – 03:25` (35 seconds)  
**Visuals:** Supervisor Cockpit receiving the order, order transition from `PENDING` to `ROBOT_ASSIGNED`, robot leaving the depot dock, side-by-side view of Gazebo movement and live customer radar.

> **Narration:**  
> "Upon customer checkout, the mission dispatcher evaluates payload limits—enforcing a maximum capacity of fifteen kilograms and twenty-two point five liters—and assigns the mission to available AMR units.
>
> Both the customer tracking portal and the supervisor cockpit reflect the identical backend truth. The mission sequence progresses systematically: from `ORDER_PREPARING` to `READY_FOR_DISPATCH`, `ROBOT_ASSIGNED`, and `ROBOT_LEAVING_DEPOT`.
>
> Notice the telemetry provenance indicator on the customer dashboard. We enforce strict data provenance: when simulation data is actively streaming, the UI displays 'LIVE GAZEBO TELEMETRY'. If simulated telemetry drops or becomes stale, the system transparently downgrades to 'LAST KNOWN POSITION' or 'SIMULATION OFFLINE'. Telemetry is never fabricated."

---

### SCENE 7 — AUTONOMOUS SIDEWALK NAVIGATION & OBSTACLE AVOIDANCE
**Timing:** `03:25 – 04:05` (40 seconds)  
**Visuals:** Robot driving along Central Boulevard, encountering static pedestrian / barrier, relative camera perception detection, deceleration and safe lane bypass, arrival at delivery bay.

> **Narration:**  
> "Now, we observe the robot in autonomous transit along the sidewalk corridor.
>
> In earlier simulation runs, navigation bugs caused collisions with the depot wall and failures in pedestrian avoidance. Through rigorous diagnosis, we identified and corrected two critical issues: first, depot door waypoints were incorrectly offset into solid building meshes; second, the vision pipeline had fixed intrinsics that blinded the camera to seventy-five percent of Gazebo's six-hundred-forty by four-hundred-eighty resolution.
>
> With these fixes implemented, the robot now detects forward obstacles in real time using relative depth segmentation. When a pedestrian or barrier obstructs the forward path, the city driver verifies lateral clearance. If a verified corridor exists, the robot safely maneuvers around the obstacle; if no safe passage is available, it smoothly comes to an emergency stop without collision.
>
> Having cleared the obstacle, it reacquires the planned route, slows down as it approaches the delivery goal, and pulls into the curbside bay within a strict tolerance of point-five meters, perfectly aligning its heading."

---

### SCENE 8 — CUSTOMER HANDOVER & SECURE OTP ACTUATION
**Timing:** `04:05 – 04:40` (35 seconds)  
**Visuals:** Robot stationary at delivery bay, state `WAITING_FOR_CUSTOMER`, customer entering 6-digit OTP on website, `cargo_hatch_joint` unlatching in Gazebo to 60°, customer confirming retrieval.

> **Narration:**  
> "Crucially, upon reaching the destination, the robot does not perform an immediate U-turn.
>
> Instead, it enters the `WAITING_FOR_CUSTOMER` state and remains stationary at the curbside bay. The customer portal receives an arrival notification and prompts the customer for their secure six-digit delivery OTP.
>
> When the customer enters the OTP on the web interface, the backend cryptographically validates the code. Only upon successful authentication does the motorized cargo hatch unlatch, rotating sixty degrees in Gazebo via the physical revolute joint controller.
>
> The customer collects the parcel and confirms retrieval on the screen. The cargo hatch then automatically closes and latches shut."

---

### SCENE 9 — RETURN TO DEPOT & MISSION COMPLETION
**Timing:** `04:40 – 05:05` (25 seconds)  
**Visuals:** Robot reversing or turning, navigating back along the sidewalk, entering the depot door at `(-27.5, -0.75)`, docking at `(-31.5, -0.75)`, state transitioning to `MISSION_COMPLETED`.

> **Narration:**  
> "With the cargo compartment securely locked, the system initiates the return journey.
>
> The robot navigates back along the approved street network, enters the depot door portal at coordinates negative twenty-seven point five, negative point seventy-five, and safely docks at the central charging bay.
>
> The mission transitions to `ROBOT_BACK_AT_DEPOT` and finally `MISSION_COMPLETED`. Both the supervisor fleet dashboard and the customer order history update persistently, reflecting the full delivery record and audit log."

---

### SCENE 10 — TECHNICAL CONCLUSION & FUTURE ROADMAP
**Timing:** `05:05 – 05:35` (30 seconds)  
**Visuals:** Summary slide, test pass metrics (132/132 unit & API tests), CAD chassis rendering, hardware transition roadmap.

> **Narration:**  
> "In conclusion, this project establishes a credible, verifiable proof of concept for autonomous sidewalk delivery.
>
> We have diagnosed and repaired critical simulation and navigation failures, replaced artificial demo timers with a true customer-driven twenty-state mission lifecycle, implemented authentic telemetry provenance, and verified the complete workflow across one hundred thirty-two unit, integration, and security tests.
>
> As a matter of scientific integrity, we emphasize that this platform is currently validated at Technology Readiness Level 3 to 4 inside Gazebo physics simulation. Transitioning to physical hardware—including embedded Hailo-8L edge acceleration, physical RealSense depth sensors, and real LiFePO4 battery power management—constitutes our next phase of engineering development.
>
> Thank you for your evaluation."
