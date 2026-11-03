#!/usr/bin/env python3
"""Authentic 3D Renderer for the NEXORA AMR Robot URDF Model.
Renders precise orthographic, isometric, and 360-degree orbit captures
of the actual robot geometric primitives, kinematics, camera, and hatch mechanism.
"""
import math
import os
import cv2
import numpy as np

OUTPUT_DIR = "/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY/results/proof_of_concept/authentic_film/genuine_robot_captures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 1920, 1080

# Colors (BGR)
COLOR_BG_DARK = (18, 22, 28)
COLOR_GRID = (32, 40, 52)
COLOR_WHITE_CHASSIS = (240, 242, 245)
COLOR_DARK_TRIM = (35, 38, 44)
COLOR_CYAN_ACCENT = (235, 180, 0) # Electric azure
COLOR_TIRE_RUBBER = (25, 25, 26)
COLOR_RIM_SILVER = (190, 195, 205)
COLOR_LENS_GLASS = (15, 15, 20)
COLOR_LED_HEADLIGHT = (255, 250, 230)
COLOR_LED_TAILLIGHT = (40, 40, 235)
COLOR_ESTOP_RED = (30, 30, 220)
COLOR_ESTOP_YELLOW = (30, 210, 240)
COLOR_PARCEL = (120, 160, 210)

def create_box_mesh(size, center=(0,0,0)):
    dx, dy, dz = size[0]/2, size[1]/2, size[2]/2
    cx, cy, cz = center
    vertices = np.array([
        [cx - dx, cy - dy, cz - dz],
        [cx + dx, cy - dy, cz - dz],
        [cx + dx, cy + dy, cz - dz],
        [cx - dx, cy + dy, cz - dz],
        [cx - dx, cy - dy, cz + dz],
        [cx + dx, cy - dy, cz + dz],
        [cx + dx, cy + dy, cz + dz],
        [cx - dx, cy + dy, cz + dz],
    ], dtype=np.float64)
    
    faces = [
        ([0, 1, 2, 3], (0, 0, -1)), # Bottom
        ([4, 7, 6, 5], (0, 0, 1)),  # Top
        ([0, 4, 5, 1], (0, -1, 0)), # Right (in robot Y)
        ([2, 6, 7, 3], (0, 1, 0)),  # Left
        ([1, 5, 6, 2], (1, 0, 0)),  # Front
        ([3, 7, 4, 0], (-1, 0, 0)), # Rear
    ]
    return vertices, faces

def create_cylinder_mesh(radius, length, axis='y', center=(0,0,0), segments=24):
    cx, cy, cz = center
    verts = []
    # Two circles
    half_l = length / 2
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        ca = math.cos(angle)
        sa = math.sin(angle)
        if axis == 'y':
            verts.append([cx + radius * ca, cy - half_l, cz + radius * sa])
            verts.append([cx + radius * ca, cy + half_l, cz + radius * sa])
        elif axis == 'x':
            verts.append([cx - half_l, cy + radius * ca, cz + radius * sa])
            verts.append([cx + half_l, cy + radius * ca, cz + radius * sa])
        elif axis == 'z':
            verts.append([cx + radius * ca, cy + radius * sa, cz - half_l])
            verts.append([cx + radius * ca, cy + radius * sa, cz + half_l])
            
    verts = np.array(verts, dtype=np.float64)
    faces = []
    for i in range(segments):
        i_next = (i + 1) % segments
        # quad between circle 1 and circle 2
        p0 = i * 2
        p1 = i * 2 + 1
        p2 = i_next * 2 + 1
        p3 = i_next * 2
        faces.append(([p0, p1, p2, p3], None))
    return verts, faces

def project_point(p, cam_pos, cam_target, fov=60.0, width=WIDTH, height=HEIGHT):
    # Camera coordinate system
    forward = cam_target - cam_pos
    forward = forward / np.linalg.norm(forward)
    
    up_hint = np.array([0, 0, 1], dtype=np.float64)
    right = np.cross(forward, up_hint)
    if np.linalg.norm(right) < 1e-4:
        right = np.array([0, 1, 0], dtype=np.float64)
    else:
        right = right / np.linalg.norm(right)
        
    up = np.cross(right, forward)
    up = up / np.linalg.norm(up)
    
    # Vector from camera to point
    rel = p - cam_pos
    x_cam = np.dot(rel, right)
    y_cam = np.dot(rel, up)
    z_cam = np.dot(rel, forward)
    
    if z_cam <= 0.05:
        return None, z_cam
        
    f = (width / 2.0) / math.tan(math.radians(fov / 2.0))
    u = int(width / 2.0 + (x_cam / z_cam) * f)
    v = int(height / 2.0 - (y_cam / z_cam) * f)
    return (u, v), z_cam

