"""Topological road network graph, A* routing, and reachability validator for small_city.

Enables the autonomous delivery robot to navigate across the entire city grid:
- Central Boulevard (y = 0.0, from x = -28.0 to x = +108.0, with legal lane y = -0.75)
- North/Central Avenue (x = -15.0, from y = -45.0 to y = +45.0)
- West Boulevard (x = -45.0, from y = -45.0 to y = +45.0)
- East Avenue (x = 45.0, from y = -45.0 to y = +45.0)
- Far East Avenue (x = 108.0, from y = -45.0 to y = +45.0)
- North Street (y = 45.0, from x = -45.0 to x = +108.0)
- South Street (y = -45.0, from x = -45.0 to x = +108.0)
- Indoor Central Logistics Depot Bay & Dock Facility (x in [-34.5, -29.0], bay door portal at x = -27.5, y = -0.75)

Pure Python, zero external dependencies, 100% unit-testable.
"""
import heapq
import math
from typing import Dict, List, Optional, Tuple

# Indoor Depot Portal Constants
DEPOT_DOCK_XY = (-31.5, -0.75)
DEPOT_DOCK_SIDEWALK_XY = (-31.5, 2.50)
DEPOT_DOOR_XY = (-27.5, -0.75)
DEPOT_DOOR_SIDEWALK_XY = (-27.5, 2.50)
DEPOT_BOUNDS = {'min_x': -35.0, 'max_x': -28.0, 'min_y': -2.5, 'max_y': 4.5}

# City Operating Geographic Boundaries
CITY_BOUNDS = {'min_x': -48.0, 'max_x': 112.0, 'min_y': -48.0, 'max_y': 48.0}

# Solid Building Footprint Blocks (No-go zones: structures, interior walls, private property)
BUILDING_BLOCKS = [
    # (name, min_x, max_x, min_y, max_y)
    ('Block NW - North West Residential & Commercial', -42.5, -17.5, 3.0, 42.5),
    ('Block SW - South West Commercial Zone', -42.5, -17.5, -42.5, -3.0),
    ('Block NC - North Central Business & Shops', -12.5, 42.5, 3.0, 42.5),
    ('Block SC - South Central Plaza & Market', -12.5, 42.5, -42.5, -3.0),
    ('Block NE - North East Housing Block', 47.5, 105.0, 3.0, 42.5),
    ('Block SE - South East Apartment Complex', 47.5, 105.0, -42.5, -3.0),
    ('Depot Building Compound (Except Bay Door)', -35.0, -28.0, -2.5, 4.5),
]

# Controlled Intersections, Stop Lines, and Crosswalks
INTERSECTION_ZONES = {
    'NORTH_AVE_CENTRAL': {
        'center': (-15.0, 0.0),
        'radius': 3.5,
        'has_traffic_light': True,
        'stop_lines': {
            'CENTRAL_BLVD_EASTBOUND': {'x': -17.5, 'y': -0.75, 'heading': 0.0},
            'NORTH_AVE_SOUTHBOUND': {'x': -12.2, 'y': 3.5, 'heading': -math.pi / 2},
        },
        'crosswalks': [
            {'name': 'North Ave Intersection Crosswalk', 'x': -15.0, 'y': 4.0, 'is_vertical': False, 'length': 6.0}
        ]
    }
}

