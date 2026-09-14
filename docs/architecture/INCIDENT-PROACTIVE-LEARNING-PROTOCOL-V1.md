# Adaptive Incident, Proactive Resolution & Learning Protocol v1

**Status:** executable architecture — v1  
**Scope:** runtime-agnostic defect detection, persistent incident state, proactive resolution, learning promotion and knowledge dissemination

## 1. Purpose

Adaptive treats a real unresolved defect as an **active orchestration obligation**.
A defect must not disappear because one worker, observer process, orchestration
run, chat session, or runtime adapter ended.

~~~text
DETECT
  -> INCIDENT
  -> DIAGNOSE / RESEARCH / EXPERIMENT
  -> ROOT CAUSE
  -> FIX
  -> VALIDATE
  -> EXTRACT LEARNING
  -> PROMOTE
  -> DISSEMINATE
  -> CONSISTENCY CHECK
  -> CLOSE
~~~

The protocol belongs to Adaptive core. It is not an OpenClaw feature and it is
not owned by a Skill.

## 2. Runtime independence

Every runtime adapter may surface failures or worker observations, but all of
them feed the same Adaptive lifecycle:

~~~text
OpenClaw --------\
future runtime ---+--> IncidentSentinel --> IncidentRegistry
custom harness ---/
~~~

A future user may therefore benefit from knowledge learned through an incident
that originally happened under another runtime.

## 3. Signal and ownership boundary

Workers may emit one bounded ADAPTIVE_DEFECT_SIGNAL containing category,
component, observable symptom, severity, optional topics and a blocking flag.

This is evidence, not authority.

Workers and Skills may report a defect, attach bounded evidence references,
propose a hypothesis, and perform authorized diagnosis, research or experiments.
They must not create their own authoritative lifecycle, silently close an
incident, promote their own output to permanent knowledge, redefine Worker
Protocol semantics, or bypass side-effect, cost, security or approval policy.

Adaptive owns incident identity, persistence, state transitions, learning
promotion, dissemination and closure.

## 4. Detection sources

IncidentSentinel accepts signals from the intelligent and infrastructure chain:

- worker defect signals;
- dispatch failures;
- runtime-result failures;
- provider/runtime classifier;
- protocol or integrity failure;
- test/regression detectors;
- future security and consistency sentinels;
- human-intervention/gap detectors.

Normal states such as dependency-not-ready, concurrency deferral and explicit
policy denial are not automatically defects.

## 5. Persistent operational memory

Default global incident state:

~~~text
~/.local/state/adaptive-ai-orchestrator/incidents/
  INC-.../
    incident.json
    timeline.jsonl
~~~

ADAPTIVE_INCIDENT_DIR may override this location.

The registry stores bounded operational facts and references. It does not store
raw prompts, arbitrary source code, credentials, secrets, chain-of-thought or
raw tool output. Repeated observations with the same normalized fingerprint
reuse the active incident and increase recurrence_count.

## 6. Four memory layers

~~~text
1. OPERATIONAL MEMORY
   active incidents, executions, pressure, next action

2. HISTORICAL MEMORY
   timeline, evidence references, attempts, hypotheses, decisions

3. EMPIRICAL LEARNING
   provisional candidates and repeated experience

4. VALIDATED KNOWLEDGE
   strategies, architectural invariants, runbooks and Skills
~~~

Incident history is not validated knowledge. Rejected hypotheses may remain
historical evidence without becoming planner guidance.

## 7. Incident lifecycle

Canonical states include DETECTED, TRIAGED, INVESTIGATING,
ROOT_CAUSE_CANDIDATE, ROOT_CAUSE_CONFIRMED, FIX_IN_PROGRESS,
FIX_IMPLEMENTED, VALIDATING, VALIDATED, LEARNING_PENDING,
KNOWLEDGE_PROMOTED, DISSEMINATING, CONSISTENCY_CHECK and CLOSED.

Additional governed states include BLOCKED, MITIGATED, WAIVED and REOPENED.

IncidentLifecycleManager enforces the gates. An incident cannot close without
validation evidence, an explicit learning disposition, completion of required
dissemination targets, and a passing consistency check with evidence references.

## 8. Resolution Pressure

ResolutionPressureEngine converts “this problem should bother Adaptive” into a
bounded 0–100 score. Inputs include severity, blocking impact, recurrence, age,
root-cause uncertainty and lifecycle phase.

Typical directives:

~~~text
0..39   monitor-and-reconcile
40..69  diagnose-next-safe-slot
70..100 diagnose-now
~~~

Validated incidents with unfinished learning/dissemination receive a specific
obligation to complete that lifecycle. Pressure changes scheduling priority,
not authority.

## 9. Automatic replanning

A blocking or sufficiently high-pressure worker defect can become a replanning
signal even when the worker did not explicitly emit ADAPTIVE_REPLAN_REQUIRED.

