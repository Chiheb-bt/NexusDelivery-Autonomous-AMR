#!/usr/bin/env python3
"""
Chiheb Robotics — NexusDelivery Autonomous Sidewalk Platform
2D Mechanical CAD Blueprint & Hardware Simulation Assets Generator

Outputs:
1. delivery_robot_chassis_2d_print.dxf (AutoCAD DXF R12 standard 1:1 scale in mm for laser/waterjet cutting)
2. delivery_robot_chassis_blueprint.svg (1:1 scale ISO technical blueprint with dimension lines & drill charts)
3. delivery_robot_wokwi_project.json (Wokwi physical hardware simulation specification)
4. docs/HARDWARE_ASSEMBLY_GUIDE.md (Comprehensive Wiki-style hardware assembly manual & Bill of Materials)
"""

import os
import math
import json

def generate_dxf():
    """Generates standard DXF R12 (AC1009) ASCII file in millimeters."""
    lines = []
    
    # Header Section
    lines.extend([
        "0", "SECTION",
        "2", "HEADER",
        "9", "$ACADVER",
        "1", "AC1009",
        "9", "$INSUNITS",
        "70", "4",  # 4 = Millimeters
        "0", "ENDSEC"
    ])
    
    # Tables Section (Layers)
    lines.extend([
        "0", "SECTION",
        "2", "TABLES",
        "0", "TABLE",
        "2", "LAYER",
        "70", "6",
        # Layer CUT_OUTLINE (Color 1: Red for Laser Cut Outer Contour)
        "0", "LAYER",
        "2", "CUT_OUTLINE",
        "70", "0",
        "62", "1",
        "6", "CONTINUOUS",
        # Layer CUT_INTERNAL (Color 3: Green for Internal Slots / Cutouts)
        "0", "LAYER",
        "2", "CUT_INTERNAL",
        "70", "0",
        "62", "3",
        "6", "CONTINUOUS",
        # Layer DRILL_HOLES (Color 4: Cyan for Drill Holes M2.5/M3/M4)
        "0", "LAYER",
        "2", "DRILL_HOLES",
        "70", "0",
        "62", "4",
        "6", "CONTINUOUS",
        # Layer ENGRAVE_TEXT (Color 2: Yellow for Label Engraving / Dimensions)
        "0", "LAYER",
        "2", "ENGRAVE_TEXT",
        "70", "0",
        "62", "2",
        "6", "CONTINUOUS",
        "0", "ENDTAB",
        "0", "ENDSEC"
    ])
    
    # Entities Section
    lines.extend([
        "0", "SECTION",
        "2", "ENTITIES"
    ])
    
    def add_line(layer, x1, y1, x2, y2):
        lines.extend([
            "0", "LINE",
            "8", layer,
            "10", f"{x1:.3f}",
            "20", f"{y1:.3f}",
            "30", "0.0",
            "11", f"{x2:.3f}",
            "21", f"{y2:.3f}",
            "31", "0.0"
        ])
        
    def add_circle(layer, cx, cy, radius):
        lines.extend([
            "0", "CIRCLE",
            "8", layer,
            "10", f"{cx:.3f}",
            "20", f"{cy:.3f}",
            "30", "0.0",
            "40", f"{radius:.3f}"
        ])
        
    def add_arc(layer, cx, cy, radius, start_angle, end_angle):
        lines.extend([
            "0", "ARC",
            "8", layer,
            "10", f"{cx:.3f}",
            "20", f"{cy:.3f}",
            "30", "0.0",
            "40", f"{radius:.3f}",
            "50", f"{start_angle:.1f}",
            "51", f"{end_angle:.1f}"
        ])
        
    def add_text(layer, text, x, y, height=5.0):
        lines.extend([
            "0", "TEXT",
            "8", layer,
            "10", f"{x:.3f}",
            "20", f"{y:.3f}",
            "30", "0.0",
            "40", f"{height:.2f}",
            "1", text
        ])

    # 1. Main Baseplate Outer Contour (600mm x 380mm with R=30mm fillet corners)
    # Bounds: X from -300 to +300, Y from -190 to +190
    R = 30.0
    x_min, x_max = -300.0, 300.0
    y_min, y_max = -190.0, 190.0
    
    # 4 Straight edges
    add_line("CUT_OUTLINE", x_min + R, y_max, x_max - R, y_max)
    add_line("CUT_OUTLINE", x_max, y_max - R, x_max, y_min + R)
    add_line("CUT_OUTLINE", x_max - R, y_min, x_min + R, y_min)
    add_line("CUT_OUTLINE", x_min, y_min + R, x_min, y_max - R)
    
    # 4 Corner Arcs
    add_arc("CUT_OUTLINE", x_max - R, y_max - R, R, 0.0, 90.0)
    add_arc("CUT_OUTLINE", x_min + R, y_max - R, R, 90.0, 180.0)
    add_arc("CUT_OUTLINE", x_min + R, y_min + R, R, 180.0, 270.0)
    add_arc("CUT_OUTLINE", x_max - R, y_min + R, R, 270.0, 360.0)

    # 2. Drive Wheel Axle Slots / Wheel Wells (Left & Right)
    # Left wheel well (Y = +135 to +185, X = -60 to +60)
    add_line("CUT_INTERNAL", -60.0, 135.0, 60.0, 135.0)
    add_line("CUT_INTERNAL", 60.0, 135.0, 60.0, 185.0)
    add_line("CUT_INTERNAL", 60.0, 185.0, -60.0, 185.0)
    add_line("CUT_INTERNAL", -60.0, 185.0, -60.0, 135.0)
    
    # Right wheel well (Y = -185 to -135, X = -60 to +60)
    add_line("CUT_INTERNAL", -60.0, -185.0, 60.0, -185.0)
    add_line("CUT_INTERNAL", 60.0, -185.0, 60.0, -135.0)
    add_line("CUT_INTERNAL", 60.0, -135.0, -60.0, -135.0)
    add_line("CUT_INTERNAL", -60.0, -135.0, -60.0, -185.0)

    # 3. Precision Drill Holes
    # Raspberry Pi 5 + Hailo-8L HAT (4x M2.5, dia 2.7mm, spacing 58.0mm x 49.0mm, centered at X=+80, Y=+65)
    rpi_cx, rpi_cy = 80.0, 65.0
    for dx in [-29.0, 29.0]:
        for dy in [-24.5, 24.5]:
            add_circle("DRILL_HOLES", rpi_cx + dx, rpi_cy + dy, 1.35)
    add_text("ENGRAVE_TEXT", "RASPBERRY PI 5 + HAILO-8L M.2 HAT (4x M2.5)", rpi_cx - 45.0, rpi_cy - 35.0, 3.5)

    # ODrive S1 Dual BLDC Controller (4x M3, dia 3.2mm, spacing 50.0mm x 40.0mm, centered at X=-80, Y=+65)
    odrv_cx, odrv_cy = -80.0, 65.0
    for dx in [-25.0, 25.0]:
        for dy in [-20.0, 20.0]:
            add_circle("DRILL_HOLES", odrv_cx + dx, odrv_cy + dy, 1.60)
    add_text("ENGRAVE_TEXT", "ODRIVE S1 DUAL BLDC (4x M3)", odrv_cx - 35.0, odrv_cy - 30.0, 3.5)

    # Intel RealSense D435i Front Bracket (2x M3, dia 3.2mm, spacing 45.0mm, at X=+285, Y=0)
    add_circle("DRILL_HOLES", 285.0, -22.5, 1.60)
    add_circle("DRILL_HOLES", 285.0, 22.5, 1.60)
    add_text("ENGRAVE_TEXT", "REALSENSE D435i FRONT MOUNT (2x M3)", 245.0, -32.0, 3.5)

    # Front Caster Mount (4x M4, dia 4.2mm, spacing 35mm x 35mm, centered at X=+220, Y=0)
    fc_cx, fc_cy = 220.0, 0.0
    for dx in [-17.5, 17.5]:
        for dy in [-17.5, 17.5]:
            add_circle("DRILL_HOLES", fc_cx + dx, fc_cy + dy, 2.10)
    add_text("ENGRAVE_TEXT", "FRONT CASTER 4x M4", fc_cx - 20.0, fc_cy + 25.0, 3.5)

    # Rear Caster Mount (4x M4, dia 4.2mm, spacing 35mm x 35mm, centered at X=-220, Y=0)
    rc_cx, rc_cy = -220.0, 0.0
    for dx in [-17.5, 17.5]:
        for dy in [-17.5, 17.5]:
            add_circle("DRILL_HOLES", rc_cx + dx, rc_cy + dy, 2.10)
    add_text("ENGRAVE_TEXT", "REAR CASTER 4x M4", rc_cx - 20.0, rc_cy + 25.0, 3.5)

    # 24V LiFePO4 Battery Tray (Centered at X=0, Y=-70, 180mm x 110mm)
    # 4 Corner Mounting Holes (4x M4, dia 4.2mm)
    for dx in [-90.0, 90.0]:
        for dy in [-55.0, 55.0]:
            add_circle("DRILL_HOLES", 0.0 + dx, -70.0 + dy, 2.10)
    # 4 Strap Slots (30mm x 5mm) for velcro containment straps
    for sx in [-50.0, 50.0]:
        for sy in [-115.0, -25.0]:
            add_line("CUT_INTERNAL", sx - 15.0, sy - 2.5, sx + 15.0, sy - 2.5)
            add_line("CUT_INTERNAL", sx + 15.0, sy - 2.5, sx + 15.0, sy + 2.5)
            add_line("CUT_INTERNAL", sx + 15.0, sy + 2.5, sx - 15.0, sy + 2.5)
            add_line("CUT_INTERNAL", sx - 15.0, sy + 2.5, sx - 15.0, sy - 2.5)
    add_text("ENGRAVE_TEXT", "24V 20Ah LiFePO4 BATTERY TRAY (512Wh)", -45.0, -73.0, 4.0)

    # Solenoid Latch Mount (2x M3, dia 3.2mm, spacing 30.0mm at X=+150, Y=0)
    add_circle("DRILL_HOLES", 150.0, -15.0, 1.60)
    add_circle("DRILL_HOLES", 150.0, 15.0, 1.60)
    add_text("ENGRAVE_TEXT", "SOLENOID LATCH 2x M3", 125.0, -25.0, 3.5)

    # 4x Cable Pass-Through Grommets (dia 25mm, radius 12.5mm)
    grommets = [(-160.0, -70.0), (-160.0, 70.0), (160.0, -70.0), (160.0, 70.0)]
    for gx, gy in grommets:
        add_circle("CUT_INTERNAL", gx, gy, 12.5)
        add_text("ENGRAVE_TEXT", "CABLE D25", gx - 12.0, gy - 2.0, 3.0)

    # Engraved Title Block & Specifications
    add_text("ENGRAVE_TEXT", "CHIHEB ROBOTICS — NEXUS-DELIVERY PLATFORM", -280.0, 170.0, 5.0)
    add_text("ENGRAVE_TEXT", "CHASSIS BASEPLATE (1:1 SCALE mm) — MATL: AL 5052-H32 4.0mm", -280.0, 160.0, 3.8)
    add_text("ENGRAVE_TEXT", "ALL TOLERANCES +/- 0.20mm — ZERO-LiDAR PURE VISION CARRIER", -280.0, 151.0, 3.2)

    lines.extend([
        "0", "ENDSEC",
        "0", "EOF"
    ])
    
    return "\n".join(lines)


