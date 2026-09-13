# Adaptive AI Orchestrator

## Runtime observability

Normal CLI executions used by the OpenClaw bridge automatically publish the
allowlisted lifecycle telemetry to the shared persistent JSONL source:

`~/.local/state/adaptive-ai-orchestrator/observability.jsonl`

The location follows `${XDG_STATE_HOME}/adaptive-ai-orchestrator/observability.jsonl`
when `XDG_STATE_HOME` is set. `ADAPTIVE_OBSERVABILITY_LOG` remains an optional
development, test, or diagnostic override. No shell activation or manual export
is required for the normal bridge composition root. The sink excludes prompts,
transcripts, reasoning, raw results, credentials, and arbitrary file content.

An adaptive AI orchestration system for analyzing projects, decomposing work, coordinating agents, selecting appropriate AI models and resources, evaluating results, replanning execution, and preserving project continuity.

The **Adaptive AI Orchestrator** is a software system — not a single agent, skill, or model router — designed to provide a structured orchestration layer between developers, AI agents, skills, models, tools, and external agent runtimes.

> **Development status:** Active development  
> **Production status:** Not production-ready

---

## 🚀 Nova máquina? Comece aqui

Você **não precisa lembrar a configuração manual** do Adaptive + Ariel Agent Skills + OpenClaw.

Em uma máquina Linux Mint / Ubuntu / Debian compatível, o ponto de entrada oficial é:

```bash
curl -fsSL https://raw.githubusercontent.com/oliveiraariel/adaptive-ai-orchestrator/main/install.sh | bash
```

Se não quiser decorar nem esse comando, abra [`COMECE-AQUI-NOVA-MAQUINA.md`](COMECE-AQUI-NOVA-MAQUINA.md). A página foi criada justamente para servir como ponto permanente de recuperação a partir do GitHub.

O bootstrap instala/sincroniza os repositórios, prepara Python, OpenClaw, skills, bridge, Gateway, SecretRefs, verificações E2E e atalhos gráficos. Em uma máquina realmente nova, a única fronteira intencionalmente interativa é a autenticação pessoal do provedor/modelo quando o OpenClaw solicitar.

---

## 🧭 Iniciar projetos pelo OpenClaw

Os prompts mestres genéricos para iniciar projetos futuros estão em [`docs/prompts/`](docs/prompts/README.md).

Use:

- [`INICIAR-PROJETO-FRONTEND.md`](docs/prompts/INICIAR-PROJETO-FRONTEND.md) para frontend/web UI;
- [`INICIAR-PROJETO-BACKEND.md`](docs/prompts/INICIAR-PROJETO-BACKEND.md) para backend/engineering;
- [`CONTINUAR-PROJETO.md`](docs/prompts/CONTINUAR-PROJETO.md) para continuar uma linha de trabalho;
- [`PARAR-E-FAZER-HANDOFF.md`](docs/prompts/PARAR-E-FAZER-HANDOFF.md) para encerrar preservando continuidade.

Quando um projeto possuir governança e documentação próprias, prefira o prompt operacional específico daquele repositório.

---

## Overview

The Adaptive AI Orchestrator is designed to reason about how complex work should be organized and executed with AI.

Rather than acting as a single agent or concentrating all responsibilities into a single skill, the Orchestrator provides a coordination and decision layer capable of reasoning about:

- project context;
- requirements and constraints;
- task decomposition;
- dependencies;
- agent responsibilities;
- skill requirements;
- model and resource selection;
- execution strategies;
- cost and latency;
- result quality;
- replanning;
- continuity;
- evidence;
- historical outcomes;
- operational learning.

The developer remains the final authority over important project decisions.

---

## Adaptive Runtime Intelligence

The Orchestrator now includes a deterministic operational-diagnostics layer for
provider/model failures. It distinguishes routing from runtime health and can
classify billing, quota, authentication, timeout, provider availability and
configuration incidents; correlate quota subtypes such as project budget, TPM,
RPM and concurrency; detect credential-route mismatches, provider-catalog
shadowing and stale effective context; and apply temporary circuit-breaker
semantics without silently rewriting permanent routing policy.

The current implementation is especially explicit about OpenAI and Kimi/Moonshot
credential provenance:

- OpenAI Platform API credentials are distinct from ChatGPT/Codex OAuth access;
- Kimi Platform pay-as-you-go routes are distinct from Kimi Code membership
  routes;
- a generic HTTP 429 is treated as a symptom until stronger budget/rate evidence
  identifies the actual cause.