Existing governance remains authoritative: max_replans, bounded Work Units,
stable graph rules, side-effect policy, concurrency budget and circuit breakers.

The worker reports the defect; Adaptive decides whether the graph must react.

## 10. Proactive supervision

IncidentSupervisor reads persistent open incidents and produces bounded
ResolutionDirective records. Every normal project plan/replan receives current
active incident obligations through RuntimeProjectPlanner.

The CLI exposes one explicit supervision cycle:

~~~bash
adaptive-orchestrator incidents
adaptive-orchestrator incidents --supervise
~~~

Supervision may publish an actionable notification while remaining free of
runtime-specific UI assumptions. An incident therefore survives session
boundaries and re-enters future orchestration decisions.

## 11. Notifications

Adaptive defines a runtime-independent NotificationPort. The default persistent
outbox is:

~~~text
~/.local/state/adaptive-ai-orchestrator/notifications.jsonl
~~~

Notifications use a stable incident/status/action key so repeated supervision
cycles do not spam the same event. Future adapters may deliver the same event to
OpenClaw UI, CLI, Slack, email, webhook or another runtime/harness. External
communication authority remains adapter/policy controlled.

## 12. External research

Adaptive defines ExternalResearchPort and can create bounded
ExternalResearchRequest objects when root cause is uncertain, external research
is allowed and resolution pressure justifies investigation.

Preferred evidence is primary: vendor/runtime documentation, official issue
trackers and upstream source repositories. Search results are evidence, not
validated knowledge. Research execution remains subject to tools, cost policy,
network authority and the normal Work Unit contract.

## 13. Learning extraction

A validated incident may become a LearningCandidate only after root cause, fix
and validation evidence exist.

Learning scope is explicit: LOCAL_ONLY, PROJECT_SPECIFIC, RUNTIME_SPECIFIC,
PROVIDER_SPECIFIC, GENERALIZABLE, ARCHITECTURAL or SECURITY_CRITICAL.

This prevents every typo or local failure from polluting global knowledge.

## 14. Dissemination

KnowledgeDisseminationPlanner maps topics to relevant consumers rather than
copying every lesson everywhere.

~~~text
result-transport
  -> Adaptive problem-solving knowledge
  -> Adaptive architecture
  -> debugging
  -> testing
  -> software-architecture

recovery
  -> Adaptive problem-solving knowledge
  -> debugging
  -> project-handoff
  -> engineering-lifecycle

security
  -> Adaptive problem-solving knowledge
  -> security-review
  -> debugging
~~~

ariel-agent-skills is a consumer of generalized learning; it is not the owner
of the incident lifecycle.

## 15. Consistency sentinel

A promoted lesson is not fully disseminated merely because new text was added.
KnowledgeConsistencySentinel deterministically checks scoped required and
forbidden invariants and returns evidence references.

The Worker Protocol/Result Store ownership rule is protected by a regression
check requiring Adaptive-owned manifest finalization, worker_writes_manifest
false, adaptive_finalizes_manifest true and completion_requires RESULT_VERIFIED,
while rejecting the stale worker-owned manifest wording discovered in the
2026-09-13 transport incident.

A passing lifecycle consistency check requires evidence references.

## 16. Communication-chain lessons already promoted

Runtime-agnostic validated strategy knowledge now includes:

- trace producer -> transport -> persistence -> consumer before retry;
- separate control/presentation plane from authoritative result plane;
- deterministic orchestrator ownership of machine integrity envelopes;
- runtime COMPLETED is not RESULT_VERIFIED;
- observer failure is not worker failure;
- same-run reconciliation before redispatch;
- staged SMALL -> MEDIUM -> LARGE transport validation;
- authoritative reference-only fan-in;
- source root, working directory, interpreter, venv and loaded module are
  distinct identities;
- unresolved incidents remain active orchestration obligations until lifecycle
  disposition is complete.

## 17. Safety and autonomy

Adaptive may autonomously read, diagnose, reconcile, search authorized sources,
compare evidence, run safe bounded experiments and propose remediation.
Filesystem writes, Git integration, deployment, credential changes, external
communication and destructive operations remain governed by their normal
authority boundaries.

Resolution pressure never grants new authority.

## 18. Relationship to Worker Protocol

The Worker Protocol remains above tasks and Skills:

~~~text
Adaptive core
  -> Worker Protocol
  -> runtime adapter
  -> worker
  -> selected Skills
~~~

Its incident contract states that a worker may report a defect signal, does not
own the incident lifecycle, Adaptive owns learning promotion, and raw worker
output is not incident memory.

## 19. Closure invariant

> An unresolved incident remains an active orchestration obligation until
> resolved, waived, superseded or explicitly blocked. A validated generalizable
> incident cannot close until its learning disposition, required dissemination
> and consistency evidence are complete.

This is the bridge from “Adaptive can learn” to “Adaptive is operationally
obligated to preserve, pursue and learn from meaningful failures.”
