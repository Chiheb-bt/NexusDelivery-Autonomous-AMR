#!/usr/bin/env python3
"""Analysis and reporting script for navigation diagnostics and acceptance criteria.

Reads:
- driver_log.csv
- eval_log.csv
- eval_summary.json
- delivery_orders.json

Outputs:
- navigation_diagnostic_report.json
- trajectory_plot.png
"""
import csv
import json
import math
import os
import sys

def analyze(results_dir: str):
    eval_summary_file = os.path.join(results_dir, "eval_summary.json")
    eval_log_file = os.path.join(results_dir, "eval_log.csv")
    driver_log_file = os.path.join(results_dir, "driver_log.csv")
    orders_file = os.path.join(results_dir, "delivery_orders.json")

    print(f"Analyzing simulation logs in {results_dir}...")

    # Load eval_summary
    eval_summary = {}
    if os.path.exists(eval_summary_file):
        with open(eval_summary_file) as f:
            eval_summary = json.load(f)

    # Load eval_log
    eval_rows = []
    if os.path.exists(eval_log_file):
        with open(eval_log_file) as f:
            reader = csv.DictReader(f)
            eval_rows = list(reader)

    # Load driver_log
    driver_rows = []
    if os.path.exists(driver_log_file):
        with open(driver_log_file) as f:
            reader = csv.DictReader(f)
            driver_rows = list(reader)

    # Load orders
    orders_data = {}
    if os.path.exists(orders_file):
        with open(orders_file) as f:
            orders_data = json.load(f)

    if not eval_rows or not driver_rows:
        print("ERROR: Incomplete logs found.")
        return

    # 1. Poses and Distances
    initial_gt = (float(eval_rows[0]['gt_x']), float(eval_rows[0]['gt_y']))
    final_gt = (float(eval_rows[-1]['gt_x']), float(eval_rows[-1]['gt_y']))

    total_dist = eval_summary.get("total_distance_travelled_m", 0.0)
    if not total_dist and eval_rows:
        total_dist = 0.0
        for i in range(1, len(eval_rows)):
            dx = float(eval_rows[i]['gt_x']) - float(eval_rows[i-1]['gt_x'])
            dy = float(eval_rows[i]['gt_y']) - float(eval_rows[i-1]['gt_y'])
            total_dist += math.hypot(dx, dy)

    # 2. Collisions and clearance
    min_clearance = eval_summary.get("minimum_obstacle_clearance_m", 999.0)
    collision_count = eval_summary.get("collision_count", 0)

    # 3. Waypoint and mission state progression
    states_seen = set()
    targets_seen = []
    rotations_in_place_count = 0
    circling_detected = False
    progress_stalls = 0
    safety_interventions = {}

    consecutive_circling_frames = 0
    prev_state = None
    for r in driver_rows:
        st = r.get('state', 'UNKNOWN')
        states_seen.add(st)
        tgt = r.get('target_name', '')
        if not targets_seen or targets_seen[-1] != tgt:
            targets_seen.append(tgt)

        # Check for in-place alignment
        if st == 'ALIGNING_HEADING' and prev_state != 'ALIGNING_HEADING':
            rotations_in_place_count += 1

        # Check for indefinite circling (|w_cmd| > 0.4 and v_cmd > 0.2 for > 3s continuous)
        w_cmd = abs(float(r.get('w_cmd', 0.0)))
        v_cmd = float(r.get('v_cmd', 0.0))
        if w_cmd > 0.40 and v_cmd > 0.20:
            consecutive_circling_frames += 1
            if consecutive_circling_frames >= 60:
                circling_detected = True
        else:
            consecutive_circling_frames = 0

        # Safety supervisor reasons
        saf_rsn = r.get('stop_reason', 'NONE')
        if saf_rsn not in ('NONE', 'DEPOT_WAIT', 'ARRIVED_DELIVERY', 'ARRIVED_PARK'):
            safety_interventions[saf_rsn] = safety_interventions.get(saf_rsn, 0) + 1

        prev_state = st

    # 4. Target vs measured velocities
    v_cmds = [float(r['v_cmd']) for r in driver_rows if 'v_cmd' in r]
    w_cmds = [float(r['w_cmd']) for r in driver_rows if 'w_cmd' in r]
    v_acts = [float(r['actual_v']) for r in driver_rows if 'actual_v' in r] if 'actual_v' in driver_rows[0] else [float(r['speed_mps']) for r in eval_rows]

    report = {
        "mission_status": eval_summary.get("mission_completion_status", "UNKNOWN"),
        "returned_to_depot": eval_summary.get("returned_to_depot", False),
        "orders_completed": eval_summary.get("orders_completed", 0),
        "initial_pose_gt": initial_gt,
        "final_pose_gt": final_gt,
        "distance_travelled_m": round(total_dist, 2),
        "minimum_obstacle_clearance_m": min_clearance,
        "collision_count": collision_count,
        "states_visited": sorted(list(states_seen)),
        "targets_sequence": targets_seen,
        "rotations_in_place_count": rotations_in_place_count,
        "circling_detected": circling_detected,
        "avg_cmd_v": round(sum(v_cmds) / len(v_cmds), 3) if v_cmds else 0.0,
        "max_cmd_v": round(max(v_cmds), 3) if v_cmds else 0.0,
        "avg_measured_v": round(sum(v_acts) / len(v_acts), 3) if v_acts else 0.0,
        "max_measured_v": round(max(v_acts), 3) if v_acts else 0.0,
        "safety_interventions": safety_interventions,
        "duration_s": eval_summary.get("mission_duration_s", float(eval_rows[-1]['t_sim']) if eval_rows else 0.0)
    }

    report_path = os.path.join(results_dir, "navigation_diagnostic_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*60)
    print("  NAVIGATION DIAGNOSTIC & ACCEPTANCE CRITERIA REPORT")
    print("="*60)
    print(f"Mission Status:          {report['mission_status']}")
    print(f"Returned to Depot:       {report['returned_to_depot']}")
    print(f"Orders Completed:        {report['orders_completed']}/2")
    print(f"Initial Pose (GT):       x={initial_gt[0]:.2f}, y={initial_gt[1]:.2f}")
    print(f"Final Pose (GT):         x={final_gt[0]:.2f}, y={final_gt[1]:.2f}")
    print(f"Total Distance:          {report['distance_travelled_m']:.2f} m")
    print(f"Min Obstacle Clearance:  {report['minimum_obstacle_clearance_m']:.3f} m")
    print(f"Collision Count:         {report['collision_count']}")
    print(f"In-Place Rotations:      {report['rotations_in_place_count']}")
    print(f"Circling Detected:       {report['circling_detected']}")
    print(f"Max Measured Velocity:   {report['max_measured_v']:.2f} m/s")
    print(f"Safety Interventions:    {report['safety_interventions']}")
    print("="*60 + "\n")

    # Generate Trajectory Plot if matplotlib available
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        xs = [float(r['gt_x']) for r in eval_rows]
        ys = [float(r['gt_y']) for r in eval_rows]

        plt.figure(figsize=(10, 8), dpi=150)
        plt.plot(xs, ys, 'b-', linewidth=2.0, label='Robot Trajectory (GT)')
        plt.plot(initial_gt[0], initial_gt[1], 'go', markersize=10, label='Start (Depot: -30, 0)')
        plt.plot(-15.0, 15.0, 'rs', markersize=9, label='Client 1 (-15, 15)')
        plt.plot(-15.0, 28.0, 'ms', markersize=9, label='Client 2 (-15, 28)')
        plt.plot(-23.0, 0.25, 'kX', markersize=12, label='Obstacle (-23, 0.25)')

        plt.axhline(0.0, color='gray', linestyle='--', alpha=0.5, label='road_x_2 Center')
        plt.axvline(-15.0, color='gray', linestyle=':', alpha=0.5, label='North Avenue Center')

        plt.title('Autonomous Delivery Trajectory - Urban Mission', fontsize=14, fontweight='bold')
        plt.xlabel('X (meters)', fontsize=12)
        plt.ylabel('Y (meters)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend(loc='lower left', fontsize=9)
        plt.tight_layout()

        plot_path = os.path.join(results_dir, "trajectory_plot.png")
        plt.savefig(plot_path)
        print(f"Trajectory plot saved to: {plot_path}")
    except Exception as e:
        print(f"Plot generation skipped: {e}")

if __name__ == "__main__":
    res_dir = sys.argv[1] if len(sys.argv) > 1 else "/home/chiheb/rdsim_ws/results"
    analyze(res_dir)
