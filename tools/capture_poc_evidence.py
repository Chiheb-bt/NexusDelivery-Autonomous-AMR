#!/usr/bin/env python3
"""Capture high-resolution Proof of Concept evidence suite for Chiheb Robotics NexusDelivery.

Captures all 4 interactive web portals and compiles visual evidence:
1. Customer Ordering Portal (Sidewalk pin drop, menu catalog, OTP compartment unlock)
2. Founder Fleet Cockpit (Front HD camera monitor, 360 depth scanner, teleop)
3. Hardware Simulator Workbench (40-pin GPIO pinout, Hailo NPU, 8-cell BMS balancer)
4. 2D CAD Fabrication Blueprint (1:1 scale laser cut chassis)
5. Doorstep Handover & Cargo Unlock
"""

import os
import subprocess
import time
import shutil

BASE_URL = "http://localhost:8080"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "assets"))
ARTIFACTS_DIR = "/home/chiheb/.gemini/antigravity-ide/brain/49b1b6a5-556f-4165-b847-7ec3d0732f25"
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

PORTALS = [
    ("customer", "poc_1_customer_portal.png", "Customer Ordering & Sidewalk Pin Dropper Portal"),
    ("founder", "poc_2_fleet_cockpit.png", "Fleet Cockpit Live Vision Monitor & Teleoperation"),
    ("hardware", "poc_3_hardware_simulator.png", "Hardware Simulator, GPIO Pinout & BMS Balancer"),
    ("cad", "poc_4_cad_blueprint.png", "2D CAD Chassis Blueprint & Laser-Cut Fabrication Suite")
]

def capture_screenshot(portal_name, filename, title):
    url = f"{BASE_URL}/?portal={portal_name}"
    out_path = os.path.join(OUTPUT_DIR, filename)
    print(f"[+] Capturing {title} from {url}...")
    
    cmd = [
        "firefox",
        "--headless",
        "--screenshot", out_path,
        "--window-size", "1920,1080",
        url
    ]
    
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
        if os.path.exists(out_path):
            file_size = os.path.getsize(out_path)
            print(f"    -> Saved {out_path} ({file_size} bytes)")
            # Copy to artifacts dir
            art_path = os.path.join(ARTIFACTS_DIR, filename)
            shutil.copy2(out_path, art_path)
            print(f"    -> Copied to artifact: {art_path}")
            return True
        else:
            print(f"[-] Screenshot failed: output file not created. Stderr: {res.stderr.decode('utf-8')[:300]}")
            return False
    except Exception as e:
        print(f"[-] Exception during screenshot: {e}")
        return False

def main():
    print("=" * 65)
    print("  CHIHEB ROBOTICS — NEXUS-DELIVERY PROOF OF CONCEPT SUITE")
    print("=" * 65)
    
    success_count = 0
    for portal, fname, title in PORTALS:
        if capture_screenshot(portal, fname, title):
            success_count += 1
        time.sleep(1)
        
    # Also verify existing simulation replays and trajectory plots
    src_replay = os.path.join(RESULTS_DIR, "final_verified_mission_replay.gif")
    if os.path.exists(src_replay):
        dest_replay = os.path.join(OUTPUT_DIR, "nexus_delivery_poc_replay.gif")
        shutil.copy2(src_replay, dest_replay)
        shutil.copy2(src_replay, os.path.join(ARTIFACTS_DIR, "nexus_delivery_poc_replay.gif"))
        print(f"[+] Replay GIF verified and copied to assets & artifacts.")
        
    src_traj = os.path.join(RESULTS_DIR, "final_verified_mission_trajectory.png")
    if os.path.exists(src_traj):
        dest_traj = os.path.join(OUTPUT_DIR, "nexus_delivery_poc_trajectory.png")
        shutil.copy2(src_traj, dest_traj)
        shutil.copy2(src_traj, os.path.join(ARTIFACTS_DIR, "nexus_delivery_poc_trajectory.png"))
        print(f"[+] Trajectory PNG verified and copied to assets & artifacts.")
        
    print(f"\n[DONE] Captured {success_count}/{len(PORTALS)} portals successfully.")

if __name__ == "__main__":
    main()
