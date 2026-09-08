# ORCHESTRATOR — AUTOMATIC PROJECT EXECUTION

**Project:** Adaptive AI Orchestrator  
**Status:** executable architecture — v0.4  
**Scope:** high-level Work Graph planning, continuously replenished lateral workers, fan-out/fan-in and bounded replanning

## 1. Purpose

Adaptive v0.4 adds the application layer that turns a broad project objective into an executable multi-Work-Unit graph instead of forcing every inbound request through one Work Unit.

The high-level path is:

```text
Project objective
   ↓
Governed planning / discovery
   ↓
Validated ProjectExecutionPlan
   ↓
Work Graph + real blocking edges
   ↓
Ready Frontier
   ↓
Conflict-safe dispatch up to concurrency budget
   ↓
Independent logical worker sessions
   ↓
FIRST completed result
   ↓
Evaluation + Finalization
   ↓
Dependency advancement / fan-in
   ↓
Immediately recompute frontier and refill free slots
   ↺ while unrelated workers continue
```

This layer composes the existing Adaptive domain/application seams; it does not replace `ExecutionCoordinator`, claims, execution policy, `AgentRuntime`, `EvaluateResult`, or `FinalizeExecution`.

## 2. Worker model

A **worker** in this execution mode is an ephemeral logical execution/session created for one ready Work Unit. It is not a newly persisted OpenClaw agent profile.

Multiple Work Units may use the same configured physical OpenClaw agent id while receiving distinct:

- task ids and retry identities;
- agent-owned session keys;
- logical roles;
- selected skill sets;
- context slices;
- scopes and constraints;
- claims and execution references.

Therefore a frontier with six safe Work Units may produce six simultaneous independent OpenClaw sessions without pre-creating six permanent agent configurations.

## 3. Planning contract

`RuntimeProjectPlanner` performs a read-only governed planning call and requires strict JSON data. The plan is never trusted directly as executable authority.

Every `ProjectExecutionPlan` must provide:

- a non-empty summary;
- unique Work Unit ids;
- independently understandable objectives;
- Work Unit kind;
- required capabilities and optional requested skills;
- expected output and acceptance criteria;
- requested side effects;
- precise repository-relative write paths for filesystem writers;
- priority/criticality scheduling hints;
- explicit required/optional dependency edges.

Required edges must be acyclic and all endpoints must exist. Planned filesystem writes without a declared write scope are rejected. Absolute paths, parent traversal and glob write scopes are rejected before execution.

The planner is instructed to add a blocking edge **only for a real prerequisite**. Layer names are not barriers by themselves.

## 4. Lateral frontend/backend execution

The graph is intentionally layer-agnostic.

Valid frontiers include, when dependencies and resource safety allow:

```text
backend + backend
frontend + frontend
backend + frontend
backend + testing + security review
frontend + accessibility review
research + architecture comparison
```

A common vertical-slice pattern is:

```text
Interface/API contract
        ↓
 ┌──────┼──────────┐
 ↓      ↓          ↓
backend frontend   contract tests
 └──────┼──────────┘
        ↓
 integration / end-to-end verification
```

The frontend does not need to wait for the entire backend when a sufficiently stable contract provides the information it needs. Conversely, the orchestrator retains a blocking dependency when the frontend would otherwise have to invent an unresolved contract or business rule.

## 5. Continuous frontier scheduling

`RunContinuousProjectOrchestration` is the operational project scheduler used by `adaptive-orchestrator orchestrate`.

It does **not** impose a barrier between batches of workers. Its loop is:

1. recompute the current ready frontier;
2. order candidates by priority/criticality;
3. compare candidates with all currently active workers for write/resource conflicts;
4. dispatch as many conflict-free Work Units as available concurrency slots permit;
5. wait only until at least one active execution completes;
6. evaluate and finalize each completed result immediately;
7. satisfy dependencies only for accepted results;
8. propagate bounded accepted outputs to dependent Work Units;
9. recompute the frontier immediately;
10. fill newly free slots while unrelated workers remain active.

Example with `max_concurrency=2`:

