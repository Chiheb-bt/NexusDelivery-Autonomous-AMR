#!/usr/bin/env python3
"""Build a presentation-ready Proof of Concept banner and visual assets for Chiheb Robotics NexusDelivery."""

import os
import shutil
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(ROOT_DIR, "docs", "assets")
ARTIFACTS_DIR = "/home/chiheb/.gemini/antigravity-ide/brain/49b1b6a5-556f-4165-b847-7ec3d0732f25"

def make_showcase_banner():
    # Banner 1920 x 1080
    W, H = 1920, 1080
    banner = Image.new("RGB", (W, H), (10, 14, 23))
    draw = ImageDraw.Draw(banner)

    # Gradient header bar
    for y in range(90):
        alpha = y / 90.0
        r = int(12 + alpha * 10)
        g = int(22 + alpha * 15)
        b = int(38 + alpha * 20)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Decorative cyan neon border at top
    draw.line([(0, 90), (W, 90)], fill=(0, 242, 254), width=3)

    # Title text
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        font_card_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_stat_val = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        font_stat_lbl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_card_title = font_title
        font_stat_val = font_title
        font_stat_lbl = font_title

    draw.text((40, 22), "CHIHEB ROBOTICS — NEXUS-DELIVERY PLATFORM", fill=(255, 255, 255), font=font_title)
    draw.text((40, 60), "Proof of Concept & Commercial Valorization Suite • Strict Zero-LiDAR Zero-GPS Vision Autonomy", fill=(0, 242, 254), font=font_sub)

    # 4 Quad Screenshots Layout
    # Grid 2x2 with stats on the right or bottom
    # Left column: 2 screenshots (Customer Portal & Cockpit)
    # Middle column: 2 screenshots (Hardware & 2D CAD)
    # Right sidebar: Executive KPI Dashboard

    grid_w = 690
    grid_h = 390
    y1 = 120
    y2 = 560

    slots = [
        ("poc_1_customer_portal.png", 40, y1, "1. Customer E-Commerce & Sidewalk Pin Dropper"),
        ("poc_2_fleet_cockpit.png", 40, y2, "2. Founder Fleet Cockpit & RealSense Vision Monitor"),
        ("poc_3_hardware_simulator.png", 760, y1, "3. Hardware Simulator, 40-Pin GPIO & BMS Balancer"),
        ("poc_4_cad_blueprint.png", 760, y2, "4. 2D Mechanical CAD Fabrication Blueprint (1:1 mm)")
    ]

    for fname, x, y, label in slots:
        img_path = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(img_path):
            with Image.open(img_path) as im:
                thumb = im.resize((grid_w, grid_h), Image.Resampling.LANCZOS)
                banner.paste(thumb, (x, y + 30))
        # Draw frame card border
        draw.rectangle([x, y, x + grid_w, y + grid_h + 30], outline=(30, 41, 59), width=2)
        draw.rectangle([x, y, x + grid_w, y + 30], fill=(17, 24, 39))
        draw.text((x + 15, y + 6), label, fill=(56, 189, 248), font=font_card_title)

    # Right Sidebar: Executive Metrics & Value Added
    sb_x = 1480
    sb_w = 400
    sb_h = 860
    draw.rectangle([sb_x, y1, sb_x + sb_w, y1 + sb_h], fill=(15, 23, 42), outline=(0, 242, 254), width=2)

    # Sidebar Header
    draw.rectangle([sb_x, y1, sb_x + sb_w, y1 + 50], fill=(23, 37, 84))
    draw.text((sb_x + 20, y1 + 14), "EXECUTIVE POC METRICS", fill=(255, 255, 255), font=font_card_title)

    stats = [
        ("TOTAL UNIT BOM COST", "$1,065.00", "93% Capex Reduction vs $15,000 LiDAR"),
        ("AUTONOMY STACK", "Zero LiDAR / Zero GPS", "RGB-D Active IR + Hailo-8L + Odometry"),
        ("COLLISION RATE", "0 Collisions", "100% Safety (Pedestrians & Curbs avoided)"),
        ("MISSION SUCCESS", "2/2 Drops (100%)", "74.8m Trajectory, Depot Round-Trip"),
        ("EDGE AI LATENCY", "7.18 ms (138 FPS)", "Hailo-8L NPU (13 TOPS INT8 @ 2.5W)"),
        ("DELIVERY MARGIN", "$0.42 / drop", "vs $4.50 human courier (-90% Opex)"),
        ("CHASSIS FABRICATION", "< 2 Hours Assembly", "4.0mm Al 5052-H32 CNC Laser-Cut"),
        ("BATTERY ENDURANCE", "21.8 km / Charge", "25.6V 20Ah LiFePO4 (8S Daly BMS)")
    ]

    stat_y = y1 + 75
    for title, val, note in stats:
        draw.rectangle([sb_x + 15, stat_y, sb_x + sb_w - 15, stat_y + 82], fill=(22, 32, 54), outline=(45, 60, 90), width=1)
        draw.text((sb_x + 25, stat_y + 8), title, fill=(148, 163, 184), font=font_stat_lbl)
        draw.text((sb_x + 25, stat_y + 26), val, fill=(0, 242, 254), font=font_stat_val)
        draw.text((sb_x + 25, stat_y + 60), note, fill=(34, 197, 94) if ("%" in note or "100" in note or "0" in note) else (203, 213, 225), font=font_stat_lbl)
        stat_y += 95

    # Footer signature
    draw.text((sb_x + 35, y1 + sb_h - 40), "Chiheb Robotics • Built for Scale", fill=(100, 116, 139), font=font_sub)

    out_file = os.path.join(ASSETS_DIR, "nexus_poc_showcase_banner.png")
    banner.save(out_file, "PNG", quality=95)
    print(f"[+] Saved showcase banner: {out_file}")

    # Copy to artifacts
    art_file = os.path.join(ARTIFACTS_DIR, "nexus_poc_showcase_banner.png")
    shutil.copy2(out_file, art_file)
    print(f"[+] Copied showcase banner to artifacts: {art_file}")

if __name__ == "__main__":
    make_showcase_banner()
