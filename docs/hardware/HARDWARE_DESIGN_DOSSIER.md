# NexusDelivery Autonomous AMR — Hardware Engineering Design Dossier

> **CRITICAL DISCLAIMER / AVERTISSEMENT OBLIGATOIRE**  
> **Concept de conception : non fabriqué, non validé.**  
> Ce dossier constitue un dossier d'études et de modélisation théorique préliminaire. Aucune carte électronique ni châssis n'a été fabriqué ou qualifié sous charge réelle.

---

## 1. System Architecture Overview

The NexusDelivery AMR is engineered as a two-wheel differential drive sidewalk autonomous mobile robot platform with passive caster balance:
* **Footprint**: 600 mm (Length) x 380 mm (Width) x 280 mm (Height).
* **Chassis Material**: 4.0 mm Aluminum 5052-H32 laser-cut flat-pack plates.
* **Payload Capacity**: 15.0 kg nominal cargo envelope (18.5 L volume).
* **Kinematics**: Differential drive via two 8" brushless geared hub motors (250W each, integrated 14-bit Hall encoders) + two 75mm rear swivel casters.
* **Target Maximum Speed**: 1.50 m/s (5.4 km/h) with 45 mm sidewalk ground clearance.

---

## 2. Electrical Architecture & Power Tree

All electrical power distribution parameters are tracked in machine-readable JSON: [`docs/hardware/power_tree.json`](power_tree.json).

```
                      +────────────────────────────────────────+
                      │ 25.6V 20Ah LiFePO4 Battery Pack (8S)   │
                      │ 512 Wh | Daly Smart BMS (40A Cont)    │
                      +───────────────────┬────────────────────+
                                          │
                                          ▼
                      +────────────────────────────────────────+
                      │  50A Slow-Blow MIDI Fuse (Littelfuse)  │
                      │  + 10 AWG High-Temp Silicone Busbar    │
                      +───────────────────┬────────────────────+
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
+───────────────────────────────────+           +───────────────────────────────────+
│ Direct Traction Power (10 AWG)    │           │ Logic & Auxiliary Branch (Fused)  │
│ - ODrive S1 FOC Motor Controller  │           │ Fused distribution to step-down   │
│ - 2x 24V 250W BLDC Hub Motors     │           │ synchronous converters            │
│ (31.25A cont / 46.88A peak @ 20V) │           │                                   │
+───────────────────────────────────+           +─────────────────┬─────────────────+
                                                                  │
                                      ┌───────────────────────────┴───────────────────────────┐
                                      ▼                                                       ▼
                    +───────────────────────────────────+                   +───────────────────────────────────+
                    │ Synchronous Buck (24V -> 5.1V 5A) │                   │ Synchronous Buck (24V -> 12.0V 3A)│
                    │ Efficiency: 90% | XL4015-MOD      │                   │ Efficiency: 92% | XL4016-MOD      │
                    +-----------------┬-----------------+                   +-----------------┬-----------------+
                                      │                                                       │
                 ┌────────────────────┴────────────────────┐                     ┌────────────┴────────────┐
                 ▼                                         ▼                     ▼                         ▼
  +─────────────────────────────+           +─────────────────────────+ +──────────────────+  +──────────────────+
  │ Raspberry Pi 5 (8GB)        │           │ 3.3V Isolated LDO       │ │ 2x Cargo Hatch   │  │ 2x Internal 40mm │
  │ + Hailo-8L M.2 AI HAT+ (13T)│           │ (AMS1117-3.3)           │ │ Solenoids (12V)  │  │ IP54 Fans (0.2A) │
  │ + RealSense D435i (USB3)    │           │ -> ISO1050 Isolated CAN │ │ (2.4A pulse 1.5s)│  +──────────────────+
  │ (4.2A cont / 5.0A peak)     │           │ (2500 Vrms isolation)   │ +──────────────────+
  +─────────────────────────────+           +─────────────────────────+
```

### Safety & Grounding Rules:
1. **Separation of High-Current Motor Lines**: Traction currents (up to 50 A peak) never flow through PCB copper tracks. They are routed directly via 10 AWG multistrand silicone cables and XT90 anti-spark connectors.
2. **Emergency Stop Concept**: Positive-opening mushroom switch acting on a dual contactor. *To be formally validated according to ISO 13849 by a certified safety engineer.*
3. **Galvanic Isolation**: CAN 2.0B bus linking the Raspberry Pi and ODrive S1 is galvanically isolated using a TI ISO1050 transceiver with 2500 Vrms dielectric rating, eliminating ground loops.

---

## 3. Carrier Board Concept & Verification Reports

The carrier board coordinates power conversion, isolated communications, and safety interlocks:
* **CAD Source Files**: [`docs/hardware/carrier_board/nexus_carrier_board.kicad_sch`](carrier_board/nexus_carrier_board.kicad_sch) and [`nexus_carrier_board.kicad_pcb`](carrier_board/nexus_carrier_board.kicad_pcb).
* **Dimensions**: 120.0 mm x 85.0 mm (4-layer stackup: Signal / Solid DGND / Power Planes / PGND).

### Raw Electrical Rules Check (ERC) Report:
Source: [`docs/hardware/carrier_board/erc_report.rpt`](carrier_board/erc_report.rpt)
```text
ERC Summary:
  Total Warnings: 2 (Intentional architectural isolated nets: 5V1_LOGIC local driving net and ISO1050 isolated external VCC2)
  Total Errors:   0
ERC Status: PASSED WITH INTENTIONAL ARCHITECTURAL WARNINGS (CONCEPT BASELINE)
```

