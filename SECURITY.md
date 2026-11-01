# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | Yes                |
| < 0.2.0 | No                 |

## Reporting a Vulnerability

If you discover a security vulnerability within this repository, please report it responsibly by contacting the maintainer directly at:

**Email**: `bchiheb598@gmail.com`

Please do NOT open public GitHub issues for security vulnerabilities. We will review and address valid reports within 7 business days.

---

## Secret and Credential Management

### Operator PIN Management
- The operator PIN must never be committed to source control or embedded in client-side scripts.
- The web bridge node and remote ingress scripts read credentials strictly from the environment variable `NEXUS_OPERATOR_PIN` (or `NEXUS_ACCESS_TOKEN`).
- If no environment variable is provided, the node generates an ephemeral, cryptographically secure 128-bit random token for the active session and logs a warning.

### PIN Rotation Procedure
In the event that an operator PIN is suspected of compromise:
1. Immediately terminate all active tunnel or web bridge sessions:
   ```bash
   pkill -f web_bridge_node
   pkill -f cloudflared
   ```
2. Generate a new high-entropy operator PIN (minimum 16 alphanumeric characters):
   ```bash
   export NEXUS_OPERATOR_PIN=$(python3 -c "import secrets; print(secrets.token_hex(16))")
   ```
3. Restart the service with the new environment variable.
4. Clear any cached operator tokens in client browsers via developer console:
   ```javascript
   sessionStorage.removeItem('nexus_operator_token');
   ```

### Automated CI Secret Scanning
This repository integrates `gitleaks` in its GitHub Actions continuous integration pipeline to audit pull requests and commits against accidental secret disclosures.
