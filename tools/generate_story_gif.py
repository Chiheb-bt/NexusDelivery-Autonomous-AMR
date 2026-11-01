#!/usr/bin/env python3
"""Generate an animated summary GIF from nexus_master_delivery_story.mp4 using PIL.
Ensures instant viewing in markdown viewers, GitHub, and browser artifacts without external codecs.
"""

import os
import cv2
from PIL import Image

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
ASSETS_DIR = os.path.join(ROOT_DIR, "docs", "assets")
ARTIFACTS_DIR = "/home/chiheb/.gemini/antigravity-ide/brain/49b1b6a5-556f-4165-b847-7ec3d0732f25"

def main():
    video_path = os.path.join(RESULTS_DIR, "nexus_master_delivery_story.mp4")
    out_gif = os.path.join(RESULTS_DIR, "nexus_master_delivery_story.gif")
    
    if not os.path.exists(video_path):
        print(f"Error: {video_path} does not exist.")
        return

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[+] Sampling GIF from {total_frames} video frames...")

    # Sample ~45 key frames across the whole 68-second video (approx 1 frame every 1.5 seconds)
    step = max(1, total_frames // 45)
    frames_pil = []

    f_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if f_idx % step == 0:
            # Resize to 960x540 for fast loading GIF
            frame_resized = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            frames_pil.append(pil_img)
        f_idx += 1
    cap.release()

    if frames_pil:
        print(f"[+] Saving {len(frames_pil)} frames to {out_gif}...")
        frames_pil[0].save(
            out_gif,
            save_all=True,
            append_images=frames_pil[1:],
            duration=350,  # 350ms per frame
            loop=0,
            optimize=True
        )
        print(f"[SUCCESS] GIF created: {out_gif} ({os.path.getsize(out_gif)/1024/1024:.2f} MB)")
        # Copy to assets and artifacts
        for dest in [os.path.join(ASSETS_DIR, "nexus_master_delivery_story.gif"),
                     os.path.join(ARTIFACTS_DIR, "nexus_master_delivery_story.gif")]:
            import shutil
            shutil.copy2(out_gif, dest)
            print(f"    -> Copied to {dest}")

if __name__ == "__main__":
    main()
