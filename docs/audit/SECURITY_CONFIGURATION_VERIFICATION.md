# NexusDelivery — Security Configuration & Threat Model Verification (Phase 6)

**Document ID:** DOC-ND-SEC-VERIF-005  
**Audit Date:** November 3, 2026  
**Auditing Team:** Application Security & Distributed Systems Engineering Team  
**Standards Evaluated:** OWASP Top 10 (2021), NIST SP 800-63B, Cyber-Physical Robotics Threat Modeling  

---

## 1. Executive Summary

This security audit inspects the identity, authentication, session lifecycle, authorization, and cryptographic safeguards of the NexusDelivery application stack. While significant improvements have been implemented (PBKDF2 password hashing, token-bucket rate limiting, CSRF tokens, and RBAC privilege separation), this audit identifies specific areas where test-convenience mechanisms must be hardened prior to commercial production deployment.

---

## 2. Password Hashing & Cryptographic Storage

### 2.1 Algorithm & Iteration Configuration
- **Hashing Function:** PBKDF2 with HMAC-SHA256 (`hashlib.pbkdf2_hmac`).
- **Salt Generation:** 16 bytes of cryptographically secure pseudo-random bytes (`secrets.token_bytes(16)`).
- **Format:** `pbkdf2:sha256:<iterations>$<salt_hex>$<hash_hex>`.
- **Iteration Count Analysis:**
  - **Environment Variable:** `PBKDF2_ITERATIONS` (default `100,000` rounds).
  - **Production Standard:** `600,000` rounds recommended by OWASP for compute-hardened production environments.
  - **Dynamic Verification:** In `security.py:verify_password()`, the iteration count is parsed directly from the stored hash prefix (`iterations = int(iterations)`), preventing legacy hashes from breaking if the global iteration count is scaled up in production.
- **Vulnerability / Finding (SEC-VULN-01):**  
  In `security.py:verify_password()` lines 65–66, a backward-compatibility fallback exists:
  ```python
  # Direct constant-time string comparison fallback for legacy plain test accounts
  return hmac.compare_digest(password, hashed_str)
  ```
  While safe against timing attacks via `hmac.compare_digest`, allowing plaintext matching if the stored hash is not formatted as PBKDF2 allows plaintext credentials in development databases.  
  **Remediation:** Enforce a strict migration policy in production: reject any stored password that does not begin with `pbkdf2:sha256:` and force a password reset.

---

## 3. Session & Token Management

### 3.1 Session Creation & Expiration
- **Token Generation:** 32-byte URL-safe high-entropy strings (`secrets.token_urlsafe(32)`, providing 256 bits of entropy).
- **CSRF Token:** 24-byte URL-safe token generated per authenticated session.
- **Session Lifetime:** 1800 seconds ($30\text{ minutes}$) hard expiration enforced via database query:
  ```sql
  SELECT s.token, s.user_id, s.role, s.csrf_token, s.expires_at FROM sessions s
  WHERE s.token = ? AND s.expires_at > ?;
  ```
- **Session Revocation:** Explicit logout endpoint (`POST /api/auth/logout`) deletes session records immediately from SQLite storage.

### 3.2 Hardcoded Static Test Bypass Tokens (SEC-VULN-02 — Critical Finding)
- **Inspection Finding:**  
  In `web_bridge_node.py` (lines 687, 751, 756), the code allows static string tokens:
  - `'OP-TOKEN-SUPERVISOR'`: Grants elevated supervisor access without database lookup.
  - `'CUST-TOKEN-SOPHIE'`: Grants default customer access without database lookup.
- **Risk Assessment:**  
  While introduced for unit test determinism and headless test suite stability, these static tokens constitute a backdoor if deployed to a public-facing production environment.
- **Remediation Requirement:**  
  Wrap all static token shortcuts inside an explicit environment check:
  ```python
  if os.environ.get("NEXUS_ENVIRONMENT") != "PRODUCTION":
      # Allow test tokens only in development/testing mode
  ```
  In production mode, require authentic database session resolution exclusively.

