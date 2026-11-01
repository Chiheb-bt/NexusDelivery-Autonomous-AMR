import math, os, sys, unittest
import numpy as np, cv2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from delivery_robot_sim import vision, control, track_geometry as tg
from delivery_robot_sim.yolo_detector import YOLODetector


def frame(line_col=None, w=320, h=240):
    img = np.full((h, w, 3), 60, np.uint8)
    if line_col is not None:
        cv2.line(img, (int(line_col), 150), (int(line_col), 239), (255, 255, 255), 10)
    return img


class Vision(unittest.TestCase):
    def test_barycentre_position(self):
        x, n = vision.line_barycentre(frame(200), (150, 230, 0, 320))
        self.assertAlmostEqual(x, 200, delta=1.5)
        self.assertGreater(n, 100)

    def test_no_line(self):
        x, _ = vision.line_barycentre(frame(None), (150, 230, 0, 320))
        self.assertIsNone(x)

    def test_clahe_keeps_line(self):
        img = vision.preprocess(frame(120), True)
        x, _ = vision.line_barycentre(img, (150, 230, 0, 320), thresh=150)
        self.assertAlmostEqual(x, 120, delta=3)

    def test_traffic_light_and_obstacle(self):
        img = frame(None)
        cv2.circle(img, (60, 80), 8, (0, 0, 255), -1)       # rouge (BGR)
        cv2.circle(img, (250, 80), 8, (0, 255, 0), -1)      # vert
        cv2.rectangle(img, (120, 130), (200, 200), (0, 128, 255), -1)  # orange
        red, green = vision.traffic_light_areas(img)
        self.assertGreater(red, 100); self.assertGreater(green, 100)
        self.assertGreater(vision.orange_density(img, (100, 220, 80, 240)), 3000)
    def test_forward_obstacle_clear(self):
        img = np.full((240, 320, 3), 75, dtype=np.uint8)
        res = vision.detect_forward_obstacles(img)
        self.assertFalse(res['obstacle_detected'])
        self.assertEqual(res['suggested_bypass'], 'NONE')

    def test_forward_obstacle_bypass(self):
        img = np.full((240, 320, 3), 75, dtype=np.uint8)
        cv2.rectangle(img, (180, 160), (240, 210), (0, 165, 255), -1)
        res = vision.detect_forward_obstacles(img)
        self.assertTrue(res['obstacle_detected'])
        self.assertGreater(res['proximity'], 0.5)
        self.assertEqual(res['suggested_bypass'], 'RIGHT')

    def test_forward_obstacle_stop_when_blocked(self):
        img = np.full((240, 320, 3), 75, dtype=np.uint8)
        # Block whole corridor width
        cv2.rectangle(img, (40, 180), (280, 230), (0, 0, 255), -1)
        res = vision.detect_forward_obstacles(img)
        self.assertTrue(res['obstacle_detected'])
        self.assertEqual(res['suggested_bypass'], 'STOP')



class Control(unittest.TestCase):
    def test_pid_sign(self):
        pid = control.PID(kp=0.01)
        # The sign is matched to the observed Gazebo camera/base-frame response.
        self.assertGreater(pid.update(+40, 0.1), 0)
        self.assertLess(pid.update(-40, 0.1), 0)

    def test_fsm_red_green(self):
        f = control.MissionFSM()
        c = f.update(0.0, control.Perception(line_x=160, red_area=300))
        self.assertEqual(c.state, "STOP_RED"); self.assertEqual(c.v, 0.0)
        c = f.update(1.0, control.Perception(line_x=160, green_area=100))
        self.assertEqual(c.state, "FOLLOW")

    def test_fsm_avoid_sequence_and_lockout(self):
        f = control.MissionFSM()
        seen, t = [], 0.0
        while t < 20:
            c = f.update(t, control.Perception(line_x=160, obstacle_px=900))
            if not seen or seen[-1] != c.state: seen.append(c.state)
            t += 0.05
        self.assertEqual(seen[:5], ["AVOID_LEFT", "AVOID_STRAIGHT", "AVOID_RIGHT", "REACQUIRE", "FOLLOW"])
        self.assertAlmostEqual(f.w_left * f.t_left + f.w_right * f.t_right, 0.0, places=6)

    def test_line_lost_safety_stop(self):
        f = control.MissionFSM(lost_timeout=1.0)
        f.update(0.0, control.Perception(line_x=None))
        c = f.update(1.5, control.Perception(line_x=None))
        self.assertEqual(c.v, 0.0)



    def test_fsm_red_light_priority(self):
        f = control.MissionFSM()
        # Trigger red light
        c = f.update(0.0, control.Perception(line_x=160, red_area=300))
        self.assertEqual(c.state, "STOP_RED")
        self.assertEqual(c.v, 0.0)
        # If green is seen while red is STILL visible, must remain STOP_RED
        c = f.update(1.0, control.Perception(line_x=160, red_area=250, green_area=150))
        self.assertEqual(c.state, "STOP_RED")
        self.assertEqual(c.v, 0.0)
        # Only when red is cleared and green is visible does it resume
        c = f.update(2.0, control.Perception(line_x=160, red_area=0, green_area=150))
        self.assertEqual(c.state, "FOLLOW")

    def test_fsm_obstacle_stop_mode(self):
        f = control.MissionFSM(obstacle_mode="stop")
        c = f.update(0.0, control.Perception(line_x=160, obstacle_px=900))
        self.assertEqual(c.state, "STOP_OBSTACLE")
        self.assertEqual(c.v, 0.0)
        # Stays stopped as long as obstacle is present
        c = f.update(1.0, control.Perception(line_x=160, obstacle_px=800))
        self.assertEqual(c.state, "STOP_OBSTACLE")
        # Resumes once obstacle cleared
        c = f.update(2.0, control.Perception(line_x=160, obstacle_px=0))
        self.assertEqual(c.state, "FOLLOW")



    def test_fsm_green_debouncing(self):
        f = control.MissionFSM(green_confirm_frames=3)
        # Red stops robot
        f.update(0.0, control.Perception(line_x=160, red_area=300))
        self.assertEqual(f.state, "STOP_RED")
        # Frame 1: green appears (red cleared) -> still STOP_RED
        c1 = f.update(1.0, control.Perception(line_x=160, green_area=100))
        self.assertEqual(c1.state, "STOP_RED")
        # Frame 2: green continues -> still STOP_RED
        c2 = f.update(1.1, control.Perception(line_x=160, green_area=100))
        self.assertEqual(c2.state, "STOP_RED")
        # Frame 3: green confirmed for 3rd time -> transitions to FOLLOW
        c3 = f.update(1.2, control.Perception(line_x=160, green_area=100))
        self.assertEqual(c3.state, "FOLLOW")

    def test_fsm_reacquire_camera_confirmed(self):
        f = control.MissionFSM(x_target=162.0)
        f.state = "REACQUIRE"
        f._t0 = 0.0
        # Line not centered yet -> remains REACQUIRE
        c1 = f.update(1.0, control.Perception(line_x=220.0))
        self.assertEqual(c1.state, "REACQUIRE")
        # Line centered in camera (|162 - 162| < 50) -> transitions to FOLLOW
        c2 = f.update(2.0, control.Perception(line_x=162.0))
        self.assertEqual(c2.state, "FOLLOW")

    def test_fsm_reacquire_lost_safety_stop(self):
        f = control.MissionFSM(t_reacquire=5.0)
        f.state = "REACQUIRE"
        f._t0 = 0.0
        # Time passes without finding line
        c = f.update(6.0, control.Perception(line_x=None))
        self.assertEqual(c.state, "LOST_LINE_STOP")
        self.assertEqual(c.v, 0.0)


