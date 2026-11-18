# Priority-aware load shedding prototype

This throwaway, self-contained HTML mockup lets readers change service utilization and route-specific p95 values, inspect admission decisions, and rehearse staged recovery after load shedding. It has no dependencies, persistence, or server behavior.

## Run it

Open `index.html` directly in a browser. The guided scenarios and free-play controls work entirely in memory.

## Scope

The model compares three route classes (Essential, Standard, and Deferrable), a first utilization threshold (80% by default), a higher threshold (90%), three responses to a p95 budget breach, and an illustrative recovery sequence. The recovery rehearsal uses symbolic waits (`x`, `2x`, and so on) and example traffic shares; it does not run a clock or process real requests. Values and route names are illustrative. This prototype is for discussing policy behavior; it is not a benchmark or production control algorithm.

See [RESULTS.md](RESULTS.md) for the assumptions, simulated outcomes, and open questions.
