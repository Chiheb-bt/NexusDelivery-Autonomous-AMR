#!/usr/bin/env python3
"""Simulation Performance Profiler & Bottleneck Diagnostic Tool (RDSim).

Measures:
- Host per-core CPU usage (Core 0, Core 1, Total)
- Process-level CPU & Memory:
  - gzserver (Gazebo physics & OGRE sensor rendering)
  - gzclient (Gazebo 3D GUI client)
  - rqt_image_view (ROS 2 GUI camera display)
  - python3 (ROS 2 autonomy nodes: city_driver_node, order_manager, evaluator)
  - Xvfb (Virtual X frame buffer if used)
- RAM usage, Available memory, Swap usage & Active Swap I/O (pswpin/pswpout)
- Docker container CPU% and Memory footprint
- Gazebo simulation time vs wall-clock time:
  - Instantaneous RTF (per-second delta)
  - Steady-State RTF (after world settling and robot spawning)
  - Moving RTF (during active robot translation)
  - Instantaneous RTF Standard Deviation (quantifying stuttering / freeze events)
- Real-world vs simulated duration and startup delay
"""

import csv
import json
import os
import subprocess
import sys
import time


def get_cpu_times():
    """Read per-core CPU times from /proc/stat."""
    core_times = {}
    with open('/proc/stat', 'r') as f:
        for line in f:
            if line.startswith('cpu'):
                parts = line.strip().split()
                name = parts[0]
                values = [float(x) for x in parts[1:]]
                idle = values[3] + values[4]  # idle + iowait
                total = sum(values)
                core_times[name] = (idle, total)
    return core_times


def get_mem_info():
    """Read RAM and Swap metrics from /proc/meminfo."""
    info = {}
    with open('/proc/meminfo', 'r') as f:
        for line in f:
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().split()[0]
                info[key] = float(val) / 1024.0  # MB
    mem_total = info.get('MemTotal', 0.0)
    mem_free = info.get('MemFree', 0.0)
    mem_avail = info.get('MemAvailable', 0.0)
    mem_used = mem_total - mem_avail
    swap_total = info.get('SwapTotal', 0.0)
    swap_free = info.get('SwapFree', 0.0)
    swap_used = swap_total - swap_free
    return {
        'mem_total_mb': round(mem_total, 1),
        'mem_used_mb': round(mem_used, 1),
        'mem_avail_mb': round(mem_avail, 1),
        'swap_total_mb': round(swap_total, 1),
        'swap_used_mb': round(swap_used, 1),
    }


def get_swap_io():
    """Read pswpin and pswpout counters from /proc/vmstat."""
    stats = {'pswpin': 0, 'pswpout': 0}
    try:
        with open('/proc/vmstat', 'r') as f:
            for line in f:
                if line.startswith('pswpin '):
                    stats['pswpin'] = int(line.split()[1])
                elif line.startswith('pswpout '):
                    stats['pswpout'] = int(line.split()[1])
    except Exception:
        pass
    return stats


def get_process_metrics():
    """Get CPU% and RSS Memory (MB) for simulation processes using ps."""
    targets = ['gzserver', 'gzclient', 'rqt_image_view', 'Xvfb', 'python3']
    proc_data = {t: {'cpu_percent': 0.0, 'rss_mb': 0.0, 'count': 0} for t in targets}
    try:
        cmd = ['ps', '-eo', 'comm,pcpu,rss,args', '--no-headers']
        out = subprocess.check_output(cmd, universal_newlines=True)
        for line in out.strip().splitlines():
            parts = line.strip().split(None, 3)
            if len(parts) >= 3:
                comm, pcpu, rss = parts[0], parts[1], parts[2]
                args = parts[3] if len(parts) > 3 else ''

                # Accurately separate rqt_image_view from autonomy python nodes
                if 'rqt_image_view' in args or 'rqt_image_view' in comm:
                    t = 'rqt_image_view'
                elif 'gzserver' in comm:
                    t = 'gzserver'
                elif 'gzclient' in comm:
                    t = 'gzclient'
                elif 'Xvfb' in comm:
                    t = 'Xvfb'
                elif 'python' in comm:
                    t = 'python3'
                else:
                    continue

                try:
                    proc_data[t]['cpu_percent'] += float(pcpu)
                    proc_data[t]['rss_mb'] += float(rss) / 1024.0
                    proc_data[t]['count'] += 1
                except ValueError:
                    pass
    except Exception:
        pass

    for t in targets:
        proc_data[t]['cpu_percent'] = round(proc_data[t]['cpu_percent'], 1)
        proc_data[t]['rss_mb'] = round(proc_data[t]['rss_mb'], 1)
    return proc_data


def get_sim_telemetry(eval_log_path):
    """Read the latest ground-truth simulation time and pose from eval_log.csv."""
    if not os.path.isfile(eval_log_path):
        return None
    try:
        with open(eval_log_path, 'r') as f:
            lines = f.readlines()
            if len(lines) > 1:
                last_line = lines[-1].strip().split(',')
                if len(last_line) >= 4:
                    return {
                        't_sim': float(last_line[0]),
                        'x': float(last_line[1]),
                        'y': float(last_line[2]),
                        'speed': float(last_line[3]),
                    }
    except Exception:
        pass
    return None


