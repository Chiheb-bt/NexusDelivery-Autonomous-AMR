# NexusDelivery — Backup & Disaster Recovery Runbook
## ACID Relational State Preservation, Automated Snapshotting & Cold Site Recovery

**Document Version:** 2.0.0  
**Database Architecture:** SQLite 3.37+ WAL Mode (Write-Ahead Logging)  
**Recovery Time Objective (RTO):** < 15 minutes  
**Recovery Point Objective (RPO):** < 1 hour (Scheduled snapshots) / Real-Time (WAL journal)

---

## 1. Storage Architecture Overview

NexusDelivery uses an ACID-compliant SQLite relational database (`nexus_delivery.db`) configured with:
- `journal_mode = WAL` (Write-Ahead Logging allows concurrent readers and writers without blocking).
- `synchronous = NORMAL` (Ensures durability across OS crashes while maximizing I/O throughput).
- `foreign_keys = ON` (Enforces referential integrity across users, sessions, orders, and addresses).
- `busy_timeout = 5000` (Mitigates transient locking contention).

### Critical Data Entities

1. **`users`**: Customer and operator accounts, Argon2id/PBKDF2 password hashes, verification state.
2. **`orders`**: Active and historical delivery missions, target Gazebo $(X, Y)$ coordinates, stopping coordinates, routing distance, ETA, and 6-digit OTP codes.
3. **`addresses`**: Saved customer doorsteps with validated Gazebo curbside docking locations.
4. **`audit_logs`**: Append-only cryptographic security audit trail (logins, teleop overrides, E-stop triggers).
5. **`sessions`**: Active bearer session tokens and CSRF credentials.

---

## 2. Automated Online Backup Procedure

Because SQLite is in WAL mode, taking a file copy with `cp` while transactions are occurring can result in an inconsistent snapshot. NexusDelivery provides a dedicated zero-downtime online backup procedure using SQLite's native `VACUUM INTO` command.

### 2.1 Backup Automation Script (`scripts/backup_database.sh`)

```bash
#!/usr/bin/env bash
# ==============================================================================
# NexusDelivery — Automated Online Database Backup
# ==============================================================================
set -euo pipefail

DB_PATH="${NEXUS_DB_PATH:-/home/chiheb/Downloads/RDSim-devel-2wheel_diff/delivery_robot_sim/nexus_delivery.db}"
BACKUP_DIR="${NEXUS_BACKUP_DIR:-/var/backups/nexus}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAPSHOT_FILE="${BACKUP_DIR}/nexus_delivery_${TIMESTAMP}.db"
ARCHIVE_FILE="${SNAPSHOT_FILE}.gz"

mkdir -p "${BACKUP_DIR}"

if [ ! -f "${DB_PATH}" ]; then
    echo "[ERROR] Database file not found at ${DB_PATH}"
    exit 1
fi

echo "[INFO] Initiating atomic snapshot: ${SNAPSHOT_FILE}"

# Execute non-blocking VACUUM INTO
sqlite3 "${DB_PATH}" "VACUUM INTO '${SNAPSHOT_FILE}';"

# Verify integrity of snapshot
INTEGRITY=$(sqlite3 "${SNAPSHOT_FILE}" "PRAGMA quick_check;")
if [ "${INTEGRITY}" != "ok" ]; then
    echo "[CRITICAL] Snapshot integrity check failed: ${INTEGRITY}"
    rm -f "${SNAPSHOT_FILE}"
    exit 2
fi

# Compress and generate SHA-256 checksum
gzip -9 "${SNAPSHOT_FILE}"
sha256sum "${ARCHIVE_FILE}" > "${ARCHIVE_FILE}.sha256"

echo "[SUCCESS] Backup complete: ${ARCHIVE_FILE}"
echo "[SHA256] $(cat ${ARCHIVE_FILE}.sha256)"

# Retention policy: Delete backups older than 14 days
find "${BACKUP_DIR}" -name "nexus_delivery_*.db.gz" -mtime +14 -delete
find "${BACKUP_DIR}" -name "nexus_delivery_*.db.gz.sha256" -mtime +14 -delete
```

