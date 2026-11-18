---
title: "When Capacity Runs Short: Protecting Essential User Journeys"
description: "How a service can preserve critical checkout behavior by shedding lower-priority work under load."
pubDate: 2026-11-18
language: en
category: Architecture
tags:
  - availability
  - load-shedding
  - resilience
readingTime: "9 min read"
featured: true
translationKey: priority-aware-load-shedding
---
A customer already at checkout should be able to pay and see whether the order went through. During a traffic surge, I'd pause personalized recommendations before letting checkout slow to a crawl. That's the trade-off this design makes.

High availability doesn't mean keeping every feature available all the time. It means protecting essential user journeys when capacity runs short.

I'd measure checkout availability from the moment the customer opens an existing cart through payment confirmation. Two things matter at that level: how often customers finish and how long it takes. CPU utilization and per-route p95 help the service decide when to act. The checkout SLO measures what the customer experiences across the whole sequence. Google SRE describes how to pick user-facing indicators and identify critical user journeys in its [SLO chapter](https://sre.google/sre-book/service-level-objectives/) and [SRE Workbook](https://sre.google/workbook/implementing-slos/).

## Give each request the priority of the journey it serves

In this store, Essential work includes fetching the existing cart during checkout, checking price and inventory, creating the order, authorizing payment, and confirming the result. Browsing and cart changes outside checkout are Standard. Personalized recommendations are Deferrable. The product team can classify journeys by what it costs the customer and the business to interrupt them.

The same endpoint can serve more than one journey. Fetching the cart to show its contents during browsing can have a different priority from fetching it to finish checkout. A trusted gateway or backend-for-frontend (BFF) can assign the priority from the journey context and pass it downstream. Each service then decides what to admit based on its own capacity. If priority travels in a header, have the trusted component set it. Google SRE treats request criticality and latency requirements as separate concerns. Envoy's experimental filter also calls out the trust requirement for the priority header. ([Google SRE](https://sre.google/sre-book/handling-overload/), [Envoy filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/priority_load_shed_filter))

<figure>
  <img src="/images/priority-load-shedding/journey-to-admission.svg" alt="Checkout and recommendation journeys receive different priorities at a trusted gateway, then pass through service-local admission control." width="1200" height="560" loading="lazy" />
  <figcaption>Priority follows the user journey; each service applies the policy using its local capacity signals.</figcaption>
</figure>

## Watch service utilization and route latency