def run_profiler(duration_sec=30, output_prefix='/tmp/prof_baseline', eval_log_path='/tmp/eval_log.csv'):
    os.makedirs(os.path.dirname(output_prefix) or '.', exist_ok=True)
    csv_file = f'{output_prefix}.csv'
    json_file = f'{output_prefix}.json'

    print(f'Starting System Profiler for {duration_sec}s...')
    print(f'Logging to: {csv_file}')

    prev_core_times = get_cpu_times()
    prev_swap_io = get_swap_io()
    start_wall = time.time()
    t_prev_wall = start_wall
    t_prev_sim = None

    records = []

    header = [
        't_wall_s', 't_sim_s', 'rtf_instant', 'rtf_cumulative',
        'cpu_total_pct', 'cpu0_pct', 'cpu1_pct',
        'gzserver_cpu_pct', 'gzserver_rss_mb',
        'gzclient_cpu_pct', 'gzclient_rss_mb',
        'rqt_cpu_pct', 'rqt_rss_mb',
        'ros_python_cpu_pct', 'ros_python_rss_mb',
        'mem_used_mb', 'mem_avail_mb', 'swap_used_mb',
        'swap_in_delta', 'swap_out_delta',
        'robot_speed_mps'
    ]

    with open(csv_file, 'w') as f_csv:
        f_csv.write(','.join(header) + '\n')

        sample_idx = 0
        startup_delay = None

        while (time.time() - start_wall) < duration_sec:
            time.sleep(1.0)
            now_wall = time.time()
            wall_elapsed = now_wall - start_wall

            # Calculate CPU usage
            curr_core_times = get_cpu_times()
            cpu_pcts = {}
            for name, (curr_idle, curr_total) in curr_core_times.items():
                if name in prev_core_times:
                    prev_idle, prev_total = prev_core_times[name]
                    diff_total = curr_total - prev_total
                    diff_idle = curr_idle - prev_idle
                    if diff_total > 0:
                        cpu_pcts[name] = round(100.0 * (1.0 - diff_idle / diff_total), 1)
                    else:
                        cpu_pcts[name] = 0.0
            prev_core_times = curr_core_times

            cpu_total = cpu_pcts.get('cpu', 0.0)
            cpu0 = cpu_pcts.get('cpu0', 0.0)
            cpu1 = cpu_pcts.get('cpu1', 0.0)

            # Swap I/O deltas
            curr_swap_io = get_swap_io()
            swap_in_d = max(0, curr_swap_io['pswpin'] - prev_swap_io['pswpin'])
            swap_out_d = max(0, curr_swap_io['pswpout'] - prev_swap_io['pswpout'])
            prev_swap_io = curr_swap_io

            # Process metrics
            procs = get_process_metrics()
            mems = get_mem_info()

            # Sim telemetry
            telem = get_sim_telemetry(eval_log_path)
            t_sim = telem['t_sim'] if telem else 0.0
            speed = telem['speed'] if telem else 0.0

            if t_sim > 0.0 and startup_delay is None:
                startup_delay = round(wall_elapsed, 1)

            if t_prev_sim is not None and (now_wall - t_prev_wall) > 0.01:
                rtf_inst = max(0.0, (t_sim - t_prev_sim) / (now_wall - t_prev_wall))
            else:
                rtf_inst = 0.0

            t_prev_sim = t_sim
            t_prev_wall = now_wall

            rtf_cumul = (t_sim / wall_elapsed) if wall_elapsed > 0 and t_sim > 0 else 0.0

            row = [
                round(wall_elapsed, 2), round(t_sim, 2), round(rtf_inst, 3), round(rtf_cumul, 3),
                cpu_total, cpu0, cpu1,
                procs['gzserver']['cpu_percent'], procs['gzserver']['rss_mb'],
                procs['gzclient']['cpu_percent'], procs['gzclient']['rss_mb'],
                procs['rqt_image_view']['cpu_percent'], procs['rqt_image_view']['rss_mb'],
                procs['python3']['cpu_percent'], procs['python3']['rss_mb'],
                mems['mem_used_mb'], mems['mem_avail_mb'], mems['swap_used_mb'],
                swap_in_d, swap_out_d,
                round(speed, 3)
            ]
            f_csv.write(','.join(map(str, row)) + '\n')
            f_csv.flush()

            records.append({
                'wall_elapsed': wall_elapsed, 't_sim': t_sim, 'rtf_inst': rtf_inst,
                'cpu_total': cpu_total, 'cpu0': cpu0, 'cpu1': cpu1,
                'gzserver_cpu': procs['gzserver']['cpu_percent'],
                'gzclient_cpu': procs['gzclient']['cpu_percent'],
                'rqt_cpu': procs['rqt_image_view']['cpu_percent'],
                'python_cpu': procs['python3']['cpu_percent'],
                'mem_used_mb': mems['mem_used_mb'],
                'mem_avail_mb': mems['mem_avail_mb'],
                'swap_used_mb': mems['swap_used_mb'],
                'swap_in_d': swap_in_d,
                'swap_out_d': swap_out_d,
                'speed': speed
            })

            sample_idx += 1
            if sample_idx % 5 == 0:
                print(
                    f'[{wall_elapsed:4.1f}s] RTF_inst={rtf_inst:.2f} | CPU_tot={cpu_total:5.1f}% '
                    f'(C0={cpu0:5.1f}%, C1={cpu1:5.1f}%) | gzserver={procs["gzserver"]["cpu_percent"]:5.1f}% | '
                    f'gzclient={procs["gzclient"]["cpu_percent"]:5.1f}% | rqt={procs["rqt_image_view"]["cpu_percent"]:4.1f}% | '
                    f'py={procs["python3"]["cpu_percent"]:4.1f}% | swap={mems["swap_used_mb"]}MB (in={swap_in_d},out={swap_out_d})'
                )

    # Compute aggregate and steady-state summaries
    if records:
        overall_avg_rtf = round(sum(r['rtf_inst'] for r in records[5:]) / max(1, len(records[5:])), 3)
        
        # Steady state samples: wall > 15s and t_sim > 0
        steady_records = [r for r in records if r['wall_elapsed'] > 15.0 and r['t_sim'] > 0.0]
        if not steady_records:
            steady_records = records[10:] if len(records) > 10 else records
        
        steady_avg_rtf = round(sum(r['rtf_inst'] for r in steady_records) / max(1, len(steady_records)), 3)
        
        # Moving samples: robot_speed > 0.05
        moving_records = [r for r in steady_records if r['speed'] > 0.05]
        moving_rtfs = [r['rtf_inst'] for r in moving_records] if moving_records else [r['rtf_inst'] for r in steady_records]
        moving_avg_rtf = round(sum(moving_rtfs) / max(1, len(moving_rtfs)), 3)
        
        # Standard deviation of RTF (jitter/stuttering index)
        variance = sum((x - moving_avg_rtf) ** 2 for x in moving_rtfs) / max(1, len(moving_rtfs))
        moving_rtf_stddev = round(variance ** 0.5, 3)

        avg_cpu = round(sum(r['cpu_total'] for r in steady_records) / len(steady_records), 1)
        avg_gzserver_cpu = round(sum(r['gzserver_cpu'] for r in steady_records) / len(steady_records), 1)
        avg_gzclient_cpu = round(sum(r['gzclient_cpu'] for r in steady_records) / len(steady_records), 1)
        max_gzserver_cpu = round(max(r['gzserver_cpu'] for r in steady_records), 1)
        max_gzclient_cpu = round(max(r['gzclient_cpu'] for r in steady_records), 1)
        avg_rqt_cpu = round(sum(r['rqt_cpu'] for r in steady_records) / len(steady_records), 1)
        avg_python_cpu = round(sum(r['python_cpu'] for r in steady_records) / len(steady_records), 1)
        total_swap_in = sum(r['swap_in_d'] for r in records)
        total_swap_out = sum(r['swap_out_d'] for r in records)
        final_swap = records[-1]['swap_used_mb']
        final_mem_avail = records[-1]['mem_avail_mb']
    else:
        overall_avg_rtf = steady_avg_rtf = moving_avg_rtf = moving_rtf_stddev = 0.0
        avg_cpu = avg_gzserver_cpu = avg_gzclient_cpu = max_gzserver_cpu = max_gzclient_cpu = avg_rqt_cpu = avg_python_cpu = 0.0
        total_swap_in = total_swap_out = final_swap = final_mem_avail = 0.0

    summary = {
        'profiling_duration_wall_s': duration_sec,
        'startup_delay_wall_s': startup_delay or 0.0,
        'overall_average_rtf': overall_avg_rtf,
        'steady_state_rtf': steady_avg_rtf,
        'moving_rtf': moving_avg_rtf,
        'moving_rtf_stddev_jitter': moving_rtf_stddev,
        'steady_host_cpu_total_percent': avg_cpu,
        'steady_gzserver_cpu_percent': avg_gzserver_cpu,
        'max_gzserver_cpu_percent': max_gzserver_cpu,
        'steady_gzclient_cpu_percent': avg_gzclient_cpu,
        'max_gzclient_cpu_percent': max_gzclient_cpu,
        'steady_rqt_image_view_cpu_percent': avg_rqt_cpu,
        'steady_ros_autonomy_python_cpu_percent': avg_python_cpu,
        'swap_used_mb': final_swap,
        'total_swap_in_pages': total_swap_in,
        'total_swap_out_pages': total_swap_out,
        'mem_available_mb': final_mem_avail,
        'num_samples': len(records)
    }

    with open(json_file, 'w') as f_json:
        json.dump(summary, f_json, indent=2)

    print(f'Profiler finished. Summary saved to {json_file}:')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    pref = sys.argv[2] if len(sys.argv) > 2 else '/tmp/prof_baseline'
    eval_csv = sys.argv[3] if len(sys.argv) > 3 else '/tmp/eval_log.csv'
    run_profiler(dur, pref, eval_csv)
