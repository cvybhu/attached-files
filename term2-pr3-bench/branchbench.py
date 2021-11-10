#!/bin/python3

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

def run(cmd):
    print(f"\n ==== Running '{cmd}'... ==== \n")
    return subprocess.check_output(["/bin/bash", "-c", cmd]).decode("utf-8", "ignore").strip()

def do_bench(name, commit):
    name = f'{name}_bench_{cur_workload}_{commit}.txt'
    workload = workloads[cur_workload]

    start_time = time.time()
    bench_out = run(f"build/release/test/perf/perf_simple_query --cpuset 1 -m 1G --operations-per-shard {workload} --task-quota-ms 10")
    run_time = time.time() - start_time
    bench_out += f"\n\nTotal time: {run_time:.2f}s\n"

    open(os.path.join(out_dir, 'bench', cur_workload, name), "w").write(bench_out)

def do_flame(name_pref, commit):
    name = f'{name_pref}_flame_{cur_workload}_{commit}'
    workload = workloads[cur_workload]

    run("rm -f perf.data")

    start_time = time.time()
    bench_out = run(f"perf record -F 99 -g -o perf.data -- build/release/test/perf/perf_simple_query_g --cpuset 1 -m 1G --operations-per-shard {workload} --task-quota-ms 10")
    run_time = time.time() - start_time
    bench_out += f"\n\nTotal time: {run_time:.2f}s\n"

    run(f"perf script > out.perf")
    run(f"../FlameGraph/stackcollapse-perf.pl ../scylla/out.perf > out.folded")
    run(f"../FlameGraph/flamegraph.pl out.folded > out.svg")

    out_path = os.path.join(out_dir, 'flame', cur_workload, name)
    data_out_path = os.path.join(out_dir, 'flame', 'data', cur_workload, name)
    run(f"mv perf.data {data_out_path}_perf.data")
    run(f"mv out.perf {data_out_path}_out.perf")
    run(f"mv out.folded {data_out_path}_out.folded")
    run(f"mv out.svg {out_path}.svg")

    open(f"{out_path}.txt", "w").write(bench_out)


# Script starts here

workload_arg = sys.argv[1]
if workload_arg not in workloads:
    print("Bad workload")
    exit(1)

cur_workload = workload_arg

if len(sys.argv) >= 3:
    if sys.argv[2] != 'f':
        print("bad second arg")
        exit(1)  

    flames = True

print(f"Workload: {cur_workload} ({workloads[cur_workload]}), flames: {flames}")
time.sleep(1)

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

if flames:
    os.makedirs(os.path.join(out_dir, 'flame'), exist_ok = True)
    os.makedirs(os.path.join(out_dir, 'flame', cur_workload), exist_ok = True)
    os.makedirs(os.path.join(out_dir, 'flame', 'data'), exist_ok = True)
    os.makedirs(os.path.join(out_dir, 'flame', 'data', cur_workload), exist_ok = True)
else:
    os.makedirs(os.path.join(out_dir, 'bench'), exist_ok = True)
    os.makedirs(os.path.join(out_dir, 'bench', cur_workload), exist_ok = True)

for i, commit in enumerate(branch_commits):
    name = f'{base_branch}_plus_{i:02d}'
    print(f"\nDoing {name}...\n")

    run(f"git checkout {commit}")
    run(f"rm -rf build/{{debug,dev,release}}/abseil")

    if flames:
        run(f"./configure.py --cflags=-fno-omit-frame-pointer")
    else:
        run(f"./configure.py")

    if flames:
        run(f"ninja build/release/test/perf/perf_simple_query_g")
    else:
        run(f"ninja build/release/test/perf/perf_simple_query")

    if flames:
        do_flame(name, commit)
    else:
        do_bench(name, commit)
