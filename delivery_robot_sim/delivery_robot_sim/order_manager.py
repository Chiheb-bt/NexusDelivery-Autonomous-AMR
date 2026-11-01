"""Autonomous delivery order manager: queue management, scheduling, state machine.

Pure Python logic decoupled from ROS for unit testing.
"""

import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class OrderStatus(str, Enum):
    PENDING = 'PENDING'
    ASSIGNED = 'ASSIGNED'
    GOING_TO_PICKUP = 'GOING_TO_PICKUP'
    PICKING_UP = 'PICKING_UP'
    CARRYING_PACKAGE = 'CARRYING_PACKAGE'
    GOING_TO_DELIVERY = 'GOING_TO_DELIVERY'
    DELIVERING = 'DELIVERING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


class MissionLifecycleState(str, Enum):
    """12-state autonomous delivery mission lifecycle plus recovery and failure states."""
    WAITING_FOR_ORDER = 'WAITING_FOR_ORDER'
    ORDER_ACCEPTED = 'ORDER_ACCEPTED'
    PLANNING_ROUTE = 'PLANNING_ROUTE'
    NAVIGATING_TO_CLIENT = 'NAVIGATING_TO_CLIENT'
    AVOIDING_OBSTACLE = 'AVOIDING_OBSTACLE'
    WAITING_AT_RED_LIGHT = 'WAITING_AT_RED_LIGHT'
    APPROACHING_DELIVERY_POINT = 'APPROACHING_DELIVERY_POINT'
    DELIVERING = 'DELIVERING'
    DELIVERY_CONFIRMED = 'DELIVERY_CONFIRMED'
    RETURNING_TO_DEPOT = 'RETURNING_TO_DEPOT'
    DOCKING = 'DOCKING'
    MISSION_COMPLETED = 'MISSION_COMPLETED'
    # Explicit recovery and failure states
    RECOVERING_ROUTE = 'RECOVERING_ROUTE'
    WAITING_FOR_CLEAR_PATH = 'WAITING_FOR_CLEAR_PATH'
    NAVIGATION_FAILED = 'NAVIGATION_FAILED'
    DELIVERY_FAILED = 'DELIVERY_FAILED'
    MISSION_CANCELLED = 'MISSION_CANCELLED'
    MISSION_FAILED = 'MISSION_FAILED'


PREDEFINED_LOCATIONS: Dict[str, Tuple[float, float]] = {
    'DEPOT_POST_OFFICE': (-30.0, 0.0),
    'CLIENT_1_NORTH_AVENUE': (-15.0, 15.0),
    'CLIENT_2_NORTH_AVENUE': (-15.0, 28.0),
    'CLIENT_3_NORTH_PLAZA': (-15.0, 38.0),
    'CLIENT_4_WEST_BOULEVARD': (-45.0, 15.0),
    'CLIENT_5_CENTRAL_SQUARE': (-5.0, 0.0),
    'CLIENT_6_EAST_AVENUE': (45.0, 15.0),
    'CLIENT_7_SOUTH_MARKET': (-15.0, -25.0),
    'CLIENT_8_FAR_EAST_MARINA': (108.0, 0.0),
}


@dataclass
class DeliveryOrder:
    order_id: str
    pickup_name: str
    pickup_xy: Tuple[float, float]
    delivery_name: str
    delivery_xy: Tuple[float, float]
    package_id: str
    priority: int = 2  # 1 = Urgent, 2 = Standard, 3 = Low
    created_time: float = 0.0
    deadline: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    assigned_time: Optional[float] = None
    completed_time: Optional[float] = None
    failure_reason: Optional[str] = None


from delivery_robot_sim.compartment_manager import CompartmentManager, CompartmentLockState


