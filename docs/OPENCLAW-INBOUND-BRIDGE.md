# OpenClaw Inbound Bridge

## Purpose

The Adaptive AI Orchestrator remains an orchestration engine, not an OpenClaw skill. OpenClaw-facing integrations must therefore use a thin inbound bridge that invokes the engine through its public CLI and returns structured results.

The bridge must not duplicate planning, policy, claims, evaluation, frontier, or replanning logic.

## Architecture

```text
User
  ↓
OpenClaw Dashboard / Chat
  ↓
OpenClaw bridge skill/tool
  ↓
adaptive-orchestrator run
  ↓
RunOrchestration
  ↓
ExecutionCoordinator + policy + claims
  ↓
OpenClawAdapter
  ↓
OpenClawGatewayClient
  ↓
OpenClaw Gateway
  ↓
agent
  ↓
result
  ↓
EvaluateResult + FinalizeExecution
  ↓
JSON result returned to bridge
```

## CLI contract

The bridge invokes either:

```bash
adaptive-orchestrator run ...
```

or, when using the repository-local editable environment:

```bash
.venv/bin/python -m adaptive_orchestrator run ...
```

Required input:

- `--objective`

Important optional inputs:

- `--agent` (defaults to `main`)
- `--skill` (repeatable)
- `--accept` (repeatable)
- `--constraint` (repeatable)
- `--context` (repeatable)
- `--side-effect` and matching `--allow-side-effect`
- `--human-approved` when the declared autonomy policy requires approval

The CLI prints exactly one JSON object on successful completion. Errors are emitted as JSON to stderr and return a non-zero exit status.

## Credential handling

The CLI reads Gateway credentials only from environment variables:

- `OPENCLAW_GATEWAY_TOKEN`
- `OPENCLAW_GATEWAY_PASSWORD`
- `OPENCLAW_GATEWAY_URL` (optional)

Credentials must never be supplied in the objective, acceptance criteria, command output, repository files, or bridge transcript.

The bridge must fail closed when the Gateway requires authentication and no usable credential is available. It must not attempt to scrape, echo, log, or persist a shared secret.

## Model and provider policy

The bridge should normally omit explicit model/provider overrides. The OpenClaw agent's configured model policy is therefore authoritative unless a deployment explicitly grants model/provider override capability.

This avoids coupling the inbound bridge to OpenClaw policy and prevents the bridge from weakening Gateway authorization.

## Acceptance semantics

When no explicit `--accept` criterion is supplied, the runner uses `runtime-completed`. This proves successful runtime completion only; it is not a semantic guarantee that the user's objective was correct.

When the caller has a concrete machine-verifiable acceptance marker, pass it explicitly with `--accept`.

## Safety

The default execution policy authorizes no side effects. A side effect must be both requested and explicitly allowed. Human-approval-required work must also carry `--human-approved` after real approval has been obtained.

The bridge must not infer approval from the existence of a chat message.

## Validation layers

1. **Unit/application tests** validate the governed `RunOrchestration` path.
2. **CLI contract tests** validate JSON output and secret non-disclosure.
3. **Gateway protocol tests** validate Adaptive → OpenClaw RPC behavior.
4. **Live smoke test** validates the deployed machine's real Gateway, agent ownership, authentication, and result retrieval.
5. **Dashboard smoke test** validates OpenClaw chat → bridge → Adaptive → OpenClaw → result.

Only layers 4 and 5 prove a specific local OpenClaw installation is operational end-to-end.