# Designated Curbside Stopping Bays & Approach Headings for Delivery Locations
CUSTOMER_STOPPING_BAYS: Dict[str, Dict] = {
    'CLIENT_1_NORTH_AVENUE': {
        'customer_name': 'Sophie Laurent',
        'door_xy': (-9.8, 15.0),
        'stopping_xy': (-14.6, 15.0),  # Standoff from sidewalk doorstep
        'approach_heading': 0.0,  # Face East toward customer doorstep
        'corridor': 'North Avenue East Sidewalk',
        'side': 'EAST',
    },
    'CLIENT_2_NORTH_AVENUE': {
        'customer_name': 'Marc Dubois',
        'door_xy': (-9.8, 28.0),
        'stopping_xy': (-14.6, 28.0),  # Standoff
        'approach_heading': 0.0,  # Face East toward storefront
        'corridor': 'North Avenue East Sidewalk',
        'side': 'EAST',
    },
    'CLIENT_3_NORTH_PLAZA': {
        'customer_name': 'Elena Rostova',
        'door_xy': (-13.4, 38.0),
        'stopping_xy': (-14.6, 38.0),  # 1.20m standoff
        'approach_heading': 0.0,
        'corridor': 'North Avenue East Sidewalk',
        'side': 'EAST',
    },
    'CLIENT_4_WEST_BOULEVARD': {
        'customer_name': 'Lucas Vance',
        'door_xy': (-46.5, 15.0),
        'stopping_xy': (-43.8, 15.0),
        'approach_heading': math.pi,  # Face West toward bistro patio
        'corridor': 'West Boulevard West Sidewalk',
        'side': 'WEST',
    },
    'CLIENT_5_CENTRAL_SQUARE': {
        'customer_name': 'Amira Khan',
        'door_xy': (-5.0, 2.5),
        'stopping_xy': (-6.0, 0.0),
        'approach_heading': math.pi / 2,  # Face North toward bakery entrance
        'corridor': 'Central Boulevard North Sidewalk',
        'side': 'NORTH',
    },
    'CLIENT_6_EAST_AVENUE': {
        'customer_name': 'David Kim',
        'door_xy': (46.5, 15.0),
        'stopping_xy': (43.8, 15.0),
        'approach_heading': 0.0,  # Face East toward Tech Labs
        'corridor': 'East Avenue East Sidewalk',
        'side': 'EAST',
    },
    'CLIENT_7_SOUTH_MARKET': {
        'customer_name': 'Marcus Brody',
        'door_xy': (-13.4, -25.0),
        'stopping_xy': (-14.6, -25.0),  # 1.20m standoff
        'approach_heading': 0.0,
        'corridor': 'North Avenue South Sidewalk',
        'side': 'EAST',
    },
    'CLIENT_8_FAR_EAST_MARINA': {
        'customer_name': 'Chloe Dubois',
        'door_xy': (108.0, 2.5),
        'stopping_xy': (106.0, 0.0),
        'approach_heading': 0.0,
        'corridor': 'Far East Marina Pier',
        'side': 'EAST',
    },
    'DEPOT_POST_OFFICE': {
        'customer_name': 'Central Logistics Depot',
        'door_xy': (-27.5, -0.75),
        'stopping_xy': (-31.5, -0.75),
        'approach_heading': 0.0,  # Docked facing East
        'corridor': 'Central Logistics Indoor Bay',
        'side': 'INDOOR',
    }
}


def is_inside_depot(x: float, y: float) -> bool:
    """Return True if (x, y) is located inside the closed indoor depot compound."""
    return (DEPOT_BOUNDS['min_x'] <= x <= DEPOT_BOUNDS['max_x']) and (DEPOT_BOUNDS['min_y'] <= y <= DEPOT_BOUNDS['max_y'])


def is_inside_building_block(x: float, y: float) -> Optional[str]:
    """Return name of building block if (x, y) is inside solid building footprint, else None."""
    if is_inside_depot(x, y):
        return None  # Depot interior is navigable by the delivery robot
    for name, min_x, max_x, min_y, max_y in BUILDING_BLOCKS:
        if name.startswith('Depot'):
            continue
        if min_x <= x <= max_x and min_y <= y <= max_y:
            return name
    return None


def segment_intersects_box(
    p1: Tuple[float, float], p2: Tuple[float, float], box: Tuple[float, float, float, float]
) -> bool:
    """Check if 2D line segment p1-p2 intersects axis-aligned box (min_x, max_x, min_y, max_y) via Liang-Barsky."""
    x1, y1 = p1
    x2, y2 = p2
    min_x, max_x, min_y, max_y = box
    dx = x2 - x1
    dy = y2 - y1

    p = [-dx, dx, -dy, dy]
    q = [x1 - min_x, max_x - x1, y1 - min_y, max_y - y1]

    u1 = 0.0
    u2 = 1.0

    for k in range(4):
        if p[k] == 0:
            if q[k] < 0:
                return False
        else:
            t = q[k] / p[k]
            if p[k] < 0:
                if t > u1:
                    u1 = t
            else:
                if t < u2:
                    u2 = t
            if u1 > u2:
                return False
    return True


