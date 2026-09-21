# Recovery Loop — Adaptive Persistent Recovery & Learning Lifecycle

**Canonical short name:** Recovery Loop  
**Formal name:** Adaptive Persistent Recovery & Learning Lifecycle  
**Architectural category:** Autonomous Recovery and Learning Subsystem  
**Status:** implementation candidate on `feat/investigation-persistent-recovery-v2`  
**Continuity:** extends Issue #38 and the preserved foundation from Draft PR #39.  
**Authority:** the Orchestrator remains the central execution authority; the Recovery Loop is a subsystem/capability coordinated by the Orchestrator and never supersedes it.

> **Canonical terminology:** `Recovery Loop` means the complete Adaptive Persistent Recovery & Learning Lifecycle, not a simple retry loop.

The **Recovery Loop** is the Adaptive subsystem responsible for persistent treatment of retrabalho, technical conflicts, failed/returned work and exhausted solution paths. It coordinates reanalysis, materially different recovery strategies, new dispatches, retests, developer pause/resume, and the automatic learning lifecycle that follows a successful retest.

It is intentionally proactive: normal tasks do not need to be submitted “through the Recovery Loop”. The Orchestrator activates the relevant recovery/learning behavior when execution evidence shows that retrabalho, strategy exhaustion, recovery, or a successful retest requires it.

## 1. Purpose

Adaptive must not stop trying merely because one worker/session ended, one bounded retry budget was exhausted, or conversational memory lost the current execution state.

The capability introduced here turns a technical failure into a persistent governed obligation:

```text
failure / returned work / strategy exhaustion
        |
        v
reconcile authoritative state
        |
        v
Investigation / Recovery Strategist
        |
        v
orchestrator chooses admissible graph delta
        |
        v
operational workers execute + retest
        |
        +---- failure ----> new recovery epoch ----+
        |                                         |
        +---- success ----> automatic learning ---+
                                  |
                                  v
                      promotion / dissemination
                                  |
                                  v
                         consistency check
                                  |
                                  v
                              closure
```

The lifecycle continues until success or a governed stop. A developer may explicitly pause it and later resume from persisted state.

## 2. Source-of-truth hierarchy

For operational/liveness decisions, conversational history is supporting evidence only.

The preferred evidence is correlated persistent/runtime state:

```text
orchestration_id
+ work_unit_id
+ execution_id / external_id
+ active execution record
+ worker/session identity when available
+ valid claim/lease
+ fresh heartbeat
+ checkpoint / Result Store
```

Important distinctions:

- checkpoint = persisted history, not proof of current life;
- controller/launcher PID = process existence, not worker proof;
- controller heartbeat = controller life, not semantic Work Unit progress;
- worker heartbeat = runtime observability, not acceptance;
- Result Store/evaluation = result evidence, not current liveness.

When chat memory says `RUNNING` but the correlated operational state says there is no live execution, the operational state wins.

## 3. Roles

### 3.1 Orchestrator

The Orchestrator owns:

- current authoritative state reconciliation;
- policy and human-authority boundaries;
- Work Graph;
- dependency semantics;
- claims and duplicate-dispatch prevention;
- Recovery Strategist invocation;
- selection/admission of recovery graph changes;
- worker dispatch;
- evaluation;
- persistent recovery epochs;
- learning lifecycle activation;
- incident closure.

The Orchestrator does not outsource authority to the Recovery Strategist.

### 3.2 Recovery Strategist

The Recovery Strategist is a logical high-reasoning worker using the `investigation` Skill.

It receives:

- project objective;
- original Work Unit objective;
- authoritative current state;
- acceptance findings;
- previous attempts/strategies and why they failed;
- relevant validated/provisional Adaptive learning;
- constraints and authority boundaries.

It returns structured analysis:

- failure class;
- problem summary;
- failed prior paths;
- materially different candidate paths;
- novelty;
- prerequisites;
- risks;
- suggested Skills;
- expected verification evidence;
- external research need;
- recommended path;
- disposition;
- Work Graph guidance;
- human-decision requirement;
- confidence.

It does **not**:

- implement;
- dispatch;
- mutate the Work Graph;
- widen authority;
- close incidents;
- promote its own conclusions to permanent knowledge.

### 3.3 Learning Curator

The Learning Curator is the second logical mode of the high-responsibility `investigation` Skill.

It runs after a Work Unit that previously failed/returned/revised reaches an accepted retest, including an ordinary revision that recovered **before** strategy exhaustion.

It receives:

