# NexusDelivery — Comprehensive Security Audit & Threat Model

**Audit Date:** November 2, 2026  
**Security Architect:** Application & Robotics Security Team  
**Scope:** Full Stack (ROS 2 Bridge, Web Applications, Authentication, APIs, Hardware Interfaces)  
**Classification:** Internal Engineering Audit

---

## 1. Executive Summary

This security audit evaluates the existing implementation of the NexusDelivery platform across all communication layers: client web application, supervisor cockpit, HTTP web bridge, in-memory state store, and ROS 2 communication buses.

**Critical Audit Verdict:** While the core robotics state machines feature sound localized security (specifically the HMAC-SHA256 one-time password OTP generation with 3-strike lockout in `order_manager.py`), the web bridge layer (`web_bridge_node.py`) and frontend applications (`client.js`, `supervisor.js`) currently exhibit **critical architectural vulnerabilities** typical of simulation prototypes. The system lacks database-backed credential storage, cryptographic session tokens, role-based access control, CSRF mitigation, rate limiting, and origin isolation between public customers and privileged operators.

---

## 2. Detailed Vulnerability Assessment

### VULN-01: Insecure In-Memory Credential Storage & Unsalted Hashing
- **Location:** `delivery_robot_sim/delivery_robot_sim/web_bridge_node.py` (lines 1298–1340)
- **CWE:** CWE-256 (Plaintext Storage of a Password), CWE-916 (Use of Password Hash with Insufficient Computational Effort)
- **Description:** Customer registrations store passwords in volatile memory dictionaries (`self.user_accounts`). Passwords are verified either in plaintext or using single-iteration unsalted hashing. No memory-hard password hashing algorithm (such as Argon2id or bcrypt) is used.
- **Impact:** Any memory inspection or diagnostic dump exposes all customer credentials instantly. All accounts vanish when the node restarts.

### VULN-02: Broken Object-Level Authorization (BOLA / IDOR) in Order API
- **Location:** `delivery_robot_sim/delivery_robot_sim/web_bridge_node.py` (lines 685–689)
- **CWE:** CWE-639 (Authorization Bypass Through User-Controlled Key)
- **Description:** The `GET /api/orders` endpoint returns the complete order list across all customers to any requester without authentication:
  ```python
  elif path == '/api/orders':
      with bridge.lock:
          data = list(bridge.orders)
      self._serve_json(data)
  ```
- **Impact:** A public customer can inspect all customer names, delivery addresses, phone numbers, order contents, and live 6-digit OTP unlock codes for every active delivery.

### VULN-03: Lack of Portal Separation & Network Privilege Creep
- **Location:** `delivery_robot_sim/delivery_robot_sim/web_bridge_node.py` (lines 650–760)
- **CWE:** CWE-284 (Improper Access Control)
- **Description:** Both the Customer Portal (`/` or `/client`) and the Fleet Supervisor Cockpit (`/supervisor`) are served on the exact same HTTP port (8080) on the same origin without boundary segregation. Anyone with network access can navigate to `http://localhost:8080/supervisor`.
- **Impact:** Privileged operator dashboards, internal hardware diagnostics, BMS cell metrics, and NPU performance logs are publicly exposed.

### VULN-04: Static Shared Operator PIN Authentication
- **Location:** `delivery_robot_sim/delivery_robot_sim/web_bridge_node.py` (lines 764–774, lines 818–828)
- **CWE:** CWE-287 (Improper Authentication), CWE-798 (Use of Hard-coded Credentials)
- **Description:** Supervisor authorization uses a single environment variable `NEXUS_OPERATOR_PIN` (or fallback token) passed as a header or query parameter. There is no multi-factor authentication (MFA), no session expiration, no token rotation, and no individual audit logging of which human operator authorized a command.
- **Impact:** A compromised PIN grants permanent, unrestricted command authority over the robot's physical actuators and Emergency Stop systems.

### VULN-05: Direct Actuator Injection from Web Requests
- **Location:** `delivery_robot_sim/delivery_robot_sim/web_bridge_node.py` (lines 925–932)
- **CWE:** CWE-306 (Missing Authentication for Critical Function)
- **Description:** The endpoint `POST /api/teleop` directly translates incoming HTTP JSON payloads (`v` and `w`) into `/cmd_vel` Twist messages without operator PIN verification:
  ```python
  elif path == '/api/teleop':
      v = float(data.get('v', 0.0))
      w = float(data.get('w', 0.0))
      t_msg = Twist()
      t_msg.linear.x = float(max(-1.0, min(1.5, v)))
      t_msg.angular.z = float(max(-1.5, min(1.5, w)))
      bridge.pub_teleop.publish(t_msg)
  ```
- **Impact:** An unauthenticated network attacker can override autonomous driving and teleoperate the robot directly into obstacles or traffic.

### VULN-06: Lack of CSRF, Rate Limiting, and Secure Headers
- **Location:** HTTP response headers in `web_bridge_node.py`
- **CWE:** CWE-352 (Cross-Site Request Forgery), CWE-799 (Improper Control of Generation of Code)
- **Description:** The server lacks CSRF tokens, rate limiting on sensitive authentication/dispatch endpoints, and critical security headers (Content Security Policy, Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options).

