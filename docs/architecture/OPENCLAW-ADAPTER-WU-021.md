# OpenClaw Adapter — WU-021

Concrete adapter for the `AgentRuntime` seam.

## Design basis

The Orchestrator keeps runtime details outside the Application/Domain core.
`AgentRuntime` is the internal contract; OpenClaw is a concrete adapter.

## Responsibilities

```text
TaskPackage
→ OpenClaw payload

OpenClaw status
→ AgentRuntimeStatus

OpenClaw result
→ AgentRuntimeResult
```

The adapter also preserves an internal `ExecutionReference` so callers do
not need to understand the external execution identifier format.

## Implemented

- `OpenClawClient` external client contract;
- `OpenClawAdapter`;
- task translation;
- status normalization;
- result translation;
- cancellation translation;
- runtime ownership validation;
- adapter tests using an in-memory fake OpenClaw client.

## Important limitation

This Work Unit does not implement a real network connection to the OpenClaw
runtime. The concrete HTTP/SDK integration remains behind `OpenClawClient`
and will be introduced when the actual runtime contract is available.

This keeps the adapter testable without inventing an external API contract
that is not yet established by the project.
