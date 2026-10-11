# CPU Scheduling Simulator

Simulates six CPU scheduling algorithms and compares them: FCFS, SJF (non-preemptive and preemptive), Round Robin (quantum = 10), and Priority (non-preemptive and preemptive).

## Run

Requires Python 3.6+ (no external libraries). Run once per test case:

```
python main.py case1.csv results1
python main.py case2.csv results2
```

Usage: `python main.py [input_file] [output_folder]`

## Input

A CSV file with a header row. `Priority` is `high`, `normal` or `low`.

```
Process_ID,Arrival_Time,CPU_Burst_Time,Priority
P001,0,1,high
```

## Output

- `results1/` (or the folder you chose): one `.txt` file per algorithm with the Gantt chart, average waiting time, average turnaround time, throughput, CPU efficiency and context switch count.
- `Report_results1.html`: a table comparing all algorithms. Open it in a browser.

## Settings

At the top of `main.py`: `RR_QUANTUM = 10` and `CONTEXT_SWITCH_TIME = 0.001`.

## Notes

- Context switch time is only used in the CPU efficiency formula, not in the timeline.
- The priority algorithms have no aging, so low priority processes may starve.
