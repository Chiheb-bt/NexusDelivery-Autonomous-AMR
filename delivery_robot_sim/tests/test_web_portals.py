"""Unit tests for Customer and Supervisor Dual Web Portals and Authentication APIs."""

import json
import os
import sys
import unittest
import urllib.request
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from delivery_robot_sim.web_bridge_node import WebBridgeNode


class WebPortalsValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize standalone node on test port
        cls.port = 8991
        cls.node = WebBridgeNode(port=cls.port)
        time.sleep(0.4)
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    def test_01_customer_portal_served_at_root(self):
        url = f"{self.base_url}/"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode('utf-8')
            self.assertIn("NexusDelivery — Autonomous Sidewalk Delivery Experience", html)
            self.assertIn("Curated Curbside Catalog", html)
            self.assertIn("Live Sidewalk GPS & Perception Radar", html)

    def test_02_supervisor_cockpit_served_at_supervisor(self):
        url = f"{self.base_url}/supervisor"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode('utf-8')
            self.assertIn("NexusDelivery — Fleet Engineer & Supervisor Cockpit", html)
            self.assertIn("NEXUS-AMR-01", html)
            self.assertIn("Powertrain & Hardware Diagnostics", html)

    def test_03_customer_registration_and_login_flow(self):
        unique_email = f"sami_{int(time.time() * 1000)}@nexus.tn"
        reg_payload = {
            'name': 'Sami Trabelsi',
            'email': unique_email,
            'password': 'safePassword123',
            'phone': '+216 22 333 444',
            'address': '7 Avenue de la Liberte, Tunis',
            'location_bay': 'CLIENT_1_NORTH_AVENUE'
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/auth/register",
            data=json.dumps(reg_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data['success'])
            self.assertIn('token', data)
            self.assertEqual(data['user']['name'], 'Sami Trabelsi')

        # Test login with newly registered credentials
        login_payload = {
            'email': unique_email,
            'password': 'safePassword123'
        }
        req_login = urllib.request.Request(
            f"{self.base_url}/api/auth/login",
            data=json.dumps(login_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req_login) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data['success'])
            self.assertIn('token', data)

    def test_04_otp_hatch_unlock(self):
        # Validate 6-digit OTP endpoint
        otp_payload = {'otp': '482910'}
        req = urllib.request.Request(
            f"{self.base_url}/api/verify_otp",
            data=json.dumps(otp_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data['success'])
            self.assertEqual(data['hatch_angle'], 1.05)
            self.assertEqual(data['hatch_status'], 'UNLOCKED_60DEG')

    def test_05_static_assets_mime_types(self):
        with urllib.request.urlopen(f"{self.base_url}/client.css") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/css", resp.headers.get("Content-Type", ""))

        with urllib.request.urlopen(f"{self.base_url}/supervisor.css") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/css", resp.headers.get("Content-Type", ""))


if __name__ == '__main__':
    unittest.main()