def does_segment_collide_with_buildings(
    p1: Tuple[float, float], p2: Tuple[float, float], allow_depot_ingress: bool = False
) -> bool:
    """Return True if segment from p1 to p2 intersects any building structure."""
    for name, min_x, max_x, min_y, max_y in BUILDING_BLOCKS:
        box = (min_x, max_x, min_y, max_y)
        if name.startswith('Depot'):
            if allow_depot_ingress:
                # Entering or exiting through the open East bay door (x >= -27.8) is allowed.
                # However, punching through the solid West back wall (x < -34.0) is strictly blocked.
                if min(p1[0], p2[0]) < -34.0:
                    return True
                continue
            if segment_intersects_box(p1, p2, box):
                return True
        else:
            if segment_intersects_box(p1, p2, box):
                return True
    return False


# Predefined key city intersections (nodes in topological graph)
INTERSECTIONS: Dict[str, Tuple[float, float]] = {
    'WEST_SOUTH': (-45.0, -45.0),
    'WEST_CENTRAL': (-45.0, 0.0),
    'WEST_NORTH': (-45.0, 45.0),
    'NORTH_AVE_SOUTH': (-15.0, -45.0),
    'NORTH_AVE_CENTRAL': (-15.0, 0.0),
    'NORTH_AVE_NORTH': (-15.0, 45.0),
    'EAST_SOUTH': (45.0, -45.0),
    'EAST_CENTRAL': (45.0, 0.0),
    'EAST_NORTH': (45.0, 45.0),
    'FAR_EAST_SOUTH': (108.0, -45.0),
    'FAR_EAST_CENTRAL': (108.0, 0.0),
    'FAR_EAST_NORTH': (108.0, 45.0),
}

# Major navigable street corridor axes across small_city
STREET_CORRIDORS = [
    # (name, is_horizontal, fixed_coord, min_val, max_val)
    ('Central Boulevard', True, 0.0, -28.0, 108.0),
    ('North Street', True, 45.0, -45.0, 108.0),
    ('South Street', True, -45.0, -45.0, 108.0),
    ('North Avenue', False, -15.0, -45.0, 45.0),
    ('West Boulevard', False, -45.0, -45.0, 45.0),
    ('East Avenue', False, 45.0, -45.0, 45.0),
    ('Far East Avenue', False, 108.0, -45.0, 45.0),
]

# Corridor-to-Intersections lookup for smart multi-turn pathfinding
CORRIDOR_NODES: Dict[str, List[str]] = {
    'West Boulevard': ['WEST_SOUTH', 'WEST_CENTRAL', 'WEST_NORTH'],
    'North Avenue': ['NORTH_AVE_SOUTH', 'NORTH_AVE_CENTRAL', 'NORTH_AVE_NORTH'],
    'East Avenue': ['EAST_SOUTH', 'EAST_CENTRAL', 'EAST_NORTH'],
    'Far East Avenue': ['FAR_EAST_SOUTH', 'FAR_EAST_CENTRAL', 'FAR_EAST_NORTH'],
    'North Street': ['WEST_NORTH', 'NORTH_AVE_NORTH', 'EAST_NORTH', 'FAR_EAST_NORTH'],
    'South Street': ['WEST_SOUTH', 'NORTH_AVE_SOUTH', 'EAST_SOUTH', 'FAR_EAST_SOUTH'],
    'Central Boulevard': ['NORTH_AVE_CENTRAL', 'EAST_CENTRAL', 'FAR_EAST_CENTRAL'],
}

# Graph adjacency list
# CRITICAL: WEST_CENTRAL is DISCONNECTED from NORTH_AVE_CENTRAL because the Central Depot building
# physically blocks Central Blvd through-traffic between x = -34.5 and x = -29.0.
GRAPH_EDGES = [
    # West Boulevard (x = -45.0)
    ('WEST_SOUTH', 'WEST_CENTRAL'),
    ('WEST_CENTRAL', 'WEST_NORTH'),

    # North Avenue (x = -15.0)
    ('NORTH_AVE_SOUTH', 'NORTH_AVE_CENTRAL'),
    ('NORTH_AVE_CENTRAL', 'NORTH_AVE_NORTH'),

    # East Avenue (x = 45.0)
    ('EAST_SOUTH', 'EAST_CENTRAL'),
    ('EAST_CENTRAL', 'EAST_NORTH'),

    # Far East Avenue (x = 108.0)
    ('FAR_EAST_SOUTH', 'FAR_EAST_CENTRAL'),
    ('FAR_EAST_CENTRAL', 'FAR_EAST_NORTH'),

    # South Street (y = -45.0)
    ('WEST_SOUTH', 'NORTH_AVE_SOUTH'),
    ('NORTH_AVE_SOUTH', 'EAST_SOUTH'),
    ('EAST_SOUTH', 'FAR_EAST_SOUTH'),

    # Central Boulevard (y = 0.0) - only open East of depot (x >= -28.0)
    ('NORTH_AVE_CENTRAL', 'EAST_CENTRAL'),
    ('EAST_CENTRAL', 'FAR_EAST_CENTRAL'),

    # North Street (y = 45.0)
    ('WEST_NORTH', 'NORTH_AVE_NORTH'),
    ('NORTH_AVE_NORTH', 'EAST_NORTH'),
    ('EAST_NORTH', 'FAR_EAST_NORTH'),
]

