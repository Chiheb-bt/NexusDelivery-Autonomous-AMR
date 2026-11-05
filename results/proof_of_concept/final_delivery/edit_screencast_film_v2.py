import os
import subprocess

SRC = "/home/chiheb/Downloads/screencast_clean.mp4"
OUT_DIR = "/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY/results/proof_of_concept/final_delivery"
AUDIO = f"{OUT_DIR}/NEXUSDELIVERY_VOICEOVER_FR.wav"

cuts = [
    ("part1_gazebo.mp4", 0, 32),
    ("part2_landing_specs.mp4", 36, 34),
    ("part3_order_dispatch.mp4", 118, 30),
    ("part4_live_transit.mp4", 148, 36),
    ("part5_doorstep_otp.mp4", 224, 22),
    ("part6_supervisor.mp4", 286, 20),
]

part_files = []
for fname, start, dur in cuts:
    out_path = f"{OUT_DIR}/{fname}"
    part_files.append(out_path)
    cmd = [
        "snap", "run", "ffmpeg", "-ss", str(start), "-i", SRC, "-t", str(dur),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-r", "30", "-an", "-y", out_path
    ]
    print(f"Cutting {fname}...")
    subprocess.run(cmd, check=True)

# Create concat list
concat_list_file = f"{OUT_DIR}/concat_list.txt"
with open(concat_list_file, "w") as f:
    for pf in part_files:
        f.write(f"file '{pf}'\n")

# Concat video parts and add French voiceover
out_final = f"{OUT_DIR}/NEXUSDELIVERY_ENGINEERING_POC.mp4"
concat_cmd = [
    "snap", "run", "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_file,
    "-i", AUDIO,
    "-c:v", "copy",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    "-y", out_final
]
print("Muxing final documentary video with audio...")
subprocess.run(concat_cmd, check=True)
print("SUCCESS: Generated", out_final)

# Create 60s showcase
out_teaser = f"{OUT_DIR}/NEXUSDELIVERY_SHORT_SHOWCASE.mp4"
teaser_cmd = [
    "snap", "run", "ffmpeg", "-i", out_final, "-t", "60",
    "-c:v", "copy", "-c:a", "copy",
    "-y", out_teaser
]
subprocess.run(teaser_cmd, check=True)
print("SUCCESS: Generated 60s teaser", out_teaser)

# Cleanup parts
for pf in part_files:
    if os.path.exists(pf):
        os.remove(pf)
if os.path.exists(concat_list_file):
    os.remove(concat_list_file)

