# Project Knowledge Governance

**Project:** Adaptive AI Orchestrator  
**Purpose:** define how current, historical, legacy, implementation and operational knowledge are classified and consumed by humans and AI agents.

## 1. Core Rule

The repository contains artifacts with different authority.

They must not be treated as one undifferentiated knowledge pool.

The project uses these classes:

```text
Normative
Operational Current
Implementation
Evidence
Historical
Legacy
Draft / Hypothesis
Dynamic State
```

## 2. Normative Knowledge

Normative artifacts describe validated project intent and approved engineering constraints.

Examples:

- project definition;
- requirements;
- system architecture;
- system design;
- SDD rules;
- approved decisions/reviews.

When implementation conflicts with valid normative intent, the conflict must be surfaced and resolved through the project change process.

Code does not silently become specification.

## 3. Operational Current Knowledge

Operational artifacts answer:

> Where are we now and what is the next safe action?

Examples:

- `CONTEXT.md`;
- `ORCHESTRATOR-NEW-CHAT-CONTEXT.md`;
- `ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md`;
- active phase plan;
- active gate report.

Operational state is time-sensitive. Test counts, runtime versions, Git state, provider/model availability and external-service behavior are snapshot evidence and must be revalidated when material.

## 4. Implementation Knowledge

`src/` represents implemented behavior.

It is authoritative for what the current code actually does, but not automatically for what the system is intended to do.

Divergence between specification and implementation is drift and must be reported.

## 5. Evidence

Tests, Work Unit implementation records, gate reports and validation outputs provide evidence.

Evidence may confirm or contradict assumptions, but evidence does not silently rewrite normative artifacts.

## 6. Historical Knowledge

Historical files preserve evolution, previous plans and previous operational snapshots.

They must be retained for traceability, but excluded from default current-state retrieval.

Historical material should be read when:

- investigating provenance;
- explaining a decision;
- comparing baselines;
- performing impact analysis;
- reconstructing prior state.

## 7. Legacy Knowledge

The Professional Software Engineering Skill is a legacy knowledge source.

Current legacy artifacts include:

- `specifications/MASTER-SPECIFICATION.md`
- `specifications/MASTER-SPECIFICATION-v0.2.md`
- `specifications/MASTER-SPECIFICATION-v0.3.md`
- `docs/process/history/skill/**`

Legacy does **not** mean useless.

Legacy means:

```text
valuable
+
retained
+
non-authoritative by default
+
requires compatibility review before reuse
```

Legacy artifacts must not be part of normal Orchestrator resume/retrieval.

## 8. Legacy Compatibility Workflow

When a legacy concept appears useful:

```text
Legacy Concept
      ↓
Compatibility Analysis
      ↓
Classify
      ├── already incorporated
      ├── useful current-project candidate
      ├── future Skill/reference candidate
      ├── future architecture/design candidate
      └── obsolete/incompatible
      ↓
Impact Analysis
      ↓
Decision
      ↓
Adopt into the correct current artifact, if approved
      ↓
Verification
      ↓
Record provenance
```

Do not modify a current specification merely to preserve legacy wording.

Do not expose legacy text to a specialist agent as current project truth unless the task explicitly requires legacy analysis.

## 9. Future Skill Extraction

Legacy material may be valuable for future specialist Skills.

A concept should become a Skill candidate only if it is:

- reusable;
- procedurally useful;
- scoped to a clear capability;
- compatible with current project architecture;
- not a duplicate of a current normative rule;
- testable through realistic agent tasks.

The original legacy artifact remains historical provenance even after useful knowledge is extracted.

## 10. OpenClaw Retrieval Rules

OpenClaw should:

1. start at `CONTEXT.md`;
2. consult `PROJECT-KNOWLEDGE-MANIFEST.yaml`;
3. retrieve only the smallest relevant current artifact set;
4. respect authority classes;
5. avoid legacy/historical material by default;
6. retrieve large documents section-by-section;
7. use code/tests as implementation/evidence, not as silent replacements for specifications;
8. query the external Orchestrator core for live mutable state when that interface becomes available.

OpenClaw should not treat broad filesystem search ranking as authority ranking.

## 11. Dynamic State

Mutable live state must not be represented by stale static documents when a live source exists.

Future live access should come from the Orchestrator core for:

- Project State;
- active Work Units;
- dependency graph;
- resource registry;
- execution lifecycle;
- recovery/reconciliation state;
- mutable evidence;
- acceptance/rejection state.

Static snapshots must identify their snapshot nature.

## 12. Generated Noise

Exclude from project knowledge:

- `.venv/**`
- `.pytest_cache/**`
- `**/__pycache__/**`
- `**/*.pyc`

## 13. Physical Reorganization Policy

Do not move legacy or historical files solely for cosmetic organization before checking references and traceability.

Use two stages:

### Stage A — Logical quarantine

- classify in the manifest;
- exclude from default retrieval;
- document authority;
- preserve existing paths.

### Stage B — Physical relocation

After reference/impact analysis, legacy or historical artifacts may be moved into clearly named archive/history folders, with all references updated in the same controlled change.

This prevents accidental breakage while still protecting AI retrieval from obsolete authority.

## 14. Citation Markers

Opaque generation-time citation markers such as `cite...` or `filecite...` should not be deleted blindly.

They require a separate citation-normalization pass that either:

- maps them to stable source references;
- replaces them with durable links/references;
- or explicitly marks them as unresolved historical provenance.

## 15. Change Rule

Knowledge classification changes are project changes.

They must be:

```text
identified
→ justified
→ impact-assessed
→ reviewed
→ versioned
→ reflected in the manifest
```
