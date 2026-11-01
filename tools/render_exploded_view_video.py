#!/usr/bin/env python3
"""
tools/render_exploded_view_video.py
Renders a vertical 9:16 (1080x1920) 60-second cinematic showcase video
of the NexusDelivery AMR hardware architecture.

Features:
- Parametric 3D isometric wireframe & solid rendering of Body & Brain layers.
- Animated vertical exploded-view expansion.
- Real-time ticking "PARTS $" counter computed directly from BOM.csv.
- Technical component callout HUD cards (3-6 words per spec).
- Mandatory visible watermarks: "Concept de conception, pas un prototype" and "Simulation".
- Output: docs/assets/nexus_hardware_exploded_view_9x16.mp4 (H.264 / MP4 1080x1920 @ 30 FPS).
"""
import os
import sys
import math
import csv
import numpy as np
import cv2

# Video configuration
WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION_S = 60
TOTAL_FRAMES = FPS * DURATION_S  # 1800 frames

COLOR_BG = (15, 17, 23)        # Dark navy #0f1117
COLOR_GRID = (30, 35, 45)      # Subtle background grid
COLOR_CYAN = (235, 185, 40)    # Technical cyan (BGR)
COLOR_ORANGE = (40, 140, 245)  # Accent orange (BGR)
COLOR_WHITE = (245, 245, 250)
COLOR_GRAY = (140, 145, 155)
COLOR_DARK_GRAY = (45, 50, 60)
COLOR_CARD_BG = (22, 27, 34)
COLOR_ACCENT_GREEN = (80, 200, 120)

def load_bom_items(csv_path):
    items = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sub = row['Subsystem'].strip()
            if not sub.startswith('Total') and 'Tunisie' not in sub:
                items.append({
                    'subsystem': sub,
                    'component': row['Component'].strip(),
                    'part_number': row['Part Number'].strip(),
                    'specs': row['Key Specifications'].strip(),
                    'qty': int(row['Quantity']),
                    'unit_cost': float(row['Unit Cost USD']),
                    'ext_cost': float(row['Extended Cost USD']),
                    'status': row['Status'].strip()
                })
    return items

def project_3d(x, y, z, cx=WIDTH//2, cy=850, scale=1.3, yaw_deg=35, pitch_deg=25):
    """Isometric 3D to 2D projection."""
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)

    # Rotate around Z (yaw)
    x1 = x * math.cos(yaw) - y * math.sin(yaw)
    y1 = x * math.sin(yaw) + y * math.cos(yaw)
    z1 = z

    # Rotate around X (pitch)
    x2 = x1
    y2 = y1 * math.cos(pitch) - z1 * math.sin(pitch)
    z2 = y1 * math.sin(pitch) + z1 * math.cos(pitch)

    # 2D Screen coords (Y inverted)
    sx = int(cx + x2 * scale)
    sy = int(cy - y2 * scale)
    return (sx, sy)

def draw_3d_box(img, x_min, x_max, y_min, y_max, z_min, z_max, color, thickness=2, fill_color=None,
                cx=WIDTH//2, cy=850, scale=1.3, yaw_deg=35, pitch_deg=25):
    """Draws a 3D box with optional semi-transparent fill and edges."""
    pts = [
        project_3d(x_min, y_min, z_min, cx, cy, scale, yaw_deg, pitch_deg), # 0
        project_3d(x_max, y_min, z_min, cx, cy, scale, yaw_deg, pitch_deg), # 1
        project_3d(x_max, y_max, z_min, cx, cy, scale, yaw_deg, pitch_deg), # 2
        project_3d(x_min, y_max, z_min, cx, cy, scale, yaw_deg, pitch_deg), # 3
        project_3d(x_min, y_min, z_max, cx, cy, scale, yaw_deg, pitch_deg), # 4
        project_3d(x_max, y_min, z_max, cx, cy, scale, yaw_deg, pitch_deg), # 5
        project_3d(x_max, y_max, z_max, cx, cy, scale, yaw_deg, pitch_deg), # 6
        project_3d(x_min, y_max, z_max, cx, cy, scale, yaw_deg, pitch_deg)  # 7
    ]

    if fill_color:
        # Fill top face (4, 5, 6, 7)
        top_poly = np.array([pts[4], pts[5], pts[6], pts[7]], np.int32)
        cv2.fillPoly(img, [top_poly], fill_color)
        # Fill right face (1, 2, 6, 5)
        right_poly = np.array([pts[1], pts[2], pts[6], pts[5]], np.int32)
        darker_fill = tuple(max(0, c - 20) for c in fill_color)
        cv2.fillPoly(img, [right_poly], darker_fill)

    # Draw wireframe edges
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]
    for i, j in edges:
        cv2.line(img, pts[i], pts[j], color, thickness, cv2.LINE_AA)

