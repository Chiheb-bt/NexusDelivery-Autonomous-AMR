#!/usr/bin/env python3
"""NEXUSDELIVERY: Premium Robotics Visual Identity & LinkedIn Showcase Generator.
Produces high-resolution, pixel-perfect presentation graphics adhering strictly
to project engineering specifications and visual identity guidelines.
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = "/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY"
ASSETS_DIR = os.path.join(BASE_DIR, "assets/presentation")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Typography configuration
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def get_font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# Color Palette
BG_DARK = (7, 11, 20)          # #070B14 Deep Space Navy
BG_PANEL = (13, 20, 36, 230)   # Glassmorphic Card Surface
BORDER_CYAN = (0, 210, 255)    # #00D2FF Electric Cyan
BORDER_BLUE = (0, 112, 243)    # #0070F3 Electric Blue
BORDER_PURPLE = (147, 51, 234) # Purple Accent
TEXT_WHITE = (248, 250, 252)   # Slate 50
TEXT_MUTED = (148, 163, 184)   # Slate 400
TEXT_CYAN = (56, 189, 248)     # Sky 400
ACCENT_GREEN = (34, 197, 94)   # Green 500
ACCENT_AMBER = (245, 158, 11)  # Amber 500
ACCENT_RED = (239, 68, 68)     # Red 500

def create_base_canvas(width=1920, height=1080):
    img = Image.new("RGBA", (width, height), BG_DARK)
    
    # Ambient radial gradient glows
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([width * 0.35, -height * 0.2, width * 1.25, height * 0.8], fill=(0, 112, 243, 30))
    glow_draw.ellipse([width * 0.55, height * 0.1, width * 1.05, height * 0.7], fill=(0, 210, 255, 22))
    glow_draw.ellipse([-width * 0.1, height * 0.4, width * 0.4, height * 1.1], fill=(0, 112, 243, 18))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    img = Image.alpha_composite(img, glow)
    
    # Subtle technical background grid
    grid = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid)
    for x in range(0, width, 80):
        grid_draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 8), width=1)
    for y in range(0, height, 80):
        grid_draw.line([(0, y), (width, y)], fill=(255, 255, 255, 8), width=1)
    img = Image.alpha_composite(img, grid)
    return img

def draw_badge(draw, x, y, text, fill_color, border_color, text_color=(255, 255, 255), font_size=15):
    font = get_font(font_size, bold=True)
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    px, py = 14, 7
    rect = [x, y, x + tw + px * 2, y + th + py * 2]
    draw.rounded_rectangle(rect, radius=6, fill=fill_color, outline=border_color, width=1)
    draw.text((x + px, y + py - bbox[1]), text, fill=text_color, font=font)
    return rect[2]

def draw_card(canvas, box, radius=12, fill=BG_PANEL, outline=BORDER_BLUE, width=1):
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    return Image.alpha_composite(canvas, overlay)


# ==============================================================================
# 1. BUILD IMAGE A — CURRENT SIMULATION MODEL
# ==============================================================================
def build_image_a():
    print("Building Image A: current_gazebo_robot.png...")
    img = create_base_canvas(1920, 1080)
    draw = ImageDraw.Draw(img)
    
    # Header Section
    draw_badge(draw, 80, 50, "CURRENT SIMULATION MODEL", (0, 112, 243, 60), BORDER_CYAN, TEXT_CYAN, 14)
    draw_badge(draw, 345, 50, "ROS 2 HUMBLE • GAZEBO CLASSIC 11 • TRL 3–4", (15, 23, 42, 180), (71, 85, 105), TEXT_MUTED, 13)
    
    draw.text((80, 88), "NEXUSDELIVERY — Robot Architecture & URDF Model", fill=TEXT_WHITE, font=get_font(34, bold=True))
    draw.text((80, 135), "Empirical ODE physics model in small_city_dynamic.world (Zero LiDAR • Zero GPS Paradigm)", fill=TEXT_MUTED, font=get_font(17))

    # Center Robot Showcase Frame
    robot_src_path = os.path.join(BASE_DIR, "assets/robot/nexus_delivery_robot.png")
    if os.path.exists(robot_src_path):
        robot_img = Image.open(robot_src_path).convert("RGBA")
        # Crop or scale nicely to center
        # Let's frame the robot in a high-tech glass card
        robot_box = [80, 180, 1260, 890]
        img = draw_card(img, robot_box, radius=16, fill=(10, 16, 30, 240), outline=(30, 58, 95), width=2)
        
        # Resize robot maintaining aspect ratio
        target_w = 1140
        target_h = int(robot_img.height * (target_w / robot_img.width))
        if target_h > 670:
            target_h = 670
            target_w = int(robot_img.width * (target_h / robot_img.height))
        robot_resized = robot_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        rx = robot_box[0] + (robot_box[2] - robot_box[0] - target_w) // 2
        ry = robot_box[1] + (robot_box[3] - robot_box[1] - target_h) // 2
        img.paste(robot_resized, (rx, ry), robot_resized)
        
        draw = ImageDraw.Draw(img)
        # Technical callout tags inside robot frame
        draw_badge(draw, robot_box[0] + 25, robot_box[1] + 25, "GROUND-TRUTH SIMULATION GEOMETRY", (0, 0, 0, 180), (30, 58, 95), TEXT_MUTED, 12)
        draw.text((robot_box[0] + 25, robot_box[3] - 40), "Differential-Drive Chassis (0.82m × 0.62m, 22 kg) • Front Stereo IR RealSense D435i Model", fill=TEXT_MUTED, font=get_font(13))

    # Right Specifications Sidebar Card
    sidebar_box = [1300, 180, 1840, 890]
    img = draw_card(img, sidebar_box, radius=16, fill=(13, 22, 42, 240), outline=BORDER_BLUE, width=1)
    draw = ImageDraw.Draw(img)
    
    sx = sidebar_box[0] + 30
    sy = sidebar_box[1] + 30
    draw.text((sx, sy), "URDF Mechanical Architecture", fill=BORDER_CYAN, font=get_font(20, bold=True))
    draw.line([(sx, sy + 32), (sidebar_box[2] - 30, sy + 32)], fill=(30, 58, 95), width=1)
    
    specs = [
        ("Platform Dimensions", "0.82 m (L) × 0.62 m (W) × 0.22 m (H)"),
        ("Total Chassis Mass", "22.0 kg ODE rigid body, CoG at -0.03m"),
        ("Drive Configuration", "2-Wheel Differential Drive (Front Active)"),
        ("Drive Wheels", "Ø 0.40 m (R=0.20m), Track Width 0.72 m"),
        ("Stabilization", "2x Continuous Rear Passive Wheels"),
        ("Perception Sensor", "Intel RealSense D435i Active IR RGB-D"),
        ("Camera Mounting", "Front fascia, z = +0.42 m above ground"),
        ("Camera Resolution", "640 × 480 @ 30 FPS Depth / RGB"),
        ("Top Cargo Hatch", "Motorized 60.1° (1.05 rad) revolute hinge"),
        ("Cargo Elevator", "Prismatic vertical lift carriage (0.12m)"),
        ("Safety Features", "Rear E-Stop switch + Amber beacon mast"),
        ("Runtime Constraints", "Strict Zero LiDAR • Strict Zero GPS"),
    ]
    
    cur_y = sy + 48
    for label, val in specs:
        draw.text((sx, cur_y), label.upper(), fill=TEXT_CYAN, font=get_font(11, bold=True))
        draw.text((sx, cur_y + 16), val, fill=TEXT_WHITE, font=get_font(13))
        cur_y += 43
        
    # Bottom Verified Empirical Banner
    bar_box = [80, 920, 1840, 1020]
    img = draw_card(img, bar_box, radius=12, fill=(10, 18, 32, 240), outline=(34, 197, 94, 120), width=1)
    draw = ImageDraw.Draw(img)
    
    draw_badge(draw, 105, 938, "BENCHMARK RESULTS", (34, 197, 94, 40), ACCENT_GREEN, ACCENT_GREEN, 13)
    draw.text((285, 940), "112.21 m Path Completed with 0 Collisions in small_city_dynamic.world", fill=TEXT_WHITE, font=get_font(16, bold=True))
    draw.text((285, 970), "Curvature-Adaptive Pure Pursuit • Ground Plane Filter • 120/120 Automated Tests Passed (100%)", fill=TEXT_MUTED, font=get_font(13))
    
    out_path = os.path.join(ASSETS_DIR, "current_gazebo_robot.png")
    img.save(out_path, format="PNG")
    print(f"Image A saved successfully: {out_path}")


# ==============================================================================
# 2. BUILD IMAGE B — FUTURE PHYSICAL PROTOTYPE CONCEPT
# ==============================================================================
def build_image_b():
    print("Building Image B: future_physical_robot_concept.png...")
    img = create_base_canvas(1920, 1080)
    draw = ImageDraw.Draw(img)
    
    # Header Section
    draw_badge(draw, 80, 50, "FUTURE PHYSICAL PROTOTYPE CONCEPT", (147, 51, 234, 60), BORDER_PURPLE, (216, 180, 254), 14)
    draw_badge(draw, 420, 50, "PROPOSED INDUSTRIAL MECHATRONIC EVOLUTION • TRL 3-4 FOUNDATION", (15, 23, 42, 180), (71, 85, 105), TEXT_MUTED, 13)
    
    draw.text((80, 88), "NEXUSDELIVERY — Industrial Product Concept & Roadmap", fill=TEXT_WHITE, font=get_font(34, bold=True))
    draw.text((80, 135), "Proposed manufacturable design based on proven simulation architecture (Strict Zero LiDAR • Zero GPS)", fill=TEXT_MUTED, font=get_font(17))

    # Center Concept Render Showcase Frame
    concept_src_path = os.path.join(ASSETS_DIR, "future_physical_robot_concept.png")
    if os.path.exists(concept_src_path):
        concept_img = Image.open(concept_src_path).convert("RGBA")
        concept_box = [80, 180, 1260, 890]
        img = draw_card(img, concept_box, radius=16, fill=(10, 16, 30, 240), outline=BORDER_PURPLE, width=2)
        
        target_w = 1140
        target_h = int(concept_img.height * (target_w / concept_img.width))
        if target_h > 670:
            target_h = 670
            target_w = int(concept_img.width * (target_h / concept_img.height))
        concept_resized = concept_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        cx = concept_box[0] + (concept_box[2] - concept_box[0] - target_w) // 2
        cy = concept_box[1] + (concept_box[3] - concept_box[1] - target_h) // 2
        img.paste(concept_resized, (cx, cy), concept_resized)
        
        draw = ImageDraw.Draw(img)
        draw_badge(draw, concept_box[0] + 25, concept_box[1] + 25, "INDUSTRIAL PRODUCT VISUALIZATION", (0, 0, 0, 180), BORDER_PURPLE, (216, 180, 254), 12)
        draw.text((concept_box[0] + 25, concept_box[3] - 40), "Satin Pearl White Molded Enclosure • Recessed Optical Depth Visor • Integrated Rugged Drive Hubs", fill=TEXT_MUTED, font=get_font(13))

    # Right Specifications Sidebar Card
    sidebar_box = [1300, 180, 1840, 890]
    img = draw_card(img, sidebar_box, radius=16, fill=(16, 20, 38, 240), outline=BORDER_PURPLE, width=1)
    draw = ImageDraw.Draw(img)
    
    sx = sidebar_box[0] + 30
    sy = sidebar_box[1] + 30
    draw.text((sx, sy), "Target Mechatronic Specifications", fill=(216, 180, 254), font=get_font(20, bold=True))
    draw.line([(sx, sy + 32), (sidebar_box[2] - 30, sy + 32)], fill=(45, 30, 75), width=1)
    
    future_specs = [
        ("Exterior Enclosure", "IP65 molded polycarbonate / composite shell"),
        ("Drive System", "Dual 24V 250W geared brushless hub motors"),
        ("Traction Wheels", "8\" puncture-proof rugged off-road rubber"),
        ("Optical Visor", "Hydrophobic anti-glare glass with heating"),
        ("Perception Enclosure", "Front RealSense D435i module flush mount"),
        ("Compute Core", "Raspberry Pi 5 (8GB) + Hailo-8L M.2 NPU"),
        ("Energy Storage", "25.6V 20Ah LiFePO4 battery pack (512 Wh)"),
        ("Battery Management", "Smart BMS over CAN bus / telemetry link"),
        ("Hatch Actuation", "12V linear actuator with dual deadbolt latch"),
        ("Customer Interface", "Capacitive RFID/NFC & dynamic OTP unlock"),
        ("Active Safety", "High-visibility LED DRLs & amber strobe mast"),
        ("Architectural Integrity", "Strict Zero LiDAR & Zero GPS preservation"),
    ]
    
    cur_y = sy + 48
    for label, val in future_specs:
        draw.text((sx, cur_y), label.upper(), fill=(192, 132, 252), font=get_font(11, bold=True))
        draw.text((sx, cur_y + 16), val, fill=TEXT_WHITE, font=get_font(13))
        cur_y += 43
        
    # Bottom Disclaimer Banner
    bar_box = [80, 920, 1840, 1020]
    img = draw_card(img, bar_box, radius=12, fill=(10, 18, 32, 240), outline=(245, 158, 11, 140), width=1)
    draw = ImageDraw.Draw(img)
    
    draw_badge(draw, 105, 938, "DESIGN DISCLAIMER", (245, 158, 11, 40), ACCENT_AMBER, ACCENT_AMBER, 13)
    draw.text((280, 940), "Proposed Physical Evolution Concept — Not Currently Installed Hardware", fill=TEXT_WHITE, font=get_font(16, bold=True))
    draw.text((280, 970), "All visual enhancements represent engineering targets validated by the functional TRL 3–4 simulation baseline.", fill=TEXT_MUTED, font=get_font(13))
    
    out_path = os.path.join(ASSETS_DIR, "future_physical_robot_concept.png")
    img.save(out_path, format="PNG")
    print(f"Image B saved successfully: {out_path}")


# ==============================================================================
# 3. BUILD LINKEDIN HERO IMAGE (NEXUSDELIVERY Flagship Banner)
# ==============================================================================
def build_linkedin_hero():
    print("Building LinkedIn Hero: nexora_linkedin_hero.png & nexusdelivery_linkedin_hero.png...")
    img = create_base_canvas(1920, 1080)
    draw = ImageDraw.Draw(img)
    
    # --------------------------------------------------------------------------
    # TOP HEADER
    # --------------------------------------------------------------------------
    # Title & Branding
    draw.text((80, 48), "NEXUSDELIVERY", fill=BORDER_CYAN, font=get_font(42, bold=True))
    draw.text((505, 52), "•", fill=(50, 75, 115), font=get_font(36, bold=True))
    draw.text((535, 58), "Camera-Based Autonomous Sidewalk Delivery Robot", fill=TEXT_WHITE, font=get_font(24, bold=True))
    
    draw_badge(draw, 1520, 56, "TRL 3–4 SIMULATION POC", (0, 112, 243, 50), BORDER_CYAN, TEXT_CYAN, 13)
    draw_badge(draw, 1750, 56, "ZERO LiDAR / GPS", (15, 23, 42, 200), (71, 85, 105), TEXT_MUTED, 13)
    
    draw.text((80, 106), "Chiheb Robotics Systems Lab  |  Lead Systems Architect: Chiheb-bt  |  ROS 2 Humble & Gazebo Classic", fill=TEXT_MUTED, font=get_font(15))
    draw.line([(80, 136), (1840, 136)], fill=(25, 45, 75), width=1)

    # --------------------------------------------------------------------------
    # LEFT COLUMN: 4 TECHNICAL HIGHLIGHTS CARDS
    # --------------------------------------------------------------------------
    left_x = 80
    left_w = 460
    cards_data = [
        ("COMPUTER VISION", "Active IR Stereo RGB-D Depth Corridor Filtering (RealSense D435i model @ 30 FPS) with dynamic pedestrian distance & TTC tracking.", BORDER_CYAN),
        ("AUTONOMOUS NAVIGATION", "Curvature-Adaptive Pure Pursuit Trajectory Follower with Liang-Barsky corridor safety boundaries & ground plane filtering.", (56, 189, 248)),
        ("ROS 2 & GAZEBO PHYSICS", "Real-time computational node graph, 1000 Hz ODE contact solver, revolute cargo hatch actuation & telemetry bridge.", BORDER_BLUE),
        ("SECURE CARGO HANDOVER", "Cryptographic HMAC-SHA256 6-digit OTP delivery verification & motorized 60.1° hatch unlocking at customer doorstep.", (147, 51, 234)),
    ]
    
    card_y = 158
    card_h = 108
    gap = 14
    for title, desc, border_col in cards_data:
        box = [left_x, card_y, left_x + left_w, card_y + card_h]
        img = draw_card(img, box, radius=10, fill=(12, 19, 35, 230), outline=border_col, width=1)
        draw = ImageDraw.Draw(img)
        
        # Cyan indicator pip
        draw.ellipse([left_x + 20, card_y + 18, left_x + 28, card_y + 26], fill=border_col)
        draw.text((left_x + 36, card_y + 14), title, fill=TEXT_WHITE, font=get_font(13, bold=True))
        
        # Word wrap description
        words = desc.split()
        lines = []
        cur_line = []
        for w in words:
            cur_line.append(w)
            tw = get_font(11).getlength(" ".join(cur_line))
            if tw > left_w - 40:
                cur_line.pop()
                lines.append(" ".join(cur_line))
                cur_line = [w]
        if cur_line:
            lines.append(" ".join(cur_line))
            
        ly = card_y + 40
        for l in lines[:3]:
            draw.text((left_x + 20, ly), l, fill=TEXT_MUTED, font=get_font(11))
            ly += 16
            
        card_y += card_h + gap

    # --------------------------------------------------------------------------
    # CENTER / RIGHT: LARGE HERO ROBOT SHOWCASE
    # --------------------------------------------------------------------------
    hero_box = [left_x + left_w + 24, 158, 1840, 646]
    img = draw_card(img, hero_box, radius=14, fill=(10, 16, 28, 240), outline=(28, 48, 80), width=1)
    
    # Load and place future physical robot concept inside hero frame
    concept_path = os.path.join(BASE_DIR, "assets/presentation/future_physical_robot_concept.png")
    if os.path.exists(concept_path):
        concept_img = Image.open(concept_path).convert("RGBA")
        hw = hero_box[2] - hero_box[0] - 20
        hh = hero_box[3] - hero_box[1] - 20
        # Resize to fill hero card nicely
        target_h = hh
        target_w = int(concept_img.width * (target_h / concept_img.height))
        if target_w > hw:
            target_w = hw
            target_h = int(concept_img.height * (target_w / concept_img.width))
        c_res = concept_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        px = hero_box[0] + (hw + 20 - target_w) // 2
        py = hero_box[1] + (hh + 20 - target_h) // 2
        img.paste(c_res, (px, py), c_res)

    draw = ImageDraw.Draw(img)
    draw_badge(draw, hero_box[0] + 25, hero_box[1] + 22, "PROPOSED PHYSICAL PROTOTYPE CONCEPT", (0, 0, 0, 190), BORDER_CYAN, TEXT_CYAN, 12)
    draw.text((hero_box[0] + 25, hero_box[3] - 32), "Satin Pearl White Composite Enclosure • Recessed Optical Visor • In-Hub Drive Motors • Flush 60° Top Hatch", fill=TEXT_MUTED, font=get_font(12))

    # --------------------------------------------------------------------------
    # LOWER TRI-PANEL: 3 GENUINE PROJECT CAPTURES
    # --------------------------------------------------------------------------
    pan_y = 664
    pan_h = 270
    pan_w = 565
    gap_p = 22
    
    panels = [
        ("GAZEBO SIMULATION WORLD: TOP VIEW", "assets/simulation/gazebo_world_top_view.png", "112.21 m Measured Sidewalk Delivery Route (small_city_dynamic.world)", 80),
        ("GAZEBO PERSPECTIVE VIEW: PEDESTRIAN STREET", "assets/simulation/gazebo_world_perspective.png", "Urban Sidewalks, Buildings, Animated Pedestrians & Traffic Lights", 80 + pan_w + gap_p),
        ("CUSTOMER DELIVERY APP & FLEET COCKPIT", "assets/website/customer_portal_preview.png", "Interactive Sidewalk Pin Dropper, Order Dispatch & Live Telemetry HUD", 80 + (pan_w + gap_p) * 2),
    ]
    
    for title, rel_path, caption, px in panels:
        p_box = [px, pan_y, px + pan_w, pan_y + pan_h]
        img = draw_card(img, p_box, radius=10, fill=(10, 16, 28, 240), outline=(30, 52, 85), width=1)
        
        full_path = os.path.join(BASE_DIR, rel_path)
        if os.path.exists(full_path):
            cap_img = Image.open(full_path).convert("RGBA")
            # Inner crop/fit for thumbnail
            tw = pan_w - 16
            th = pan_h - 60
            
            # center crop to match aspect ratio
            aspect_target = tw / th
            aspect_src = cap_img.width / cap_img.height
            if aspect_src > aspect_target:
                new_w = int(cap_img.height * aspect_target)
                offset = (cap_img.width - new_w) // 2
                cropped = cap_img.crop((offset, 0, offset + new_w, cap_img.height))
            else:
                new_h = int(cap_img.width / aspect_target)
                offset = (cap_img.height - new_h) // 2
                cropped = cap_img.crop((0, offset, cap_img.width, offset + new_h))
                
            c_thumb = cropped.resize((tw, th), Image.Resampling.LANCZOS)
            img.paste(c_thumb, (px + 8, pan_y + 30), c_thumb)
            
        draw = ImageDraw.Draw(img)
        draw.text((px + 14, pan_y + 10), title, fill=TEXT_CYAN, font=get_font(11, bold=True))
        draw.text((px + 14, pan_y + pan_h - 22), caption, fill=TEXT_MUTED, font=get_font(10))

    # --------------------------------------------------------------------------
    # BOTTOM TECH STACK & METRICS BAR
    # --------------------------------------------------------------------------
    bot_box = [80, 954, 1840, 1030]
    img = draw_card(img, bot_box, radius=10, fill=(10, 16, 28, 250), outline=BORDER_BLUE, width=1)
    draw = ImageDraw.Draw(img)
    
    draw.text((105, 968), "TECHNOLOGY STACK:", fill=TEXT_CYAN, font=get_font(12, bold=True))
    draw.text((260, 968), "Python 3.10  •  ROS 2 Humble  •  Gazebo Classic 11  •  OpenCV  •  SQLite3  •  REST APIs", fill=TEXT_WHITE, font=get_font(13))
    
    draw.text((105, 994), "EMPIRICAL METRICS:", fill=TEXT_CYAN, font=get_font(12, bold=True))
    draw.text((260, 994), "120 / 120 Tests Passed (100%)  •  0 Collisions (112.21m path)  •  320×240 → 640×480 RealSense  •  Zero LiDAR / Zero GPS", fill=TEXT_MUTED, font=get_font(13))
    
    # Save both nexora_linkedin_hero.png (matching prompt prompt 6) and nexusdelivery_linkedin_hero.png
    hero_p1 = os.path.join(ASSETS_DIR, "nexora_linkedin_hero.png")
    hero_p2 = os.path.join(ASSETS_DIR, "nexusdelivery_linkedin_hero.png")
    img.save(hero_p1, format="PNG")
    img.save(hero_p2, format="PNG")
    print(f"LinkedIn Hero saved to: {hero_p1} and {hero_p2}")

if __name__ == "__main__":
    build_image_a()
    build_image_b()
    build_linkedin_hero()
    print("ALL PRESENTATION ASSETS GENERATED SUCCESSFULLY!")
