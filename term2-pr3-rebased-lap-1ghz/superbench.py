import json
import pprint
import os
import subprocess
import time
import matplotlib.pyplot as plt

workloads = {
    'small': 1000_000,
    'medium': 10_000_000,
    'big': 100_000_000,
}

workdir = 'superbench'
flamedir = '../FlameGraph'

# Binaries for benchmarking:
# {workdir}/bin/bench/perf_simple_query_bench_<commit>

# Binaries for flamegraph generation (-fno-omit-frame-pointer, debug symbols):
# {workdir}/bin/flame/perf_simple_query_flame_<commit>

# Individual results of benchmarks:
# {workdir}/out/bench/single/{small, medium, big}/master_plus_<xx>_bench_<workload>_<commit>_<i>.txt

# Averaged results of benchmarks:
# {workdir}/out/bench/averaged/{small, medium, big}/master_plus_<xx>_benchavg_<workload>_<commit>.txt

# Charts of benchmarks:
# {workdir}/out/bench/charts/{small, medium, big}/{{workload}_tps, ...}.png

# Generated flamegraphs
# {workdir}/out/flame/graphs/{small, medium, big}/master_plus_<xx>_flame_<workload>_commit.svg

# Generated differential flamegraphs
# {workdir}/out/flame/diffgraphs/{small, medium, big}/master_plus_<xx>_<yy>diffflame_<workload>_<commit>_<commit>.svg

# Results of flamegraph benchmark runs
# {workdir}/out/flame/results/{small, medium, big}/master_plus_<xx>_flame_<workload>_<commit>_res.txt

# Perf data collected during flamegraph benchmark runs
# {workdir}/out/flame/data/{small, medium, big}/master_plus_<xx>_flame_<workload>_<commit>_perf.data

def run(cmd):
    print(f"\n ==== Running '{cmd}'... ==== \n")
    return subprocess.check_output(["/bin/bash", "-c", cmd]).decode("utf-8", "ignore").strip()

def build_bench_binaries(branch_commits):
    run("./configure.py --mode release")
    for commit in branch_commits:
        run(f"git checkout {commit}")
        run(f"ninja build/release/test/perf/perf_simple_query")
        run(f"cp build/release/test/perf/perf_simple_query {workdir}/bin/bench/perf_simple_query_bench_{commit}")

def build_flame_binaries(branch_commits):
    run("./configure.py --mode release --cflags=-fno-omit-frame-pointer")
    for commit in branch_commits:
        run(f"git checkout {commit}")
        run(f"ninja build/release/test/perf/perf_simple_query_g")
        run(f"cp build/release/test/perf/perf_simple_query_g {workdir}/bin/flame/perf_simple_query_flame_{commit}")

def parse_bench_results(bench_out):
    for l in bench_out.split('\n'):
        if not l.startswith('median '):
            continue

        if not 'tps' in l:
            continue

        tps = float(l.split(' ')[1])
        allocs = float(l.split(' ')[4])
        tasks = float(l.split(' ')[7])
        instructions = float(l.split(' ')[11])

        return {
            'tps': tps,
            'allocs': allocs,
            'tasks': tasks,
            'instructions': instructions
        }

def run_single_benchmark(commit, workload_name, master_plus, i):
    ops = workloads[workload_name]

    start_time = time.time()
    bench_out = run(f"{workdir}/bin/bench/perf_simple_query_bench_{commit} --cpuset 1 -m 1G --task-quota-ms 10 --operations-per-shard {ops}")
    run_time = time.time() - start_time

    bench_res = parse_bench_results(bench_out)
    bench_res['run_time'] = run_time
    bench_res_str = json.dumps(bench_res) + '\n'
    out_file_name = f"{workdir}/out/bench/single/{workload_name}/master_plus_{master_plus:02d}_bench_{workload_name}_{commit}_{i}.txt"
    open(out_file_name, "w").write(bench_res_str)

    return bench_res

