# Adaptive AI Orchestrator

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

## Core Idea

The project follows a workflow similar to:

```text
PROJECT
   ↓
Context Analysis
   ↓
Structural Analysis
   ↓
Planning
   ↓
Work Units
   ↓
Agent & Skill Analysis
   ↓
Resource / Model Selection
   ↓
Delegation
   ↓
Execution
   ↓
Result Evaluation
   ↓
Replanning
   ↓
Continuity & Evidence
   ↺
```

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

The bootstrap installs/synchronizes the repositories and Python environment, installs OpenClaw when needed, configures the skill root and the `adaptive-orchestrator-bridge`, migrates Gateway authentication to a file-backed SecretRef, validates the managed Gateway, runs both integration directions end-to-end, and installs Linux Setup / Update / Verify launchers.

A fresh computer still requires the user's own interactive model-provider authentication when OpenClaw onboarding requests it; credentials are never stored in Git.

See [`bootstrap/README.md`](bootstrap/README.md) for the full recovery, update, verification, security, and dry-run contract.

## CLI entrypoint

Version 0.3 introduces a runtime-neutral inbound entrypoint. The installed command is:

```bash
adaptive-orchestrator
```

It is also available without relying on the console-script installation:

```bash
python -m adaptive_orchestrator
```

The first high-level command executes one governed Work Unit through the existing Adaptive core seams: readiness, claim ownership, execution policy, delegation, result evaluation, and finalization.

```bash
adaptive-orchestrator run \
  --objective "Respond exactly with ADAPTIVE_OK." \
  --agent main \
  --accept ADAPTIVE_OK
```

OpenClaw Gateway credentials are read from the process environment and are never printed by the CLI:

```bash
export OPENCLAW_GATEWAY_TOKEN='...'
adaptive-orchestrator doctor
```

`OPENCLAW_GATEWAY_PASSWORD` is also supported. `OPENCLAW_GATEWAY_URL` defaults to `ws://127.0.0.1:18789` when unset.

The CLI intentionally does **not** force a model/provider override by default. The selected OpenClaw agent may therefore use its configured model policy. Explicit `--model` and `--provider` options remain available for callers whose Gateway policy permits overrides.

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
OpenClaw agents / models / skills
```

The inbound path uses a thin bridge rather than turning the Adaptive engine into an OpenClaw skill:

```text
OpenClaw chat / dashboard
        ↓
thin bridge skill or tool
        ↓
adaptive-orchestrator CLI
        ↓
Adaptive core
        ↓
OpenClaw Gateway
```

The bridge is responsible only for invocation and result transport. Planning, policy, claims, evaluation, and other orchestration semantics remain owned by the Adaptive core.

See `docs/OPENCLAW-INBOUND-BRIDGE.md` for the bridge contract, security model, and validation procedure.
