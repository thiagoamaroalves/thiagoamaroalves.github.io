# Prototype observations

## Question

Can a gateway combine a service utilization threshold with route-specific p95 budgets, while limiting lower-priority traffic before essential traffic?

## Assumptions in this mockup

- `Essential`, `Standard`, and `Deferrable` are generic route classes, not names from a real service.
- The first utilization threshold is 80%, based on the scenario described. A second threshold at 90% is an illustrative escalation point that can be changed in the prototype.
- Each route has its own p95 budget and observed p95 value. All latency values are synthetic.
- The default latency policy protects the highest-priority route with a p95 breach by limiting lower-priority routes. A route-local policy and a warning-only policy are also available for comparison.
- Load thresholds and p95 policy decisions are combined; if both would limit the same route, the page shows both reasons.

## Simulated outcomes

| Scenario | Expected decision in the model |
| --- | --- |
| 65% utilization; every route within its p95 budget | All routes remain admitted. |
| 85% utilization; p95 values healthy | Deferrable is limited; Essential and Standard remain admitted. |
| 95% utilization; p95 values healthy | Deferrable and Standard are limited; Essential remains admitted. |
| 65% utilization; Essential p95 exceeds its budget | Under the default policy, Standard and Deferrable are limited to protect Essential. |
| 65% utilization; only Deferrable p95 exceeds its budget | Deferrable is limited; Essential and Standard remain admitted. |
| 65% utilization; Standard p95 exceeds its budget | Under the default policy, Deferrable is limited; Essential and Standard remain admitted. |

These are outputs of the prototype's explicit rules, not measured performance improvements. In particular, the model assumes that shedding lower-priority routes can help a higher-priority route's p95. A route-specific downstream bottleneck may not respond to that action.

## Confirmed policy decision

The author confirmed this behavior during prototype review: when the Essential route's p95 exceeds its budget, limit lower-priority routes to protect it even when overall utilization is below 80%. Route priority is the policy; p95 is a route-specific signal that can activate it independently of the utilization guardrail.

This confirms the desired decision rule, not a measured latency improvement. The effect on real p95 still needs evidence from an actual workload.

## Questions to settle together

1. When a route's own p95 is over budget, should the system limit that route, preserve it by shedding lower-priority traffic, or choose based on its priority?
2. Should the second utilization threshold at 90% shed Standard traffic, or should escalation depend on a different signal?
3. What observation window and minimum request count make a route p95 stable enough to drive admission decisions?

The next version should change only after these rules match the service behavior we want to describe. No production conclusion is recorded yet.
