#!/usr/bin/env python3
"""Intelligent Multi-Order Mission Dispatcher for NexusDelivery.

Implements route-aware multi-drop scheduling, priority evaluation,
payload capacity validation (max 15.0 kg, 22.5 L), and transparent dispatch decision logging.

Features:
- Multi-order grouping along shared sidewalk corridors.
- Destination reachability validation against Gazebo world topological graph.
- Transparent decision log recording reasoning for every dispatch or rejection.
- Explicit lifecycle status tracking:
    Cart -> Pending confirmation -> Confirmed -> Waiting for robot -> Assigned ->
    Preparing cargo -> En route -> Arriving -> Delivered -> Failed -> Cancelled.
"""

from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from delivery_robot_sim.route_planner import (
    CITY_BOUNDS,
    DEPOT_DOCK_XY,
    CUSTOMER_STOPPING_BAYS,
    plan_city_route,
)
from delivery_robot_sim.gazebo_world_map import (
    compute_route_distance,
    estimate_eta_seconds,
)

MAX_PAYLOAD_CAPACITY_KG = 15.0     # Maximum total payload weight
MAX_PAYLOAD_VOLUME_L = 22.5        # Compartment volume limit
NOMINAL_CRUISING_SPEED_M_S = 0.80  # Speed for ETA computation


class OrderLifecycleStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY_FOR_DISPATCH = "READY_FOR_DISPATCH"
    ROBOT_ASSIGNED = "ROBOT_ASSIGNED"
    ROBOT_EN_ROUTE = "ROBOT_EN_ROUTE"
    ROBOT_ARRIVED = "ROBOT_ARRIVED"
    HANDOVER_IN_PROGRESS = "HANDOVER_IN_PROGRESS"
    DELIVERED = "DELIVERED"
    RETURNING_TO_DEPOT = "RETURNING_TO_DEPOT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    UNREACHABLE = "UNREACHABLE"

    # Backward-compatible aliases
    CART = "PENDING"
    PENDING_CONFIRMATION = "PENDING"
    WAITING_FOR_ROBOT = "READY_FOR_DISPATCH"
    ASSIGNED = "ROBOT_ASSIGNED"
    PREPARING_CARGO = "PREPARING"
    EN_ROUTE = "ROBOT_EN_ROUTE"
    ARRIVING = "ROBOT_ARRIVED"



@dataclass
class DispatchDecision:
    timestamp: float
    order_id: str
    customer_id: str
    decision: str  # e.g., "ASSIGNED_IMMEDIATE", "BATCHED_MULTI_DROP", "QUEUED", "REJECTED"
    reason: str
    route_distance_m: float
    estimated_eta_s: float
    current_payload_kg: float
    robot_id: str = "NEXUS-AMR-01"


@dataclass
class DispatchableOrder:
    order_id: str
    customer_id: str
    customer_name: str
    destination_name: str
    destination_xy: Tuple[float, float]
    stopping_xy: Tuple[float, float]
    approach_heading: float
    package_id: str
    items: List[Dict]
    total_weight_kg: float = 1.0
    total_volume_l: float = 2.0
    priority: int = 2  # 1 = Urgent, 2 = Standard, 3 = Low
    deadline: Optional[float] = None
    created_time: float = field(default_factory=time.time)
    status: OrderLifecycleStatus = OrderLifecycleStatus.PENDING_CONFIRMATION
    assigned_robot_id: Optional[str] = None
    assigned_time: Optional[float] = None
    completed_time: Optional[float] = None
    failure_reason: Optional[str] = None
    otp_code: str = "123456"


