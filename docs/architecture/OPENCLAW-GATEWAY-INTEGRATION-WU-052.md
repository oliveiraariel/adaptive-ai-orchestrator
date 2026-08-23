# OpenClaw Gateway Integration — WU-052

**Projeto:** Adaptive AI Orchestrator
**Work Unit:** WU-052
**Status:** Implemented and verified against the documented protocol using a local fake Gateway

## Objective

Provide a concrete OpenClaw Gateway adapter behind the existing `AgentRuntime`
seam without coupling Domain/Application to Gateway protocol types.

## Verified protocol facts

The current OpenClaw Gateway protocol uses WebSocket text frames with JSON,
requires a first `connect` request after the `connect.challenge` event, and
currently uses operator protocol v4. External applications are directed to the
Gateway WebSocket + RPC surface for agent runs, waiting, events and cancellation.

Agent execution is initiated through `agent`, which returns a `runId`, and
terminal status is obtained through `agent.wait`. Session work can be aborted
through the Gateway session controls.

## Internal mapping

```text
TaskPackage
   ↓
OpenClawAdapter
   ↓
OpenClawGatewayClient
   ↓
WebSocket / Gateway RPC
```

External identifiers remain encapsulated by `ExecutionReference`.

## Supported methods in this slice

```text
connect
agent
agent.wait
sessions.abort
```

## Verification

The slice is verified using a local WebSocket fake Gateway that validates:

- connect handshake;
- protocol v4 negotiation;
- authentication field placement;
- agent submission;
- run identifier mapping;
- `agent.wait` normalization;
- timeout handling;
- cancellation;
- end-to-end mapping through `OpenClawAdapter`.

A live OpenClaw Gateway remains the required operational acceptance test.
