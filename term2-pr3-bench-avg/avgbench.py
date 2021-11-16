#!/bin/python3

my_env = dict(

bench_branch = 'term2-pr3'
base_branch = 'master'

out_dir = 'outbench'

workloads = {
    'small': 1000_000,
    'medium': 10_000_000,
    'big': 100_000_000,
}

cur_workload = None
flames = False

import subprocess
import os
import time
import sys
import pprint
import json

def run(cmd):
    print(f"\n ==== Running '{cmd}'... ==== \n")
    try:
        return subprocess.check_output(cmd, shell=True, env=my_env).decode("utf-8", "ignore").strip()
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        raise

def parse_bench_results(bench_out):
    for l in bench_out.split('\n'):
        if not l.startswith('median '):
            continue

        if not 'tps' in l:
            continue

        tps = float(l.split(' ')[1])
        tasks = float(l.split(' ')[4])
        allocs = float(l.split(' ')[7])
        instructions = float(l.split(' ')[11])

        return (tps, tasks, allocs, instructions)

def do_one_bench(workload):
    ops = workloads[workload]

    start_time = time.time()
    bench_out = run(f"build/release/test/perf/perf_simple_query --cpuset 1 -m 1G --operations-per-shard {ops} --task-quota-ms 10")
    run_time = time.time() - start_time
    print(bench_out)

    tps, tasks, allocs, instructions = parse_bench_results(bench_out)

    return (tps, tasks, allocs, instructions, run_time)


def do_bench(name, commit, workload):
    tpss = []
    taskss = []
    allocss = []
    instructionss = []
    run_times = []

    n = 5
    for i in range(n):
        tps, tasks, allocs, instructions, run_time = do_one_bench(workload)
        tpss.append(tps)
        taskss.append(tasks)
        allocss.append(allocs)
        instructionss.append(instructions)
        run_times.append(run_time)

        one_res = {
            'tps': tps,
            'tasks': tasks,
            'allocations': allocs,
            'instructions': instructions,
            'run_time': run_time
        }
        one_res_text = json.dumps(one_res) + '\n'
        one_name = f'{name}_singlebench_{workload}_{commit}_{i}.txt'
        open(os.path.join(out_dir, 'avg', 'single', workload, one_name), "w").write(one_res_text)

    avg_tps = sum(tpss) / n
    avg_tasks = sum(taskss) / n
    avg_allocs = sum(allocss) / n
    avg_instructions = sum(instructionss) / n
    avg_run_time = sum(run_times) / n

    json_result = {
        'tps': avg_tps,
        'tasks': avg_tasks,
        'allocations': avg_allocs,
        'instructions': avg_instructions,
        'run_time': avg_run_time
    }
    res = json.dumps(json_result) + "\n"

    out_name = f'{name}_avgbench_{workload}_{commit}.txt'
    open(os.path.join(out_dir, 'avg', workload, out_name), "w").write(res)
    print(res)

# Script starts here
last_common = run(f"git merge-base {base_branch} {bench_branch}")
read_commits = run(f'git log {bench_branch} -1024 --format=format:"%H"').split('\n')

branch_commits = []
for c in read_commits:
    branch_commits.append(c)
    if c == last_common:
        break

# Go from the common point to the top of the bench branch
branch_commits.reverse()

print("Benchmarking commits:")
pprint.pprint(branch_commits)

#run(f"rm -rf {out_dir}")
os.makedirs(out_dir, exist_ok = True)
os.makedirs(os.path.join(out_dir, 'avg', 'small'), exist_ok = True)
os.makedirs(os.path.join(out_dir, 'avg', 'medium'), exist_ok = True)
os.makedirs(os.path.join(out_dir, 'avg', 'big'), exist_ok = True)
os.makedirs(os.path.join(out_dir, 'avg', 'single', 'small'), exist_ok = True)
os.makedirs(os.path.join(out_dir, 'avg', 'single', 'medium'), exist_ok = True)
os.makedirs(os.path.join(out_dir, 'avg', 'single', 'big'), exist_ok = True)

if not 'CCACHE_RECACHE=1' in run("env"):
    print("NO CCACHE_RECACHE=1 found!")
    exit(1)

#print(run("env"))

for i, commit in enumerate(branch_commits):
    name = f'{base_branch}_plus_{i:02d}'
    print(f"\nDoing {name}...\n")

    run(f"git checkout {commit}")
    try:
        run("ninja clean")
    except:
        pass
    
    run("ccache -c")
    run("./configure.py --mode release")
    run("ninja build/release/test/perf/perf_simple_query")

    for workload in workloads.keys():
        do_bench(name, commit, workload)
