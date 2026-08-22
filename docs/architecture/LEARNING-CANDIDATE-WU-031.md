# Learning Candidate — WU-031

Initial domain representation of a possible learning derived from project
execution.

## Design basis

The Design defines `LearningCandidate` as a mechanism that prevents
experience from becoming a rule directly.

The candidate records:

```text
observation
context
evidence
scope
confidence
potentialImpact
proposedUse
validationStatus
history
```

## Implemented

- `LearningCandidate`
- `LearningValidationStatus`
- observation
- context
- evidence
- scope
- confidence
- potential impact
- proposed use
- validation status
- validation history
- controlled validation/rejection transitions
- domain tests

## Architectural intent

A LearningCandidate is not yet a rule, policy, or permanent system
knowledge.

It remains a candidate until independently validated. This preserves the
distinction between observed experience and approved project knowledge.

## Scope

This Work Unit does not implement:

- automatic learning extraction;
- promotion to policy;
- knowledge persistence;
- statistical learning;
- cross-project learning;
- model training.
