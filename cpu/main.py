import copy
import csv
import os
import sys
import threading
from collections import deque

# ---------------- SETTINGS ----------------
# Usage:    python main.py [input_file] [output_folder]
# Example:  python main.py case1.csv results1
INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "case1.csv"
OUTPUT_FOLDER = sys.argv[2] if len(sys.argv) > 2 else "results1"
CONTEXT_SWITCH_TIME = 0.001   # time cost of one context switch
RR_QUANTUM = 10               # Round Robin time slice (quantum)

PRIORITY_MAP = {"high": 1, "normal": 2, "low": 3}   # lower number = higher priority
RESULT_ORDER = ["FCFS", "SJF_NP", "SJF_P", "RR", "Priority_NP", "Priority_P"]


class Process:
    def __init__(self, pid, arrival, burst, priority_text):
        self.pid = pid
        self.arrival = int(arrival)
        self.burst = int(burst)
        self.priority = PRIORITY_MAP.get(priority_text.lower(), 4)

        self.remaining = self.burst
        self.waiting = 0
        self.turnaround = 0
        self.finish_time = 0

    def finish(self, time):
        """Computes the process metrics when it finishes at the given time."""
        self.finish_time = time
        self.turnaround = time - self.arrival
        self.waiting = self.turnaround - self.burst


# ---------------- 1) READ INPUT ----------------
def read_input():
    processes = []
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip the header row
            for row in reader:
                if len(row) >= 4 and row[0].strip():
                    processes.append(Process(*(cell.strip() for cell in row[:4])))
    except FileNotFoundError:
        print(f"ERROR: '{INPUT_FILE}' not found!")
        sys.exit(1)
    except Exception as e:
        print(f"Error while reading the file: {e}")
        return []
    return processes


