# Adaptive AI Orchestrator — Project Context

**Purpose:** root entry point for humans and AI agents resuming or inspecting the project.

**Status:** Phase 3 in progress — continuous bounded multiagent project execution v0.4 is repository-validated; the installed OpenClaw multiagent E2E remains pending; next official Work Unit: `WU-055 — Runtime Event Monitoring`.

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
3. `specifications/orchestrator/ORCHESTRATOR-MULTIAGENT-REQUIREMENTS-v0.4.md`
4. `docs/architecture/ORCHESTRATOR-SYSTEM-ARCHITECTURE.md`
5. `docs/architecture/ORCHESTRATOR-SYSTEM-DESIGN.md`
6. `docs/process/ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md`
7. approved reviews / decisions applicable to the topic
8. implementation plans / Work Units
9. source code
10. tests / operational evidence

Specification remains normative for intended behavior. Code and tests are implementation/evidence and must not silently redefine the specification.

### Operational state

For current execution status, prefer the newest applicable operational evidence:

1. this `CONTEXT.md`
2. `docs/process/MULTIAGENT-PROJECT-EXECUTION-v0.4-GATE.md`
3. `docs/process/ORCHESTRATOR-NEW-CHAT-CONTEXT-v0.8.md`
4. `docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY-v0.8.md`
5. `PROJECT-KNOWLEDGE-MANIFEST.yaml`
6. current phase implementation plan and gate
7. Work Unit implementation/evidence records
8. v0.7 and older continuity snapshots

The unversioned `ORCHESTRATOR-NEW-CHAT-CONTEXT.md` and `ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md` describe the pre-v0.4 operational snapshot. Retain them for provenance, but do not let them override the v0.8 continuity or v0.4 gate when describing current state.

If operational documents disagree, do not silently choose one. Compare version, scope, date, authority, supersession and supporting evidence.

## 3. Current State

Validated:

- Phase 1 — Core implementation: complete.
- Phase 2 — Operational evolution: complete for its validated scope.
- `WU-051` — Gateway protocol research: complete.
- `WU-052` — OpenClaw Gateway WebSocket adapter: complete.
- `WU-053` — Gateway runtime vertical slice: complete.
- `WU-054` — Real Gateway compatibility: complete for the tested local path.
- Real OpenClaw Gateway compatibility: **PASS** for the tested historical local path.
- Continuous bounded multiagent project orchestration v0.4: **IMPLEMENTED AND REPOSITORY-VALIDATED**.
- Project-level entrypoint: `adaptive-orchestrator orchestrate`.
- Dynamic Ready Frontier, continuous slot replenishment, accepted-result dependency advancement, bounded retries/replanning and fan-in are implemented for the v0.4 scope.
- Parallel backend/backend, frontend/frontend and backend/frontend execution is allowed when the Work Graph, policy and write/runtime safety permit it.
- Automated evidence includes six independent Work Units with `max_concurrency=6` and a test proving a newly unlocked Work Unit starts before an unrelated long-running worker finishes.
- Fail-closed merged CI evidence for v0.4: **284 tests passed**; Orchestrator Validation and Bootstrap Validation passed.
- Ariel Agent Skills multiagent integration validation passed on its merged `main`.

Still required before claiming the user's installed stack has passed the new multiagent path:

- `adaptive-openclaw-update`;
- `adaptive-openclaw-verify --e2e` on the installed Linux/OpenClaw environment.

Open roadmap:

- `WU-055` — Runtime Event Monitoring.
- `WU-056` — Durable Execution / Recovery Integration.
- `WU-057` — Operational Acceptance.
- managed-worktree/runtime isolation integration for stronger parallel-writer isolation;
- production observability / security / deployment hardening.

The project is **not production-ready**.

Operational numbers, Git state, runtime versions, models and test counts are snapshots. Revalidate them in the active clone before declaring them current.

## 4. Multiagent Execution Boundary

The v0.4 project path is:

```text
broad objective
→ governed planning
→ validated Work Graph
→ dynamic Ready Frontier
→ smallest useful compatible worker set
→ bounded parallel dispatch
→ first result returned
→ evaluation/finalization
→ dependency advancement
→ frontier recomputation
→ newly unlocked worker may fill a free slot while unrelated workers remain active
→ fan-in / bounded replan as needed
```

`max_concurrency` is a ceiling, not a target. Economicity of tokens/context and meaningful decomposition take precedence over maximizing agent count.

Workers are ephemeral runtime sessions/executions; v0.4 does not claim that every worker is a newly persisted OpenClaw agent profile.

For shared-checkout writes, `filesystem.write` requires explicit repository-relative literal `write_paths`. Overlapping writers are serialized. v0.4 does not claim automatic Git worktree/container isolation, and stricter project governance must prevail.

## 5. Mandatory Resume Order

When resuming development, read:

1. `CONTEXT.md`
2. `docs/process/MULTIAGENT-PROJECT-EXECUTION-v0.4-GATE.md`
3. `docs/process/ORCHESTRATOR-NEW-CHAT-CONTEXT-v0.8.md`
4. `docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY-v0.8.md`
5. `PROJECT-KNOWLEDGE-MANIFEST.yaml`
6. `docs/architecture/ORCHESTRATOR-SYSTEM-ARCHITECTURE.md`
7. `docs/architecture/ORCHESTRATOR-SYSTEM-DESIGN.md`
8. `docs/architecture/ORCHESTRATOR-AUTOMATIC-PROJECT-EXECUTION.md`
9. `docs/architecture/ORCHESTRATOR-MULTIAGENT-EXECUTION.md`
10. `docs/process/ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md`
11. Phase 3 plan/gate and WU-specific artifacts when the task reaches WU-055 or later.

Read additional artifacts only when the task requires them.

Do not load the entire repository or all historical material by default.

## 6. Legacy Knowledge Rule

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

## 7. OpenClaw Boundary

OpenClaw is an external runtime / agentic execution environment.

The Adaptive AI Orchestrator core remains authoritative for its own:

- project state;
- planning and plan mutation;
- Work Unit/dependency semantics;
- Ready Frontier and worker scheduling;
- resource-selection policies;
- authorization/governance;
- evaluation decisions;
- replanning;
- durable recovery;
- evidence and governed learning.

The `adaptive-orchestrator-bridge` is an invocation boundary, not the scheduler. OpenClaw may execute bounded work and provide operational evidence, but it must not silently redefine project specification, policy, gates or authoritative project knowledge.

## 8. Generated / Local Noise

Do not treat these as project knowledge:

- `.venv/**`
- `.pytest_cache/**`
- `**/__pycache__/**`
- `**/*.pyc`

## 9. Change Discipline

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