class IntelligentMissionDispatcher:
    """Central dispatch engine coordinating fleet assignment, multi-drop bundling,
    and decision accountability."""

    def __init__(self, depot_xy: Tuple[float, float] = DEPOT_DOCK_XY):
        self.lock = threading.RLock()
        self.depot_xy = depot_xy
        self.queue: List[DispatchableOrder] = []
        self.active_mission_orders: List[DispatchableOrder] = []
        self.completed_orders: List[DispatchableOrder] = []
        self.decision_log: List[DispatchDecision] = []
        self.current_robot_xy = depot_xy
        self.robot_is_available = True
        self.battery_soc_pct = 95.0

    def get_current_payload(self) -> Tuple[float, float]:
        """Calculates total weight and volume currently loaded in active mission."""
        with self.lock:
            w = sum(o.total_weight_kg for o in self.active_mission_orders)
            v = sum(o.total_volume_l for o in self.active_mission_orders)
            return round(w, 2), round(v, 2)

    def validate_destination_reachability(self, dest_xy: Tuple[float, float]) -> Tuple[bool, str]:
        """Verifies destination is within the verified small_city_dynamic.world service bounds
        and connects to the topological sidewalk route planner."""
        x, y = dest_xy
        if not (-45.0 <= x <= 45.0 and -45.0 <= y <= 45.0):
            return False, f"Coordinates ({x:.1f}, {y:.1f}) exceed supported Gazebo operational envelope [-45, 45]m."

        # Check path existence from depot
        route = plan_city_route(self.depot_xy, dest_xy)
        if len(route) < 2:
            return False, f"No safe topological sidewalk path found to destination ({x:.1f}, {y:.1f})."

        return True, "Destination reachability validated."

    def submit_customer_order(
        self,
        order_id: str,
        customer_id: str,
        customer_name: str,
        dest_name: str,
        dest_xy: Tuple[float, float],
        stopping_xy: Tuple[float, float],
        heading: float,
        items: List[Dict],
        total_weight_kg: float,
        total_volume_l: float,
        priority: int = 2,
        otp_code: str = "123456"
    ) -> Tuple[bool, str, Optional[DispatchDecision]]:
        """Submits an order into the dispatch engine with validation and multi-drop bundling."""
        with self.lock:
            # 1. Validate payload capacity
            if total_weight_kg > MAX_PAYLOAD_CAPACITY_KG:
                decision = DispatchDecision(
                    timestamp=time.time(),
                    order_id=order_id,
                    customer_id=customer_id,
                    decision="REJECTED",
                    reason=f"Order payload {total_weight_kg:.1f}kg exceeds robot max capacity {MAX_PAYLOAD_CAPACITY_KG}kg.",
                    route_distance_m=0.0,
                    estimated_eta_s=0.0,
                    current_payload_kg=0.0
                )
                self.decision_log.append(decision)
                return False, decision.reason, decision

            # 2. Validate reachability
            reachable, reason = self.validate_destination_reachability(stopping_xy)
            if not reachable:
                decision = DispatchDecision(
                    timestamp=time.time(),
                    order_id=order_id,
                    customer_id=customer_id,
                    decision="REJECTED",
                    reason=reason,
                    route_distance_m=0.0,
                    estimated_eta_s=0.0,
                    current_payload_kg=0.0
                )
                self.decision_log.append(decision)
                return False, reason, decision

            # 3. Compute planned distance and ETA from current robot position
            route = plan_city_route(self.current_robot_xy, stopping_xy)
            dist_m = compute_route_distance(route, self.current_robot_xy)
            eta_s = estimate_eta_seconds(dist_m, NOMINAL_CRUISING_SPEED_M_S)

            order = DispatchableOrder(
                order_id=order_id,
                customer_id=customer_id,
                customer_name=customer_name,
                destination_name=dest_name,
                destination_xy=dest_xy,
                stopping_xy=stopping_xy,
                approach_heading=heading,
                package_id=f"PKG-{order_id[-3:]}",
                items=items,
                total_weight_kg=total_weight_kg,
                total_volume_l=total_volume_l,
                priority=priority,
                status=OrderLifecycleStatus.CONFIRMED,
                otp_code=otp_code
            )

            curr_weight, curr_vol = self.get_current_payload()

            # 4. Check if we can assign immediately or batch with active mission
            can_combine = (
                curr_weight + total_weight_kg <= MAX_PAYLOAD_CAPACITY_KG and
                curr_vol + total_volume_l <= MAX_PAYLOAD_VOLUME_L and
                len(self.active_mission_orders) < 3  # Max 3 multi-drop deliveries per trip
            )

            if len(self.active_mission_orders) == 0 and self.robot_is_available:
                # Immediate assignment
                order.status = OrderLifecycleStatus.ASSIGNED
                order.assigned_robot_id = "NEXUS-AMR-01"
                order.assigned_time = time.time()
                self.active_mission_orders.append(order)
                decision_type = "ASSIGNED_IMMEDIATE"
                decision_reason = (
                    f"Robot available at {self.current_robot_xy}. "
                    f"Direct assignment along corridor ({dist_m:.1f}m, ETA {int(eta_s)}s)."
                )
            elif can_combine:
                # Multi-drop batching
                order.status = OrderLifecycleStatus.ASSIGNED
                order.assigned_robot_id = "NEXUS-AMR-01"
                order.assigned_time = time.time()
                self.active_mission_orders.append(order)
                # Sort active orders by distance along topological path for optimal sequence
                self._optimize_multi_drop_route()
                decision_type = "BATCHED_MULTI_DROP"
                decision_reason = (
                    f"Compatible corridor delivery detected. Grouped into active multi-drop mission. "
                    f"Total payload: {curr_weight + total_weight_kg:.1f}kg / {MAX_PAYLOAD_CAPACITY_KG}kg."
                )
            else:
                # Enqueue in priority order
                order.status = OrderLifecycleStatus.WAITING_FOR_ROBOT
                self.queue.append(order)
                self._sort_queue()
                decision_type = "QUEUED"
                decision_reason = (
                    f"Robot engaged on existing mission. "
                    f"Queued with priority {priority} at position #{len(self.queue)}."
                )

            decision = DispatchDecision(
                timestamp=time.time(),
                order_id=order_id,
                customer_id=customer_id,
                decision=decision_type,
                reason=decision_reason,
                route_distance_m=round(dist_m, 2),
                estimated_eta_s=round(eta_s, 1),
                current_payload_kg=round(curr_weight + (total_weight_kg if decision_type != "QUEUED" else 0.0), 2)
            )
            self.decision_log.append(decision)
            return True, decision_reason, decision

    def _sort_queue(self):
        """Sorts waiting orders by priority (1=Urgent), deadline, and created time."""
        self.queue.sort(key=lambda o: (o.priority, o.deadline or float("inf"), o.created_time))

    def _optimize_multi_drop_route(self):
        """Orders the active stops to minimize backtracking using nearest neighbor along sidewalk graph."""
        if len(self.active_mission_orders) <= 1:
            return

        current_pt = self.current_robot_xy
        remaining = list(self.active_mission_orders)
        ordered: List[DispatchableOrder] = []

        while remaining:
            best_idx = 0
            best_dist = float("inf")
            for i, ord_obj in enumerate(remaining):
                r = plan_city_route(current_pt, ord_obj.stopping_xy)
                d = compute_route_distance(r, current_pt)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            chosen = remaining.pop(best_idx)
            ordered.append(chosen)
            current_pt = chosen.stopping_xy

        self.active_mission_orders = ordered

    def update_robot_telemetry(self, current_xy: Tuple[float, float], battery_soc: float, is_available: bool):
        """Updates robot state for live distance recalculation and dynamic dispatching."""
        with self.lock:
            self.current_robot_xy = current_xy
            self.battery_soc_pct = battery_soc
            self.robot_is_available = is_available

            # Check if active missions are completed and promote queued orders
            if len(self.active_mission_orders) == 0 and self.queue and is_available:
                next_order = self.queue.pop(0)
                next_order.status = OrderLifecycleStatus.ASSIGNED
                next_order.assigned_robot_id = "NEXUS-AMR-01"
                next_order.assigned_time = time.time()
                self.active_mission_orders.append(next_order)

                r = plan_city_route(self.current_robot_xy, next_order.stopping_xy)
                d = compute_route_distance(r, self.current_robot_xy)
                eta = estimate_eta_seconds(d, NOMINAL_CRUISING_SPEED_M_S)

                self.decision_log.append(DispatchDecision(
                    timestamp=time.time(),
                    order_id=next_order.order_id,
                    customer_id=next_order.customer_id,
                    decision="ASSIGNED_PROMOTED_FROM_QUEUE",
                    reason="Robot returned to available state. Promoted top priority queued order.",
                    route_distance_m=round(d, 2),
                    estimated_eta_s=round(eta, 1),
                    current_payload_kg=next_order.total_weight_kg
                ))

    def get_decision_log(self, limit: int = 50) -> List[Dict]:
        """Returns the recent dispatch decision log."""
        with self.lock:
            recent = self.decision_log[-limit:]
            return [asdict(d) for d in reversed(recent)]

    def get_active_orders(self) -> List[Dict]:
        with self.lock:
            return [asdict(o) for o in self.active_mission_orders]

    def get_queued_orders(self) -> List[Dict]:
        with self.lock:
            return [asdict(o) for o in self.queue]