def generate_svg_blueprint():
    """Generates standard technical 2D vector blueprint in SVG with mm units and ISO title block."""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="-350 -240 700 480" width="700mm" height="480mm" style="background:#0b0f19; font-family:'Inter', system-ui, sans-serif;">
  <defs>
    <!-- Grid Pattern (10mm minor, 50mm major) -->
    <pattern id="grid10" width="10" height="10" patternUnits="userSpaceOnUse">
      <path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="0.3"/>
    </pattern>
    <pattern id="grid50" width="50" height="50" patternUnits="userSpaceOnUse">
      <rect width="50" height="50" fill="url(#grid10)" />
      <path d="M 50 0 L 0 0 0 50" fill="none" stroke="rgba(56,189,248,0.12)" stroke-width="0.6"/>
    </pattern>
    <!-- Arrow Markers -->
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#38bdf8"/>
    </marker>
    <marker id="arrow-amber" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#fbbf24"/>
    </marker>
  </defs>

  <!-- Background Grid -->
  <rect x="-350" y="-240" width="700" height="480" fill="url(#grid50)"/>

  <!-- Center Coordinate Crosshairs -->
  <line x1="-330" y1="0" x2="330" y2="0" stroke="rgba(56,189,248,0.25)" stroke-width="0.8" stroke-dasharray="8,4,2,4"/>
  <line x1="0" y1="-220" x2="0" y2="220" stroke="rgba(56,189,248,0.25)" stroke-width="0.8" stroke-dasharray="8,4,2,4"/>
  <text x="5" y="-5" fill="rgba(56,189,248,0.5)" font-size="6" font-family="'JetBrains Mono', monospace">(0, 0) WHEELBASE ORIGIN</text>

  <!-- ============================================================== -->
  <!-- 1. MAIN CHASSIS BASEPLATE CONTOUR (600mm x 380mm, R=30mm)      -->
  <!-- ============================================================== -->
  <!-- Outer Cut Contour in High-Vis Red/Orange Glow -->
  <rect x="-300" y="-190" width="600" height="380" rx="30" ry="30"
        fill="rgba(15,23,42,0.85)" stroke="#ef4444" stroke-width="1.8" filter="drop-shadow(0 0 4px rgba(239,68,68,0.5))"/>

  <!-- ============================================================== -->
  <!-- 2. WHEEL WELL SLOTS (LEFT & RIGHT)                             -->
  <!-- ============================================================== -->
  <!-- Left Wheel Well (Y = +135 to +185, X = -60 to +60) -->
  <rect x="-60" y="135" width="120" height="50" rx="4"
        fill="rgba(16,185,129,0.12)" stroke="#10b981" stroke-width="1.2" stroke-dasharray="2,2"/>
  <text x="-48" y="162" fill="#10b981" font-size="6" font-weight="600">LEFT WHEEL WELL (120x50mm)</text>
  <circle cx="0" cy="160" r="1.5" fill="#10b981"/>

  <!-- Right Wheel Well (Y = -185 to -135, X = -60 to +60) -->
  <rect x="-60" y="-185" width="120" height="50" rx="4"
        fill="rgba(16,185,129,0.12)" stroke="#10b981" stroke-width="1.2" stroke-dasharray="2,2"/>
  <text x="-52" y="-158" fill="#10b981" font-size="6" font-weight="600">RIGHT WHEEL WELL (120x50mm)</text>
  <circle cx="0" cy="-160" r="1.5" fill="#10b981"/>

  <!-- ============================================================== -->
  <!-- 3. ELECTRONICS COMPONENT FOOTPRINTS & DRILL HOLES              -->
  <!-- ============================================================== -->
  
  <!-- RASPBERRY PI 5 + HAILO-8L M.2 HAT -->
  <g id="rpi5_footprint">
    <rect x="43.5" y="34.5" width="85" height="56" rx="4" fill="rgba(56,189,248,0.08)" stroke="#38bdf8" stroke-width="1.0"/>
    <text x="47" y="47" fill="#38bdf8" font-size="6" font-weight="700">RASPBERRY PI 5 (8GB)</text>
    <text x="47" y="55" fill="#94a3b8" font-size="5">+ Hailo-8L M.2 HAT (13 TOPS)</text>
    <!-- 4x M2.5 Holes (Spacing 58x49) -->
    <circle cx="51.0" cy="40.5" r="1.35" fill="#38bdf8" stroke="#ffffff" stroke-width="0.5"/>
    <circle cx="109.0" cy="40.5" r="1.35" fill="#38bdf8" stroke="#ffffff" stroke-width="0.5"/>
    <circle cx="51.0" cy="89.5" r="1.35" fill="#38bdf8" stroke="#ffffff" stroke-width="0.5"/>
    <circle cx="109.0" cy="89.5" r="1.35" fill="#38bdf8" stroke="#ffffff" stroke-width="0.5"/>
    <text x="50" y="80" fill="#38bdf8" font-size="4.5">4x M2.5 (dia 2.7mm)</text>
  </g>

  <!-- ODRIVE S1 DUAL BLDC MOTOR CONTROLLER -->
  <g id="odrive_footprint">
    <rect x="-115" y="38" width="70" height="54" rx="4" fill="rgba(168,85,247,0.08)" stroke="#a855f7" stroke-width="1.0"/>
    <text x="-110" y="52" fill="#c084fc" font-size="6" font-weight="700">ODRIVE S1 DUAL FOC</text>
    <text x="-110" y="60" fill="#94a3b8" font-size="5">24V-56V / 40A CAN Bus</text>
    <!-- 4x M3 Holes (Spacing 50x40) -->
    <circle cx="-105.0" cy="45.0" r="1.6" fill="#a855f7" stroke="#ffffff" stroke-width="0.5"/>
    <circle cx="-55.0" cy="45.0" r="1.6" fill="#a855f7" stroke="#ffffff" stroke-width="0.5"/>
    <circle cx="-105.0" cy="85.0" r="1.6" fill="#a855f7" stroke="#ffffff" stroke-width="0.5"/>
    <circle cx="-55.0" cy="85.0" r="1.6" fill="#a855f7" stroke="#ffffff" stroke-width="0.5"/>
    <text x="-105" y="78" fill="#a855f7" font-size="4.5">4x M3 (dia 3.2mm)</text>
  </g>

  <!-- INTEL REALSENSE D435i CAMERA FRONT MOUNT -->
  <g id="realsense_mount">
    <rect x="270" y="-30" width="25" height="60" rx="3" fill="rgba(244,63,94,0.12)" stroke="#f43f5e" stroke-width="1.0"/>
    <text x="272" y="-12" fill="#f43f5e" font-size="5" font-weight="700">REALSENSE</text>
    <text x="272" y="-5" fill="#f43f5e" font-size="4.5">D435i Depth</text>
    <circle cx="285.0" cy="-22.5" r="1.6" fill="#f43f5e" stroke="#fff" stroke-width="0.5"/>
    <circle cx="285.0" cy="22.5" r="1.6" fill="#f43f5e" stroke="#fff" stroke-width="0.5"/>
    <text x="272" y="15" fill="#f43f5e" font-size="4">2x M3 (45mm)</text>
  </g>

  <!-- 24V 20Ah LiFePO4 BATTERY TRAY -->
  <g id="battery_tray">
    <rect x="-95" y="-130" width="190" height="120" rx="4" fill="rgba(234,179,8,0.08)" stroke="#eab308" stroke-width="1.2"/>
    <text x="-80" y="-115" fill="#fbbf24" font-size="7" font-weight="700">24V 20Ah LiFePO4 BATTERY PACK (512 Wh)</text>
    <text x="-80" y="-105" fill="#94a3b8" font-size="5.5">Daly Smart BMS w/ Active Balancing + I2C/CAN Telemetry</text>
    <!-- 4x M4 Mounting Holes -->
    <circle cx="-90" cy="-125" r="2.1" fill="#eab308" stroke="#fff" stroke-width="0.5"/>
    <circle cx="90" cy="-125" r="2.1" fill="#eab308" stroke="#fff" stroke-width="0.5"/>
    <circle cx="-90" cy="-15" r="2.1" fill="#eab308" stroke="#fff" stroke-width="0.5"/>
    <circle cx="90" cy="-15" r="2.1" fill="#eab308" stroke="#fff" stroke-width="0.5"/>
    <!-- 4 Strap Cutout Slots -->
    <rect x="-65" y="-127.5" width="30" height="5" rx="2" fill="#1e293b" stroke="#eab308" stroke-width="0.8"/>
    <rect x="35" y="-127.5" width="30" height="5" rx="2" fill="#1e293b" stroke="#eab308" stroke-width="0.8"/>
    <rect x="-65" y="-17.5" width="30" height="5" rx="2" fill="#1e293b" stroke="#eab308" stroke-width="0.8"/>
    <rect x="35" y="-17.5" width="30" height="5" rx="2" fill="#1e293b" stroke="#eab308" stroke-width="0.8"/>
    <text x="-40" y="-70" fill="#fbbf24" font-size="5">VELCRO STRAP MOUNTING SLOTS (4x)</text>
  </g>

  <!-- FRONT CASTER WHEEL MOUNT (X = +220) -->
  <g id="front_caster">
    <rect x="200" y="-20" width="40" height="40" rx="3" fill="rgba(148,163,184,0.1)" stroke="#94a3b8" stroke-width="0.8" stroke-dasharray="3,2"/>
    <circle cx="202.5" cy="-17.5" r="2.1" fill="#94a3b8" stroke="#fff" stroke-width="0.5"/>
    <circle cx="237.5" cy="-17.5" r="2.1" fill="#94a3b8" stroke="#fff" stroke-width="0.5"/>
    <circle cx="202.5" cy="17.5" r="2.1" fill="#94a3b8" stroke="#fff" stroke-width="0.5"/>
    <circle cx="237.5" cy="17.5" r="2.1" fill="#94a3b8" stroke="#fff" stroke-width="0.5"/>
    <text x="204" y="3" fill="#cbd5e1" font-size="4.5" font-weight="600">FRONT CASTER</text>
    <text x="206" y="10" fill="#94a3b8" font-size="4">4x M4 (35x35)</text>
  </g>

  <!-- REAR CASTER WHEEL MOUNT (X = -220) -->
  <g id="rear_caster">
    <rect x="-240" y="-20" width="40" height="40" rx="3" fill="rgba(148,163,184,0.1)" stroke="#94a3b8" stroke-width="0.8" stroke-dasharray="3,2"/>
    <circle cx="-237.5" cy="-17.5" r="2.1" fill="#94a3b8" stroke="#fff" stroke-width="0.5"/>
    <circle cx="-202.5" cy="-17.5" r="2.1" fill="#94a3b8" stroke="#fff" stroke-width="0.5"/>
    <circle cx="-237.5" cy="17.5" r="2.1" fill="#94a3b8" stroke="#fff" stroke-width="0.5"/>
    <circle cx="-202.5" cy="17.5" r="2.1" fill="#94a3b8" stroke="#fff" stroke-width="0.5"/>
    <text x="-236" y="3" fill="#cbd5e1" font-size="4.5" font-weight="600">REAR CASTER</text>
    <text x="-234" y="10" fill="#94a3b8" font-size="4">4x M4 (35x35)</text>
  </g>

  <!-- DELIVERY HATCH SOLENOID LOCK (X = +150) -->
  <g id="solenoid_lock">
    <circle cx="150" cy="-15" r="1.6" fill="#ec4899" stroke="#fff" stroke-width="0.5"/>
    <circle cx="150" cy="15" r="1.6" fill="#ec4899" stroke="#fff" stroke-width="0.5"/>
    <rect x="140" y="-20" width="20" height="40" rx="2" fill="rgba(236,72,153,0.1)" stroke="#ec4899" stroke-width="0.8"/>
    <text x="135" y="-24" fill="#ec4899" font-size="5" font-weight="600">SOLENOID LOCK 12V</text>
  </g>

  <!-- 4x CABLE GROMMETS (dia 25mm) -->
  <circle cx="-160" cy="-70" r="12.5" fill="rgba(14,165,233,0.12)" stroke="#0ea5e9" stroke-width="1.0"/>
  <text x="-173" y="-68" fill="#38bdf8" font-size="4.5">CABLE D25</text>

  <circle cx="-160" cy="70" r="12.5" fill="rgba(14,165,233,0.12)" stroke="#0ea5e9" stroke-width="1.0"/>
  <text x="-173" y="72" fill="#38bdf8" font-size="4.5">CABLE D25</text>

  <circle cx="160" cy="-70" r="12.5" fill="rgba(14,165,233,0.12)" stroke="#0ea5e9" stroke-width="1.0"/>
  <text x="147" y="-68" fill="#38bdf8" font-size="4.5">CABLE D25</text>

  <circle cx="160" cy="70" r="12.5" fill="rgba(14,165,233,0.12)" stroke="#0ea5e9" stroke-width="1.0"/>
  <text x="147" y="72" fill="#38bdf8" font-size="4.5">CABLE D25</text>

  <!-- ============================================================== -->
  <!-- 4. ENGINEERING DIMENSION LINES (ISO 128 / ASME Y14.5M)         -->
  <!-- ============================================================== -->
  <!-- Length Dimension: 600.00 mm (Bottom) -->
  <line x1="-300" y1="208" x2="300" y2="208" stroke="#38bdf8" stroke-width="1.0" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
  <line x1="-300" y1="192" x2="-300" y2="216" stroke="rgba(56,189,248,0.5)" stroke-width="0.6"/>
  <line x1="300" y1="192" x2="300" y2="216" stroke="rgba(56,189,248,0.5)" stroke-width="0.6"/>
  <rect x="-40" y="202" width="80" height="12" fill="#0b0f19"/>
  <text x="0" y="211" fill="#38bdf8" font-size="8" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono', monospace">600.0 mm</text>

  <!-- Width Dimension: 380.00 mm (Right) -->
  <line x1="316" y1="-190" x2="316" y2="190" stroke="#38bdf8" stroke-width="1.0" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
  <line x1="302" y1="-190" x2="324" y2="-190" stroke="rgba(56,189,248,0.5)" stroke-width="0.6"/>
  <line x1="302" y1="190" x2="324" y2="190" stroke="rgba(56,189,248,0.5)" stroke-width="0.6"/>
  <rect x="310" y="-10" width="12" height="20" fill="#0b0f19" transform="rotate(-90 316 0)"/>
  <text x="316" y="3" fill="#38bdf8" font-size="8" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono', monospace" transform="rotate(-90 316 0)">380.0 mm</text>

  <!-- Wheelbase & Caster Spacing: 440.00 mm -->
  <line x1="-220" y1="-202" x2="220" y2="-202" stroke="#fbbf24" stroke-width="0.8" marker-start="url(#arrow-amber)" marker-end="url(#arrow-amber)"/>
  <line x1="-220" y1="-192" x2="-220" y2="-208" stroke="rgba(251,191,36,0.5)" stroke-width="0.6"/>
  <line x1="220" y1="-192" x2="220" y2="-208" stroke="rgba(251,191,36,0.5)" stroke-width="0.6"/>
  <rect x="-60" y="-208" width="120" height="12" fill="#0b0f19"/>
  <text x="0" y="-199" fill="#fbbf24" font-size="7" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono', monospace">CASTER DISTANCE: 440.0 mm</text>

  <!-- Corner Radius Callout (R30) -->
  <line x1="-279" y1="-169" x2="-250" y2="-140" stroke="#ef4444" stroke-width="0.8"/>
  <text x="-248" y="-136" fill="#ef4444" font-size="6" font-weight="700">R 30.0 mm (4x)</text>

  <!-- ============================================================== -->
  <!-- 5. OFFICIAL ENGINEERING TITLE BLOCK                            -->
  <!-- ============================================================== -->
  <g id="title_block" transform="translate(-290, -180)">
    <rect width="210" height="60" rx="3" fill="rgba(15,23,42,0.92)" stroke="rgba(56,189,248,0.4)" stroke-width="1.0"/>
    <text x="10" y="16" fill="#38bdf8" font-size="8" font-weight="800">CHIHEB ROBOTICS — NEXUS-DELIVERY</text>
    <text x="10" y="27" fill="#f8fafc" font-size="6.5" font-weight="600">CHASSIS STRUCTURAL BASEPLATE (REV 2.4)</text>
    <line x1="10" y1="31" x2="200" y2="31" stroke="rgba(56,189,248,0.2)" stroke-width="0.6"/>
    <text x="10" y="40" fill="#94a3b8" font-size="5">MATERIAL: 4.0mm Aluminum 5052-H32 / Laser Cut</text>
    <text x="10" y="48" fill="#94a3b8" font-size="5">SCALE: 1:1 (True Millimeter Units) | TOLERANCE: +/-0.20mm</text>
    <text x="10" y="55" fill="#10b981" font-size="5" font-weight="600">READY FOR CNC LASER / WATERJET / 3D PRINT</text>
  </g>

  <!-- Drill Chart Table (Top Right) -->
  <g id="drill_chart" transform="translate(140, -180)">
    <rect width="150" height="56" rx="3" fill="rgba(15,23,42,0.92)" stroke="rgba(56,189,248,0.4)" stroke-width="1.0"/>
    <text x="8" y="14" fill="#38bdf8" font-size="6.5" font-weight="700">DRILL SCHEDULE</text>
    <line x1="8" y1="18" x2="142" y2="18" stroke="rgba(56,189,248,0.2)" stroke-width="0.6"/>
    <text x="8" y="27" fill="#38bdf8" font-size="5">• 4x M2.5 (dia 2.7mm) — Raspberry Pi 5</text>
    <text x="8" y="35" fill="#a855f7" font-size="5">• 4x M3 (dia 3.2mm) — ODrive S1 Controller</text>
    <text x="8" y="43" fill="#f43f5e" font-size="5">• 4x M3 (dia 3.2mm) — RealSense &amp; Solenoid</text>
    <text x="8" y="51" fill="#eab308" font-size="5">• 12x M4 (dia 4.2mm) — Casters &amp; Battery Tray</text>
  </g>
