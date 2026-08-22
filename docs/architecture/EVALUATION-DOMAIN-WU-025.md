# Evaluation Domain — WU-025

Initial domain representation of an evaluation result.

## Design basis

The Design defines `Evaluation` with:

```text
id
target
evaluator
criteria
evidence
findings
verdict
confidence
impact
timestamp
```

Possible verdicts include:

```text
ACCEPTED
ACCEPTED_WITH_CONDITIONS
RETURNED
BLOCKED
REJECTED
```

## Implemented

- `Evaluation`
- `EvaluationVerdict`
- identity and target invariants
- evaluator identity
- criteria/evidence/findings
- verdict
- confidence range
- impact
- timestamp
- evidence requirement for accepted verdicts
- domain tests

## Scope

This Work Unit does not implement:

- evaluation criteria resolution;
- evidence collection;
- evaluator orchestration;
- state update;
- replanning;
- persistence.

Those belong to subsequent Work Units.
