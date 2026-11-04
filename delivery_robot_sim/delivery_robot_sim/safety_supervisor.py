"""Dedicated Safety Supervisor for Autonomous Delivery Robots (ROS 2 / Embedded Pure Python).

Centralized safety authority ensuring fail-safe operation:
- Monitors sensor freshness (camera, depth, IMU, odometry timeouts).
- Monitors motor stall / wheel slip.
- Monitors obstacle proximity and dynamic pedestrian intrusion.
- Enforces deterministic, prioritised state transitions:
  INITIALIZING -> NORMAL_OPERATION -> REDUCED_SPEED -> WAITING_FOR_CLEAR_PATH
  -> REPLANNING -> SAFE_STOP -> FAULT_LATCHED -> RECOVERY_CHECK -> HUMAN_ASSISTANCE_REQUIRED
  -> EMERGENCY_STOP.
- Enforces fault latching (critical faults cannot be cleared by a timer).
- Guarantees immediate zero-delay safety stops overriding normal navigation.
"""

from enum import Enum
from typing import Optional, Tuple


class SafetySupervisorState(str, Enum):
    INITIALIZING = 'INITIALIZING'
    NORMAL_OPERATION = 'NORMAL_OPERATION'
    REDUCED_SPEED = 'REDUCED_SPEED'
    WAITING_FOR_CLEAR_PATH = 'WAITING_FOR_CLEAR_PATH'
    REPLANNING = 'REPLANNING'
    SAFE_STOP = 'SAFE_STOP'
    FAULT_LATCHED = 'FAULT_LATCHED'
    RECOVERY_CHECK = 'RECOVERY_CHECK'
    HUMAN_ASSISTANCE_REQUIRED = 'HUMAN_ASSISTANCE_REQUIRED'
    EMERGENCY_STOP = 'EMERGENCY_STOP'