class YoloReady(unittest.TestCase):
    def test_yolo_detector_falls_back_cleanly(self):
        mpath = os.path.join(os.path.dirname(__file__), '..', 'yolov8n.pt')
        det = YOLODetector(model_path=mpath if os.path.exists(mpath) else "yolov8n.pt", conf=0.25)
        self.assertIsInstance(det.detect(np.zeros((10, 10, 3), dtype=np.uint8)), list)


class Geometry(unittest.TestCase):
    def test_on_line(self):
        self.assertAlmostEqual(tg.cross_track_error(0, -2), 0, places=6)
        self.assertAlmostEqual(tg.cross_track_error(4, 0), 0, places=6)
        self.assertAlmostEqual(tg.cross_track_error(0, -2.3), 0.3, places=6)

    def test_tangent_ccw(self):
        tx, ty = tg.tangent(0, -2)
        self.assertAlmostEqual(tx, 1, places=3); self.assertAlmostEqual(ty, 0, places=3)



class Fusion(unittest.TestCase):
    def test_white_floor_is_not_a_line(self):
        white = np.full((240, 320, 3), 255, np.uint8)
        x, _ = vision.line_barycentre(white, (110, 200, 0, 320))
        self.assertIsNone(x)

    def test_yolo_overrides(self):
        from delivery_robot_sim.yolo_detector import (
            Detection,
            apply_overrides,
            is_forward_obstacle,
        )
        img = np.full((240, 320, 3), 60, np.uint8)
        cv2.circle(img, (100, 80), 8, (0, 0, 255), -1)
        red, green, obs = apply_overrides([Detection("traffic light", 0.9, 80, 60, 120, 100)], img, 0, 0, 0, vision.traffic_light_areas)
        self.assertGreater(red, 100); self.assertEqual(green, 0)
        self.assertEqual(apply_overrides([Detection("stop sign", 0.9, 0, 0, 50, 50)], img, 0, 0, 0, vision.traffic_light_areas), (0, 0, 0))
        self.assertEqual(
            apply_overrides(
                [Detection("traffic light", 0.9, 80, 60, 120, 100)],
                img,
                0,
                0,
                0,
                vision.traffic_light_areas,
                traffic_lights_enabled=False,
            ),
            (0, 0, 0),
        )
        self.assertEqual(apply_overrides([Detection("person", 0.8, 110, 100, 210, 220)], img, 0, 0, 0, vision.traffic_light_areas)[2], 2500)
        self.assertTrue(is_forward_obstacle(Detection("chair", 0.8, 120, 100, 210, 220), img.shape))
        self.assertFalse(is_forward_obstacle(Detection("chair", 0.8, 0, 100, 45, 220), img.shape))
        self.assertFalse(is_forward_obstacle(Detection("chair", 0.8, 120, 10, 210, 90), img.shape))


from delivery_robot_sim.order_manager import OrderManager, DeliveryOrder, OrderStatus

