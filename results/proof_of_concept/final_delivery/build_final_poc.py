#!/usr/bin/env python3
"""
NEXUSDELIVERY — Authentic POC Video Builder
Using ONLY real assets from the actual simulation and project
"""
import os, sys, shutil
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Paths
BASE = "/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY"
RESULTS = "/home/chiheb/rdsim_ws/results"
PRES = "/home/chiheb/Downloads/RDSim-devel-2wheel_diff/presentations/assets"
OUT = f"{BASE}/results/proof_of_concept/final_delivery"
os.makedirs(OUT, exist_ok=True)

# --- Asset Inventory ---
REAL_ASSETS = {
    "gazebo_perspective": f"{RESULTS}/test_cinematic_gazebo.jpg",   # 1920x1080 real Gazebo
    "trajectory": f"{RESULTS}/trajectory_plot.png",                 # Real mission trajectory
    "replay_gif": f"{RESULTS}/replay.gif",                          # Real replay animation
    "snapshot_bgr": f"{RESULTS}/snapshot_bgr.jpg",                  # Real camera view
    "snapshot_depth": f"{RESULTS}/snapshot_depth.jpg",              # Real depth view
    "waypoints_schema": f"{PRES}/plan_ville_waypoints_schematiques.png",  # Schematic diagram
    "robot_top_schema": f"{PRES}/schema_robot_camera_gps.png",       # Robot top view schema
    "screencast": f"{BASE}/results/proof_of_concept/Screencast From 2026-11-04 22-56-53.webm",
    # URDF-rendered views (authentic geometry, enhanced presentation)
    "robot_front": f"{BASE}/results/proof_of_concept/authentic_film/genuine_robot_captures/capture_01_robot_front_view.jpg",
    "robot_side": f"{BASE}/results/proof_of_concept/authentic_film/genuine_robot_captures/capture_02_robot_side_view.jpg",
    "robot_rear": f"{BASE}/results/proof_of_concept/authentic_film/genuine_robot_captures/capture_03_robot_rear_view.jpg",
    "robot_wheels": f"{BASE}/results/proof_of_concept/authentic_film/genuine_robot_captures/capture_05_differential_wheels.jpg",
    "robot_camera_assy": f"{BASE}/results/proof_of_concept/authentic_film/genuine_robot_captures/capture_06_front_camera_assembly.jpg",
    "cargo_compartment": f"{BASE}/results/proof_of_concept/authentic_film/genuine_robot_captures/capture_07_cargo_compartment.jpg",
    "cargo_hatch": f"{BASE}/results/proof_of_concept/authentic_film/genuine_robot_captures/capture_08_cargo_hatch_actuation.jpg",
}

AI_FLAGGED = [
    "capture_09_robot_depot_departure.jpg",   # Uber Eats photorealistic — AI image, excluded
    "capture_10_robot_world_navigation.jpg",  # Photorealistic city — AI image, excluded
    "capture_11_robot_doorstep_arrival.jpg",
    "capture_12_robot_waiting_customer.jpg",
    "capture_13_robot_depot_return.jpg",
]