# Build undirected adjacency map with metric Euclidean distances
ADJACENCY: Dict[str, List[Tuple[str, float]]] = {}
for u, v in GRAPH_EDGES:
    x1, y1 = INTERSECTIONS[u]
    x2, y2 = INTERSECTIONS[v]
    dist = math.hypot(x2 - x1, y2 - y1)
    ADJACENCY.setdefault(u, []).append((v, dist))
    ADJACENCY.setdefault(v, []).append((u, dist))


def snap_to_corridor(x: float, y: float) -> Tuple[float, float, str]:
    """Snap an arbitrary (x, y) query point to the nearest navigable street corridor."""
    # Special case: inside depot
    if is_inside_depot(x, y):
        return DEPOT_DOOR_XY[0], DEPOT_DOOR_XY[1], 'Central Boulevard'

    best_dist = float('inf')
    best_pt = (x, y)
    best_corridor = 'Unknown'

    for name, is_horiz, fixed, v_min, v_max in STREET_CORRIDORS:
        if is_horiz:
            # Horizontal street: fixed y
            # Central Boulevard physically terminates at the depot building (x = -28.0)
            if name == 'Central Boulevard' and x < -28.0:
                continue
            px = max(v_min, min(v_max, x))
            py = fixed
        else:
            # Vertical street: fixed x
            px = fixed
            py = max(v_min, min(v_max, y))
        d = math.hypot(px - x, py - y)
        if d < best_dist:
            best_dist = d
            best_pt = (px, py)
            best_corridor = name

    return best_pt[0], best_pt[1], best_corridor


def is_destination_reachable(x: float, y: float, max_dist_from_road: float = 6.0) -> bool:
    """Validate whether a point is close enough to a navigable corridor to be reachable."""
    if is_inside_depot(x, y):
        return True
    sx, sy, _ = snap_to_corridor(x, y)
    return math.hypot(sx - x, sy - y) <= max_dist_from_road


def validate_and_snap_destination(
    x: float, y: float, max_road_dist: float = 8.0
) -> Tuple[bool, Tuple[float, float], float, str]:
    """Validate destination coordinates against physical city geometry and return reachable curbside stopping bay.

    Returns:
        (is_valid, (stopping_x, stopping_y), approach_heading_rad, explanation_status)
    """
    # 1. Geographic operating boundary check
    if not (CITY_BOUNDS['min_x'] <= x <= CITY_BOUNDS['max_x'] and CITY_BOUNDS['min_y'] <= y <= CITY_BOUNDS['max_y']):
        return False, (x, y), 0.0, "REJECTED_OUTSIDE_CITY_BOUNDS"

    # 2. Indoor Central Logistics Depot
    if is_inside_depot(x, y):
        return True, (DEPOT_DOCK_XY[0], DEPOT_DOCK_XY[1]), 0.0, "DEPOT_DOCK_FACILITY"

    # 3. Known designated customer stopping bays
    for bay_id, bay in CUSTOMER_STOPPING_BAYS.items():
        door_x, door_y = bay['door_xy']
        if math.hypot(door_x - x, door_y - y) <= 4.0:
            return True, bay['stopping_xy'], bay['approach_heading'], f"VALIDATED_BAY_{bay_id}"

    # 4. Building footprint check (no-go zone)
    bname = is_inside_building_block(x, y)
    if bname is not None:
        sx, sy, corr = snap_to_corridor(x, y)
        dist_to_corr = math.hypot(sx - x, sy - y)
        if dist_to_corr > max_road_dist:
            return False, (x, y), 0.0, f"REJECTED_INSIDE_RESTRICTED_{bname}"
        # Snap to outer perimeter curbside facing the building
        approach_heading = math.atan2(y - sy, x - sx)
        return True, (sx, sy), approach_heading, f"SNAPPED_TO_PERIMETER_OF_{bname}"

    # 5. General open city area reachability
    sx, sy, corr = snap_to_corridor(x, y)
    dist = math.hypot(sx - x, sy - y)
    if dist <= max_road_dist:
        approach_heading = math.atan2(y - sy, x - sx) if dist > 0.1 else 0.0
        return True, (sx, sy), approach_heading, f"SNAPPED_TO_CORRIDOR_{corr.upper().replace(' ', '_')}"

    return False, (x, y), 0.0, "REJECTED_UNREACHABLE_NO_ROAD_ACCESS"


