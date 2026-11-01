import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from gps_navigation_math import (
    gps_to_world_xy,
    is_near_forward_obstacle,
    waypoint_velocity,
    wrap_angle,
)


class GpsNavigationMathTest(unittest.TestCase):
    def test_reference_fix_maps_to_spawn(self):
        self.assertEqual(
            gps_to_world_xy(38.0, -122.0, 38.0, -122.0, -30.0, 0.0, 180.0),
            (-30.0, 0.0),
        )

    def test_heading_180_maps_east_to_negative_world_x(self):
        latitude = 38.0
        longitude = -122.0 + math.degrees(
            1.0 / (6378137.0 * math.cos(math.radians(latitude)))
        )
        x, y = gps_to_world_xy(
            latitude, longitude, latitude, -122.0, 0.0, 0.0, 180.0
        )
        self.assertAlmostEqual(x, -1.0, places=5)
        self.assertAlmostEqual(y, 0.0, places=5)

    def test_heading_180_maps_north_to_negative_world_y(self):
        latitude = 38.0 + math.degrees(1.0 / 6378137.0)
        x, y = gps_to_world_xy(
            latitude, -122.0, 38.0, -122.0, 0.0, 0.0, 180.0
        )
        self.assertAlmostEqual(x, 0.0, places=5)
        self.assertAlmostEqual(y, -1.0, places=5)

    def test_wrap_angle_stays_in_signed_pi_interval(self):
        self.assertAlmostEqual(wrap_angle(3.0 * math.pi), math.pi)
        self.assertAlmostEqual(wrap_angle(-3.0 * math.pi), -math.pi)

    def test_waypoint_ahead_commands_forward_motion(self):
        linear, angular, distance = waypoint_velocity(
            0.0, 0.0, 0.0, 10.0, 0.0, 0.35, 0.8, 2.0
        )
        self.assertAlmostEqual(linear, 0.35)
        self.assertAlmostEqual(angular, 0.0)
        self.assertAlmostEqual(distance, 10.0)

    def test_waypoint_behind_turns_in_place(self):
        linear, angular, _ = waypoint_velocity(
            0.0, 0.0, 0.0, -10.0, 0.0, 0.35, 0.8, 2.0
        )
        self.assertAlmostEqual(linear, 0.0)
        self.assertAlmostEqual(abs(angular), 0.8)

    def test_near_forward_person_is_hazard(self):
        self.assertTrue(
            is_near_forward_obstacle(
                "person", (140, 100, 180, 220), (240, 320, 3), 0.52, 0.30
            )
        )

    def test_far_or_off_corridor_object_is_not_hazard(self):
        self.assertFalse(
            is_near_forward_obstacle(
                "car", (10, 100, 50, 220), (240, 320, 3), 0.52, 0.30
            )
        )
        self.assertFalse(
            is_near_forward_obstacle(
                "car", (140, 10, 180, 80), (240, 320, 3), 0.52, 0.30
            )
        )


if __name__ == "__main__":
    unittest.main()
