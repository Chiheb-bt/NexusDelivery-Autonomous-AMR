"""Perception vision algorithms (pure OpenCV & numpy, unit-testable without ROS).

Contains:
1. CLAHE preprocessing on luminance channel.
2. Robust forward drivable-area & obstacle detection for urban navigation.
3. Traffic light state detection (red and green signal lamps).
4. Visual arrival cues and debug visualization overlays.
5. Legacy lane & orange density functions for backward compatibility.
"""

import cv2
import numpy as np


def preprocess(bgr, use_clahe=True, clip=2.0, tile=8):
    """CLAHE on L-channel of LAB color space to normalize lighting."""
    if not use_clahe or bgr is None or bgr.size == 0:
        return bgr
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile)).apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def detect_forward_obstacles(bgr, roi=(75, 215, 25, 295), min_area=200, max_area=15000):
    """Detect obstacles in the forward road corridor using saturation and asphalt contrast.

    Returns dict with:
      - obstacle_detected (bool)
      - proximity (float [0.0, 1.0], 1.0 = immediately ahead)
      - lateral_offset (float [-1.0, 1.0], -1.0=left, +1.0=right)
      - clearance_left (float [0.0, 1.0])
      - clearance_right (float [0.0, 1.0])
      - safe_passable (bool)
      - suggested_bypass (str: 'LEFT', 'RIGHT', 'STOP', 'NONE')
      - bbox (tuple: (x, y, w, h) or None)
      - annotated_img (np.ndarray with debug overlays)
    """
    if bgr is None or bgr.size == 0:
        return {
            'obstacle_detected': False, 'proximity': 0.0, 'lateral_offset': 0.0,
            'clearance_left': 1.0, 'clearance_right': 1.0, 'safe_passable': True,
            'suggested_bypass': 'NONE', 'bbox': None, 'annotated_img': bgr
        }

    h_img, w_img = bgr.shape[:2]
    r0, r1, c0, c1 = roi
    r0, r1 = max(0, r0), min(h_img, r1)
    c0, c1 = max(0, c0), min(w_img, c1)
    corridor_h = float(r1 - r0)
    corridor_w = float(c1 - c0)

    annotated = bgr.copy()
    cv2.rectangle(annotated, (c0, r0), (c1, r1), (180, 180, 50), 1)

    corridor = bgr[r0:r1, c0:c1]
    hsv = cv2.cvtColor(corridor, cv2.COLOR_BGR2HSV)

    # 1. High saturation objects (orange barrier, cones, vehicles, signs)
    sat_mask = cv2.inRange(hsv, (0, 65, 50), (180, 255, 255))

    # 2. Strong contrast against local asphalt
    road_sample = corridor[max(0, int(corridor_h - 40)):int(corridor_h), 80:min(180, int(corridor_w))]
    mean_asphalt = road_sample.mean(axis=(0, 1)) if road_sample.size else np.array([70.0, 75.0, 75.0])
    diff = np.abs(corridor.astype(np.float32) - mean_asphalt).mean(axis=2)
    diff_mask = (diff > 70).astype(np.uint8) * 255

    combined = cv2.bitwise_or(sat_mask, diff_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    clean = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
    clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    significant = []
    for c in contours:
        area = cv2.contourArea(c)
        bx, by, bw, bh = cv2.boundingRect(c)
        if min_area <= area:
            significant.append((c, area, (bx, by, bw, bh)))

    if not significant:
        cv2.putText(annotated, 'CORRIDOR: CLEAR', (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return {
            'detected': False, 'obstacle_detected': False, 'proximity': 0.0, 'lateral_offset': 0.0,
            'clearance_left': 1.0, 'clearance_right': 1.0, 'safe_passable': True,
            'suggested_bypass': 'NONE', 'bbox': None, 'annotated_img': annotated
        }

    # Select the most critical obstacle (lowest bottom edge, closest to robot)
    chosen = max(significant, key=lambda item: (item[2][1] + item[2][3]) * 1000 + item[1])
    _, _, (bx, by, bw, bh) = chosen

    gx, gy = bx + c0, by + r0
    y_bottom = gy + bh
    proximity = np.clip((y_bottom - r0) / corridor_h, 0.0, 1.0)
    center_x = gx + bw / 2.0
    lateral_offset = np.clip((center_x - (w_img / 2.0)) / (w_img / 2.0), -1.0, 1.0)

    px_left = max(0, gx - c0)
    px_right = max(0, c1 - (gx + bw))
    clearance_left = float(px_left / corridor_w)
    clearance_right = float(px_right / corridor_w)

    safe_pass_margin = 0.08
    safe_passable = max(clearance_left, clearance_right) >= safe_pass_margin

    if not safe_passable:
        suggested_bypass = 'STOP'
    elif clearance_left >= clearance_right:
        # Clearance on image left (u < 160) corresponds to the open RIGHT road lane (world -Y)
        suggested_bypass = 'RIGHT'
    else:
        # Clearance on image right (u > 160) corresponds to the open LEFT road lane (world +Y)
        suggested_bypass = 'LEFT'

    color_box = (0, 0, 255) if suggested_bypass == 'STOP' else (0, 165, 255)
    cv2.rectangle(annotated, (gx, gy), (gx + bw, gy + bh), color_box, 2)
    cv2.line(annotated, (gx, y_bottom), (gx + bw, y_bottom), (0, 255, 255), 2)

    status_str = f'OBS: {suggested_bypass} (p={proximity:.2f}, L={clearance_left:.2f}, R={clearance_right:.2f})'
    cv2.putText(annotated, status_str, (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_box, 1)

    contour_sat = sat_mask[by:by+bh, bx:bx+bw]
    is_colored = int(np.count_nonzero(contour_sat)) >= 15

    return {
        'detected': True,
        'obstacle_detected': True,
        'proximity': float(proximity),
        'lateral_offset': float(lateral_offset),
        'clearance_left': float(clearance_left),
        'clearance_right': float(clearance_right),
        'safe_passable': bool(safe_passable),
        'suggested_bypass': suggested_bypass,
        'is_colored': bool(is_colored),
        'bbox': (gx, gy, bw, bh),
        'annotated_img': annotated
    }


# Calibrated camera geometry constants (from camera_info and URDF)
CAMERA_FX = 265.23347
CAMERA_FY = 265.23347
CAMERA_CX = 160.5
CAMERA_CY = 120.5
CAMERA_HEIGHT_M = 0.35
MIN_BODY_CLEARANCE_M = 0.48
MIN_OBSTACLE_HEIGHT_M = 0.08
MAX_OBSTACLE_HEIGHT_M = 2.2

# Cached projection arrays for fixed ROI
_CACHED_ROI = None
_CACHED_U_RATIO = None
_CACHED_V_RATIO = None
_CACHED_Z_GROUND = None
_CACHED_IS_ABOVE_CY = None


def _get_roi_cached_matrices(roi):
    global _CACHED_ROI, _CACHED_U_RATIO, _CACHED_V_RATIO, _CACHED_Z_GROUND, _CACHED_IS_ABOVE_CY
    if _CACHED_ROI != roi:
        r0, r1, c0, c1 = roi
        v_indices, u_indices = np.mgrid[r0:r1, c0:c1]
        _CACHED_U_RATIO = ((u_indices - CAMERA_CX) / CAMERA_FX).astype(np.float32)
        _CACHED_V_RATIO = ((v_indices - CAMERA_CY) / CAMERA_FY).astype(np.float32)
        v_diff = np.maximum(v_indices - CAMERA_CY, 0.5)
        _CACHED_Z_GROUND = ((CAMERA_HEIGHT_M * CAMERA_FY) / v_diff).astype(np.float32)
        _CACHED_IS_ABOVE_CY = (v_indices <= CAMERA_CY)
        _CACHED_ROI = roi
    return _CACHED_U_RATIO, _CACHED_V_RATIO, _CACHED_Z_GROUND, _CACHED_IS_ABOVE_CY


def analyze_depth_corridor(depth_img, roi=(50, 185, 30, 290), max_range=20.0, stop_dist=0.85, caution_dist=4.5):
    """Analyze forward depth corridor with calibrated 3D ground rejection.

    Rejects ground plane asphalt using camera geometry (height above ground >= 0.08m)
    and eliminates chassis self-reflections (< 0.48m).
    Evaluates metric lateral clearance for safe bypass decision.
    """
    if depth_img is None or depth_img.size == 0:
        return {
            'depth_valid': False, 'min_distance': 999.0, 'obstacle_detected': False,
            'left_depth': 999.0, 'right_depth': 999.0, 'safe_passable': False,
            'suggested_bypass': 'STOP'
        }

    h_img, w_img = depth_img.shape[:2]
    r0, r1, c0, c1 = roi
    r0, r1 = max(0, r0), min(h_img, r1)
    c0, c1 = max(0, c0), min(w_img, c1)

    corridor = depth_img[r0:r1, c0:c1].astype(np.float32)

    # Sensor health check (distinguishes all-NaN/corrupted stream from valid sensor data)
    finite_sensor = np.isfinite(depth_img) & (depth_img > 0.05) & (depth_img <= max_range)
    if int(np.count_nonzero(finite_sensor)) < 50:
        return {
            'depth_valid': False, 'min_distance': 999.0, 'obstacle_detected': False,
            'left_depth': 999.0, 'right_depth': 999.0, 'safe_passable': False,
            'suggested_bypass': 'STOP'
        }

    # Points in corridor within sensor range
    valid_mask = np.isfinite(corridor) & (corridor >= MIN_BODY_CLEARANCE_M) & (corridor <= max_range)

    u_ratio, v_ratio, z_ground, is_above_cy = _get_roi_cached_matrices((r0, r1, c0, c1))
    Z = corridor
    Y_lat = u_ratio * Z
    Z_h = CAMERA_HEIGHT_M - v_ratio * Z

    # Geometric ground plane rejection:
    is_in_front_of_ground = is_above_cy | (Z < (z_ground - 0.18))

    obstacle_points = valid_mask & is_in_front_of_ground & (Z_h >= MIN_OBSTACLE_HEIGHT_M) & (Z_h <= MAX_OBSTACLE_HEIGHT_M)

    # Monitored forward road corridor: body width 0.62m -> half-width 0.65m
    corridor_obs = obstacle_points & (np.abs(Y_lat) <= 0.65) & (Z < caution_dist)
    obs_px = int(np.count_nonzero(corridor_obs))

    obstacle_detected = (obs_px >= 25)
    if obstacle_detected:
        min_dist = float(np.percentile(Z[corridor_obs], 5))
        obs_y_pts = Y_lat[corridor_obs]
        obs_y_median = float(np.median(obs_y_pts))
    else:
        min_dist = 999.0
        obs_y_median = 0.0

    # Lateral passage clearance analysis
    # Evaluate obstacle presence in left and right bypass lanes within the obstacle depth slice
    z_slice_min = max(MIN_BODY_CLEARANCE_M, min_dist - 0.5)
    z_slice_max = min(caution_dist, min_dist + 1.5)

    # Metric lateral corridors aligned with camera optical frame:
    # Camera optical X (Y_lat): negative is robot LEFT, positive is robot RIGHT
    left_corridor_blockers = obstacle_points & (Y_lat >= -1.00) & (Y_lat <= -0.35) & (Z >= z_slice_min) & (Z <= z_slice_max)
    right_corridor_blockers = obstacle_points & (Y_lat >= 0.35) & (Y_lat <= 1.00) & (Z >= z_slice_min) & (Z <= z_slice_max)

    left_block_count = int(np.count_nonzero(left_corridor_blockers))
    right_block_count = int(np.count_nonzero(right_corridor_blockers))

    # Median depth in left and right halves for diagnostic logging
    # Note: image left (u < mid_c) has Y_lat < 0 (robot LEFT)
    # image right (u > mid_c) has Y_lat > 0 (robot RIGHT)
    mid_c = (c1 - c0) // 2
    left_c = corridor[:, :mid_c]
    right_c = corridor[:, mid_c:]
    left_valid = left_c[np.isfinite(left_c) & (left_c >= MIN_BODY_CLEARANCE_M)]
    right_valid = right_c[np.isfinite(right_c) & (right_c >= MIN_BODY_CLEARANCE_M)]
    left_d = float(np.median(left_valid)) if left_valid.size >= 10 else 999.0
    right_d = float(np.median(right_valid)) if right_valid.size >= 10 else 999.0

    # Passage is open if blockers < 40 or median depth is open
    left_clear = (left_block_count < 40) or (left_d >= 4.2)
    right_clear = (right_block_count < 40) or (right_d >= 4.2)
    has_passage = left_clear or right_clear
    both_clear = left_clear and right_clear

    safe_passable = has_passage and (min_dist >= stop_dist)

    if not obstacle_detected:
        suggested_bypass = 'NONE'
        safe_passable = True
    elif min_dist < stop_dist:
        suggested_bypass = 'STOP'
        safe_passable = False
    elif obs_y_median < -0.06:
        # Obstacle is on the robot's LEFT side (camera optical X < 0, Y_lat < 0)
        # Safe bypass is on the RIGHT (offset -0.75m), provided right corridor is clear
        if right_clear:
            suggested_bypass = 'RIGHT'
            safe_passable = True
        else:
            suggested_bypass = 'STOP'
            safe_passable = False
    elif obs_y_median > 0.06:
        # Obstacle is on the robot's RIGHT side (camera optical X > 0, Y_lat > 0)
        # Safe bypass is on the LEFT (offset +0.65m), provided left corridor is clear
        if left_clear:
            suggested_bypass = 'LEFT'
            safe_passable = True
        else:
            suggested_bypass = 'STOP'
            safe_passable = False
    else:
        # Obstacle is centered (|Y_lat| <= 0.06)
        # Select side with greater open depth clearance; fallback to RIGHT
        if right_clear and left_clear:
            if left_d > right_d + 0.5:
                suggested_bypass = 'LEFT'
            else:
                suggested_bypass = 'RIGHT'
            safe_passable = True
        elif right_clear:
            suggested_bypass = 'RIGHT'
            safe_passable = True
        elif left_clear:
            suggested_bypass = 'LEFT'
            safe_passable = True
        else:
            suggested_bypass = 'STOP'
            safe_passable = False

    return {
        'depth_valid': True,
        'min_distance': min_dist,
        'corridor_distance': min_dist,
        'distance_m': min_dist,
        'obstacle_detected': obstacle_detected,
        'left_depth': left_d,
        'right_depth': right_d,
        'safe_passable': safe_passable,
        'suggested_bypass': suggested_bypass,
        'both_clear': both_clear,
        'obs_y_median': obs_y_median
    }


def fuse_rgb_and_depth(bgr, depth_img=None, roi=(50, 185, 30, 290)):
    """Fuse RGB optical detection with metric depth measurements.

    Gated by 3D ground plane verification to eliminate optical asphalt false positives.
    """
    rgb_res = detect_forward_obstacles(bgr)
    if depth_img is None:
        rgb_res['obstacle_distance'] = 999.0
        rgb_res['distance_m'] = 999.0
        rgb_res['depth_valid'] = False
        rgb_res['left_depth'] = 999.0
        rgb_res['right_depth'] = 999.0
        return rgb_res

    depth_res = analyze_depth_corridor(depth_img, roi=roi, caution_dist=4.5)
    obs_dist = depth_res['min_distance']
    obs_detected = depth_res['obstacle_detected']

    # Sample obstacle distance from bbox if verified by 3D obstacle points above ground
    if rgb_res['bbox'] is not None:
        bx, by, bw, bh = rgb_res['bbox']
        h_img, w_img = depth_img.shape[:2]
        bx1, by1 = max(0, bx), max(0, by)
        bx2, by2 = min(w_img, bx + bw), min(h_img, by + bh)
        if by2 > by1 and bx2 > bx1:
            bbox_depth = depth_img[by1:by2, bx1:bx2].astype(np.float32)
            v_b, u_b = np.mgrid[by1:by2, bx1:bx2]
            valid_b = np.isfinite(bbox_depth) & (bbox_depth >= MIN_BODY_CLEARANCE_M) & (bbox_depth < 4.5)
            if int(np.count_nonzero(valid_b)) >= 10:
                Zh_b = CAMERA_HEIGHT_M - ((v_b - CAMERA_CY) / CAMERA_FY) * bbox_depth
                Ylat_b = ((u_b - CAMERA_CX) / CAMERA_FX) * bbox_depth
                # True obstacles must be physically above ground level (>= 0.08m) and within vehicle lateral width
                true_obs_b = valid_b & (Zh_b >= MIN_OBSTACLE_HEIGHT_M) & (Zh_b <= MAX_OBSTACLE_HEIGHT_M) & (np.abs(Ylat_b) <= 0.65)
                if int(np.count_nonzero(true_obs_b)) >= 12:
                    box_dist = float(np.percentile(bbox_depth[true_obs_b], 5))
                    if box_dist < obs_dist:
                        obs_dist = box_dist
                        obs_detected = True

    # Fallback only when depth sensor is invalid/offline: let saturated optical objects trigger caution
    if not obs_detected and not depth_res['depth_valid'] and rgb_res.get('obstacle_detected', False) and rgb_res.get('is_colored', False):
        obs_detected = True
        obs_dist = min(obs_dist, 3.2)

    # Determine recommended bypass direction and passability from verified 3D depth
    if depth_res['depth_valid'] and obs_detected:
        bypass = depth_res['suggested_bypass']
        if bypass == 'NONE':
            if rgb_res.get('bbox') is not None:
                bx, by, bw, bh = rgb_res['bbox']
                center_u = bx + bw / 2.0
                # center_u > CAMERA_CX (image right) is road LEFT (+Y) -> bypass RIGHT
                bypass = 'RIGHT' if center_u >= CAMERA_CX else 'LEFT'
            elif rgb_res.get('suggested_bypass') in ('LEFT', 'RIGHT'):
                bypass = rgb_res['suggested_bypass']
            else:
                bypass = 'RIGHT'
        safe_passable = depth_res.get('safe_passable', True)
    elif depth_res['depth_valid']:
        # Forward depth corridor is clear; do not let 2D RGB optical illusions force an obstacle bypass!
        obs_detected = False
        obs_dist = 999.0
        bypass = 'NONE'
        safe_passable = True
    elif obs_detected and obs_dist < 4.2:
        bypass = rgb_res['suggested_bypass']
        safe_passable = rgb_res['safe_passable']
    else:
        obs_detected = False
        obs_dist = 999.0
        bypass = 'NONE'
        safe_passable = True

    annotated = rgb_res['annotated_img']
    if depth_res['depth_valid']:
        depth_info = f'DEPTH: min={obs_dist:.2f}m (L={depth_res["left_depth"]:.1f}m, R={depth_res["right_depth"]:.1f}m)'
        cv2.putText(annotated, depth_info, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 0), 1)

    return {
        'detected': obs_detected,
        'obstacle_detected': obs_detected,
        'obstacle_distance': float(obs_dist),
        'distance_m': float(obs_dist),
        'proximity': float(np.clip((4.5 - obs_dist) / 4.0, 0.0, 1.0)) if obs_dist < 4.5 else rgb_res['proximity'],
        'lateral_offset': rgb_res['lateral_offset'],
        'clearance_left': rgb_res['clearance_left'],
        'clearance_right': rgb_res['clearance_right'],
        'left_depth': depth_res['left_depth'],
        'right_depth': depth_res['right_depth'],
        'safe_passable': safe_passable,
        'suggested_bypass': bypass,
        'depth_valid': depth_res['depth_valid'],
        'bbox': rgb_res.get('bbox'),
        'annotated_img': annotated
    }


def _largest_blob(mask):
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        return 0
    return int(stats[1:, cv2.CC_STAT_AREA].max())


def traffic_light_areas(bgr, roi=None):
    """Aire (pixels) du plus grand blob rouge et du plus grand blob vert.

    Si roi est fourni (r0, r1, c0, c1), la détection est restreinte à cette région
    pour éviter les faux positifs (ex: briques ou vêtements au sol).
    """
    if bgr is None or bgr.size == 0:
        return 0, 0
    if roi is not None:
        r0, r1, c0, c1 = roi
        h, w = bgr.shape[:2]
        r0 = max(0, min(h, r0))
        r1 = max(r0, min(h, r1))
        c0 = max(0, min(w, c0))
        c1 = max(c0, min(w, c1))
        crop = bgr[r0:r1, c0:c1]
    else:
        crop = bgr

    if crop.size == 0:
        return 0, 0

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    red = (
        cv2.inRange(hsv, (0, 150, 150), (10, 255, 255))
        | cv2.inRange(hsv, (170, 150, 150), (180, 255, 255))
    )
    green = cv2.inRange(hsv, (40, 100, 100), (85, 255, 255))
    return _largest_blob(red), _largest_blob(green)


def line_barycentre(bgr, roi, thresh=170, min_pixels=30, max_fill=0.6):
    """Barycentre des pixels clairs de la ROI (compatibilité descendante)."""
    if bgr is None or bgr.size == 0:
        return None, 0
    r0, r1, c0, c1 = roi
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mask = gray[r0:r1, c0:c1] > thresh
    n = int(mask.sum())
    if n < min_pixels or n > max_fill * mask.size:
        return None, n
    cols = np.nonzero(mask)[1]
    return float(cols.mean() + c0), n


def orange_density(bgr, roi):
    """Nombre de pixels orange dans la ROI (compatibilité descendante)."""
    if bgr is None or bgr.size == 0:
        return 0
    r0, r1, c0, c1 = roi
    hsv = cv2.cvtColor(bgr[r0:r1, c0:c1], cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (5, 120, 80), (25, 255, 255))
    return int(np.count_nonzero(mask))


class DynamicActorTracker:
    """Tracks dynamic agents and pedestrians across consecutive RGB-D vision frames."""

    def __init__(self, crossing_speed_threshold_mps: float = 0.15):
        self.crossing_speed_thresh = crossing_speed_threshold_mps
        self.prev_time = None
        self.prev_y_lat = None
        self.prev_dist = None
        self.consecutive_crossing_frames = 0

    def reset(self):
        self.prev_time = None
        self.prev_y_lat = None
        self.prev_dist = None
        self.consecutive_crossing_frames = 0

    def update(self, now: float, obs_detected: bool, obs_dist: float, obs_y_lat: float, robot_speed: float = 0.0):
        if not obs_detected or obs_dist > 6.0:
            self.reset()
            return {'is_pedestrian_crossing': False, 'lateral_speed': 0.0, 'ttc': 999.0}

        if self.prev_time is None or now <= self.prev_time:
            self.prev_time = now
            self.prev_y_lat = obs_y_lat
            self.prev_dist = obs_dist
            return {'is_pedestrian_crossing': False, 'lateral_speed': 0.0, 'ttc': 999.0}

        dt = max(1e-3, now - self.prev_time)
        v_lat = (obs_y_lat - self.prev_y_lat) / dt
        approach_speed = max(0.10, robot_speed + max(0.0, (self.prev_dist - obs_dist) / dt))
        ttc = obs_dist / approach_speed

        self.prev_time = now
        self.prev_y_lat = obs_y_lat
        self.prev_dist = obs_dist

        # If lateral motion is significant across corridor and approaching path center
        is_moving_across = abs(v_lat) >= self.crossing_speed_thresh and abs(obs_y_lat) < 1.10
        if is_moving_across:
            self.consecutive_crossing_frames += 1
        else:
            self.consecutive_crossing_frames = max(0, self.consecutive_crossing_frames - 1)

        is_crossing = (self.consecutive_crossing_frames >= 2 and ttc < 5.0)
        return {
            'is_pedestrian_crossing': is_crossing,
            'lateral_speed': float(v_lat),
            'ttc': float(ttc)
        }