### 2.2 Cron Schedule Configuration

Configure hourly snapshotting via cron:

```bash
# /etc/cron.d/nexus-backup
0 * * * * chiheb /home/chiheb/Downloads/RDSim-devel-2wheel_diff/scripts/backup_database.sh >> /var/log/nexus_backup.log 2>&1
```

---

## 3. Disaster Recovery Procedures

### 3.1 Scenario 1: Database File Corruption

**Symptoms:**
- Log error: `sqlite3.DatabaseError: file is not a database` or `database disk image is malformed`.
- Web Bridge fails to start or responds with HTTP 500 on all `/api/orders` endpoints.

**Recovery Steps:**

1. Stop the Web Bridge service:
   ```bash
   sudo systemctl stop nexus-web-bridge
   ```

2. Quarantine the corrupted database:
   ```bash
   mv /home/chiheb/Downloads/RDSim-devel-2wheel_diff/delivery_robot_sim/nexus_delivery.db \
      /home/chiheb/Downloads/RDSim-devel-2wheel_diff/delivery_robot_sim/nexus_delivery_corrupt_$(date +%s).db
   ```

3. Retrieve and verify the latest uncorrupted snapshot:
   ```bash
   LATEST_BACKUP=$(ls -t /var/backups/nexus/nexus_delivery_*.db.gz | head -1)
   sha256sum -c "${LATEST_BACKUP}.sha256"
   ```

4. Restore database from compressed archive:
   ```bash
   gunzip -c "${LATEST_BACKUP}" > /home/chiheb/Downloads/RDSim-devel-2wheel_diff/delivery_robot_sim/nexus_delivery.db
   chmod 640 /home/chiheb/Downloads/RDSim-devel-2wheel_diff/delivery_robot_sim/nexus_delivery.db
   ```

5. Verify database integrity:
   ```bash
   sqlite3 /home/chiheb/Downloads/RDSim-devel-2wheel_diff/delivery_robot_sim/nexus_delivery.db "PRAGMA integrity_check;"
   # Expected output: ok
   ```

6. Restart service:
   ```bash
   sudo systemctl start nexus-web-bridge
   ```

---

### 3.2 Scenario 2: Compromised Operator Session or Token Leak

**Symptoms:**
- Unrecognized teleoperation command in `audit_logs`.
- Operator PIN exposed in logs or network trace.

**Recovery Steps:**

1. Immediately rotate `NEXUS_OPERATOR_PIN` in `/etc/nexus/nexus.env`:
   ```bash
   NEW_PIN=$(openssl rand -hex 16)
   sudo sed -i "s/NEXUS_OPERATOR_PIN=.*/NEXUS_OPERATOR_PIN=${NEW_PIN}/" /etc/nexus/nexus.env
   ```

2. Revoke all active sessions directly in database:
   ```bash
   sqlite3 /home/chiheb/Downloads/RDSim-devel-2wheel_diff/delivery_robot_sim/nexus_delivery.db "DELETE FROM sessions;"
   ```

3. Restart the service to arm new PIN:
   ```bash
   sudo systemctl restart nexus-web-bridge
   ```

4. Audit security trail for unauthorized commands:
   ```bash
   sqlite3 /home/chiheb/Downloads/RDSim-devel-2wheel_diff/delivery_robot_sim/nexus_delivery.db \
     "SELECT timestamp, actor_id, action, target_entity FROM audit_logs ORDER BY id DESC LIMIT 50;"
   ```

---

### 3.3 Scenario 3: Complete Host Failure (Cold Site Migration)

1. Provision fresh Ubuntu 22.04 LTS host.
2. Install ROS 2 Humble Hawksbill and Gazebo Classic 11.
3. Clone repository `Chiheb-bt/NexusDelivery-Autonomous-AMR`.
4. Restore latest encrypted backup from remote offsite S3/rsync storage.
5. Launch `simulation_launch.py` and `web_bridge_node.py`.
6. Total estimated recovery time: **12 minutes**.
