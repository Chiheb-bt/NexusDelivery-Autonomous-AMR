# NexusDelivery — Deployment & Operations Guide
## Enterprise Setup, Simulation Execution, Security Configuration & Reverse Proxy Hardening

**Document Version:** 2.0.0  
**Target Environment:** Ubuntu 22.04 LTS (Jammy Jellyfish)  
**Middleware:** ROS 2 Humble Hawksbill • Gazebo Classic 11.10.2 • Python 3.10+  
**Target Architecture:** Modular Monolith with Dual Isolated Portals (Customer & Supervisor)

---

## 1. System Requirements & Prerequisites

### 1.1 Hardware Specifications

| Component | Minimum Specification (Development/Evaluation) | Recommended Specification (Multi-Robot / High-Fi) |
| :--- | :--- | :--- |
| **CPU** | 4-Core x86_64 (e.g. Intel Core i5 / AMD Ryzen 5) | 8-Core x86_64 (Intel Core i7 / AMD Ryzen 7) |
| **RAM** | 8 GB DDR4 | 16 GB DDR4/DDR5 |
| **GPU** | Integrated Intel UHD / Iris Xe (Software OpenGL) | Dedicated NVIDIA RTX 3060+ (NVIDIA Proprietary Drivers) |
| **Storage** | 20 GB Free SSD Space | 50 GB NVMe PCIe SSD |
| **Network** | Loopback / 100 Mbps LAN | 1 Gbps LAN with TLS 1.3 Reverse Proxy |

### 1.2 Software Dependencies

- **Operating System:** Ubuntu 22.04.4 LTS (Linux kernel 5.15 / 6.5)
- **Robotics Runtime:** ROS 2 Humble Hawksbill (`ros-humble-desktop`)
- **Simulation Engine:** Gazebo Classic 11.10.2 (`gazebo11`, `gazebo-ros-pkgs`)
- **Python Runtime:** Python 3.10.12+ with standard packages:
  - `sqlite3` (Built-in ACID relational database)
  - `hashlib`, `hmac`, `secrets` (Cryptographic security)
  - `opencv-python` / `cv_bridge` (Perception stream handling)
  - `numpy`, `scipy` (Geometric trajectory planning)
- **Web Browser Client:** Chrome 100+, Firefox 95+, Safari 15+, Edge 100+ (Requires HTML5 Canvas 2D and Web Audio API).

---

## 2. Environment Variables & Secret Configuration

NexusDelivery enforces zero hardcoded secrets. Privileged tokens and cryptographic configurations must be supplied via process environment variables or an enterprise secret manager (e.g. HashiCorp Vault, AWS Secrets Manager).

### 2.1 Configuration Table

| Environment Variable | Description | Default (If Unset) | Security Level |
| :--- | :--- | :--- | :--- |
| `NEXUS_OPERATOR_PIN` | Master supervisor authorization token for manual teleoperation and emergency stops. | *Generates ephemeral 32-char hex token on launch* | **CRITICAL / RESTRICTED** |
| `PBKDF2_ITERATIONS` | Iteration count for PBKDF2-HMAC-SHA256 password hashing. | `100000` (Production) / `10000` (CI Tests) | **HIGH** |
| `NEXUS_PORT` | HTTP port for dual-portal Web Bridge server. | `8080` | **INTERNAL** |
| `NEXUS_BIND_ADDR` | Network interface address for server binding. | `0.0.0.0` (Use `127.0.0.1` behind Nginx) | **HIGH** |
| `NEXUS_DB_PATH` | Path to persistent SQLite ACID database. | `delivery_robot_sim/nexus_delivery.db` | **MEDIUM** |
| `SIMULATION_MODE` | Runtime execution mode (`SIMULATION` or `HARDWARE`). | `SIMULATION` | **MEDIUM** |

### 2.2 Production Secret Sourcing (`/etc/nexus/nexus.env`)

Create a secure environment file with `chmod 600`:

```bash
sudo mkdir -p /etc/nexus
sudo cat << 'EOF' > /etc/nexus/nexus.env
NEXUS_OPERATOR_PIN=Str0ng-0per4tor-P1N-2026!
PBKDF2_ITERATIONS=600000
NEXUS_PORT=8080
NEXUS_BIND_ADDR=127.0.0.1
NEXUS_DB_PATH=/var/lib/nexus/delivery.db
SIMULATION_MODE=SIMULATION
EOF
sudo chmod 600 /etc/nexus/nexus.env
```

---

## 3. Starting the Autonomous Delivery Platform

### 3.1 Step 1: Source the ROS 2 Environment

