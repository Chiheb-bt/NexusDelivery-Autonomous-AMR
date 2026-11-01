"""ROS-independent helpers for the GPS waypoint controller."""

import math


EARTH_RADIUS_M = 6378137.0
OBSTACLE_LABELS = frozenset({
    "person", "bicycle", "car", "motorcycle", "bus", "truck", "train",
    "boat", "bench", "cat", "dog", "horse", "sheep", "cow", "bear",
    "backpack", "suitcase", "chair", "couch", "potted plant",
    "dining table", "skateboard", "surfboard",
})


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def gps_to_world_xy(latitude, longitude, origin_lat, origin_lon,
                    origin_x, origin_y, world_heading_deg):
    """Project a nearby fix into the small-city SDF world frame."""
    lat0 = math.radians(origin_lat)
    east = EARTH_RADIUS_M * math.cos(lat0) * math.radians(longitude - origin_lon)
    north = EARTH_RADIUS_M * math.radians(latitude - origin_lat)
    heading = math.radians(world_heading_deg)
    x = origin_x + east * math.cos(heading) - north * math.sin(heading)
    y = origin_y + east * math.sin(heading) + north * math.cos(heading)
    return x, y


def quaternion_yaw(q):
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z),
    )


def is_near_forward_obstacle(label, box, image_shape, clearance_y, corridor_fraction):
    height, width = image_shape[:2]
    x1, _, x2, y2 = box
    return (
        label.lower() in OBSTACLE_LABELS
        and width * (0.5 - corridor_fraction) <= (x1 + x2) * 0.5
        <= width * (0.5 + corridor_fraction)
        and y2 >= height * clearance_y
    )


def waypoint_velocity(x, y, yaw, goal_x, goal_y, max_linear_speed,
                      max_angular_speed, lookahead_distance):
    dx, dy = goal_x - x, goal_y - y
    distance = math.hypot(dx, dy)
    bearing_error = wrap_angle(math.atan2(dy, dx) - yaw)
    if abs(bearing_error) > math.pi * 0.5:
        angular = math.copysign(max_angular_speed, bearing_error)
        return 0.0, angular, distance
    angular = clamp(
        2.0 * max_linear_speed * math.sin(bearing_error)
        / max(distance, lookahead_distance),
        -max_angular_speed,
        max_angular_speed,
    )
    turn_scale = clamp(1.0 - abs(bearing_error) / 1.2, 0.2, 1.0)
    return max_linear_speed * turn_scale, angular, distance
