#!/usr/bin/env bash
set -euo pipefail

# Headless simulation runner for RDSim camera-based autonomous delivery robot
# Usage: ./run_headless_simulation.sh [duration_seconds: default 90] [world_name: default small_city.world]

duration=${1:-180}
world_name=${2:-small_city_dynamic.world}
traffic_light=${RDSIM_TRAFFIC_LIGHT:-true}

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace="${RDSIM_WS:-$HOME/rdsim_ws}"
results="${RDSIM_RESULTS_DIR:-$workspace/results}"
container_results="${results/#$workspace//ws}"

mkdir -p "$results"

echo "============================================================"
echo "  CHIHEB ROBOTICS — NEXUS-DELIVERY AUTONOMOUS PLATFORM"
echo "  Automated Headless Simulation & Evaluation Runner"
echo "  Duration: ${duration}s | World: ${world_name}"
echo "  Perception: Front RGB Camera + Depth Sensing (NO LiDAR, NO GPS)"
echo "  Localization: Wheel Odometry (/odom) + IMU | Zero GPS Reliance"
echo "  Results Dir: $results"
echo "  Web Fleet HUD: http://localhost:8080"
echo "============================================================"

# Ensure docker image exists
if ! docker image inspect ros-humble-gazebo:latest >/dev/null 2>&1; then
    echo "Docker image ros-humble-gazebo:latest not found. Building from docker/Dockerfile..."
    docker build -t ros-humble-gazebo:latest "$project_dir/docker"
fi

# Prevent concurrent simulations
docker ps -q --filter ancestor=ros-humble-gazebo:latest | xargs -r docker rm -f >/dev/null 2>&1 || true
sleep 1

echo "Running simulation inside container..."
docker run --rm \
  --name rdsim_sim_container \
  -p 8080:8080 \
  -u "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e ROS_HOME=/tmp/.ros \
  -e RDSIM_TRAFFIC_LIGHT="$traffic_light" \
  -e RDSIM_SCENARIO="${RDSIM_SCENARIO:-empty}" \
  -e RDSIM_RESULTS_DIR="$container_results" \
  -v "$project_dir:$project_dir:ro" \
  -v "$project_dir:/rdsim:ro" \
  -v "$workspace:/ws" \
  -v /etc/passwd:/etc/passwd:ro \
  -v /etc/group:/etc/group:ro \
  ros-humble-gazebo:latest bash -lc "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && bash /rdsim/run_demo.sh $duration false $world_name"

echo "============================================================"
echo "  Simulation Completed."
echo "  Results stored in: $results"
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