### Raw Design Rules Check (DRC) Report:
Source: [`docs/hardware/carrier_board/drc_report.rpt`](carrier_board/drc_report.rpt)
```text
Design Rules Settings:
  - Minimum Track Width: 0.25 mm (Signal) / 1.50 mm (Power)
  - Minimum Track Clearance: 0.20 mm
  - Minimum Via Diameter: 0.60 mm (0.30 mm drill)
DRC Summary:
  Errors: 0 | Warnings: 0 | Unconnected Pads: 0
DRC Status: PASSED (CONCEPT BASELINE, UNFABRICATED)
```

---

## 4. Mechanical Design & Parametric 3D CAD

All 3D geometry is generated parametrically from [`tools/generate_parametric_cad.py`](../../tools/generate_parametric_cad.py) and matches the 2D DXF laser-cut blueprint [`docs/cad/delivery_robot_chassis_2d_print.dxf`](../cad/delivery_robot_chassis_2d_print.dxf):

### Available 3D CAD Exports:
1. **Chassis Baseplate STL**: [`docs/hardware/cad/nexus_chassis_baseplate.stl`](cad/nexus_chassis_baseplate.stl) (600x380 mm base with 120 mm side skirts).
2. **Cargo Lid STL**: [`docs/hardware/cad/nexus_cargo_lid_60deg.stl`](cad/nexus_cargo_lid_60deg.stl) (Angled 60-degree motorized hatch cover).
3. **Brain Carrier Plate STL**: [`docs/hardware/cad/nexus_brain_carrier_plate.stl`](cad/nexus_brain_carrier_plate.stl) (Internal electronics tray).
4. **Exploded Assembly STL**: [`docs/hardware/cad/nexus_exploded_assembly.stl`](cad/nexus_exploded_assembly.stl) (Full multi-layer stackup).
5. **STEP Master Assembly**: [`docs/hardware/cad/nexus_chassis_assembly.step`](cad/nexus_chassis_assembly.step) (Standard ISO 10303-21 CAD exchange format).

### Ingress Protection (IP54 Target):
* **Perimeter Sealing**: Closed-cell EPDM foam gasket (6.0 mm width x 3.0 mm thickness) along the perimeter of the top cover.
* **Cable Pass-Through**: All external wiring (charging port, emergency stop) passes through IP68 nylon cable glands (M16 / M20).
* **Atmospheric Equalization**: Hydrophobic Gore-Tex membrane vent (M12 threaded plug) prevents pressure buildup while barring water droplets and dust.

---

## 5. Unified Bill of Materials (BOM)

Single source of truth: [`docs/hardware/BOM_HARDWARE_UNIFIED.csv`](BOM_HARDWARE_UNIFIED.csv).

| Category | Component | Part Number | Qty | Unit (USD) | Extended (USD) | Status |
|:---|:---|:---|:---:|:---:|:---:|:---|
| **Compute Core** | Raspberry Pi 5 (8GB) | SC1112 | 1 | $80.00 | $80.00 | DATASHEET |
| **Edge AI NPU** | Hailo-8L M.2 AI Module | HM21LB1C2AE | 1 | $75.00 | $75.00 | DATASHEET |
| **M.2 Interface HAT** | Raspberry Pi M.2 HAT+ | SC1115 | 1 | $12.00 | $12.00 | DATASHEET |
| **Depth Sensor** | Intel RealSense D435i | 999AFR | 1 | $349.00 | $349.00 | DATASHEET |
| **Motor Driver** | ODrive S1 FOC Controller | ODrive-S1-40A | 1 | $169.00 | $169.00 | DATASHEET |
| **Traction Hubs** | 8" Brushless Geared Hubs | BLDC-24V-250W-HUB | 2 | $95.00 | $190.00 | ESTIMATION |
| **Main Battery** | 24V 20Ah LiFePO4 (8S) | 8S-LFP-20AH | 1 | $195.00 | $195.00 | ESTIMATION |
| **Power Buck 5V** | 24V to 5.1V 5A Synchronous | XL4015-MOD | 1 | $8.50 | $8.50 | ESTIMATION |
| **Power Buck 12V**| 24V to 12.0V 3A Synchronous | XL4016-MOD | 1 | $7.00 | $7.00 | ESTIMATION |
| **Cargo Solenoids**| 12V Deadbolt Solenoids | DC-12V-10MM-LATCH | 2 | $14.00 | $28.00 | ESTIMATION |
| **Lock Relay** | 5V Optocoupler Relay | RELAY-5V-1CH | 1 | $3.50 | $3.50 | ESTIMATION |
| **Safety Interlock**| 22mm Mushroom E-Stop | LAY37-11ZS | 1 | $9.00 | $9.00 | ESTIMATION |
| **Status Lighting** | WS2812B NeoPixel Ring | WS2812B-16R | 1 | $6.50 | $6.50 | ESTIMATION |
| **Caster Wheels** | 75mm Polyurethane Casters | CASTER-75MM-PU | 2 | $11.00 | $22.00 | ESTIMATION |
| **Chassis Shell** | Aluminum 5052-H32 Laser Cut | CR-NEXUS-FRAME-V2 | 1 | $75.00 | $75.00 | ESTIMATION |
| **Carrier PCB** | 4-Layer Carrier + 10 AWG Harness | CR-NEXUS-PDB-V1 | 1 | $45.00 | $45.00 | ESTIMATION |
| **Total Pièces Brutes** | **NexusDelivery AMR (16 postes)** | **FULL-PARTS-V2** | - | - | **$1,274.50 USD** | **CALCULÉ** |
| *Fret & Douane TN* | Transport (15kg) + Douane/TVA (~30%) | LOGISTICS-TN | - | - | *$580.00 USD* | ESTIMATION - A VERIFIER |
| **Total Rendu Tunisie**| **NexusDelivery Landed Cost** | **TOTAL-LANDED-TN** | - | - | **$1,854.50 USD** | **ESTIMATION - A VERIFIER** |
