# Delegate Work — WU-022

Initial application use case for delegating a prepared Work Unit to an
`AgentRuntime`.

## Flow

```text
Work Unit
→ validate readiness
→ validate TaskPackage
→ call AgentRuntime
→ receive ExecutionReference
→ transition Work Unit to RUNNING
```

## Implemented

- `DelegateWorkRequest`
- `DelegateWorkResult`
- `DelegateWork`
- precondition validation;
- TaskPackage/Work Unit consistency;
- configuration consistency;
- runtime submission;
- execution acceptance check;
- Work Unit transition to `RUNNING`;
- application tests with a fake runtime.

## Architectural intent

The use case depends only on the internal `AgentRuntime` seam. It does not
know OpenClaw API details or external execution identifiers beyond the
normalized `ExecutionReference`.

The runtime adapter remains responsible for translating the internal
contract to the concrete runtime.

## Scope

This Work Unit does not implement:

- monitoring loops;
- result retrieval orchestration;
- retry policy;
- failure recovery;
- Evaluation;
- Replanning;
- execution persistence.
