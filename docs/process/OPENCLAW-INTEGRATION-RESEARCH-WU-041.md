# OpenClaw Integration Research — WU-041

## Findings

The current official OpenClaw documentation describes the Gateway as the
external control plane. External applications should communicate through the
Gateway protocol using WebSocket and RPC when they need to start agent runs,
stream events, await terminal results, cancel work or inspect resources.

For one-shot scripted use, the documented `openclaw agent` command is an
available integration surface. The command can target an agent or session,
accept a message or message file, select a model, emit JSON, and return a
process status suitable for automation.

The documented agent flow uses:

```text
agent RPC
→ { runId, acceptedAt }
→ agent.wait
→ terminal result
```

The Gateway also exposes `sessions.*` for durable session state.

## Architecture implications

1. The project must not couple the Domain to OpenClaw session objects.
2. `ExecutionReference` remains the internal execution identity.
3. The adapter owns external session/run identifiers.
4. Runtime integration must be version-pinned and revalidated when OpenClaw is
   upgraded.
5. A real WebSocket adapter should be introduced only after the actual Gateway
   environment and authentication contract are available for integration tests.

## Sources

- OpenClaw Gateway protocol
- OpenClaw external-app integration guidance
- OpenClaw agent CLI reference
- OpenClaw agent loop reference
- OpenClaw TypeBox / protocol schema guidance