def run_averaged_benchmark(commit, workload_name, master_plus):
    runs_num = 5

    params = ['tps', 'allocs', 'tasks', 'instructions', 'run_time']
    avg_result = dict()
    for p in params:
        avg_result[p] = 0

    for i in range(runs_num):
        bench_res = run_single_benchmark(commit, workload_name, master_plus, i)
        for p in params:
            avg_result[p] += bench_res[p]
    
    for p in params:
        avg_result[p] /= runs_num

    bench_res_str = json.dumps(avg_result)
    out_file_name = f"{workdir}/out/bench/averaged/{workload_name}/master_plus_{master_plus:02d}_benchavg_{workload_name}_{commit}.txt"
    open(out_file_name, "w").write(bench_res_str)

def run_flame_bench(commit, workload_name, master_plus):
    ops = workloads[workload_name]
    perf_data_path = f"{workdir}/out/flame/data/{workload_name}/master_plus_{master_plus:02d}_flame_{workload_name}_{commit}_perf.data"
    bin_path = f"{workdir}/bin/flame/perf_simple_query_flame_{commit}"

    start_time = time.time()
    bench_out = run(f"perf record -F 99 -g -o {perf_data_path} -- {bin_path} --cpuset 1 -m 1G --task-quota-ms 10 --operations-per-shard {ops}")
    run_time = time.time() - start_time

    bench_res = parse_bench_results(bench_out)
    bench_res['run_time'] = run_time

    bench_res_str = json.dumps(bench_res) + '\n'
    out_file_name = f"{workdir}/out/flame/results/{workload_name}/master_plus_{master_plus:02d}_flame_{workload_name}_{commit}_res.txt"
    open(out_file_name, "w").write(bench_res_str)

def generate_single_flamegraph(commit, workload_name, master_plus):
    run(f"rm -rf {workdir}/tmp")
    os.makedirs(f"{workdir}/tmp")
    perf_data_path = f"{workdir}/out/flame/data/{workload_name}/master_plus_{master_plus:02d}_flame_{workload_name}_{commit}_perf.data"
    out_path = f"{workdir}/out/flame/graphs/{workload_name}/master_plus_{master_plus:02d}_flame_{workload_name}_{commit}.svg"

    # {workdir}/out/flame/graphs/{small, medium, big}/master_plus_<xx>_flame_<workload>_commit.svg

    run(f"perf script -i {perf_data_path} > {workdir}/tmp/out.perf")
    run(f"{flamedir}/stackcollapse-perf.pl {workdir}/tmp/out.perf > {workdir}/tmp/out.folded")
    run(f"{flamedir}/flamegraph.pl {workdir}/tmp/out.folded > {out_path}")

    run(f"rm -rf {workdir}/tmp")

def generate_differential_flamegraph(commit1, commit2, master_plus1, master_plus2, workload_name):
    run(f"rm -rf {workdir}/tmp")
    os.makedirs(f"{workdir}/tmp")
    perf_data_path1 = f"{workdir}/out/flame/data/{workload_name}/master_plus_{master_plus1:02d}_flame_{workload_name}_{commit1}_perf.data"
    perf_data_path2 = f"{workdir}/out/flame/data/{workload_name}/master_plus_{master_plus2:02d}_flame_{workload_name}_{commit2}_perf.data"
    out_path = f"{workdir}/out/flame/diffgraphs/{workload_name}/master_plus_{master_plus1:02d}_{master_plus2:02d}_diffflame_{workload_name}_{commit1}_{commit2}.svg"

    run(f"perf script -i {perf_data_path1} > {workdir}/tmp/out1.perf")
    run(f"perf script -i {perf_data_path2} > {workdir}/tmp/out2.perf")
    run(f"{flamedir}/stackcollapse-perf.pl {workdir}/tmp/out1.perf > {workdir}/tmp/out1.folded")
    run(f"{flamedir}/stackcollapse-perf.pl {workdir}/tmp/out2.perf > {workdir}/tmp/out2.folded")
    run(f"{flamedir}/difffolded.pl {workdir}/tmp/out1.folded {workdir}/tmp/out2.folded | {flamedir}/flamegraph.pl > {out_path}")

    run(f"rm -rf {workdir}/tmp")