class OrderManagementTests(unittest.TestCase):
    def test_order_lifecycle_and_transitions(self):
        om = OrderManager(depot_xy=(-30.0, 0.0))
        o1 = DeliveryOrder('ORD-1', 'DEPOT', (-30.0, 0.0), 'CLIENT_A', (-15.0, 15.0), 'PKG-1')
        self.assertTrue(om.add_order(o1, now=1.0))

        # Evaluation at depot
        act = om.evaluate_next_action(current_robot_xy=(-30.0, 0.0), now=2.0)
        self.assertEqual(act['action'], 'PICKUP')
        self.assertEqual(om.current_order.status, OrderStatus.PICKING_UP)

        # Confirm pickup
        om.confirm_pickup('ORD-1')
        self.assertEqual(om.carried_package, 'PKG-1')

        # Next action -> GOING_TO_DELIVERY
        act = om.evaluate_next_action(current_robot_xy=(-25.0, 0.0), now=5.0)
        self.assertEqual(act['action'], 'DELIVERY')
        self.assertEqual(om.current_order.status, OrderStatus.GOING_TO_DELIVERY)

        # Arrive at destination and confirm delivery
        om.confirm_delivery('ORD-1', now=25.0)
        self.assertEqual(o1.status, OrderStatus.COMPLETED)
        self.assertIsNone(om.carried_package)

        # After completion: queue is empty, returns to depot
        act = om.evaluate_next_action(current_robot_xy=(-15.0, 15.0), now=26.0)
        self.assertEqual(act['action'], 'PARK')
        self.assertTrue(om.returning_to_depot)

    def test_dynamic_order_insertion_and_priority(self):
        om = OrderManager()
        o1 = DeliveryOrder('ORD-1', 'DEPOT', (-30.0, 0.0), 'CLIENT_A', (-15.0, 15.0), 'PKG-1', priority=2)
        om.add_order(o1, now=1.0)
        om.evaluate_next_action((-30.0, 0.0), now=1.0)
        om.confirm_pickup('ORD-1')

        # While carrying PKG-1, dynamic order ORD-2 arrives with priority 1
        o2 = DeliveryOrder('ORD-2', 'DEPOT', (-30.0, 0.0), 'CLIENT_B', (-15.0, 30.0), 'PKG-2', priority=1)
        self.assertTrue(om.add_order(o2, now=15.0))

        # Current order ORD-1 remains active (do not abandon loaded package)
        act = om.evaluate_next_action((-20.0, 0.0), now=16.0)
        self.assertEqual(act['order_id'], 'ORD-1')

        # Once ORD-1 is delivered, ORD-2 is next
        om.confirm_delivery('ORD-1', now=30.0)
        act2 = om.evaluate_next_action((-15.0, 15.0), now=31.0)
        self.assertEqual(act2['order_id'], 'ORD-2')

    def test_multi_drop_manifest_and_return_to_depot(self):
        om = OrderManager(depot_xy=(-30.0, 0.0))
        o1 = DeliveryOrder('ORD-001', 'DEPOT', (-30.0, 0.0), 'CLIENT_1', (-15.0, 15.0), 'PKG-101', priority=1)
        o2 = DeliveryOrder('ORD-002', 'DEPOT', (-30.0, 0.0), 'CLIENT_2', (-15.0, 28.0), 'PKG-102', priority=2)
        om.add_order(o1)
        om.add_order(o2)

        # Multi-package loading at depot dwell
        om.confirm_pickup('ORD-001')
        om.confirm_pickup('ORD-002')
        self.assertEqual(len(om.carried_packages), 2)

        # Leg 1: Deliver ORD-001 to Client 1
        act1 = om.evaluate_next_action((-30.0, 0.0), now=2.0)
        self.assertEqual(act1['action'], 'DELIVERY')
        self.assertEqual(act1['order_id'], 'ORD-001')
        om.confirm_delivery('ORD-001', now=20.0)
        self.assertEqual(o1.status, OrderStatus.COMPLETED)

        # Leg 2: Deliver ORD-002 to Client 2
        act2 = om.evaluate_next_action((-15.0, 15.0), now=21.0)
        self.assertEqual(act2['action'], 'DELIVERY')
        self.assertEqual(act2['order_id'], 'ORD-002')
        om.confirm_delivery('ORD-002', now=40.0)
        self.assertEqual(o2.status, OrderStatus.COMPLETED)

        # Leg 3: Return to Depot
        act3 = om.evaluate_next_action((-15.0, 28.0), now=41.0)
        self.assertEqual(act3['action'], 'PARK')
        self.assertTrue(om.returning_to_depot)

        # Park at Depot
        act4 = om.evaluate_next_action((-30.0, 0.0), now=65.0)
        self.assertEqual(act4['action'], 'WAIT')
        self.assertEqual(om.mission_state, 'MISSION_COMPLETED')

    def test_empty_queue_stays_at_depot(self):
        om = OrderManager(depot_xy=(-30.0, 0.0))
        act = om.evaluate_next_action((-30.0, 0.0), now=1.0)
        self.assertEqual(act['action'], 'WAIT')
        self.assertEqual(om.mission_state, 'WAITING_FOR_ORDER')

    def test_cancel_order(self):
        om = OrderManager()
        o = DeliveryOrder('ORD-X', 'DEPOT', (-30.0, 0.0), 'CLIENT_X', (-15.0, 15.0), 'PKG-X')
        om.add_order(o)
        self.assertTrue(om.cancel_order('ORD-X', 'Test cancel'))
        self.assertEqual(o.status, OrderStatus.CANCELLED)


class DepthVisionTests(unittest.TestCase):
    def test_depth_corridor_clear(self):
        # 240x320 depth image with uniform 8.0m distance (clear road)
        depth = np.full((240, 320), 8.0, dtype=np.float32)
        res = vision.analyze_depth_corridor(depth)
        self.assertFalse(res['obstacle_detected'])
        self.assertGreater(res['corridor_distance'], 5.0)
        self.assertTrue(res['safe_passable'])
        self.assertEqual(res['suggested_bypass'], 'NONE')

    def test_depth_corridor_obstacle_center(self):
        # Center obstacle at 1.8m within obstacle horizon ROI
        depth = np.full((240, 320), 6.0, dtype=np.float32)
        depth[80:130, 120:200] = 1.8
        res = vision.analyze_depth_corridor(depth)
        self.assertTrue(res['obstacle_detected'])
        self.assertAlmostEqual(res['corridor_distance'], 1.8, delta=0.2)
        self.assertIn(res['suggested_bypass'], ('LEFT', 'RIGHT'))

    def test_depth_corridor_nan_and_inf_handling(self):
        depth = np.full((240, 320), np.nan, dtype=np.float32)
        depth[70:100, 100:220] = np.inf
        depth[90:130, 120:200] = 2.2
        res = vision.analyze_depth_corridor(depth)
        self.assertTrue(res['obstacle_detected'])
        self.assertAlmostEqual(res['corridor_distance'], 2.2, delta=0.2)

    def test_depth_corridor_wall_blocked(self):
        # Barrier spanning entire road corridor at 2.0m -> no passage possible
        depth = np.full((240, 320), 2.0, dtype=np.float32)
        res = vision.analyze_depth_corridor(depth)
        self.assertTrue(res['obstacle_detected'])
        self.assertFalse(res['safe_passable'])
        self.assertEqual(res['suggested_bypass'], 'STOP')

    def test_depth_corridor_all_nan_invalid(self):
        # Completely invalid/corrupted sensor data
        depth = np.full((240, 320), np.nan, dtype=np.float32)
        res = vision.analyze_depth_corridor(depth)
        self.assertFalse(res['depth_valid'])
        self.assertFalse(res['safe_passable'])
        self.assertEqual(res['suggested_bypass'], 'STOP')

    def test_fuse_rgb_and_depth(self):
        bgr = np.full((240, 320, 3), 70, dtype=np.uint8)
        # Add orange obstacle
        cv2.rectangle(bgr, (130, 150), (190, 210), (0, 140, 255), -1)
        depth = np.full((240, 320), 5.0, dtype=np.float32)
        depth[150:210, 130:190] = 2.0
        fused = vision.fuse_rgb_and_depth(bgr, depth)
        self.assertTrue(fused['obstacle_detected'])
        self.assertAlmostEqual(fused['distance_m'], 2.0, delta=0.3)


class EvaluatorStatusTests(unittest.TestCase):
    def test_evaluator_success_requires_both_deliveries_and_return(self):
        # Mock evaluator summary logic
        def get_status(completed, returned, collisions, failed):
            if collisions > 0:
                return 'COLLISION_DETECTED'
            elif completed >= 2 and returned:
                return 'SUCCESS'
            elif completed >= 2 and not returned:
                return 'FAILED_TO_RETURN'
            elif failed > 0:
                return 'INCOMPLETE_ORDERS'
            return 'IN_PROGRESS'

        self.assertEqual(get_status(completed=2, returned=True, collisions=0, failed=0), 'SUCCESS')
        self.assertEqual(get_status(completed=2, returned=False, collisions=0, failed=0), 'FAILED_TO_RETURN')
        self.assertEqual(get_status(completed=1, returned=False, collisions=0, failed=0), 'IN_PROGRESS')
        self.assertEqual(get_status(completed=1, returned=False, collisions=0, failed=1), 'INCOMPLETE_ORDERS')
        self.assertEqual(get_status(completed=2, returned=True, collisions=1, failed=0), 'COLLISION_DETECTED')