```text
t0  worker A ────────────────┐
    worker B ─────────────────────────────┐
                              │            │
t1  A accepted → unlocks C    │            │
    worker C starts ────────┐ │            │
                            │ │            │
t2  C completes             └─┘            │
                                             │
t3  B completes                            └─┘
```

C is allowed to start at `t1`; it does not wait for B merely because A and B were dispatched together. This is the required lateral-session behavior.

For compatibility, result records historically named `waves` are retained, but in continuous mode they represent **dispatch generations**, not synchronization barriers. CLI output also exposes the clearer `dispatch_generations` field.

## 6. Concurrency bounds and token economy

Concurrency is a capability, not a target metric.

Defaults are intentionally bounded:

- `max_concurrency = 4`;
- `max_work_units = 24`;
- `max_waves = 24` (compatibility name for maximum dispatch generations);
- `max_attempts_per_work_unit = 2`;
- `max_replans = 2`.

The CLI accepts other bounded values; concurrency is validated in the range 1–32.

The planner is instructed to avoid token-expensive micro-fragmentation. The worker count follows the useful ready frontier, not a fixed pool. Two useful workers should not become six merely because the limit permits six. Conversely, six genuinely independent useful Work Units may use six slots when policy and budget allow it.

`SkillResolver` further reduces context by selecting the smallest compatible deterministic skill set that covers each Work Unit's capabilities, including only required skill dependencies.

## 7. Shared-workspace write safety

Adaptive v0.4 does **not** claim automatic Git worktree/container isolation.

When multiple workers share a checkout:

- read-only Work Units may execute concurrently;
- a read-only Work Unit may execute alongside a writer when no other resource rule blocks it;
- two write-capable Work Units may execute concurrently only when their literal repository-relative write-path prefixes are disjoint;
- a candidate is checked not only against workers chosen in the same dispatch generation but also against **workers already active from earlier generations**;
- parent/child or equal path ownership overlaps and is serialized;
- `parallel_safe=false` prevents concurrent sharing;
- unsafe absolute, traversal, wildcard or missing filesystem-write scopes are rejected by the plan contract.

This is conservative by design. Future runtime adapters may add worktree/sandbox allocation as a stronger isolation strategy without changing the domain semantics.

## 8. Authority and side effects

Planning is read-only.

Worker side effects remain governed by the existing `ExecutionPolicy`. A Work Unit that requests an effect not present in the caller's allowed side effects is denied before runtime dispatch.

For normal repository development, a user/bridge may explicitly authorize:

```text
filesystem.write
```

That does not authorize:

- destructive deletion outside scope;
- credential mutation;
- deployment or publication;
- external communication;
- unrelated repositories;
- business-scope changes.

Human-only Work Units are marked `HUMAN_ACTION` and are not delegated to an agent runtime.

## 9. Fan-in context

Accepted upstream results are available to downstream Work Units through bounded context transfer.

Only dependency-relevant outputs are propagated, and each upstream result is truncated by the configured dependency-context budget. Large authoritative artifacts should be passed by project pointers rather than copied repeatedly.

This supports patterns such as:

```text
backend result ─┐
                ├─→ integration worker
frontend result ┘
```

without informal untracked worker-to-worker conversation.

## 10. Evaluation semantics

Runtime success is not semantic proof.

The current `EvaluateResult` observable gate can verify explicit evidence/literal criteria such as `runtime-completed`. For project work, semantic assurance should therefore be represented by additional Work Units such as:

- tests;
- contract verification;
- code review;
- security review;
- integration tests;
- UI/accessibility verification.

The planner is explicitly told not to fabricate natural-language string criteria as proof of semantic correctness.

A dependency becomes satisfied only after the upstream result reaches an accepted verdict. Runtime completion by itself cannot unlock downstream work.

## 11. Bounded replanning

A worker must not silently expand its own scope.

When genuinely necessary missing work is discovered, the worker may return:

```text
ADAPTIVE_REPLAN_REQUIRED: <reason>
```

Only an **accepted** Work Unit can request replanning. Once such a request appears, the continuous scheduler stops launching additional workers, allows already-active work to drain, then performs bounded replanning against a stable execution state.

