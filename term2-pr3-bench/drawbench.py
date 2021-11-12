bench_dir = 'outbench/bench/big'
out_dir = 'outbench'

import os
import matplotlib.pyplot as plt

bench_filenames = []
for f in os.listdir(bench_dir):
    if f.endswith('.txt'):
        bench_filenames.append(f)

bench_filenames.sort()

def read_bench_result(f):
    for l in open(os.path.join(bench_dir, f)).readlines():
        if not l.startswith('median '):
            continue

        if not 'tps' in l:
            continue

        tps = float(l.split(' ')[1])
        tasks = float(l.split(' ')[4])
        allocs = float(l.split(' ')[7])
        instructions = float(l.split(' ')[11])

        return (tps, tasks, allocs, instructions)

tpss = []
taskss = []
allocss = []
instructionss = []

for f in bench_filenames:
    tps, tasks, allocs, instructions = read_bench_result(f)
    tpss.append(tps)
    taskss.append(tasks)
    allocss.append(allocs)
    instructionss.append(instructions)

x = [i for i in range(len(tpss))]

plt.plot(x, tpss, 'o--')
plt.title('TPS')
plt.xticks(x)
plt.xlabel('master +')
plt.ylabel('tps')
plt.savefig(os.path.join(out_dir, 'tps.png'))
plt.close()

plt.plot(x, instructionss, 'o--')
plt.title('Instructions')
plt.xticks(x)
plt.xlabel('master +')
plt.ylabel('instructions')
plt.savefig(os.path.join(out_dir, 'instructions.png'))
plt.close()

plt.plot(x, taskss, 'o--')
plt.title('Tasks')
plt.xticks(x)
plt.xlabel('master +')
plt.ylabel('tasks')
plt.savefig(os.path.join(out_dir, 'tasks.png'))
plt.close()

plt.plot(x, allocss, 'o--')
plt.title("Allocations")
plt.xticks(x)
plt.xlabel('master +')
plt.ylabel('allocations')
plt.savefig(os.path.join(out_dir, 'allocations.png'))
plt.close()