#!/usr/bin/env python3
"""Generate a high-definition 1080p MP4 Proof of Concept video for Chiheb Robotics NexusDelivery.

Combines:
1. Title Showcase & Executive Overview
2. Customer Ordering Portal (Map pin drop, meal catalog, order dispatch)
3. Street Navigation & RealSense Front Camera (Pedestrian & obstacle detection HUD)
4. Mission Trajectory & Obstacle Avoidance (Full round-trip simulation)
5. Founder Fleet Cockpit (360 Depth Scanner, Hailo NPU, Telemetry)
6. Hardware Simulator & 2D CAD Blueprint
7. Doorstep Handover & Cargo Compartment Unlock
"""

import os
import cv2
import numpy as np
import shutil

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(ROOT_DIR, "docs", "assets")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
ARTIFACTS_DIR = "/home/chiheb/.gemini/antigravity-ide/brain/49b1b6a5-556f-4165-b847-7ec3d0732f25"

W, H = 1920, 1080
FPS = 25

def create_slide_frame(base_img_path, title_text, subtitle_text, progress_pct=0.0):
    if os.path.exists(base_img_path):
        img = cv2.imread(base_img_path)
        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_LANCZOS4)
    else:
        img = np.zeros((H, W, 3), dtype=np.uint8)

    # Top overlay header banner
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (W, 75), (10, 14, 23), -1)
    # Bottom status bar
    cv2.rectangle(overlay, (0, H - 45), (W, H), (10, 14, 23), -1)
    img = cv2.addWeighted(overlay, 0.85, img, 0.15, 0)

    # Cyan accent lines
    cv2.line(img, (0, 75), (W, 75), (254, 242, 0), 2)  # BGR cyan
    cv2.line(img, (0, H - 45), (W, H - 45), (50, 70, 90), 1)

    # Top text
    cv2.putText(img, "CHIHEB ROBOTICS  |  NEXUS-DELIVERY AUTONOMOUS PLATFORM", (40, 32),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(img, title_text, (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (254, 242, 0), 1, cv2.LINE_AA)

    # Bottom status
    cv2.putText(img, subtitle_text, (40, H - 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(img, "Strict Zero-LiDAR Zero-GPS  *  BOM: $1,065 USD  *  100% Mission Success", (W - 750, H - 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 180), 1, cv2.LINE_AA)

    # Progress bar at very bottom
    prog_w = int(W * progress_pct)
    cv2.rectangle(img, (0, H - 4), (prog_w, H), (254, 242, 0), -1)

    return img

def main():
    out_mp4 = os.path.join(RESULTS_DIR, "nexus_delivery_poc_video.mp4")
    print(f"[+] Generating Proof of Concept video: {out_mp4}")

    # Use mp4v codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_mp4, fourcc, FPS, (W, H))

    scenes = [
        # (Image path, Title, Subtitle, duration_sec)
        ("nexus_poc_showcase_banner.png",
         "1. EXECUTIVE PROOF OF CONCEPT & COMMERCIAL VALORIZATION",
         "Level 4 Sidewalk Delivery Robot * Hailo-8L AI + Intel RealSense D435i * 93% Capex Reduction", 4.0),

        ("poc_1_customer_portal.png",
         "2. CUSTOMER ORDERING PORTAL & SIDEWALK PIN DROPPER",
         "Interactive Vector Map * Direct Curbside Stopping Bay Snapping * Real-time 5-Stage Stepper", 4.5),

        ("poc_2_fleet_cockpit.png",
         "3. FOUNDER FLEET COCKPIT & REALSENSE VISION MONITOR",
         "Front RGB-D Camera Stream * Dynamic Obstacle Range & Pedestrian Gating * 360 Depth Scanner", 4.5),

        ("street_camera_frame.jpg",
         "4. REALSENSE D435i ACTIVE STEREO VISION ON SIDEWALK",
         "YOLOv8s + Depth Bounding Box [OBSTACLE 1.0m] * Parked Vehicles & Crosswalk Detection", 3.5),

        ("intersection_camera_frame.jpg",
         "5. DYNAMIC INTERSECTION NAVIGATION & OBSTACLE YIELDING",
         "Pedestrian Gating [0.4m] * Red Fire Hydrant Clearance * 0 Collisions Verified", 3.5),

        ("final_verified_mission_trajectory.png",
         "6. AUTONOMOUS MISSION TRAJECTORY & DEPOT ROUND-TRIP",
         "89.76m Total Travel * 2/2 Multi-Drop Orders Delivered * Depot Docking Verified", 4.5),

        ("poc_3_hardware_simulator.png",
         "7. PHYSICAL HARDWARE SIMULATOR & BMS CELL BALANCER",
         "40-Pin GPIO Interactive Pinout * Hailo-8L NPU Benchmark (7.18 ms) * Daly 8S LiFePO4 BMS", 4.0),

        ("poc_4_cad_blueprint.png",
         "8. 2D MECHANICAL CAD FABRICATION BLUEPRINT (1:1 SCALE)",
         "4.0mm Aluminum 5052-H32 CNC Laser-Cut Baseplate * Standardized DXF/SVG * < 2 Hours Assembly", 4.0),

        ("poc_5_doorstep_unlocked.png",
         "9. DOORSTEP ARRIVAL & CARGO COMPARTMENT UNLOCK",
         "Dynamic 6-Digit OTP Solenoid Hatch Unlatching * Audio Doorbell Chime * Contactless Handover", 4.0),

        ("nexus_poc_showcase_banner.png",
         "10. CHIHEB ROBOTICS — BUILT TO SCALE AT $1,065.00 BOM",
         "$0.42 / Delivery Unit Economics * 21 Days Fleet Payback * Ready for Commercial Rollout", 4.0)
    ]

    total_duration = sum(s[3] for s in scenes)
    current_time = 0.0

    for idx, (img_name, title, subtitle, dur) in enumerate(scenes):
        img_path = os.path.join(ASSETS_DIR, img_name)
        if not os.path.exists(img_path):
            img_path = os.path.join(RESULTS_DIR, img_name)

        num_frames = int(dur * FPS)
        for f in range(num_frames):
            pct = (current_time + (f / float(num_frames)) * dur) / total_duration
            frame = create_slide_frame(img_path, title, subtitle, pct)

            # Add subtle pan/zoom effect or timestamp
            sec_remain = int(dur - (f / float(FPS)))
            cv2.putText(frame, f"00:{int(current_time + f/FPS):02d} / 00:{int(total_duration):02d}", (W - 180, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

            out.write(frame)
        current_time += dur
        print(f"    -> Rendered Scene {idx+1}/{len(scenes)}: {title}")

    out.release()
    print(f"[DONE] Video rendered successfully: {out_mp4}")

    # Copy to docs/assets and artifacts
    dest_asset = os.path.join(ASSETS_DIR, "nexus_delivery_poc_video.mp4")
    dest_artifact = os.path.join(ARTIFACTS_DIR, "nexus_delivery_poc_video.mp4")
    shutil.copy2(out_mp4, dest_asset)
    shutil.copy2(out_mp4, dest_artifact)
    print(f"    -> Copied to {dest_asset}")
    print(f"    -> Copied to {dest_artifact}")

if __name__ == "__main__":
    main()
