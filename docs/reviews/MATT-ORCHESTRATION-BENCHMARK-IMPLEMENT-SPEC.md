# Orchestration Benchmark — Matt `implement-spec` vs Adaptive AI Orchestrator

**Status:** Initial focused comparison  
**Purpose:** identify concrete orchestration mechanisms in Matt Pocock's `implement-spec` that may strengthen the Adaptive AI Orchestrator without sacrificing runtime agnosticism.

## 1. Scope

This review compares:

- Matt Pocock `skills/in-progress/implement-spec/SKILL.md`;
- Adaptive `Plan`, `Dependency`, `WorkUnit`, `WorkUnitReadiness`, `PlanWork`, `AgentRuntime`, `DelegateWork`, and related execution abstractions.

`implement-spec` is explicitly beta/in-progress upstream, so maturity is evaluated by mechanism, not by release status.

## 2. What `implement-spec` operationalizes well

The skill provides an end-to-end concurrent implementation coordinator around a specification and its ticket graph:

```text
spec + tickets
    ↓
task graph
    ↓
ready frontier
    ↓
parallel implementer subagents
    ↓
per-worker branch + worktree
    ↓
merger subagent
    ↓
integration branch / draft PR
    ↓
frontier recomputation
    ↺
final code review
    ↓
review fixes
    ↓
ready PR + cleanup
```

Important mechanisms:

- treats work as a dependency graph rather than a linear list;
- makes the ready frontier operational rather than descriptive;
- performs fan-out across all currently ready tickets;
- isolates workers in independent worktrees/branches;
- uses a dedicated merger role for fan-in;
- recomputes the frontier after each integrated result;
- separates exploration from implementation where useful;
- uses context pointers rather than duplicating full context to each worker;
- ends with an independent review stage;
- cleans temporary execution workspaces.

## 3. What Adaptive already has

Adaptive already has broader generalized abstractions:

### Dependency-aware planning

`Dependency` explicitly represents source, target, required/optional status and satisfaction. `WorkUnitReadinessEvaluator` computes READY/BLOCKED from required dependencies. `PlanWork` emits `ready_work_unit_ids`, `blocked_work_unit_ids`, and an initial `parallel_groups` tuple.

### Runtime seam

`AgentRuntime` normalizes submission, status retrieval, result retrieval and cancellation without exposing a specific harness SDK.

### Delegation contract

`DelegateWork` validates the Work Unit, selected resource configuration and TaskPackage before submitting execution.

### Wider decision model

Adaptive additionally models capability analysis, Skill selection, Agent selection, Model selection, ResultPackage evaluation, recovery, replanning, continuity and learning.

## 4. Confirmed gap: frontier exists semantically, but not yet as a scheduler loop

Adaptive can currently **compute which Work Units are ready**, and `Plan` can carry a parallel group. However, the current application layer does not yet provide a first-class orchestration loop equivalent to:

```text
while unfinished work exists:
    compute frontier
    claim eligible work
    dispatch frontier members within policy/budget
    monitor executions
    accept/evaluate returned results
    integrate accepted outputs
    satisfy/update dependencies
    recompute frontier
```

`implement-spec` expresses this operational loop directly for software tickets.

### Candidate improvement

Introduce a runtime-neutral **Frontier Scheduler / Execution Coordinator** rather than copying Git/worktree behaviour into the domain.

Possible responsibilities:

```text
ExecutionCoordinator
├── calculate frontier
├── respect concurrency budget
├── prevent duplicate ownership
├── dispatch eligible Work Units
├── monitor execution references
├── receive ResultPackages
├── route results to evaluation
├── advance dependencies only after accepted outcomes
├── recompute frontier
└── stop / wait / escalate when no safe progress exists
```

## 5. Confirmed gap: Work Unit ownership / claim semantics

`WorkUnitState` currently includes planning, readiness, execution, evaluation, revision, completion, cancellation and reopening states, but does not identify which execution/worker owns a unit while concurrent schedulers or agents are operating.

`wayfinder` and `implement-spec` both assume a form of single-worker ownership: Wayfinder explicitly claims a ticket; implement-spec assigns each ready ticket to one implementer execution/worktree.

### Candidate improvement

Model ownership separately from business/work state where possible, e.g. an `ExecutionClaim` rather than overloading `WorkUnitState`:

```text
ExecutionClaim
├── work_unit_id
├── claimant / execution_id
├── acquired_at
├── lease / expiry (if runtime requires it)
├── status
└── release reason
```

Benefits:

- prevents duplicate execution;
- supports multiple scheduler instances;
- allows recovery from abandoned workers;
- separates orchestration concurrency from domain lifecycle.

## 6. Confirmed gap: fan-out / fan-in are not first-class

Adaptive currently supports a ready parallel group concept but does not model a **parallel execution batch**, its completion policy, or its aggregation/fan-in stage.

