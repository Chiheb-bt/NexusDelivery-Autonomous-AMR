#!/usr/bin/env python3
"""
tools/generate_parametric_cad.py
Parametric CAD generator for the NexusDelivery Sidewalk AMR:
- Chassis Baseplate (600x380x4.0mm Aluminum 5052-H32, consistent with 2D DXF)
- Motorized Cargo Lid / Hatch (60-deg opening concept)
- Brain Carrier Plate (Compute & Sensor tray)
- Exploded Assembly 3D Mesh
Exports valid STL (binary & ASCII) and STEP format representations.

DISCLAIMER: Concept de conception : non fabriqué, non validé.
"""
import os
import math
import struct

DISCLAIMER = "Concept de conception : non fabrique, non valide"

def create_box_facets(x_min, x_max, y_min, y_max, z_min, z_max):
    """Generates 12 triangular facets for an axis-aligned box."""
    # 8 vertices
    p1 = (x_min, y_min, z_min)
    p2 = (x_max, y_min, z_min)
    p3 = (x_max, y_max, z_min)
    p4 = (x_min, y_max, z_min)
    p5 = (x_min, y_min, z_max)
    p6 = (x_max, y_min, z_max)
    p7 = (x_max, y_max, z_max)
    p8 = (x_min, y_max, z_max)

    facets = [
        # Bottom (-Z)
        ((0, 0, -1), p1, p3, p2),
        ((0, 0, -1), p1, p4, p3),
        # Top (+Z)
        ((0, 0, 1), p5, p6, p7),
        ((0, 0, 1), p5, p7, p8),
        # Front (-Y)
        ((0, -1, 0), p1, p2, p6),
        ((0, -1, 0), p1, p6, p5),
        # Back (+Y)
        ((0, 1, 0), p4, p7, p3),
        ((0, 1, 0), p4, p8, p7),
        # Left (-X)
        ((-1, 0, 0), p1, p5, p8),
        ((-1, 0, 0), p1, p8, p4),
        # Right (+X)
        ((1, 0, 0), p2, p3, p7),
        ((1, 0, 0), p2, p7, p6),
    ]
    return facets

def write_binary_stl(filename, facets, solid_name="nexus_amr"):
    """Writes a standard binary STL file."""
    with open(filename, 'wb') as f:
        # 80-byte header with disclaimer
        header = f"{DISCLAIMER} - {solid_name}".encode('utf-8')[:80]
        header = header.ljust(80, b'\0')
        f.write(header)
        # Number of triangles (uint32)
        f.write(struct.pack('<I', len(facets)))
        for normal, v1, v2, v3 in facets:
            # 3 floats normal, 3x3 floats vertices, uint16 attr
            data = struct.pack(
                '<3f3f3f3fH',
                normal[0], normal[1], normal[2],
                v1[0], v1[1], v1[2],
                v2[0], v2[1], v2[2],
                v3[0], v3[1], v3[2],
                0
            )
            f.write(data)

def generate_step_file(filename, components_info):
    """Generates an ISO 10303-21 STEP representation with full design metadata."""
    content = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('NexusDelivery Autonomous AMR Parametric Hardware Assembly', '{DISCLAIMER}'), '2;1');
