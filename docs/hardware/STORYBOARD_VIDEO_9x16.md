# Storyboard — NexusDelivery Autonomous AMR Vertical Showcase Video (9:16)

> **Format**: Vertical Video (1080 x 1920 px, 9:16 Aspect Ratio)  
> **Target Duration**: 60.0 seconds (1,800 frames @ 30 FPS)  
> **Audio**: Silent (MP4 video stream only)  
> **Mandatory Watermarks**:
> - `Concept de conception, pas un prototype` (displayed during CAD / hardware sequence)
> - `Simulation Gazebo Classic` (displayed during dynamic mission replay sequence)

---

## Cinematic Progression & Scene Timeline

### Act 1: Hook & Platform Identity (00:00 – 00:08 | Frames 0 – 240)
* **Visual**: Sleek dark slate gradient background (#0d1117). Orthographic projection of the assembled NexusDelivery sidewalk robot rotating slowly along the yaw axis.
* **Top Overlay**: `NEXUSDELIVERY AUTONOMOUS AMR` | `Hardware Engineering Dossier`.
* **Lower Watermark**: `Concept de conception, pas un prototype`.
* **Key Callouts**:
  - `Dimensions: 600 x 380 mm`
  - `Dual 250W Geared Hubs`
  - `Zero-LiDAR Vision Architecture`
* **PARTS $ Counter**: Initialized at `$0.00 USD`.

### Act 2: Cinematic Exploded View — Body & Brain (00:08 – 00:24 | Frames 241 – 720)
* **Visual**: Robot smoothly separates vertically along the Z-axis into three distinct mechanical layers:
  1. **Top Layer**: 60-degree motorized cargo hatch with cellular EPDM perimeter gasket.
  2. **Middle Layer ("Brain Plate")**: Elevated component tray housing Raspberry Pi 5, Hailo-8L M.2 NPU, isolated carrier PCB, and Intel RealSense D435i camera.
  3. **Bottom Layer ("Body Plate")**: 4.0mm Aluminum 5052-H32 baseplate, 24V 20Ah LiFePO4 battery pack, ODrive S1 FOC controller, and dual 8" hub drive motors.
* **Label**: `Exploded View: Brain Plate & Body Plate Separation`.

### Act 3: Synchronized Component Highlight & BOM Counter (00:24 – 00:44 | Frames 721 – 1320)
* **Dynamic Counter Behavior**: Reads line items directly from `delivery_robot_sim/web_dashboard/downloads/BOM.csv`. With each component illuminated, a technical card appears and the counter increments:
  1. `Raspberry Pi 5 (8GB)` -> `Quad Cortex-A76 @ 2.4GHz` -> **+$80.00** ($80.00)
  2. `Hailo-8L M.2 AI HAT+` -> `13 INT8 TOPS @ 2.5W` -> **+$75.00** ($155.00)
  3. `M.2 Interface HAT+` -> `PCIe Gen 3.0 Adapter` -> **+$12.00** ($167.00)
  4. `Intel RealSense D435i` -> `Active IR Stereo Depth` -> **+$349.00** ($516.00)
  5. `ODrive S1 Controller` -> `Dual FOC 24V-56V CAN` -> **+$169.00** ($685.00)
  6. `2x 250W Hub Motors` -> `14-bit Hall Feedback` -> **+$190.00** ($875.00)
  7. `24V 20Ah LiFePO4` -> `512Wh Daly Smart BMS` -> **+$195.00** ($1,070.00)
  8. `Dual Synchronous Bucks` -> `5.1V 5A + 12V 3A Rails` -> **+$15.50** ($1,085.50)
  9. `2x Cargo Solenoids` -> `12V 10mm Spring Latches` -> **+$28.00** ($1,113.50)
  10. `E-Stop & Status Ring` -> `Safety Interlock + LEDs` -> **+$15.50** ($1,129.00)
  11. `2x Heavy-Duty Casters` -> `75mm Polyurethane Swivel` -> **+$22.00** ($1,151.00)
  12. `Aluminum 5052 Shell` -> `4.0mm Laser Flat-Pack` -> **+$75.00** ($1,226.00)
  13. `Carrier PCB & Harness` -> `4-Layer PDB + 10 AWG` -> **+$45.00** -> **$1,274.50 USD**!
* **Counter Arrival**: Settles firmly on `$1,274.50 USD`.

### Act 4: Electrical Power Tree & Simulation Baseline (00:44 – 00:52 | Frames 1321 – 1560)
* **Visual**: Transition to power routing overlay:
  - `Main Bus: 25.6V LiFePO4 (33A cont / 50A peak)`
  - `High Current: 10 AWG Silicone (Bypasses PCB)`
  - `Communications: Galvanically Isolated CAN 2.0B`
  - `Safety: 50A MIDI Slow-Blow Fuse + E-Stop Concept`
* **Watermark**: `Simulation Gazebo Classic — TRL 3`.

### Act 5: Summary & Call to Action (00:52 – 01:00 | Frames 1561 – 1800)
* **Summary Scorecard**:
  - `Total Pièces Brutes: $1,274.50 USD` (Calculé depuis BOM CSV)
  - `Coût Rendu Tunisie: $1,854.50 USD` (Estimation indicative fret & douane)
  - `Maturité: TRL 3 (Simulation-First Proof of Concept)`
  - `Unit Tests: 79/79 Passing (100%)`
* **Call to Action**:
  - `Explore Full Open-Source Engineering Dossier:`
  - `github.com/Chiheb-bt/NexusDelivery-Autonomous-AMR`
  - `Branch: feat/hardware-design`