def add_label(img, text, position="bottom", color=(255,220,0), bg=(0,0,0,180), fontsize=28):
    """Add a text label overlay to an image"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize)
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    margin = 20
    if position == "bottom":
        x = (img.width - tw) // 2
        y = img.height - th - margin*2
    elif position == "top":
        x = margin
        y = margin
    else:
        x, y = position
    
    # Background box
    draw.rectangle([x-10, y-8, x+tw+10, y+th+8], fill=bg)
    draw.text((x, y), text, font=font, fill=color)
    
    result = Image.alpha_composite(img, overlay)
    return result.convert('RGB')

def make_title_card(text, subtitle="", bg=(5,5,20), size=(1920,1080)):
    """Create a dark title card"""
    img = Image.new('RGB', size, bg)
    draw = ImageDraw.Draw(img)
    
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        font_big = ImageFont.load_default()
        font_sm = font_big
    
    # Cyan accent bar
    draw.rectangle([0, 480, 1920, 486], fill=(0, 180, 220))
    
    # Title text
    bbox = draw.textbbox((0,0), text, font=font_big)
    tw = bbox[2]-bbox[0]
    draw.text(((size[0]-tw)//2, 360), text, font=font_big, fill=(255,255,255))
    
    if subtitle:
        bbox2 = draw.textbbox((0,0), subtitle, font=font_sm)
        tw2 = bbox2[2]-bbox2[0]
        draw.text(((size[0]-tw2)//2, 510), subtitle, font=font_sm, fill=(180,220,255))
    
    return img

def make_metrics_card(size=(1920,1080)):
    """Create a metrics summary card with real data"""
    img = Image.new('RGB', size, (5,10,20))
    draw = ImageDraw.Draw(img)
    
    try:
        font_hdr = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_val = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        font_lbl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except:
        font_hdr = font_val = font_lbl = ImageFont.load_default()
    
    draw.text((80, 60), "RÉSULTATS EXPÉRIMENTAUX MESURÉS", font=font_hdr, fill=(0,220,255))
    draw.text((80, 120), "Session de simulation — 4 Novembre 2026 — eval_summary.json", font=font_lbl, fill=(150,180,220))
    draw.rectangle([80, 165, 1840, 170], fill=(0,180,220))
    
    metrics = [
        ("Distance totale parcourue", "112,21 m", (100,255,100)),
        ("Vitesse maximale mesurée", "1,086 m/s", (100,255,100)),
        ("Vitesse moyenne", "0,793 m/s", (100,255,100)),
        ("Marge min obstacle", "0,512 m", (100,255,100)),
        ("Nombre de collisions", "0", (100,255,100)),
        ("Commandes livrées", "1 / 2  (ORD-034 ✓)", (100,255,100)),
        ("Retour au dépôt", "OUI", (100,255,100)),
        ("Tests automatisés", "75 / 75  (100 %)", (100,255,100)),
        ("Stack capteurs", "RGB Camera + RGB-D + IMU + Odom  •  ZÉRO GPS  •  ZÉRO LiDAR", (200,200,255)),
        ("Niveau TRL validé", "TRL 3–4  (Simulation haute fidélité)", (255,220,80)),
    ]
    
    y = 200
    for label, value, color in metrics:
        draw.text((100, y), f"▸  {label}", font=font_lbl, fill=(180,200,240))
        draw.text((860, y), value, font=font_val, fill=color)
        y += 72
    
    draw.text((80, 1010), "Source: /home/chiheb/rdsim_ws/results/eval_summary.json  |  navigation_diagnostic_report.json", 
              font=font_lbl, fill=(80,100,140))
    
    return img

# ============ Build GitHub Assets ============
print("Building authentic GitHub assets...")

# 1. Robot close-up (authentic URDF render)
if os.path.exists(REAL_ASSETS["robot_front"]):
    img = Image.open(REAL_ASSETS["robot_front"])
    img = add_label(img, "NEXORA — Modèle URDF Xacro réel • Gazebo Classic • Châssis 0,82m × 0,62m • 22 kg")
    img.save(f"{BASE}/assets/robot/nexus_delivery_robot.png")
    print("✓ nexus_delivery_robot.png")

# 2. Gazebo perspective (authentic Gazebo screenshot)
if os.path.exists(REAL_ASSETS["gazebo_perspective"]):
    img = Image.open(REAL_ASSETS["gazebo_perspective"])
    img = add_label(img, "Gazebo Classic — small_city_dynamic.world  •  Simulation physique réelle")
    img.save(f"{BASE}/assets/simulation/gazebo_world_perspective.png")
    print("✓ gazebo_world_perspective.png")

# 3. Trajectory as top-view representation
if os.path.exists(REAL_ASSETS["trajectory"]):
    img = Image.open(REAL_ASSETS["trajectory"]).convert('RGB')
    img_resized = img.resize((1920, 1080), Image.LANCZOS)
    img_labeled = add_label(img_resized, "Trajectoire mesurée • Dépôt (-31,5; -0,75) → Clients → Retour • 112,21 m • 0 Collision")
    img_labeled.save(f"{BASE}/assets/simulation/gazebo_world_top_view.png")
    print("✓ gazebo_world_top_view.png (trajectory plot as top-view representation)")

# 4. Metrics card
metrics = make_metrics_card()
metrics.save(f"{BASE}/assets/diagrams/mission_metrics_summary.png")
print("✓ mission_metrics_summary.png")

# 5. Robot schema
if os.path.exists(REAL_ASSETS["robot_top_schema"]):
    shutil.copy(REAL_ASSETS["robot_top_schema"], f"{BASE}/assets/diagrams/robot_architecture_schema.png")
    print("✓ robot_architecture_schema.png")

# 6. Waypoints schema
if os.path.exists(REAL_ASSETS["waypoints_schema"]):
    shutil.copy(REAL_ASSETS["waypoints_schema"], f"{BASE}/assets/diagrams/city_waypoints_schema.png")
    print("✓ city_waypoints_schema.png")

# 7. Camera view (real robot camera)
if os.path.exists(REAL_ASSETS["snapshot_bgr"]):
    img = Image.open(REAL_ASSETS["snapshot_bgr"])
    img = add_label(img, "/camera/image_raw • Vue réelle caméra frontale du robot • ROS 2 Topic")
    img.save(f"{BASE}/assets/simulation/robot_camera_view_real.png")
    print("✓ robot_camera_view_real.png")

# 8. Depth view
if os.path.exists(REAL_ASSETS["snapshot_depth"]):
    img = Image.open(REAL_ASSETS["snapshot_depth"])
    img = add_label(img, "/camera/depth/image_raw • Vue profondeur réelle • Détection obstacles piétons")
    img.save(f"{BASE}/assets/simulation/robot_depth_view_real.png")
    print("✓ robot_depth_view_real.png")

print("\n✅ GitHub assets generated in:", f"{BASE}/assets/")
print("\nAI-FLAGGED images (excluded from production use):")
for f in AI_FLAGGED:
    print(f"  ⚠ {f}")