def _astar(start_node: str, goal_node: str, blocked_edges: Optional[set] = None) -> Tuple[List[str], float]:
    """A* search between two graph intersection nodes, returning path and metric cost."""
    if start_node == goal_node:
        return [start_node], 0.0

    def heuristic(node: str) -> float:
        gx, gy = INTERSECTIONS[goal_node]
        nx, ny = INTERSECTIONS[node]
        return math.hypot(gx - nx, gy - ny)

    pq = [(heuristic(start_node), 0.0, start_node, [start_node])]
    visited = {}

    while pq:
        f, g, current, path = heapq.heappop(pq)
        if current in visited and visited[current] <= g:
            continue
        visited[current] = g

        if current == goal_node:
            return path, g

        for neighbor, weight in ADJACENCY.get(current, []):
            if blocked_edges and ((current, neighbor) in blocked_edges or (neighbor, current) in blocked_edges):
                continue
            cost = g + weight
            if neighbor not in visited or cost < visited[neighbor]:
                heapq.heappush(pq, (cost + heuristic(neighbor), cost, neighbor, path + [neighbor]))

    return [start_node, goal_node], 999.0


def plan_city_route(
    start_xy: Tuple[float, float],
    goal_xy: Tuple[float, float],
    blocked_edges: Optional[set] = None
) -> List[Tuple[float, float]]:
    """Compute an ordered sequence of metric road waypoints from start to goal.

    Rules:
    1. Depot Egress: Trips starting inside depot (x <= -28.0) MUST first output
       DEPOT_DOOR_XY (-27.5, -0.75) to roll out of the bay door before navigating.
    2. Depot Ingress: Trips ending at depot dock MUST route via DEPOT_DOOR_XY before
       entering dock (-31.5, -0.75).
    3. Multi-corridor city travel routes strictly via topological A* on unobstructed streets.
    4. On Central Boulevard (between x = -28.0 and x = -15.0), lane y = -0.75 is maintained.
    """
    start_in_depot = is_inside_depot(start_xy[0], start_xy[1]) or (start_xy[0] <= -28.0 and (-2.5 <= start_xy[1] <= 4.5))
    goal_in_depot = is_inside_depot(goal_xy[0], goal_xy[1]) or (goal_xy[0] <= -28.0 and (-2.5 <= goal_xy[1] <= 4.5))

    # 1. Trivial stay inside depot
    if start_in_depot and goal_in_depot:
        return [(goal_xy[0], goal_xy[1])]

    # Determine appropriate depot portal door (sidewalk plaza y=2.50 vs legacy y=-0.75)
    def _get_depot_door(xy):
        return DEPOT_DOOR_SIDEWALK_XY if xy[1] >= 1.0 else DEPOT_DOOR_XY

    def _get_depot_dock(xy):
        return DEPOT_DOCK_SIDEWALK_XY if xy[1] >= 1.0 else DEPOT_DOCK_XY

    # 2. Outward trip from inside depot to city
    if start_in_depot:
        door_wp = _get_depot_door(start_xy)
        outward_route = _plan_street_route(door_wp, goal_xy, blocked_edges=blocked_edges)
        # Prepend door waypoint if robot is still inside (< -27.8m)
        if start_xy[0] < -27.8:
            return [door_wp] + [wp for wp in outward_route if math.hypot(wp[0] - door_wp[0], wp[1] - door_wp[1]) > 0.5]
        return outward_route

    # 3. Inward trip from city returning to depot dock
    if goal_in_depot:
        door_wp = _get_depot_door(goal_xy)
        dock_target = _get_depot_dock(goal_xy)
        dock_wp = (goal_xy[0], goal_xy[1]) if goal_xy[0] < -29.0 else dock_target
        inward_route = _plan_street_route(start_xy, door_wp, blocked_edges=blocked_edges)
        res = [wp for wp in inward_route if math.hypot(wp[0] - door_wp[0], wp[1] - door_wp[1]) > 0.5]
        res.append(door_wp)
        res.append(dock_wp)
        return _prune_collinear(start_xy, res)

    # 4. Standard city street-to-street route
    return _plan_street_route(start_xy, goal_xy, blocked_edges=blocked_edges)


