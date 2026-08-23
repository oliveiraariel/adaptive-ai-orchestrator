# Adaptive AI Orchestrator — Phase 3 Implementation Plan

**Status:** Local implementation complete — live runtime gate pending
**Purpose:** replace the Phase 2 external-runtime boundary with a verified
OpenClaw Gateway implementation and then close the live-runtime operational gate.

## Phase 3 sequence

```text
WU-051  Gateway protocol research                          ✅
WU-052  OpenClaw Gateway WebSocket Adapter                ✅
   ↓
WU-053  Gateway Runtime Vertical Slice                    ✅
   ↓
WU-054  Live Gateway Compatibility / Acceptance Test      ⏳
   ↓
WU-055  Runtime Event Monitoring                           ⏳
   ↓
WU-056  Durable Execution / Recovery Integration            ⏳
   ↓
WU-057  Operational Acceptance                             ⏳
```

## WU-052 — Gateway WebSocket Adapter

Implemented a concrete client behind `OpenClawClient` using the documented
Gateway WebSocket + RPC protocol.

Verified:

- protocol v4 handshake;
- operator scopes;
- authentication fields;
- `agent` submission;
- `agent.wait` terminal status;
- `sessions.abort` cancellation;
- protocol mismatch failure;
- timeout normalization;
- error propagation.

## WU-053 — Gateway Vertical Slice

Validated the complete internal path:

```text
TaskPackage
→ OpenClawAdapter
→ OpenClawGatewayClient
→ WebSocket Gateway
→ agent
→ agent.wait
→ Result
→ AgentRuntimeResult
```

The slice currently uses a local fake Gateway because a live OpenClaw instance is
not available inside the development test environment.

## WU-054 — Live Gateway Acceptance

This is the next environment-dependent gate.

Required:

```text
OpenClaw installed
+ Gateway running
+ protocol version known/pinned
+ valid agent
+ working model/provider
+ authentication configured
```

Acceptance must execute the real Gateway rather than a fake server.

## WU-055 — Runtime Event Monitoring

After live acceptance, subscribe to the `agent` event stream and normalize only
metadata required by the Orchestrator. Do not copy prompts, tool arguments or
raw sensitive content into telemetry by default.

## WU-056 — Durable Execution / Recovery Integration

Connect Gateway run identity, durable project state and recovery policy so that
restart/recovery semantics remain deterministic and do not duplicate accepted
runs.

## WU-057 — Operational Acceptance

Close the live-runtime gate with:

```text
specified
implemented
verified
reviewed
traceable
operational evidence
```

Do not mark Phase 3 complete until the real environment passes this gate.
