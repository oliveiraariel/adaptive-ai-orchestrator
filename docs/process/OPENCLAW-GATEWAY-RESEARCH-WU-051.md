# OpenClaw Gateway Research — WU-051

**Projeto:** Adaptive AI Orchestrator
**Work Unit:** WU-051
**Status:** Research consolidated

## Verified current protocol facts

The current OpenClaw documentation defines the Gateway as the external control
plane. External applications use WebSocket transport with JSON frames and RPC
methods. The first pre-connect event is `connect.challenge`; the client then
sends a `connect` request and receives `hello-ok` with the negotiated protocol
and feature metadata.

The current operator client protocol is v4. The OpenClaw guidance recommends
negotiating/pinning the protocol version used by the tested Gateway.

Agent execution is documented as:

```text
agent
→ { runId, acceptedAt }
→ agent.wait
→ terminal result
```

`agent.wait` is wait-only: a timeout does not stop the underlying agent run.
Cancellation is a separate operation. Gateway session controls expose
`sessions.abort` and related run/session operations.

## Relevant schema contracts inspected

```text
ConnectParamsSchema
AgentParamsSchema
AgentWaitParamsSchema
AgentEventSchema
```

Important `agent` inputs used by the Orchestrator adapter include:

```text
message
agentId
model
provider
sessionKey
timeout
deliver
idempotencyKey
```

The Orchestrator deliberately sends only the subset required by its internal
execution contract.

## Architecture decision

Keep:

```text
AgentRuntime
   ↓
OpenClawAdapter
   ↓
OpenClawGatewayClient
   ↓
Gateway WebSocket + RPC
```

The Domain and Application layers must not import Gateway protocol schemas,
WebSocket types or OpenClaw SDK types.

## Source policy

The implementation was aligned with current official OpenClaw documentation
and the public OpenClaw repository protocol schemas. The client is protocol-
specific and therefore must be version-pinned/revalidated when OpenClaw changes
the wire contract.

References:

- https://docs.openclaw.ai/gateway/protocol
- https://docs.openclaw.ai/gateway/clients
- https://docs.openclaw.ai/concepts/agent-loop
- https://github.com/openclaw/openclaw/blob/main/packages/gateway-protocol/src/schema/frames.ts
- https://github.com/openclaw/openclaw/blob/main/packages/gateway-protocol/src/schema/agent.ts