def _plan_street_route(
    start_xy: Tuple[float, float],
    goal_xy: Tuple[float, float],
    blocked_edges: Optional[set] = None
) -> List[Tuple[float, float]]:
    """Plan route between two street points in the open urban grid using corridor-optimal A*."""
    sx, sy, s_corr = snap_to_corridor(start_xy[0], start_xy[1])
    gx, gy, g_corr = snap_to_corridor(goal_xy[0], goal_xy[1])

    # If already at destination
    if math.hypot(goal_xy[0] - start_xy[0], goal_xy[1] - start_xy[1]) < 0.8:
        return [(goal_xy[0], goal_xy[1])]

    # 1. Same corridor -> direct line ONLY if no building block collision
    if s_corr == g_corr:
        eff_g = (goal_xy[0], -0.75) if s_corr == 'Central Boulevard' and (start_xy[0] < -15.0 or goal_xy[0] < -15.0) else (goal_xy[0], goal_xy[1])
        if not does_segment_collide_with_buildings(start_xy, eff_g, allow_depot_ingress=False):
            return [eff_g]

    # 2. Multi-turn pathfinding: find candidate corridor entry/exit nodes minimizing total path length
    start_cands = CORRIDOR_NODES.get(s_corr, list(INTERSECTIONS.keys()))
    goal_cands = CORRIDOR_NODES.get(g_corr, list(INTERSECTIONS.keys()))

    best_cost = float('inf')
    best_node_path = []

    for sn in start_cands:
        d_start = math.hypot(INTERSECTIONS[sn][0] - sx, INTERSECTIONS[sn][1] - sy)
        for gn in goal_cands:
            d_goal = math.hypot(gx - INTERSECTIONS[gn][0], gy - INTERSECTIONS[gn][1])
            path, cost = _astar(sn, gn, blocked_edges=blocked_edges)
            total = d_start + cost + d_goal
            if total < best_cost:
                best_cost = total
                best_node_path = path

    raw_waypoints = []
    for node in best_node_path:
        pt = INTERSECTIONS[node]
        if node == 'NORTH_AVE_CENTRAL' and (start_xy[0] < -16.0 or goal_xy[0] < -16.0):
            pt = (-15.0, -0.75)
        raw_waypoints.append(pt)

    # Append destination
    eff_goal = (goal_xy[0], -0.75) if g_corr == 'Central Boulevard' and goal_xy[0] < -15.0 else (goal_xy[0], goal_xy[1])
    raw_waypoints.append(eff_goal)

    # Prune overshoot if goal lies along the final corridor before the last intersection
    raw_waypoints = _prune_overshoot(raw_waypoints, eff_goal)

    return _prune_collinear(start_xy, raw_waypoints)


def _prune_overshoot(waypoints: List[Tuple[float, float]], goal_xy: Tuple[float, float]) -> List[Tuple[float, float]]:
    """If the penultimate intersection overshoots the goal on the same street axis, drop it."""
    if len(waypoints) >= 3:
        A = waypoints[-3]
        B = waypoints[-2]
        G = goal_xy
        # Vertical corridor check (same X)
        if abs(A[0] - B[0]) < 0.5 and abs(B[0] - G[0]) < 0.5:
            if min(A[1], B[1]) <= G[1] <= max(A[1], B[1]):
                return waypoints[:-2] + [G]
        # Horizontal corridor check (same Y)
        if abs(A[1] - B[1]) < 0.5 and abs(B[1] - G[1]) < 0.5:
            if min(A[0], B[0]) <= G[0] <= max(A[0], B[0]):
                return waypoints[:-2] + [G]
    return waypoints


def _prune_collinear(start_xy: Tuple[float, float], waypoints: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Eliminate redundant intermediate collinear or backward waypoints."""
    pruned = []
    for pt in waypoints:
        if math.hypot(pt[0] - start_xy[0], pt[1] - start_xy[1]) < 0.8:
            continue
        if not pruned or math.hypot(pt[0] - pruned[-1][0], pt[1] - pruned[-1][1]) > 0.8:
            pruned.append(pt)

    if not pruned and waypoints:
        pruned.append(waypoints[-1])

    return pruned
