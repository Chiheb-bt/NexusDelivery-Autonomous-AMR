"""Gazebo World Geospatial Mapping Engine for NexusDelivery.

Defines the authentic 2D geometric vector model of rdsim_gazebo/worlds/small_city_dynamic.world:
- Physical world boundaries: X in [-48.0, 112.0]m, Y in [-48.0, 48.0]m (15,360 m^2)
- Navigable street corridors, driving lanes, and sidewalk meshes
- Solid building footprint blocks (restricted no-go zones)
- Controlled intersections, crosswalks, and traffic light posts
- Indoor Central Logistics Depot and customer delivery stopping bays
- Forward and inverse affine coordinate transformation between Gazebo metric space and screen space
"""

import math
from typing import Dict, List, Optional, Tuple

from delivery_robot_sim.route_planner import (
    CITY_BOUNDS,
    DEPOT_BOUNDS,
    DEPOT_DOCK_XY,
    DEPOT_DOOR_XY,
    BUILDING_BLOCKS,
    STREET_CORRIDORS,
    INTERSECTIONS,
    CUSTOMER_STOPPING_BAYS,
    validate_and_snap_destination,
    plan_city_route,
)

# World Metric Limits
WORLD_X_MIN = CITY_BOUNDS['min_x']  # -48.0
WORLD_X_MAX = CITY_BOUNDS['max_x']  # 112.0
WORLD_Y_MIN = CITY_BOUNDS['min_y']  # -48.0
WORLD_Y_MAX = CITY_BOUNDS['max_y']  # 48.0
WORLD_WIDTH_M = WORLD_X_MAX - WORLD_X_MIN   # 160.0
WORLD_HEIGHT_M = WORLD_Y_MAX - WORLD_Y_MIN  # 96.0

# Road & Sidewalk Dimensions
ROAD_WIDTH_M = 7.0
SIDEWALK_WIDTH_M = 2.0


def gazebo_to_screen(
    x_g: float, y_g: float,
    canvas_w: float, canvas_h: float,
    margin: float = 30.0
) -> Tuple[float, float]:
    """Convert Gazebo metric point (x_g, y_g) to 2D canvas screen pixel coordinates (u, v)."""
    usable_w = canvas_w - (2 * margin)
    usable_h = canvas_h - (2 * margin)

    scale_x = usable_w / WORLD_WIDTH_M
    scale_y = usable_h / WORLD_HEIGHT_M
    scale = min(scale_x, scale_y)

    # Center map within available canvas aspect ratio
    offset_x = margin + (usable_w - (WORLD_WIDTH_M * scale)) / 2.0
    offset_y = margin + (usable_h - (WORLD_HEIGHT_M * scale)) / 2.0

    u = offset_x + (x_g - WORLD_X_MIN) * scale
    v = offset_y + (WORLD_Y_MAX - y_g) * scale  # Invert Y for screen coordinates
    return round(u, 2), round(v, 2)


def screen_to_gazebo(
    u: float, v: float,
    canvas_w: float, canvas_h: float,
    margin: float = 30.0
) -> Tuple[float, float]:
    """Convert 2D canvas screen pixel coordinates (u, v) back to Gazebo metric point (x_g, y_g)."""
    usable_w = canvas_w - (2 * margin)
    usable_h = canvas_h - (2 * margin)

    scale_x = usable_w / WORLD_WIDTH_M
    scale_y = usable_h / WORLD_HEIGHT_M
    scale = min(scale_x, scale_y)

    offset_x = margin + (usable_w - (WORLD_WIDTH_M * scale)) / 2.0
    offset_y = margin + (usable_h - (WORLD_HEIGHT_M * scale)) / 2.0

    x_g = WORLD_X_MIN + (u - offset_x) / scale
    y_g = WORLD_Y_MAX - (v - offset_y) / scale
    return round(x_g, 2), round(y_g, 2)


