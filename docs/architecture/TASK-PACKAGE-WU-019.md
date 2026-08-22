# Task Package — WU-019

Initial domain representation of the package handed to an execution agent.

## Design basis

The Design defines `TaskPackage` with:

```text
taskId
workUnitId
objective
scope
context
inputs
artifacts
decisions
dependencies
constraints
configuration
expectedOutput
acceptanceCriteria
```

`TaskPackage` transmits context and contract. It does not contain the
business rules of the agent execution itself.

## Implemented

- `TaskPackage`
- execution identity
- Work Unit reference
- objective and scope
- context and inputs
- artifacts and decisions
- dependencies and constraints
- `ResourceConfiguration`
- expected outputs
- acceptance criteria
- domain invariants
- domain tests

## Scope

This Work Unit does not execute the task, call a runtime, monitor execution,
or build a ResultPackage.

Those concerns belong to later Work Units.
