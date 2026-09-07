# Adaptive AI Orchestrator — Maturity Gap Plan after Matt Skills Audit

**Status:** Approved for implementation on analysis branch  
**Source comparison:** Matt ecosystem baseline + current Adaptive architecture  
**Goal:** improve real orchestration maturity without importing harness-specific mechanics into the core.

## 1. Decision rule

A capability is promoted only when the upstream mechanism is materially stronger or fills a real Adaptive gap. The promoted form must preserve the Adaptive architecture's runtime neutrality.

```text
upstream mechanism
→ extract problem and invariant
→ remove Git/Claude/tracker-specific implementation
→ design runtime-neutral domain contract
→ implement vertical slice
→ test success + failure + boundary cases
→ revalidate against existing architecture
```

## 2. Confirmed strengths already present in Adaptive

Do not replace these with simpler Matt equivalents:

- Project-first reasoning;
- explicit Work Unit abstraction;
- Agent / Skill / Model separation;
- capability-first resource analysis;
- Resource Configuration;
- TaskPackage and ResultPackage contracts;
- runtime port (`AgentRuntime`);
- explicit Result Evaluation domain;
- recovery action classification;
- replanning/versioned plans;
- evidence, continuity and learning concepts;
- explicit security-over-autonomy architectural principle.

## 3. Priority gaps

| Priority | Gap | Evidence from comparison | Implementation decision |
|---|---|---|---|
| P0 | ready-frontier scheduler loop | `implement-spec` operationalizes concurrent frontier execution; Adaptive currently computes readiness but does not schedule it | implement runtime-neutral `ExecutionCoordinator` |
| P0 | duplicate-work prevention | `wayfinder` claims tickets; concurrent Adaptive workers have no first-class ownership contract | implement `ExecutionClaim` + `ClaimRegistry` port/in-memory adapter |
| P0 | authority/autonomy gate | upstream separates fact delegation, HITL, wizard-only actions and pre-tool guardrails; Adaptive has principle but not a first-class policy decision | implement `ExecutionPolicy`, `AutonomyClass`, `PolicyDecision` and gate before delegation |
| P0 | recursive delegation bounds | desired ecosystem requires subagents; current runtime seam has no depth/cycle/budget contract | implement `DelegationContext` with bounded depth and lineage |
| P1 | independent multi-axis evaluation | `code-review` proves value of context-isolated Standards/Spec reviewers | implement `EvaluationPlan`, axes and deterministic aggregation; runtime parallelism remains adapter-level |
| P1 | context-transfer strategy | `writing-for-agents` + handoff expose context load/pointer/redaction maturity | implement explicit context strategy/pointers in task contract |
| P1 | Work Unit intent classes | `wayfinder` distinguishes research/prototype/grilling/task and HITL/AFK | add runtime-neutral `WorkUnitKind` to represent execution, decision, research, prototype and human action |
| P2 | partial-information planning/fog | `wayfinder` avoids false decomposition beyond known frontier | document + add planning-horizon model after scheduler slice is stable |
| P2 | retrospective environment learning | `retro` converts observed failures into environment improvements | integrate with existing controlled-learning lifecycle after policy admission is mature |
| P2 | workspace isolation/fan-in adapters | `implement-spec` uses worktrees and merger subagent | represent isolation/integration strategy as execution metadata/adapter capability, not core Git semantics |

## 4. Core design boundaries

### 4.1 Claim is not a Work Unit state

A claim is execution ownership with lifecycle independent from business progress. `READY → RUNNING` remains a Work Unit transition; claim/lease is a concurrency-control record.

### 4.2 Policy is not hidden in prompt prose

A policy gate produces an explicit result:

```text
ALLOW
REQUIRE_HUMAN_APPROVAL
REQUIRE_HUMAN_EXECUTION
DENY
```

Delegation may proceed only from `ALLOW` or from a human-approved request whose policy allows it.

### 4.3 Recursion carries lineage

Every delegated task may carry:

```text
root_task_id
parent_task_id
depth
max_depth
```

A child cannot be created when the next depth exceeds the authorized maximum. Runtime-specific subagent APIs remain adapters.

### 4.4 Frontier coordinator is runtime-neutral

It must not know about:

- Git branches/worktrees;
- Claude background jobs;
- GitHub issues;
- OpenClaw-specific commands.

It coordinates Work Units, claims, policies, TaskPackages and `AgentRuntime` executions.

### 4.5 Evaluation axes remain independent

Aggregation must not collapse findings into one blended narrative before the acceptance decision. Required axes retain identity and verdict.

## 5. Selected vertical slices

### Slice A — policy + delegation lineage

Deliverables:

- `domain/execution_policy.py`
- `domain/delegation_context.py`
- TaskPackage extensions
- policy gate tests
- recursion boundary tests

Gate:

- autonomous safe task allowed;
- approval-required task blocked without approval and allowed with approval;
- human-execution/forbidden task cannot be agent-delegated;
- child delegation beyond max depth fails deterministically.

### Slice B — claims + frontier scheduling

Deliverables:

- `domain/execution_claim.py`
- claim registry protocol + in-memory implementation
- `application/execution_coordinator.py`
- scheduler tests

Gate:

- only ready frontier is considered;
- concurrency budget is enforced;
- same Work Unit cannot be claimed twice;
- failed dispatch releases its claim;
- successful dispatch returns execution + claim lineage;
- blocked dependencies do not dispatch.

### Slice C — evaluation planning

Deliverables:

- `domain/evaluation_plan.py`
- aggregation tests

Gate:

- required axis rejection blocks overall acceptance;
- optional axis cannot hide required-axis failure;
- accepted-with-conditions remains visible;
- missing required evaluation is BLOCKED, never silently accepted.

### Slice D — context strategy

Deliverables:

- `domain/context_strategy.py`
- TaskPackage context pointers/strategy/redaction contract
- tests for invariants

Gate:

- pointer-based context can be selected without copying full context;
- sensitive transfer requires redaction declaration;
- strategy is metadata, not a harness command.

## 6. Deferred items

These are explicitly deferred until Slices A-D pass:

- persistent distributed leases;
- event-stream scheduler;
- distributed leader election;
- Git worktree adapter;
- generic sandbox/container manager;
- automatic Skill supply-chain admission;
- policy DSL;
- probabilistic model scoring;
- full planning-fog persistence.

Deferral prevents the comparison exercise from turning the project into an unvalidated distributed-systems framework.

## 7. Compatibility standard

Existing public constructors should remain source-compatible where practical by using safe defaults for new fields. Existing tests must continue passing. New capabilities must be additive unless an existing behavior is demonstrably unsafe.

## 8. Gate result

**Transversal/gap-analysis gate: PASS.**

The next phase is implementation of Slices A-D, followed by full regression tests and architecture revalidation before any merge to `main`.
