# VM experiment results

## Outcome

The two triggers behaved as designed in this synthetic service: CPU pressure shed lower priorities first, while a shared dependency could breach route p95 with service CPU below 2%. The runs are single exploratory trials, not production guidance.

## Environment and method

- Ubuntu 26.04.1 VM, 4 vCPUs, 7.2 GiB RAM, Python 3.14.4.
- Service pinned itself to CPU 0; constant-arrival load generator ran on CPU 1 with `taskset`.
- All runs used the route mix Essential/Standard/Deferrable = 10/30/60, `MAX_IN_FLIGHT=512`, and zero client schedule drops in the accepted runs.
- For p95 runs: dependency capacity 2, 100 ms per call, 300-second rolling window, 60-second evaluations, and `MIN_SAMPLES=100`. These are lab settings, not universal values.

## CPU pressure

The CPU comparison used 140 offered requests/second for 60 seconds, a shared dependency capacity of 64, and the route CPU costs in the service defaults (2/4/8 ms).

| Mode | Essential served / p95 | Standard served / shed | Deferrable served / shed | CPU observation |
| --- | --- | --- | --- | --- |
| No shedding | 825 / 18.68 ms | 2,619 / 0 | 4,956 / 0 | 89.51% in an in-run snapshot; route p95s were below their configured budgets. |
| CPU shedding | 825 / 13.34 ms | 2,137 / 482 | 2,478 / 2,478 | An in-run snapshot read 83.04%; resource-based rejection counts show both configured tiers were exercised. |

All 8,400 scheduled requests completed in each run without client schedule drops or other errors. Essential had no rejections in either run. Its observed client p95 was about 29% lower with shedding, but this is one run per mode and should be treated as directional only. Full summaries: [baseline](results/baseline-none-140rps.json) and [CPU shedding](results/load-mode-140rps.json).

## Shared-dependency latency

The p95 comparison offered 21 requests/second against an illustrative shared-dependency capacity of 20 requests/second, with CPU work disabled.

| Mode | Duration | Essential served / p95 | Standard shed | Deferrable shed | CPU observation |
| --- | --- | --- | --- | --- | --- |
| No shedding | 180 s | 378 / 9,470.74 ms | 0 | 0 | Below 2% in sampled snapshots. |
| p95 shedding | 240 s | 499 / 5,219.89 ms | 490 | 1,655 | About 1.4% when Essential became protected. |

Without shedding, all 3,780 requests were served even though Essential p95 exceeded its 250 ms budget by a wide margin. With p95 shedding, Essential remained un-rejected while lower priorities were limited. At the first evaluation Essential had 97 samples, below `MIN_SAMPLES`; after two eligible consecutive breach checks (at roughly 180 seconds), it became protected. Before that, the controller had already limited Deferrable after Standard's p95 breach. The check windows overlap, so consecutive checks indicate persistence rather than independent samples. Full summaries: [baseline](results/p95-baseline-none-21rps.json) and [p95 shedding](results/p95-policy-21rps.json).

The p95 summaries include slow Essential responses from before the policy activated. This run validates the trigger and priority decision, not rapid p95 recovery. The service also does not implement the staged recovery ramp shown in the conceptual mockup.

## Invalid pilot and limits

The earlier Windows-host pilot in [cpu-none-pilot.json](results/cpu-none-pilot.json) is excluded: it scheduled 140 requests/second but dropped 2,837 arrivals. The accepted runs use a generator pinned to a separate VM core.

This is one Python process, one VM, and one simulated dependency. Results do not establish safe thresholds, cover multiple replicas, or prove how a real database/network bottleneck behaves. Repeat under varied workloads before drawing broader conclusions.
