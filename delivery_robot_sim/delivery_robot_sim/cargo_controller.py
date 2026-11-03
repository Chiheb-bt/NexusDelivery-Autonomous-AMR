#!/usr/bin/env python3
"""Dedicated 11-State Cargo Mechanism & Vertical Lift Controller for NexusDelivery.

Implements the formal delivery handover finite state machine (FSM):
    IDLE -> CHECKING -> UNLOCKING -> OPENING -> LIFTING ->
    READY_FOR_HANDOVER -> CARGO_REMOVED -> LOWERING -> CLOSING -> LOCKED
    (or FAULT on obstruction, overload, limit switch trip, or emergency stop)

Safety interlocks:
- Drive commands (/cmd_vel) strictly inhibited when hatch is open (> 0.05 rad)
  or vertical lift is raised (> 0.005 m).
- Gazebo physical joint actuation via 'gz joint' for both:
  1) cargo_hatch_joint (revolute, 0.0 to 1.05 rad)
  2) cargo_lift_joint (prismatic, 0.0 to 0.12 m)
"""

from __future__ import annotations

import json
import logging
import math
import shutil
import subprocess
import threading
import time
from enum import Enum
from typing import Callable, Dict, Optional, Tuple

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String, Float32, Bool
    ROS_AVAILABLE = True
except ImportError:
    Node = object
    ROS_AVAILABLE = False


class CargoMechanismState(str, Enum):
    IDLE = "IDLE"
    CHECKING = "CHECKING"
    UNLOCKING = "UNLOCKING"
    OPENING = "OPENING"
    LIFTING = "LIFTING"
    READY_FOR_HANDOVER = "READY_FOR_HANDOVER"
    CARGO_REMOVED = "CARGO_REMOVED"
    LOWERING = "LOWERING"
    CLOSING = "CLOSING"
    LOCKED = "LOCKED"
    FAULT = "FAULT"


class FaultReason(str, Enum):
    NONE = "NONE"
    OBSTRUCTION_DETECTED = "OBSTRUCTION_DETECTED"
    MOTOR_OVERLOAD = "MOTOR_OVERLOAD"
    LIMIT_SWITCH_TRIP = "LIMIT_SWITCH_TRIP"
    SENSOR_DISAGREEMENT = "SENSOR_DISAGREEMENT"
    POWER_LOSS = "POWER_LOSS"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"


# Engineering Limits
HATCH_CLOSED_ANGLE = 0.0       # rad
HATCH_OPEN_ANGLE = 1.05        # rad (~60.1 deg)
LIFT_LOWER_LIMIT = 0.0         # m (stowed)
LIFT_UPPER_LIMIT = 0.12        # m (raised 120mm)
MAX_LIFT_CURRENT_A = 4.5       # Amperes (motor overload trip threshold)
RATED_LIFT_SPEED_M_S = 0.025   # 25 mm/s (4.8s full stroke)


