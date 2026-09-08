# Adaptive AI Orchestrator — Multiagent Project Execution v0.4 Gate

**Status:** IMPLEMENTATION / CI GATE PASSED  
**Deployment E2E:** pending on the installed Linux/OpenClaw environment  
**Merged implementation:** `f90a2f02f6217549837dc6d4b1f14c6abebc9f34`  
**Adaptive version:** `0.4.0`

## 1. Purpose

This record closes the repository-side validation gate for the v0.4 higher-level project orchestration capability introduced above the original one-Work-Unit inbound slice.

It is operational evidence, not a replacement for:

- `specifications/orchestrator/ORCHESTRATOR-MULTIAGENT-REQUIREMENTS-v0.4.md`;
- `docs/architecture/ORCHESTRATOR-AUTOMATIC-PROJECT-EXECUTION.md`;
- `docs/architecture/ORCHESTRATOR-MULTIAGENT-EXECUTION.md`.

## 2. Capability validated

The implemented project path is:

```text
broad project objective
        ↓
read-only governed planning
        ↓
validated ProjectExecutionPlan / Work Graph
        ↓
dynamic Ready Frontier
        ↓
smallest useful set of compatible workers
        ↓
continuous bounded parallel execution
        ↓
first returned result
        ↓
evaluation + finalization
        ↓
dependency advancement
        ↓
frontier recomputation
        ↓
newly unlocked worker may fill a free slot
while unrelated workers remain active
        ↓
explicit fan-in / bounded replan when needed
        ↺
```

The scheduler is intentionally **continuous**, not a sequence of barrier-synchronized batches. A `dispatch generation` records a scheduling event; it does not require every worker created in that generation to finish before later independent work may start.

## 3. Concurrency semantics

The capability supports layer-agnostic lateral work when real prerequisites and resource safety allow it, including:

```text
backend + backend
frontend + frontend
backend + frontend
implementation + tests/review/security
research + architecture analysis
```

The worker count is dynamic. `max_concurrency` is a ceiling, not a target. The implementation can schedule 1, 2, 3, 4, 6 or more logical workers up to the configured bound when useful independent work exists.

Workers are ephemeral independent runtime sessions/executions. v0.4 does **not** claim that every logical worker is a newly persisted OpenClaw agent profile.

## 4. Economicity

The planner and skill resolver are required to avoid artificial fan-out:

- no splitting merely to increase agent count;
- minimum compatible skill set per Work Unit;
- bounded dependency-result context;
- no repeated project discovery when authoritative context already exists;
- fan-out only for independently useful ready work;
- fan-in only where parallel results actually need reconciliation.

## 5. Dependency and fan-in semantics

Required dependencies are validated as an acyclic graph.

Only accepted upstream results may advance required dependencies. Downstream Work Units receive bounded dependency-relevant context from accepted results instead of relying on informal worker-to-worker conversation.

Explicit integration, synthesis, testing or review Work Units are used when multiple branches of work must converge.

## 6. Continuous slot replenishment evidence

Application tests explicitly exercise this scenario:

```text
fast prerequisite + long independent worker start together
        ↓
fast prerequisite completes first
        ↓
result accepted
        ↓
dependent downstream Work Unit becomes READY
        ↓
new worker starts before the long independent worker finishes
```

This verifies that the implementation does not impose an artificial wave barrier.

## 7. Scalability evidence

The automated suite includes a six-independent-Work-Unit scenario with `max_concurrency=6` and verifies that the project scheduler observes six dispatched concurrent workers.

Actual deployed concurrency remains bounded by both Adaptive policy and the external runtime/provider limits. A configured runtime may impose a lower effective ceiling.

## 8. Retry / execution identity

Retries are bounded. Every attempt receives a distinct execution/task identity, including attempts beyond the second retry, so idempotency/session keys do not collide across attempts.

Exhausted autonomous retries become governed blocked work instead of looping indefinitely.

## 9. Replanning

An accepted worker may signal genuinely necessary missing work through:

```text
ADAPTIVE_REPLAN_REQUIRED: <reason>
```

Replanning is:

- additive;
- bounded by `max_replans` and `max_work_units`;
- performed only after active work drains once a replan is pending;
- graph-revalidated before execution resumes;
- prohibited from retroactively adding an unsatisfied required prerequisite to work already running/evaluating/completed.