</svg>
"""
    return svg


def generate_wokwi_project():
    """Generates Wokwi physical hardware simulation specification json."""
    wokwi_data = {
        "version": 1,
        "author": "Chiheb Robotics — NexusDelivery Team",
        "name": "NexusDelivery Physical Hardware Workbench & Assembly",
        "description": "Virtual physical hardware wiring simulation of the autonomous sidewalk delivery robot (Zero-LiDAR architecture).",
        "editor": "wokwi",
        "parts": [
            {
                "type": "board-pi-5",
                "id": "rpi5",
                "top": 120,
                "left": 350,
                "attrs": {
                    "model": "Raspberry Pi 5 Model B 8GB",
                    "os": "Ubuntu 22.04 LTS (ROS 2 Humble)",
                    "cpu": "Quad-core ARM Cortex-A76 @ 2.4GHz",
                    "ram": "8GB LPDDR4X"
                }
            },
            {
                "type": "module-hailo8l-hat",
                "id": "npu_hailo",
                "top": 120,
                "left": 550,
                "attrs": {
                    "interface": "PCIe Gen 3.0 x1 Lane",
                    "compute": "13 TOPS INT8 Neural Processing Unit",
                    "model_pipeline": "YOLOv8s Pedestrian & Obstacle Detection (138 FPS, 7.2ms latency)"
                }
            },
            {
                "type": "sensor-realsense-d435i",
                "id": "rgbd_cam",
                "top": -80,
                "left": 350,
                "attrs": {
                    "interface": "USB 3.0 SuperSpeed (5 Gbps)",
                    "depth_technology": "Active IR Stereo + RGB 1080p",
                    "imu": "Bosch BMI055 6-DoF IMU",
                    "range": "0.2m to 5.0m sidewalk clearance"
                }
            },
            {
                "type": "controller-odrive-s1",
                "id": "odrive_motor_controller",
                "top": 350,
                "left": 350,
                "attrs": {
                    "bus_voltage": "24V DC",
                    "rated_current": "40A continuous",
                    "control_mode": "Dual FOC (Field Oriented Control)",
                    "interface": "CAN Bus 2.0B @ 1 Mbps (or UART0)"
                }
            },
            {
                "type": "motor-bldc-planetary",
                "id": "left_drive_motor",
                "top": 450,
                "left": 150,
                "attrs": {
                    "power": "250W 24V BLDC",
                    "reduction": "15:1 Planetary Gearbox",
                    "encoder": "14-bit Absolute Magnetic (SPI/ABI)"
                }
            },
            {
                "type": "motor-bldc-planetary",
                "id": "right_drive_motor",
                "top": 450,
                "left": 580,
                "attrs": {
                    "power": "250W 24V BLDC",
                    "reduction": "15:1 Planetary Gearbox",
                    "encoder": "14-bit Absolute Magnetic (SPI/ABI)"
                }
            },
            {
                "type": "battery-lifepo4-8s",
                "id": "main_battery",
                "top": 350,
                "left": 50,
                "attrs": {
                    "chemistry": "LiFePO4 (Lithium Iron Phosphate)",
                    "cells": "8S1P (3.2V x 8 = 25.6V nominal)",
                    "capacity": "20Ah (512 Wh)",
                    "bms": "Daly Smart BMS w/ Active Balancing & I2C/CAN bus"
                }
            },
            {
                "type": "regulator-buck-sync",
                "id": "dcdc_5v_5a",
                "top": 240,
                "left": 180,
                "attrs": {
                    "input": "24V DC",
                    "output": "5.1V DC @ 5A (25.5W)",
                    "efficiency": "94.5%"
                }
            },
            {
                "type": "regulator-buck-sync",
                "id": "dcdc_12v_3a",
                "top": 240,
                "left": 80,
                "attrs": {
                    "input": "24V DC",
                    "output": "12.0V DC @ 3A (36W)"
                }
            },
            {
                "type": "actuator-solenoid-latch",
                "id": "cargo_latch",
                "top": 120,
                "left": 120,
                "attrs": {
                    "voltage": "12V DC",
                    "stroke": "10mm spring-return deadbolt",
                    "relay": "Optocoupler isolated relay with 1N4007 flyback diode"
                }
            },
            {
                "type": "switch-estop-kill",
                "id": "emergency_stop",
                "top": 350,
                "left": 230,
                "attrs": {
                    "type": "Push-to-lock, twist-to-release safety kill switch",
                    "interlock": "Cuts ODrive VBUS + GPIO23 hardware interrupt"
                }
            },
            {
                "type": "led-ring-ws2812b",
                "id": "halo_rgb_ring",
                "top": -80,
                "left": 550,
                "attrs": {
                    "pixels": 16,
                    "interface": "Single-wire NZR (GPIO18/24)",
                    "states": "Emerald=Nominal, Cyan=Customer Unlock, Amber=Caution, Red=E-Stop"
                }
            }
        ],
        "connections": [
            ["main_battery:V+", "emergency_stop:IN", "red", ["v30", "h100"]],
            ["emergency_stop:OUT", "odrive_motor_controller:VBUS", "red", ["h60"]],
            ["emergency_stop:OUT", "dcdc_5v_5a:VIN", "red", ["v-40"]],
            ["emergency_stop:OUT", "dcdc_12v_3a:VIN", "red", ["v-40"]],
            ["main_battery:GND", "odrive_motor_controller:GND", "black", ["v40", "h200"]],
            ["main_battery:GND", "dcdc_5v_5a:GND", "black", ["v-20"]],
            ["main_battery:GND", "rpi5:GND", "black", ["v-100"]],
            
            ["dcdc_5v_5a:VOUT", "rpi5:5V_IN", "orange", ["v-60", "h100"]],
            ["dcdc_12v_3a:VOUT", "cargo_latch:V+", "orange", ["v-60"]],
            
            ["rpi5:PCIE_FPC", "npu_hailo:PCIE_M2", "cyan", ["h40"]],
            ["rpi5:USB3_0", "rgbd_cam:TYPE_C", "blue", ["v-120"]],
            
            ["rpi5:GPIO18", "cargo_latch:RELAY_SIG", "green", ["h-120"]],
            ["rpi5:GPIO23", "emergency_stop:SENSE", "purple", ["v120"]],
            ["rpi5:GPIO24", "halo_rgb_ring:DIN", "yellow", ["v-100"]],
            
            ["rpi5:CAN_H", "odrive_motor_controller:CAN_H", "blue", ["v120"]],
            ["rpi5:CAN_L", "odrive_motor_controller:CAN_L", "magenta", ["v120"]],
            ["main_battery:I2C_SDA", "rpi5:GPIO2_SDA", "white", ["v-140", "h200"]],
            ["main_battery:I2C_SCL", "rpi5:GPIO3_SCL", "white", ["v-140", "h200"]],
            
            ["odrive_motor_controller:M0_UVW", "left_drive_motor:UVW", "orange", ["v40", "h-120"]],
            ["odrive_motor_controller:M1_UVW", "right_drive_motor:UVW", "orange", ["v40", "h140"]],
            ["left_drive_motor:ENCODER", "odrive_motor_controller:ENC0", "gray", ["h100"]],
            ["right_drive_motor:ENCODER", "odrive_motor_controller:ENC1", "gray", ["h-100"]]
        ]
    }
    return json.dumps(wokwi_data, indent=2)


def generate_hardware_markdown_guide():
    """Generates comprehensive Wiki documentation for hardware assembly."""
    doc = """# NexusDelivery: Complete Physical Hardware Architecture & Assembly Manual
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
4. Deburr all edges and insert rubber cable grommets into the four $\varnothing 25\text{mm}$ holes.

