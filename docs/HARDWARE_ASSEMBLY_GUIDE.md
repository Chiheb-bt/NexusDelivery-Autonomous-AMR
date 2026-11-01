# NexusDelivery: Complete Physical Hardware Architecture & Assembly Manual
**Chiheb Robotics — Autonomous Sidewalk Delivery Platform**
*Architecture: Zero-LiDAR / Zero-GPS Vision Autonomy (RGB-D + Edge AI + Wheel Odometry + IMU)*

---

## 1. Physical Hardware Bill of Materials (BOM)

| Subsystem | Component | Part Number / Model | Key Specifications | Quantity | Est. Unit Cost ($) |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Compute Core** | Raspberry Pi 5 (8GB) | SC1112 | Quad Cortex-A76 @ 2.4GHz, 8GB LPDDR4X, PCIe 2.0/3.0, 40-pin GPIO | 1 | $80.00 |
| **AI Coprocessor** | Hailo-8L M.2 AI Acceleration Module | HM21LB1C2AE | 13 TOPS INT8 Neural Processor, M.2 2242, 2.5W typical TDP | 1 | $75.00 |
| **M.2 Interface HAT** | Raspberry Pi M.2 HAT+ | SC1115 | Official PCIe to M.2 Key-M adapter board (PCIe Gen 3.0 support) | 1 | $12.00 |
| **Perception Sensor** | Intel RealSense D435i | 999AFR | Active IR Stereo Depth (0.2–5.0m) + 1080p RGB + Bosch BMI055 6-DoF IMU | 1 | $349.00 |
| **Motor Controller** | ODrive S1 Dual BLDC Controller | ODrive-S1-40A | Dual Field-Oriented Control (FOC), 24V–56V, 40A cont., CAN 2.0B / UART | 1 | $169.00 |
| **Traction Drive** | Brushless Planetary Gear Motors | BLDC-24V-250W-PG15 | 24V 250W BLDC, 15:1 planetary reduction, 32 N·m peak, Hall + 14-bit encoder | 2 | $85.00 |
| **Main Battery** | 24V 20Ah LiFePO4 Battery Pack | 8S1P-LFP-20AH | 25.6V nominal, 512 Wh, 2000+ cycle life, built-in Daly Smart BMS (I2C/SMBus) | 1 | $195.00 |
| **Power Converter 1** | Synchronous Buck Converter (5V/5A) | LM2596S-HV / XL4015 | 24V in -> 5.1V 5.0A out (for Raspberry Pi 5 & Hailo-8L) | 1 | $8.50 |
| **Power Converter 2** | Synchronous Buck Converter (12V/3A) | XL4016 DC-DC | 24V in -> 12.0V 3.0A out (for Solenoid Lock & Headlights) | 1 | $7.00 |
| **Hatch Security** | Electronic Deadbolt Solenoid | DC-12V-10MM-LATCH | 12V DC spring-loaded latch, 1.2A pulse, 10mm throw | 1 | $14.00 |
| **Lock Relay** | Optocoupler Relay Module | 1-Channel 5V Relay | 5V trigger from GPIO18, optoisolated, with 1N4007 flyback diode | 1 | $3.50 |
| **Safety Interlock** | Industrial Emergency Stop Button | LAY37-11ZS | Push-to-lock, twist-to-release 22mm panel mount, NC/NO contacts | 1 | $9.00 |
| **Status Lighting** | WS2812B RGB NeoPixel Ring | 16-LED Ring 5050 | 16 addressable RGB LEDs, 5V, single data pin control | 1 | $6.50 |
| **Caster Wheels** | Heavy-Duty Swivel Casters | 75mm Polyurethane | 75mm diameter, 35x35mm 4-hole mounting plate, 60kg load rating each | 2 | $11.00 |
| **Structural Frame** | 2D Laser-Cut Baseplate | CR-NEXUS-BASE-V2 | 4.0mm Aluminum 5052-H32 / 600x380mm (from `delivery_robot_chassis_2d_print.dxf`) | 1 | $45.00 |
| **Hardware Total** | — | — | **Complete Autonomous Delivery Unit** | — | **~$1,065.00** |

---

## 2. Raspberry Pi 5 40-Pin GPIO Wiring Table

| Pin # | Pin Name | Physical Connection / Destination | Signal Type | Logic Level |
| :---: | :--- | :--- | :--- | :---: |
| **Pin 2** | 5V Power In | Output of 24V->5.1V 5A Buck Regulator | DC Power (+) | +5.1V |
| **Pin 4** | 5V Power In | Output of 24V->5.1V 5A Buck Regulator (Parallel) | DC Power (+) | +5.1V |
| **Pin 6** | Ground | Common Ground Bus (BMS, Buck, ODrive) | Power GND | 0V |
| **Pin 3** | GPIO 2 (I2C1 SDA) | Daly Smart BMS I2C Telemetry Data | Bidirectional I2C | 3.3V |
| **Pin 5** | GPIO 3 (I2C1 SCL) | Daly Smart BMS I2C Telemetry Clock | Bidirectional I2C | 3.3V |
| **Pin 8** | GPIO 14 (UART0 TX) | ODrive S1 UART RX (Alternative to CAN) | Serial Asynchronous | 3.3V |
| **Pin 10** | GPIO 15 (UART0 RX) | ODrive S1 UART TX (Alternative to CAN) | Serial Asynchronous | 3.3V |
| **Pin 12** | GPIO 18 (PWM0) | Delivery Compartment Solenoid Relay Signal | Active HIGH Pulse | 3.3V |
| **Pin 16** | GPIO 23 | Emergency Stop Interlock Sense Loop | Input (Pull-Up) | 3.3V |
| **Pin 18** | GPIO 24 | WS2812B NeoPixel Status Halo Ring Data | High-Speed Digital NZR | 3.3V |
| **Pin 24** | GPIO 8 (SPI0 CE0) | MCP2515 CAN Bus Controller (CAN_H / CAN_L) | SPI Bus | 3.3V |
| **Pin 19** | GPIO 10 (SPI0 MOSI)| MCP2515 CAN Bus Controller | SPI Bus | 3.3V |
| **Pin 21** | GPIO 9 (SPI0 MISO) | MCP2515 CAN Bus Controller | SPI Bus | 3.3V |
| **Pin 23** | GPIO 11 (SPI0 SCLK)| MCP2515 CAN Bus Controller | SPI Bus | 3.3V |

