"""Régulateur PID et machine à états de mission (sans ROS, testables).

Convention : erreur e = x_hat - x_target (pixels). The camera image is mirrored
relative to the base-link yaw convention in this model: a positive image error
requires positive angular velocity to converge to the stripe.
"""
from dataclasses import dataclass


class PID:
    def __init__(self, kp=0.012, ki=0.0, kd=0.0, i_limit=50.0, w_limit=1.5):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.i_limit, self.w_limit = i_limit, w_limit
        self.reset()

    def reset(self):
        self._i = 0.0
        self._prev = None

    def update(self, err, dt):
        dt = max(dt, 1e-3)
        self._i = max(-self.i_limit, min(self.i_limit, self._i + err * dt))  # anti-windup
        d = 0.0 if self._prev is None else (err - self._prev) / dt
        self._prev = err
        out = self.kp * err + self.ki * self._i + self.kd * d
        return max(-self.w_limit, min(self.w_limit, out))


@dataclass
class Perception:
    line_x: float = None      # barycentre (None si ligne perdue)
    obstacle_px: int = 0      # pixels orange dans la ROI obstacle
    red_area: int = 0         # aire du plus grand blob rouge
    green_area: int = 0       # aire du plus grand blob vert


@dataclass
class Command:
    state: str
    mode: str                 # "lane" (suivi PID) ou "fixed" (v, w imposés)
    v: float = 0.0
    w: float = 0.0
    narrow_roi: bool = False  # fenêtrage étroit après le dépassement


class MissionFSM:
    """FOLLOW -> STOP_RED / AVOID_LEFT -> AVOID_STRAIGHT -> AVOID_RIGHT -> REACQUIRE -> FOLLOW.

    Ou FOLLOW -> STOP_OBSTACLE si obstacle_mode == "stop".
    Politique de sécurité feux :
    - Rouge : arrêt immédiat, maintenu tant que le rouge est actif.
    - Vert : reprise uniquement si le vert est confirmé (filtrage antibruit) et le rouge dissipé.
    Politique d'évitement :
    - Le retour à FOLLOW depuis REACQUIRE exige la détection réelle de la ligne par la caméra.
    - En cas d'échec de réacquisition avant timeout, arrêt de sécurité (LOST_LINE_STOP).
    """

    def __init__(self, v_base=0.25, t_left=0.55, t_straight=4.5, t_right=1.0,
                 t_reacquire=8.0, lockout=12.0, w_avoid=1.0,
                 thr_obstacle=400, thr_red=150, thr_green=40, lost_timeout=1.0,
                 obstacle_mode="avoid", x_target=162.0, green_confirm_frames=1):
        self.v_base, self.v_avoid = v_base, v_base
        self.t_left, self.t_straight, self.t_right = t_left, t_straight, t_right
        self.t_reacquire, self.lockout = t_reacquire, lockout
        self.w_left = w_avoid
        self.w_right = -w_avoid * t_left / t_right   # cap net nul
        self.thr_obstacle, self.thr_red, self.thr_green = thr_obstacle, thr_red, thr_green
        self.lost_timeout = lost_timeout
        self.obstacle_mode = obstacle_mode
        self.x_target = x_target
        self.green_confirm_frames = green_confirm_frames

        self.state = "FOLLOW"
        self._t0 = 0.0
        self._lockout_until = 0.0
        self._lost_since = None
        self._green_counter = 0

    def _goto(self, state, now):
        self.state, self._t0 = state, now
        if state != "STOP_RED":
            self._green_counter = 0

    def update(self, now, p: Perception):
        s = self.state

        if s == "FOLLOW":
            if p.red_area >= self.thr_red:
                self._goto("STOP_RED", now)
            elif p.obstacle_px >= self.thr_obstacle and now >= self._lockout_until:
                if self.obstacle_mode == "stop":
                    self._goto("STOP_OBSTACLE", now)
                else:
                    self._goto("AVOID_LEFT", now)

        elif s == "STOP_RED":
            # Si le rouge reste actif, réinitialiser le compteur de confirmation verte
            if p.red_area >= self.thr_red:
                self._green_counter = 0
            elif p.green_area >= self.thr_green:
                self._green_counter += 1
                if self._green_counter >= self.green_confirm_frames:
                    self._goto("FOLLOW", now)
            else:
                self._green_counter = 0

        elif s == "STOP_OBSTACLE":
            if p.obstacle_px < self.thr_obstacle:
                self._goto("FOLLOW", now)

        elif s == "AVOID_LEFT" and now - self._t0 >= self.t_left:
            self._goto("AVOID_STRAIGHT", now)

        elif s == "AVOID_STRAIGHT" and now - self._t0 >= self.t_straight:
            self._goto("AVOID_RIGHT", now)

        elif s == "AVOID_RIGHT" and now - self._t0 >= self.t_right:
            self._goto("REACQUIRE", now)

        elif s == "REACQUIRE":
            # Confirmation de réacquisition par la perception caméra :
            # La ligne est visible et proche du centre visé
            if p.line_x is not None and abs(p.line_x - self.x_target) < 50.0:
                self._lockout_until = now + self.lockout
                self._goto("FOLLOW", now)
            elif now - self._t0 >= self.t_reacquire:
                # Échec de réacquisition après expiration du délai imparti
                if p.line_x is not None:
                    # Ligne aperçue même si excentrée : autorise poursuite prudente
                    self._lockout_until = now + self.lockout
                    self._goto("FOLLOW", now)
                else:
                    self._goto("LOST_LINE_STOP", now)

        elif s == "LOST_LINE_STOP":
            # Arrêt d'urgence sécurisé : ne reprend que si la caméra retrouve la ligne
            if p.line_x is not None:
                self._goto("FOLLOW", now)

        s = self.state
        if s in ("STOP_RED", "STOP_OBSTACLE", "LOST_LINE_STOP"):
            return Command(s, "fixed", 0.0, 0.0)
        if s == "AVOID_LEFT":
            return Command(s, "fixed", self.v_avoid, self.w_left)
        if s == "AVOID_STRAIGHT":
            return Command(s, "fixed", self.v_avoid, 0.0)
        if s == "AVOID_RIGHT":
            return Command(s, "fixed", self.v_avoid, self.w_right)

        # Mode suivi de ligne (FOLLOW ou REACQUIRE)
        if p.line_x is None:
            self._lost_since = self._lost_since if self._lost_since is not None else now
            if now - self._lost_since > self.lost_timeout:
                return Command(s, "fixed", 0.0, 0.0)  # Arrêt de sécurité
            return Command(s, "lane", self.v_base * 0.5, 0.0, s == "REACQUIRE")

        self._lost_since = None
        return Command(s, "lane", self.v_base, 0.0, s == "REACQUIRE")


