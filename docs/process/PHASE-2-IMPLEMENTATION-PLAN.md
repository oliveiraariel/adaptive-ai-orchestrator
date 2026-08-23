# Adaptive AI Orchestrator — Phase 2 Implementation Plan

**Status:** In progress
**Purpose:** evolve the verified prototype core toward durable, observable and
operational execution without breaking the existing architecture.

## Phase 2 sequence

```text
WU-038  Durable Project Persistence
   ↓
WU-039  Complete Project-State Persistence
   ↓
WU-040  Persistence Vertical Slice / Resume
   ↓
WU-041  Real OpenClaw Contract Research + Adapter Design
   ↓
WU-042  Real Runtime Integration Spike
   ↓
WU-043  Runtime Monitoring / Execution Lifecycle
   ↓
WU-044  Telemetry Port + OpenTelemetry Adapter
   ↓
WU-045  Execution Cost / Latency / Quality Accounting
   ↓
WU-046  Stronger Evaluation Engine
   ↓
WU-047  Recovery Orchestration
   ↓
WU-048  Resource Policy Hardening
   ↓
WU-049  Governed Learning Promotion
   ↓
WU-050  Operational Hardening + Final Validation
```

## Sequencing principles

### Persistence before runtime durability

The Orchestrator must first be able to preserve project state independently of
an external runtime.

### Research before real integration

The current OpenClaw documentation defines its runtime model as a local agent
runtime/harness architecture and exposes multiple execution surfaces. The
project must therefore avoid inventing an HTTP contract. A concrete integration
must begin with a compatibility spike against the actual OpenClaw installation
and supported control surface.

### Telemetry as a port

The core should emit normalized orchestration events. OpenTelemetry should be
an Infrastructure adapter, not a Domain dependency.

### Learning remains governed

Telemetry and evidence may produce Learning Candidates, but validated learning
must not silently mutate policy or selection rules.

## Phase 2 definition of done

```text
specified
+
implemented
+
verified
+
reviewed
+
traceable
+
operational evidence
```

Every WU must preserve architecture verification and the full regression suite.

## Completed in current execution

```text
WU-038  Durable Project Persistence                 ✅
WU-039  Complete Project-State Persistence          ✅
WU-040  Persistence Vertical Slice / Resume         ✅
WU-041  OpenClaw Integration Research               ✅
WU-042  OpenClaw CLI Integration Boundary           ✅
WU-044  Telemetry Port                              ✅
WU-045  Execution Cost / Latency Accounting         ✅
WU-047  Bounded Retry / Recovery                    ✅
WU-048  Resource Policy Hardening                    ✅
WU-049  Governed Learning Promotion                 ✅
WU-050  Operational Hardening                        ✅
```

`WU-043` (long-running runtime monitoring) and the direct Gateway WebSocket
adapter remain intentionally blocked on a real OpenClaw integration
environment/version. The current CLI adapter is the verified external surface
for one-shot execution.

## Final Phase 2 Gate

The phase is considered closed for all locally testable capabilities when:

```text
237 tests passed
+
PRACTICAL VALIDATION: PASS
```

The remaining live-runtime gate is external-environment dependent and is
therefore promoted to Phase 3 rather than being falsely marked complete.
