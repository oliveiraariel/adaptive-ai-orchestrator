# Checkpoint Administration Requirements v1

**Status:** normative supplement to the orchestrator requirements  
**Scope:** durable project-orchestration checkpoints and their supported lifecycle administration

## Objective

Adaptive must actively reconcile persisted orchestration state with authoritative
runtime evidence. A non-terminal `RUNNING` checkpoint is historical intent, not
proof that a controller or worker is still alive.

The administration lifecycle is:

```text
detect -> investigate -> classify -> decide -> execute -> validate -> persist -> report
```

It is a control-plane capability. It must reuse the Project Orchestration
Supervisor, durable checkpoint store, Result Store and existing resume path; it
must not become a second scheduler.

## Functional requirements

### RF-CPA-001 — Durable detection

At supervisor startup and on each watch pass, inspect every durable
non-terminal checkpoint in the requested scope. A targeted guardian inspects
only its own orchestration; an unscoped supervisor inspects all of them.

### RF-CPA-002 — Evidence-based classification

Classification must consider checkpoint identity and phase, desired state,
controller heartbeat, active execution identities, authoritative Result Store
records, Work Unit states, control-plane fence and workspace safety. It must
never infer active work from `RUNNING` alone.

The classification vocabulary is administration metadata, not a new project
execution state:

| Classification | Meaning | Default action |
| --- | --- | --- |
| `ACTIVE` | correlated controller heartbeat is fresh | observe |
| `PAUSED` | developer or prior administrator paused it | observe |
| `COMPLETED` | every Work Unit is accepted with authoritative semantic completion evidence | terminalize through the checkpoint store |
| `RECOVERABLE` | a targeted, clean workspace can safely enter the existing resume path | resume the same id |
| `HUMAN_DECISION_REQUIRED` | scope, workspace, evidence or authority makes automatic resumption unsafe | administrative pause and report |
| `BUSY` | another governed mutation holds the orchestration lock | retry later without mutation |
| `TERMINAL` | the checkpoint is already terminal | observe |

### RF-CPA-003 — Bounded global behavior

An unscoped/global supervisor may detect, classify, report, terminalize proven
completion, and administratively pause unsafe work. It must not automatically
resume a stale historical orchestration. A checkpoint admitted by this version
may explicitly carry a durable `global_auto_resume=true` policy marker; only
such a checkpoint, or a targeted guardian/explicit target scope, is eligible
for `RECOVERABLE` resume.

### RF-CPA-004 — Proven completion only

An administrative terminal transition requires: no active executions; all
persisted Work Units `COMPLETED`; and an authoritative, integrity-verifiable
Result Store record with an `ADAPTIVE_WORK_STATUS: COMPLETE` footer and no
unmet criteria for every Work Unit. Runtime completion, a temporary file, a
manifest alone, or transport success is insufficient.

### RF-CPA-005 — Safe administrative hold

When automatic progress is unsafe, persist `desired_state=PAUSED` via the
official checkpoint store and append a sanitized administration report. This
does not claim functional success and does not erase active execution identity,
Result Store evidence, records, manifests, or Work Unit obligations.

### RF-CPA-006 — Idempotency and exclusion

Every mutation uses the orchestration control-plane mutation lock. Each report
has a deterministic id based on the orchestration, classification and a
checkpoint fingerprint that excludes prior administration reports. Repeated
inspection of unchanged state must not append duplicate reports or redispatch
work.

### RF-CPA-007 — Audit and observability

Persist a report containing the original desired state, classification,
sanitized evidence codes, action, checkpoint fingerprint, timestamp and any
human-decision reason. Emit allowlisted lifecycle events without objective
text, prompts, credentials, result contents or temporary-file contents.

## Safety and compatibility constraints

- Existing project execution states and Work Unit states remain authoritative;
  `classification` is only administration metadata.
- Never edit a checkpoint JSON manually, delete a Result Store artifact, or
  promote a `*.tmp` file into a result.
- A dirty Git workspace makes automatic resume unsafe and requires a hold.
- The existing targeted resume path remains responsible for claims, worker
  liveness reconciliation, Recovery Loop strategy, scheduling and evaluation.
- Result Store verification must use the existing official reader.

## Acceptance criteria

1. Fresh controller heartbeat is observed without resume.
2. A stale global historical checkpoint is held rather than resumed.
3. A clean, stale, targeted checkpoint is eligible for the existing resume
   path exactly once.
4. A dirty workspace is held and its active identity is preserved.
5. A fully proven completed checkpoint becomes terminal through the official
   store and an audit report is persisted.
6. A partial result or a temporary result file cannot terminalize a checkpoint.
7. Repeated inspection is idempotent; a concurrent mutation produces `BUSY`.
8. Events and persisted reports retain identity and omit raw sensitive payloads.