- before/after attempt evidence;
- accepted retest result;
- validation references;
- project identity;
- relevant validated/provisional Adaptive knowledge.

It returns a structured recommendation:

- problem/root cause supported by evidence;
- successful remediation;
- reusable learning statement;
- learning scope;
- target hints for Adaptive/project/runtime/selected Skills;
- confidence;
- whether the lesson should be promoted at all.

It is read-only. It does not edit knowledge or Skills. Adaptive core filters targets, promotes learning, verifies incorporation, and closes the lifecycle.

### 3.4 Operational workers

Operational workers execute only the Work Units admitted by the Orchestrator. They can use the appropriate implementation/testing/debugging/review Skill set and receive relevant validated learning overlays selected by Adaptive.

### 3.5 Incident Supervisor

The Incident Supervisor preserves unresolved defects/investigations as obligations across sessions and prioritizes diagnosis, research, validation and learning work.

A `PAUSED_BY_DEVELOPER` incident stays persisted but is not automatically scheduled until resumed.

### 3.6 Project Orchestration Supervisor

The Project Orchestration Supervisor is deterministic, not an LLM.

It scans non-terminal project checkpoints and controller heartbeat evidence:

- `desired_state=PAUSED` -> do not resume;
- fresh controller heartbeat -> observe only;
- RUNNING desired state + missing/stale controller heartbeat -> acquire supervisor lease and resume the same orchestration id.

The resumed Orchestrator reconciles the same persisted active execution identities. The Supervisor does not invent workers or plans.

Normal CLI project execution starts a detached, per-orchestration supervisor guardian by default. The guardian is scoped to the same `orchestration_id`, observes while the controller heartbeat is fresh, resumes only after the controller becomes missing/stale, and exits when the targeted checkpoint becomes terminal. If durable admission never materializes, it exits after a bounded startup grace period instead of inventing a replacement orchestration. `--no-auto-supervisor` is an explicit diagnostic/operational opt-out, not the normal mode.

A failed automatic controller-resume is **not** a reason for the guardian itself to terminate. In watch mode the supervisor records the failed resume, retains its durable lease until expiry as a retry cooldown, and continues watching the same non-terminal orchestration. One-shot supervision remains fail-fast for explicit operator diagnostics.

## 4. Failure and recovery states

### Ordinary RETURNED

A returned result remains active work.

Within the normal bounded strategy cycle:

```text
RETURNED
 -> retry current strategy when useful
 -> materially different strategy generation
 -> evaluate again
```

### Strategy exhaustion

When bounded strategies for the same Work Unit are exhausted:

```text
RECOVERY_REQUIRED
 -> Recovery Strategist
 -> strategist-guided replan
 -> corrective prerequisite / new safe path
 -> original Work Unit resumes after prerequisite acceptance
```

### Progressive recovery and fault isolation

Persistent recovery must make **material state progress**, not merely spend planner calls. The scheduler therefore treats recovery as a per-Work-Unit concern rather than a project-wide stop-the-world mode.

Recovery Strategist dispositions are operational:

- `RETRY_DIFFERENT_STRATEGY` returns the same Work Unit to bounded revision immediately, without invoking Planner;
- `REPLAN_WITH_PREREQUISITE` invokes Planner only when a real upstream prerequisite is needed;
- `EXTERNAL_RESEARCH` may materialize a bounded RESEARCH prerequisite;
- `WAIT_HUMAN`, `PAUSE`, and `NO_NOVEL_PATH` suspend/block only the affected Work Unit, preserving unrelated execution.

A recovery replan counts as structural progress only when it can unblock the target, normally by adding a new required prerequisite edge into the RECOVERY_REQUIRED Work Unit. A malformed topology gets a bounded correction opportunity using `max_replans`; repeated no-progress replans then fall back to a direct retry of the original bounded objective instead of repeatedly churning the control plane.

Each Work Unit also has a persisted stalled-recovery budget. `max_stalled_recovery_cycles` defaults to 3. When that budget is exhausted, Adaptive marks only that Work Unit BLOCKED with a `recovery-suspended` reason. Independent Work Units continue. Downstream dependents remain naturally ineligible until the suspended prerequisite is explicitly reopened or corrected.

Transient Recovery Strategist/Planner failures use the same bounded fallback policy: retry useful work first; suspend only the affected Work Unit after repeated stalled cycles. A control-plane provider failure is therefore no longer allowed to stop a 10/20/40-Work-Unit project.

Before spending a new recovery cycle, ordinary criticality=0 work may be reconciled from prior authoritative Result Store evidence when all of these are true:

- runtime completed;
- result transport is authoritative and complete;
- the worker emitted structured `COMPLETE`;
- it declared no unmet criteria;
- independent review is not required.

Critical work and independent-review policy stay on the strict evidence path.

This is Adaptive's **bulkhead rule**: a failure in one Work Unit must not sink unrelated Work Units.

`pending_replan` is therefore **not** a project-wide dispatch lock. It records control-plane work still owed for one or more recovery targets. While it is true, any independently READY Work Unit may still be dispatched. The scheduler prefers ready functional execution over synchronous Strategist/Planner work and returns to the recovery lane when no independent executable work is available.

### Dependency block

A Work Unit merely waiting for a required upstream dependency does not need Investigation. It becomes ready when the prerequisite is accepted.

### Human/authority/external stop

Investigation must not manufacture a solution when progress requires:

- a genuine business/human decision;
- missing authority;
- denied policy action;
- credentials the runtime cannot obtain;
- an external prerequisite unavailable to the system.

These become explicit governed stops/waits rather than fake technical retries.

## 5. Persistent recovery epochs

Normal attempts remain bounded. Persistence exists at the lifecycle level, not by making one retry loop infinite.

```text
RECOVERY EPOCH 1
  strategy A
  strategy B
  -> exhausted

Recovery Strategist reanalysis

RECOVERY EPOCH 2
  strategy C
  corrective prerequisite D
  -> retest

...
```

Each epoch receives the history of prior paths so that the Strategist searches a new part of the solution space.

Configuration:

- `persistent_recovery=true` enables strategist-guided epochs;
- `max_recovery_epochs=0` means no fixed strategist epoch count;
- `max_stalled_recovery_cycles=3` bounds repeated recovery that produces no useful progress for one Work Unit;
- `pragmatic_low_criticality_acceptance=true` allows authoritative COMPLETE/no-unmet evidence to overcome literal wording mismatches for criticality=0 work.

A failed recovery-plan topology consumes only the bounded per-epoch replanning budget. It does not consume the whole project's ability to replan later: cumulative `replan_count` is audit data, not a lifetime project fuse.

Exhaustion is scoped to the attempted worker/strategy/path. It is not equivalent to exhaustion of the project. After the per-Work-Unit stalled budget is exhausted, that Work Unit is suspended/blocked and unrelated ready work continues.

## 5.1 Throughput safeguards

Recovery is not the only place where a large project can become accidentally over-constrained. Continuous execution therefore applies these additional progress safeguards:

- **soft dispatch budget:** the effective wave budget scales with Work Graph size and bounded worker retry policy (up to the global safety cap), so a valid 40+ Work Unit serial graph is not stopped by a small historic default;
- **skill-resolution bulkhead:** an unknown/incompatible skill requirement blocks only the affected Work Unit instead of aborting preflight for the entire graph;
- **background learning is non-blocking:** an open automatic-learning lifecycle is recorded and observed, but it does not set `pending_replan` or stop functional delivery;
- **transactional recovery replans:** rejected replans roll back newly-added transient nodes/edges before fallback, so invalid remediation plans cannot leave orphan Work Units in the persisted graph.

## 6. Recovery topology

For an original Work Unit `U` in `RECOVERY_REQUIRED`, a new remediation `R` needed before retry must be represented as:

```text
R -> U
```

not:

```text
U -> R
```

The original identity/history is preserved. Accepted unrelated work stays accepted.

A corrective child that satisfies the exact finding that returned the original must be reconciled explicitly so the original is not stranded after the fix is already accepted.

## 7. Developer pause and resume

The project checkpoint persists a `desired_state`.

```text
RUNNING -> PAUSED -> RUNNING
```

`pause-project` sets `desired_state=PAUSED`.

Pause semantics:

- no new workers are dispatched after the controller observes the request;
- already active work may settle;
- checkpoint/attempt/strategy/recovery epoch state is preserved;
- the result is `PAUSED`, not incorrectly terminalized as `BLOCKED`.

`resume-project` changes the desired state back to RUNNING and resumes the same orchestration identity.

A stop report must be reconstructable from incident/checkpoint history: problem, current epoch, attempted paths, last recommended path, current WU state, evidence, learning state and pause reason.

## 8. Active persistence across controller death

`supervise-projects --watch` provides the active persistence loop.

The deterministic supervisor:

1. enumerates durable non-terminal checkpoints;
2. reads the correlated orchestration heartbeat;
3. ignores PAUSED projects;
4. does not duplicate a project whose controller heartbeat is fresh;
5. acquires an orchestration-specific supervisor lease;
6. resumes the **same orchestration id** when the controller is missing/stale;
7. lets the resumed Orchestrator recover the same external executions from checkpoint;
8. lets Result Store verification override a stale runtime `RUNNING` lifecycle when a valid final worker result was already atomically published;
9. returns control to the normal retry/strategy/Recovery Strategist path when the recovered result is still semantically incomplete.

For normal CLI project execution, Adaptive now starts this persistence mechanism proactively as a detached per-orchestration guardian. It is therefore not necessary for the OpenClaw caller or a human to type “tente novamente” merely because the launching controller/session ended. The guardian does **not** create a new orchestration and does **not** duplicate scheduling logic: it only watches and invokes the supported resume path for the existing durable orchestration.

A host/service manager may still run a broader `supervise-projects --watch` service for deployment-level coverage. The process-manager choice remains deployment-specific; the recovery semantics live in Adaptive.

## 9. Incident lifecycle

The preserved incident lifecycle remains:

```text
DETECT
 -> INCIDENT
 -> DIAGNOSE / RESEARCH / EXPERIMENT
 -> ROOT CAUSE
 -> FIX
 -> RETEST / VALIDATE
 -> LEARNING
 -> PROMOTION
 -> DISSEMINATION
 -> CONSISTENCY CHECK
 -> CLOSE
```

An incident does not disappear merely because a worker/chat/session ended.

## 10. Successful retest as learning trigger

A successful retest after **any prior unsuccessful attempt** is an automatic learning-analysis trigger.

This includes:

- ordinary `RETURNED` / `REVISION_REQUIRED` correction that succeeds within the normal bounded retry/strategy cycle;
- persistent Investigation / Recovery that succeeds in a later recovery epoch;
- accepted corrective-child reconciliation of an original returned Work Unit.

A first-attempt success is not treated as a retest and does not create learning merely because it completed.

Adaptive records:

- root problem/cause;
- successful remediation path;
- validation references;
- recovery epoch/path history;
- affected topics/context;
- confidence.

The Learning Curator first produces a structured recommendation. Adaptive then validates/narrows that recommendation and combines it with deterministic `KnowledgePromotionPolicy` / dissemination safeguards.

Possible scopes include:

- local only;
- project-specific;
- runtime/provider-specific;
- generalizable;
- architectural;
- security-critical.

## 11. Where learning is incorporated

Learning is deliberately routed to the narrowest useful layer.

### Adaptive problem-solving knowledge

Cross-project problem-solving/recovery strategies are promoted into validated Adaptive knowledge.

Repository-reviewed canonical strategies live in:

`knowledge/problem-solving-strategies.json`

Validated incident learning is also written to a sanitized runtime validated-knowledge store so it becomes usable immediately without waiting for a source-repository release.

### Project knowledge

Project-specific lessons remain scoped to project knowledge and must not leak into unrelated projects.

### Skill-targeted learning

`KnowledgeDisseminationPlanner` decides whether role-specific Skills benefit.

Examples:

- debugging -> failure isolation, liveness diagnosis;
- testing -> regression obligations;
- software-architecture -> event/liveness contract invariants;
- work-decomposition -> recovery topology;
- integration-release -> artifact readiness vs orchestration debt;
- adaptive-orchestrator-bridge -> authority/state boundary.

Validated runtime lessons carry target identifiers such as `skills:debugging`. Adaptive injects relevant targeted learning only into workers that selected those Skills.

`LOCAL_ONLY` learning is retained in incident history but is **not** written into reusable validated/provisional guidance, preventing a one-off correction from leaking globally.

This provides immediate operational assimilation while source-controlled Skill changes remain governable, reviewable dissemination artifacts.

## 12. Learning safety

Automatic learning must not store:

- raw prompts;
- chain-of-thought;
- secrets/tokens/credentials;
- arbitrary source code;
- entire worker outputs;
- unsupported business rules.

A successful retest validates the remediation in that context; it does not authorize arbitrary universalization. Scope classification and consistency checks remain mandatory.

## 13. Validated field lessons promoted in this implementation

The following are now canonical validated strategy candidates in the branch:

1. **Authoritative operational state over conversational memory**
2. **Correlated worker proof-of-life**
3. **Artifact readiness separated from orchestration observability debt**
4. **Controlled A/B component isolation + platform-native logs before speculative repair**