class SmoothMotionController:
    """Smooth velocity profiler, critically-damped steering controller, and rate limiter.
    
    Guarantees:
    - Progressive acceleration from rest (no instantaneous speed jumps).
    - Smooth approach deceleration toward waypoints, delivery stops, and docking.
    - Curvature-adaptive speed scaling during turns.
    - Critically-damped steering (P-heading + D-yaw-rate) to eliminate oscillation/zigzagging.
    - Immediate emergency stops (zero delay on safety triggers).
    - Inner wheel anti-stall velocity allocation for differential drive.
    """

    def __init__(self,
                 max_v=0.50,
                 max_w=0.65,
                 max_accel=0.60,
                 max_decel_normal=0.80,
                 max_w_accel=1.20,
                 kp_w=1.20,
                 kd_w=0.22,
                 approach_dist=4.5,
                 docking_speed=0.18,
                 wheel_track=0.62):
        self.max_v = max_v
        self.max_w = max_w
        self.max_accel = max_accel
        self.max_decel_normal = max_decel_normal
        self.max_w_accel = max_w_accel
        self.kp_w = kp_w
        self.kd_w = kd_w
        self.approach_dist = approach_dist
        self.docking_speed = docking_speed
        self.wheel_track = wheel_track
        self._prev_heading_err = None

    def reset(self):
        self._prev_heading_err = None

    def compute_approach_speed(self, dist_to_target: float, cruise_speed: float = None) -> float:
        """Progressive deceleration profile when approaching target or waypoint."""
        import math
        v_cruise = cruise_speed if cruise_speed is not None else self.max_v
        if dist_to_target > self.approach_dist:
            return v_cruise
        ratio = max(0.0, dist_to_target / max(0.01, self.approach_dist))
        v_decel = self.docking_speed + (v_cruise - self.docking_speed) * math.sqrt(ratio)
        return max(self.docking_speed, min(v_cruise, v_decel))

    def compute_turn_speed(self, heading_err: float, base_speed: float, curvature_factor: float = 1.25) -> float:
        """Smoothly scale down linear speed on sharp turns."""
        scale = 1.0 / (1.0 + curvature_factor * abs(heading_err))
        return max(0.18, base_speed * scale)

    def compute_steering(self, heading_err: float, yaw_rate: float = 0.0, dt: float = 0.05) -> float:
        """Critically damped steering correction to eliminate zigzag oscillations."""
        if abs(yaw_rate) > 1e-4:
            d_term = yaw_rate
        elif self._prev_heading_err is not None and dt > 1e-4:
            d_term = (heading_err - self._prev_heading_err) / dt
        else:
            d_term = 0.0

        self._prev_heading_err = heading_err
        w = self.kp_w * heading_err - self.kd_w * d_term
        return max(-self.max_w, min(self.max_w, w))

    def compute_in_place_turn(self, heading_err: float, yaw_rate: float = 0.0, dt: float = 0.05, min_w: float = 0.35) -> float:
        """Compute angular velocity for pure in-place rotation towards target heading."""
        import math
        abs_err = abs(heading_err)
        w_mag = min(self.max_w, max(min_w, self.kp_w * abs_err))
        w_cmd = math.copysign(w_mag, heading_err)
        if abs(yaw_rate) > 1e-4:
            w_cmd -= self.kd_w * yaw_rate
        return max(-self.max_w, min(self.max_w, w_cmd))

    def ramp_velocities(self,
                        current_v: float,
                        current_w: float,
                        target_v: float,
                        target_w: float,
                        dt: float = 0.05,
                        is_emergency_stop: bool = False):
        """Apply acceleration limits while ensuring safety stops remain instantaneous."""
        if is_emergency_stop:
            return 0.0, 0.0

        dt = max(1e-4, min(0.2, dt))

        max_dv_up = self.max_accel * dt
        max_dv_down = self.max_decel_normal * dt

        if target_v > current_v:
            new_v = current_v + min(target_v - current_v, max_dv_up)
        else:
            new_v = current_v + max(target_v - current_v, -max_dv_down)

        max_dw = self.max_w_accel * dt
        new_w = current_w + max(-max_dw, min(max_dw, target_w - current_w))

        # Inner wheel anti-stall clamp applies only during forward rolling (target_v > 0.05 and new_v > 0.05),
        # not during pure in-place differential pivot where wheels rotate in opposite directions.
        if new_v > 0.05 and target_v > 0.05:
            half_b = self.wheel_track / 2.0
            max_w_allowed = min(self.max_w, max(0.25, (new_v - 0.04) / half_b))
            new_w = max(-max_w_allowed, min(max_w_allowed, new_w))

        return new_v, new_w

