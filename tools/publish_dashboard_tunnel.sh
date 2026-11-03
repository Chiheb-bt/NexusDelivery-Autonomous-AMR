#!/bin/bash
# ==============================================================================
# Chiheb Robotics — NexusDelivery Fleet Mission Control
# Public Remote Access Tunnel Launcher (Cloudflare Tunnel)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOUDFLARED_BIN="${SCRIPT_DIR}/cloudflared"
PORT="${1:-8080}"
LOG_FILE="/tmp/nexus_tunnel.log"
PID_FILE="/tmp/nexus_tunnel.pid"

if [ ! -x "${CLOUDFLARED_BIN}" ]; then
  echo "[-] cloudflared binary not found at ${CLOUDFLARED_BIN}!"
  exit 1
fi

# Kill previous tunnel instance if running
if [ -f "${PID_FILE}" ]; then
  OLD_PID=$(cat "${PID_FILE}" || true)
  if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
    echo "[*] Terminating prior tunnel instance (PID: ${OLD_PID})..."
    kill "${OLD_PID}" 2>/dev/null || true
    sleep 1
  fi
  rm -f "${PID_FILE}"
fi

echo "[+] Launching Cloudflare Tunnel for NexusDelivery Mission Control on port ${PORT}..."
rm -f "${LOG_FILE}"

nohup "${CLOUDFLARED_BIN}" tunnel --protocol http2 --url "http://localhost:${PORT}" > "${LOG_FILE}" 2>&1 &
TUNNEL_PID=$!
disown "${TUNNEL_PID}" 2>/dev/null || true
echo "${TUNNEL_PID}" > "${PID_FILE}"

echo "[*] Establishing secure HTTPS edge ingress (PID: ${TUNNEL_PID})..."

TUNNEL_URL=""
for i in {1..20}; do
  sleep 1
  if grep -o 'https://[-a-zA-Z0-9\.]*\.trycloudflare\.com' "${LOG_FILE}" > /tmp/found_url.txt 2>/dev/null; then
    TUNNEL_URL=$(head -n 1 /tmp/found_url.txt)
    if [ -n "${TUNNEL_URL}" ]; then
      break
    fi
  fi
done

if [ -z "${TUNNEL_URL}" ]; then
  echo "[-] Failed to detect public tunnel URL within timeout. Check log: ${LOG_FILE}"
  exit 1
fi

OPERATOR_PIN="${NEXUS_OPERATOR_PIN:-}"
if [ -z "${OPERATOR_PIN}" ]; then
  echo "[-] ERROR: NEXUS_OPERATOR_PIN environment variable is not defined."
  echo "[-] Set it before publishing: export NEXUS_OPERATOR_PIN='your-strong-pin'"
  exit 1
fi

echo ""
echo "================================================================================"
echo "NEXUSDELIVERY FLEET MISSION CONTROL IS PUBLISHED"
echo "================================================================================"
echo "  PUBLIC SECURE URL   : ${TUNNEL_URL}"
echo "  ACCESS OPERATOR PIN : [CONFIGURED VIA NEXUS_OPERATOR_PIN]"
echo "  STATUS              : ACTIVE PROXY"
echo "================================================================================"
echo "Share this URL to monitor and command the robot from any phone, laptop, or remote location."
echo "Log output available at: ${LOG_FILE}"
