#!/usr/bin/env bash
set -euo pipefail

DURATION=${1:-50}
WORLD=${2:-small_city.world}
OUT_DIR=${3:-/home/chiheb/rdsim_ws/results/optimized_benchmark_headless}
mkdir -p "$OUT_DIR"
rm -f /home/chiheb/rdsim_ws/results/eval_log.csv /home/chiheb/rdsim_ws/results/eval_summary.json

echo "=== Starting Headless Benchmark (${DURATION}s, World: ${WORLD}, Out: ${OUT_DIR}) ==="

# 1. Start profiler in background on host
python3 /home/chiheb/Downloads/RDSim-devel-2wheel_diff/tools/system_profiler.py \
    "$DURATION" "$OUT_DIR/headless_metrics" "/home/chiheb/rdsim_ws/results/eval_log.csv" \
    > "$OUT_DIR/profiler.log" 2>&1 &
PROF_PID=$!

# 2. Measure topic publishing rates in steady-state (from t=25s to t=35s)
(
    sleep 25
    if docker ps --format '{{.Names}}' | grep -q 'rdsim_sim_container'; then
        docker exec rdsim_sim_container bash -lc "source /opt/ros/humble/setup.bash && python3 /rdsim/tools/measure_topic_rates.py 10" > "$OUT_DIR/topic_rates.txt" 2>&1 || true
    fi
) &
TOPIC_PID=$!

# 3. Run simulation in HEADLESS mode (gui=false)
cd /home/chiheb/Downloads/RDSim-devel-2wheel_diff
./run_headless_simulation.sh "$DURATION" "$WORLD" > "$OUT_DIR/sim_run.log" 2>&1 || true

# 4. Wait for profiler and topic monitor to finish
wait "$PROF_PID" 2>/dev/null || true
wait "$TOPIC_PID" 2>/dev/null || true

echo "=== Headless Benchmark Complete ==="
if [ -f "$OUT_DIR/headless_metrics.json" ]; then
    cat "$OUT_DIR/headless_metrics.json"
fi