Measure utilization against what the service actually has available, such as its assigned CPU cores or quota. As it approaches that limit, it can reject lower-priority work first. A route can also slow down while CPU is nearly idle. Checkout might be waiting for a shared database or a downstream queue. Route p95 gives the controller a way to see that pressure. [Google SRE](https://sre.google/sre-book/handling-overload/)

With a classic Prometheus histogram, you can estimate p95 for each route over the last five minutes:

```text
histogram_quantile(
  0.95,
  sum by (route, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)
```

Grouping by route gives each route its own estimate. Prometheus interpolates within the histogram buckets. [Prometheus query functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)

Before acting on p95, require at least `N` requests in the window. Pick that floor using representative traffic. For this design, the controller checks the rolling five-minute window every minute and acts after two consecutive eligible readings exceed the route's budget. The windows overlap. The second reading checks whether the breach is still visible a minute later, with some of the same requests contributing to both readings.

<figure>
  <img src="/images/priority-load-shedding/p95-evidence-window.svg" alt="Three p95 evaluations show 97 samples below N, then a first eligible breach at 217 samples, then a second breach at 354 samples." width="1200" height="590" loading="lazy" />
  <figcaption>In this run, the sample floor delayed Essential protection until about three minutes. The windows overlap, so the second check confirms persistence rather than doubling independent samples.</figcaption>
</figure>

## Shed work that competes for the constrained resource

The CPU policy starts by limiting Deferrable work at 80% utilization. At 90%, it limits Standard work too. The service keeps admitting Essential requests as capacity allows. Both thresholds are inputs for the experiment.

The route policy can act below the CPU threshold. If checkout p95 breaches its budget and the sample and timing conditions are met, shed lower-priority work that uses the same constrained dependency. If recommendations use a different resource and the payment provider is slow, focus on the payment dependency. If the Deferrable route is the only one over its budget, limit that route locally.

<figure>
  <img src="/images/priority-load-shedding/two-pressure-signals.svg" alt="Comparison of global CPU pressure with healthy p95 and low CPU with an Essential route p95 breach." width="1200" height="660" loading="lazy" />
  <figcaption>The two triggers are independent. CPU tiers and the p95 budget shown are settings from this experiment, not production defaults.</figcaption>
</figure>

When the service sheds a recommendation request, the page can leave the panel out and let the customer continue checkout. Where a retry makes sense, cap the attempts and use exponential backoff with jitter. A circuit breaker can suspend calls to an unhealthy dependency. [AWS Well-Architected: Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel05-bp03.html)

## What happened in the VM

I changed the mockup to compare two paths. In the control, requests go straight to the service without `X-Request-Priority`; the route path labels workload for measurement, but the admission policy sees each request as unclassified. In the treatment, a local gateway overwrites any client-supplied priority and assigns one before forwarding. The p95 runs use the same seed and Essential/Standard/Deferrable mix. The gateway uses the request path as a stand-in for journey context; a production classifier would need to distinguish different journeys that share an endpoint.

For CPU pressure, each run offered 180 requests per second for 60 seconds. Without classification, the service returned all 10,800 responses, but only 21 of 1,054 Essential responses arrived within the 250 ms budget; Essential p95 was 3.47 seconds and service CPU peaked at 99.91%. Through the gateway, 1,009 of 1,053 Essential responses (95.82%) stayed within budget, with a 243.86 ms p95. The service shed 514 Standard and 3,031 Deferrable requests as CPU pressure rose. The gateway run had one client scheduling miss; its 429 responses were the intended shedding, with no other request errors. This is one synthetic run per path.

For latency pressure, a shared dependency had two slots and took 100 ms per call. At 23 requests per second for five minutes, CPU stayed below 3.4%. Without the priority header, the service hit its 512-request in-flight limit and rejected 40 of 665 Essential attempts; only 9 finished within 250 ms, and served p95 reached 25.74 seconds. The p95 detector saw the breach after about 120 seconds, but the admission policy could not select lower-priority work because the requests had no priority rank.

Through the gateway, all 665 Essential requests were served, while 1,308 Standard and 2,458 Deferrable requests were shed. The five-minute Essential p95 was still 16.99 seconds, and 345 of 665 responses (51.88%) were within budget because that whole-run measure includes slow responses from before protection activated. In a separate 60-second sample after activation, all 144 Essential responses stayed within budget and p95 was 102.83 ms. The rolling five-minute p95 remained high because its window still contained the earlier slow responses. The separate sample describes post-activation behavior; it does not replace the full-window SLO.

My first gateway p95 attempt had a 30-second upstream timeout and returned two 502 errors on Standard requests. I aligned it with the load generator's 90-second timeout and repeated the pair; that repeat had no schedule drops or other errors. These are single VM experiments, not production measurements. [Experiment setup, results, and raw JSON summaries](https://github.com/thiagoamaroalves/thiagoamaroalves.github.io/blob/main/experiments/priority-load-shedding/RESULTS.md#gateway-classification-comparison)

## Bring traffic back in stages

The recovery design waits for two healthy observations. After shedding triggered by utilization, it also waits for utilization to drop below 70%. It then restores lower-priority traffic in steps of 5%, 10%, 25%, 50%, and 100%, with two healthy observations at each step. If the service starts to degrade, the controller returns to the last stable share.

The mockup spaces probes at `x`, `2x`, `4x`, and `8x`. After four failed probes, the circuit breaker allows a small probe every `y` interval. In production, I'd add jitter and cap retry attempts so clients spread out their calls. Timeouts and a circuit breaker can limit how much time and capacity the service spends calling an unhealthy dependency. The VM test covered the overload triggers and rejection decisions. The recovery thresholds, intervals, and failure count still need testing. ([AWS retry guidance](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel05-bp03.html), [AWS timeout guidance](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel05-bp05.html))

## What I'd test before using this in checkout

The lab used one VM, one Python service, one synthetic dependency, and one run per configuration. To make a checkout availability claim, I'd repeat the tests with representative traffic, calibrate the utilization thresholds, route budgets, and sample floors, and measure successful purchases and end-to-end latency from cart to payment confirmation. A separate look at the responses after protection kicks in would show how quickly checkout latency recovers.
