"""Unit tests for Security, RBAC, and Database Subsystems."""

import os
import tempfile
import unittest

from delivery_robot_sim.security import (
    hash_password,
    verify_password,
    generate_session_token,
    generate_csrf_token,
    has_permission,
    LeakyBucketLimiter,
)
from delivery_robot_sim.database import DatabaseManager


class SecurityAndDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, 'test_nexus.db')
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_password_hashing_and_verification(self):
        pwd = "UltraSecretPassword123!"
        hashed = hash_password(pwd)
        self.assertTrue(hashed.startswith("pbkdf2:sha256:"))
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword!", hashed))
        self.assertFalse(verify_password("", hashed))

    def test_02_rbac_permissions(self):
        # Customers have restricted permissions
        self.assertTrue(has_permission('CUSTOMER', 'order:create'))
        self.assertTrue(has_permission('CUSTOMER', 'order:view_own'))
        self.assertFalse(has_permission('CUSTOMER', 'order:view_all'))
        self.assertFalse(has_permission('CUSTOMER', 'robot:teleop'))
        self.assertFalse(has_permission('CUSTOMER', 'robot:estop'))

        # Operators can teleop and E-stop
        self.assertTrue(has_permission('OPERATOR', 'robot:teleop'))
        self.assertTrue(has_permission('OPERATOR', 'robot:estop'))
        self.assertTrue(has_permission('OPERATOR', 'order:view_all'))
        self.assertFalse(has_permission('OPERATOR', 'users:manage'))

        # Super Admin has all
        self.assertTrue(has_permission('SUPER_ADMIN', 'users:manage'))
        self.assertTrue(has_permission('SUPER_ADMIN', 'audit:export'))

    def test_03_rate_limiter(self):
        limiter = LeakyBucketLimiter(capacity=3, refill_rate=0.1)
        self.assertTrue(limiter.is_allowed("test_key"))
        self.assertTrue(limiter.is_allowed("test_key"))
        self.assertTrue(limiter.is_allowed("test_key"))
        # 4th attempt exceeds capacity
        self.assertFalse(limiter.is_allowed("test_key"))

    def test_04_database_authentication_and_sessions(self):
        # Authenticate seeded user
        ok, msg, user, sess_tok, csrf_tok = self.db.authenticate_user('client@nexus.tn', 'password123')
        self.assertTrue(ok)
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'CUSTOMER')
        self.assertIsNotNone(sess_tok)
        self.assertIsNotNone(csrf_tok)

        # Validate session
        sess = self.db.validate_session(sess_tok)
        self.assertIsNotNone(sess)
        self.assertEqual(sess['email'], 'client@nexus.tn')

        # Revoke session
        self.assertTrue(self.db.revoke_session(sess_tok))
        self.assertIsNone(self.db.validate_session(sess_tok))

    def test_05_tenant_scoped_orders_prevent_idor(self):
        # User 1 (Sophie) has seeded ORD-001
        u1_orders = self.db.get_orders_for_customer('USR-001')
        self.assertGreaterEqual(len(u1_orders), 1)
        self.assertTrue(all(o['customer_id'] == 'USR-001' for o in u1_orders))

        # User 2 (Marc) has seeded ORD-002
        u2_orders = self.db.get_orders_for_customer('USR-002')
        self.assertGreaterEqual(len(u2_orders), 1)
        self.assertTrue(all(o['customer_id'] == 'USR-002' for o in u2_orders))

        # Ensure no cross-customer leakage
        u1_ids = {o['id'] for o in u1_orders}
        u2_ids = {o['id'] for o in u2_orders}
        self.assertTrue(u1_ids.isdisjoint(u2_ids))

    def test_06_otp_verification_lifecycle(self):
        new_ord = self.db.create_order(
            customer_id='USR-001',
            customer_name='Sophie Laurent',
            delivery_name='CLIENT_1_NORTH_AVENUE',
            target_x=-9.8, target_y=15.0,
            stopping_x=-14.6, stopping_y=15.0,
            approach_heading=0.0,
            package_id='PKG-TEST',
            items=[{'id': 'PRD-01', 'qty': 1}],
            otp='998877'
        )
        ord_id = new_ord['order_id']

        # Wrong OTP fails
        ok, msg = self.db.verify_order_otp(ord_id, '000000')
        self.assertFalse(ok)
        self.assertEqual(self.db.get_order(ord_id)['status'], 'QUEUED')

        # Correct OTP succeeds
        ok, msg = self.db.verify_order_otp(ord_id, '998877')
        self.assertTrue(ok)
        self.assertEqual(self.db.get_order(ord_id)['status'], 'DELIVERED')


if __name__ == '__main__':
    unittest.main()