---

## 3. Step-by-Step Mechanical & Electrical Assembly

### Step 1: Chassis Baseplate Fabrication (2D Ready-to-Print)
1. Load `delivery_robot_chassis_2d_print.dxf` into your laser cutter, CNC router, or waterjet software (e.g. LightBurn, LaserWeb, Fusion 360).
2. Set Material: **4.0mm Aluminum 5052-H32** (or 6.0mm Acrylic / Polycarbonate for rapid prototyping).
3. Laser parameters:
   - Layer `CUT_OUTLINE` (Red): Outer 600mm x 380mm perimeter (Cut speed 18 mm/s, Power 95%).
   - Layer `CUT_INTERNAL` (Green): Wheel well cutouts & cable pass-through grommets.
   - Layer `DRILL_HOLES` (Cyan): Center drill/cut precision holes (M2.5, M3, M4).
4. Deburr all edges and insert rubber cable grommets into the four $arnothing 25	ext{mm}$ holes.

### Step 2: Drivetrain & Casters
1. Mount the two 75mm polyurethane swivel casters to the front ($X = +220	ext{mm}$) and rear ($X = -220	ext{mm}$) using M4 x 16mm button-head screws and nylon lock nuts.
2. Mount the two 24V 250W planetary gear motors into the chassis side bracket dropouts at $X = 0	ext{mm}$.
3. Secure the two 200mm polyurethane-tread drive wheels to the motor keyed output shafts with M6 axle clamping bolts (Torque: 14 N·m).

### Step 3: Power Distribution & Battery Enclosure
1. Place the 24V 20Ah LiFePO4 battery pack inside the centered battery containment tray ($X = 0, Y = -70	ext{mm}$).
2. Strap the pack firmly with two 25mm heavy-duty velcro cinch straps through the laser-cut slots.
3. Wire the battery positive terminal through the **LAY37-11ZS Emergency Stop Switch** on the top panel before connecting to the main distribution terminal block.
4. Connect the 24V -> 5.1V 5A buck regulator to power the Raspberry Pi 5.
5. Connect the 24V -> 12V 3A buck regulator to power the compartment lock solenoid.

### Step 4: Computing & Neural Processing Unit (NPU)
1. Fasten four M2.5 x 12mm brass standoffs onto the chassis at the Raspberry Pi mounting holes.
2. Plug the **Hailo-8L M.2 AI Module** into the Raspberry Pi M.2 HAT+ Key-M slot and secure with the M2 screw.
3. Connect the 16-pin impedance-controlled FPC ribbon cable between the Raspberry Pi 5 PCIe port and the M.2 HAT+.
4. Secure the assembly onto the standoffs with M2.5 nuts.

### Step 5: Perception Camera Mount
1. Fasten the Intel RealSense D435i camera to the front bumper bracket at $X = +285	ext{mm}$ using two M3 x 8mm machine screws.
2. Route the USB 3.0 Type-C high-flex shielded cable through the front grommet into one of the blue USB 3.0 ports on the Raspberry Pi 5.

### Step 6: Cargo Compartment & Automated Solenoid Lock
1. Install the 12V spring-return electric latch onto the compartment hatch lip at $X = +150	ext{mm}$.
2. Wire the solenoid coil to the optocoupler relay normally-open (NO) contacts with a 1N4007 flyback diode across the terminals (cathode to +12V).
3. Connect relay input pin to **GPIO 18** on the Raspberry Pi.

---

## 4. Software Bringup & Hardware Test Commands

```bash
# 1. Verify PCIe connection to Hailo-8L NPU
lspci -v
# Output should show: 00:00.0 Co-processor: Hailo Technologies Ltd. Hailo-8 AI Processor

# 2. Test Hailo-8L NPU inference benchmark
hailortcli run yolo_v8s.hef --frames 1000
# Expected: >130 FPS, Latency: ~7.2 ms, Temp: <52 deg C

# 3. Test Intel RealSense D435i RGB-D stream
rs-enumerate-devices
# Expected: Intel RealSense D435i, Depth stream 640x480 @ 30 FPS, Color stream 1920x1080 @ 30 FPS

# 4. Trigger Delivery Compartment Solenoid Hatch Unlock
python3 -c "import gpiod; chip = gpiod.Chip('gpiochip4'); line = chip.get_line(18); line.request(consumer='lock', type=gpiod.LINE_REQ_DIR_OUT); line.set_value(1)"
```
