# Priority-aware load-shedding experiment

This dependency-free Python lab compares requests sent directly to a service without a priority signal against requests classified by a local gateway. The service uses the gateway's `X-Request-Priority` header for admission decisions. Route names remain available for workload generation and measurement, but the service treats unclassified requests equally.

## Run the paired experiments

Copy `service.py`, `gateway.py`, `loadgen.py`, and `run_gateway_comparison.py` into a clean directory on the Ubuntu VM. The runner pins the service, generator, and gateway to separate CPU cores and writes load summaries, `/metrics` snapshots, and logs to a new results directory.

```bash
cd ~/priority-load-shedding-gateway-comparison
python3 run_gateway_comparison.py --scenario all
```

Use `--scenario cpu` or `--scenario p95` to run one comparison. The CPU pair offers 180 requests/second for 60 seconds with the existing 10/30/60 Essential/Standard/Deferrable mix. The p95 pair offers 23 requests/second for five minutes against a two-slot dependency that takes 100 ms per request. The gateway treatment then records an additional 60-second sample after protection activates. This lets the direct control fill the service's 512 in-flight limit while the Essential-only load remains below dependency capacity. Both pairs use the same route mix, random seed, and settings in the direct and gateway cases.

The p95 experiment uses a 300-second rolling window, one-minute evaluations, `MIN_SAMPLES=100`, and a 250 ms Essential budget. The gateway's upstream timeout defaults to 90 seconds to match the generator's timeout. The CPU tiers are 80% and 90%. These are lab inputs, not recommended production defaults. The load generator reports served p95, successful responses within each route budget, rejections, other errors, and client schedule drops. Keep schedule drops at zero where possible and report any misses; exclude runs with substantial client-side loss.

## What the comparison means

The control sends no priority header and the service cannot shed requests selectively. In the treatment, the gateway overwrites any client-supplied value and assigns priority from the workload route before forwarding. This isolates the value of a trusted priority signal in this mock service; it is not a benchmark of production gateways or a complete user-journey classifier.

The service pins itself to one CPU core and uses a semaphore for its simulated shared dependency. An initial CPU run was excluded because the base HTTP accept queue rejected connections before they reached the service. The lab server now uses a larger queue so the application admission policy receives the overload. The first gateway p95 attempt also exposed a shorter proxy timeout and was repeated after aligning timeouts. These single VM trials do not establish production-safe thresholds, model multiple replicas, or prove that shedding unrelated work fixes a route-local bottleneck. See [RESULTS.md](RESULTS.md) for the recorded VM results and limitations.
