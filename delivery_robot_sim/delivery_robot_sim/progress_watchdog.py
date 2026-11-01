"""Progress Watchdog for Autonomous Delivery Navigation.

Monitors distance reduction toward active waypoint and heading error convergence.
Detects rotation loops, controller stalls, route blockages, and safety stops.
Provides structured diagnostic telemetry and triggers bounded recovery when safe.
"""
from dataclasses import dataclass
import math
from typing import Optional, Tuple


@dataclass
class WatchdogStatus:
    state: str                 # "NORMAL", "ROTATING", "PROGRESS_STALL", "ROTATION_STALL", "SAFE_STOP"
    stall_detected: bool = False
    stall_reason: str = "NONE"
    recovery_action: str = "NONE"  # "NONE", "REALIGN_IN_PLACE", "RESET_BYPASS", "SAFE_STOP"
    dist_to_wp: float = 0.0
    heading_error: float = 0.0
    time_without_progress_s: float = 0.0
    stall_count: int = 0


class ProgressWatchdog:
    """Explicit progress watchdog as required by project specification."""

    def __init__(self,
                 progress_timeout_s: float = 12.0,
                 min_progress_dist_m: float = 0.20,
                 rotation_timeout_s: float = 10.0,
                 stall_speed_thresh: float = 0.04,
                 max_recovery_attempts: int = 2):
        self.progress_timeout_s = progress_timeout_s
        self.min_progress_dist_m = min_progress_dist_m
        self.rotation_timeout_s = rotation_timeout_s
        self.stall_speed_thresh = stall_speed_thresh
        self.max_recovery_attempts = max_recovery_attempts

        self.active_target_name = "NONE"
        self.active_wp = (0.0, 0.0)
        self.min_dist_to_wp = 999.0
        self.last_progress_time = 0.0
        self.rotation_start_time = None
        self.stall_count = 0
        self.recovery_attempts = 0
        self.last_recovery_time = 0.0
        self.is_stalled = False
        self.stall_reason = "NONE"

    def reset_target(self, now: float, target_name: str, target_wp: Tuple[float, float], current_xy: Tuple[float, float]):
        """Call when active waypoint or mission target changes."""
        self.active_target_name = target_name
        self.active_wp = target_wp
        self.min_dist_to_wp = math.hypot(target_wp[0] - current_xy[0], target_wp[1] - current_xy[1])
        self.last_progress_time = now
        self.rotation_start_time = None
        self.recovery_attempts = 0
        self.is_stalled = False
        self.stall_reason = "NONE"

    def evaluate(self,
                 now: float,
                 current_xy: Tuple[float, float],
                 target_wp: Tuple[float, float],
                 heading_err: float,
                 cmd_v: float,
                 cmd_w: float,
                 actual_v: float,
                 safety_state: str = "NORMAL",
                 is_paused: bool = False) -> WatchdogStatus:
        """Evaluate route progress over time."""
        dist = math.hypot(target_wp[0] - current_xy[0], target_wp[1] - current_xy[1])

        # If operationally paused (dwell, red light, parking), hold watchdog
        if is_paused:
            self.last_progress_time = now
            self.rotation_start_time = None
            self.is_stalled = False
            return WatchdogStatus(
                state="NORMAL",
                stall_detected=False,
                stall_reason="PAUSED_NOMINAL",
                dist_to_wp=dist,
                heading_error=heading_err,
                time_without_progress_s=0.0,
                stall_count=self.stall_count
            )

        # 1. Check if robot made meaningful progress toward target
        if dist < (self.min_dist_to_wp - self.min_progress_dist_m):
            self.min_dist_to_wp = dist
            self.last_progress_time = now
            self.is_stalled = False
            self.stall_reason = "NONE"

        # 2. Track in-place rotation duration (only when robot is stopped in forward motion)
        is_rotating = (abs(cmd_w) > 0.20 and abs(heading_err) > 0.45 and actual_v < self.stall_speed_thresh)
        if is_rotating:
            if self.rotation_start_time is None:
                self.rotation_start_time = now
            rotation_duration = now - self.rotation_start_time
        else:
            self.rotation_start_time = None
            rotation_duration = 0.0

        time_without_progress = (now - self.last_progress_time) if self.last_progress_time is not None else 0.0

        # 3. Detect Rotation Convergence Stall (circling or stuck spinning)
        if rotation_duration > self.rotation_timeout_s:
            self.is_stalled = True
            self.stall_count += 1
            reason = "ROTATION_CONVERGENCE_STALL"
            action = "REALIGN_IN_PLACE" if self.recovery_attempts < self.max_recovery_attempts else "SAFE_STOP"
            if action != "SAFE_STOP":
                self.recovery_attempts += 1
                self.rotation_start_time = now
            return WatchdogStatus(
                state="ROTATION_STALL",
                stall_detected=True,
                stall_reason=reason,
                recovery_action=action,
                dist_to_wp=dist,
                heading_error=heading_err,
                time_without_progress_s=time_without_progress,
                stall_count=self.stall_count
            )

        # 4. Detect Progress Stall (distance not decreasing)
        if time_without_progress > self.progress_timeout_s:
            self.is_stalled = True
            self.stall_count += 1

            # Identify failure root cause
            if safety_state not in ("NORMAL", "REDUCED_SPEED", "WAITING_FOR_ORDER"):
                reason = f"SAFETY_INTERVENTION_{safety_state}"
                action = "NONE"  # Let safety supervisor handle its own protocol
            elif cmd_v > 0.10 and actual_v < self.stall_speed_thresh:
                reason = "PHYSICAL_OBSTRUCTION_OR_WHEEL_SLIP"
                action = "RESET_BYPASS" if self.recovery_attempts < self.max_recovery_attempts else "SAFE_STOP"
            elif abs(heading_err) > 0.40:
                reason = "HEADING_MISALIGNMENT"
                action = "REALIGN_IN_PLACE"
            elif cmd_v <= 0.05:
                reason = "VELOCITY_STARVATION"
                action = "RESET_BYPASS"
            else:
                reason = "DISTANCE_TO_TARGET_NOT_DECREASING"
                action = "RESET_BYPASS" if self.recovery_attempts < self.max_recovery_attempts else "SAFE_STOP"

            if action in ("REALIGN_IN_PLACE", "RESET_BYPASS"):
                self.recovery_attempts += 1
                self.last_progress_time = now

            return WatchdogStatus(
                state="PROGRESS_STALL",
                stall_detected=True,
                stall_reason=reason,
                recovery_action=action,
                dist_to_wp=dist,
                heading_error=heading_err,
                time_without_progress_s=time_without_progress,
                stall_count=self.stall_count
            )

        # Nominal progress
        state = "ROTATING" if is_rotating else "NORMAL"
        return WatchdogStatus(
            state=state,
            stall_detected=False,
            stall_reason="NONE",
            recovery_action="NONE",
            dist_to_wp=dist,
            heading_error=heading_err,
            time_without_progress_s=time_without_progress,
            stall_count=self.stall_count
        )
