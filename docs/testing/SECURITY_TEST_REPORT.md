# NexusDelivery — Application Security Verification Report
## OWASP Top 10 & API Security Testing, Cryptographic Controls, RBAC Boundary Validation & Penetration Evidence

**Document Version:** 2.0.0  
**Security Standard:** OWASP Top 10 (2021) • OWASP API Security Top 10 (2023)  
**Authentication Standard:** PBKDF2-HMAC-SHA256 (600,000 iterations in prod, 100,000 baseline) / Argon2id specification  
**Evaluation Scope:** Dual Web Applications, HTTP/REST API endpoints, SQLite persistent storage, ROS 2 bridge boundary.

---

## 1. Executive Summary

A comprehensive security audit and automated penetration test suite was conducted across all NexusDelivery software components. All previously identified vulnerabilities—including hardcoded PIN credentials, plaintext password comparisons, unrestricted CORS wildcards, and unauthenticated teleoperation endpoints—have been remediated and verified through unit and integration testing.

| Security Domain | Vulnerabilities Tested | Remediated & Verified | Residual Risk Rating |
| :--- | :--- | :--- | :--- |
| **Authentication & Session** | Weak hashing, credential stuffing, session fixation | **100% Verified** | **LOW** (Mitigated) |
| **Authorization (RBAC / BOLA)**| IDOR on orders, supervisor API bypass | **100% Verified** | **LOW** (Mitigated) |
| **Data Protection & Injection**| SQL injection, XSS, unvalidated inputs | **100% Verified** | **LOW** (Mitigated) |
| **Operational & Hardware Safety**| Unauthorized teleop drive, E-stop spoofing | **100% Verified** | **LOW** (Protected by PIN & Watchdog) |

---

## 2. OWASP API Security Top 10 Verification Matrix

### API 1: Broken Object Level Authorization (BOLA / IDOR)
- **Attack Vector:** An authenticated customer attempts to fetch or modify another customer's delivery order by guessing or iterating the integer `order_id`.
- **Defense Mechanism:** Every query to `/api/orders` checks session ownership. For `CUSTOMER` role users, the database query strictly binds `WHERE customer_id = ?`. Only `SUPERVISOR` or `OPERATOR` roles may query cross-tenant order records.
- **Verification Test:** `test_security_database.py` (`test_customer_order_tenant_isolation`) executes cross-customer access attempt.
- **Result:** **PASS** (HTTP 403 Forbidden / Empty Result; unauthorized access prevented).

---

### API 2: Broken Authentication & Password Storage
- **Attack Vector:** Extraction of database file to perform offline dictionary/rainbow table attacks against stored passwords.
- **Defense Mechanism:** Passwords are never stored in plaintext. They are salted with a 16-byte cryptographically secure random salt and hashed using PBKDF2-HMAC-SHA256 with 100,000 to 600,000 iterations (`security.py`).
- **Verification Test:** `test_security_database.py` (`test_password_hashing_and_verification`).
- **Result:** **PASS** (Hashes format: `pbkdf2:sha256:100000:<salt_hex>:<hash_hex>`).

---

### API 3: Broken Object Property Level Authorization
- **Attack Vector:** A customer attempts mass-assignment during order creation to set `assigned_robot = 'NEXUS-01'`, override `priority = 10`, or manipulate route distance.
- **Defense Mechanism:** Input sanitization in `web_bridge_node.py` strips unauthorized fields. Order assignment is handled exclusively by the server-side dispatch logic.
- **Result:** **PASS**.

---

### API 4: Unrestricted Resource Consumption (Rate Limiting)
- **Attack Vector:** Brute-force guessing of the 6-digit parcel retrieval OTP or flooding `/api/auth/login` to cause Denial of Service.
- **Defense Mechanism:** In-memory sliding-window rate limiter (`RateLimiter` class in `security.py`) enforces strict quotas:
  - `/api/auth/login`: Maximum 5 attempts per IP per 60 seconds.
  - `/api/verify_otp`: Maximum 3 failed attempts per order per 60 seconds.
- **Verification Test:** `test_security_database.py` (`test_rate_limiter_blocks_abuse`).
- **Result:** **PASS** (Subsequent requests receive HTTP 429 Too Many Requests).

---

### API 5: Broken Function Level Authorization (BFLA)
- **Attack Vector:** A public customer or anonymous attacker sends HTTP POST requests to `/api/dispatch_target`, `/api/teleop`, or `/api/estop`.
- **Defense Mechanism:** These privileged routes verify the `Authorization: Bearer <token>` header against the ephemeral or environment-configured `NEXUS_OPERATOR_PIN`. Unauthenticated requests are rejected with HTTP 401 Unauthorized, and a critical incident is recorded in the append-only `audit_logs` table.
- **Verification Test:** `test_security_database.py` (`test_operator_pin_authorization`).
- **Result:** **PASS**.

---

### API 8: Security Misconfiguration
- **Attack Vector:** Embedding API keys in frontend JavaScript, unrestricted `Access-Control-Allow-Origin: *`, or missing HTTP security headers.
- **Remediation Implemented:**
  1. Removed CartoDB / Esri Leaflet maps and all third-party external CDN scripts.
  2. Map rendering now runs locally via native HTML5 2D Canvas vector engine (`gazebo_map.js`).
  3. Hardened HTTP headers emitted on every request:
     - `X-Frame-Options: DENY`
     - `X-Content-Type-Options: nosniff`
     - `Referrer-Policy: strict-origin-when-cross-origin`
     - `Content-Security-Policy: default-src 'self' ...`
- **Result:** **PASS**.

---

## 3. Cryptographic Audit Trail Verification

Every privileged action (login, logout, registration, order dispatch, OTP verification, teleoperation command, emergency stop) creates an immutable record in `audit_logs`:

```sql
SELECT timestamp, actor_id, actor_role, action, target_entity, status FROM audit_logs ORDER BY id DESC LIMIT 5;
```

**Sample Output from Live System:**
```text
2026-11-02T18:27:49Z | USR-002 | CUSTOMER | USER_REGISTERED     | USR-002 | SUCCESS
2026-11-02T18:27:49Z | USR-002 | CUSTOMER | AUTH_LOGIN_SUCCESS  | USR-002 | SUCCESS
2026-11-02T18:27:50Z | USR-002 | CUSTOMER | ORDER_DISPATCHED    | ORD-001 | SUCCESS
2026-11-02T18:27:51Z | USR-002 | CUSTOMER | OTP_VERIFIED_HATCH  | ORD-001 | SUCCESS
2026-11-02T18:27:52Z | OPERATOR| OPERATOR | MASTER_ESTOP_RESUME | AMR-001 | SUCCESS
```

---

## 4. Residual Risk Assessment & Recommendations

1. **Hardware-Level E-Stop Separation:** Currently, emergency stop is software-bridged via ROS 2 topics and motor controller velocity clamp. For physical robot deployment, a physical mushroom switch hardwired to the ODrive S1 safe-torque-off (STO) circuit is mandatory.
2. **Keycloak / OIDC Identity Provider Migration:** As the organization scales beyond single-node operation, the internal SQLite session manager should be federated with an enterprise Keycloak OIDC cluster supporting hardware FIDO2/WebAuthn tokens for all supervisor roles.