class SmoothMotionControllerTests(unittest.TestCase):
    def setUp(self):
        self.ctrl = control.SmoothMotionController(
            max_v=0.55,
            max_w=0.65,
            max_accel=0.60,
            max_decel_normal=0.80,
            max_w_accel=1.20,
            kp_w=1.20,
            kd_w=0.22,
            approach_dist=4.5,
            docking_speed=0.18,
            wheel_track=0.62
        )

    def test_progressive_acceleration_from_rest(self):
        # Starting from 0.0 m/s with target 0.55 m/s and dt = 0.05
        # Max acceleration dv = 0.60 * 0.05 = 0.030 m/s per cycle
        v, w = self.ctrl.ramp_velocities(0.0, 0.0, 0.55, 0.0, dt=0.05)
        self.assertAlmostEqual(v, 0.030, places=4)
        self.assertLess(v, 0.55)

    def test_approach_deceleration_profile(self):
        # Beyond approach distance (> 4.5m), speed is cruise speed
        v_far = self.ctrl.compute_approach_speed(10.0, cruise_speed=0.55)
        self.assertAlmostEqual(v_far, 0.55, places=3)

        # Midway at 2.25m, speed is decelerated
        v_mid = self.ctrl.compute_approach_speed(2.25, cruise_speed=0.55)
        self.assertLess(v_mid, 0.55)
        self.assertGreater(v_mid, 0.18)

        # Inside tolerance / docking (0.0m), speed is minimum docking creep speed (0.18)
        v_dock = self.ctrl.compute_approach_speed(0.0, cruise_speed=0.55)
        self.assertAlmostEqual(v_dock, 0.18, places=2)

    def test_turn_curvature_slowdown(self):
        # Zero heading error -> full base speed
        v_straight = self.ctrl.compute_turn_speed(0.0, 0.55)
        self.assertAlmostEqual(v_straight, 0.55, places=3)

        # 45-degree turn (0.785 rad) -> speed scaled down
        v_turn = self.ctrl.compute_turn_speed(0.785, 0.55)
        self.assertLess(v_turn, v_straight)
        self.assertGreaterEqual(v_turn, 0.18)

    def test_critically_damped_steering_counteracts_yaw_rate(self):
        # When heading error is positive and robot is already turning in that direction (positive yaw rate),
        # D-term dampens steering command to prevent overshoot / oscillation
        w_undamped = self.ctrl.compute_steering(0.30, yaw_rate=0.0, dt=0.05)
        w_damped = self.ctrl.compute_steering(0.30, yaw_rate=0.40, dt=0.05)
        self.assertLess(w_damped, w_undamped)

    def test_emergency_stop_immediacy(self):
        # Emergency stop must return 0.0, 0.0 immediately regardless of current speed
        v, w = self.ctrl.ramp_velocities(0.55, 0.40, 0.0, 0.0, dt=0.05, is_emergency_stop=True)
        self.assertEqual(v, 0.0)
        self.assertEqual(w, 0.0)

    def test_anti_wheel_stall_limit(self):
        # At moderate speed, max_w is bounded to prevent inner wheel reversal/stall
        v, w = self.ctrl.ramp_velocities(0.12, 0.0, 0.12, 1.0, dt=0.05)
        # Inner wheel v_in = v - w * (wheel_track / 2) >= ~0.04
        inner_v = v - w * (0.62 / 2.0)
        self.assertGreaterEqual(inner_v, 0.02)


class MissionLifecycleTests(unittest.TestCase):
    def test_all_12_required_states_present(self):
        from delivery_robot_sim.order_manager import MissionLifecycleState
        expected_states = [
            'WAITING_FOR_ORDER',
            'ORDER_ACCEPTED',
            'PLANNING_ROUTE',
            'NAVIGATING_TO_CLIENT',
            'AVOIDING_OBSTACLE',
            'WAITING_AT_RED_LIGHT',
            'APPROACHING_DELIVERY_POINT',
            'DELIVERING',
            'DELIVERY_CONFIRMED',
            'RETURNING_TO_DEPOT',
            'DOCKING',
            'MISSION_COMPLETED'
        ]
        for s in expected_states:
            self.assertIn(s, MissionLifecycleState.__members__)

    def test_recovery_and_failure_states_present(self):
        from delivery_robot_sim.order_manager import MissionLifecycleState
        recovery_states = [
            'RECOVERING_ROUTE',
            'WAITING_FOR_CLEAR_PATH',
            'NAVIGATION_FAILED',
            'DELIVERY_FAILED',
            'MISSION_CANCELLED',
            'MISSION_FAILED'
        ]
        for s in recovery_states:
            self.assertIn(s, MissionLifecycleState.__members__)

    def test_predefined_locations_catalog(self):
        from delivery_robot_sim.order_manager import PREDEFINED_LOCATIONS
        self.assertEqual(PREDEFINED_LOCATIONS['DEPOT_POST_OFFICE'], (-30.0, 0.0))
        self.assertEqual(PREDEFINED_LOCATIONS['CLIENT_1_NORTH_AVENUE'], (-15.0, 15.0))
        self.assertEqual(PREDEFINED_LOCATIONS['CLIENT_2_NORTH_AVENUE'], (-15.0, 28.0))

    def test_duplicate_delivery_confirmation_prevention(self):
        from delivery_robot_sim.order_manager import OrderManager, DeliveryOrder, OrderStatus, MissionLifecycleState
        om = OrderManager()
        o = DeliveryOrder('ORD-TEST', 'DEPOT', (-30.0, 0.0), 'CLIENT', (-15.0, 15.0), 'PKG-T')
        om.add_order(o)
        om.confirm_pickup('ORD-TEST')

        # First confirmation must succeed
        res1 = om.confirm_delivery('ORD-TEST', now=10.0)
        self.assertTrue(res1)
        self.assertEqual(o.status, OrderStatus.COMPLETED)
        self.assertEqual(om.mission_state, MissionLifecycleState.DELIVERY_CONFIRMED.value)

        # Second confirmation must fail and prevent duplicate event
        res2 = om.confirm_delivery('ORD-TEST', now=12.0)
        self.assertFalse(res2)

    def test_invalid_duplicate_order_rejected(self):
        from delivery_robot_sim.order_manager import OrderManager, DeliveryOrder
        om = OrderManager()
        o1 = DeliveryOrder('ORD-DUP', 'DEPOT', (-30.0, 0.0), 'CLIENT', (-15.0, 15.0), 'PKG-1')
        o2 = DeliveryOrder('ORD-DUP', 'DEPOT', (-30.0, 0.0), 'CLIENT', (-15.0, 15.0), 'PKG-2')
        self.assertTrue(om.add_order(o1))
        self.assertFalse(om.add_order(o2))  # duplicate ID rejected

    def test_cancel_order_transitions_to_cancelled(self):
        from delivery_robot_sim.order_manager import OrderManager, DeliveryOrder, OrderStatus, MissionLifecycleState
        om = OrderManager()
        o = DeliveryOrder('ORD-CANCEL', 'DEPOT', (-30.0, 0.0), 'CLIENT', (-15.0, 15.0), 'PKG-C')
        om.add_order(o)
        om.confirm_pickup('ORD-CANCEL')
        om.evaluate_next_action((-25.0, 0.0), now=5.0)

        self.assertTrue(om.cancel_order('ORD-CANCEL', 'Emergency cancellation'))
        self.assertEqual(o.status, OrderStatus.CANCELLED)
        self.assertEqual(om.mission_state, MissionLifecycleState.MISSION_CANCELLED.value)
        self.assertTrue(om.returning_to_depot)


