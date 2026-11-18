# Priority-aware load-shedding experiment

This dependency-free service turns the article proposal into a repeatable lab experiment. It models three request priorities and a shared, capacity-limited downstream dependency. On the Ubuntu VM, the service pins itself to the first available CPU core; pin the load generator to another core so its work does not inflate the service CPU signal. Use a VM with at least two vCPUs.

## What this experiment can show

- A service can shed Deferrable traffic when its process CPU reaches a configured load tier, even while route p95 values remain healthy.
- A shared downstream queue can push Essential p95 over budget while service CPU is below the load tier; the p95 policy can then shed lower-priority traffic.
- The same policy may not help a route-local bottleneck. This experiment models shared dependency contention; it is not a production system or a general performance claim.

The service pins itself to one available CPU core and reports its process CPU as a percentage of that one-core budget. Its shared dependency uses a semaphore and configurable service time. These are explicit simulation boundaries, not a full microservice architecture. The recovery ramp is represented in the HTML mockup; this service experiment focuses on overload triggers and priority decisions.

## Run the service on the VM

Copy `service.py` and `loadgen.py` to `~/priority-load-shedding-lab/` on the VM. `MIN_SAMPLES` must be selected for each experiment; the program has no universal default.

```bash
cd ~/priority-load-shedding-lab
MIN_SAMPLES=100 SHEDDING_MODE=load python3 service.py
```

Useful settings include `SHEDDING_MODE` (`none`, `load`, `p95`, `combined`), `MIN_SAMPLES`, `DEPENDENCY_CONCURRENCY`, `DEPENDENCY_WORK_MS`, `P95_WINDOW_SECONDS`, `P95_EVAL_SECONDS`, and `CPU_WORK_<ROUTE>_MS`. The default p95 window is 300 seconds and evaluation interval is 60 seconds. The 80% and 90% CPU tiers are experiment inputs; 90% is illustrative.

## Generate traffic on a separate core

Run this from another VM terminal. The service uses the first available core; the example pins the generator to core 1.

```bash
cd ~/priority-load-shedding-lab
taskset -c 1 python3 loadgen.py \
  --base-url http://127.0.0.1:8080 \
  --rate 140 --duration 60 \
  --weights essential:10,standard:30,deferrable:60 \
  --max-workers 512 \
  --output cpu-load.json
```

The accepted runs and measured outputs are in [RESULTS.md](RESULTS.md) and `results/`. An earlier Windows-host pilot missed its target arrival rate, so it is retained but marked invalid in the results record.

For a p95-trigger run, allow enough time to collect `MIN_SAMPLES` and observe two consecutive one-minute evaluations. The five-minute window is rolling from startup, not a mandatory five-minute warmup. Use a constrained shared dependency, for example `DEPENDENCY_CONCURRENCY=2` and `DEPENDENCY_WORK_MS=100`, and a rate just above its 20 requests/second service capacity. Set `SHEDDING_MODE=p95` and `CPU_WORK_ESSENTIAL_MS=0` (and likewise for the other routes) to isolate the latency trigger. Check `/metrics` during and after each run.

## Compare runs

Use the same route weights, arrival rate, duration, and service settings for each comparison. Run `SHEDDING_MODE=none` against `load` for CPU pressure, and `none` against `p95` for shared-dependency latency. Save each load-generator summary and `/metrics` snapshots. Record the VM configuration, environment values, p95 by route, successful responses, shed counts, other errors, and service CPU. Repeat each mode before drawing conclusions.

## Limits

The result describes this single-VM, synthetic workload only. It does not establish safe production thresholds, model multiple replicas, or prove that shedding unrelated traffic fixes a route-specific dependency failure. See [RESULTS.md](RESULTS.md) for the experiment record.