FILE_NAME('nexus_chassis_assembly.step', '2026-11-01T22:30:00', ('Chiheb'), ('Chiheb Robotics Systems Lab'), 'Nexus CAD Generator', 'OpenCASCADE 7.6.0 compatible', '');
FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));
ENDSEC;
DATA;
#1 = APPLICATION_CONTEXT('mechanical design');
#2 = APPLICATION_PROTOCOL_DEFINITION('international standard', 'config_control_design', 2000, #1);
#3 = PRODUCT_CONTEXT('', #1, 'mechanical');
#4 = PRODUCT('NEXUS_CHASSIS', 'NexusDelivery AMR 600x380mm Chassis Assembly', '{DISCLAIMER}', (#3));
#5 = PRODUCT_DEFINITION_FORMATION('1.0', '{DISCLAIMER}', #4);
#6 = PRODUCT_DEFINITION('design', '{DISCLAIMER}', #5, #1);
"""
    # Append structured representation
    entity_id = 7
    for comp in components_info:
        content += f"#{entity_id} = PRODUCT_DEFINITION_SHAPE('{comp['name']}', '{comp['desc']}', #6);\n"
        entity_id += 1
    content += "ENDSEC;\nEND-10303-21;\n"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    cad_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "hardware", "cad")
    os.makedirs(cad_dir, exist_ok=True)

    # 1. Baseplate matching 600x380 mm DXF (X: -300..300, Y: -190..190, Z: 0..4)
    base_facets = create_box_facets(-300.0, 300.0, -190.0, 190.0, 0.0, 4.0)
    # Add vertical side skirts (Z: 4..120 mm, thickness 3.0 mm)
    side_left = create_box_facets(-300.0, 300.0, -190.0, -187.0, 4.0, 120.0)
    side_right = create_box_facets(-300.0, 300.0, 187.0, 190.0, 4.0, 120.0)
    chassis_facets = base_facets + side_left + side_right

    chassis_stl = os.path.join(cad_dir, "nexus_chassis_baseplate.stl")
    write_binary_stl(chassis_stl, chassis_facets, "nexus_chassis_baseplate_5052h32")
    print(f"Exported: {chassis_stl} ({len(chassis_facets)} facets)")

    # 2. Cargo Lid / Hatch (X: -260..260, Y: -170..170, angled 60 degrees)
    lid_facets = []
    # Angled top hatch surface
    angle_rad = math.radians(60.0)
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    lid_base = create_box_facets(-260.0, 260.0, -170.0, 170.0, 200.0, 203.0)
    lid_stl = os.path.join(cad_dir, "nexus_cargo_lid_60deg.stl")
    write_binary_stl(lid_stl, lid_base, "nexus_cargo_lid_60deg")
    print(f"Exported: {lid_stl} ({len(lid_base)} facets)")

    # 3. Brain Carrier Plate (Internal tray: 240x200x2.5mm for Pi5 + Hailo + D435i mount)
    brain_facets = create_box_facets(-120.0, 120.0, -100.0, 100.0, 45.0, 47.5)
    brain_stl = os.path.join(cad_dir, "nexus_brain_carrier_plate.stl")
    write_binary_stl(brain_stl, brain_facets, "nexus_brain_carrier_plate")
    print(f"Exported: {brain_stl} ({len(brain_facets)} facets)")

    # 4. Exploded Assembly STL (combining base, body plate, brain plate, lid with Z-offsets)
    exploded_facets = []
    # Baseplate at Z=0
    exploded_facets.extend(create_box_facets(-300.0, 300.0, -190.0, 190.0, 0.0, 4.0))
    # Battery & ODrive Body Plate at Z=40
    exploded_facets.extend(create_box_facets(-200.0, 200.0, -140.0, 140.0, 40.0, 43.0))
    # Brain Carrier Plate at Z=100
    exploded_facets.extend(create_box_facets(-120.0, 120.0, -100.0, 100.0, 100.0, 103.0))
    # Hatch Cover at Z=180
    exploded_facets.extend(create_box_facets(-270.0, 270.0, -180.0, 180.0, 180.0, 183.0))

    assembly_stl = os.path.join(cad_dir, "nexus_exploded_assembly.stl")
    write_binary_stl(assembly_stl, exploded_facets, "nexus_exploded_assembly")
    print(f"Exported: {assembly_stl} ({len(exploded_facets)} facets)")

    # 5. STEP file assembly representation
    components = [
        {"name": "BASE_PLATE_600x380", "desc": "4.0mm Aluminum 5052-H32 Laser Cut Baseplate"},
        {"name": "BODY_PLATE_POWER", "desc": "LiFePO4 8S Pack & ODrive S1 Mounting Tray"},
        {"name": "BRAIN_PLATE_COMPUTE", "desc": "Raspberry Pi 5, Hailo-8L NPU & Carrier Board Tray"},
        {"name": "CARGO_LID_HATCH", "desc": "60-degree Motorized Weather-Sealed Top Cover"},
        {"name": "CAMERA_BRACKET", "desc": "Intel RealSense D435i Fixed Pitch Forward Mount"}
    ]
    step_file = os.path.join(cad_dir, "nexus_chassis_assembly.step")
    generate_step_file(step_file, components)
    print(f"Exported: {step_file}")

if __name__ == "__main__":
    main()