# ---------------- 2) REPORTING ----------------
def write_report(processes, timeline, file_name):
    n = len(processes)
    avg_waiting = sum(p.waiting for p in processes) / n
    avg_turnaround = sum(p.turnaround for p in processes) / n

    throughput = {t: sum(1 for p in processes if p.finish_time <= t)
                  for t in (50, 100, 150, 200)}

    # A context switch happens when two consecutive slices belong to different processes
    switch_count = sum(1 for i in range(1, len(timeline))
                       if timeline[i][1] != timeline[i - 1][1])

    total_work = sum(p.burst for p in processes)
    end_time = max(p.finish_time for p in processes)
    efficiency = total_work / (end_time + switch_count * CONTEXT_SWITCH_TIME)

    path = os.path.join(OUTPUT_FOLDER, file_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("a) TIMELINE (Gantt chart):\n")
        for start, pid, end in timeline:
            f.write(f"[{start}]--{pid}--[{end}]\n")
        f.write(f"\nb) Average Waiting Time: {avg_waiting:.2f}\n")
        f.write(f"c) Average Turnaround Time: {avg_turnaround:.2f}\n")
        f.write(f"d) Throughput (completed jobs by time): {throughput}\n")
        f.write(f"e) CPU Efficiency: {efficiency:.4f}\n")
        f.write(f"f) Total Context Switches: {switch_count}\n")

    return {"avg_waiting": avg_waiting,
            "avg_turnaround": avg_turnaround,
            "efficiency": efficiency}


# ---------------- 3) ALGORITHMS ----------------
def fcfs(data, results):
    processes = sorted(copy.deepcopy(data), key=lambda p: p.arrival)
    time = 0
    timeline = []

    for p in processes:
        if time < p.arrival:          # CPU is idle, wait for the process to arrive
            time = p.arrival
        start = time
        time += p.burst
        timeline.append((start, p.pid, time))
        p.finish(time)

    print("FCFS completed.")
    results["FCFS"] = write_report(processes, timeline, "FCFS.txt")


def _non_preemptive(data, key):
    """Shared logic for SJF (NP) and Priority (NP)."""
    processes = copy.deepcopy(data)
    time = 0
    done = []
    timeline = []

    while len(done) < len(processes):
        ready = [p for p in processes if p.arrival <= time and p not in done]
        if not ready:
            time += 1
            continue
        chosen = min(ready, key=key)
        start = time
        time += chosen.burst
        timeline.append((start, chosen.pid, time))
        chosen.finish(time)
        done.append(chosen)

    return done, timeline


def _preemptive(data, key):
    """Shared logic for SJF (P) and Priority (P), simulated in 1-unit steps."""
    processes = copy.deepcopy(data)
    time = 0
    finished_count = 0
    timeline = []
    previous_pid = None

    while finished_count < len(processes):
        ready = [p for p in processes if p.arrival <= time and p.remaining > 0]
        if not ready:
            time += 1
            previous_pid = None
            continue

        chosen = min(ready, key=key)
        if chosen.pid != previous_pid:
            timeline.append([time, chosen.pid, 0])
            previous_pid = chosen.pid

        chosen.remaining -= 1
        time += 1
        timeline[-1][2] = time

        if chosen.remaining == 0:
            finished_count += 1
            chosen.finish(time)
            previous_pid = None

    return processes, timeline


def sjf_np(data, results):
    processes, timeline = _non_preemptive(data, lambda p: p.burst)
    print("SJF (Non-Preemptive) completed.")
    results["SJF_NP"] = write_report(processes, timeline, "SJF_NP.txt")


def sjf_p(data, results):
    processes, timeline = _preemptive(data, lambda p: p.remaining)
    print("SJF (Preemptive) completed.")
    results["SJF_P"] = write_report(processes, timeline, "SJF_P.txt")


def priority_np(data, results):
    processes, timeline = _non_preemptive(data, lambda p: p.priority)
    print("Priority (Non-Preemptive) completed.")
    results["Priority_NP"] = write_report(processes, timeline, "Priority_NP.txt")


def priority_p(data, results):
    processes, timeline = _preemptive(data, lambda p: p.priority)
    print("Priority (Preemptive) completed.")
    results["Priority_P"] = write_report(processes, timeline, "Priority_P.txt")


def round_robin(data, results):
    processes = sorted(copy.deepcopy(data), key=lambda p: p.arrival)
    queue = deque()
    time = 0
    i = 0
    timeline = []

    def enqueue_arrivals():
        nonlocal i
        while i < len(processes) and processes[i].arrival <= time:
            queue.append(processes[i])
            i += 1

    while queue or i < len(processes):
        enqueue_arrivals()
        if not queue:                 # CPU is idle, jump to the next arrival
            time = processes[i].arrival
            continue

        p = queue.popleft()
        run_time = min(RR_QUANTUM, p.remaining)
        start = time
        time += run_time
        p.remaining -= run_time
        timeline.append((start, p.pid, time))

        enqueue_arrivals()            # processes that arrived meanwhile enter before p
        if p.remaining > 0:
            queue.append(p)
        else:
            p.finish(time)

    print("Round Robin completed.")
    results["RR"] = write_report(processes, timeline, "RoundRobin.txt")


# ---------------- 4) HTML REPORT ----------------
def create_html(results):
    rows = ""
    for algo in RESULT_ORDER:
        if algo not in results:
            continue
        r = results[algo]
        rows += (f"        <tr><td>{algo}</td><td>{r['avg_waiting']:.2f}</td>"
                 f"<td>{r['avg_turnaround']:.2f}</td><td>{r['efficiency']:.4f}</td></tr>\n")

    best = min(results, key=lambda a: results[a]["avg_waiting"])
    worst = max(results, key=lambda a: results[a]["avg_waiting"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>CPU Scheduling Report ({OUTPUT_FOLDER})</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        h1 {{ color: #333; }}
        table {{ width: 80%; border-collapse: collapse; margin-top: 20px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #ccc; padding: 12px; text-align: center; }}
        th {{ background-color: #007bff; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>CPU Scheduling Analysis ({OUTPUT_FOLDER})</h1>
    <p>Input file: {INPUT_FILE} | Round Robin quantum: {RR_QUANTUM}
       | Context switch time: {CONTEXT_SWITCH_TIME}</p>
    <h2>Algorithm Comparison</h2>
    <table>
        <thead><tr><th>Algorithm</th><th>Avg. Waiting Time</th>
        <th>Avg. Turnaround Time</th><th>CPU Efficiency</th></tr></thead>
        <tbody>
{rows}        </tbody>
    </table>
    <p>Note: Lower waiting and turnaround times and higher efficiency indicate better performance.</p>
    <h2>Summary</h2>
    <p>Based on average waiting time, the best algorithm is <b>{best}</b>
       ({results[best]['avg_waiting']:.2f}) and the worst is <b>{worst}</b>
       ({results[worst]['avg_waiting']:.2f}).</p>
</body>
</html>
"""
    file_name = f"Report_{OUTPUT_FOLDER}.html"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML report ({file_name}) created.")


# ---------------- MAIN PROGRAM ----------------
if __name__ == "__main__":
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    print(f"--- Simulation starting: input={INPUT_FILE}, output={OUTPUT_FOLDER} ---")

    data = read_input()
    if not data:
        print(f"ERROR: could not read any data from {INPUT_FILE}.")
        sys.exit(1)

    results = {}
    threads = [
        threading.Thread(target=func, args=(data, results))
        for func in (fcfs, sjf_np, sjf_p, round_robin, priority_np, priority_p)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    create_html(results)
    print(f"--- All done. Check the '{OUTPUT_FOLDER}' folder. ---")