Sanitized incidents are recorded in
`~/.local/state/adaptive-ai-orchestrator/provider-incidents.jsonl`, while
governed troubleshooting knowledge lives in
`knowledge/provider-operational-lessons.json`.

See [`docs/runtime-intelligence.md`](docs/runtime-intelligence.md).

For model/provider/auth policy changes, use the
[policy activation runbook](docs/policy-activation-runbook.md). It separates
Adaptive worker routing from OpenClaw owner-session auth/account state and
requires an auth-order check plus smoke test before project work resumes.

The current automatic model policy is intentionally economy-first:

```text
high complexity
  -> moonshot/kimi-k2.7-code when ADAPTIVE_KIMI_ENABLED=1
  -> openai/gpt-5.6-luna primary OAuth
  -> optional secondary Luna OAuth
  -> openrouter/poolside/laguna-s-2.1:free
  -> openrouter/poolside/laguna-xs-2.1:free

medium / low complexity
  -> openai/gpt-5.6-luna primary OAuth
  -> optional secondary Luna OAuth
  -> openrouter/poolside/laguna-s-2.1:free
  -> openrouter/poolside/laguna-xs-2.1:free

manual-only premium models
  -> moonshot/kimi-k3
  -> openai/gpt-5.6-sol
```

Adaptive-routed Luna work fails closed when the configured OpenAI OAuth profile
is missing, preventing accidental fallback to a paid OpenAI Platform API key.

## Execution integrity

Field operation exposed several important distinctions that are now part of the executable contract:

- runtime completion is not semantic completion;
- `ACCEPTED_WITH_CONDITIONS` and worker-reported `PARTIAL` remain non-terminal;
- project workers emit a compact `ADAPTIVE_WORK_STATUS` / blocker / unmet-criteria footer so unfinished work cannot be silently promoted to complete;
- missing implementation or wiring that is already authorized is work, not a blocker;
- repeated unsuccessful attempts trip a bounded circuit-breaker reason instead of creating endless equivalent retries;
- long independent checklists should be decomposed into finishable, evidence-gated Work Units;
- stale persisted `RUNNING` state must be reconciled against current runtime/session evidence before redispatch.

The incident-derived rationale and cross-layer lessons are recorded in [`docs/execution-integrity-field-learning-2026-09-13.md`](docs/execution-integrity-field-learning-2026-09-13.md).

## Core Idea

The project follows a workflow similar to:

```text
PROJECT
   ↓
Context Analysis
   ↓
Structural Analysis
   ↓
Planning / Work Graph
   ↓
Ready Frontier
   ↓
Agent & Skill Analysis
   ↓
Parallel-safe Delegation
   ↓
Independent Worker Sessions
   ↓
First Completion → Evaluate → Refill Frontier
   ↓
Fan-in / Dependency Advancement
   ↓
Bounded Replanning
   ↓
Continuity & Evidence
   ↺
```

## Scalable multiagent project execution — v0.4

Version 0.4 adds the executable higher-level project loop above the earlier one-Work-Unit inbound slice.

A broad objective can now be converted into a validated acyclic Work Graph. Adaptive recomputes the ready frontier and dynamically creates independent logical worker sessions for useful ready Work Units, up to a bounded concurrency limit.

This supports lateral combinations such as:

```text
backend + backend
frontend + frontend
backend + frontend
implementation + testing/review
```

when real prerequisites and workspace safety allow them.

A stable API/interface contract can therefore unlock backend and frontend work at the same time rather than forcing the whole backend to finish first. Parallel results can converge into explicit integration/testing/review Work Units.

The scheduler is **continuously replenished**: when one worker finishes and its accepted result unlocks new work, Adaptive can fill the free slot immediately while unrelated workers from earlier dispatches continue running. Project execution is not forced through barrier-style batches.

The worker count is **not fixed**. A frontier can use 2, 3, 4, 6 or more logical workers up to the configured/policy limit, but the planner is instructed to avoid token-expensive micro-fragmentation and to use only useful independent workers.

Workers are independent runtime sessions, not automatically persisted OpenClaw agent profiles. When several workers share one checkout, filesystem writers require literal repository-relative write scopes. Missing/unsafe/overlapping scopes are rejected or serialized, including conflicts against workers already active from earlier dispatch generations. This version does not claim automatic Git-worktree/container isolation.

