# Delegation Vertical Slice — WU-023

Fourth vertical slice of the Adaptive AI Orchestrator.

## Composition

```text
Work Unit
+
ResourceConfiguration
+
TaskPackage
+
AgentRuntime
+
DelegateWork
    ↓
ExecutionReference
```

## Proven behavior

The slice demonstrates that the Orchestrator can:

1. accept a prepared Work Unit in an eligible state;
2. use its selected `ResourceConfiguration`;
3. submit a `TaskPackage` through the `AgentRuntime` seam;
4. receive an internal `ExecutionReference`;
5. transition the Work Unit to `RUNNING`;
6. refuse delegation when the Work Unit is not ready.

## Runtime independence

The test uses an in-memory fake runtime. The orchestration flow therefore
does not depend on an OpenClaw SDK, transport or network.

OpenClaw remains an adapter implementation behind `AgentRuntime`.

## Exit criterion

A Work Unit can cross the delegation seam and produce a normalized
execution reference without exposing runtime-specific details to the
application/domain core.