class SafetySupervisorTests(unittest.TestCase):
    def setUp(self):
        from delivery_robot_sim.safety_supervisor import SafetySupervisor, SafetySupervisorState
        self.sup = SafetySupervisor(
            sensor_timeout_s=0.50,
            patience_timeout_s=8.0,
            stall_timeout_s=2.5,
            min_safe_clearance_m=0.85,
            reduced_speed_clearance_m=3.0,
            recovery_dwell_s=1.0
        )

    def test_nominal_operation(self):
        from delivery_robot_sim.safety_supervisor import SafetySupervisorState
        state, v_lim, override, reason = self.sup.evaluate(
            now=1.0, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03,
            min_obstacle_dist=15.0, is_pedestrian_crossing=False, cmd_v=0.50, actual_v=0.48
        )
        self.assertEqual(state, SafetySupervisorState.NORMAL_OPERATION)
        self.assertAlmostEqual(v_lim, 0.55)
        self.assertIsNone(override)

    def test_sensor_timeout_latches_fault(self):
        from delivery_robot_sim.safety_supervisor import SafetySupervisorState
        # Camera is 0.60s old (> 0.50s timeout)
        state, v_lim, override, reason = self.sup.evaluate(
            now=1.0, camera_age=0.60, depth_age=0.05, imu_age=0.02, odom_age=0.03,
            min_obstacle_dist=15.0
        )
        self.assertEqual(state, SafetySupervisorState.FAULT_LATCHED)
        self.assertEqual(override, (0.0, 0.0))
        self.assertIn('CAM', reason)

        # When camera returns, it transitions to active RECOVERY_CHECK and remains safely stopped
        state2, _, override2, _ = self.sup.evaluate(
            now=1.1, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03,
            min_obstacle_dist=15.0
        )
        self.assertEqual(state2, SafetySupervisorState.RECOVERY_CHECK)
        self.assertEqual(override2, (0.0, 0.0))

    def test_motor_stall_detection(self):
        from delivery_robot_sim.safety_supervisor import SafetySupervisorState
        # Commanded 0.45 m/s but actual is 0.00 m/s for 3.0s (> 2.5s stall timeout)
        self.sup.evaluate(now=0.0, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03,
                          min_obstacle_dist=10.0, cmd_v=0.45, actual_v=0.00)
        state, _, override, reason = self.sup.evaluate(
            now=3.0, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03,
            min_obstacle_dist=10.0, cmd_v=0.45, actual_v=0.00
        )
        self.assertEqual(state, SafetySupervisorState.FAULT_LATCHED)
        self.assertIn('MOTOR_STALL', reason)
        self.assertEqual(override, (0.0, 0.0))

    def test_pedestrian_crossing_yield_and_patience_replanning(self):
        from delivery_robot_sim.safety_supervisor import SafetySupervisorState
        # 1. Pedestrian crossing detected -> yield immediately
        state, v_lim, override, reason = self.sup.evaluate(
            now=10.0, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03,
            min_obstacle_dist=2.5, is_pedestrian_crossing=True, actual_v=0.0
        )
        self.assertEqual(state, SafetySupervisorState.WAITING_FOR_CLEAR_PATH)
        self.assertEqual(override, (0.0, 0.0))

        # 2. After 4 seconds, still waiting
        state2, _, override2, _ = self.sup.evaluate(
            now=14.0, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03,
            min_obstacle_dist=2.5, is_pedestrian_crossing=True, actual_v=0.0
        )
        self.assertEqual(state2, SafetySupervisorState.WAITING_FOR_CLEAR_PATH)

        # 3. After 9 seconds (> 8.0s patience), transition to REPLANNING
        state3, v_lim3, override3, reason3 = self.sup.evaluate(
            now=19.5, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03,
            min_obstacle_dist=2.5, is_pedestrian_crossing=True, actual_v=0.0
        )
        self.assertEqual(state3, SafetySupervisorState.REPLANNING)
        self.assertIsNone(override3)
        self.assertAlmostEqual(v_lim3, 0.18)

    def test_recovery_check_verification(self):
        from delivery_robot_sim.safety_supervisor import SafetySupervisorState
        # Trigger fault
        self.sup.evaluate(now=1.0, camera_age=0.8, depth_age=0.05, imu_age=0.02, odom_age=0.03, min_obstacle_dist=10.0)
        self.assertEqual(self.sup.state, SafetySupervisorState.FAULT_LATCHED)

        # Trigger recovery
        self.assertTrue(self.sup.clear_latched_fault())
        self.assertEqual(self.sup.state, SafetySupervisorState.RECOVERY_CHECK)

        # Evaluating during dwell (0.5s < 1.0s) stays in RECOVERY_CHECK
        s1, _, _, _ = self.sup.evaluate(now=2.0, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03, min_obstacle_dist=10.0)
        self.assertEqual(s1, SafetySupervisorState.RECOVERY_CHECK)

        # After dwell (now = 3.2s >= 2.0 + 1.0), returns to NORMAL_OPERATION
        s2, _, _, _ = self.sup.evaluate(now=3.2, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03, min_obstacle_dist=10.0)
        self.assertEqual(s2, SafetySupervisorState.NORMAL_OPERATION)

    def test_emergency_stop_assertion(self):
        from delivery_robot_sim.safety_supervisor import SafetySupervisorState
        self.sup.assert_emergency_stop('MANUAL_TEST_BUTTON')
        self.assertEqual(self.sup.state, SafetySupervisorState.EMERGENCY_STOP)

        state, v_lim, override, reason = self.sup.evaluate(
            now=1.0, camera_age=0.05, depth_age=0.05, imu_age=0.02, odom_age=0.03, min_obstacle_dist=10.0
        )
        self.assertEqual(state, SafetySupervisorState.EMERGENCY_STOP)
        self.assertEqual(override, (0.0, 0.0))

        # Unlatching allows recovery
        self.sup.release_emergency_stop()
        self.assertEqual(self.sup.state, SafetySupervisorState.RECOVERY_CHECK)