See [`docs/architecture/ORCHESTRATOR-AUTOMATIC-PROJECT-EXECUTION.md`](docs/architecture/ORCHESTRATOR-AUTOMATIC-PROJECT-EXECUTION.md) and [`specifications/orchestrator/ORCHESTRATOR-MULTIAGENT-REQUIREMENTS-v0.4.md`](specifications/orchestrator/ORCHESTRATOR-MULTIAGENT-REQUIREMENTS-v0.4.md) for the current project-execution contract.

## Local development

Python 3.12 or newer is required. Use an isolated virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,gateway]"
python -m pytest -q
```

Editable-install metadata is intentionally ignored by Git through `*.egg-info/`.

## Reproducible machine bootstrap

A new Debian/Ubuntu/Linux Mint machine can reconstruct the Adaptive + Ariel Agent Skills + OpenClaw environment with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/oliveiraariel/adaptive-ai-orchestrator/main/install.sh | bash
```

The bootstrap installs/synchronizes the repositories and Python environment, installs OpenClaw when needed, configures the skill root and the `adaptive-orchestrator-bridge`, migrates Gateway authentication to a file-backed SecretRef, validates the managed Gateway, runs integration checks, and installs Linux Setup / Update / Verify launchers.

A fresh computer still requires the user's own interactive model-provider authentication when OpenClaw onboarding requests it; credentials are never stored in Git.

See [`bootstrap/README.md`](bootstrap/README.md) for the full recovery, update, verification, security, and dry-run contract.

## CLI entrypoint

The installed command is:

```bash
adaptive-orchestrator
```

It is also available without relying on the console-script installation:

```bash
python -m adaptive_orchestrator
```

### Bounded single Work Unit

```bash
adaptive-orchestrator run \
  --objective "Respond exactly with ADAPTIVE_OK." \
  --agent main \
  --accept ADAPTIVE_OK
```

This path remains useful for one governed task and preserves the original readiness, claim, execution-policy, delegation, evaluation and finalization seams.

### Multiagent project mode

```bash
adaptive-orchestrator orchestrate \
  --objective "Execute the authorized project objective." \
  --agent main \
  --max-concurrency 4
```

For repository edits, explicitly grant only the required effect:

```bash
adaptive-orchestrator orchestrate \
  --objective "Implement the requested project changes." \
  --agent main \
  --allow-side-effect filesystem.write \
  --max-concurrency 4
```

Project mode provides:

- read-only AI-backed planning into strict structured data;
- graph validation and required-edge cycle rejection;
- minimum compatible skill-set resolution per Work Unit;
- dynamic ready-frontier worker creation;
- continuous free-slot replenishment after accepted completions;
- conservative shared-checkout write-scope validation/conflict control;
- dependency-result fan-in context;
- bounded retry with distinct attempt identities and human-action boundaries;
- bounded additive replanning when accepted workers discover necessary missing work;
- structured project-level execution records and dispatch generations.

A deterministic `--plan-file` can bypass AI planning for tests and E2E validation while exercising the same execution loop.

## Gateway credentials

OpenClaw Gateway credentials are read from the process environment/host secret injection and are never printed by the CLI. `OPENCLAW_GATEWAY_URL` defaults to `ws://127.0.0.1:18789` when unset.

The CLI normally leaves model/provider selection to the configured OpenClaw agent policy rather than forcing overrides.

## OpenClaw integration direction

The outbound runtime path is:

```text
Adaptive AI Orchestrator
        ↓
OpenClawAdapter
        ↓
OpenClawGatewayClient
        ↓
OpenClaw Gateway
        ↓
independent agent-owned worker sessions
```

The inbound path uses a thin bridge rather than turning the Adaptive engine into an OpenClaw skill:

```text
OpenClaw chat / dashboard
        ↓
adaptive-orchestrator-bridge
        ↓
run OR orchestrate
        ↓
Adaptive core / continuous project scheduler
        ↓
OpenClaw Gateway workers
        ↓
Adaptive evaluation / frontier refill / fan-in
        ↓
structured result
```

The bridge is responsible only for invocation and result transport. Planning, policy, claims, worker count, concurrency, continuous scheduling, fan-in, evaluation and replanning remain owned by Adaptive.

See [`docs/OPENCLAW-INBOUND-BRIDGE.md`](docs/OPENCLAW-INBOUND-BRIDGE.md) for the bridge contract, security model, and validation procedure.
### Conversation session identity

Use `--session-id` (or `ADAPTIVE_SESSION_ID`) to associate multiple bounded
executions with one conversational session. The session identifier is
observability metadata only: each execution still has its own
`orchestration_id` and emits a terminal lifecycle event when finished.
