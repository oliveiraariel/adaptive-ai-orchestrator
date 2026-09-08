# ORCHESTRATOR — AUTOMATIC PROJECT EXECUTION

**Project:** Adaptive AI Orchestrator  
**Status:** executable architecture — v0.4  
**Scope:** high-level Work Graph planning, synchronized lateral workers, fan-out/fan-in and bounded replanning

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
Parallel-safe wave selection
   ↓
Dynamic logical worker sessions
   ↓
Result join
   ↓
Evaluation + Finalization
   ↓
Dependency advancement / fan-in
   ↓
Frontier recomputation
   ↓
Bounded additive replanning when required
   ↺
```

This layer composes the existing Adaptive domain/application seams; it does not replace `ExecutionCoordinator`, claims, execution policy, `AgentRuntime`, `EvaluateResult`, or `FinalizeExecution`.

## 2. Worker model

A **worker** in this execution mode is an ephemeral logical execution/session created for one ready Work Unit. It is not a newly persisted OpenClaw agent profile.

Multiple Work Units may use the same configured physical OpenClaw agent id while receiving distinct:

- task ids;
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
- precise write paths for write-capable parallel work;
- priority/criticality scheduling hints;
- explicit required/optional dependency edges.

Required edges must be acyclic and all endpoints must exist.

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

The frontend does not need to wait for the entire backend when a sufficiently stable contract provides the information it needs. Conversely, the orchestrator must retain a blocking dependency when the frontend would otherwise have to invent an unresolved contract or business rule.

## 5. Synchronized parallel waves

`RunProjectOrchestration` uses **synchronized waves**:

1. recompute the current ready frontier;
2. order candidates by priority/criticality;
3. choose a conflict-free subset up to `max_concurrency`;
4. prepare bounded TaskPackages and minimal skill sets;
5. dispatch all selected Work Units before waiting for any one result;
6. retrieve worker results concurrently;
7. evaluate and finalize every returned result;
8. satisfy accepted dependency edges;
9. join accepted outputs into downstream context;
10. recompute the frontier.

This creates real lateral runtime sessions while keeping the Adaptive engine authoritative over synchronization.

## 6. Concurrency bounds and token economy

Concurrency is a capability, not a target metric.

Defaults are intentionally bounded:

- `max_concurrency = 4`;
- `max_work_units = 24`;
- `max_waves = 24`;
- `max_attempts_per_work_unit = 2`;
- `max_replans = 2`.

The CLI accepts other bounded values; concurrency is validated in the range 1–32.

The planner is instructed to avoid token-expensive micro-fragmentation. The worker count follows the useful ready frontier, not a fixed pool. Two useful workers should not become six merely because the limit permits six.

`SkillResolver` further reduces context by selecting the smallest compatible deterministic skill set that covers each Work Unit's capabilities, including only required skill dependencies.

## 7. Shared-workspace write safety

Adaptive v0.4 does **not** claim automatic Git worktree/container isolation.

When multiple workers share a checkout:

- read-only Work Units may share a wave;
- a read-only Work Unit may share a wave with a writer when no other resource rule blocks it;
- two write-capable Work Units may share a wave only when both declare precise `write_paths` and those path prefixes do not overlap;
- unknown, global, wildcard, parent/child, or otherwise overlapping write ownership is serialized;
- `parallel_safe=false` serializes that Work Unit against other selected work.

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

## 11. Bounded replanning

A worker must not silently expand its own scope.

When genuinely necessary missing work is discovered, the worker may return:

```text
ADAPTIVE_REPLAN_REQUIRED: <reason>
```

Only an **accepted** Work Unit can trigger replanning. The runtime planner receives the current plan and compact execution state and may return a revised full plan.

The executor admits only additive changes:

- existing Work Unit ids/semantics remain authoritative;
- only new Work Unit ids are instantiated;
- only new dependency edges are added;
- dependencies from already completed sources are immediately satisfied;
- total Work Units and replan count remain bounded;
- the merged graph is revalidated before execution resumes.

Optional polish should not trigger replanning.

## 12. Failure and retry behavior

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

## 14. OpenClaw bridge

The OpenClaw bridge remains thin. It uses its private selector:

```text
--multi-agent
```

to route project work to `adaptive-orchestrator orchestrate` instead of the legacy one-Work-Unit `run` command.

The bridge must not recreate planning or worker scheduling in its prompt.

## 15. Verification requirements

This capability is not considered validated merely because the planner can describe parallel work. Tests must demonstrate:

- strict plan parsing and DAG validation;
- minimum skill-set resolution;
- one prerequisite unlocking multiple simultaneous workers;
- backend + frontend parallel frontier;
- at least six independent workers when the concurrency cap permits;
- fan-in downstream context from multiple accepted workers;
- overlapping write scopes serialized;
- disjoint write scopes parallelized;
- unauthorized side effects blocked before runtime;
- human Work Units not delegated;
- failed work bounded by retry limits;
- accepted replan signal adding necessary work and resuming the frontier;
- CLI project-mode structured output;
- selected skill configuration reaching the OpenClaw worker message.

A real deployed machine additionally requires a live multi-session E2E through its actual OpenClaw Gateway.

## 16. Non-claims

Adaptive v0.4 does not claim:

- persistent creation of arbitrary OpenClaw agent profiles;
- automatic Git worktree/container isolation;
- unlimited parallelism;
- semantic proof from runtime completion alone;
- permission to bypass project governance or human authority;
- that more workers always improve quality or cost.

The implemented guarantee is a bounded, policy-governed, dependency-aware, scalable orchestration loop over independent runtime worker sessions.