class CompartmentSecurityTests(unittest.TestCase):
    def setUp(self):
        from delivery_robot_sim.compartment_manager import CompartmentManager, CompartmentLockState
        self.cm = CompartmentManager(token_validity_s=300.0)
        self.cm.assign_package('COMPARTMENT_1', 'PKG-101', 'ORD-001')

    def test_otp_generation_and_valid_authentication(self):
        from delivery_robot_sim.compartment_manager import CompartmentLockState
        otp, token_hash = self.cm.generate_delivery_token('ORD-001', now=100.0)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

        # Correct code unlocks compartment
        success, msg = self.cm.authenticate_customer('ORD-001', otp, now=120.0)
        self.assertTrue(success)
        self.assertEqual(self.cm.get_compartment_status('ORD-001'), CompartmentLockState.UNLOCKED_DELIVERY.value)

        # Confirm hatch closed locks it again
        self.assertTrue(self.cm.confirm_compartment_closed_and_locked('ORD-001'))
        self.assertEqual(self.cm.get_compartment_status('ORD-001'), CompartmentLockState.DELIVERY_VERIFIED.value)

    def test_replay_protection(self):
        otp, _ = self.cm.generate_delivery_token('ORD-001', now=100.0)
        # First use succeeds
        ok1, _ = self.cm.authenticate_customer('ORD-001', otp, now=110.0)
        self.assertTrue(ok1)

        # Reusing the exact same OTP fails
        ok2, msg2 = self.cm.authenticate_customer('ORD-001', otp, now=115.0)
        self.assertFalse(ok2)
        self.assertIn('TOKEN_ALREADY_USED', msg2)

    def test_tamper_lockout(self):
        from delivery_robot_sim.compartment_manager import CompartmentLockState
        otp, _ = self.cm.generate_delivery_token('ORD-001', now=100.0)

        # 3 wrong attempts
        self.cm.authenticate_customer('ORD-001', '000000', now=105.0)
        self.cm.authenticate_customer('ORD-001', '111111', now=106.0)
        ok3, msg3 = self.cm.authenticate_customer('ORD-001', '222222', now=107.0)
        self.assertFalse(ok3)
        self.assertIn('TAMPER_ALERT', msg3)
        self.assertEqual(self.cm.get_compartment_status('ORD-001'), CompartmentLockState.TAMPER_ALERT.value)

    def test_token_expiration(self):
        otp, _ = self.cm.generate_delivery_token('ORD-001', now=100.0)
        # Attempt after 301 seconds (> 300s validity window)
        ok, msg = self.cm.authenticate_customer('ORD-001', otp, now=405.0)
        self.assertFalse(ok)
        self.assertIn('EXPIRED', msg)


class DynamicActorTrackingTests(unittest.TestCase):
    def setUp(self):
        from delivery_robot_sim.vision import DynamicActorTracker
        self.tracker = DynamicActorTracker(crossing_speed_threshold_mps=0.15)

    def test_lateral_crossing_speed_estimation(self):
        # Frame 1 at t=1.0: obstacle at y=-0.80m (left side)
        res1 = self.tracker.update(now=1.0, obs_detected=True, obs_dist=3.0, obs_y_lat=-0.80, robot_speed=0.3)
        self.assertFalse(res1['is_pedestrian_crossing'])

        # Frame 2 at t=1.5: obstacle moved laterally to y=-0.50m (moving right across corridor at 0.6 m/s)
        res2 = self.tracker.update(now=1.5, obs_detected=True, obs_dist=2.8, obs_y_lat=-0.50, robot_speed=0.3)
        self.assertAlmostEqual(res2['lateral_speed'], 0.60, places=2)

        # Frame 3 at t=2.0: obstacle reached y=-0.20m (continuing across path, TTC ~ 3.5s)
        res3 = self.tracker.update(now=2.0, obs_detected=True, obs_dist=2.5, obs_y_lat=-0.20, robot_speed=0.3)
        self.assertTrue(res3['is_pedestrian_crossing'])
        self.assertLess(res3['ttc'], 5.0)

    def test_stationary_obstacle_no_pedestrian_flag(self):
        # Stationary barrier: lateral position stays constant at y=0.25m
        self.tracker.update(now=1.0, obs_detected=True, obs_dist=3.0, obs_y_lat=0.25)
        self.tracker.update(now=1.5, obs_detected=True, obs_dist=2.8, obs_y_lat=0.25)
        res = self.tracker.update(now=2.0, obs_detected=True, obs_dist=2.6, obs_y_lat=0.25)
        self.assertFalse(res['is_pedestrian_crossing'])
        self.assertAlmostEqual(res['lateral_speed'], 0.0, places=2)


class InPlaceTurnTests(unittest.TestCase):
    def setUp(self):
        self.ctrl = control.SmoothMotionController(max_w=0.65, kp_w=1.20, kd_w=0.22)

    def test_in_place_turn_magnitude_and_direction(self):
        w_left = self.ctrl.compute_in_place_turn(1.57)
        self.assertGreater(w_left, 0.0)
        self.assertAlmostEqual(w_left, 0.65, places=2)

        w_right = self.ctrl.compute_in_place_turn(-1.57)
        self.assertLess(w_right, 0.0)
        self.assertAlmostEqual(w_right, -0.65, places=2)

    def test_in_place_turn_damping(self):
        w_undamped = self.ctrl.compute_in_place_turn(0.50, yaw_rate=0.0)
        w_damped = self.ctrl.compute_in_place_turn(0.50, yaw_rate=0.50)
        self.assertLess(w_damped, w_undamped)

    def test_ramp_allows_in_place_turn_at_zero_linear_speed(self):
        new_v, new_w = self.ctrl.ramp_velocities(0.0, 0.0, 0.0, 0.65, dt=0.05)
        self.assertEqual(new_v, 0.0)
        self.assertGreater(new_w, 0.0)