This conservative drain-before-replan rule avoids mutating dependencies underneath in-flight Work Units and keeps planner activity inside the project concurrency budget.

The executor admits only controlled additive evolution:

- existing Work Unit ids/semantics remain authoritative;
- only new Work Unit ids are instantiated;
- only new dependency edges are added;
- dependencies from already completed sources are immediately satisfied;
- a new unsatisfied required edge cannot be attached to a Work Unit that already started or completed;
- every replan invocation counts against `max_replans`, even if it adds no Work Unit;
- total Work Units remain bounded;
- the merged graph is revalidated before execution resumes.

Optional polish should not trigger replanning.

## 12. Failure, retry and idempotency behavior

The project runner distinguishes:

- dependency-not-ready;
- policy blocked;
- workspace-conflict deferred;
- dispatch failed;
- runtime result failure;
- evaluation returned/rejected;
- human action blocked;
- bounded-plan exhaustion.

Revision-required Work Units can re-enter the ready frontier up to the configured attempt limit. Exhausted work is blocked rather than retried indefinitely.

Every retry receives a distinct task identity. This prevents a third or later retry from accidentally reusing an OpenClaw idempotency key or session identity created by an earlier `REVISION_REQUIRED` attempt.

## 13. CLI

High-level project mode:

```bash
adaptive-orchestrator orchestrate \
  --objective "Implement the authorized project objective." \
  --agent main \
  --max-concurrency 4
```

For repository edits, the caller must explicitly authorize the effect:

```bash
adaptive-orchestrator orchestrate \
  --objective "Implement the requested repository changes." \
  --agent main \
  --allow-side-effect filesystem.write \
  --max-concurrency 4
```

A deterministic prebuilt plan may be supplied for tests/E2E:

```bash
adaptive-orchestrator orchestrate \
  --objective "Run deterministic validation plan." \
  --plan-file /path/to/plan.json \
  --max-concurrency 3
```

Project mode intentionally does not accept single-Work-Unit-only flags such as a forced worker model/provider or a caller-supplied project-level acceptance marker. Per-Work-Unit capabilities, tools, side effects and acceptance criteria belong to the validated plan.

## 14. OpenClaw bridge

The OpenClaw bridge remains thin. It uses its private selector:

```text
--multi-agent
```

to route project work to `adaptive-orchestrator orchestrate` instead of the one-Work-Unit `run` command.

The bridge must not recreate planning, worker counts, frontier scheduling, claims, evaluation or replanning in its prompt.

## 15. Verification requirements

This capability is not considered validated merely because the planner can describe parallel work. Automated tests must demonstrate:

- strict plan parsing and DAG validation;
- repository-relative write-scope validation;
- minimum skill-set resolution;
- one prerequisite unlocking multiple simultaneous workers;
- backend + frontend parallel frontier;
- at least six independent workers when the concurrency cap permits;
- a newly unblocked worker filling a free slot **before an unrelated active worker finishes**;
- fan-in downstream context from multiple accepted workers;
- overlapping active write scopes serialized;
- disjoint write scopes parallelized;
- unauthorized side effects blocked before runtime;
- human Work Units not delegated;
- failed work bounded by retry limits;
- retry task identities unique beyond the second attempt;
- accepted replan signal adding necessary work and resuming the frontier;
- CLI project-mode structured output;
- selected skill configuration reaching the OpenClaw worker message;
- CI installing Gateway dependencies and propagating pytest failure through diagnostic pipelines.

A real deployed machine additionally requires a live multi-session E2E through its actual OpenClaw Gateway.

## 16. Non-claims

Adaptive v0.4 does not claim:

- persistent creation of arbitrary OpenClaw agent profiles;
- automatic Git worktree/container isolation;
- unlimited parallelism;
- semantic proof from runtime completion alone;
- permission to bypass project governance or human authority;
- that more workers always improve quality or cost.

The implemented guarantee is a bounded, policy-governed, dependency-aware, continuously replenished scalable orchestration loop over independent runtime worker sessions.
