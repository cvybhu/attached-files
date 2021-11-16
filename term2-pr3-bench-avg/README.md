# Averaged results of benchmarking term2-pr3 branch
All results are averaged over 5 runs.\
All builds are clean.

## Workloads:
* small - 1000_000
* medium - 10_000_000
* big - 100_000_000

## Command
```bash
build/release/test/perf/perf_simple_query --cpuset 1 -m 1G --operations-per-shard {workload} --task-quota-ms 10
```

## Graphs

### Big
![](graphs/big/tps.png)
![](graphs/big/instructions.png)
![](graps/big/allocations.png)
![](graphs/big/tasks.png)

### Medium

![](graphs/medium/tps.png)
![](graphs/medium/instructions.png)
![](graps/medium/allocations.png)
![](graphs/medium/tasks.png)

### Small

![](graphs/small/tps.png)
![](graphs/small/instructions.png)
![](graps/small/allocations.png)
![](graphs/small/tasks.png)