def get_gazebo_world_manifest() -> Dict:
    """Return complete structured geometric manifest of the Gazebo simulation world."""
    buildings = []
    for name, min_x, max_x, min_y, max_y in BUILDING_BLOCKS:
        buildings.append({
            'name': name,
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y,
            'width_m': round(max_x - min_x, 2),
            'height_m': round(max_y - min_y, 2),
            'center_x': round((min_x + max_x) / 2.0, 2),
            'center_y': round((min_y + max_y) / 2.0, 2),
            'type': 'DEPOT_COMPOUND' if name.startswith('Depot') else 'BUILDING_BLOCK'
        })

    roads = []
    for name, is_horiz, fixed, v_min, v_max in STREET_CORRIDORS:
        if is_horiz:
            roads.append({
                'name': name,
                'orientation': 'HORIZONTAL',
                'fixed_y': fixed,
                'min_x': v_min,
                'max_x': v_max,
                'width_m': ROAD_WIDTH_M
            })
        else:
            roads.append({
                'name': name,
                'orientation': 'VERTICAL',
                'fixed_x': fixed,
                'min_y': v_min,
                'max_y': v_max,
                'width_m': ROAD_WIDTH_M
            })

    intersections = []
    for name, (ix, iy) in INTERSECTIONS.items():
        intersections.append({
            'id': name,
            'x': ix,
            'y': iy,
            'has_traffic_light': (name == 'NORTH_AVE_CENTRAL')
        })

    bays = []
    for bay_id, b in CUSTOMER_STOPPING_BAYS.items():
        bays.append({
            'id': bay_id,
            'customer_name': b['customer_name'],
            'door_xy': list(b['door_xy']),
            'stopping_xy': list(b['stopping_xy']),
            'approach_heading': round(b['approach_heading'], 3),
            'approach_heading_deg': round(math.degrees(b['approach_heading']), 1),
            'corridor': b['corridor'],
            'side': b['side']
        })

    crosswalks = [
        {
            'id': 'depot_pedestrian_crosswalk',
            'name': 'Depot Zebra Crosswalk (Central Blvd)',
            'x': -26.5,
            'y_min': -2.8,
            'y_max': 2.8,
            'orientation': 'VERTICAL'
        },
        {
            'id': 'intersection_pedestrian_crosswalk',
            'name': 'North Ave Intersection Crosswalk',
            'y': 3.5,
            'x_min': -18.0,
            'x_max': -12.0,
            'orientation': 'HORIZONTAL'
        }
    ]

    landmarks = [
        {'id': 'depot_staff', 'name': 'Depot Logistics Dispatcher', 'x': -28.8, 'y': 4.5, 'type': 'PERSONNEL'},
        {'id': 'client_1_sophie', 'name': 'Sophie Laurent Doorstep', 'x': -9.8, 'y': 15.0, 'type': 'CUSTOMER'},
        {'id': 'client_2_marc', 'name': 'Marc Dubois Storefront', 'x': -9.8, 'y': 28.0, 'type': 'CUSTOMER'},
        {'id': 'pedestrian_bystander', 'name': 'Sidewalk Pedestrian', 'x': -20.0, 'y': 11.5, 'type': 'PEDESTRIAN'},
        {'id': 'depot_postbox', 'name': 'Depot Outgoing Postbox', 'x': -26.5, 'y': 5.0, 'type': 'INFRASTRUCTURE'},
        {'id': 'trash_bin_1', 'name': 'Curbside Trash Bin 1', 'x': -24.5, 'y': 5.0, 'type': 'INFRASTRUCTURE'},
        {'id': 'trash_bin_2', 'name': 'Curbside Trash Bin 2', 'x': -9.8, 'y': 13.5, 'type': 'INFRASTRUCTURE'},
        {'id': 'fire_hydrant', 'name': 'High-Pressure Fire Hydrant', 'x': -19.5, 'y': -4.5, 'type': 'SAFETY'},
        {'id': 'street_lamp_depot', 'name': 'Depot LED Street Lamp', 'x': -26.5, 'y': 4.6, 'type': 'LIGHTING'},
        {'id': 'street_lamp_north_ave', 'name': 'North Ave LED Street Lamp', 'x': -19.5, 'y': 9.0, 'type': 'LIGHTING'},
        {'id': 'stop_sign', 'name': 'Regulatory Stop Sign', 'x': -19.5, 'y': 4.5, 'type': 'TRAFFIC_CONTROL'},
    ]

    dynamic_actors = [
        {
            'id': 'pedestrian_depot_crossing',
            'name': 'Crossing Pedestrian (Depot Crosswalk)',
            'base_x': -26.5,
            'y_range': [-2.8, 2.8],
            'cycle_time_sec': 22.0
        }
    ]

    return {
        'world_name': 'small_city_dynamic.world',
        'title': 'Gazebo Classic 11 Simulation Urban Footprint',
        'bounds': {
            'min_x': WORLD_X_MIN,
            'max_x': WORLD_X_MAX,
            'min_y': WORLD_Y_MIN,
            'max_y': WORLD_Y_MAX,
            'width_m': WORLD_WIDTH_M,
            'height_m': WORLD_HEIGHT_M
        },
        'depot': {
            'name': 'Central Logistics Depot Hub',
            'bounds': DEPOT_BOUNDS,
            'dock_xy': list(DEPOT_DOCK_XY),
            'door_xy': list(DEPOT_DOOR_XY)
        },
        'buildings': buildings,
        'roads': roads,
        'intersections': intersections,
        'crosswalks': crosswalks,
        'landmarks': landmarks,
        'dynamic_actors': dynamic_actors,
        'bays': bays
    }


def compute_route_distance(waypoints: List[Tuple[float, float]], start_xy: Optional[Tuple[float, float]] = None) -> float:
    """Calculate total topological route distance in meters from start to end of waypoints."""
    if not waypoints:
        return 0.0
    pts = [start_xy] + list(waypoints) if start_xy else list(waypoints)
    total_m = 0.0
    for i in range(len(pts) - 1):
        total_m += math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
    return round(total_m, 2)


def estimate_eta_seconds(distance_m: float, avg_speed_mps: float = 0.8, turn_overhead_sec: float = 4.0) -> int:
    """Calculate realistic travel ETA in seconds based on robot kinematic speed and turns."""
    if distance_m <= 0.0:
        return 0
    travel_time = distance_m / max(0.2, avg_speed_mps)
    # Estimate ~1 turn per 20 meters
    estimated_turns = max(1, int(distance_m / 20.0))
    total_seconds = travel_time + (estimated_turns * turn_overhead_sec)
    return int(round(total_seconds))

