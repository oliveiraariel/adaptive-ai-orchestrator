# Agent Runtime Port — WU-020

First explicit external seam of the Orchestrator.

## Design basis

The Design identifies `AgentRuntime` as the runtime boundary and states that
the concrete implementation may be OpenClaw, Hermes, or another runtime.

The architectural review further identifies this as a real seam because the
core must remain independent from runtime implementations.

## Contract

The application seam exposes orchestration concepts:

```text
submit(TaskPackage)
→ ExecutionReference

get_status(ExecutionReference)
→ AgentRuntimeStatus

retrieve_result(ExecutionReference)
→ AgentRuntimeResult

cancel(ExecutionReference)
→ ExecutionReference
```

The contract intentionally does not mirror any runtime SDK.

## Implemented

- `AgentRuntime` protocol
- `ExecutionReference`
- `AgentRuntimeStatus`
- `AgentRuntimeResult`
- application-level seam tests with a fake adapter

## Scope

This Work Unit does not implement:

- OpenClaw integration;
- Hermes integration;
- provider SDKs;
- network transport;
- execution monitoring loops;
- result normalization rules beyond the seam shape.

Those belong to subsequent Work Units.
