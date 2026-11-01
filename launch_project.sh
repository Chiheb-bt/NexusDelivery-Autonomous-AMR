#!/usr/bin/env bash
set -euo pipefail

# Chiheb Robotics — NexusDelivery Primary Platform Launcher
# Seamless shortcut to visual 3D Gazebo simulation + Web Fleet Control HUD

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$script_dir/run_visual_simulation.sh" "$@"