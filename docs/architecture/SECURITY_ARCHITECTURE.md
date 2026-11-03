# NexusDelivery — Security Architecture & Access Control Specification

**Document Version:** 2.0.0  
**Date:** November 2026  
**Status:** Approved Security Architecture  
**Target Standard:** OWASP Top 10 (2021), ISO 27001, SOC-2 Type II Control Mapping

---

## 1. Identity & Access Management (IAM)

### 1.1 Password Hashing Specification
All passwords stored in the persistent database are hashed using **Argon2id** (the winner of the Password Hashing Competition, RFC 9106) with industry-standard parameters:
- **Algorithm:** Argon2id
- **Memory Cost ($m$):** 65,536 KiB (64 MiB)
- **Time Cost ($t$):** 3 iterations
- **Parallelism ($p$):** 4 threads
- **Salt Length:** 16 bytes cryptographically random (`os.urandom(16)`)
- **Key Length:** 32 bytes

*Fallback Implementation for lightweight environments:* PBKDF2-HMAC-SHA256 with 600,000 iterations and 16-byte random salt.

### 1.2 Session Management & Token Architecture
- **Session Mechanism:** Cryptographically signed server-side session IDs or short-lived JSON Web Tokens (JWT) using HMAC-SHA256 (`HS256`) with a 256-bit server secret key.
- **Cookie Security Attributes:**
  - `HttpOnly`: Strictly prevents client-side JavaScript access via `document.cookie` (mitigating XSS session theft).
  - `SameSite=Strict`: Prevents cookies from being transmitted in cross-site requests (mitigating CSRF).
  - `Secure`: Transmitted exclusively over encrypted HTTPS connections in production.
- **Token Lifespans:**
  - Access Token / Session: 30 minutes.
  - Refresh Token: 7 days, stored hashed in database with automatic rotation and immediate revocation upon reuse detection.

### 1.3 Multi-Factor Authentication (MFA)
- Mandatory for privileged roles (`OPERATOR`, `FLEET_MANAGER`, `SUPER_ADMIN`).
- Implements Time-Based One-Time Password (TOTP) algorithm per RFC 6238 using a 160-bit shared secret and 30-second time-step.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Permission / Action | `CUSTOMER` | `READ_ONLY` | `MAINTENANCE` | `OPERATOR` | `FLEET_MANAGER` | `SUPER_ADMIN` |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Browse Catalog & Menu** | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| **Pick Gazebo Doorstep** | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| **Create Delivery Order** | ALLOW | DENY | DENY | ALLOW | ALLOW | ALLOW |
| **View Own Orders** | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| **Cancel Own Order** | ALLOW | DENY | DENY | ALLOW | ALLOW | ALLOW |
| **View All Fleet Orders** | **DENY (BOLA Guard)** | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| **View RealSense Cam Stream**| DENY | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| **View Fleet Telemetry & BMS**| DENY | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| **Authorize Waypoint Dispatch**| DENY | DENY | DENY | ALLOW | ALLOW | ALLOW |
| **Manual Teleoperation (v, w)**| **DENY** | **DENY** | ALLOW (Bench) | ALLOW | ALLOW | ALLOW |
| **Master Emergency Stop (E-Stop)**| DENY | DENY | ALLOW | ALLOW | ALLOW | ALLOW |
| **Reset E-Stop Interlock** | DENY | DENY | DENY | ALLOW | ALLOW | ALLOW |
| **Manage Users & RBAC** | DENY | DENY | DENY | DENY | DENY | ALLOW |
| **Export Audit Logs** | DENY | DENY | DENY | DENY | ALLOW | ALLOW |

---

## 3. Defense Against OWASP Top 10 Vulnerabilities

### 3.1 Broken Object-Level Authorization (BOLA / IDOR) Defense
- **Vulnerability:** A customer querying `/api/orders` receiving data belonging to another customer.
- **Architectural Control:** Every SQL query executed on customer endpoints enforces tenant isolation:
  ```sql
  SELECT * FROM orders WHERE customer_id = :authenticated_user_id AND id = :requested_order_id;
  ```
- Any attempt by a `CUSTOMER` role to access an order without matching `customer_id` produces an immediate `HTTP 403 Forbidden` and logs a security violation event.

### 3.2 Actuator Injection & Teleoperation Interlocks
- **Vulnerability:** Unauthenticated HTTP client driving the physical robot via `/api/teleop`.
- **Architectural Control:**
  1. The teleoperation endpoint strictly enforces the `robot:teleop` permission and requires an active authenticated session.
  2. The robot's onboard `safety_supervisor.py` enforces speed ceilings ($v \le 1.3\text{ m/s}$) and automatic emergency braking when obstacles are within $0.8\text{ m}$.
  3. Every manual intervention command triggers a signed audit log entry containing operator ID, joystick vector, and timestamp.
  4. If operator heartbeat is lost for $> 500\text{ ms}$, the driver automatically zeros velocity (`cmd_vel = 0.0`).

### 3.3 Rate Limiting & DoS Protection
- Leaky bucket algorithm implemented at API gateway / reverse proxy:
  - Login endpoint (`/api/auth/login`): 5 requests per minute per IP.
  - Order creation (`/api/orders`): 10 requests per minute per authenticated user.
  - Telemetry polling: 10 requests per second per client.

---

## 4. Cryptographic Delivery Handover (OTP Specification)

The physical cargo compartment hatch is secured by a dynamic one-time password (OTP) workflow:
1. **Generation:** When the robot arrives at the customer's delivery bay, `order_manager.py` generates a 6-digit numeric OTP using HMAC-SHA256:
   $$\text{OTP} = \text{HMAC-SHA256}(K_{\text{secret}}, \text{order\_id} \parallel \text{timestamp}) \pmod{10^6}$$
2. **Storage:** Only the cryptographic SHA-256 hash of the OTP is retained in the database; the plaintext code is delivered directly to the customer's authenticated tracking view.
3. **Lockout Policy:**
   - 3 consecutive incorrect OTP entries immediately lock the cargo latch for $300\text{ seconds}$ and dispatch a security alert to the supervisor cockpit.
   - Code validity expires after $180\text{ seconds}$ following confirmed robot arrival.

---

## 5. Audit Logging & Compliance Architecture

Every security-sensitive event is committed to an append-only relational table:

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    signature TEXT
);
```

**Logged Actions:**
- `AUTH_LOGIN_SUCCESS` / `AUTH_LOGIN_FAILURE`
- `ORDER_CREATED` / `ORDER_CANCELLED`
- `HATCH_UNLOCK_ATTEMPT` (Record of OTP match or failure)
- `OPERATOR_DISPATCH_OVERRIDE`
- `TELEOPERATION_ENGAGED` / `TELEOPERATION_RELEASED`
- `EMERGENCY_STOP_TRIGGERED` / `EMERGENCY_STOP_RESET`
