# Work Unit Readiness — WU-009

Formal readiness evaluation for Work Units.

## Rule

A Work Unit is `READY` only when:

```text
state is eligible
+
no required dependency is unsatisfied
```

Otherwise it is `BLOCKED`.

## Implemented

- `ReadinessStatus`
- `WorkUnitReadiness`
- `WorkUnitReadinessEvaluator`
- single and batch evaluation
- explicit blocking-dependency evidence
- domain tests

## Integration

The readiness rule is extracted into a dedicated domain module so the
planning use case can consume one coherent domain decision instead of
reimplementing readiness rules itself.

This Work Unit does not implement graph cycle detection or plan
generation.
