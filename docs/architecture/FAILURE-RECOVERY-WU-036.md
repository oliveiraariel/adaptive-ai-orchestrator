# Failure / Recovery — WU-036

Initial application boundary for classifying execution failures into bounded
recovery actions.

## Design basis

The Replanning material identifies several possible responses to failures:

```text
retry
select another model
select another agent
alter context
divide the Work Unit
replan
```

The decision must consider the cause before simply repeating the execution.

## Implemented

- `RecoveryAction`
- `RecoveryRequest`
- `RecoveryResult`
- `RecoverExecution`
- transient failure → `RETRY`
- resource/model/skill failure → `RESELECT_RESOURCE`
- dependency/requirement/scope change → `REPLAN`
- unknown failure → `ESCALATE`
- non-failed execution → `STOP`
- application tests

## Architectural intent

This Work Unit classifies the failure and identifies the next bounded
direction. It does not itself perform retry, resource reselection, or
replanning.

Those are separate use cases and should remain independently testable.

## Scope

This first recovery slice does not implement:

- retry counters;
- backoff;
- circuit breakers;
- automatic agent switching;
- context mutation;
- Work Unit decomposition;
- human notification;
- persistence of recovery history.

Those are later hardening concerns.