### Step 2: Drivetrain & Casters
1. Mount the two 75mm polyurethane swivel casters to the front ($X = +220\text{mm}$) and rear ($X = -220\text{mm}$) using M4 x 16mm button-head screws and nylon lock nuts.
2. Mount the two 24V 250W planetary gear motors into the chassis side bracket dropouts at $X = 0\text{mm}$.
3. Secure the two 200mm polyurethane-tread drive wheels to the motor keyed output shafts with M6 axle clamping bolts (Torque: 14 N·m).

### Step 3: Power Distribution & Battery Enclosure
1. Place the 24V 20Ah LiFePO4 battery pack inside the centered battery containment tray ($X = 0, Y = -70\text{mm}$).
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
1. Fasten the Intel RealSense D435i camera to the front bumper bracket at $X = +285\text{mm}$ using two M3 x 8mm machine screws.
2. Route the USB 3.0 Type-C high-flex shielded cable through the front grommet into one of the blue USB 3.0 ports on the Raspberry Pi 5.

### Step 6: Cargo Compartment & Automated Solenoid Lock
1. Install the 12V spring-return electric latch onto the compartment hatch lip at $X = +150\text{mm}$.
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
"""
    return doc


def main():
    root = "/home/chiheb/Downloads/RDSim-devel-2wheel_diff"
    downloads_dir = os.path.join(root, "delivery_robot_sim/web_dashboard/downloads")
    docs_dir = os.path.join(root, "docs")
    cad_dir = os.path.join(root, "docs/cad")
    
    os.makedirs(downloads_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(cad_dir, exist_ok=True)
    
    # 1. Generate DXF (Laser cut standard)
    dxf_content = generate_dxf()
    dxf_path = os.path.join(downloads_dir, "delivery_robot_chassis_2d_print.dxf")
    with open(dxf_path, "w") as f:
        f.write(dxf_content)
    # Also save to docs/cad
    with open(os.path.join(cad_dir, "delivery_robot_chassis_2d_print.dxf"), "w") as f:
        f.write(dxf_content)
    print(f"Generated DXF: {dxf_path} ({len(dxf_content)} bytes)")
    
    # 2. Generate SVG Blueprint
    svg_content = generate_svg_blueprint()
    svg_path = os.path.join(downloads_dir, "delivery_robot_chassis_blueprint.svg")
    with open(svg_path, "w") as f:
        f.write(svg_content)
    with open(os.path.join(cad_dir, "delivery_robot_chassis_blueprint.svg"), "w") as f:
        f.write(svg_content)
    print(f"Generated SVG: {svg_path} ({len(svg_content)} bytes)")
    
    # 3. Generate Wokwi Project Spec
    wokwi_content = generate_wokwi_project()
    wokwi_path = os.path.join(downloads_dir, "delivery_robot_wokwi_project.json")
    with open(wokwi_path, "w") as f:
        f.write(wokwi_content)
    with open(os.path.join(root, "wokwi.diagram.json"), "w") as f:
        f.write(wokwi_content)
    print(f"Generated Wokwi Spec: {wokwi_path}")
    
    # 4. Generate Hardware Markdown Guide
    guide_content = generate_hardware_markdown_guide()
    guide_path = os.path.join(docs_dir, "HARDWARE_ASSEMBLY_GUIDE.md")
    with open(guide_path, "w") as f:
        f.write(guide_content)
    print(f"Generated Assembly Guide: {guide_path}")

if __name__ == "__main__":
    main()