Matt's implementation concretely fans out implementer subagents and fans completed work back into an integration branch using a merger subagent.

### Candidate improvement

Add generalized concepts such as:

```text
ExecutionGroup
├── member executions
├── concurrency policy
├── completion policy
├── failure policy
├── aggregation strategy
└── integration result
```

Do not assume all fan-in is Git merge. Possible aggregators include:

- artifact merger;
- evidence aggregator;
- result synthesizer;
- reviewer ensemble;
- transaction coordinator;
- no aggregation beyond dependency advancement.

Git worktrees/branches should remain an adapter-level workspace isolation strategy.

## 7. Confirmed gap: execution workspace isolation is not explicit

Matt's skill protects parallel implementers from filesystem/Git interference using separate worktrees and branches.

Adaptive's `AgentRuntime` contract abstracts execution, but it does not currently express workspace isolation requirements.

### Candidate improvement

Introduce a runtime-neutral workspace policy/profile:

```text
WorkspaceIsolation
├── SHARED_READ_ONLY
├── SHARED_CONTROLLED_WRITE
├── ISOLATED_COPY
├── ISOLATED_WORKTREE
├── CONTAINER
└── RUNTIME_MANAGED
```

The Orchestrator should select or require an isolation level based on collision risk and side effects. The runtime adapter translates that requirement to worktrees, containers, sandboxes, cloud workspaces, etc.

## 8. Improvement opportunity: sparse context via pointers

`implement-spec` explicitly tells agents to communicate sparsely and rely on pointers to specs, tickets, research notes and commits.

Adaptive `TaskPackage` already separates context, artifacts, decisions, dependencies and constraints, which is a strong foundation. The missing step is a more explicit policy for **pointer vs inline material** and for context-budget selection.

Candidate future fields/concepts:

```text
ContextReference
├── locator
├── authority
├── relevance condition
├── freshness/version
└── required / optional
```

This should be designed together with continuity, provenance and security.

## 9. Improvement opportunity: exploration as a separate execution role

Matt allows a preliminary exploration subagent to create shared notes before implementers run. This prevents every implementer from independently paying the same exploration cost.

Adaptive should not hard-code an `explorer` agent, but its planning model can recognize **shared prerequisite knowledge Work Units** that unblock several downstream Work Units.

Example:

```text
Research / Exploration WU
        ↓
shared evidence artifact
   ┌────┼────┐
   ▼    ▼    ▼
WU-A  WU-B  WU-C
```

This aligns naturally with dependency graphs and economicity.

## 10. Improvement opportunity: integration is a separate responsibility

Matt uses a merger subagent instead of allowing every implementer to write directly into the final branch.

This reveals a generally useful distinction:

```text
produce result
≠
integrate result
```

Adaptive already states that producing a result does not mean accepting it. The next refinement is:

```text
produce
→ evaluate
→ authorize integration
→ integrate
→ verify integrated state
```

For code this can mean merge/cherry-pick/rebase; for documents it may mean structured patching; for databases it may mean migration application; for plans it may mean state update.

## 11. Improvement opportunity: completion cleanup

`implement-spec` explicitly cleans implementer worktrees at the end. Adaptive should eventually represent temporary execution resources and cleanup obligations so abandoned workspaces, credentials, locks, branches, files or runtime jobs do not become unmanaged residue.

Candidate abstraction:

```text
ExecutionResource
├── id
├── owner execution
├── lifecycle
├── sensitivity
└── cleanup policy
```

## 12. Where Adaptive is currently stronger

The Matt skill should **not** replace Adaptive's architecture. Adaptive remains stronger as a general orchestration model in these areas:

- explicit separation of Agent, Skill and Model;
- capability-first resource selection;
- runtime abstraction;
- TaskPackage / ResultPackage contracts;
- evidence and uncertainty;
- result evaluation before acceptance;
- recovery action classification;
- replanning;
- continuity and learning;
- economicity;
- developer policy / authority as an architectural principle.

Therefore the appropriate strategy is **mechanism extraction**, not architecture replacement.

## 13. Initial decision status

| Candidate | Status |
|---|---|
| Frontier scheduler loop | **Strong candidate — continue design** |
| Claim / ownership semantics | **Strong candidate — continue design** |
| Fan-out / fan-in model | **Strong candidate — continue design** |
| Workspace isolation abstraction | **Strong candidate — continue design** |
| Context pointers as typed references | Candidate — coordinate with knowledge/security analysis |
| Exploration prerequisite Work Units | Candidate — likely expressible with existing dependency model |
| Separate integration stage | **Strong candidate — continue design** |
| Execution resource cleanup | Candidate — coordinate with runtime lifecycle analysis |
| Copy worktree/branch implementation into domain | **Reject** — adapter-specific |
| Make `implement-spec` the Orchestrator | **Reject** — too narrow and harness/software-delivery specific |

No production architecture or code has been changed by this review yet.