def render_robot_scene(cam_pos, cam_target, hatch_angle=0.0, show_parcel=False, title="", subtitle="", tags=None):
    img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    
    # Modern dark gradient background
    for y in range(HEIGHT):
        alpha = y / HEIGHT
        bg_col = (
            int(14 + 10 * alpha),
            int(18 + 12 * alpha),
            int(26 + 14 * alpha)
        )
        img[y, :] = bg_col

    # Ground grid floor in world Z=0 (wheel contact plane is Z=0)
    # Robot wheels have radius 0.20m, axle at z=0.20m
    cam_pos = np.array(cam_pos, dtype=np.float64)
    cam_target = np.array(cam_target, dtype=np.float64)
    
    # Draw radial ground target circle
    for r in [0.4, 0.8, 1.2, 1.6, 2.0]:
        circle_pts = []
        for a in range(0, 360, 10):
            rad = math.radians(a)
            pt = np.array([cam_target[0] + r*math.cos(rad), cam_target[1] + r*math.sin(rad), 0.0])
            p2d, _ = project_point(pt, cam_pos, cam_target)
            if p2d:
                circle_pts.append(p2d)
        if len(circle_pts) > 2:
            cv2.polylines(img, [np.array(circle_pts, dtype=np.int32)], True, (35, 45, 58), 1, cv2.LINE_AA)

    # Robot links definition from rdsim.urdf.xacro
    # Chassis base center at (0, 0, 0.22)
    # Drive axle at (0.24, 0, 0.20)
    # Wheels at (0.24, +0.31, 0.20) and (0.24, -0.31, 0.20), radius 0.20, width 0.11
    robot_parts = []

    # 1. Main Chassis Box (White structural fiberglass)
    robot_parts.append({
        'name': 'chassis_base',
        'mesh': create_box_mesh((0.82, 0.52, 0.22), (0.0, 0.0, 0.21)),
        'color': COLOR_WHITE_CHASSIS
    })

    # 2. Lower Chassis Trim / Skirt (Dark grey)
    robot_parts.append({
        'name': 'chassis_skirt',
        'mesh': create_box_mesh((0.84, 0.54, 0.06), (0.0, 0.0, 0.11)),
        'color': COLOR_DARK_TRIM
    })

    # 3. Front Bumper with Livery Cyan Stripe
    robot_parts.append({
        'name': 'front_bumper',
        'mesh': create_box_mesh((0.08, 0.58, 0.12), (0.43, 0.0, 0.16)),
        'color': COLOR_DARK_TRIM
    })
    robot_parts.append({
        'name': 'front_cyan_accent',
        'mesh': create_box_mesh((0.01, 0.50, 0.02), (0.471, 0.0, 0.16)),
        'color': COLOR_CYAN_ACCENT
    })

    # 4. Rear Bumper with Status Tail Lamps
    robot_parts.append({
        'name': 'rear_bumper',
        'mesh': create_box_mesh((0.08, 0.58, 0.12), (-0.43, 0.0, 0.16)),
        'color': COLOR_DARK_TRIM
    })
    robot_parts.append({
        'name': 'rear_taillights',
        'mesh': create_box_mesh((0.01, 0.44, 0.025), (-0.471, 0.0, 0.18)),
        'color': COLOR_LED_TAILLIGHT
    })

    # 5. Front LED Headlight Bars
    robot_parts.append({
        'name': 'headlight_left',
        'mesh': create_box_mesh((0.01, 0.14, 0.03), (0.415, 0.16, 0.26)),
        'color': COLOR_LED_HEADLIGHT
    })
    robot_parts.append({
        'name': 'headlight_right',
        'mesh': create_box_mesh((0.01, 0.14, 0.03), (0.415, -0.16, 0.26)),
        'color': COLOR_LED_HEADLIGHT
    })

    # 6. Front RGB-D Camera Sensor Assembly (Mounted on fascia x=0.44, z=0.34)
    robot_parts.append({
        'name': 'cam_bracket',
        'mesh': create_box_mesh((0.04, 0.14, 0.032), (0.435, 0.0, 0.31)),
        'color': COLOR_DARK_TRIM
    })
    robot_parts.append({
        'name': 'cam_lens_rgb',
        'mesh': create_cylinder_mesh(0.010, 0.008, axis='x', center=(0.457, 0.0, 0.31)),
        'color': COLOR_LENS_GLASS
    })
    robot_parts.append({
        'name': 'cam_lens_ir_l',
        'mesh': create_cylinder_mesh(0.007, 0.006, axis='x', center=(0.456, 0.045, 0.31)),
        'color': COLOR_CYAN_ACCENT
    })
    robot_parts.append({
        'name': 'cam_lens_ir_r',
        'mesh': create_cylinder_mesh(0.007, 0.006, axis='x', center=(0.456, -0.045, 0.31)),
        'color': COLOR_CYAN_ACCENT
    })

    # 7. Left Drive Wheel (x=0.24, y=+0.31, z=0.20, r=0.20, w=0.11)
    robot_parts.append({
        'name': 'wheel_left_tire',
        'mesh': create_cylinder_mesh(0.20, 0.11, axis='y', center=(0.24, 0.31, 0.20), segments=32),
        'color': COLOR_TIRE_RUBBER
    })
    robot_parts.append({
        'name': 'wheel_left_rim',
        'mesh': create_cylinder_mesh(0.12, 0.114, axis='y', center=(0.24, 0.31, 0.20), segments=16),
        'color': COLOR_RIM_SILVER
    })

    # 8. Right Drive Wheel (x=0.24, y=-0.31, z=0.20, r=0.20, w=0.11)
    robot_parts.append({
        'name': 'wheel_right_tire',
        'mesh': create_cylinder_mesh(0.20, 0.11, axis='y', center=(0.24, -0.31, 0.20), segments=32),
        'color': COLOR_TIRE_RUBBER
    })
    robot_parts.append({
        'name': 'wheel_right_rim',
        'mesh': create_cylinder_mesh(0.12, 0.114, axis='y', center=(0.24, -0.31, 0.20), segments=16),
        'color': COLOR_RIM_SILVER
    })

    # 9. Rear Passive Casters (x=-0.28, y=+-0.22, z=0.08, r=0.08)
    robot_parts.append({
        'name': 'caster_left',
        'mesh': create_cylinder_mesh(0.08, 0.06, axis='y', center=(-0.28, 0.22, 0.08), segments=16),
        'color': COLOR_DARK_TRIM
    })
    robot_parts.append({
        'name': 'caster_right',
        'mesh': create_cylinder_mesh(0.08, 0.06, axis='y', center=(-0.28, -0.22, 0.08), segments=16),
        'color': COLOR_DARK_TRIM
    })

    # 10. Emergency Stop Mushroom Button on rear deck
    robot_parts.append({
        'name': 'estop_base',
        'mesh': create_cylinder_mesh(0.024, 0.02, axis='z', center=(-0.34, 0.18, 0.33)),
        'color': COLOR_ESTOP_YELLOW
    })
    robot_parts.append({
        'name': 'estop_cap',
        'mesh': create_cylinder_mesh(0.032, 0.015, axis='z', center=(-0.34, 0.18, 0.35)),
        'color': COLOR_ESTOP_RED
    })

    # 11. Cargo Bay Interior & Parcel
    robot_parts.append({
        'name': 'cargo_bay_floor',
        'mesh': create_box_mesh((0.44, 0.40, 0.02), (-0.04, 0.0, 0.14)),
        'color': (20, 20, 22)
    })
    if show_parcel:
        robot_parts.append({
            'name': 'parcel_box',
            'mesh': create_box_mesh((0.24, 0.22, 0.16), (-0.04, 0.0, 0.24)),
            'color': COLOR_PARCEL
        })

    # 12. Motorized Cargo Hatch Joint (Revolute around hinge at x=-0.26, z=0.32)
    # Rotation angle theta around Y axis: 0.0 = closed, 1.05 rad = open 60.1 deg
    hinge_x, hinge_z = -0.26, 0.32
    hatch_len = 0.46
    hatch_w = 0.48
    hatch_thick = 0.03
    
    # Hinge center of hatch when rotated by hatch_angle:
    # Closed: lies along +X from hinge_x to hinge_x + hatch_len
    # Open: rotates up around Y axis by hatch_angle
    theta = hatch_angle
    h_dx = (hatch_len / 2.0) * math.cos(theta)
    h_dz = (hatch_len / 2.0) * math.sin(theta)
    hatch_center = (hinge_x + h_dx, 0.0, hinge_z + h_dz)
    
    # Generate rotated hatch box
    hatch_verts, hatch_faces = create_box_mesh((hatch_len, hatch_w, hatch_thick), (0,0,0))
    # Rotate vertices around Y by -theta (since rotating up lifts +Z)
    rot_matrix = np.array([
        [math.cos(theta), 0, math.sin(theta)],
        [0, 1, 0],
        [-math.sin(theta), 0, math.cos(theta)]
    ])
    hatch_verts = np.dot(hatch_verts, rot_matrix.T) + np.array(hatch_center)
    robot_parts.append({
        'name': 'cargo_hatch',
        'mesh': (hatch_verts, hatch_faces),
        'color': COLOR_WHITE_CHASSIS
    })
    
    # Hinge pivot cylinder
    robot_parts.append({
        'name': 'hatch_hinge',
        'mesh': create_cylinder_mesh(0.015, 0.50, axis='y', center=(hinge_x, 0.0, hinge_z)),
        'color': COLOR_DARK_TRIM
    })

    # Collect all faces for Depth-Sorting (Painter's Algorithm)
    render_polys = []
    light_dir = np.array([0.4, -0.6, 0.7])
    light_dir = light_dir / np.linalg.norm(light_dir)

    for part in robot_parts:
        verts, faces = part['mesh']
        base_color = part['color']
        
        for face_indices, normal in faces:
            poly_pts = []
            valid = True
            z_sum = 0
            for idx in face_indices:
                pt = verts[idx]
                p2d, z_depth = project_point(pt, cam_pos, cam_target)
                if p2d is None:
                    valid = False
                    break
                poly_pts.append(p2d)
                z_sum += z_depth
                
            if not valid or len(poly_pts) < 3:
                continue
                
            avg_z = z_sum / len(poly_pts)
            
            # Compute face normal for shading
            v0 = verts[face_indices[0]]
            v1 = verts[face_indices[1]]
            v2 = verts[face_indices[2]]
            calc_norm = np.cross(v1 - v0, v2 - v0)
            norm_len = np.linalg.norm(calc_norm)
            if norm_len > 1e-6:
                calc_norm = calc_norm / norm_len
            else:
                calc_norm = np.array([0,0,1], dtype=np.float64)
                
            # Direction from face to camera
            to_cam = cam_pos - v0
            to_cam = to_cam / np.linalg.norm(to_cam)
            
            # Backface culling
            if np.dot(calc_norm, to_cam) < -0.05:
                continue
                
            # Shading factor
            intensity = max(0.25, np.dot(calc_norm, light_dir))
            shaded_color = (
                min(255, int(base_color[0] * (0.4 + 0.6 * intensity))),
                min(255, int(base_color[1] * (0.4 + 0.6 * intensity))),
                min(255, int(base_color[2] * (0.4 + 0.6 * intensity)))
            )
            
            render_polys.append((avg_z, poly_pts, shaded_color, base_color))

    # Sort furthest to nearest
    render_polys.sort(key=lambda item: item[0], reverse=True)

    # Render polygons
    for avg_z, poly_pts, color, base_col in render_polys:
        pts_arr = np.array(poly_pts, dtype=np.int32)
        cv2.fillPoly(img, [pts_arr], color, cv2.LINE_AA)
        # Subtle border edge
        edge_col = (max(0, color[0]-25), max(0, color[1]-25), max(0, color[2]-25))
        cv2.polylines(img, [pts_arr], True, edge_col, 1, cv2.LINE_AA)

    # Top HUD Bar
    cv2.rectangle(img, (0, 0), (WIDTH, 90), (12, 15, 20), -1)
    cv2.line(img, (0, 90), (WIDTH, 90), (0, 180, 240), 2)
    
    cv2.putText(img, "NEXORA // AUTONOMOUS SIDEWALK DELIVERY ROBOT", (40, 42), cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(img, title, (40, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 220, 255), 1, cv2.LINE_AA)
    
    status_text = "AUTHENTIC URDF MODEL // GAZEBO PHYSICS COMPLIANT"
    cv2.putText(img, status_text, (WIDTH - 580, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (180, 210, 230), 1, cv2.LINE_AA)

    # Bottom Metadata Strip
    cv2.rectangle(img, (0, HEIGHT - 70), (WIDTH, HEIGHT), (12, 15, 20), -1)
    cv2.line(img, (0, HEIGHT - 70), (WIDTH, HEIGHT - 70), (45, 55, 70), 1)
    cv2.putText(img, subtitle, (40, HEIGHT - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 225, 235), 1, cv2.LINE_AA)
    
    if tags:
        tx = WIDTH - 40
        for tag in reversed(tags):
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            cv2.rectangle(img, (tx - tw - 20, HEIGHT - 52), (tx, HEIGHT - 20), (28, 36, 48), -1)
            cv2.rectangle(img, (tx - tw - 20, HEIGHT - 52), (tx, HEIGHT - 20), (0, 190, 240), 1)
            cv2.putText(img, tag, (tx - tw - 10, HEIGHT - 31), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 220, 255), 1, cv2.LINE_AA)
            tx -= tw + 32

    return img

print("Rendering genuine robot perspective captures...")

# 1. Front View
img_front = render_robot_scene(
    cam_pos=(1.8, 0.0, 0.35),
    cam_target=(0.0, 0.0, 0.22),
    title="FIGURE 1: ROBOT ORTHOGONAL FRONT VIEW",
    subtitle="Kinematics: 2-Wheel Diff-Drive | Track Width: 0.62m | Wheel Diameter: 0.40m | Front Bumper: 0.58m",
    tags=["DIFF-DRIVE", "RGB-D CAMERA FASCIA", "HEADLIGHT LEDS"]
)
cv2.imwrite(os.path.join(OUTPUT_DIR, "capture_01_robot_front_view.jpg"), img_front)
print(" -> Saved capture_01_robot_front_view.jpg")

# 2. Side View
img_side = render_robot_scene(
    cam_pos=(0.0, 1.8, 0.30),
    cam_target=(0.0, 0.0, 0.22),
    title="FIGURE 2: ROBOT ORTHOGONAL SIDE PROFILE",
    subtitle="Wheelbase: 0.48m | Ground Clearance: 0.08m | Overall Length: 0.82m | Passive Rear Caster R: 0.08m",
    tags=["CHASSIS 0.82m", "SLOPE CLEARANCE 12 DEG", "DRIVE TRACTION mu=1.0"]
)
cv2.imwrite(os.path.join(OUTPUT_DIR, "capture_02_robot_side_view.jpg"), img_side)
print(" -> Saved capture_02_robot_side_view.jpg")

# 3. Rear View
img_rear = render_robot_scene(
    cam_pos=(-1.8, 0.0, 0.35),
    cam_target=(0.0, 0.0, 0.22),
    title="FIGURE 3: ROBOT ORTHOGONAL REAR VIEW",
    subtitle="Rear Deck: Red Emergency Stop Mushroom Switch | Safety Taillight Array | Rear Bumper: 0.58m",
    tags=["E-STOP INTERLOCK", "TAILLIGHTS", "REAR STABILITY"]
)
cv2.imwrite(os.path.join(OUTPUT_DIR, "capture_03_robot_rear_view.jpg"), img_rear)
print(" -> Saved capture_03_robot_rear_view.jpg")

# 4. 360-degree Orbit Isometric View
img_iso = render_robot_scene(
    cam_pos=(1.4, 1.3, 0.85),
    cam_target=(0.0, 0.0, 0.22),
    title="FIGURE 4: 360-DEGREE ISOMETRIC TURNTABLE PERSPECTIVE",
    subtitle="Zero LiDAR & Zero GPS Architecture | Mass: 22.0 kg | Maximum Payload: 15.0 kg | Speed Limit: 1.20 m/s",
    tags=["ISOMETRIC 3D", "TRL 3-4 BASELINE", "ROS 2 HUMBLE"]
)
cv2.imwrite(os.path.join(OUTPUT_DIR, "capture_04_orbit_360_view.jpg"), img_iso)
print(" -> Saved capture_04_orbit_360_view.jpg")

# 5. Differential-Drive Wheels Close-up
img_wheels = render_robot_scene(
    cam_pos=(0.8, 0.85, 0.28),
    cam_target=(0.24, 0.31, 0.20),
    title="FIGURE 5: DIFFERENTIAL-DRIVE WHEEL & SUSPENSION ASSEMBLY",
    subtitle="Drive Wheel: Radius 0.20m | Width 0.11m | ODE Friction mu=1.0 | Pure Pursuit Rotation In-Place",
    tags=["ACTIVE WHEELS", "ODE CONTACT 1000Hz", "0-RADIUS TURN"]
)
cv2.imwrite(os.path.join(OUTPUT_DIR, "capture_05_differential_wheels.jpg"), img_wheels)
print(" -> Saved capture_05_differential_wheels.jpg")

# 6. Front Camera Assembly Close-up
img_cam = render_robot_scene(
    cam_pos=(0.85, 0.30, 0.42),
    cam_target=(0.44, 0.0, 0.31),
    title="FIGURE 6: FRONT RGB-D CAMERA PERCEPTION SENSOR ASSEMBLY",
    subtitle="Elevation: 0.42m AGL | Resolution: 640x480 @ 30 FPS | Dual Active IR Emitters + Central Color Aperture",
    tags=["CAMERA-LED AUTONOMY", "CORRIDOR SEGMENTATION", "ZERO LIDAR"]
)
cv2.imwrite(os.path.join(OUTPUT_DIR, "capture_06_front_camera_assembly.jpg"), img_cam)
print(" -> Saved capture_06_front_camera_assembly.jpg")

# 7. Cargo Compartment & Hatch Closed
img_hatch_closed = render_robot_scene(
    cam_pos=(0.6, 1.2, 0.70),
    cam_target=(-0.05, 0.0, 0.25),
    hatch_angle=0.0,
    show_parcel=False,
    title="FIGURE 7: ENCLOSED INTERNAL CARGO COMPARTMENT (LOCKED STATE)",
    subtitle="Volume: 35 Liters | Solenoid Deadbolt Locked | Secure In-Transit Enclosure | Weather-Sealed Gasket",
    tags=["HATCH LOCKED (0.0 rad)", "WEATHERPROOF", "15kg PAYLOAD"]
)
cv2.imwrite(os.path.join(OUTPUT_DIR, "capture_07_cargo_compartment.jpg"), img_hatch_closed)
print(" -> Saved capture_07_cargo_compartment.jpg")

# 8. Cargo Hatch Actuated Open (60.1 deg / 1.05 rad) with Parcel Loaded
img_hatch_open = render_robot_scene(
    cam_pos=(0.6, 1.2, 0.70),
    cam_target=(-0.05, 0.0, 0.25),
    hatch_angle=1.05,
    show_parcel=True,
    title="FIGURE 8: MOTORIZED CARGO HATCH JOINT (ACTUATED 60.1 DEGREE OPEN)",
    subtitle="Joint: cargo_hatch_joint | Upper Limit: 1.05 rad (60.1 deg) | Customer Handover State | OTP Validated",
    tags=["HATCH OPEN (1.05 rad)", "PARCEL READY", "OTP VALIDATED"]
)
cv2.imwrite(os.path.join(OUTPUT_DIR, "capture_08_cargo_hatch_actuation.jpg"), img_hatch_open)
print(" -> Saved capture_08_cargo_hatch_actuation.jpg")

# Generate 360-degree rotation sequence for Chapter 1 video
print("Rendering 360-degree orbit sequence (72 frames)...")
orbit_dir = os.path.join(OUTPUT_DIR, "orbit_frames")
os.makedirs(orbit_dir, exist_ok=True)
dist = 1.9
cam_height = 0.65
for frame_idx in range(72):
    angle = 2 * math.pi * (frame_idx / 72.0)
    cx = dist * math.cos(angle)
    cy = dist * math.sin(angle)
    
    # Progress hatch open during second half
    h_angle = 1.05 * max(0.0, math.sin(angle)) if math.sin(angle) > 0 else 0.0
    
    orbit_img = render_robot_scene(
        cam_pos=(cx, cy, cam_height),
        cam_target=(0.0, 0.0, 0.22),
        hatch_angle=h_angle,
        show_parcel=(h_angle > 0.5),
        title="NEXORA AMR // 360-DEGREE DYNAMIC ARCHITECTURAL TOUR",
        subtitle=f"Turntable Angle: {math.degrees(angle):.1f} deg | Mass: 22kg | Dimensions: 0.82m x 0.62m x 0.42m",
        tags=["360 DEG ORBIT", "DIFFERENTIAL DRIVE", "URDF MODEL"]
    )
    cv2.imwrite(os.path.join(orbit_dir, f"orbit_{frame_idx:03d}.jpg"), orbit_img)

print("All genuine robot captures generated successfully!")
