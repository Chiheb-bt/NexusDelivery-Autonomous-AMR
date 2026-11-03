"""Unit tests for Corporate Website, Customer Application, and Supervisor Cockpit Tri-Portal Separation and RBAC APIs."""

import json
import os
import sys
import unittest
import urllib.request
import urllib.error
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from delivery_robot_sim.web_bridge_node import WebBridgeNode


class WebPortalsValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize standalone node on isolated test port
        cls.port = 8991
        cls.node = WebBridgeNode(port=cls.port)
        time.sleep(0.4)
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    def test_01_corporate_portal_served_at_root(self):
        url = f"{self.base_url}/"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode('utf-8')
            self.assertIn("NexusDelivery — Autonomous Sidewalk Robotics Platform", html)
            self.assertIn("Autonomous Sidewalk Robotics for", html)
            self.assertIn("Last-Mile Logistics", html)
            self.assertIn("Launch Customer Portal", html)
            self.assertIn("Fleet Operations", html)
            self.assertIn("TRL 3–4 SIMULATION BASELINE", html)

    def test_02_customer_portal_served_at_client(self):
        url = f"{self.base_url}/client"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode('utf-8')
            self.assertIn("NexusDelivery — Autonomous Sidewalk Delivery Experience", html)
            self.assertIn("Curated Curbside Catalog", html)
            self.assertIn("Live Sidewalk GPS & Perception Radar", html)

    def test_03_supervisor_cockpit_served_at_supervisor(self):
        url = f"{self.base_url}/supervisor"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode('utf-8')
            self.assertIn("NexusDelivery — Fleet Engineer & Supervisor Cockpit", html)
            self.assertIn("NEXUS-AMR-01", html)
            self.assertIn("Powertrain & Hardware Diagnostics", html)

    def test_04_customer_registration_and_login_flow(self):
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

    def test_05_supervisor_login_flow(self):
        login_payload = {
            'email': 'supervisor@nexus.tn',
            'password': 'nexus2026'
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/auth/login",
            data=json.dumps(login_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data['success'])
            self.assertIn('token', data)
            self.assertEqual(data['user']['role'], 'OPERATOR')

    def test_06_unauthenticated_orders_blocked(self):
        # GET /api/orders without token must return 401 Unauthorized
        req_get = urllib.request.Request(f"{self.base_url}/api/orders")
        try:
            with urllib.request.urlopen(req_get) as resp:
                self.fail("Expected HTTP 401 Unauthorized but got 200 OK")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)

        # POST /api/orders without token must return 401 Unauthorized
        order_payload = {
            'target_name': 'CLIENT_1_NORTH_AVENUE',
            'items': [{'id': 'PRD-01', 'qty': 1}]
        }
        req_post = urllib.request.Request(
            f"{self.base_url}/api/orders",
            data=json.dumps(order_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req_post) as resp:
                self.fail("Expected HTTP 401 Unauthorized but got 200 OK")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)

    def test_07_customer_cannot_access_supervisor_apis(self):
        # Authenticate as customer Sophie
        login_payload = {'email': 'client@nexus.tn', 'password': 'password123'}
        req_login = urllib.request.Request(
            f"{self.base_url}/api/auth/login",
            data=json.dumps(login_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req_login) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            cust_token = data['token']

        # Attempt to call supervisor audit logs with customer token -> 403 Forbidden
        req_audit = urllib.request.Request(
            f"{self.base_url}/api/audit_logs",
            headers={'Authorization': f"Bearer {cust_token}"}
        )
        try:
            with urllib.request.urlopen(req_audit) as resp:
                self.fail("Expected 403 Forbidden for customer accessing audit logs")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)

        # Attempt to call supervisor teleop with customer token -> 403 Forbidden
        req_teleop = urllib.request.Request(
            f"{self.base_url}/api/teleop",
            data=json.dumps({'v': 0.5, 'w': 0.0}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {cust_token}"}
        )
        try:
            with urllib.request.urlopen(req_teleop) as resp:
                self.fail("Expected 403 Forbidden for customer executing robot teleop")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)

        # Attempt to call supervisor E-STOP with customer token -> 403 Forbidden
        req_estop = urllib.request.Request(
            f"{self.base_url}/api/estop",
            data=json.dumps({'state': 'STOP'}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {cust_token}"}
        )
        try:
            with urllib.request.urlopen(req_estop) as resp:
                self.fail("Expected 403 Forbidden for customer executing remote E-stop")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)

    def test_08_supervisor_can_access_supervisor_apis(self):
        # Authenticate as supervisor
        login_payload = {'email': 'supervisor@nexus.tn', 'password': 'nexus2026'}
        req_login = urllib.request.Request(
            f"{self.base_url}/api/auth/login",
            data=json.dumps(login_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req_login) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            sup_token = data['token']

        # Call teleop with supervisor token -> 200 OK
        req_teleop = urllib.request.Request(
            f"{self.base_url}/api/teleop",
            data=json.dumps({'v': 0.0, 'w': 0.0}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {sup_token}"}
        )
        with urllib.request.urlopen(req_teleop) as resp:
            self.assertEqual(resp.status, 200)
            teleop_res = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(teleop_res['success'])

        # Call audit logs with supervisor token -> 200 OK
        req_audit = urllib.request.Request(
            f"{self.base_url}/api/audit_logs",
            headers={'Authorization': f"Bearer {sup_token}"}
        )
        with urllib.request.urlopen(req_audit) as resp:
            self.assertEqual(resp.status, 200)
            logs = json.loads(resp.read().decode('utf-8'))
            self.assertIsInstance(logs, list)

    def test_09_customer_isolated_orders_tenant_security(self):
        # Login Sophie
        req_sophie = urllib.request.Request(
            f"{self.base_url}/api/auth/login",
            data=json.dumps({'email': 'client@nexus.tn', 'password': 'password123'}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req_sophie) as resp:
            tok = json.loads(resp.read().decode('utf-8'))['token']

        req_orders = urllib.request.Request(
            f"{self.base_url}/api/orders",
            headers={'Authorization': f"Bearer {tok}"}
        )
        with urllib.request.urlopen(req_orders) as resp:
            self.assertEqual(resp.status, 200)
            orders = json.loads(resp.read().decode('utf-8'))
            self.assertIsInstance(orders, list)
            # Ensure Sophie only sees orders where customer_id is USR-001
            for o in orders:
                self.assertEqual(o['customer_id'], 'USR-001')

    def test_10_otp_hatch_unlock(self):
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

    def test_11_static_assets_mime_types(self):
        with urllib.request.urlopen(f"{self.base_url}/corporate.css") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/css", resp.headers.get("Content-Type", ""))

        with urllib.request.urlopen(f"{self.base_url}/client.css") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/css", resp.headers.get("Content-Type", ""))

        with urllib.request.urlopen(f"{self.base_url}/supervisor.css") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/css", resp.headers.get("Content-Type", ""))


if __name__ == '__main__':
    unittest.main()
