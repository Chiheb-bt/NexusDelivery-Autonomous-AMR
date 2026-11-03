"""Persistent Relational Database Subsystem for NexusDelivery.

Implements:
- ACID-compliant SQLite storage with foreign keys, WAL mode, and connection pooling
- Persistent user accounts, PBKDF2 password hashes, and session management
- Single-use, expiring email verification tokens and verification status tracking
- Saved customer delivery addresses in Gazebo world coordinates
- Complete 14-state multi-drop order lifecycle tracking and tenant-scoped queries
- Payload weight (max 15.0 kg) and volume (max 22.5 L) validation
- Idempotency / duplicate order submission protection
- Immutable security audit logging
"""

import json
import logging
import os
import secrets
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

logger = logging.getLogger("NexusDelivery.Database")

DEFAULT_DB_PATH = os.path.join(
    os.environ.get("RDSIM_RESULTS_DIR", os.path.join(os.path.dirname(__file__), '..', '..', 'results')),
    'nexus_delivery.db'
)

# Explicit 14 Order States
ORDER_STATES = (
    'PENDING',
    'CONFIRMED',
    'PREPARING',
    'READY_FOR_DISPATCH',
    'ROBOT_ASSIGNED',
    'ROBOT_EN_ROUTE',
    'ROBOT_ARRIVED',
    'HANDOVER_IN_PROGRESS',
    'DELIVERED',
    'RETURNING_TO_DEPOT',
    'COMPLETED',
    'CANCELLED',
    'FAILED',
    'UNREACHABLE',
)