class OrderManager:
    """Persistent in-memory queue, order lifecycle FSM, and heuristic scheduler."""

    def __init__(self, depot_xy=(-30.0, 0.0), depot_name='DEPOT_POST_OFFICE', mission_id='MSN-001'):
        self.depot_xy = depot_xy
        self.depot_name = depot_name
        self.mission_id = mission_id
        self.orders: Dict[str, DeliveryOrder] = {}
        self.current_order: Optional[DeliveryOrder] = None
        self.carried_packages: set = set()
        self.completed_delivery_ids: set = set()
        self.compartments = CompartmentManager()
        self.mission_state = MissionLifecycleState.WAITING_FOR_ORDER.value
        self.returning_to_depot = False

    def generate_order_otp(self, order_id: str, now: float) -> Tuple[str, str]:
        """Generate dynamic 6-digit OTP and HMAC token upon arriving at client."""
        return self.compartments.generate_delivery_token(order_id, now)

    def authenticate_order_otp(self, order_id: str, candidate_otp: str, now: float) -> Tuple[bool, str]:
        """Verify candidate customer OTP to unlock cargo hatch."""
        return self.compartments.authenticate_customer(order_id, candidate_otp, now)

    @property
    def carried_package(self) -> Optional[str]:
        if self.current_order and self.current_order.package_id in self.carried_packages:
            return self.current_order.package_id
        if self.carried_packages:
            return next(iter(self.carried_packages))
        return None

    @carried_package.setter
    def carried_package(self, val: Optional[str]):
        if val is None:
            if self.current_order and self.current_order.package_id in self.carried_packages:
                self.carried_packages.discard(self.current_order.package_id)
            else:
                self.carried_packages.clear()
        else:
            self.carried_packages.add(val)

    def add_order(self, order: DeliveryOrder, now: float = 0.0) -> bool:
        """Accept a new order into the queue (dynamic order support)."""
        if order.order_id in self.orders:
            return False
        order.created_time = now if order.created_time <= 0 else order.created_time
        order.status = OrderStatus.PENDING
        self.orders[order.order_id] = order
        comp_id = f'COMPARTMENT_{min(2, len(self.orders))}'
        self.compartments.assign_package(comp_id, order.package_id, order.order_id)
        if self.mission_state == MissionLifecycleState.WAITING_FOR_ORDER.value:
            self.mission_state = MissionLifecycleState.ORDER_ACCEPTED.value
        return True


    def cancel_order(self, order_id: str, reason: str = 'User cancellation') -> bool:
        if order_id not in self.orders:
            return False
        order = self.orders[order_id]
        if order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            return False
        order.status = OrderStatus.CANCELLED
        order.failure_reason = reason
        if self.current_order and self.current_order.order_id == order_id:
            self.carried_packages.discard(self.current_order.package_id)
            self.current_order = None
            self.mission_state = MissionLifecycleState.MISSION_CANCELLED.value
            self.returning_to_depot = True
        return True

    def get_pending_orders(self) -> List[DeliveryOrder]:
        pending = [o for o in self.orders.values() if o.status == OrderStatus.PENDING]
        # Sort by priority ascending (1 highest), then created_time
        return sorted(pending, key=lambda o: (o.priority, o.created_time))

    def get_schedulable_orders(self) -> List[DeliveryOrder]:
        sched = [o for o in self.orders.values() if o.status in (OrderStatus.PENDING, OrderStatus.CARRYING_PACKAGE)]
        return sorted(sched, key=lambda o: (o.priority, o.created_time))

    def evaluate_next_action(self, current_robot_xy: Tuple[float, float], now: float):
        """Evaluate next mission action and return target dict:
        { 'target_name': str, 'target_xy': (x,y), 'action': 'PICKUP'|'DELIVERY'|'PARK'|'WAIT', 'order_id': str }
        """
        # 1. If currently carrying a package for active order
        def _get_heading(name: str) -> float:
            try:
                from delivery_robot_sim.route_planner import CUSTOMER_STOPPING_BAYS
                if name in CUSTOMER_STOPPING_BAYS:
                    return float(CUSTOMER_STOPPING_BAYS[name].get('approach_heading', 0.0))
            except Exception:
                pass
            return 0.0

        if self.current_order and (self.current_order.package_id in self.carried_packages or self.current_order.status == OrderStatus.CARRYING_PACKAGE):
            self.carried_packages.add(self.current_order.package_id)
            self.current_order.status = OrderStatus.GOING_TO_DELIVERY
            self.mission_state = MissionLifecycleState.NAVIGATING_TO_CLIENT.value
            self.returning_to_depot = False
            return {
                'target_name': self.current_order.delivery_name,
                'target_xy': self.current_order.delivery_xy,
                'target_heading': _get_heading(self.current_order.delivery_name),
                'action': 'DELIVERY',
                'order_id': self.current_order.order_id,
                'package_id': self.current_order.package_id
            }

        # 2. If no active order, pick next schedulable order
        schedulable = self.get_schedulable_orders()
        if schedulable and not self.current_order:
            next_order = schedulable[0]
            next_order.assigned_time = now if next_order.assigned_time is None else next_order.assigned_time
            self.current_order = next_order

            # If package is already in onboard multi-package compartment, proceed to delivery!
            if next_order.package_id in self.carried_packages or next_order.status == OrderStatus.CARRYING_PACKAGE:
                next_order.status = OrderStatus.GOING_TO_DELIVERY
                self.carried_packages.add(next_order.package_id)
                self.mission_state = MissionLifecycleState.NAVIGATING_TO_CLIENT.value
                self.returning_to_depot = False
                return {
                    'target_name': next_order.delivery_name,
                    'target_xy': next_order.delivery_xy,
                    'target_heading': _get_heading(next_order.delivery_name),
                    'action': 'DELIVERY',
                    'order_id': next_order.order_id,
                    'package_id': next_order.package_id
                }

            # If at pickup location already, immediately start pickup dwell
            dist_to_pickup = ((current_robot_xy[0] - next_order.pickup_xy[0])**2 +
                              (current_robot_xy[1] - next_order.pickup_xy[1])**2)**0.5
            if dist_to_pickup < 1.5:
                next_order.status = OrderStatus.PICKING_UP
                self.mission_state = MissionLifecycleState.ORDER_ACCEPTED.value
            else:
                next_order.status = OrderStatus.GOING_TO_PICKUP
                self.mission_state = MissionLifecycleState.PLANNING_ROUTE.value

            self.returning_to_depot = False
            return {
                'target_name': next_order.pickup_name,
                'target_xy': next_order.pickup_xy,
                'target_heading': 0.0,
                'action': 'PICKUP',
                'order_id': next_order.order_id,
                'package_id': next_order.package_id
            }

        # 3. If currently assigned but waiting for pickup
        if self.current_order and self.current_order.status in (OrderStatus.ASSIGNED, OrderStatus.GOING_TO_PICKUP):
            return {
                'target_name': self.current_order.pickup_name,
                'target_xy': self.current_order.pickup_xy,
                'target_heading': 0.0,
                'action': 'PICKUP',
                'order_id': self.current_order.order_id,
                'package_id': self.current_order.package_id
            }

        # 4. If no pending or active orders: return to depot and park
        dist_to_depot = ((current_robot_xy[0] - self.depot_xy[0])**2 +
                         (current_robot_xy[1] - self.depot_xy[1])**2)**0.5
        completed_count = sum(1 for o in self.orders.values() if o.status == OrderStatus.COMPLETED)
        if dist_to_depot > 1.2:
            self.mission_state = MissionLifecycleState.RETURNING_TO_DEPOT.value
            self.returning_to_depot = True
            return {
                'target_name': self.depot_name,
                'target_xy': self.depot_xy,
                'target_heading': 0.0,
                'action': 'PARK',
                'order_id': 'NONE',
                'package_id': 'NONE'
            }
        else:
            if completed_count > 0 and len(self.get_pending_orders()) == 0:
                self.mission_state = MissionLifecycleState.MISSION_COMPLETED.value
            else:
                self.mission_state = MissionLifecycleState.WAITING_FOR_ORDER.value
            self.returning_to_depot = False
            return {
                'target_name': self.depot_name,
                'target_xy': self.depot_xy,
                'target_heading': 0.0,
                'action': 'WAIT',
                'order_id': 'NONE',
                'package_id': 'NONE'
            }

    def confirm_pickup(self, order_id: str):
        """Confirm simulated package loading."""
        if self.current_order and self.current_order.order_id == order_id:
            self.carried_packages.add(self.current_order.package_id)
            self.current_order.status = OrderStatus.CARRYING_PACKAGE
        elif order_id in self.orders:
            self.carried_packages.add(self.orders[order_id].package_id)
            self.orders[order_id].status = OrderStatus.CARRYING_PACKAGE

    def confirm_delivery(self, order_id: str, now: float = 0.0) -> bool:
        """Confirm simulated package unloading and order completion exactly once.
        Guarantees protection against duplicate delivery confirmation.
        """
        if order_id in self.completed_delivery_ids:
            return False
        if order_id not in self.orders:
            return False
        order = self.orders[order_id]
        if order.status == OrderStatus.COMPLETED:
            return False

        order.status = OrderStatus.COMPLETED
        order.completed_time = now
        self.carried_packages.discard(order.package_id)
        self.compartments.confirm_compartment_closed_and_locked(order_id)
        if self.current_order and self.current_order.order_id == order_id:
            self.current_order = None
        self.completed_delivery_ids.add(order_id)
        self.mission_state = MissionLifecycleState.DELIVERY_CONFIRMED.value
        return True

    def get_summary_stats(self) -> Dict:
        completed = sum(1 for o in self.orders.values() if o.status == OrderStatus.COMPLETED)
        failed = sum(1 for o in self.orders.values() if o.status in (OrderStatus.FAILED, OrderStatus.CANCELLED))
        pending = sum(1 for o in self.orders.values() if o.status == OrderStatus.PENDING)
        active = 1 if self.current_order else 0
        return {
            'mission_id': self.mission_id,
            'total_orders': len(self.orders),
            'completed_orders': completed,
            'failed_orders': failed,
            'pending_orders': pending,
            'active_orders': active,
            'current_order_id': self.current_order.order_id if self.current_order else 'NONE',
            'package_load_status': f'CARRYING {self.carried_package}' if self.carried_package else 'EMPTY',
            'mission_state': self.mission_state,
            'returning_to_depot': self.returning_to_depot,
            'completed_delivery_ids': list(self.completed_delivery_ids)
        }
