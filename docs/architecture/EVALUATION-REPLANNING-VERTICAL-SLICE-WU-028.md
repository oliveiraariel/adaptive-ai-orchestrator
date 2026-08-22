# Evaluation + Replanning Vertical Slice — WU-028

Fifth vertical slice of the Adaptive AI Orchestrator.

## Composition

```text
ResultPackage
    ↓
EvaluateResult
    ↓
Evaluation
    ↓
ReplanProject
    ↓
PlanRevision
```

## Proven behavior

The slice demonstrates that the Orchestrator can:

1. receive a normalized execution result;
2. evaluate the result against explicit criteria;
3. produce an Evaluation verdict and evidence;
4. use that evaluation as a replanning trigger;
5. revise the current Plan into a new version;
6. preserve unaffected Work Units;
7. target the affected Work Unit;
8. add newly discovered work;
9. represent newly introduced dependencies in the revised plan.

## Important boundary

The slice intentionally does not make `EvaluateResult` automatically call
`ReplanProject`.

The Design describes the possibility of triggering replanning after
evaluation, but keeping the two operations separate preserves clear use
case boundaries and makes the integration explicit.

## Exit criterion

The system has a complete executable loop for:

```text
EXECUTE
→ RESULT
→ EVALUATE
→ REPLAN
→ NEW PLAN
```

without requiring external persistence or a real runtime.
