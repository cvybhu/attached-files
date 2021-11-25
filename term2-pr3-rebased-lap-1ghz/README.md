# Results of benchmarking rebased term2-pr3 branch on a laptop throttled to 1GHz

## Workloads:
* small - 1000_000
* medium - 10_000_000
* big - 100_000_000 (not finished, would take too long)

## Command
```bash
build/release/test/perf/perf_simple_query --cpuset 1 -m 1G --operations-per-shard {workload} --task-quota-ms 10
```

## Graphs

### Small

![](bench/charts/small/small_tps.png)
![](bench/charts/small/small_instructions.png)
![](bench/charts/small/small_allocs.png)
![](bench/charts/small/small_tasks.png)