---

## 3. Comprehensive Threat Model

We analyze potential adversaries: malicious web users, intercepted network actors, compromised credentials, and insider operators.

| Threat ID | Threat Category | Attack Vector | Potential Impact | Required Defense Control |
|:---|:---|:---|:---|:---|
| **TM-01** | **Account Takeover** | Brute force or credential stuffing on `/api/auth/login` | Attacker hijacks customer account and delivery history | Rate limiting (max 5 attempts / min), Argon2id password hashing, optional 2FA |
| **TM-02** | **Unauthorized Order Snooping** | Calling `GET /api/orders` | Exposure of customer PII, addresses, phone numbers, and pickup OTPs | Enforce tenant scoping: customers can ONLY query orders where `customer_id == authenticated_user_id` |
| **TM-03** | **Actuator Hijacking** | Sending unauthorized `POST /api/teleop` or `POST /api/dispatch_target` | Robot motion deviation, physical crash, pedestrian collision | Mandatory cryptographically signed JWT with `OPERATOR` role claim, hardware watchdog |
| **TM-04** | **Denial of Service (DoS)** | Flooding `POST /api/orders` with thousands of fake delivery requests | Exhausts robot fleet queue and freezes physical delivery operations | Captcha / rate-limiting, delivery fee authorization hold, max 1 active order per unverified account |
| **TM-05** | **E-Stop Sabotage / Denial** | Unauthorized invocation of `/api/estop` | Halts logistics operations across the city | Require signed operator audit logs; keep physical E-stop independent of web stack |
| **TM-06** | **OTP Interception & Theft** | Guessing or brute-forcing 6-digit handover OTP | Package theft from cargo compartment | 3-strike lockout, HMAC-SHA256 dynamic rotating code, physical hatch tamper sensor |
| **TM-07** | **Forged Robot Telemetry** | Injecting falsified odometry or battery levels | Supervisor cockpit blind to real robot distress or low battery | Authenticated ROS 2 / DDS domain boundaries; reject telemetry with backward timestamps |
| **TM-08** | **Cross-Site Scripting (XSS)** | Malicious payload in customer delivery address or notes | Session theft from fleet supervisor viewing customer orders | Strict input validation, output HTML entity encoding, Content Security Policy (CSP) |

---

## 4. Target Security Architecture & Remediation Plan

```
+-----------------------------------------------------------------------------------------+
|                                    INTERNET CLIENTS                                     |
+------------------------------------+----------------------------------------------------+
                                     |
               HTTPS (TLS 1.3) / Strict Content-Security-Policy
                                     |
                                     v
+-----------------------------------------------------------------------------------------+
| Reverse Proxy / API Gateway (e.g. Nginx / Caddy)                                        |
| - SSL Termination & Rate Limiting                                                       |
| - Origin & Path-Based Routing:                                                          |
|     /client, /api/customer/*  --> Customer Realm (Port 8000)                            |
|     /supervisor, /api/fleet/* --> Privileged Operator Realm (Port 8001, VPN / MFA Only)|
+------------------------------------+----------------------------------------------------+
                                     |
               Authenticated Session / Short-Lived JWT (Argon2id)
                                     |
                                     v
+-----------------------------------------------------------------------------------------+
| NexusDelivery Secure Backend Service                                                    |
|                                                                                         |
|  [Auth Module]           [Order Service]          [Fleet Dispatcher]                    |
|  - Argon2id Password     - Input Validation       - Feasible Graph Verification         |
|  - HttpOnly Cookie       - Tenant Scoping         - Role Check: OPERATOR                |
|  - CSRF Verification     - PII Masking            - Rate Limiting                       |
|                                                                                         |
|  [PostgreSQL / SQLite Database]                                                         |
|  - Users (Customers, Operators, Admins)                                                 |
|  - Addresses (Validated coordinates)                                                    |
|  - Orders (State, items, encrypted hashes)                                              |
|  - Audit Log (Every dispatch, teleop, or E-Stop action with operator ID & timestamp)   |
+------------------------------------+----------------------------------------------------+
                                     |
                   Controlled Localhost ROS 2 Adapter (Zero Public DDS)
                                     |
                                     v
+-----------------------------------------------------------------------------------------+
| ROS 2 Humble Robotics Runtime (Isolated Simulation / Hardware Network)                  |
| - /delivery/new_order, /odom, /camera/image_raw                                         |
+-----------------------------------------------------------------------------------------+
```

### Immediate Remediation Requirements:
1. **Strict Port & Portal Separation:** Separate Customer Platform and Supervisor Cockpit into distinct authorization realms.
2. **Mandatory Tenant Scoping:** Ensure customer queries are strictly filtered by authenticated `user_id`. Never return all orders globally.
3. **Password Security:** Use standard, well-tested cryptographic hashing (Argon2id or PBKDF2 with salt) and eliminate plaintext credential storage.
4. **Command Authorization:** Require verified operator tokens for all motion, dispatch, hatch, and E-Stop commands.
5. **Audit Logging:** Maintain an immutable audit table recording every supervisor intervention, teleoperation command, and emergency override.
