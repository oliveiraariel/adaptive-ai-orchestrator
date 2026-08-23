# OpenClaw Gateway Integration — WU-052

**Projeto:** Adaptive AI Orchestrator
**Work Unit:** WU-052
**Status:** Implemented and validated against local fake Gateway and real OpenClaw Gateway

## Objective

Provide a concrete OpenClaw Gateway client behind the existing `AgentRuntime`
seam without coupling Domain/Application to Gateway protocol types.

## Architecture

```text
TaskPackage
   ↓
OpenClawAdapter
   ↓
OpenClawGatewayClient
   ↓
WebSocket / Gateway RPC
   ↓
OpenClaw Agent
```

## Implemented operations

```text
connect
agent
agent.wait
chat.history
sessions.abort
```

## Connection contract

Validated:

```text
protocol v4
client.id = gateway-client
client.mode = backend
role = operator
scopes = operator.read, operator.write
```

## Execution contract

```text
submit()
→ agent
→ runId

get_status()
→ agent.wait(timeoutMs=0)
→ timeout is exposed as RUNNING

retrieve_result()
→ agent.wait(...)
→ chat.history(sessionKey)
→ extract assistant text

cancel()
→ sessions.abort
```

## Result extraction

Only assistant text blocks are treated as semantic output:

```text
role = assistant
content[].type = text
```

`thinking` blocks are deliberately excluded.

## Session isolation

```text
sessionKey = orchestrator:<task_id>
```

## Verification

Automated infrastructure and vertical-slice tests cover:

```text
connect.challenge
connect / hello-ok
protocol mismatch
authentication
agent submission
agent.wait
wait timeout semantics
chat.history
assistant text extraction
sessionKey propagation
cancel
OpenClawAdapter mapping
```

The complete regression suite after integration:

```text
207 passed
```

## Real runtime validation

A real local OpenClaw Gateway was exercised with:

```text
agent: main
runtime: codex
model: openai/gpt-5.5
```

Validated output:

```text
ORCHESTRATOR_GATEWAY_OK
```

## Findings

1. Gateway client identity and mode must match the runtime's accepted schema.
2. Model overrides may be rejected by runtime policy even when a model exists
   in the catalog.
3. `agent.wait` timeout is not equivalent to run failure or cancellation.
4. `agent.wait` is not sufficient to reconstruct semantic answer text;
   transcript retrieval is required.
5. The runtime boundary remains properly isolated from Domain/Application.

## Remaining work outside WU-052

```text
runtime event monitoring
reconnect/reconciliation
durable execution/recovery
final operational acceptance
production hardening
```
