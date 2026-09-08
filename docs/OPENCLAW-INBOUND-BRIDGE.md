# OpenClaw Inbound Bridge

## Purpose

The Adaptive AI Orchestrator remains an orchestration engine, not an OpenClaw skill. OpenClaw-facing integrations therefore use a thin inbound bridge that invokes the engine through its public CLI and returns structured results.

The bridge must not duplicate planning, policy, claims, evaluation, frontier, concurrency, fan-in, or replanning logic.

## Two inbound execution modes

### Bounded single Work Unit

```text
User
  ↓
OpenClaw Dashboard / Chat
  ↓
adaptive-orchestrator-bridge
  ↓
adaptive-orchestrator run
  ↓
RunOrchestration
  ↓
ExecutionCoordinator + policy + claims
  ↓
OpenClaw Gateway / worker session
  ↓
EvaluateResult + FinalizeExecution
  ↓
JSON result
```

### High-level multiagent project execution

```text
User
  ↓
OpenClaw Dashboard / Chat
  ↓
adaptive-orchestrator-bridge --multi-agent
  ↓
adaptive-orchestrator orchestrate
  ↓
read-only RuntimeProjectPlanner
  ↓
validated Work Graph
  ↓
RunProjectOrchestration
  ↓
ready frontier
  ↓
parallel-safe synchronized worker wave
  ↓
OpenClaw Gateway → independent agent-owned sessions
  ↓
result join + evaluation + finalization
  ↓
dependency advancement / fan-in
  ↓
next frontier / bounded replan
  ↺
```

The bridge's `--multi-agent` option is a bridge-private selector. The helper removes it and invokes the public `orchestrate` CLI command.

## CLI contract — single Work Unit

```bash
adaptive-orchestrator run \
  --objective "Analyze this bounded task." \
  --agent main
```

Important options include:

- `--agent`;
- repeatable `--skill`;
- repeatable `--accept`;
- repeatable `--constraint` and `--context`;
- `--side-effect` and matching `--allow-side-effect`;
- `--human-approved` when the declared autonomy policy requires approval.

## CLI contract — multiagent project

```bash
adaptive-orchestrator orchestrate \
  --objective "Execute the authorized project objective." \
  --agent main \
  --max-concurrency 4
```

Important project-mode options include:

- `--agent` — physical OpenClaw agent/workspace owner for worker sessions;
- `--planner-agent` — optional distinct planning agent id;
- `--max-concurrency` — synchronized worker cap;
- `--max-work-units`, `--max-waves`, `--max-attempts`, `--max-replans` — bounded execution controls;
- `--skill-registry` — explicit Ariel Agent Skills registry path when automatic sibling discovery is unavailable;
- `--plan-file` — deterministic prebuilt plan for tests/E2E;
- repeatable `--context` and `--constraint`;
- `--allow-side-effect filesystem.write` when the user's request clearly authorizes repository edits;
- `--human-approved` when the autonomy class requires real prior approval.

The default side-effect policy is read-only. The planner cannot grant itself authority that the outer caller did not provide.

## Worker sessions and skills

Each ready Work Unit becomes an independent runtime execution with a unique task/session identity. Several Work Units may use the same configured OpenClaw agent id while behaving as separate logical specialists through their role, scope, selected skills, and bounded context.

Adaptive does not need to persist a new OpenClaw agent profile for every worker. Worker count is dynamic and follows the useful ready frontier.

The selected `ResourceConfiguration` is included in the worker message so the runtime agent can see the selected skills/tools and execution configuration.

## Shared checkout safety

The current OpenClaw adapter does not claim Git worktree/container isolation.

When workers share a checkout, Adaptive project mode only co-schedules write-capable Work Units when their declared repository-relative `write_paths` are non-overlapping. Unknown, broad, wildcard, parent/child, or overlapping write scopes are serialized. Read-only work remains freely parallelizable subject to the concurrency budget and policy.

## Credential handling

The CLI reads Gateway credentials only from environment variables:

- `OPENCLAW_GATEWAY_TOKEN`;
- `OPENCLAW_GATEWAY_PASSWORD`;
- `OPENCLAW_GATEWAY_URL` (optional).

Credentials must never be supplied in the objective, acceptance criteria, command output, repository files, Work Unit context, or bridge transcript.

The bridge must fail closed when the Gateway requires authentication and no usable credential is available. It must not attempt to scrape, echo, log, or persist a shared secret.

## Model and provider policy

The bridge and project orchestrator normally omit explicit model/provider overrides. The configured OpenClaw agent's model policy remains authoritative unless a deployment explicitly grants override capability.

This avoids coupling the orchestration layer to one provider and prevents a bridge from weakening Gateway authorization.

## Acceptance semantics

For a single Work Unit, a concrete machine-verifiable literal marker may be supplied with `--accept`.

For project mode, runtime completion is normally the per-worker execution gate, while semantic confidence is established through explicit testing, review, security, integration, or other verification Work Units in the graph. Runtime completion by itself is not semantic proof.

## Safety

- Planning is read-only.
- Side effects must be explicitly allowed by the outer execution policy.
- Human-only Work Units are not delegated to an agent.
- Workers cannot recursively invoke the bridge/Adaptive again.
- Replanning is bounded and additive; workers cannot silently expand their own authority.
- Concurrency is bounded and must be useful, not maximized for its own sake.

## Validation layers

1. **Domain/application tests** validate plan invariants, skill resolution, frontier waves, write-scope conflict control, fan-in, retries and replanning.
2. **CLI contract tests** validate both `run` and `orchestrate` JSON output and secret non-disclosure.
3. **Gateway protocol tests** validate Adaptive → OpenClaw RPC behavior and worker configuration transport.
4. **Deterministic multiagent E2E plan** validates multiple real OpenClaw sessions, observed parallelism and synchronization.
5. **Dashboard smoke test** validates OpenClaw chat → bridge → Adaptive project mode → OpenClaw workers → project result.

Only live layers against the actual local Gateway prove that a specific deployed machine is operational end to end.

See `docs/architecture/ORCHESTRATOR-AUTOMATIC-PROJECT-EXECUTION.md` for the full high-level execution contract.
