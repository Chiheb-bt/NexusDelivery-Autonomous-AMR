#!/usr/bin/env python3
"""Gazebo user camera tracking daemon for Chiheb Robotics NexusDelivery.

Monitors Gazebo for rdsim entity and commands the user camera to follow the robot chassis.
"""
import subprocess
import time
import sys

def run_cmd(args):
    try:
        res = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        return res.returncode == 0, res.stdout.strip()
    except Exception as e:
        return False, str(e)

def main():
    print("[CameraFollow] Initializing Gazebo camera tracking daemon...")
    model_found = False
    for _ in range(60):
        ok, out = run_cmd(["gz", "model", "-m", "rdsim", "-i"])
        if ok and "rdsim" in out:
            model_found = True
            break
        time.sleep(1.0)

    if not model_found:
        print("[CameraFollow] Warning: rdsim not detected within timeout. Exiting.")
        return

    print("[CameraFollow] rdsim detected in Gazebo! Locking user camera onto robot...")
    time.sleep(1.0)

    # Detect active cameras
    _, cam_list = run_cmd(["gz", "camera", "-l"])
    cameras = [line.strip() for line in cam_list.splitlines() if line.strip()]
    if not cameras:
        cameras = ["default::user_camera", "gzclient_camera", "user_camera"]

    print(f"[CameraFollow] Active cameras: {cameras}")
    for cam in cameras:
        ok, res = run_cmd(["gz", "camera", "-c", cam, "-f", "rdsim"])
        if ok:
            print(f"[CameraFollow] Successfully attached {cam} to follow rdsim.")
        else:
            print(f"[CameraFollow] Failed for {cam}: {res}")

    print("[CameraFollow] Active tracking engaged.")

if __name__ == "__main__":
    main()