class ProgressWatchdogTests(unittest.TestCase):
    def setUp(self):
        from delivery_robot_sim.progress_watchdog import ProgressWatchdog
        self.wd = ProgressWatchdog(progress_timeout_s=4.0, min_progress_dist_m=0.20, rotation_timeout_s=4.0)

    def test_nominal_progress_resets_watchdog(self):
        self.wd.reset_target(now=0.0, target_name="WP1", target_wp=(-20.0, 0.0), current_xy=(-30.0, 0.0))
        st = self.wd.evaluate(now=1.0, current_xy=(-29.0, 0.0), target_wp=(-20.0, 0.0), heading_err=0.05, cmd_v=0.5, cmd_w=0.0, actual_v=0.5)
        self.assertFalse(st.stall_detected)
        self.assertEqual(st.state, "NORMAL")

    def test_progress_timeout_stall_detection(self):
        self.wd.reset_target(now=0.0, target_name="WP1", target_wp=(-20.0, 0.0), current_xy=(-30.0, 0.0))
        st = self.wd.evaluate(now=4.5, current_xy=(-30.0, 0.0), target_wp=(-20.0, 0.0), heading_err=0.0, cmd_v=0.5, cmd_w=0.0, actual_v=0.0)
        self.assertTrue(st.stall_detected)
        self.assertEqual(st.state, "PROGRESS_STALL")
        self.assertIn("OBSTRUCTION", st.stall_reason)

    def test_rotation_convergence_stall_detection(self):
        self.wd.reset_target(now=0.0, target_name="WP1", target_wp=(-20.0, 0.0), current_xy=(-30.0, 0.0))
        self.wd.evaluate(now=1.0, current_xy=(-30.0, 0.0), target_wp=(-20.0, 0.0), heading_err=1.2, cmd_v=0.0, cmd_w=0.5, actual_v=0.0)
        st = self.wd.evaluate(now=5.5, current_xy=(-30.0, 0.0), target_wp=(-20.0, 0.0), heading_err=1.2, cmd_v=0.0, cmd_w=0.5, actual_v=0.0)
        self.assertTrue(st.stall_detected)
        self.assertEqual(st.state, "ROTATION_STALL")

    def test_operational_pause_does_not_trigger_watchdog(self):
        self.wd.reset_target(now=0.0, target_name="DEPOT", target_wp=(-30.0, 0.0), current_xy=(-30.0, 0.0))
        st = self.wd.evaluate(now=10.0, current_xy=(-30.0, 0.0), target_wp=(-30.0, 0.0), heading_err=0.0, cmd_v=0.0, cmd_w=0.0, actual_v=0.0, is_paused=True)
        self.assertFalse(st.stall_detected)
        self.assertEqual(st.state, "NORMAL")


class RoutePlannerTests(unittest.TestCase):
    def test_direct_single_street_route(self):
        from delivery_robot_sim.route_planner import plan_city_route
        wps = plan_city_route((-15.0, 15.0), (-15.0, 28.0))
        self.assertEqual(wps, [(-15.0, 28.0)])

    def test_single_corner_turn_route(self):
        from delivery_robot_sim.route_planner import plan_city_route
        wps = plan_city_route((-25.0, 0.0), (-15.0, 15.0))
        self.assertEqual(len(wps), 2)
        self.assertEqual(wps[0], (-15.0, -0.75))
        self.assertEqual(wps[1], (-15.0, 15.0))

    def test_depot_egress_routing(self):
        from delivery_robot_sim.route_planner import plan_city_route
        wps = plan_city_route((-31.5, -0.75), (-45.0, 15.0))
        self.assertEqual(wps[0], (-27.5, -0.75))
        self.assertEqual(wps[-1], (-45.0, 15.0))

    def test_reachability_validation(self):
        from delivery_robot_sim.route_planner import is_destination_reachable
        self.assertTrue(is_destination_reachable(-30.0, 0.0))
        self.assertTrue(is_destination_reachable(-15.0, 25.0))
        self.assertTrue(is_destination_reachable(-45.0, 10.0))
        self.assertFalse(is_destination_reachable(999.0, 999.0))

    def test_destination_validation_and_snapping(self):
        from delivery_robot_sim.route_planner import validate_and_snap_destination
        # Valid customer bay: Client 1 with safe 1.20m curbside standoff
        valid, snap_xy, heading, status = validate_and_snap_destination(-13.4, 15.0)
        self.assertTrue(valid)
        self.assertEqual(snap_xy, (-14.6, 15.0))
        self.assertAlmostEqual(heading, 0.0)
        self.assertIn("VALIDATED_BAY", status)

        # Inside indoor depot dock facility
        valid, snap_xy, heading, status = validate_and_snap_destination(-30.0, 0.0)
        self.assertTrue(valid)
        self.assertEqual(snap_xy, (-31.5, -0.75))
        self.assertEqual(status, "DEPOT_DOCK_FACILITY")

        # Outside city boundaries
        valid, _, _, status = validate_and_snap_destination(500.0, 500.0)
        self.assertFalse(valid)
        self.assertEqual(status, "REJECTED_OUTSIDE_CITY_BOUNDS")

        # Inside deep solid restricted building (> 8m from road)
        valid, _, _, status = validate_and_snap_destination(-30.0, 25.0)
        self.assertFalse(valid)

    def test_building_penetration_prevention(self):
        from delivery_robot_sim.route_planner import (
            segment_intersects_box, does_segment_collide_with_buildings, plan_city_route
        )
        # 1. Segment intersects building block
        box = (-42.5, -17.5, 3.0, 42.5)
        self.assertTrue(segment_intersects_box((-50.0, 20.0), (-10.0, 20.0), box))
        self.assertFalse(segment_intersects_box((-50.0, -10.0), (-10.0, -10.0), box))

        # 2. Destination behind depot: route must navigate around via street grid, NOT through back wall
        start_outside = (-27.0, -0.75)
        behind_depot = (-45.0, 15.0)
        route = plan_city_route(start_outside, behind_depot)
        self.assertTrue(len(route) >= 2)
        # Ensure no waypoint punches through the depot compound (-35.0 to -28.0, y in [-2.5, 2.0])
        for wp in route:
            in_back_wall = (-35.0 <= wp[0] <= -28.5 and abs(wp[1]) <= 2.2)
            self.assertFalse(in_back_wall, f"Waypoint {wp} penetrated depot back wall!")

    def test_obstacle_blocked_corridor_replanning(self):
        from delivery_robot_sim.route_planner import _astar
        # Nominal path from NORTH_AVE_SOUTH to EAST_SOUTH: direct edge on South Street
        path_open, cost_open = _astar('NORTH_AVE_SOUTH', 'EAST_SOUTH')
        self.assertEqual(path_open, ['NORTH_AVE_SOUTH', 'EAST_SOUTH'])

        # Block the direct South Street edge: must route via NORTH_AVE_CENTRAL -> EAST_CENTRAL -> EAST_SOUTH
        blocked = {('NORTH_AVE_SOUTH', 'EAST_SOUTH'), ('EAST_SOUTH', 'NORTH_AVE_SOUTH')}
        path_detour, cost_detour = _astar('NORTH_AVE_SOUTH', 'EAST_SOUTH', blocked_edges=blocked)
        self.assertEqual(path_detour, ['NORTH_AVE_SOUTH', 'NORTH_AVE_CENTRAL', 'EAST_CENTRAL', 'EAST_SOUTH'])
        self.assertGreater(cost_detour, cost_open)


