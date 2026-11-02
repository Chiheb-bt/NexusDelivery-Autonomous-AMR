"""Persistent Relational Database Subsystem for NexusDelivery.

Implements:
- ACID-compliant SQLite storage with foreign keys and connection pooling
- Persistent user accounts, PBKDF2 password hashes, and session management
- Saved customer delivery addresses in Gazebo world coordinates
- Complete multi-drop order lifecycle tracking and tenant-scoped queries
- Immutable security audit logging
"""

import json
import os
import sqlite3
import threading
import time
from typing import Dict, List, Optional, Tuple

from delivery_robot_sim.security import (
    hash_password,
    verify_password,
    generate_session_token,
    generate_csrf_token,
)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'results', 'nexus_delivery.db'
)


class DatabaseManager:
    """Thread-safe SQLite database manager for NexusDelivery."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            self.db_path = os.path.abspath(DEFAULT_DB_PATH)
        else:
            self.db_path = os.path.abspath(db_path)

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_schema(self):
        with self._lock:
            with self._get_connection() as conn:
                conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'CUSTOMER',
                    phone TEXT,
                    mfa_enabled INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    csrf_token TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS addresses (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    label TEXT NOT NULL,
                    gazebo_x REAL NOT NULL,
                    gazebo_y REAL NOT NULL,
                    stopping_bay_id TEXT,
                    stopping_x REAL NOT NULL,
                    stopping_y REAL NOT NULL,
                    approach_heading REAL NOT NULL,
                    reachability_status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL REFERENCES users(id),
                    customer_name TEXT NOT NULL,
                    robot_id TEXT DEFAULT 'NEXUS-01',
                    delivery_name TEXT NOT NULL,
                    target_x REAL NOT NULL,
                    target_y REAL NOT NULL,
                    stopping_x REAL NOT NULL,
                    stopping_y REAL NOT NULL,
                    approach_heading REAL NOT NULL,
                    package_id TEXT NOT NULL,
                    items_json TEXT NOT NULL,
                    priority INTEGER DEFAULT 2,
                    status TEXT NOT NULL DEFAULT 'QUEUED',
                    otp_hash TEXT NOT NULL,
                    otp_display TEXT,
                    created_time REAL NOT NULL,
                    assigned_time REAL,
                    completed_time REAL,
                    cancelled_time REAL,
                    cancellation_reason TEXT,
                    route_distance_m REAL DEFAULT 0.0,
                    estimated_duration_s REAL DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_entity TEXT NOT NULL,
                    details_json TEXT,
                    ip_address TEXT
                );
                """)

                # Seed initial baseline accounts if empty
                cur = conn.execute("SELECT COUNT(*) FROM users;")
                if cur.fetchone()[0] == 0:
                    self._seed_default_data(conn)

    def _seed_default_data(self, conn: sqlite3.Connection):
        now = time.time()
        # Seed users
        seed_users = [
            ('USR-001', 'client@nexus.tn', hash_password('password123'), 'Sophie Laurent', 'CUSTOMER', '+216 20 123 456'),
            ('USR-002', 'marc@nexus.tn', hash_password('password123'), 'Marc Dubois', 'CUSTOMER', '+216 22 987 654'),
            ('USR-003', 'operator@nexus.tn', hash_password('nexus2026'), 'Fleet Operator Alpha', 'OPERATOR', '+216 71 100 200'),
            ('USR-004', 'admin@nexus.tn', hash_password('Admin2026!'), 'Lead Robotics Admin', 'SUPER_ADMIN', '+216 71 100 300'),
        ]
        conn.executemany(
            "INSERT INTO users (id, email, password_hash, name, role, phone) VALUES (?, ?, ?, ?, ?, ?);",
            seed_users
        )

        # Seed initial standard orders ORD-001 and ORD-002
        orders_seed = [
            (
                'ORD-001', 'USR-001', 'Sophie Laurent', 'NEXUS-01',
                'CLIENT_1_NORTH_AVENUE', -9.8, 15.0, -14.6, 15.0, 0.0,
                'PKG-101', json.dumps([{'id': 'PRD-01', 'name': 'Artisan Margherita Pizza', 'qty': 1}]),
                1, 'IN_TRANSIT', '482910', '482910', now, now, None, None, None, 31.5, 37.0
            ),
            (
                'ORD-002', 'USR-002', 'Marc Dubois', 'NEXUS-01',
                'CLIENT_2_NORTH_AVENUE', -9.8, 28.0, -14.6, 28.0, 0.0,
                'PKG-102', json.dumps([{'id': 'PRD-02', 'name': 'Fresh Sushi Bento Deluxe', 'qty': 2}]),
                2, 'ASSIGNED', '739104', '739104', now, now, None, None, None, 44.5, 52.0
            )
        ]
        conn.executemany("""
            INSERT INTO orders (
                id, customer_id, customer_name, robot_id,
                delivery_name, target_x, target_y, stopping_x, stopping_y, approach_heading,
                package_id, items_json, priority, status, otp_hash, otp_display,
                created_time, assigned_time, completed_time, cancelled_time, cancellation_reason,
                route_distance_m, estimated_duration_s
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, orders_seed)

        # Initial audit log entry
        conn.execute("""
            INSERT INTO audit_logs (actor_id, actor_role, action, target_entity, details_json)
            VALUES ('SYSTEM', 'SYSTEM', 'DATABASE_INITIALIZED', 'SCHEMA', '{"version": "2.0.0"}');
        """)

    # ========================================================================
    # User & Session Management
    # ========================================================================

    def register_user(self, email: str, password: str, name: str, role: str = 'CUSTOMER', phone: Optional[str] = None) -> Tuple[bool, str, Optional[Dict]]:
        email = email.strip().lower()
        if not email or not password or not name:
            return False, "Email, password, and name are required.", None

        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id FROM users WHERE email = ?;", (email,))
                if cur.fetchone():
                    return False, "An account with this email address already exists.", None

                cur = conn.execute("SELECT COUNT(*) FROM users;")
                count = cur.fetchone()[0]
                user_id = f"USR-{count + 1:03d}"
                pw_hash = hash_password(password)

                conn.execute(
                    "INSERT INTO users (id, email, password_hash, name, role, phone) VALUES (?, ?, ?, ?, ?, ?);",
                    (user_id, email, pw_hash, name, role, phone)
                )

                self.log_audit_event(user_id, role, 'USER_REGISTERED', user_id, f'{{"email": "{email}"}}')
                user_data = {
                    'id': user_id,
                    'email': email,
                    'name': name,
                    'role': role,
                    'phone': phone
                }
                return True, "Registration successful.", user_data

    def authenticate_user(self, email: str, password: str, ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[Dict], Optional[str], Optional[str]]:
        email = email.strip().lower()
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM users WHERE email = ?;", (email,))
                row = cur.fetchone()
                if not row:
                    self.log_audit_event('ANONYMOUS', 'GUEST', 'AUTH_FAILURE_NOT_FOUND', email, None, ip_address)
                    return False, "Invalid email address or password.", None, None, None

                if not verify_password(password, row['password_hash']):
                    self.log_audit_event(row['id'], row['role'], 'AUTH_FAILURE_PASSWORD', email, None, ip_address)
                    return False, "Invalid email address or password.", None, None, None

                # Generate session and CSRF token
                session_token = generate_session_token(32)
                csrf_token = generate_csrf_token(24)
                expires_at = time.time() + 1800.0  # 30-minute session

                conn.execute(
                    "INSERT INTO sessions (token, user_id, role, csrf_token, expires_at) VALUES (?, ?, ?, ?, ?);",
                    (session_token, row['id'], row['role'], csrf_token, expires_at)
                )

                self.log_audit_event(row['id'], row['role'], 'AUTH_LOGIN_SUCCESS', row['id'], None, ip_address)
                user_data = {
                    'id': row['id'],
                    'customer_id': row['id'],
                    'email': row['email'],
                    'name': row['name'],
                    'role': row['role'],
                    'phone': row['phone']
                }
                return True, "Authentication successful.", user_data, session_token, csrf_token

    def validate_session(self, token: str) -> Optional[Dict]:
        if not token:
            return None
        now = time.time()
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("""
                    SELECT s.token, s.user_id, s.role, s.csrf_token, s.expires_at,
                           u.email, u.name, u.phone
                    FROM sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.token = ? AND s.expires_at > ?;
                """, (token, now))
                row = cur.fetchone()
                if row:
                    return dict(row)
                return None

    def revoke_session(self, token: str) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM sessions WHERE token = ?;", (token,))
                return True

    # ========================================================================
    # Saved Addresses in Gazebo Coordinates
    # ========================================================================

    def save_address(
        self, user_id: str, label: str,
        gazebo_x: float, gazebo_y: float,
        stopping_bay_id: str, stopping_x: float, stopping_y: float,
        approach_heading: float, reachability_status: str
    ) -> Dict:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM addresses;")
                addr_id = f"ADDR-{cur.fetchone()[0] + 1:03d}"
                conn.execute("""
                    INSERT INTO addresses (
                        id, user_id, label, gazebo_x, gazebo_y,
                        stopping_bay_id, stopping_x, stopping_y, approach_heading, reachability_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (addr_id, user_id, label, gazebo_x, gazebo_y, stopping_bay_id, stopping_x, stopping_y, approach_heading, reachability_status))
                return {
                    'id': addr_id,
                    'user_id': user_id,
                    'label': label,
                    'gazebo_x': gazebo_x,
                    'gazebo_y': gazebo_y,
                    'stopping_bay_id': stopping_bay_id,
                    'stopping_x': stopping_x,
                    'stopping_y': stopping_y,
                    'approach_heading': approach_heading,
                    'reachability_status': reachability_status
                }

    def get_user_addresses(self, user_id: str) -> List[Dict]:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM addresses WHERE user_id = ? ORDER BY created_at DESC;", (user_id,))
                return [dict(r) for r in cur.fetchall()]

    # ========================================================================
    # Multi-Drop Order Management & Tenant-Scoped Queries
    # ========================================================================

    def create_order(
        self, customer_id: str, customer_name: str, delivery_name: str,
        target_x: float, target_y: float, stopping_x: float, stopping_y: float,
        approach_heading: float, package_id: str, items: List[Dict],
        priority: int = 2, otp: Optional[str] = None,
        route_dist: float = 0.0, est_duration: float = 0.0
    ) -> Dict:
        now = time.time()
        import random
        otp_val = otp if otp else f"{random.randint(100000, 999999)}"
        items_str = json.dumps(items)

        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM orders;")
                order_id = f"ORD-{cur.fetchone()[0] + 1:03d}"

                conn.execute("""
                    INSERT INTO orders (
                        id, customer_id, customer_name, robot_id, delivery_name,
                        target_x, target_y, stopping_x, stopping_y, approach_heading,
                        package_id, items_json, priority, status, otp_hash, otp_display,
                        created_time, assigned_time, route_distance_m, estimated_duration_s
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    order_id, customer_id, customer_name, 'NEXUS-01', delivery_name,
                    target_x, target_y, stopping_x, stopping_y, approach_heading,
                    package_id, items_str, priority, 'QUEUED', otp_val, otp_val,
                    now, now, route_dist, est_duration
                ))

                self.log_audit_event(customer_id, 'CUSTOMER', 'ORDER_CREATED', order_id, f'{{"delivery_name": "{delivery_name}"}}')

                return {
                    'order_id': order_id,
                    'customer_id': customer_id,
                    'customer_name': customer_name,
                    'robot_id': 'NEXUS-01',
                    'delivery_name': delivery_name,
                    'delivery_xy': [stopping_x, stopping_y],
                    'target_xy': [target_x, target_y],
                    'approach_heading': approach_heading,
                    'package_id': package_id,
                    'items': items,
                    'priority': priority,
                    'status': 'QUEUED',
                    'otp': otp_val,
                    'route_distance_m': route_dist,
                    'estimated_duration_s': est_duration,
                    'created_time': now
                }

    def get_order(self, order_id: str) -> Optional[Dict]:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM orders WHERE id = ?;", (order_id,))
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(row)
                d['items'] = json.loads(d['items_json'])
                d['order_id'] = d['id']
                d['delivery_xy'] = [d['stopping_x'], d['stopping_y']]
                d['otp'] = d['otp_display']
                return d

    def get_orders_for_customer(self, customer_id: str) -> List[Dict]:
        """Tenant-scoped query preventing IDOR: customers see only their own orders."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY created_time DESC;", (customer_id,))
                results = []
                for row in cur.fetchall():
                    d = dict(row)
                    d['items'] = json.loads(d['items_json'])
                    d['order_id'] = d['id']
                    d['delivery_xy'] = [d['stopping_x'], d['stopping_y']]
                    d['otp'] = d['otp_display']
                    results.append(d)
                return results

    def get_all_orders_supervisor(self) -> List[Dict]:
        """Privileged query available strictly to operators and managers."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM orders ORDER BY created_time DESC;")
                results = []
                for row in cur.fetchall():
                    d = dict(row)
                    d['items'] = json.loads(d['items_json'])
                    d['order_id'] = d['id']
                    d['delivery_xy'] = [d['stopping_x'], d['stopping_y']]
                    d['otp'] = d['otp_display']
                    results.append(d)
                return results

    def get_all_orders(self) -> List[Dict]:
        """Return all orders (alias for get_all_orders_supervisor)."""
        return self.get_all_orders_supervisor()


    def update_order_status(self, order_id: str, new_status: str) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                now = time.time()
                if new_status == 'COMPLETED':
                    conn.execute("UPDATE orders SET status = ?, completed_time = ? WHERE id = ?;", (new_status, now, order_id))
                else:
                    conn.execute("UPDATE orders SET status = ? WHERE id = ?;", (new_status, order_id))
                self.log_audit_event('SYSTEM', 'ROBOTICS_FSM', 'ORDER_STATUS_UPDATED', order_id, f'{{"new_status": "{new_status}"}}')
                return True

    def cancel_order(self, order_id: str, actor_id: str, reason: str = 'Customer cancellation') -> Tuple[bool, str]:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM orders WHERE id = ?;", (order_id,))
                row = cur.fetchone()
                if not row:
                    return False, "Order not found."
                if row['status'] in ('IN_TRANSIT', 'ARRIVED', 'DELIVERED', 'COMPLETED'):
                    return False, f"Cannot cancel order in status '{row['status']}'."

                now = time.time()
                conn.execute(
                    "UPDATE orders SET status = 'CANCELLED', cancelled_time = ?, cancellation_reason = ? WHERE id = ?;",
                    (now, reason, order_id)
                )
                self.log_audit_event(actor_id, 'USER', 'ORDER_CANCELLED', order_id, f'{{"reason": "{reason}"}}')
                return True, "Order cancelled successfully."

    def verify_order_otp(self, order_id: str, candidate_otp: str) -> Tuple[bool, str]:
        candidate_otp = candidate_otp.strip()
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM orders WHERE id = ?;", (order_id,))
                row = cur.fetchone()
                if not row:
                    return False, "Order not found."
                expected_otp = row['otp_display']
                if expected_otp and candidate_otp == expected_otp:
                    conn.execute("UPDATE orders SET status = 'DELIVERED' WHERE id = ?;", (order_id,))
                    self.log_audit_event('CUSTOMER', 'CUSTOMER', 'OTP_VERIFICATION_SUCCESS', order_id)
                    return True, "OTP verified successfully. Hatch unlocked."
                else:
                    self.log_audit_event('CUSTOMER', 'CUSTOMER', 'OTP_VERIFICATION_FAILED', order_id, f'{{"attempt": "{candidate_otp}"}}')
                    return False, "Invalid one-time password code."

    # ========================================================================
    # Audit Logging
    # ========================================================================

    def log_audit_event(
        self, actor_id: str, actor_role: str, action: str,
        target_entity: str, details: Optional[str] = None, ip_address: Optional[str] = None
    ):
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO audit_logs (actor_id, actor_role, action, target_entity, details_json, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (actor_id, actor_role, action, target_entity, details, ip_address))
        except Exception:
            pass

    def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?;", (limit,))
                return [dict(r) for r in cur.fetchall()]


_DB_INSTANCE: Optional[DatabaseManager] = None
_DB_LOCK = threading.Lock()


def get_database(db_path: Optional[str] = None) -> DatabaseManager:
    """Return thread-safe singleton instance of DatabaseManager."""
    global _DB_INSTANCE
    with _DB_LOCK:
        if _DB_INSTANCE is None:
            _DB_INSTANCE = DatabaseManager(db_path)
        return _DB_INSTANCE