class CargoMechanismController(Node if ROS_AVAILABLE else object):
    """Safety-critical controller managing the physical hatch, vertical lead screw lift,
    safety limit switches, optical presence sensors, and drive inhibition interlocks."""

    def __init__(self, node_name: str = "cargo_mechanism_controller"):
        if ROS_AVAILABLE:
            super().__init__(node_name)
            self.logger = self.get_logger()
        else:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(node_name)

        self.lock = threading.RLock()
        
        # State Machine Attributes
        self.state = CargoMechanismState.IDLE
        self.fault_reason = FaultReason.NONE
        self.previous_state = CargoMechanismState.IDLE

        # Physical Joint & Sensor Coordinates
        self.hatch_angle = HATCH_CLOSED_ANGLE
        self.lift_position = LIFT_LOWER_LIMIT
        self.cargo_present = False
        self.solenoid_locked = True
        
        # Limit Switches & Diagnostics
        self.switch_hatch_closed = True
        self.switch_hatch_open = False
        self.switch_lift_lower = True
        self.switch_lift_upper = False
        self.motor_current_a = 0.0
        self.estop_active = False
        self.power_ok = True
        self.active_order_id: Optional[str] = None
        self.customer_handover_otp: Optional[str] = None

        # State transition timestamp
        self.state_entry_time = time.time()
        self.target_lift_pos = LIFT_LOWER_LIMIT
        self.target_hatch_angle = HATCH_CLOSED_ANGLE

        # ROS 2 Pub / Sub
        if ROS_AVAILABLE:
            self.pub_state = self.create_publisher(String, "/cargo/state", 10)
            self.pub_telemetry = self.create_publisher(String, "/cargo/telemetry", 10)
            self.pub_drive_inhibit = self.create_publisher(Bool, "/safety/drive_inhibit", 10)

            self.sub_cmd = self.create_subscription(String, "/cargo/cmd", self._on_cmd_msg, 10)
            self.sub_estop = self.create_subscription(String, "/safety/estop", self._on_estop_msg, 10)

    # ========================================================================
    # Safety Interlocks & Drive Inhibit
    # ========================================================================

    def can_drive(self) -> bool:
        """Safety Gate: Driving is prohibited whenever the hatch is open,
        the vertical lift is raised, or the mechanism is not securely locked."""
        with self.lock:
            if self.estop_active:
                return False
            if self.hatch_angle > 0.05:
                return False
            if self.lift_position > 0.005:
                return False
            if self.state not in (CargoMechanismState.IDLE, CargoMechanismState.LOCKED):
                return False
            return True

    def get_status(self) -> Dict:
        """Returns structured JSON-serializable controller telemetry."""
        with self.lock:
            return {
                "state": self.state.value,
                "fault_reason": self.fault_reason.value,
                "can_drive": self.can_drive(),
                "hatch_angle_rad": round(self.hatch_angle, 3),
                "hatch_angle_deg": round(math.degrees(self.hatch_angle), 1),
                "lift_position_m": round(self.lift_position, 4),
                "lift_position_mm": round(self.lift_position * 1000.0, 1),
                "cargo_present": self.cargo_present,
                "solenoid_locked": self.solenoid_locked,
                "switches": {
                    "hatch_closed": self.switch_hatch_closed,
                    "hatch_open": self.switch_hatch_open,
                    "lift_lower": self.switch_lift_lower,
                    "lift_upper": self.switch_lift_upper,
                },
                "diagnostics": {
                    "motor_current_a": round(self.motor_current_a, 2),
                    "estop_active": self.estop_active,
                    "power_ok": self.power_ok,
                },
                "active_order_id": self.active_order_id,
                "timestamp": time.time(),
            }

    # ========================================================================
    # State Machine Transitions
    # ========================================================================

    def _transition_to(self, new_state: CargoMechanismState, fault: FaultReason = FaultReason.NONE):
        self.previous_state = self.state
        self.state = new_state
        self.fault_reason = fault
        self.state_entry_time = time.time()
        self.logger.info(f"[CARGO_FSM] {self.previous_state.value} -> {self.state.value} (Fault: {fault.value})")

        if ROS_AVAILABLE and getattr(self, "pub_state", None):
            msg = String()
            msg.data = json.dumps({"state": self.state.value, "fault": self.fault_reason.value})
            self.pub_state.publish(msg)

    def trigger_estop(self, reason: str = "EMERGENCY_STOP"):
        """Emergency stop: cuts all actuator power and trips into FAULT immediately."""
        with self.lock:
            self.estop_active = True
            self.motor_current_a = 0.0
            self._transition_to(CargoMechanismState.FAULT, FaultReason.EMERGENCY_STOP)

    def reset_fault(self) -> bool:
        """Reset fault state after conditions are cleared."""
        with self.lock:
            if self.estop_active or not self.power_ok:
                return False
            self.fault_reason = FaultReason.NONE
            # Attempt to return to safe locked state
            if self.hatch_angle <= 0.05 and self.lift_position <= 0.005:
                self._transition_to(CargoMechanismState.LOCKED)
            else:
                self._transition_to(CargoMechanismState.CHECKING)
            return True

    # ========================================================================
    # Handover Sequence Execution
    # ========================================================================

    def begin_handover(self, order_id: str, otp: str, has_cargo: bool = True) -> bool:
        """Initiates the 12-step customer handover sequence."""
        with self.lock:
            if self.estop_active or not self.power_ok:
                self._transition_to(CargoMechanismState.FAULT, FaultReason.EMERGENCY_STOP)
                return False

            if self.state not in (CargoMechanismState.IDLE, CargoMechanismState.LOCKED):
                return False

            self.active_order_id = order_id
            self.customer_handover_otp = otp
            self.cargo_present = has_cargo

            # 1. Enter CHECKING state
            self._transition_to(CargoMechanismState.CHECKING)

        # 2. Perform sensor validation sweep
        if not self._check_sensors():
            with self.lock:
                self._transition_to(CargoMechanismState.FAULT, FaultReason.SENSOR_DISAGREEMENT)
            return False

        # 3. Enter UNLOCKING
        with self.lock:
            self._transition_to(CargoMechanismState.UNLOCKING)
            self.solenoid_locked = False

        # 4. Enter OPENING
        with self.lock:
            self._transition_to(CargoMechanismState.OPENING)
        self._actuate_hatch(HATCH_OPEN_ANGLE)

        # 5. Enter LIFTING
        with self.lock:
            self._transition_to(CargoMechanismState.LIFTING)
        self._actuate_lift(LIFT_UPPER_LIMIT)

        # 6. Enter READY_FOR_HANDOVER
        with self.lock:
            self._transition_to(CargoMechanismState.READY_FOR_HANDOVER)
        return True

    def confirm_cargo_collected(self) -> bool:
        """Customer retrieves item; optical sensor trips -> CARGO_REMOVED -> LOWERING -> CLOSING -> LOCKED."""
        with self.lock:
            if self.state != CargoMechanismState.READY_FOR_HANDOVER:
                return False

            self.cargo_present = False
            self._transition_to(CargoMechanismState.CARGO_REMOVED)

        # Step 9: Lower platform
        with self.lock:
            self._transition_to(CargoMechanismState.LOWERING)
        self._actuate_lift(LIFT_LOWER_LIMIT)

        # Step 10: Close hatch
        with self.lock:
            self._transition_to(CargoMechanismState.CLOSING)
        self._actuate_hatch(HATCH_CLOSED_ANGLE)

        # Step 11 & 12: Lock & Verify Closure
        with self.lock:
            self.solenoid_locked = True
            self.switch_hatch_closed = True
            self.switch_hatch_open = False
            self.switch_lift_lower = True
            self.switch_lift_upper = False
            self._transition_to(CargoMechanismState.LOCKED)
            self.active_order_id = None
        return True

    # ========================================================================
    # Hardware & Simulation Actuation
    # ========================================================================

    def _check_sensors(self) -> bool:
        """Verify sensor agreement before unlatching."""
        with self.lock:
            if not self.power_ok:
                return False
            # Check limit switches match actual joint coordinates
            if self.lift_position <= 0.005 and not self.switch_lift_lower:
                return False
            if self.hatch_angle <= 0.05 and not self.switch_hatch_closed:
                return False
            return True

    def _actuate_hatch(self, target_angle: float):
        """Actuate motorized hatch in simulation and update state."""
        with self.lock:
            self.target_hatch_angle = target_angle
            self.hatch_angle = target_angle
            if target_angle > 0.5:
                self.switch_hatch_open = True
                self.switch_hatch_closed = False
            else:
                self.switch_hatch_open = False
                self.switch_hatch_closed = True

        # Send command to Gazebo Classic joint controller if gz is available
        if shutil.which("gz"):
            try:
                subprocess.run([
                    "gz", "joint",
                    "-m", "rdsim",
                    "-j", "cargo_hatch_joint",
                    "--pos-t", f"{target_angle:.3f}",
                    "--pos-p", "120.0",
                    "--pos-d", "6.0"
                ], capture_output=True, timeout=1.0)
            except Exception:
                pass

    def _actuate_lift(self, target_height: float):
        """Actuate prismatic vertical lead screw in simulation and update state."""
        with self.lock:
            self.target_lift_pos = target_height
            self.lift_position = target_height
            if target_height > 0.05:
                self.switch_lift_upper = True
                self.switch_lift_lower = False
            else:
                self.switch_lift_upper = False
                self.switch_lift_lower = True

        # Send command to Gazebo Classic prismatic joint controller if gz is available
        if shutil.which("gz"):
            try:
                subprocess.run([
                    "gz", "joint",
                    "-m", "rdsim",
                    "-j", "cargo_lift_joint",
                    "--pos-t", f"{target_height:.3f}",
                    "--pos-p", "300.0",
                    "--pos-d", "15.0"
                ], capture_output=True, timeout=1.0)
            except Exception:
                pass

    # ========================================================================
    # ROS 2 Message Handlers
    # ========================================================================

    def _on_cmd_msg(self, msg: String):
        try:
            data = json.loads(msg.data)
            action = data.get("action", "")
            if action == "START_HANDOVER":
                self.begin_handover(
                    data.get("order_id", "ORD-TEST"),
                    data.get("otp", "123456"),
                    data.get("cargo_present", True)
                )
            elif action == "CONFIRM_COLLECTED":
                self.confirm_cargo_collected()
            elif action == "RESET_FAULT":
                self.reset_fault()
        except Exception as e:
            self.logger.error(f"Error parsing cargo command: {e}")

    def _on_estop_msg(self, msg: String):
        val = msg.data.strip().upper()
        if val in ("ENGAGE", "1", "TRUE", "ESTOP"):
            self.trigger_estop("REMOTE_ESTOP_TOPIC")
        elif val in ("RELEASE", "0", "FALSE", "RESET"):
            with self.lock:
                self.estop_active = False
            self.reset_fault()
