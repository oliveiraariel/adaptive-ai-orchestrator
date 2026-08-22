# Plan Work — WU-008

Initial application use case for producing a minimal Project Plan.

## Flow

```text
load current Project baseline
→ identify Work Units
→ evaluate required dependencies
→ determine readiness
→ prioritize
→ produce Plan
```

## Implemented

- `PlanWorkRequest`
- `PlanWorkResult`
- `PlanWork` use case
- dependency-based readiness
- priority ordering
- minimal `Plan` creation
- application tests

## Intentional limits

Cycle detection and a dedicated READY/BLOCKED domain policy are not implemented here.
They remain separate concerns for subsequent Work Units.

This first version also receives the current Work Units and dependencies as input rather than introducing speculative repositories or catalogs before a real seam is required.
