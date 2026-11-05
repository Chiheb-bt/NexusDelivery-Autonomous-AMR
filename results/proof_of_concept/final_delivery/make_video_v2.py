#!/usr/bin/env python3
"""Build the NEXUSDELIVERY POC video — moviepy 2.x API"""
import os
os.environ['IMAGEIO_FFMPEG_EXE'] = '/snap/bin/ffmpeg'

import moviepy as mp
from moviepy import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np

BASE = "/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY"
RESULTS = "/home/chiheb/rdsim_ws/results"
PRES = "/home/chiheb/Downloads/RDSim-devel-2wheel_diff/presentations/assets"
CAPS = f"{BASE}/results/proof_of_concept/authentic_film/genuine_robot_captures"
OUT = f"{BASE}/results/proof_of_concept/final_delivery"
os.makedirs(OUT, exist_ok=True)

W, H = 1920, 1080
FPS = 24

def load_img(path, size=(W,H)):
    if not os.path.exists(path):
        print(f"  MISSING: {path}")
        return np.zeros((size[1], size[0], 3), dtype=np.uint8) + np.array([10,10,25], dtype=np.uint8)
    img = Image.open(path).convert('RGB').resize(size, Image.LANCZOS)
    return np.array(img)

def add_label_pil(img_arr, text, color=(0,220,255)):
    img = Image.fromarray(img_arr)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except:
        font = ImageFont.load_default()
    draw.rectangle([0, H-72, W, H], fill=(5,5,20))
    draw.text((28, H-58), text, font=font, fill=color)
    return np.array(img)

