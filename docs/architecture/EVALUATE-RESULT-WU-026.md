# Evaluate Result — WU-026

Initial application use case for evaluating a normalized `ResultPackage`.

## Design basis

The Design defines the evaluation flow conceptually as:

```text
EvaluationRequest
→ CriteriaResolver
→ EvidenceResolver
→ Evaluator
→ Verdict
→ StateUpdate
```

The review recommends keeping that pipeline internal rather than exposing
each stage as a public module.

This Work Unit therefore exposes a single application operation:

```text
EvaluateResult
→ Evaluation
```

## Implemented

- `EvaluateResultRequest`
- `EvaluateResultResult`
- `EvaluateResult`
- explicit criteria input;
- evidence/result inspection;
- `EvaluationVerdict` production;
- confidence calculation;
- findings;
- application tests.

## Important limitation

The current criterion-matching rule is deliberately minimal. A criterion is
considered satisfied when it is present in the result evidence or textual
result representation.

This is a first executable slice, not the final evaluation engine.

## Scope

This Work Unit does not implement:

- sophisticated semantic evaluation;
- multiple evaluators;
- state update;
- replanning;
- persistent evaluation history;
- evaluator model selection.