class TrafficLightROITests(unittest.TestCase):
    def test_upper_right_roi_rejection_of_ground_red_objects(self):
        # Frame with a red object on the ground (e.g. red car/brick at u=100, v=200)
        img = np.full((240, 320, 3), 60, dtype=np.uint8)
        cv2.rectangle(img, (80, 180), (120, 220), (0, 0, 255), -1)  # BGR red

        # Unrestricted full frame sees red
        red_full, _ = vision.traffic_light_areas(img, roi=None)
        self.assertGreater(red_full, 500)

        # Targeted upper-right traffic light ROI rejects ground red object!
        red_targeted, _ = vision.traffic_light_areas(img, roi=(10, 130, 130, 315))
        self.assertEqual(red_targeted, 0)

        # Elevated traffic light in upper right (u=200, v=50) is detected
        cv2.circle(img, (200, 50), 10, (0, 0, 255), -1)
        red_elevated, _ = vision.traffic_light_areas(img, roi=(10, 130, 130, 315))
        self.assertGreater(red_elevated, 100)


class CargoDeliveryManagerTests(unittest.TestCase):
    def test_cargo_manager_initialization_and_hatch_control(self):
        from delivery_robot_sim.cargo_delivery_manager import CargoDeliveryManager, HATCH_CLOSED_ANGLE, HATCH_OPEN_ANGLE
        mgr = CargoDeliveryManager(node_name="test_cargo_mgr")
        self.assertEqual(mgr.hatch_angle, HATCH_CLOSED_ANGLE)
        self.assertEqual(mgr.hatch_state, "CLOSED")
        self.assertFalse(mgr.package_loaded)

        # Test opening hatch
        mgr.set_hatch_target(HATCH_OPEN_ANGLE)
        self.assertAlmostEqual(mgr.hatch_angle, 1.05, places=2)
        self.assertEqual(mgr.hatch_state, "OPEN")

        # Test closing hatch
        mgr.set_hatch_target(HATCH_CLOSED_ANGLE)
        self.assertEqual(mgr.hatch_angle, 0.0)
        self.assertEqual(mgr.hatch_state, "CLOSED")

    def test_package_state_and_toggle(self):
        from delivery_robot_sim.cargo_delivery_manager import CargoDeliveryManager
        mgr = CargoDeliveryManager(node_name="test_cargo_mgr_2")
        self.assertFalse(mgr.package_loaded)
        mgr.package_loaded = True
        self.assertTrue(mgr.package_loaded)
        mgr.package_loaded = False
        self.assertFalse(mgr.package_loaded)

    def test_package_sdf_path_exists(self):
        from delivery_robot_sim.cargo_delivery_manager import get_package_sdf_path
        sdf_path = get_package_sdf_path()
        self.assertTrue(os.path.exists(sdf_path), f"Package SDF path does not exist: {sdf_path}")


class BillOfMaterialsValidationTests(unittest.TestCase):
    """Rigorous mathematical verification of BOM.csv and generator script."""

    def setUp(self):
        self.repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.bom_path = os.path.join(
            self.repo_root, "delivery_robot_sim", "web_dashboard", "downloads", "BOM.csv"
        )

    def test_bom_csv_file_exists(self):
        self.assertTrue(os.path.exists(self.bom_path), f"BOM.csv not found at {self.bom_path}")

    def test_bom_arithmetic_exactness(self):
        import csv
        with open(self.bom_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            item_count = 0
            for row in reader:
                subsystem = row["Subsystem"].strip()
                if subsystem.startswith("Total") or "Tunisie" in subsystem:
                    continue
                item_count += 1
                qty = int(row["Quantity"])
                unit_cost = float(row["Unit Cost USD"])
                ext_cost = float(row["Extended Cost USD"])
                self.assertGreater(qty, 0, f"Zero or negative quantity on {row['Component']}")
                self.assertGreater(unit_cost, 0.0, f"Zero or negative unit cost on {row['Component']}")
                expected = round(qty * unit_cost, 2)
                self.assertAlmostEqual(
                    ext_cost, expected, places=2,
                    msg=f"BOM math error on {row['Component']}: {qty} * {unit_cost} != {ext_cost}"
                )
            self.assertGreaterEqual(item_count, 15, "BOM should have at least 15 verified line items")

    def test_bom_total_sum_matches(self):
        import csv
        parts_total = 0.0
        reported_total = None
        with open(self.bom_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                subsystem = row["Subsystem"].strip()
                if subsystem == "Total Pièces Brutes":
                    reported_total = float(row["Extended Cost USD"])
                elif not subsystem.startswith("Total") and "Tunisie" not in subsystem:
                    parts_total += float(row["Extended Cost USD"])

        self.assertIsNotNone(reported_total, "Total Pièces Brutes row missing from BOM.csv")
        self.assertAlmostEqual(
            parts_total, reported_total, places=2,
            msg=f"Sum of parts ({parts_total:.2f}) does not match reported total ({reported_total:.2f})"
        )

    def test_bom_table_generator_script(self):
        from tools.generate_bom_table import generate_markdown_table
        table_md, parts_tot, landed_tot = generate_markdown_table(self.bom_path)
        self.assertIn("Total pieces brutes", table_md)
        self.assertIn("Total rendu Tunisie", table_md)
        self.assertGreater(parts_tot, 1000.0)
        self.assertGreater(landed_tot, parts_tot)


if __name__ == "__main__":
    unittest.main(verbosity=2)