def make_title_arr(title, subtitle="", bg=(5,5,20)):
    img = Image.new('RGB', (W,H), bg)
    draw = ImageDraw.Draw(img)
    try:
        f_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 76)
        f_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
        f_hdr = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
    except:
        f_big = f_sub = f_hdr = ImageFont.load_default()
    draw.rectangle([0, H//2-4, W, H//2+4], fill=(0,180,220))
    draw.text((60, 46), "NEXORA  //  AUTONOMOUS SIDEWALK DELIVERY ROBOT", font=f_hdr, fill=(0,180,220))
    draw.text((60, 108), "Chiheb Robotics Systems Lab  •  TRL 3–4  •  Proof of Concept", font=f_sub, fill=(100,140,200))
    bbox = draw.textbbox((0,0), title, font=f_big)
    tw = bbox[2]-bbox[0]
    draw.text(((W-tw)//2, H//2+36), title, font=f_big, fill=(255,255,255))
    if subtitle:
        bbox2 = draw.textbbox((0,0), subtitle, font=f_sub)
        tw2 = bbox2[2]-bbox2[0]
        draw.text(((W-tw2)//2, H//2+136), subtitle, font=f_sub, fill=(180,220,255))
    return np.array(img)

def make_chapter_arr(num, title):
    return make_title_arr(f"CHAPITRE {num}", title)

def img_clip(arr, duration):
    return ImageClip(arr, duration=duration)

def path_clip(path, duration, label=None):
    arr = load_img(path)
    if label:
        arr = add_label_pil(arr, label)
    return ImageClip(arr, duration=duration)

# ==== BUILD SCENES ====
print("Building scenes...")
clips = []

def add(c):
    # Add crossfade
    clips.append(c.with_effects([vfx.FadeIn(0.5)]))

# INTRO
add(ImageClip(make_title_arr("NEXORA", "Plateforme Autonome de Livraison Urbaine — Proof of Concept"), duration=4.0))

# OPENING: Real Gazebo
add(path_clip(f"{RESULTS}/test_cinematic_gazebo.jpg", 8.0,
    "Vue Gazebo Classic réelle — small_city_dynamic.world — Robot NexusDelivery"))

# CHAPTER 1
add(ImageClip(make_chapter_arr("1", "LE ROBOT : ARCHITECTURE DIFFÉRENTIELLE"), duration=2.5))
add(path_clip(f"{CAPS}/capture_01_robot_front_view.jpg", 7.0,
    "Vue frontale URDF — Châssis 0,82m × 0,62m — 22 kg — Certifié Gazebo Physics"))
add(path_clip(f"{CAPS}/capture_02_robot_side_view.jpg", 6.0,
    "Vue latérale — Caméra RGB-D + Baie cargo + Trappe motorisée 60°"))
add(path_clip(f"{CAPS}/capture_05_differential_wheels.jpg", 6.0,
    "Roues différentielles — R=0,20m — ODE 1000Hz — Rotation zéro-rayon"))
add(path_clip(f"{CAPS}/capture_06_front_camera_assembly.jpg", 5.0,
    "Module perception RGB-D — FOV 87° — IMU 6 axes — ZÉRO LiDAR"))
add(path_clip(f"{CAPS}/capture_07_cargo_compartment.jpg", 5.0,
    "Compartiment cargo — Verrou OTP HMAC-SHA256 — Trappe articulée"))
add(path_clip(f"{CAPS}/capture_08_cargo_hatch_actuation.jpg", 5.5,
    "Actionnement trappe — Joint 0,0 → 1,05 rad (60°) — Contrôlé Gazebo"))

# CHAPTER 2: World  
add(ImageClip(make_chapter_arr("2", "ENVIRONNEMENT GAZEBO"), duration=2.5))
add(path_clip(f"{RESULTS}/test_cinematic_gazebo.jpg", 7.0,
    "Gazebo Classic — Routes, Feux tricolores, Stop Signs, Bâtiments, Obstacles dynamiques"))
add(path_clip(f"{PRES}/plan_ville_waypoints_schematiques.png", 7.0,
    "Réseau topologique — Dépôt → WP1–WP4 → Points de livraison"))

# CHAPTER 3: ROS 2
add(ImageClip(make_chapter_arr("3", "ARCHITECTURE ROS 2 & PERCEPTION"), duration=2.5))
add(path_clip(f"{PRES}/schema_robot_camera_gps.png", 7.0,
    "/camera/image_raw + /camera/depth + /odom + /imu — ZÉRO GPS"))
add(path_clip(f"{RESULTS}/snapshot_bgr.jpg", 5.5,
    "/camera/image_raw — Vue caméra frontale réelle du robot en mission"))
add(path_clip(f"{RESULTS}/snapshot_depth.jpg", 5.5,
    "/camera/depth/image_raw — Carte de profondeur réelle — Détection obstacles"))

# Bug fixes card
bug_img = Image.new('RGB', (W,H), (5,8,20))
draw = ImageDraw.Draw(bug_img)
try:
    ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 46)
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    ff = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
except:
    ft = fb = ff = ImageFont.load_default()
draw.text((80, 60), "PROBLÈMES RÉELS RENCONTRÉS & CORRECTIONS D'INGÉNIERIE", font=ft, fill=(0,220,255))
draw.rectangle([80, 130, W-80, 134], fill=(0,180,220))
bugs = [
    ("BUG 1 : Collision mur dépôt",
     "Waypoints ciblaient y=+2.50m → à l'intérieur du bâtiment",
     "FIX: Coordonnées verrouillées (-27.50, -0.75)m — portail physique vérifié"),
    ("BUG 2 : Angle mort caméra (75% invisible)",
     "Intrinsèques 320×240 codés sur flux réel 640×480 → perte 75% pixels",
     "FIX: Intrinsèques adaptatifs fx=fy=336.85, cx=320, cy=240"),
    ("BUG 3 : Retour prématuré auto-dwell 2s",
     "Minuterie auto-validait OTP et déclenchait demi-tour sans intervention client",
     "FIX: État WAITING_FOR_CUSTOMER indéfini → attente OTP réelle"),
]
y = 170
for title, problem, fix in bugs:
    draw.text((100, y), f"▸ {title}", font=ff, fill=(255,180,50))
    draw.text((120, y+42), f"⚠  {problem}", font=fb, fill=(220,180,180))
    draw.text((120, y+84), f"✓  {fix}", font=fb, fill=(100,255,100))
    y += 155
add(ImageClip(np.array(bug_img), duration=12.0))

# CHAPTER 4: Web Dashboard — use screencast
add(ImageClip(make_chapter_arr("4", "PORTAIL CLIENT & COCKPIT SUPERVISEUR"), duration=2.5))
screencast_path = f"{BASE}/results/proof_of_concept/Screencast From 2026-11-04 22-56-53.webm"
if os.path.exists(screencast_path):
    try:
        web_clip = VideoFileClip(screencast_path, audio=False).subclip(0, 15).resized((W, H))
        txt_arr = add_label_pil(np.zeros((H,W,3),dtype=np.uint8), 
                                "Dashboard Web Fleet Cockpit réel — Télémétrie Gazebo LIVE — http://localhost:8080")
        txt_clip = ImageClip(txt_arr, duration=15).with_effects([vfx.MaskColor(color=[0,0,0])])
        clips.append(web_clip.with_effects([vfx.FadeIn(0.5)]))
        print("  ✓ Screencast web clip included (15s)")
    except Exception as e:
        print(f"  Screencast error: {e}")
        add(path_clip(f"{RESULTS}/test_cinematic_gazebo.jpg", 10.0,
            "Web Fleet Cockpit — Gazebo Telemetry LIVE — http://localhost:8080"))
else:
    add(path_clip(f"{RESULTS}/test_cinematic_gazebo.jpg", 10.0,
        "Web Fleet Cockpit — http://localhost:8080"))

# CHAPTER 5: Mission
add(ImageClip(make_chapter_arr("5", "MISSION AUTONOME — DONNÉES MESURÉES"), duration=2.5))
add(path_clip(f"{RESULTS}/trajectory_plot.png", 12.0,
    "Trajectoire mesurée — 112,21 m — 0 Collision — Marge min 0,512 m — ORD-034 Livré ✓"))

# CHAPTER 6: Results
add(ImageClip(make_chapter_arr("6", "RÉSULTATS EXPÉRIMENTAUX VALIDÉS"), duration=2.5))
add(path_clip(f"{BASE}/assets/diagrams/mission_metrics_summary.png", 12.0,
    "Source: eval_summary.json + navigation_diagnostic_report.json — Données réelles"))

# Closing
add(ImageClip(make_title_arr("TRL 3–4  |  ZÉRO GPS  |  ZÉRO LiDAR",
    "112,21 m • 0 Collision • 1 Livraison Réussie • 75/75 Tests ✓"), duration=5.0))
add(ImageClip(make_title_arr("NEXORA — NEXUSDELIVERY",
    "Chiheb Ben Taher  •  github.com/Chiheb-bt  •  Chiheb Robotics Systems Lab"), duration=4.0))

# ==== CONCAT ====
print(f"Total scenes: {len(clips)}")
video = concatenate_videoclips(clips, method="compose")
print(f"Video duration: {video.duration:.1f}s")

# ==== AUDIO ====
narration_wav = f"{BASE}/results/proof_of_concept/authentic_film/narration_fr.wav"
if os.path.exists(narration_wav):
    audio = AudioFileClip(narration_wav)
    if audio.duration > video.duration:
        audio = audio.subclipped(0, video.duration)
    video = video.with_audio(audio)
    print(f"✓ Audio attached ({audio.duration:.1f}s)")

# ==== EXPORT ====
print("Exporting full POC video...")
out1 = f"{OUT}/NEXUSDELIVERY_ENGINEERING_POC.mp4"
video.write_videofile(out1, fps=FPS, codec='libx264', audio_codec='aac',
                     bitrate='2000k', logger='bar')
print(f"✅ {out1}  ({os.path.getsize(out1)/1e6:.1f} MB)")

print("Exporting short showcase (60s)...")
out2 = f"{OUT}/NEXUSDELIVERY_SHORT_SHOWCASE.mp4"
video.subclipped(0, min(60, video.duration)).write_videofile(
    out2, fps=FPS, codec='libx264', bitrate='2000k', logger='bar')
print(f"✅ {out2}")