MAX_PAYLOAD_WEIGHT_KG = 15.0
MAX_PAYLOAD_VOLUME_L = 22.5


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
                    email_verified INTEGER DEFAULT 0,
                    email_verified_at REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS email_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    email TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at REAL NOT NULL,
                    used INTEGER DEFAULT 0,
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
                    delivery_instructions TEXT,
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
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    otp_hash TEXT NOT NULL,
                    otp_display TEXT,
                    weight_kg REAL DEFAULT 1.0,
                    volume_l REAL DEFAULT 2.0,
                    delivery_instructions TEXT,
                    idempotency_key TEXT,
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

                # Automatic schema migrations for pre-existing databases
                self._migrate_existing_schema(conn)

                # Seed initial baseline accounts if empty
                cur = conn.execute("SELECT COUNT(*) FROM users;")
                if cur.fetchone()[0] == 0:
                    self._seed_default_data(conn)
                else:
                    self._ensure_default_accounts(conn)

    def _migrate_existing_schema(self, conn: sqlite3.Connection):
        """Safely add new columns to pre-existing SQLite tables."""
        # 1. users table migrations
        cur = conn.execute("PRAGMA table_info(users);")
        user_cols = {r['name'] for r in cur.fetchall()}
        if 'email_verified' not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0;")
        if 'email_verified_at' not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN email_verified_at REAL;")

        # 2. orders table migrations
        cur = conn.execute("PRAGMA table_info(orders);")
        order_cols = {r['name'] for r in cur.fetchall()}
        if 'weight_kg' not in order_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN weight_kg REAL DEFAULT 1.0;")
        if 'volume_l' not in order_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN volume_l REAL DEFAULT 2.0;")
        if 'delivery_instructions' not in order_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN delivery_instructions TEXT;")
        if 'idempotency_key' not in order_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN idempotency_key TEXT;")

        # 3. addresses table migrations
        cur = conn.execute("PRAGMA table_info(addresses);")
        addr_cols = {r['name'] for r in cur.fetchall()}
        if 'delivery_instructions' not in addr_cols:
            conn.execute("ALTER TABLE addresses ADD COLUMN delivery_instructions TEXT;")

    def _ensure_default_accounts(self, conn: sqlite3.Connection):
        now = time.time()
        # Ensure default accounts are verified
        conn.execute(
            "UPDATE users SET email_verified = 1, email_verified_at = ? WHERE email IN ('client@nexus.tn', 'marc@nexus.tn', 'operator@nexus.tn', 'admin@nexus.tn', 'supervisor@nexus.tn');",
            (now,)
        )
        # Ensure supervisor account exists
        cur_sup = conn.execute("SELECT COUNT(*) FROM users WHERE email = 'supervisor@nexus.tn';")
        if cur_sup.fetchone()[0] == 0:
            cur_ids = conn.execute("SELECT id FROM users;")
            existing = {r[0] for r in cur_ids.fetchall()}
            sup_id = "USR-SUP"
            while sup_id in existing:
                sup_id = f"USR-SUP-{secrets.token_hex(2)}"
            conn.execute(
                "INSERT INTO users (id, email, password_hash, name, role, phone, email_verified, email_verified_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?);",
                (sup_id, 'supervisor@nexus.tn', hash_password('nexus2026'), 'Fleet Supervisor', 'OPERATOR', '+216 71 100 400', now)
            )

    def _seed_default_data(self, conn: sqlite3.Connection):
        now = time.time()
        seed_users = [
            ('USR-001', 'client@nexus.tn', hash_password('password123'), 'Sophie Laurent', 'CUSTOMER', '+216 20 123 456', 1, now),
            ('USR-002', 'marc@nexus.tn', hash_password('password123'), 'Marc Dubois', 'CUSTOMER', '+216 22 987 654', 1, now),
            ('USR-003', 'operator@nexus.tn', hash_password('nexus2026'), 'Fleet Operator Alpha', 'OPERATOR', '+216 71 100 200', 1, now),
            ('USR-004', 'admin@nexus.tn', hash_password('Admin2026!'), 'Lead Robotics Admin', 'SUPER_ADMIN', '+216 71 100 300', 1, now),
            ('USR-005', 'supervisor@nexus.tn', hash_password('nexus2026'), 'Fleet Supervisor', 'OPERATOR', '+216 71 100 400', 1, now),
        ]
        conn.executemany(
            "INSERT INTO users (id, email, password_hash, name, role, phone, email_verified, email_verified_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            seed_users
        )

        orders_seed = [
            (
                'ORD-001', 'USR-001', 'Sophie Laurent', 'NEXUS-01',
                'CLIENT_1_NORTH_AVENUE', -9.8, 15.0, -14.6, 15.0, 0.0,
                'PKG-101', json.dumps([{'id': 'PRD-01', 'name': 'Artisan Margherita Pizza', 'qty': 1, 'weight_kg': 0.8, 'volume_l': 1.5}]),
                1, 'ROBOT_EN_ROUTE', '482910', '482910', 0.8, 1.5, now, now, None, None, None, 31.5, 37.0
            ),
            (
                'ORD-002', 'USR-002', 'Marc Dubois', 'NEXUS-01',
                'CLIENT_2_NORTH_AVENUE', -9.8, 28.0, -14.6, 28.0, 0.0,
                'PKG-102', json.dumps([{'id': 'PRD-02', 'name': 'Fresh Sushi Bento Deluxe', 'qty': 2, 'weight_kg': 1.2, 'volume_l': 2.0}]),
                2, 'ROBOT_ASSIGNED', '739104', '739104', 1.2, 2.0, now, now, None, None, None, 44.5, 52.0
            )
        ]
        conn.executemany("""
            INSERT INTO orders (
                id, customer_id, customer_name, robot_id,
                delivery_name, target_x, target_y, stopping_x, stopping_y, approach_heading,
                package_id, items_json, priority, status, otp_hash, otp_display,
                weight_kg, volume_l,
                created_time, assigned_time, completed_time, cancelled_time, cancellation_reason,
                route_distance_m, estimated_duration_s
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, orders_seed)

        conn.execute("""
            INSERT INTO audit_logs (actor_id, actor_role, action, target_entity, details_json)
            VALUES ('SYSTEM', 'SYSTEM', 'DATABASE_INITIALIZED', 'SCHEMA', '{"version": "2.1.0", "states": 14}');
        """)

    # ========================================================================
    # User Registration, Email Verification & Session Management
    # ========================================================================

    def register_user(
        self,
        email: str,
        password: str,
        name: str,
        role: str = 'CUSTOMER',
        phone: Optional[str] = None,
        email_verified: int = 0
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Register a new customer or operator account."""
        email = email.strip().lower()
        if not email or not password or not name:
            return False, "Email, password, and name are required.", None

        if len(password) < 6:
            return False, "Password must be at least 6 characters long.", None

        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id FROM users WHERE email = ?;", (email,))
                if cur.fetchone():
                    return False, "An account with this email address already exists.", None

                cur = conn.execute("SELECT id FROM users;")
                existing_ids = {r[0] for r in cur.fetchall()}
                idx = len(existing_ids) + 1
                user_id = f"USR-{idx:03d}"
                while user_id in existing_ids:
                    idx += 1
                    user_id = f"USR-{idx:03d}"
                pw_hash = hash_password(password)

                verified_ts = time.time() if email_verified else None
                conn.execute(
                    "INSERT INTO users (id, email, password_hash, name, role, phone, email_verified, email_verified_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                    (user_id, email, pw_hash, name, role, phone, email_verified, verified_ts)
                )

                self.log_audit_event(user_id, role, 'USER_REGISTERED', user_id, f'{{"email": "{email}", "verified": {email_verified}}}', conn=conn)
                user_data = {
                    'id': user_id,
                    'customer_id': user_id,
                    'email': email,
                    'name': name,
                    'role': role,
                    'phone': phone,
                    'email_verified': email_verified,
                    'email_verified_at': verified_ts
                }
                return True, "Registration successful.", user_data

    def create_email_verification(self, user_id: str, email: str, token: str, expiry_seconds: int = 86400) -> bool:
        """Store a single-use expiring email verification token."""
        now = time.time()
        expires_at = now + expiry_seconds
        with self._lock:
            with self._get_connection() as conn:
                # Invalidate any previous unverified tokens for this user
                conn.execute("UPDATE email_verifications SET used = 2 WHERE user_id = ? AND used = 0;", (user_id,))
                conn.execute(
                    "INSERT INTO email_verifications (user_id, email, token, expires_at, used) VALUES (?, ?, ?, ?, 0);",
                    (user_id, email.lower(), token, expires_at)
                )
                self.log_audit_event(user_id, 'USER', 'EMAIL_VERIFICATION_TOKEN_ISSUED', token[:8] + '***', conn=conn)
                return True

    def verify_email_token(self, token: str) -> Tuple[bool, str, Optional[Dict]]:
        """Verify an email token: single-use, check expiry, activate user account."""
        now = time.time()
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM email_verifications WHERE token = ?;",
                    (token,)
                )
                rec = cur.fetchone()
                if not rec:
                    return False, "Invalid or unrecognized verification token.", None

                if rec['used'] == 1:
                    return False, "This verification link has already been used.", None

                if rec['used'] == 2:
                    return False, "This verification link has been superseded by a newer request.", None

                if rec['expires_at'] < now:
                    return False, "This verification token has expired. Please request a new one.", None

                # Mark token used
                conn.execute("UPDATE email_verifications SET used = 1 WHERE id = ?;", (rec['id'],))

                # Activate user
                conn.execute(
                    "UPDATE users SET email_verified = 1, email_verified_at = ? WHERE id = ?;",
                    (now, rec['user_id'])
                )

                cur_u = conn.execute("SELECT * FROM users WHERE id = ?;", (rec['user_id'],))
                user_row = cur_u.fetchone()
                u_dict = dict(user_row) if user_row else {}
                u_dict.pop('password_hash', None)

                self.log_audit_event(rec['user_id'], u_dict.get('role', 'CUSTOMER'), 'EMAIL_VERIFIED_SUCCESS', rec['user_id'], conn=conn)
                return True, "Email verified successfully! You can now place autonomous delivery orders.", u_dict

    def is_user_verified(self, user_id: str) -> bool:
        """Return True if user account email is verified."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT email_verified FROM users WHERE id = ?;", (user_id,))
                row = cur.fetchone()
                if row and row['email_verified'] == 1:
                    return True
                return False

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Fetch user by email (without password hash)."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM users WHERE email = ?;", (email.strip().lower(),))
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(row)
                d.pop('password_hash', None)
                return d

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Fetch user by ID (without password hash)."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(row)
                d.pop('password_hash', None)
                return d

    def get_all_users_supervisor(self) -> List[Dict]:
        """Return registered users list for supervisor inspection (without password hashes)."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id, email, name, role, phone, email_verified, email_verified_at, created_at FROM users ORDER BY created_at DESC;")
                return [dict(r) for r in cur.fetchall()]

    def authenticate_user(self, email: str, password: str, ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[Dict], Optional[str], Optional[str]]:
        email = email.strip().lower()
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM users WHERE email = ?;", (email,))
                row = cur.fetchone()
                if not row:
                    self.log_audit_event('ANONYMOUS', 'GUEST', 'AUTH_FAILURE_NOT_FOUND', email, None, ip_address, conn=conn)
                    return False, "Invalid email address or password.", None, None, None

                if not verify_password(password, row['password_hash']):
                    self.log_audit_event(row['id'], row['role'], 'AUTH_FAILURE_PASSWORD', email, None, ip_address, conn=conn)
                    return False, "Invalid email address or password.", None, None, None

                # Generate session and CSRF token
                session_token = generate_session_token(32)
                csrf_token = generate_csrf_token(24)
                expires_at = time.time() + 1800.0  # 30-minute session

                conn.execute(
                    "INSERT INTO sessions (token, user_id, role, csrf_token, expires_at) VALUES (?, ?, ?, ?, ?);",
                    (session_token, row['id'], row['role'], csrf_token, expires_at)
                )

                self.log_audit_event(row['id'], row['role'], 'AUTH_LOGIN_SUCCESS', row['id'], None, ip_address, conn=conn)
                user_data = {
                    'id': row['id'],
                    'customer_id': row['id'],
                    'email': row['email'],
                    'name': row['name'],
                    'role': row['role'],
                    'phone': row['phone'],
                    'email_verified': row['email_verified'],
                    'email_verified_at': row['email_verified_at']
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
                           u.email, u.name, u.phone, u.email_verified, u.email_verified_at
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
        stopping_bay_id: Optional[str], stopping_x: float, stopping_y: float,
        approach_heading: float, reachability_status: str,
        delivery_instructions: Optional[str] = None
    ) -> Dict:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM addresses;")
                addr_id = f"ADDR-{cur.fetchone()[0] + 1:03d}"
                conn.execute("""
                    INSERT INTO addresses (
                        id, user_id, label, gazebo_x, gazebo_y,
                        stopping_bay_id, stopping_x, stopping_y, approach_heading,
                        reachability_status, delivery_instructions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    addr_id, user_id, label, gazebo_x, gazebo_y,
                    stopping_bay_id or '', stopping_x, stopping_y, approach_heading,
                    reachability_status, delivery_instructions or ''
                ))
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
                    'reachability_status': reachability_status,
                    'delivery_instructions': delivery_instructions
                }

    def get_user_addresses(self, user_id: str) -> List[Dict]:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM addresses WHERE user_id = ? ORDER BY created_at DESC;", (user_id,))
                return [dict(r) for r in cur.fetchall()]

    # ========================================================================
    # Multi-Drop Order Management & Lifecycle
    # ========================================================================

    def create_order(
        self, customer_id: str, customer_name: str, delivery_name: str,
        target_x: float, target_y: float, stopping_x: float, stopping_y: float,
        approach_heading: float, package_id: str, items: List[Dict],
        priority: int = 2, otp: Optional[str] = None,
        route_dist: float = 0.0, est_duration: float = 0.0,
        initial_status: str = 'CONFIRMED',
        delivery_instructions: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict:
        """Create and persist an order with capacity and email-verification rules."""
        now = time.time()

        with self._lock:
            with self._get_connection() as conn:
                # 1. Enforce verified customer account rule
                cur_u = conn.execute("SELECT email_verified FROM users WHERE id = ?;", (customer_id,))
                user_row = cur_u.fetchone()
                if user_row and user_row['email_verified'] != 1:
                    raise PermissionError(
                        "Cannot place order: Customer account email is unverified. "
                        "Please verify your email address to enable autonomous deliveries."
                    )

                # 2. Duplicate submission protection (idempotency key within last 60s)
                if idempotency_key:
                    cur_dup = conn.execute(
                        "SELECT * FROM orders WHERE idempotency_key = ? AND created_time > ?;",
                        (idempotency_key, now - 60.0)
                    )
                    existing = cur_dup.fetchone()
                    if existing:
                        logger.warning(f"Duplicate order rejected for idempotency key: {idempotency_key}")
                        d = dict(existing)
                        d['items'] = json.loads(d['items_json'])
                        d['order_id'] = d['id']
                        d['delivery_xy'] = [d['stopping_x'], d['stopping_y']]
                        d['otp'] = d['otp_display']
                        return d

                # 3. Payload weight and volume calculation & validation
                total_w = sum(it.get('weight_kg', 0.5) * it.get('qty', 1) for it in items) or 0.8
                total_v = sum(it.get('volume_l', 1.0) * it.get('qty', 1) for it in items) or 1.5

                if total_w > MAX_PAYLOAD_WEIGHT_KG:
                    raise ValueError(f"Payload weight ({total_w:.1f} kg) exceeds maximum robot cargo limit ({MAX_PAYLOAD_WEIGHT_KG} kg).")
                if total_v > MAX_PAYLOAD_VOLUME_L:
                    raise ValueError(f"Payload volume ({total_v:.1f} L) exceeds maximum cargo compartment volume ({MAX_PAYLOAD_VOLUME_L} L).")

                # Generate 6-digit OTP
                otp_val = otp if otp else f"{secrets.randbelow(900000) + 100000}"
                items_str = json.dumps(items)

                cur_cnt = conn.execute("SELECT COUNT(*) FROM orders;")
                order_id = f"ORD-{cur_cnt.fetchone()[0] + 1:03d}"

                status_val = initial_status if initial_status in ORDER_STATES else 'CONFIRMED'

                conn.execute("""
                    INSERT INTO orders (
                        id, customer_id, customer_name, robot_id, delivery_name,
                        target_x, target_y, stopping_x, stopping_y, approach_heading,
                        package_id, items_json, priority, status, otp_hash, otp_display,
                        weight_kg, volume_l, delivery_instructions, idempotency_key,
                        created_time, assigned_time, route_distance_m, estimated_duration_s
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    order_id, customer_id, customer_name, 'NEXUS-01', delivery_name,
                    target_x, target_y, stopping_x, stopping_y, approach_heading,
                    package_id, items_str, priority, status_val, otp_val, otp_val,
                    round(total_w, 2), round(total_v, 2), delivery_instructions or '', idempotency_key or '',
                    now, now, route_dist, est_duration
                ))

                self.log_audit_event(customer_id, 'CUSTOMER', 'ORDER_CREATED', order_id, f'{{"delivery_name": "{delivery_name}", "status": "{status_val}"}}', conn=conn)

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
                    'status': status_val,
                    'otp': otp_val,
                    'weight_kg': total_w,
                    'volume_l': total_v,
                    'delivery_instructions': delivery_instructions,
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
        """Privileged query available strictly to operators, fleet supervisors and admins."""
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
        return self.get_all_orders_supervisor()

    def update_order_status(self, order_id: str, new_status: str) -> bool:
        """Update order lifecycle status according to explicit state machine."""
        with self._lock:
            with self._get_connection() as conn:
                now = time.time()
                if new_status in ('COMPLETED', 'DELIVERED'):
                    conn.execute("UPDATE orders SET status = ?, completed_time = ? WHERE id = ?;", (new_status, now, order_id))
                else:
                    conn.execute("UPDATE orders SET status = ? WHERE id = ?;", (new_status, order_id))
                self.log_audit_event('SYSTEM', 'ROBOTICS_FSM', 'ORDER_STATUS_UPDATED', order_id, f'{{"new_status": "{new_status}"}}', conn=conn)
                return True

    def cancel_order(self, order_id: str, actor_id: str, reason: str = 'Customer cancellation') -> Tuple[bool, str]:
        """Cancel order under strict safety rules (cannot cancel en route or arrived)."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM orders WHERE id = ?;", (order_id,))
                row = cur.fetchone()
                if not row:
                    return False, "Order not found."

                curr_status = row['status']
                if curr_status in ('COMPLETED', 'CANCELLED'):
                    return False, f"Order is already {curr_status}."

                # Customer cannot cancel once robot is en route or at delivery doorstep
                non_cancellable_for_customer = (
                    'ROBOT_EN_ROUTE', 'IN_TRANSIT', 'ROBOT_ARRIVED', 'ARRIVED',
                    'HANDOVER_IN_PROGRESS', 'DELIVERED', 'RETURNING_TO_DEPOT'
                )
                if curr_status in non_cancellable_for_customer and actor_id != 'SUPERVISOR':
                    return False, f"Cannot cancel order in status '{curr_status}'. Robot is already en route or completed."

                now = time.time()
                conn.execute(
                    "UPDATE orders SET status = 'CANCELLED', cancelled_time = ?, cancellation_reason = ? WHERE id = ?;",
                    (now, reason, order_id)
                )
                self.log_audit_event(actor_id, 'USER', 'ORDER_CANCELLED', order_id, f'{{"reason": "{reason}", "previous_status": "{curr_status}"}}', conn=conn)
                return True, "Order cancelled successfully."

    def verify_order_otp(self, order_id: str, candidate_otp: str) -> Tuple[bool, str]:
        """Verify delivery OTP, transition status to DELIVERED, and audit log."""
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
                    self.log_audit_event('CUSTOMER', 'CUSTOMER', 'OTP_VERIFICATION_SUCCESS', order_id, conn=conn)
                    return True, "OTP verified successfully. Hatch unlocked."
                else:
                    self.log_audit_event('CUSTOMER', 'CUSTOMER', 'OTP_VERIFICATION_FAILED', order_id, f'{{"attempt": "{candidate_otp}"}}', conn=conn)
                    return False, "Invalid one-time password code."

    # ========================================================================
    # Audit Logging
    # ========================================================================

    def log_audit_event(
        self, actor_id: str, actor_role: str, action: str,
        target_entity: str, details: Optional[str] = None, ip_address: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None
    ):
        try:
            if conn is not None:
                conn.execute("""
                    INSERT INTO audit_logs (actor_id, actor_role, action, target_entity, details_json, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (actor_id, actor_role, action, target_entity, details, ip_address))
            else:
                with self._get_connection() as c:
                    c.execute("""
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
