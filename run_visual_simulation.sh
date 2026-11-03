#!/usr/bin/env bash
set -euo pipefail

# Visual 3D simulation runner for RDSim autonomous delivery robot
# Usage: ./run_visual_simulation.sh [duration_seconds: default 0 (until Gazebo window is closed or Ctrl+C)] [world_name: default small_city_dynamic.world]

duration=${1:-0}
world_name=${2:-small_city_dynamic.world}
traffic_light=${RDSIM_TRAFFIC_LIGHT:-true}

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace="${RDSIM_WS:-$HOME/rdsim_ws}"
results="${RDSIM_RESULTS_DIR:-$workspace/results}"
container_results="${results/#$workspace//ws}"

mkdir -p "$results"

echo "============================================================"
echo "  CHIHEB ROBOTICS — NEXUS-DELIVERY AUTONOMOUS PLATFORM"
echo "  Gazebo Classic 3D Living Urban Simulation + ROS 2 Humble"
echo "  Perception: Front RGB Camera + Depth Sensing (NO LiDAR, NO GPS)"
echo "  Localization: Wheel Odometry (/odom) + IMU | Zero GPS Reliance"
echo "  Depot Hub: Central Logistics Facility (-31.5, -0.75)"
echo "  Web Fleet HUD: http://localhost:8080"
echo "============================================================"

# Check for DISPLAY
if [ -z "${DISPLAY:-}" ]; then
  echo "Error: DISPLAY environment variable is not set." >&2
  echo "Visual simulation requires an active graphical X11 desktop display." >&2
  exit 1
fi

# Ensure docker image exists
if ! docker image inspect ros-humble-gazebo:latest >/dev/null 2>&1; then
    echo "Docker image ros-humble-gazebo:latest not found. Building from docker/Dockerfile..."
    docker build -t ros-humble-gazebo:latest "$project_dir/docker"
fi

# Prevent concurrent simulations
docker ps -q --filter ancestor=ros-humble-gazebo:latest | xargs -r docker rm -f >/dev/null 2>&1 || true
sleep 1

# Configure X11 authorization
xauth_file="${XAUTHORITY:-$HOME/.Xauthority}"
xauth_args=()
if [ -f "$xauth_file" ]; then
    xauth_args=(-e XAUTHORITY=/tmp/.Xauthority -v "$xauth_file:/tmp/.Xauthority:ro")
fi

# Authorize local X connections if xhost utility is present
if command -v xhost >/dev/null 2>&1; then
    xhost +si:localuser:"$(whoami)" >/dev/null 2>&1 || xhost +local:"$(whoami)" >/dev/null 2>&1 || true
fi

# Pass DRI device if available for OpenGL hardware acceleration
dri_args=()
libgl_software=1
if [ -d /dev/dri ]; then
    dri_args=(--device /dev/dri:/dev/dri --group-add 44 --group-add 990)
    libgl_software=0
fi

echo "Launching visible Gazebo Classic GUI and autonomy pipeline..."
docker run --rm \
  --name rdsim_sim_container \
  -p 8080:8080 \
  -u "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e ROS_HOME=/tmp/.ros \
  -e DISPLAY="$DISPLAY" \
  "${xauth_args[@]}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /etc/passwd:/etc/passwd:ro \
  -v /etc/group:/etc/group:ro \
  "${dri_args[@]}" \
  -e RDSIM_TRAFFIC_LIGHT="$traffic_light" \
  -e RDSIM_SCENARIO="${RDSIM_SCENARIO:-empty}" \
  -e RDSIM_RESULTS_DIR="$container_results" \
  -e QT_X11_NO_MITSHM=1 \
  -e LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-$libgl_software}" \
  -v "$project_dir:$project_dir:ro" \
  -v "$project_dir:/rdsim:ro" \
  -v "$workspace:/ws" \
  ros-humble-gazebo:latest bash -lc "
set -e
source /opt/ros/humble/setup.bash
source /ws/install/setup.bash
bash /rdsim/run_demo.sh $duration true $world_name
"

echo "============================================================"
echo "  Visual simulation session ended cleanly."
echo "  Results and logs stored in: $results"
if [ -f "$results/eval_summary.json" ]; then
    echo "  --- Evaluation Summary (JSON) ---"
    cat "$results/eval_summary.json"
    echo ""
fi
if [ -f "$results/delivery_orders.json" ]; then
    echo "  --- Delivery Orders (JSON) ---"
    cat "$results/delivery_orders.json"
    echo ""
fi
echo "============================================================"
