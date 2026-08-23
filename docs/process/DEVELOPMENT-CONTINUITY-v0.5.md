# Development Continuity — Adaptive AI Orchestrator

**Version:** 0.5
**Status:** Phase 2 complete for testable scope; real OpenClaw integration pending environment gate.

## Current state

The prototype core is implemented and verified.

Phase 2 added:

```text
Durable Project State
→ Resume
→ OpenClaw CLI boundary
→ Telemetry
→ Cost/Latency accounting
→ Bounded recovery
→ Resource policy
→ Governed learning promotion
→ CI / packaging hardening
```

## Verification

Current working implementation snapshot:

```text
237 tests passed
Practical validation: PASS
```

## Important architectural decisions

- Domain remains independent of infrastructure technologies.
- Repository ports are internal contracts; persistence is Infrastructure.
- SQLite is the first durable adapter, not the permanent storage decision.
- OpenClaw is integrated first through its documented CLI surface.
- A future direct Gateway adapter must use the current Gateway WebSocket/RPC
  protocol and a pinned OpenClaw version.
- Telemetry is normalized internally and mapped to OpenTelemetry at the edge.
- Retry is bounded and separate from replan/reselection decisions.
- Policies are enforced before execution.
- Learning promotion is approval-gated and never mutates policy silently.

## Current gate

The only material gate that cannot be closed from the current environment is
real OpenClaw integration validation.

Required user-side environment:

```text
OpenClaw installed
Gateway available
known version
configured agent
usable model/provider
authentication
```

## Next implementation sequence

```text
WU-051  OpenClaw Gateway compatibility spike
WU-052  Gateway WebSocket transport
WU-053  agent + agent.wait integration
WU-054  live monitoring / events
WU-055  real runtime end-to-end
WU-056  operational acceptance
```

After the live runtime gate, reassess whether additional provider, persistence,
security or scaling work is justified by actual requirements rather than
assumed future needs.