```bash
source /opt/ros/humble/setup.bash
cd /home/chiheb/Downloads/RDSim-devel-2wheel_diff
colcon build --symlink-install --packages-select delivery_robot_sim
source install/setup.bash
```

### 3.2 Step 2: Launch Gazebo Simulation (`small_city_dynamic.world`)

Launch the photorealistic urban environment featuring dynamic actors, traffic signals, curbside sidewalks, and the Central Logistics Depot:

```bash
ros2 launch delivery_robot_sim simulation_launch.py
```

### 3.3 Step 3: Launch Web Bridge & Dual Isolated Portals

Launch the standalone backend service that binds both portals to the shared SQLite database and ROS 2 telemetry pipeline:

```bash
export $(cat /etc/nexus/nexus.env | xargs)
PYTHONPATH=delivery_robot_sim python3 delivery_robot_sim/delivery_robot_sim/web_bridge_node.py
```

*Console verification output:*
```text
[INFO] [web_bridge_node] Web Dashboard static directory resolved: /.../delivery_robot_sim/web_dashboard
[INFO] [web_bridge_node] Gazebo World vector map initialized: small_city_dynamic (Origin: 36.800500, 10.180000)
[INFO] [web_bridge_node] Web Bridge & Mission Control Server listening on http://127.0.0.1:8080
```

---

## 4. Web Portal Access

Both web platforms are served from the same hardened HTTP engine under strict role-based path separation:

| Platform | URL | Purpose & Target Audience |
| :--- | :--- | :--- |
| **Customer Experience Portal** | `http://localhost:8080/client` (or `/`) | Curbside food/grocery catalog, interactive Gazebo doorstep selector, live AMR route tracking, 6-digit OTP delivery hatch unlock. |
| **Supervisor Operations Cockpit** | `http://localhost:8080/supervisor` | Tactical multi-rover telemetry, RealSense D435i AI HUD, Hailo-8L benchmarks, mission queue, audit trails, remote teleoperation override. |

---

## 5. Production Nginx Reverse Proxy & TLS Hardening

For deployment outside `localhost`, a hardened Nginx reverse proxy terminates TLS 1.3 and enforces strict Content Security Policy (CSP), HTTP Strict Transport Security (HSTS), and CORS allowlists.

### 5.1 Nginx Site Configuration (`/etc/nginx/sites-available/nexusdelivery.conf`)

```nginx
# Upstream Web Bridge Daemon
upstream nexus_backend {
    server 127.0.0.1:8080;
    keepalive 32;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name delivery.nexusrobotics.tn fleet.nexusrobotics.tn;
    return 301 https://$host$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name delivery.nexusrobotics.tn fleet.nexusrobotics.tn;

    # TLS Certificates (Let's Encrypt / Enterprise CA)
    ssl_certificate /etc/letsencrypt/live/nexusrobotics.tn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nexusrobotics.tn/privkey.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none';" always;

    # Customer App Entry
    location / {
        proxy_pass http://nexus_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Supervisor Cockpit Access Restrictions (Internal Subnets Only)
    location /supervisor {
        # Allow enterprise operations VPN / subnet only
        allow 192.168.1.0/24;
        allow 10.8.0.0/24;
        allow 127.0.0.1;
        deny all;

        proxy_pass http://nexus_backend/supervisor;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 6. Systemd Service Deployment

Ensure continuous operation and auto-restart on failure using systemd services.

### 6.1 Service Unit (`/etc/systemd/system/nexus-web-bridge.service`)

```ini
[Unit]
Description=NexusDelivery Autonomous Web Bridge & Fleet Controller
After=network.target

[Service]
Type=simple
User=chiheb
WorkingDirectory=/home/chiheb/Downloads/RDSim-devel-2wheel_diff
EnvironmentFile=/etc/nexus/nexus.env
ExecStart=/usr/bin/python3 delivery_robot_sim/delivery_robot_sim/web_bridge_node.py
Restart=always
RestartSec=5s
LimitNOFILE=65536

# Security Sandbox
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=/var/lib/nexus /tmp

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nexus-web-bridge.service
sudo systemctl status nexus-web-bridge.service
```

---

## 7. Health & Freshness Verification

To monitor system liveness and telemetry freshness:

```bash
# 1. Server Liveness Check
curl -s http://127.0.0.1:8080/api/telemetry | jq .freshness_age_s

# Expected output:
# 0.02 (fresh live telemetry)

# 2. Gazebo World Vector Manifest Check
curl -s http://127.0.0.1:8080/api/map/gazebo_world | jq .bounds

# Expected output:
# { "min_x": -48.0, "max_x": 112.0, "min_y": -48.0, "max_y": 48.0 }
```
