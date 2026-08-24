# Adaptive AI Orchestrator — Project Context

**Purpose:** root entry point for humans and AI agents resuming or inspecting the project.

**Status:** Phase 3 in progress — real OpenClaw Gateway compatibility validated; next Work Unit: `WU-055 — Runtime Event Monitoring`.

## 1. Project Identity

The current project is the **Adaptive AI Orchestrator**.

The earlier **Professional Software Engineering Skill** is valuable legacy methodological knowledge, but it is **not** the normative identity or source of truth of the Adaptive AI Orchestrator.

Legacy knowledge may only influence the current project after explicit compatibility analysis and governed adoption.

## 2. Authority Rules

Interpret every artifact according to its role.

### Normative intent

Use this precedence when determining intended behavior:

1. `specifications/orchestrator/PROJECT-DEFINITION.md`
2. `specifications/orchestrator/ORCHESTRATOR-REQUIREMENTS.md`
3. `docs/architecture/ORCHESTRATOR-SYSTEM-ARCHITECTURE.md`
4. `docs/architecture/ORCHESTRATOR-SYSTEM-DESIGN.md`
5. `docs/process/ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md`
6. approved reviews / decisions applicable to the topic
7. implementation plans / Work Units
8. source code
9. tests / operational evidence

Specification remains normative for intended behavior. Code and tests are implementation/evidence and must not silently redefine the specification.

### Operational state

For current execution status, prefer the newest applicable operational evidence:

1. this `CONTEXT.md`
2. `docs/process/ORCHESTRATOR-NEW-CHAT-CONTEXT.md`
3. `docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md`
4. current phase implementation plan
5. current gate report
6. Work Unit implementation/evidence records
7. historical continuity snapshots

If operational documents disagree, do not silently choose one. Compare version, scope, date, authority, and supporting evidence.

## 3. Current State

Validated:

- Fase 1 — Core implementation: complete.
- Fase 2 — Operational evolution: complete for its validated scope.
- `WU-051` — Gateway protocol research: complete.
- `WU-052` — OpenClaw Gateway WebSocket adapter: complete.
- `WU-053` — Gateway runtime vertical slice: complete.
- `WU-054` — Real Gateway compatibility: complete for the tested local path.
- Real OpenClaw Gateway compatibility: **PASS** for the tested path.
- Historical regression evidence for the Gateway validation snapshot: `207 passed`.
- Historical real result: `ORCHESTRATOR_GATEWAY_OK`.

Open:

- `WU-055` — Runtime Event Monitoring.
- `WU-056` — Durable Execution / Recovery Integration.
- `WU-057` — Operational Acceptance.
- production observability / security / deployment hardening.

The project is **not production-ready**.

Operational numbers, Git state, runtime versions, models and test counts are snapshots. Revalidate them in the active clone before declaring them current.

## 4. Mandatory Resume Order

When resuming development, read:

1. `CONTEXT.md`
2. `docs/process/ORCHESTRATOR-NEW-CHAT-CONTEXT.md`
3. `docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md`
4. `PROJECT-KNOWLEDGE-MANIFEST.yaml`
5. `docs/architecture/ORCHESTRATOR-SYSTEM-ARCHITECTURE.md`
6. `docs/architecture/ORCHESTRATOR-SYSTEM-DESIGN.md`
7. `docs/process/ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md`
8. `docs/process/PHASE-3-IMPLEMENTATION-PLAN.md`
9. `docs/process/PHASE-3-GATE-REPORT.md`
10. `docs/process/OPENCLAW-GATEWAY-RESEARCH-WU-051.md`
11. `docs/architecture/OPENCLAW-GATEWAY-INTEGRATION-WU-052.md`

Read additional artifacts only when the task requires them.

Do not load the entire repository or all historical material by default.

## 5. Legacy Knowledge Rule

The following are **legacy/non-authoritative by default**:

- `specifications/MASTER-SPECIFICATION.md`
- `specifications/MASTER-SPECIFICATION-v0.2.md`
- `specifications/MASTER-SPECIFICATION-v0.3.md`
- `docs/process/history/skill/**`

Rules:

- retain them;
- do not delete them merely because they are legacy;
- do not use them as current Orchestrator authority;
- do not include them in default OpenClaw retrieval;
- consult them only for explicit legacy analysis, provenance, or compatibility review;
- promote useful concepts only through the current project's SDD/governance process.

## 6. OpenClaw Boundary

OpenClaw is an external runtime / agentic execution environment.

The Adaptive AI Orchestrator core remains authoritative for its own:

- project state;
- planning and plan mutation;
- Work Unit/dependency semantics;
- resource-selection policies;
- authorization/governance;
- evaluation decisions;
- durable recovery;
- evidence and governed learning.

OpenClaw may read project knowledge, execute bounded work and provide operational evidence, but it must not silently redefine the project specification or mutate authoritative project knowledge without an explicit approved workflow.

## 7. Generated / Local Noise

Do not treat these as project knowledge:

- `.venv/**`
- `.pytest_cache/**`
- `**/__pycache__/**`
- `**/*.pyc`

## 8. Change Discipline

Relevant changes follow:

```text
discovery
→ evidence
→ impact analysis
→ decision
→ update the correct specification/design/process artifact
→ implementation when required
→ verification
→ evidence
→ continuity update
→ versioning
```

Do not convert experience, a prompt, a Skill, runtime behavior or legacy guidance directly into project authority.
