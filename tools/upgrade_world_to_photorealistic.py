#!/usr/bin/env python3
"""Upgrade small_city_dynamic.world with red brick sidewalks, commercial storefronts, and parked cars."""
import re
import sys

WORLD_PATH = "/home/chiheb/Downloads/RDSim-devel-2wheel_diff/rdsim_gazebo/worlds/small_city_dynamic.world"

def main():
    print(f"Reading {WORLD_PATH}...")
    with open(WORLD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update user_camera pose to low 3/4 front view facing CHIHEB_BOT
    old_camera_pattern = r"(<gui>\s*<camera name=[\"']user_camera[\"']>\s*<pose>)[^<]*(</pose>\s*</camera>\s*</gui>)"
    new_camera_pose = r"\g<1>-28.8 -0.45 0.48 0 0.10 -2.85\g<2>"
    content = re.sub(old_camera_pattern, new_camera_pose, content, count=1)

    # 2. Replace all sidewalk material <ambient>0.2 0.2 0.2 1.0</ambient> with Gazebo/Bricks
    old_mat = """      <material>
        <ambient>0.2 0.2 0.2 1.0</ambient>
      </material>"""
    new_mat = """      <material>
        <script>
          <uri>file://media/materials/scripts/gazebo.material</uri>
          <name>Gazebo/Bricks</name>
        </script>
      </material>"""
    
    count = content.count(old_mat)
    print(f"Replacing {count} sidewalk ambient materials with Gazebo/Bricks...")
    content = content.replace(old_mat, new_mat)

    # 3. Add commercial storefronts, parked cars, outdoor cafe tables along Central Blvd
    # Insert right before </world>
    city_props = """
    <!-- ============================================================== -->
    <!-- Photorealistic Commercial Streetscape & Curbside Props         -->
    <!-- ============================================================== -->
    <!-- Parked Blue Car along Boulevard Curb -->
    <include>
      <name>parked_car_blue_curb</name>
      <pose>-20.5 -2.2 0.05 0 0 0</pose>
      <uri>model://hatchback_blue</uri>
    </include>

    <!-- Parked Red Car along Boulevard Curb -->
    <include>
      <name>parked_car_red_curb</name>
      <pose>-16.5 -2.2 0.05 0 0 0</pose>
      <uri>model://hatchback_red</uri>
    </include>

    <!-- Sidewalk Commercial Cafe Tables & Seating -->
    <include>
      <name>cafe_outdoor_table_1</name>
      <pose>-20.0 2.4 0.15 0 0 0</pose>
      <uri>model://cafe_table</uri>
    </include>
    <include>
      <name>cafe_outdoor_chair_1</name>
      <pose>-20.0 2.8 0.15 0 0 -1.57</pose>
      <uri>model://chair_1</uri>
    </include>
    <include>
      <name>cafe_outdoor_chair_2</name>
      <pose>-20.0 2.0 0.15 0 0 1.57</pose>
      <uri>model://chair_1</uri>
    </include>

    <!-- Streetlamp Post -->
    <include>
      <name>sidewalk_lamp_post_1</name>
      <pose>-22.5 2.6 0.15 0 0 0</pose>
      <uri>model://lamp_post</uri>
    </include>

    <!-- Sidewalk Urban Tree -->
    <include>
      <name>sidewalk_oak_tree_1</name>
      <pose>-17.5 2.6 0.15 0 0 0</pose>
      <uri>model://oak_tree</uri>
    </include>

    <!-- Sidewalk Public Trash Bin -->
    <include>
      <name>sidewalk_trash_bin_1</name>
      <pose>-24.0 2.5 0.15 0 0 0</pose>
      <uri>model://trash_bin</uri>
    </include>
"""
    if "parked_car_blue_curb" not in content:
        content = content.replace("</world>", city_props + "\n  </world>")

    with open(WORLD_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("small_city_dynamic.world successfully upgraded!")

if __name__ == "__main__":
    main()
