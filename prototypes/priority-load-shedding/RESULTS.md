# Prototype observations

## Question

Can a gateway combine service utilization with route-specific p95 budgets, limiting lower-priority traffic to protect important routes under pressure?

## Confirmed design decisions

- Essential, Standard, and Deferrable are illustrative route classes ordered by priority.
- Reaching the 80% utilization guardrail limits Deferrable first. The 90% escalation point is still an illustrative value.
- A route-specific p95 breach can activate priority protection even below 80% utilization. In particular, an Essential route breach limits lower-priority traffic.
- Calculate p95 per route over a rolling five-minute window and evaluate it every minute. Require two consecutive breaches, with enough samples, before applying the latency policy. A longer window (for example, one hour) gives context; it is not the fast protection signal.
- Recovery requires two consecutive healthy observations. If utilization triggered shedding, utilization must also be below 70% before re-admission.
- Re-admission uses limited new traffic and ramps through illustrative shares of 5%, 10%, 25%, 50%, and 100%. Require two healthy observations at each step. If a probe degrades, roll back to the last stable share.
- Failed recovery probes use symbolic exponential waits (`x`, `2x`, `4x`, `8x`). The rehearsal enters circuit-breaker mode after four consecutive failures and then allows a limited probe every `y`. The failure count and intervals are examples, not chosen production settings.

## Simulated outcomes

| Scenario | Expected decision in the model |
| --- | --- |
| 65% utilization; all route p95 values within budget | All routes remain admitted. |
| 85% utilization; p95 values healthy | Deferrable is limited; Essential and Standard remain admitted. |
| 95% utilization; p95 values healthy | Deferrable and Standard are limited; Essential remains admitted. |
| 65% utilization; Essential p95 exceeds its budget | Under the default policy, Standard and Deferrable are limited to protect Essential. |
| Recovery probes remain healthy | New traffic is admitted in stages; each successful stage becomes the rollback point for the next. |
| A recovery probe fails | The model returns to the last stable share and lengthens the next wait. Repeated failures move it to periodic circuit-breaker probes. |

These are outputs of the prototype's explicit rules, not measured performance improvements. The model assumes that shedding lower-priority routes can help a higher-priority route's p95. A route-specific downstream bottleneck may not respond to that action.

## Still to decide

1. What minimum request count makes each route's p95 sample usable for a decision?
2. How should a p95 breach on a lower-priority route affect traffic below it: local limiting, priority protection, or another policy?
3. What workload-specific values should set `x`, the maximum backoff, `y`, and circuit-breaker entry conditions?
4. Should a 90% load escalation limit Standard traffic, or should escalation use a different signal?

All names, latency budgets, measured p95 values, traffic shares, and recovery thresholds in the mockup are illustrative. Validate them with a representative workload before treating them as operational guidance.