def generate_flamegraphs(branch_commits):
    for workload_name in ['small']:#, 'medium']:
        last_commit = None
        for master_plus, commit in enumerate(branch_commits):
            generate_single_flamegraph(commit, workload_name, master_plus)

            if master_plus != 0:
                generate_differential_flamegraph(last_commit, commit, master_plus - 1, master_plus, workload_name)
            
            last_commit = commit

def generate_charts(branch_commits, workload_name):
    params = ['tps', 'allocs', 'tasks', 'instructions', 'run_time']
    single_xs = dict([(p, []) for p in params])
    single_ys = dict([(p, []) for p in params])
    avg_xs = dict([(p, []) for p in params])
    avg_ys = dict([(p, []) for p in params])

    for master_plus, commit in enumerate(branch_commits):
        for i in range(5):
            single_fname = f"{workdir}/out/bench/single/{workload_name}/master_plus_{master_plus:02d}_bench_{workload_name}_{commit}_{i}.txt"
            single_res = json.loads(open(single_fname).read())
            for p in params:
                single_xs[p].append(master_plus)
                single_ys[p].append(single_res[p])

        avg_fname = f"{workdir}/out/bench/averaged/{workload_name}/master_plus_{master_plus:02d}_benchavg_{workload_name}_{commit}.txt"
        avg_res = json.loads(open(avg_fname).read())
        for p in params:
            avg_xs[p].append(master_plus)
            avg_ys[p].append(avg_res[p])

    for p in params:
        avgs, = plt.plot(avg_xs[p], avg_ys[p], 'o--')
        avgs.set_label('mean of 5 runs')

        singles = plt.scatter(single_xs[p], single_ys[p], color='green', alpha=0.2)
        singles.set_label('single runs')

        for (x, y) in zip(avg_xs[p], avg_ys[p]):
            plt.annotate(str(x), (x, y))
        
        plt.title(p)
        plt.xlabel('commits after master')
        plt.ylabel(p)
        plt.legend()

        plt.savefig(f"{workdir}/out/bench/charts/{workload_name}/{workload_name}_{p}.png")
        plt.close()

os.makedirs(f"{workdir}/bin/bench/", exist_ok=True)
os.makedirs(f"{workdir}/bin/flame/", exist_ok=True)

for workload in workloads.keys():
    os.makedirs(f"{workdir}/out/bench/single/{workload}", exist_ok=True)
    os.makedirs(f"{workdir}/out/bench/averaged/{workload}", exist_ok=True)
    os.makedirs(f"{workdir}/out/bench/charts/{workload}", exist_ok=True)
    os.makedirs(f"{workdir}/out/flame/graphs/{workload}", exist_ok=True)
    os.makedirs(f"{workdir}/out/flame/diffgraphs/{workload}", exist_ok=True)
    os.makedirs(f"{workdir}/out/flame/data/{workload}", exist_ok=True)
    os.makedirs(f"{workdir}/out/flame/results/{workload}", exist_ok=True)


base_branch = "master"
bench_branch = "term2-pr3-based"
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
os.makedirs(workdir, exist_ok = True)

build_bench_binaries(branch_commits)
#build_flame_binaries(branch_commits)

#for workload_name in ['small']:#workloads.keys():
#    for master_plus, commit in enumerate(branch_commits):
#        run_averaged_benchmark(commit, workload_name, master_plus)
#run_flame_bench(commit, workload_name, master_plus)

for workload_name in ['small']: #, 'medium']:
    generate_charts(branch_commits, workload_name)

#generate_flamegraphs(branch_commits)
