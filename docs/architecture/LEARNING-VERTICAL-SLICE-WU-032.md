# Learning Vertical Slice — WU-032

Sixth vertical slice of the Adaptive AI Orchestrator.

## Composition

```text
EvidenceRecord
    ↓
LearningCandidate
    ↓
UNDER_VALIDATION
    ↓
VALIDATED / REJECTED
```

## Proven behavior

The slice demonstrates that the Orchestrator can:

1. preserve provenance from an evidence record;
2. represent an observed pattern as a `LearningCandidate`;
3. keep the candidate explicitly unvalidated;
4. move it into controlled validation;
5. validate only when evidence exists;
6. reject a candidate without converting it into a rule.

## Architectural boundary

The slice deliberately does not promote a validated candidate into a Policy,
Skill, Model Selection rule, or permanent knowledge store.

That promotion is a separate governance concern and is not justified yet by
the current implementation scope.

## Exit criterion

The system can preserve execution-derived learning as a governed candidate
without automatically changing future orchestration behavior.
