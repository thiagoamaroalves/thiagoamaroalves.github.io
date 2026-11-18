# VM experiment results

## Outcome

The paired comparison shows the design difference in this synthetic service: without a trusted priority signal, the service cannot select lower-priority work to reject first; with a gateway classification, it can preserve Essential responses while shedding Standard and Deferrable work. CPU pressure and a slow shared dependency exercised the resource and p95 triggers separately. These are exploratory VM runs, not production guidance.

## Environment and method

- Ubuntu 26.04.1 VM, 4 vCPUs, 7.2 GiB RAM, Python 3.14.4.
- Service pinned itself to CPU 0; constant-arrival load generator ran on CPU 1 with `taskset`.
- The paired gateway runs used the route mix Essential/Standard/Deferrable = 10/30/60 and `MAX_IN_FLIGHT=512`. The repeated p95 pair had zero client schedule drops; the CPU gateway run had one miss out of 10,800 scheduled arrivals, which is reported below.
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

## Gateway classification comparison

The paired comparison tests what the earlier route-aware runs did not: whether the service can protect an Essential request when it receives no trusted priority. The direct control sends requests without `X-Request-Priority`; the route path is retained for workload and measurement only. The treatment sends traffic through a local gateway that overwrites any client-supplied value. Both use the same seed and 10/30/60 route mix. The gateway classification is a lab stand-in for journey context; a real gateway must account for endpoints used by more than one journey.

### CPU pressure

Each run offered 180 requests/second for 60 seconds. The service ran on CPU 0, the generator on CPU 1, and the gateway on CPU 2.

| Path | Essential within 250 ms | Essential served p95 | Standard shed | Deferrable shed | Peak service CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct, no priority header | 21 / 1,054 (1.99%) | 3,470.16 ms | 0 | 0 | 99.91% |
| Through priority gateway | 1,009 / 1,053 (95.82%) | 243.86 ms | 514 | 3,031 | 95.67% |

There were no unexpected request errors. The direct run had no shedding; the gateway's 429 responses are the intentional resource-based shedding shown in the table. The gateway run had one client scheduling miss out of 10,800 planned arrivals; the direct run had none. The results are from one run per path. Raw summaries and CPU monitors are in [`gateway-comparison-final`](results/gateway-comparison-final/).

### Shared-dependency p95 pressure

Each run offered 23 requests/second for 300 seconds against a two-slot dependency taking 100 ms per call. Service CPU stayed below 3.4%. With no priority header, the service reached its 512-request in-flight limit and rejected 40 of 665 Essential attempts; only 9 completed within 250 ms. Essential served p95 was 25,739.85 ms. The detector recorded a p95 breach around 120 seconds, but unclassified requests had no priority rank for the admission policy to use.

Through the gateway, all 665 Essential requests were served and none rejected. Across the full five-minute run, 345 were within 250 ms (51.88%) and Essential served p95 was 16,985.01 ms; the controller shed 1,308 Standard and 2,458 Deferrable requests. Protection activated at about 120 seconds. A separate 60-second sample afterward served all 144 Essential attempts within budget, with p95 102.83 ms; all 450 Standard and 786 Deferrable attempts in that sample were shed. The service's rolling five-minute p95 still read about 16.9 seconds after the sample because it retained slow responses from before activation. The separate sample measures post-activation responses; it does not replace the full-window SLO.

The first gateway p95 attempt used a 30-second upstream timeout and returned two 502 errors on Standard requests. That attempt is excluded from the figures above. I aligned the gateway timeout with the load generator's 90-second timeout and repeated the pair; the repeat had zero client schedule drops and zero other errors. Raw data and per-second monitors are in [`p95-gateway-comparison-repeat`](results/p95-gateway-comparison-repeat/).

## Invalid pilot and limits

The earlier Windows-host pilot in [cpu-none-pilot.json](results/cpu-none-pilot.json) is excluded: it scheduled 140 requests/second but dropped 2,837 arrivals. The accepted runs use a generator pinned to a separate VM core. An initial CPU repeat that exposed the operating-system accept queue before service admission is also excluded from the gateway comparison; the corrected server uses a larger HTTP backlog.

This is one Python process, one VM, and one simulated dependency. Results do not establish safe thresholds, cover multiple replicas, or prove how a real database/network bottleneck behaves. Repeat under varied workloads before drawing broader conclusions.
