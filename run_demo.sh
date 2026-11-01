#!/usr/bin/env bash
set -euo pipefail

duration=${1:-180}
gui=${2:-false}
world_name=${3:-small_city_dynamic.world}

if ! [[ "$duration" =~ ^(0|[1-9][0-9]*)$ ]]; then
  printf 'Usage: %s <seconds|0> [gui: true|false] [small_city.world|camera_delivery.world]
' "$0" >&2
  exit 2
fi
if [[ "$gui" != true && "$gui" != false ]]; then
  printf 'GUI option must be true or false
' >&2
  exit 2
fi

case "$world_name" in
  small_city*.world)
    spawn_x=${RDSIM_SPAWN_X:--31.5}
    traffic_light=${RDSIM_TRAFFIC_LIGHT:-true}
    ;;
  camera_delivery.world)
    spawn_x=${RDSIM_SPAWN_X:--2.8}
    traffic_light=${RDSIM_TRAFFIC_LIGHT:-true}
    ;;
  *)
    printf 'Unsupported world: %s\n' "$world_name" >&2
    exit 2
    ;;
esac

if [[ "$traffic_light" != true && "$traffic_light" != false ]]; then
  printf 'RDSIM_TRAFFIC_LIGHT must be true or false\n' >&2
  exit 2
fi
spawn_y=${RDSIM_SPAWN_Y:--0.75}
spawn_z=${RDSIM_SPAWN_Z:-0.05}

if [[ -d /ws/src ]]; then
  workspace=/ws
else
  workspace=${RDSIM_WS:-"$HOME/rdsim_ws"}
fi
results=${RDSIM_RESULTS_DIR:-"$workspace/results"}
install_base=${RDSIM_INSTALL_BASE:-/tmp/install}
if [[ ! -f "$install_base/setup.bash" ]]; then
  install_base="$workspace/install"
fi
mkdir -p "$results"
rm -f "$results/eval_summary.json" "$results/delivery_orders.json" "$results/delivery_orders.csv"

set +u
source /opt/ros/humble/setup.bash
source "$install_base/setup.bash"
set -u

export PYTHONUNBUFFERED=1
export GAZEBO_MODEL_DATABASE_URI=""
export GAZEBO_MODEL_PATH="$install_base/rdsim_gazebo/share/rdsim_gazebo/models:/rdsim/rdsim_gazebo/models:${GAZEBO_MODEL_PATH:-}"

xvfb_pid=""
if [[ "$gui" != true ]]; then
  if [[ -z "${DISPLAY:-}" ]]; then
    # Start headless virtual X server for Gazebo camera sensor rendering
    Xvfb :99 -screen 0 1280x1024x24 -ac +extension GLX +render -noreset >/dev/null 2>&1 &
    xvfb_pid=$!
    export DISPLAY=:99
    for _ in {1..20}; do
      if [[ -S /tmp/.X11-unix/X99 ]]; then
        break
      fi
      sleep 0.1
    done
  fi
fi

setsid ros2 launch rdsim_gazebo camera_only.launch.py \
  results_dir:="$results" gui:="$gui" world_name:="$world_name" \
  spawn_x:="$spawn_x" spawn_y:="$spawn_y" spawn_z:="$spawn_z" \
  traffic_light:="$traffic_light" \
  obstacle_x:="${RDSIM_OBS_X:--23.0}" obstacle_y:="${RDSIM_OBS_Y:-0.25}" \
  simulate_depth_drop_t:="${RDSIM_DEPTH_DROP_T:-0.0}" \
  >"$results/run.log" 2>&1 &
launch_pid=$!
launch_stopped=false
recorder_pid=""

recorder_script="$workspace/src/RDSim/tools/record_dynamic_world_evidence.py"
if [[ ! -f "$recorder_script" ]]; then
  recorder_script="/rdsim/tools/record_dynamic_world_evidence.py"
fi
if [[ -f "$recorder_script" ]]; then
  python3 "$recorder_script" --results-dir "$results" >"$results/evidence_recorder.log" 2>&1 &
  recorder_pid=$!
fi


cleanup() {
  if [[ "$launch_stopped" == true ]]; then
    return
  fi
  launch_stopped=true
  if kill -0 "$launch_pid" 2>/dev/null; then
    kill -INT -- -"$launch_pid" 2>/dev/null || kill -INT "$launch_pid" 2>/dev/null || true
    for i in {1..8}; do
      if ! kill -0 "$launch_pid" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    if kill -0 "$launch_pid" 2>/dev/null; then
      kill -TERM -- -"$launch_pid" 2>/dev/null || kill -TERM "$launch_pid" 2>/dev/null || true
      sleep 2
      kill -9 -- -"$launch_pid" 2>/dev/null || kill -9 "$launch_pid" 2>/dev/null || true
    fi
  fi
  wait "$launch_pid" 2>/dev/null || true

  # Stop evidence recorder cleanly
  if [[ -n "${recorder_pid:-}" ]] && kill -0 "$recorder_pid" 2>/dev/null; then
    kill -INT "$recorder_pid" 2>/dev/null || true
    wait "$recorder_pid" 2>/dev/null || true
  fi

  # Stop virtual X server only AFTER gzserver and ROS launch have cleanly exited
  if [[ -n "$xvfb_pid" ]] && kill -0 "$xvfb_pid" 2>/dev/null; then
    kill "$xvfb_pid" 2>/dev/null || true
    wait "$xvfb_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM

if (( duration == 0 )); then
  printf 'Simulation running until Gazebo is closed or Ctrl+C; logs: %s/run.log
' "$results"
  wait "$launch_pid" || {
    printf 'Launch exited; see %s/run.log
' "$results" >&2
    exit 1
  }
else
  deadline=$((SECONDS + duration))
  while (( SECONDS < deadline )); do
    kill -0 "$launch_pid" 2>/dev/null || {
      printf 'Launch exited early; see %s/run.log\n' "$results" >&2
      exit 1
    }
    if [[ -f "$results/eval_summary.json" ]] && grep -q '"mission_completion_status": "SUCCESS"' "$results/eval_summary.json" 2>/dev/null; then
      printf 'Mission SUCCESS detected in evaluator! Stopping simulation cleanly...\n'
      sleep 2
      break
    fi
    sleep 1
  done
  cleanup
fi
trap - EXIT INT TERM

printf '%s
' '--- Mission states recorded ---'
if [[ -f "$results/driver_log.csv" ]]; then
  tail -n +2 "$results/driver_log.csv" | cut -d, -f2 | sort -u
fi
printf '%s
' '--- Orders summary ---'
if [[ -f "$results/delivery_orders.csv" ]]; then
  cat "$results/delivery_orders.csv"
fi

replay="$workspace/src/delivery_robot_sim/tools/replay_video.py"
if [[ -f "$replay" ]] && [[ -f "$results/driver_log.csv" ]] && [[ -f "$results/eval_log.csv" ]]; then
  python3 "$replay" --driver "$results/driver_log.csv"     --eval "$results/eval_log.csv" --out "$results/replay.gif" 2>/dev/null || true
fi

analyzer="$workspace/src/RDSim/tools/analyze_navigation_run.py"
if [[ ! -f "$analyzer" ]]; then
  analyzer="/rdsim/tools/analyze_navigation_run.py"
fi
if [[ -f "$analyzer" ]] && [[ -f "$results/eval_summary.json" ]]; then
  python3 "$analyzer" "$results" 2>/dev/null || true
fi
printf 'Results saved to: %s
' "$results"
