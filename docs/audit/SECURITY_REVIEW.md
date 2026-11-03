# NexusDelivery — Application Security & Threat Model Review (Phase F)

**Document ID:** DOC-ND-SEC-005  
**Revision:** 2.0  
**Authors:** Application Security Engineer, Backend & Distributed Systems Architect  
**Date:** November 3, 2026  
**Status:** IMPLEMENTED AND AUDITED (OWASP Top 10 & Robotics Hardening Applied)  

---

## 1. Executive Summary

This security review evaluates the NexusDelivery autonomous delivery platform against the OWASP Top 10 web vulnerabilities and specialized cyber-physical attack vectors targeting autonomous mobile robots (AMRs). 

In accordance with Phase F rules:
- Hardcoded default operator PINs and secret keys were migrated to environment-injected configurations (`NEXUS_SECRET_KEY`, `NEXUS_OPERATOR_PIN`).
- Password storage utilizes PBKDF2-HMAC-SHA256 with individual cryptographic salts and 100,000 hashing rounds.
- Role-Based Access Control (RBAC) strictly isolates `CUSTOMER` endpoints from `SUPERVISOR` cockpit controls.
- Single-use 6-digit OTP delivery tokens are validated with constant-time comparison to prevent timing attacks.

---

## 2. Threat Modeling & Vulnerability Analysis

```mermaid
graph TD
    Attacker[External Threat Actor]
    Attacker -->|Brute-Force Attacks| AuthRateLimit[Token-Bucket Rate Limiter]
    AuthRateLimit -->|Pass| AuthAPI[/api/auth/login]
    AuthAPI -->|PBKDF2-HMAC-SHA256| UserDB[(Encrypted User Store)]
    
    Attacker -.->|Unauthorized Cockpit Access| RBAC_Gate{RBAC Middleware}
    RBAC_Gate -->|Role != SUPERVISOR| Reject403[HTTP 403 Forbidden]
    RBAC_Gate -->|Valid Supervisor Token| SupervisorEndpoints[/api/supervisor/*]
    
    Attacker -.->|Tampered Delivery OTP| OTP_Validator[Constant-Time OTP Check]
    OTP_Validator -->|Failed Hash Match| InhibitHatch[Keep Hatch Locked & Log Incident]
    OTP_Validator -->|Valid Token| UnlockHatch[Engage Hatch Actuator]
```

### 2.1 Threat Vector Assessment
| Threat Scenario | Severity | Mitigation Implemented | Residual Risk |
|---|:---:|---|---|
| **Brute-Force Login / PIN Guessing** | HIGH | Token-bucket rate limiting (max 5 failed attempts per IP / 60 seconds). | LOW |
| **Credential Theft via Database Leak** | HIGH | PBKDF2-HMAC-SHA256 with 100,000 iterations and 16-byte random salts per user. Plaintext passwords never stored. | LOW |
| **Privilege Escalation to Supervisor Cockpit** | CRITICAL | Cryptographically signed session tokens; strict role assertion on `/api/supervisor/*` and `/api/cargo/*`. | LOW |
| **Delivery Compartment Tampering / OTP Brute Force** | HIGH | 6-digit single-use OTPs with 15-minute expiration; maximum 3 failed unlock attempts before lockout. | LOW |
| **Denial of Service (DoS) via API Flood** | MEDIUM | Sliding window request rate limiting on all incoming JSON endpoints. | MEDIUM (requires reverse-proxy WAF in production) |
| **Command Injection over ROS 2 Network** | HIGH | Input sanitization on all telemetry inputs; no shell commands executed from web payloads. | LOW |

---

## 3. Cryptographic & Architecture Verification

### 3.1 Password Hashing Implementation
```python
def hash_password(password: str) -> str:
    """Generate PBKDF2-HMAC-SHA256 password hash with unique 16-byte salt."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + dk.hex()

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verify password against stored salt:hash using constant-time comparison."""
    try:
        salt_hex, hash_hex = stored_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(dk, expected_hash)
    except Exception:
        return False
```

### 3.2 Role-Based Access Control (RBAC) Isolation
- **Role `CUSTOMER`:**
  - Allowed: Browse catalog, compose cart, drop destination pin, place order, enter OTP for assigned order.
  - Denied: Accessing `/api/supervisor/*`, triggering manual dispatch, overriding hatch motors, viewing other customer orders.
- **Role `SUPERVISOR`:**
  - Allowed: Real-time telemetry monitoring, viewing dispatch decision logs, manual route dispatching, triggering emergency braking (E-Stop).
  - Denied: Exposing customer plain credentials or payment tokens.

---

## 4. Production Deployment Security Guidelines

While the current software prototype meets rigorous local verification standards, **physical real-world commercial deployment requires the following operational security controls**:

1. **TLS / HTTPS Termination:**  
   Deploy an enterprise reverse proxy (e.g., NGINX or Cloudflare) terminating TLS 1.3 with HSTS (`Strict-Transport-Security`). Never serve unencrypted HTTP over public cellular networks (4G/5G).
2. **ROS 2 SROS2 Security Enclave:**  
   Enable SROS2 (DDS Security) with x.509 certificates and access control policies for all ROS 2 nodes to encrypt `/cmd_vel`, `/odom`, and `/camera/image_raw` over the robot internal Ethernet/CAN bus.
3. **Physical Hardware Tamper Sensors:**  
   Integrate optical switches and inertial shock sensors on the chassis to detect chassis breach, forced lid prying, or vehicle abduction.
4. **Hardware Security Module (HSM):**  
   Store disk encryption keys and root device certificates inside a TPM 2.0 or secure element on the primary compute board.

---

## 5. Phase F Sign-Off Matrix

| Security Audit Parameter | Baseline Status | Verified Status | Result |
|---|---|---|:---:|
| Password Hashing | Plaintext / Weak Hash | PBKDF2-HMAC-SHA256 (100k rounds) | **PASS** |
| Session Token Security | Predictable | 32-byte cryptographically secure random tokens | **PASS** |
| Customer / Supervisor RBAC | Undefined | Enforced role check on all endpoints | **PASS** |
| Rate Limiting Defense | None | Token-bucket rate limiting implemented | **PASS** |
| Secret Management | Hardcoded strings | Environment variable injection with safeguards | **PASS** |
| Overall Phase F Status | Prototype | **Hardened Application Baseline** | **PASS** |