They were derived from real SGFP/Adaptive field incidents and are incorporated both into Adaptive knowledge and relevant Skills where role-specific reuse adds value.

## 14. Observability contract

Recovery lifecycle events are allowlisted/versioned operational events.

The implementation accepts, among others:

- `worker_recovered`;
- `work_unit_reconciled`;
- `recovery_strategy_analyzed`;
- `automatic_learning_triggered`;
- `automatic_learning_failed`;
- `orchestration_paused`.

A legitimate newly emitted recovery event must not crash observability consumers. Producer/consumer contract regression tests are required.

## 15. Closure contract

A technical recovery is successful when the original acceptance surface passes.

An **incident** is not closed until:

1. validation evidence exists;
2. learning disposition is decided;
3. required dissemination targets are completed;
4. consistency check passes.

The final incident/recovery report must contain:

- problem;
- root cause;
- attempted paths;
- successful solution;
- validation evidence;
- what was learned;
- learning scope;
- where it was incorporated;
- Skills targeted/updated;
- residual debt or uncertainty;
- final closure status.

## 16. Implementation map

Core/domain:

- `src/domain/incident.py`
- `src/domain/investigation.py`

Investigation/recovery:

- `src/application/investigation_strategy.py`
- `src/application/persistent_recovery.py`
- `src/application/incident_supervisor.py`
- `src/application/orchestration_supervisor.py`

Learning:

- `src/application/learning_analysis.py`
- `src/domain/learning_analysis.py`
- `src/application/automatic_learning.py`
- `src/application/problem_solving_learning.py`
- `src/application/knowledge_consistency.py`

Persistence:

- `src/infrastructure/incident_registry.py`
- `src/infrastructure/project_orchestration_checkpoint.py`

Execution integration:

- `src/application/run_project_orchestration.py`
- `src/application/continuous_project_orchestration.py`
- `src/application/runtime_project_planner.py`
- `src/adaptive_orchestrator/resilient_project_orchestration.py`
- `src/adaptive_orchestrator/cli.py`

## 17. Validation state before Issue #38 can close

The implementation has automated repository-level coverage for the lifecycle, but Issue #38 remains open until the owner accepts the implementation after representative runtime/environmental validation.

Automated proof includes:

- strategist parsing and safety;
- Learning Curator structured analysis;
- ordinary successful-retest learning trigger;
- local-only learning non-leakage;
- persistent recovery epoch tests;
- developer pause/resume checkpoint behavior;
- controller-death supervisor tests;
- no duplicate resume with fresh heartbeat/lease;
- observability event-contract regression;
- successful-retest automatic learning/dissemination/closure;
- targeted validated knowledge reuse;
- representative in-process E2E:
  - operational worker returns/fails;
  - strategy exhausts;
  - Recovery Strategist proposes new path;
  - Orchestrator dispatches recovery work;
  - retest succeeds;
  - automatic learning triggers;
  - learning is scoped/disseminated;
  - consistency gate passes;
  - incident closes.

Repository CI must remain green across Adaptive core, Ariel Agent Skills and Control Room. A live OpenClaw/provider execution is still the recommended final environmental proof before Issue #38 is closed or the Draft PR is promoted for merge.


## Authoritative project finalization and observer isolation

Project execution, shell observation and preflight execution are separate
lifecycles. A parent tool or conversation must never infer the project result
from the death of an observer process or from an earlier bounded Work Unit.

Adaptive exposes the read-only command:

```text
adaptive-orchestrator project-status \
  --orchestration-id <exact-id> \
  --project-root <project-root>
```

It reads the durable checkpoint without dispatching or resuming work and returns
an explicit lifecycle status:

- a non-terminal checkpoint is `RUNNING` or `PAUSED`;
- a terminal checkpoint is classified as `COMPLETED`, `PARTIAL`,
  `BLOCKED`, or `RECOVERY_REQUIRED` from its Work Unit states.

Fresh `orchestrate` also accepts a caller-allocated `--orchestration-id`.
The Adaptive/OpenClaw Bridge allocates this id before launch so every layer can
refer to the same project identity before, during and after durable admission.
Fresh orchestration refuses to reuse an id that already owns a checkpoint;
existing projects must use `project-status` / `resume-project`.

This closes the observer-identity gap exposed by the 2026-09-18 SGFP incident,
where Adaptive reached terminal `COMPLETED` but the parent conversation
reported an infrastructure blocker using stale precheck/process evidence.

Reusable invariant:

```text
precheck state != shell observer state != Adaptive project state
terminal user conclusion requires an authoritative project-state read
```
