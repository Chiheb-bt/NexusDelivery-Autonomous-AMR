"""ROS 2 node for realistic autonomous delivery operations and dynamic orders.

Manages depot pickup, client delivery dispatch, package loading/unloading dwell,
dynamic order arrivals during transit, and safe return to depot.
Logs order events and outputs delivery_orders.json / delivery_orders.csv.
"""

import csv
import json
import math
import os
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String

from delivery_robot_sim.order_manager import (
    DeliveryOrder,
    OrderManager,
    OrderStatus,
    MissionLifecycleState,
    PREDEFINED_LOCATIONS
)


class OrderManagerNode(Node):
    def __init__(self):
        super().__init__('order_manager_node')

        # Parameters
        self.declare_parameter('mission_id', 'MSN-20261022-01')
        self.declare_parameter('depot_x', -30.0)
        self.declare_parameter('depot_y', 0.0)
        self.declare_parameter('initial_scenario', 'standard')  # 'standard' or 'empty'
        self.declare_parameter('dynamic_order_time_s', 15.0)
        self.declare_parameter('dwell_time_s', 2.0)
        self.declare_parameter('results_dir', '/tmp')

        mission_id = str(self.get_parameter('mission_id').value)
        depot_x = float(self.get_parameter('depot_x').value)
        depot_y = float(self.get_parameter('depot_y').value)
        self.scenario = os.environ.get('RDSIM_SCENARIO', str(self.get_parameter('initial_scenario').value))
        self.dynamic_order_time_s = float(self.get_parameter('dynamic_order_time_s').value)
        self.dwell_time_s = float(self.get_parameter('dwell_time_s').value)
        self.results_dir = str(self.get_parameter('results_dir').value)
        os.makedirs(self.results_dir, exist_ok=True)

        self.order_mgr = OrderManager(depot_xy=(depot_x, depot_y), mission_id=mission_id)
        self.robot_xy = (depot_x, depot_y)
        self.start_sim_time = None
        self.dynamic_order_injected = False
        self.dwell_until = None
        self.dwell_action = None
        self.dwell_order_id = None

        # Setup initial orders according to scenario
        if self.scenario != 'empty':
            # Initial Order 1: Depot -> Client 1 (North Avenue Residence Curbside Bay)
            o1 = DeliveryOrder(
                order_id='ORD-001',
                pickup_name='DEPOT_POST_OFFICE',
                pickup_xy=(depot_x, depot_y),
                delivery_name='CLIENT_1_NORTH_AVENUE',
                delivery_xy=(-14.2, 15.0),
                package_id='PKG-101',
                priority=1,
                created_time=0.0
            )
            # Initial Order 2: Depot -> Client 2 (North Avenue Commercial Curbside Bay)
            o2 = DeliveryOrder(
                order_id='ORD-002',
                pickup_name='DEPOT_POST_OFFICE',
                pickup_xy=(depot_x, depot_y),
                delivery_name='CLIENT_2_NORTH_AVENUE',
                delivery_xy=(-14.2, 28.0),
                package_id='PKG-102',
                priority=2,
                created_time=0.0
            )
            self.order_mgr.add_order(o1)
            self.order_mgr.add_order(o2)
            self.get_logger().info('Initialized order queue with multi-drop manifest: ORD-001 (Client 1) and ORD-002 (Client 2).')
        else:
            self.get_logger().info('Running EMPTY queue scenario: robot will park and wait at depot.')

        # ROS 2 Subscriptions & Publications
        self.sub_odom = self.create_subscription(Odometry, '/odom', self._on_odom, 10)
        self.sub_arrival = self.create_subscription(String, '/delivery/arrival_event', self._on_arrival, 10)
        self.sub_new_order = self.create_subscription(String, '/delivery/new_order', self._on_new_order, 10)
        self.sub_cancel_order = self.create_subscription(String, '/delivery/cancel_order', self._on_cancel_order, 10)
        self.sub_handover = self.create_subscription(String, '/delivery/confirm_handover', self._on_handover_confirmed, 10)

        self.pub_target = self.create_publisher(String, '/delivery/current_target', 10)
        self.pub_status = self.create_publisher(String, '/delivery/mission_status', 10)
        self.pub_queue = self.create_publisher(String, '/delivery/order_queue', 10)

        self.timer = self.create_timer(0.5, self._on_timer)
        self.get_logger().info('Delivery Order Manager Node started successfully.')

    def _sim_time(self) -> float:
        clock = self.get_clock()
        return clock.now().nanoseconds / 1e9

    def _on_odom(self, msg: Odometry):
        self.robot_xy = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def _on_new_order(self, msg: String):
        try:
            data = json.loads(msg.data)
            o = DeliveryOrder(
                order_id=data['order_id'],
                pickup_name=data.get('pickup_name', 'DEPOT_POST_OFFICE'),
                pickup_xy=tuple(data.get('pickup_xy', (-30.0, 0.0))),
                delivery_name=data.get('delivery_name', 'CLIENT_GENERIC'),
                delivery_xy=tuple(data.get('delivery_xy', (-15.0, 25.0))),
                package_id=data.get('package_id', 'PKG-NEW'),
                priority=int(data.get('priority', 2)),
                created_time=self._sim_time()
            )
            if self.order_mgr.add_order(o, now=self._sim_time()):
                self.get_logger().info(f'ACCEPTED new dynamic order: {o.order_id} -> {o.delivery_name}')
            else:
                self.get_logger().warn(f'Order {o.order_id} already exists in queue.')
        except Exception as e:
            self.get_logger().error(f'Failed to parse new order: {e}')

    def _on_cancel_order(self, msg: String):
        order_id = msg.data.strip()
        if self.order_mgr.cancel_order(order_id, reason='External cancellation command'):
            self.get_logger().warn(f'CANCELLED order {order_id}')

    def _on_handover_confirmed(self, msg: String):
        """Handle customer confirmation of parcel retrieval: lock compartment and return to depot."""
        try:
            data = json.loads(msg.data)
            order_id = data.get('order_id', self.dwell_order_id or '')
            now = self._sim_time()
            self.get_logger().info(f'Handover confirmed for {order_id}. Compartment locked. Initiating return to depot.')
            if order_id in self.order_mgr.orders:
                self.order_mgr.confirm_delivery(order_id, now=now)
            self.dwell_until = None
            self.dwell_action = None
            self.dwell_order_id = None
            self.dwell_otp = None
            self.order_mgr.returning_to_depot = True
            self.order_mgr.mission_state = MissionLifecycleState.RETURNING_TO_DEPOT.value
            self._publish_status(now)
        except Exception as e:
            self.get_logger().error(f'Error handling handover confirmation: {e}')

    def _on_arrival(self, msg: String):
        """Handle arrival notification from navigation driver."""
        try:
            data = json.loads(msg.data)
            action = data.get('action', '')
            order_id = data.get('order_id', '')
            now = self._sim_time()

            if action == 'PICKUP':
                self.get_logger().info(f'Arrived at pickup for {order_id}. Beginning package loading dwell ({self.dwell_time_s}s)...')
                self.dwell_until = now + self.dwell_time_s
                self.dwell_action = 'PICKUP'
                self.dwell_order_id = order_id
                self.order_mgr.mission_state = MissionLifecycleState.ORDER_ACCEPTED.value

            elif action == 'DELIVERY':
                otp, token_hash = self.order_mgr.generate_order_otp(order_id, now)
                cust_name = 'Customer'
                pkg_id = 'PKG-101'
                if order_id in self.order_mgr.orders:
                    ord_obj = self.order_mgr.orders[order_id]
                    cust_name = getattr(ord_obj, 'customer_name', 'Customer')
                    pkg_id = getattr(ord_obj, 'package_id', 'PKG')

                self.get_logger().info(
                    f'Arrived at client destination for {order_id}. '
                    f'CUSTOMER_NOTIFICATION: OTP={otp}. Robot stopped and awaiting customer verification on website.'
                )
                # Strict commercial behavior: robot remains waiting at doorstep until customer validates OTP
                self.dwell_until = None
                self.dwell_action = None
                self.dwell_order_id = order_id
                self.dwell_otp = otp
                self.order_mgr.mission_state = 'WAITING_FOR_CUSTOMER'

                # Broadcast client handover event for Web HUD & Customer Portal
                handover_evt = {
                    'event': 'CUSTOMER_ARRIVAL_NOTIFICATION',
                    'action': 'WAITING_FOR_CUSTOMER',
                    'order_id': order_id,
                    'customer_name': cust_name,
                    'package_id': pkg_id,
                    'otp': otp,
                    'hatch_status': 'LOCKED',
                    'timestamp': now
                }
                msg_h = String()
                msg_h.data = json.dumps(handover_evt)
                try:
                    self.pub_status.publish(msg_h)
                except Exception:
                    pass

            elif action == 'PARK':
                self.get_logger().info('Arrived and safely parked at Depot. Waiting for new orders.')
                completed_count = sum(1 for o in self.order_mgr.orders.values() if o.status == OrderStatus.COMPLETED)
                if completed_count > 0 and len(self.order_mgr.get_pending_orders()) == 0:
                    self.order_mgr.mission_state = MissionLifecycleState.MISSION_COMPLETED.value
                else:
                    self.order_mgr.mission_state = MissionLifecycleState.WAITING_FOR_ORDER.value
                self.order_mgr.returning_to_depot = False

        except Exception as e:
            self.get_logger().error(f'Error handling arrival event: {e}')

    def _on_timer(self):
        if not rclpy.ok():
            return
        now = self._sim_time()
        if self.start_sim_time is None:
            self.start_sim_time = now

        elapsed = now - self.start_sim_time

        # Check for dynamic order injection in standard demo scenario
        if self.scenario != 'empty' and not self.dynamic_order_injected and elapsed >= self.dynamic_order_time_s:
            self.dynamic_order_injected = True
            self.get_logger().info(
                f'*** En-route status at t={elapsed:.1f}s: Delivery manifest active ({len(self.order_mgr.orders)} orders queued/active). ***'
            )

        # Auto-trigger pickup loading dwell if robot is already at depot with an assigned order
        if (self.order_mgr.current_order and 
            self.order_mgr.current_order.status in (OrderStatus.ASSIGNED, OrderStatus.PICKING_UP) and 
            self.dwell_until is None and self.order_mgr.carried_package is None):
            dist_to_pickup = math.hypot(self.robot_xy[0] - self.order_mgr.current_order.pickup_xy[0],
                                        self.robot_xy[1] - self.order_mgr.current_order.pickup_xy[1])
            if dist_to_pickup < 2.0:
                self.get_logger().info(f'Robot at Depot. Beginning package loading dwell ({self.dwell_time_s}s) for {self.order_mgr.current_order.order_id}...')
                self.dwell_until = now + self.dwell_time_s
                self.dwell_action = 'PICKUP'
                self.dwell_order_id = self.order_mgr.current_order.order_id
                self.order_mgr.mission_state = MissionLifecycleState.ORDER_ACCEPTED.value
                self._publish_status(now)
                return

        # Check if currently in loading or unloading dwell
        if self.dwell_until is not None:
            if now < self.dwell_until:
                # Still dwelling
                self._publish_status(now)
                return
            else:
                # Dwell complete!
                if self.dwell_action == 'PICKUP':
                    self.order_mgr.confirm_pickup(self.dwell_order_id)
                    # Also load any other scheduled depot orders for multi-compartment delivery
                    for o in self.order_mgr.get_pending_orders():
                        if o.pickup_xy == self.order_mgr.depot_xy:
                            self.order_mgr.confirm_pickup(o.order_id)
                    self.order_mgr.mission_state = MissionLifecycleState.NAVIGATING_TO_CLIENT.value
                    self.get_logger().info(
                        f'Package loading confirmed for manifest ({len(self.order_mgr.carried_packages)} packages loaded: {self.order_mgr.carried_packages}). Commencing transit to delivery destinations.'
                    )
                elif self.dwell_action == 'DELIVERY':
                    # Customer enters OTP and unlocks compartment
                    otp = getattr(self, 'dwell_otp', '123456')
                    auth_ok, auth_msg = self.order_mgr.authenticate_order_otp(self.dwell_order_id, otp, now)
                    self.get_logger().info(f'Compartment access for {self.dwell_order_id}: {auth_msg}')
                    confirmed = self.order_mgr.confirm_delivery(self.dwell_order_id, now=now)
                    if confirmed:
                        self.order_mgr.mission_state = MissionLifecycleState.DELIVERY_CONFIRMED.value
                        self.get_logger().info(
                            f'DELIVERY_CONFIRMED for {self.dwell_order_id}. '
                            f'Cargo hatch locked. Remaining packages: {self.order_mgr.carried_packages}'
                        )
                        self._publish_status(now)
                self.dwell_until = None
                self.dwell_action = None
                self.dwell_order_id = None
                self.dwell_otp = None

        # Evaluate next action
        act = self.order_mgr.evaluate_next_action(self.robot_xy, now=now)

        # Publish target to driver node
        msg_target = String()
        msg_target.data = json.dumps(act)
        try:
            if rclpy.ok():
                self.pub_target.publish(msg_target)
        except Exception:
            pass

        self._publish_status(now)

    def _publish_status(self, now: float):
        if not rclpy.ok():
            return
        stats = self.order_mgr.get_summary_stats()
        stats['timestamp'] = now
        stats['robot_x'] = round(self.robot_xy[0], 3)
        stats['robot_y'] = round(self.robot_xy[1], 3)

        msg_status = String()
        msg_status.data = json.dumps(stats)
        try:
            if rclpy.ok():
                self.pub_status.publish(msg_status)
        except Exception:
            pass

        # Publish order queue list
        queue_data = [
            {
                'mission_id': self.order_mgr.mission_id,
                'order_id': o.order_id,
                'status': o.status.value,
                'priority': o.priority,
                'package_id': o.package_id,
                'delivery_name': o.delivery_name,
                'created_time': round(o.created_time, 2)
            }
            for o in self.order_mgr.orders.values()
        ]
        msg_q = String()
        msg_q.data = json.dumps(queue_data)
        try:
            if rclpy.ok():
                self.pub_queue.publish(msg_q)
        except Exception:
            pass

    def save_reports(self):
        """Export order history to CSV and JSON on shutdown."""
        orders_list = []
        for o in self.order_mgr.orders.values():
            orders_list.append({
                'mission_id': self.order_mgr.mission_id,
                'order_id': o.order_id,
                'status': o.status.value,
                'priority': o.priority,
                'package_id': o.package_id,
                'pickup_name': o.pickup_name,
                'delivery_name': o.delivery_name,
                'created_time': round(o.created_time, 3),
                'assigned_time': round(o.assigned_time, 3) if o.assigned_time else None,
                'completed_time': round(o.completed_time, 3) if o.completed_time else None,
                'failure_reason': o.failure_reason
            })

        json_path = os.path.join(self.results_dir, 'delivery_orders.json')
        with open(json_path, 'w') as fj:
            json.dump(orders_list, fj, indent=2)

        csv_path = os.path.join(self.results_dir, 'delivery_orders.csv')
        with open(csv_path, 'w', newline='') as fc:
            writer = csv.writer(fc)
            writer.writerow(['order_id', 'status', 'priority', 'package_id', 'pickup', 'destination', 'created_time', 'completed_time', 'failure_reason'])
            for o in orders_list:
                writer.writerow([
                    o['order_id'], o['status'], o['priority'], o['package_id'],
                    o['pickup_name'], o['delivery_name'], o['created_time'],
                    o['completed_time'], o['failure_reason'] or ''
                ])
        print(f'[order_manager_node] Saved order logs to {json_path} and {csv_path}', flush=True)


def main(args=None):
    rclpy.init(args=args)
    node = OrderManagerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            node.save_reports()
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except Exception:
                pass


if __name__ == '__main__':
    main()