---

## 4. Role-Based Access Control (RBAC) & Privileged Endpoints

### 4.1 Role Hierarchy
Defined roles: `CUSTOMER`, `READ_ONLY`, `MAINTENANCE_ENGINEER`, `OPERATOR`, `FLEET_MANAGER`, `SUPER_ADMIN`.

| Endpoint Path | Method | Minimum Required Role | Unauthenticated Response | Customer Role Response |
|---|:---:|---|:---:|:---:|
| `/api/telemetry` | GET | `ANONYMOUS` (Public Telemetry) | HTTP 200 OK | HTTP 200 OK |
| `/api/products` | GET | `ANONYMOUS` (Public Catalog) | HTTP 200 OK | HTTP 200 OK |
| `/api/orders` | GET | `CUSTOMER` (Own orders) / `OPERATOR` (All) | HTTP 401 Unauthorized | HTTP 200 (Filtered) |
| `/api/audit_logs` | GET | `OPERATOR` / `SUPER_ADMIN` | HTTP 401 Unauthorized | HTTP 403 Forbidden |
| `/api/dispatch/decision_log`| GET | `ANONYMOUS` (Transparent audit) | HTTP 200 OK | HTTP 200 OK |
| `/api/cargo/lift` | POST | `CUSTOMER` (Handover) / `OPERATOR` | HTTP 401 Unauthorized | HTTP 200 (During OTP) |
| `/api/supervisor/estop` | POST | `OPERATOR` / `SUPER_ADMIN` | HTTP 401 Unauthorized | HTTP 403 Forbidden |
| `/api/teleop` | POST | `OPERATOR` / `SUPER_ADMIN` | HTTP 401 Unauthorized | HTTP 403 Forbidden |

---

## 5. Delivery OTP Handover Verification

### 5.1 One-Time Password Specification
- **Format:** 6 cryptographically generated numeric digits (`secrets.randbelow(10)`).
- **Entropy:** $10^6$ combinations ($1,000,000$ possibilities).
- **Storage:** Stored in database as a secure digest (`otp_hash`).
- **Timing Defense:** Verification evaluated via constant-time string matching.
- **Brute-Force Rate Limiting:**
  - Token-bucket rate limiting restricts OTP submission attempts to 5 per minute per IP address.
  - Exceeding limit locks the compartment and flags an audit event (`AUTH_FAILURE_PASSWORD`).
- **Single-Use Invalidation:** Upon successful validation, the order status transitions to `DELIVERED` and the OTP is cleared from memory.

---

## 6. Secret Management & Environment Hardening

| Secret / Config Parameter | Storage Mechanism | Default / Fallback Behavior | Production Hardening Mandate |
|---|---|---|---|
| `NEXUS_SECRET_KEY` | Environment variable | Ephemeral random 32-byte secret generated at startup | Must be mounted via Docker Secret or Kubernetes Secret. |
| `NEXUS_OPERATOR_PIN` | Environment variable | Ephemeral random token generated if unset | Must be injected via secure secret store. |
| `PBKDF2_ITERATIONS` | Environment variable | Defaults to `100,000` | Set `PBKDF2_ITERATIONS=600000` in production. |
| Database Storage | SQLite (`nexus_delivery.db`) | Local filesystem with POSIX permissions `0644` | Ensure file ownership is locked to `chmod 0600` in deployment. |

---

## 7. Security Sign-Off Summary

- **Authentication Architecture:** **IMPLEMENTED AND RUNTIME VERIFIED** (PBKDF2, sessions, CSRF).
- **Access Control (RBAC):** **IMPLEMENTED AND RUNTIME VERIFIED** (Privileged APIs protected).
- **Rate Limiting:** **IMPLEMENTED AND RUNTIME VERIFIED** (Leaky bucket rate limiter active).
- **Production Hardening Action Item:** **Eliminate static bypass tokens (`OP-TOKEN-SUPERVISOR`) in production builds.**
