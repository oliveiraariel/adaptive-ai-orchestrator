# OpenClaw Gateway Research — WU-051

**Projeto:** Adaptive AI Orchestrator
**Work Unit:** WU-051
**Status:** Research consolidated and validated against the tested runtime

## Objective

Establish the concrete OpenClaw Gateway contract required by the
`AgentRuntime → OpenClawAdapter → OpenClawGatewayClient` boundary.

## Verified protocol facts

The OpenClaw Gateway uses WebSocket transport with JSON request/response
frames and Gateway RPC methods. The tested connection begins with
`connect.challenge`, followed by a `connect` request and `hello-ok`.

The tested Gateway used protocol v4.

Agent execution is asynchronous:

```text
agent
→ runId / accepted acknowledgement
→ agent.wait
→ terminal state
```

`agent.wait` is wait-only. A wait timeout does not itself cancel the run.
Cancellation uses a separate session/run operation.

The result transcript can be read through:

```text
chat.history
```

## Methods used by the validated adapter

```text
connect
agent
agent.wait
chat.history
sessions.abort
```

## Observed runtime configuration

```text
OpenClaw: 2026.7.1-2
Gateway: loopback
Port: 18789
Protocol: v4
Client id: gateway-client
Client mode: backend
Role: operator
Scopes:
  operator.read
  operator.write
```

## Model availability finding

The model catalog exposed multiple OpenAI models, but catalog presence was not
equivalent to successful execution for the tested account/runtime route.

Observed:

```text
openai/gpt-5.6-sol
→ catalogued
→ execution rejected by tested Codex/ChatGPT route

openai/gpt-5.5
→ configured as default
→ real execution successful
```

Therefore the Orchestrator must distinguish:

```text
catalog availability
runtime availability
account/provider entitlement
runtime authorization
successful execution
```

## Result retrieval finding

The final assistant answer was not taken solely from `agent.wait`.

Validated flow:

```text
agent.wait
→ terminal state

chat.history(sessionKey)
→ assistant message
→ content[type=text]
→ final output
```

`thinking` content is not promoted to result text.

## Session contract

The adapter uses:

```text
sessionKey = orchestrator:<task_id>
```

This isolates orchestration executions from the interactive main session.

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

Domain and Application must not import OpenClaw protocol schemas, WebSocket
types, SDK types or provider-specific runtime objects.

## Evidence

A real task executed through the Gateway produced:

```text
ORCHESTRATOR_GATEWAY_OK
```

with:

```text
status = ok
stopReason = stop
```

The full automated regression suite after integration reported:

```text
207 passed
```

## Research conclusion

The OpenClaw Gateway is sufficiently understood for the validated execution
path. Further research should now be driven by the next open capability:
runtime event monitoring, reconnect semantics, or durable execution/recovery.

## Sources

- https://docs.openclaw.ai/gateway/protocol
- https://docs.openclaw.ai/gateway/clients
- https://docs.openclaw.ai/concepts/agent-loop
- https://github.com/openclaw/openclaw/blob/main/packages/gateway-protocol/src/schema/frames.ts
- https://github.com/openclaw/openclaw/blob/main/packages/gateway-protocol/src/schema/agent.ts