A replan request is processed even when the signaling Work Unit was the last Work Unit in the current graph, because the replan itself may legitimately add the next required work.

## 10. Human authority

`HUMAN_ACTION` Work Units are not delegated to agent runtime execution.

The project-level execution policy remains authoritative for side effects. A planner cannot grant itself an effect that the outer caller did not authorize.

## 11. Shared-checkout write safety

For the current v0.4 OpenClaw adapter, automatic Git worktree/container isolation is **not** claimed.

A Work Unit requesting `filesystem.write` must declare literal repository-relative `write_paths`. Unsafe scopes are rejected, including:

- missing write ownership;
- absolute paths;
- parent traversal;
- glob/wildcard ownership;
- broad/unknown ownership where safe concurrency cannot be established.

Two writers sharing a checkout are co-scheduled only when their ownership prefixes are non-overlapping. Newly considered writers are checked against writers that are already active from earlier dispatch generations.

A repository with a stricter governance rule — for example, requiring isolated branch/worktree ownership for every parallel writer — must keep those writers serialized until the active runtime proves that stronger isolation. Project governance is not weakened merely to obtain more parallelism.

## 12. OpenClaw boundary

Project mode is exposed through:

```bash
adaptive-orchestrator orchestrate
```

The OpenClaw-facing `adaptive-orchestrator-bridge` remains a thin invocation boundary. Its `--multi-agent` selector routes to project mode; planning, scheduling, claims, policy, worker count, evaluation, fan-in and replanning remain owned by Adaptive.

Ariel Agent Skills versions aligned with this gate:

- `adaptive-orchestrator-bridge` 0.2.1;
- `engineering-lifecycle` 0.2.1;
- `work-decomposition` 0.2.1.

## 13. CI integrity correction

During the v0.4 validation cycle, a false-positive CI condition was discovered:

1. Gateway tests imported `websockets`, but the workflow installed only the test extra;
2. the pytest command was piped through `tee` without fail-closed pipe semantics.

The workflow was corrected to install:

```text
.[test,gateway]
```

and to use `pipefail`. This caused the next run to expose a real scheduler/replan defect that was then corrected.

Therefore only the post-fix fail-closed CI result is accepted as v0.4 gate evidence.

## 14. Final repository-side validation evidence

On merged `main` commit:

```text
f90a2f02f6217549837dc6d4b1f14c6abebc9f34
```

GitHub Actions completed successfully:

```text
Orchestrator Validation: PASS
Bootstrap Validation:    PASS
```

The fail-closed Orchestrator Validation run installed the Gateway dependency, compiled source/tests and reported:

```text
284 passed
```

The companion Ariel Agent Skills merge also passed its `Validate skills` workflow on `main`.

## 15. Deployment E2E still required

Repository CI cannot prove the user's installed OpenClaw Gateway, local credentials, model availability, session concurrency or bridge injection.

After synchronizing the local machine, the remaining deployment proof is:

```bash
adaptive-openclaw-update
adaptive-openclaw-verify --e2e
```

The current E2E verifies:

1. the original single-Work-Unit round trip;
2. a deterministic multiagent project run with at least three simultaneous worker sessions plus fan-in;
3. OpenClaw inbound bridge → Adaptive project mode → OpenClaw workers → Adaptive result.

A successful local E2E validates the installed environment. It does not turn the entire Adaptive project into a production-ready system.

## 16. Non-claims / remaining project work

Passing this gate means the **v0.4 bounded multiagent project execution capability** is implemented and repository-validated.

It does not close the broader project roadmap. The following remain open according to the Phase 3 plan:

- `WU-055` Runtime Event Monitoring;
- `WU-056` Durable Execution / Recovery Integration;
- `WU-057` Operational Acceptance;
- production observability/security/deployment hardening.

It also does not claim automated managed-worktree integration/merge orchestration for parallel writers. That stronger isolation can be added behind the existing runtime/isolation seams without redefining Ready Frontier or Work Graph semantics.

## 17. Gate decision

```text
V0.4 IMPLEMENTATION / CI GATE: PASS
LOCAL INSTALLED OPENCLAW E2E:     PENDING
PRODUCTION-READY:                 NO
```

The next official Phase 3 Work Unit remains `WU-055 — Runtime Event Monitoring`, unless a later governed decision changes the roadmap.