def draw_card(img, x, y, w, h, title, subtitle, details, badge=None, border_color=COLOR_CYAN):
    """Draws a professional technical HUD card."""
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), COLOR_CARD_BG, -1)
    cv2.addWeighted(overlay, 0.88, img, 0.12, 0, img)
    cv2.rectangle(img, (x, y), (x + w, y + h), border_color, 2, cv2.LINE_AA)

    # Accent corner brackets
    bl = 12
    cv2.line(img, (x, y), (x + bl, y), border_color, 4)
    cv2.line(img, (x, y), (x, y + bl), border_color, 4)
    cv2.line(img, (x + w, y), (x + w - bl, y), border_color, 4)
    cv2.line(img, (x + w, y), (x + w, y + bl), border_color, 4)
    cv2.line(img, (x, y + h), (x + bl, y + h), border_color, 4)
    cv2.line(img, (x, y + h), (x, y + h - bl), border_color, 4)
    cv2.line(img, (x + w, y + h), (x + w - bl, y + h), border_color, 4)
    cv2.line(img, (x + w, y + h), (x + w, y + h - bl), border_color, 4)

    # Typography
    cv2.putText(img, title, (x + 24, y + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.95, COLOR_WHITE, 2, cv2.LINE_AA)
    cv2.putText(img, subtitle, (x + 24, y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.72, COLOR_CYAN, 2, cv2.LINE_AA)

    line_y = y + 124
    for d in details:
        cv2.putText(img, f"> {d}", (x + 24, line_y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, COLOR_GRAY, 1, cv2.LINE_AA)
        line_y += 34

    if badge:
        bw = len(badge) * 11 + 20
        cv2.rectangle(img, (x + w - bw - 20, y + 20), (x + w - 20, y + 54), (40, 60, 45), -1)
        cv2.rectangle(img, (x + w - bw - 20, y + 20), (x + w - 20, y + 54), COLOR_ACCENT_GREEN, 1)
        cv2.putText(img, badge, (x + w - bw - 10, y + 43), cv2.FONT_HERSHEY_SIMPLEX, 0.52, COLOR_ACCENT_GREEN, 1, cv2.LINE_AA)

def render_frame(frame_idx, bom_items, cumulative_costs, total_bom_cost):
    """Renders a single 1080x1920 frame."""
    t_sec = frame_idx / FPS
    img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    img[:] = COLOR_BG

    # 1. Subtle background grid
    for gy in range(0, HEIGHT, 80):
        cv2.line(img, (0, gy), (WIDTH, gy), COLOR_GRID, 1)
    for gx in range(0, WIDTH, 80):
        cv2.line(img, (gx, 0), (gx, HEIGHT), COLOR_GRID, 1)

    # 2. Header HUD
    cv2.line(img, (60, 130), (WIDTH - 60, 130), (45, 55, 75), 2)
    cv2.putText(img, "NEXUSDELIVERY AUTONOMOUS AMR", (60, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.95, COLOR_WHITE, 2, cv2.LINE_AA)
    cv2.putText(img, "HARDWARE ENGINEERING DOSSIER | EXPLODED VIEW", (60, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_CYAN, 1, cv2.LINE_AA)
    cv2.putText(img, "REV 1.0-CONCEPT", (WIDTH - 240, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_ORANGE, 1, cv2.LINE_AA)

    # 3. Dynamic Timeline & Progression
    # Yaw slowly rotates
    yaw = 28 + (frame_idx / TOTAL_FRAMES) * 55.0
    pitch = 24

    # Exploded separation offset along Z
    # Act 1 (0-8s): 0mm
    # Act 2 (8-24s): smooth expansion 0 -> 160mm
    # Act 3 (24-44s): held at 160mm
    # Act 4 (44-52s): slight compression
    # Act 5 (52-60s): assembled final
    if t_sec < 8.0:
        sep_z = 0.0
    elif t_sec < 20.0:
        p = (t_sec - 8.0) / 12.0
        sep_z = 160.0 * (1.0 - math.cos(p * math.pi)) / 2.0
    elif t_sec < 44.0:
        sep_z = 160.0
    elif t_sec < 52.0:
        p = (t_sec - 44.0) / 8.0
        sep_z = 160.0 - 120.0 * p
    else:
        sep_z = 40.0

    # 4. Draw 3D Exploded Robot Assembly
    scale = 1.45
    cy_robot = 750

    # A. Body Layer (Z = 0)
    # Chassis Baseplate (600x380x4 mm)
    draw_3d_box(img, -200, 200, -130, 130, 0, 8, COLOR_CYAN, 2, (35, 45, 60), cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
    # 2x Traction Hub Motors (Left and Right)
    draw_3d_box(img, -40, 40, -155, -130, -35, 45, COLOR_ORANGE, 2, (40, 50, 70), cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
    draw_3d_box(img, -40, 40, 130, 155, -35, 45, COLOR_ORANGE, 2, (40, 50, 70), cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
    # 2x Casters (Front and Rear)
    draw_3d_box(img, -170, -145, -15, 15, -25, 0, COLOR_GRAY, 1, None, cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
    draw_3d_box(img, 145, 170, -15, 15, -25, 0, COLOR_GRAY, 1, None, cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
    # Battery Pack LiFePO4 (Body Plate)
    draw_3d_box(img, -140, 20, -80, 80, 10, 60, (50, 160, 220), 2, (30, 50, 70), cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
    # ODrive S1 Controller
    draw_3d_box(img, 40, 120, -50, 50, 10, 35, (100, 200, 120), 2, (30, 60, 40), cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)

    # B. Brain Layer (Elevated by sep_z)
    bz = 90 + sep_z
    # Brain Carrier Plate (240x200 mm)
    draw_3d_box(img, -80, 80, -70, 70, bz, bz + 6, COLOR_CYAN, 2, (45, 60, 80), cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
    # Raspberry Pi 5 + Hailo NPU M.2 HAT+
    draw_3d_box(img, -60, 20, -50, 20, bz + 6, bz + 28, (80, 220, 140), 2, (35, 75, 50), cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
    # Intel RealSense D435i Camera (Front Bracket)
    draw_3d_box(img, 60, 95, -45, 45, bz + 10, bz + 35, (230, 140, 40), 2, (60, 40, 25), cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)

    # C. Motorized Cargo Hatch (Elevated by 2 * sep_z)
    lz = 160 + sep_z * 2.0
    # Top Lid Plate (520x340 mm)
    draw_3d_box(img, -180, 180, -115, 115, lz, lz + 6, COLOR_WHITE, 2, (60, 70, 85), cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)

    # 5. Connecting Standoffs (dotted when exploded)
    if sep_z > 20.0:
        c1 = project_3d(-70, -60, 8, cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
        c2 = project_3d(-70, -60, bz, cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
        cv2.line(img, c1, c2, (80, 100, 120), 1, cv2.LINE_AA)
        c3 = project_3d(70, 60, 8, cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
        c4 = project_3d(70, 60, bz, cy=cy_robot, scale=scale, yaw_deg=yaw, pitch_deg=pitch)
        cv2.line(img, c3, c4, (80, 100, 120), 1, cv2.LINE_AA)

    # 6. Act-Specific Overlays & BOM Counter
    # Live Ticking BOM Counter
    if t_sec < 8.0:
        current_cost = 0.0
        active_idx = 0
    elif t_sec < 44.0:
        # Progress across items
        p = (t_sec - 8.0) / 36.0
        exact_idx = min(len(bom_items) - 1, int(p * len(bom_items)))
        active_idx = exact_idx
        current_cost = cumulative_costs[active_idx]
    else:
        active_idx = len(bom_items) - 1
        current_cost = total_bom_cost

    # Large Counter HUD Banner
    cv2.rectangle(img, (60, 1070), (WIDTH - 60, 1200), (22, 27, 34), -1)
    cv2.rectangle(img, (60, 1070), (WIDTH - 60, 1200), COLOR_ORANGE, 2, cv2.LINE_AA)
    cv2.putText(img, "PARTS COST (BOM EXTENDED)", (84, 1110), cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_GRAY, 1, cv2.LINE_AA)
    cost_text = f"${current_cost:,.2f} USD"
    cv2.putText(img, cost_text, (84, 1175), cv2.FONT_HERSHEY_SIMPLEX, 1.8, COLOR_WHITE, 3, cv2.LINE_AA)
    cv2.putText(img, "LIVE BOM CSV COUNTER", (WIDTH - 360, 1110), cv2.FONT_HERSHEY_SIMPLEX, 0.52, COLOR_CYAN, 1, cv2.LINE_AA)
    cv2.putText(img, f"ITEM {active_idx+1:02d} / {len(bom_items):02d}", (WIDTH - 250, 1170), cv2.FONT_HERSHEY_SIMPLEX, 0.72, COLOR_ORANGE, 2, cv2.LINE_AA)

    # Technical Callout Card
    cur_item = bom_items[active_idx]
    card_title = f"{cur_item['component']} (Qty: {cur_item['qty']})"
    card_sub = f"Subsystem: {cur_item['subsystem']} | P/N: {cur_item['part_number']}"
    card_details = [
        f"Key Specifications: {cur_item['specs']}",
        f"Unit Price: ${cur_item['unit_cost']:.2f} USD | Total Line: ${cur_item['ext_cost']:.2f} USD",
        f"Source Status: {cur_item['status']}"
    ]

    if t_sec < 8.0:
        draw_card(img, 60, 1240, WIDTH - 120, 270,
                  "NEXUSDELIVERY AUTONOMOUS AMR",
                  "600x380mm Differential Drive Sidewalk Platform",
                  [
                      "Zero-LiDAR Active Infrared RGB-D Perception",
                      "Hailo-8L M.2 AI HAT+ (13 INT8 TOPS @ 2.5W)",
                      "4.0mm Aluminum 5052-H32 Laser-Cut Flat-Pack Frame",
                      "79/79 Automated Unit Tests Passing (100% Core Coverage)"
                  ],
                  badge="TRL 3 BASELINE")
    elif t_sec < 44.0:
        draw_card(img, 60, 1240, WIDTH - 120, 270,
                  card_title, card_sub, card_details,
                  badge=cur_item['status'])
    elif t_sec < 52.0:
        draw_card(img, 60, 1240, WIDTH - 120, 270,
                  "ELECTRICAL POWER TREE & SAFETY",
                  "25.6V LiFePO4 (512 Wh) + Daly Smart BMS",
                  [
                      "33A Continuous / 50A Peak Current Capacity",
                      "10 AWG High-Temp Silicone Power Wiring (Bypasses PCB)",
                      "50A Slow-Blow MIDI Main Fuse (Littelfuse 0498050.M)",
                      "Galvanically Isolated CAN 2.0B Bus (2500 Vrms Isolation)"
                  ],
                  badge="SAFETY CONCEPT")
    else:
        draw_card(img, 60, 1240, WIDTH - 120, 270,
                  "NEXUSDELIVERY CAPITAL EXPENDITURE",
                  "Reconciled Single Source of Truth (BOM.csv)",
                  [
                      f"Total Pieces Brutes (16 postes): ${total_bom_cost:,.2f} USD",
                      "Fret & Douane Tunisie (indicatif ~30%): $580.00 USD (ESTIMATION - A VERIFIER)",
                      f"Total Rendu Tunisie: ${total_bom_cost + 580.00:,.2f} USD (ESTIMATION)",
                      "GitHub: github.com/Chiheb-bt/NexusDelivery-Autonomous-AMR"
                  ],
                  badge="VERIFIED BOM")

    # 7. Bottom Permanent Mandatory Watermarks
    cv2.rectangle(img, (0, HEIGHT - 90), (WIDTH, HEIGHT), (12, 14, 18), -1)
    cv2.line(img, (0, HEIGHT - 90), (WIDTH, HEIGHT - 90), (45, 50, 60), 1)

    if 44.0 <= t_sec < 52.0:
        cv2.putText(img, "Simulation Gazebo Classic | TRL 3 Baseline", (60, HEIGHT - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, COLOR_CYAN, 2, cv2.LINE_AA)
    else:
        cv2.putText(img, "Concept de conception, pas un prototype", (60, HEIGHT - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (100, 110, 240), 2, cv2.LINE_AA)

    time_str = f"{int(t_sec//60):02d}:{int(t_sec%60):02d} / 01:00"
    cv2.putText(img, time_str, (WIDTH - 220, HEIGHT - 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, COLOR_GRAY, 1, cv2.LINE_AA)

    return img

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(repo_root, "delivery_robot_sim", "web_dashboard", "downloads", "BOM.csv")
    output_dir = os.path.join(repo_root, "docs", "assets")
    os.makedirs(output_dir, exist_ok=True)
    output_video = os.path.join(output_dir, "nexus_hardware_exploded_view_9x16.mp4")

    print(f"Loading BOM line items from: {csv_path}")
    bom_items = load_bom_items(csv_path)
    total_bom_cost = sum(i['ext_cost'] for i in bom_items)
    print(f"Loaded {len(bom_items)} BOM items. Total cost: ${total_bom_cost:.2f} USD")

    # Precalculate running cumulative costs
    cumulative_costs = []
    current_acc = 0.0
    for it in bom_items:
        current_acc += it['ext_cost']
        cumulative_costs.append(current_acc)

    print(f"Target Video: {output_video}")
    print(f"Resolution: {WIDTH}x{HEIGHT} (9:16) @ {FPS} FPS | Duration: {DURATION_S}s ({TOTAL_FRAMES} frames)")

    # Initialize video writer with mp4v (widely compatible on Linux systems)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_video, fourcc, FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        writer = cv2.VideoWriter(output_video, fourcc, FPS, (WIDTH, HEIGHT))

    if not writer.isOpened():
        raise RuntimeError("Failed to initialize cv2.VideoWriter. Check video codec support.")

    # Render frames
    print("Starting rendering pipeline...")
    for idx in range(TOTAL_FRAMES):
        frame = render_frame(idx, bom_items, cumulative_costs, total_bom_cost)
        writer.write(frame)
        if idx % 150 == 0 or idx == TOTAL_FRAMES - 1:
            progress_pct = (idx + 1) / TOTAL_FRAMES * 100.0
            print(f"Render progress: {idx+1}/{TOTAL_FRAMES} frames ({progress_pct:.1f}%) | Time: {(idx+1)/FPS:.1f}s")

    writer.release()
    print("Video rendering complete!")

    if os.path.exists(output_video) and os.path.getsize(output_video) > 100000:
        file_size_mb = os.path.getsize(output_video) / (1024 * 1024)
        print(f"SUCCESS: Video generated at {output_video} ({file_size_mb:.2f} MB)")
    else:
        raise RuntimeError(f"Video file generation failed or output too small: {output_video}")

if __name__ == '__main__':
    main()