class SafetySupervisor:
    """Deterministic Safety Supervisor ensuring safety priorities always override navigation."""

    def __init__(self,
                 sensor_timeout_s: float = 0.50,
                 patience_timeout_s: float = 8.0,
                 stall_timeout_s: float = 2.5,
                 min_safe_clearance_m: float = 0.65,
                 reduced_speed_clearance_m: float = 3.2,
                 recovery_dwell_s: float = 1.0,
                 nominal_speed_limit: float = 0.55):
        self.sensor_timeout_s = sensor_timeout_s
        self.patience_timeout_s = patience_timeout_s
        self.stall_timeout_s = stall_timeout_s
        self.min_safe_clearance_m = min_safe_clearance_m
        self.reduced_speed_clearance_m = reduced_speed_clearance_m
        self.recovery_dwell_s = recovery_dwell_s
        self.nominal_speed_limit = nominal_speed_limit

        self.state = SafetySupervisorState.INITIALIZING
        self.latched_fault_reason: Optional[str] = None
        self.waiting_since: Optional[float] = None
        self.stall_since: Optional[float] = None
        self.recovery_since: Optional[float] = None
        self.emergency_stop_latched = False

    def assert_emergency_stop(self, reason: str = 'MANUAL_ESTOP_ASSERTED'):
        """Immediate software/hardware emergency stop latch."""
        self.emergency_stop_latched = True
        self.latched_fault_reason = reason
        self.state = SafetySupervisorState.EMERGENCY_STOP

    def release_emergency_stop(self):
        """Operator unlatch of emergency stop."""
        self.emergency_stop_latched = False
        self.latched_fault_reason = None
        self.state = SafetySupervisorState.RECOVERY_CHECK
        self.recovery_since = None

    def clear_latched_fault(self) -> bool:
        """Attempt to clear a latched fault through active recovery check."""
        if self.emergency_stop_latched:
            return False
        if self.state in (SafetySupervisorState.FAULT_LATCHED, SafetySupervisorState.HUMAN_ASSISTANCE_REQUIRED):
            self.state = SafetySupervisorState.RECOVERY_CHECK
            self.latched_fault_reason = None
            self.recovery_since = None
            return True
        return False

    def evaluate(self,
                 now: float,
                 camera_age: float,
                 depth_age: float,
                 imu_age: float,
                 odom_age: float,
                 min_obstacle_dist: float,
                 is_pedestrian_crossing: bool = False,
                 cmd_v: float = 0.0,
                 actual_v: float = 0.0,
                 red_light_active: bool = False,
                 emergency_stop: bool = False) -> Tuple[SafetySupervisorState, float, Optional[Tuple[float, float]], str]:
        """Evaluate safety rules and return (state, max_v_allowed, override_twist, reason).
        
        override_twist is None if normal navigation control is permitted.
        If override_twist is (v, w), navigation command MUST be overridden.
        """
        # 1. EMERGENCY STOP (Highest Priority)
        if emergency_stop or self.emergency_stop_latched:
            self.emergency_stop_latched = True
            self.state = SafetySupervisorState.EMERGENCY_STOP
            return self.state, 0.0, (0.0, 0.0), 'EMERGENCY_STOP_ACTIVE'

        # 2. SENSOR FRESHNESS CHECK (Hardware/Driver Watchdog)
        stale_sensors = []
        if camera_age > self.sensor_timeout_s:
            stale_sensors.append(f'CAM({camera_age:.2f}s)')
        if depth_age > self.sensor_timeout_s:
            stale_sensors.append(f'DEPTH({depth_age:.2f}s)')
        if imu_age > self.sensor_timeout_s:
            stale_sensors.append(f'IMU({imu_age:.2f}s)')
        if odom_age > self.sensor_timeout_s:
            stale_sensors.append(f'ODOM({odom_age:.2f}s)')

        if stale_sensors:
            self.state = SafetySupervisorState.FAULT_LATCHED
            self.latched_fault_reason = 'SENSOR_TIMEOUT: ' + ', '.join(stale_sensors)
            return self.state, 0.0, (0.0, 0.0), self.latched_fault_reason

        # 3. MOTOR STALL / WHEEL SLIP DETECTION
        # Commanded forward velocity > 0.15 m/s but actual odometry velocity < 0.02 m/s
        if abs(cmd_v) > 0.15 and abs(actual_v) < 0.02 and not red_light_active and min_obstacle_dist > self.min_safe_clearance_m:
            if self.stall_since is None:
                self.stall_since = now
            elif now - self.stall_since > self.stall_timeout_s:
                self.state = SafetySupervisorState.FAULT_LATCHED
                self.latched_fault_reason = f'MOTOR_STALL_DETECTED ({now - self.stall_since:.1f}s stuck)'
                return self.state, 0.0, (0.0, 0.0), self.latched_fault_reason
        else:
            self.stall_since = None

        # 4. HANDLE LATCHED FAULT STATE
        if self.state == SafetySupervisorState.FAULT_LATCHED:
            if not stale_sensors and self.latched_fault_reason and 'SENSOR_TIMEOUT' in self.latched_fault_reason:
                # Sensors have recovered: transition to active RECOVERY_CHECK to verify stability
                self.state = SafetySupervisorState.RECOVERY_CHECK
                self.latched_fault_reason = None
                self.recovery_since = None
            else:
                return self.state, 0.0, (0.0, 0.0), (self.latched_fault_reason or 'FAULT_LATCHED')

        # 5. HANDLE RECOVERY CHECK STATE
        if self.state == SafetySupervisorState.RECOVERY_CHECK:
            if min_obstacle_dist < self.min_safe_clearance_m or red_light_active:
                # Recovery blocked by environment
                self.recovery_since = None
                return self.state, 0.0, (0.0, 0.0), 'RECOVERY_CHECK_WAITING_CLEARANCE'
            if self.recovery_since is None:
                self.recovery_since = now
                return self.state, 0.0, (0.0, 0.0), 'RECOVERY_CHECK_OBSERVING'
            elif now - self.recovery_since >= self.recovery_dwell_s:
                # Diagnostics confirmed: return to normal
                self.state = SafetySupervisorState.NORMAL_OPERATION
                self.recovery_since = None
            else:
                return self.state, 0.0, (0.0, 0.0), 'RECOVERY_CHECK_CONFIRMING'

        # 6. TRAFFIC LIGHT RED STOP (Safety Stop)
        if red_light_active:
            self.state = SafetySupervisorState.SAFE_STOP
            self.waiting_since = None
            return self.state, 0.0, (0.0, 0.0), 'TRAFFIC_LIGHT_RED'

        # 7. CRITICAL OBSTACLE STOP (Distance < safe clearance)
        if min_obstacle_dist < self.min_safe_clearance_m:
            self.state = SafetySupervisorState.SAFE_STOP
            self.waiting_since = None
            return self.state, 0.0, (0.0, 0.0), f'OBSTACLE_STOP (dist={min_obstacle_dist:.2f}m)'

        # 8. PEDESTRIAN CROSSING / CORRIDOR INTRUSION (Yielding & Waiting)
        if is_pedestrian_crossing or (min_obstacle_dist < 1.40 and abs(actual_v) < 0.05):
            if self.waiting_since is None:
                self.waiting_since = now
                self.state = SafetySupervisorState.WAITING_FOR_CLEAR_PATH
                return self.state, 0.0, (0.0, 0.0), 'YIELDING_FOR_PEDESTRIAN'

            wait_duration = now - self.waiting_since
            if wait_duration > self.patience_timeout_s:
                # Blockage prolonged -> trigger replanning / detour
                self.state = SafetySupervisorState.REPLANNING
                return self.state, 0.18, None, f'PATIENCE_TIMEOUT ({wait_duration:.1f}s) -> REPLANNING'
            else:
                self.state = SafetySupervisorState.WAITING_FOR_CLEAR_PATH
                return self.state, 0.0, (0.0, 0.0), f'WAITING_FOR_CLEAR_PATH ({wait_duration:.1f}s)'

        # Pedestrian/obstacle cleared
        self.waiting_since = None

        # 9. REDUCED SPEED (Proximity caution)
        if min_obstacle_dist <= self.reduced_speed_clearance_m:
            self.state = SafetySupervisorState.REDUCED_SPEED
            v_limit = 0.55 if min_obstacle_dist < 1.2 else min(0.95, self.nominal_speed_limit * 0.85)
            return self.state, v_limit, None, f'CAUTION_PROXIMITY (dist={min_obstacle_dist:.2f}m)'

        # 10. NOMINAL OPERATION
        self.state = SafetySupervisorState.NORMAL_OPERATION
        return self.state, self.nominal_speed_limit, None, 'NOMINAL_OPERATION'
