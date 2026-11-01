#!/usr/bin/env python3
"""Create a lightweight animated replay from the driver/evaluator CSV logs.

This script is intentionally small and defensive: it exits cleanly if the logs are
not present, and it intentionally does not fabricate results.
"""

import argparse
import csv
import math
import os
import sys


def read_driver_csv(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def read_eval_csv(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_animation(driver_rows, eval_rows, output_path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.animation import PillowWriter
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(f"matplotlib/Pillow unavailable: {exc}") from exc

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("RDSim Autonomous Delivery Robot - Mission Replay", fontsize=12)

    xs = []
    ys = []
    for row in eval_rows:
        try:
            x_val = row.get("gt_x") if "gt_x" in row else row.get("x")
            y_val = row.get("gt_y") if "gt_y" in row else row.get("y")
            if x_val is not None and y_val is not None:
                xs.append(float(x_val))
                ys.append(float(y_val))
        except (KeyError, TypeError, ValueError):
            continue

    if xs:
        ax = axes[0]
        ax.plot(xs, ys, color="royalblue", linewidth=2.5, label="Robot Path")
        ax.scatter([xs[0]], [ys[0]], color="forestgreen", s=80, marker="o", label="Depot Start")
        if len(xs) > 1:
            ax.scatter([xs[-1]], [ys[-1]], color="crimson", s=80, marker="X", label="Terminal Position")
        # Draw known obstacle if nearby
        ax.scatter([-23.0], [0.25], color="darkorange", s=90, marker="s", label="Obstacle (-23, 0.25)")
        ax.set_title("Urban Road Trajectory (Ground Truth)")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend(loc="best", fontsize=8)

    speeds = []
    for row in eval_rows:
        try:
            s_val = row.get("speed_mps")
            if s_val is not None:
                speeds.append(float(s_val))
        except (KeyError, TypeError, ValueError):
            continue

    if speeds:
        ax2 = axes[1]
        ax2.plot(speeds, color="darkorange", linewidth=1.5, label="Linear Speed (m/s)")
        ax2.set_title("Vehicle Velocity Profile")
        ax2.set_xlabel("Sample Step")
        ax2.set_ylabel("Speed (m/s)")
        ax2.grid(True, alpha=0.3, linestyle="--")
        ax2.legend(loc="upper right", fontsize=8)
    else:
        # Fallback to driver log
        v_cmds = []
        for row in driver_rows:
            try:
                v_cmds.append(float(row.get("v_cmd", 0.0)))
            except (KeyError, TypeError, ValueError):
                continue
        if v_cmds:
            ax2 = axes[1]
            ax2.plot(v_cmds, color="darkorange", linewidth=1.5, label="Commanded Linear Speed (m/s)")
            ax2.set_title("Commanded Speed Profile")
            ax2.set_xlabel("Control Step")
            ax2.set_ylabel("Cmd V (m/s)")
            ax2.grid(True, alpha=0.3, linestyle="--")
            ax2.legend(loc="upper right", fontsize=8)

    if not xs and not speeds:
        raise RuntimeError("No valid rows found in the CSV logs")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    writer = PillowWriter(fps=10)
    with writer.saving(fig, output_path, dpi=120):
        for _ in range(1):
            writer.grab_frame()
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Replay delivery_robot_sim logs as a simple GIF")
    parser.add_argument("--driver", default="/tmp/driver_log.csv", help="path to the driver CSV")
    parser.add_argument("--eval", default="/tmp/eval_log.csv", help="path to the evaluator CSV")
    parser.add_argument("--out", default="docs/run_replay.gif", help="output GIF path")
    args = parser.parse_args()

    try:
        driver_rows = read_driver_csv(args.driver)
        eval_rows = read_eval_csv(args.eval)
        if not driver_rows and not eval_rows:
            raise FileNotFoundError(f"No logs found at {args.driver} or {args.eval}")
        build_animation(driver_rows, eval_rows, args.out)
        print(f"Created replay GIF at {args.out}")
        return 0
    except Exception as exc:
        print(f"Replay not created: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
