# Checkpoint Administration

## Decision

Checkpoint administration is an extension of the existing supervisor, not a
replacement scheduler. The new `CheckpointAdministrator` is a small
control-plane module placed before `ProjectOrchestrationSupervisor.run_once`.
It reads the same durable sources, writes only via the official checkpoint
store, and delegates recovery to the existing targeted resume callback.

```text
checkpoint store + heartbeat + control plane + Result Store + workspace probe
                                  |
                                  v
                      CheckpointAdministrator
                  /             |              \
             terminalize       hold          targeted resume
                  |              |                |
             checkpoint store  checkpoint store   existing supervisor/controller
```

## Authority and isolation

The administrator owns only classification, administrative pausing, proven
terminalization, reports and observability. It does not plan, create Work
Units, dispatch workers, read raw prompt/result payloads, rewrite historical
records or decide recovery strategies.

The supervisor remains the liveness/lease gate. The resumed continuous
orchestrator remains responsible for worker Result Store reconciliation,
claims, evaluation and Recovery Loop handling.

## Global versus targeted supervision

A global pass is deliberately conservative: it detects and regularizes stale
history, but does not resume it. New admissions persist an explicit
`global_auto_resume=true` policy marker, so service startup can recover new
governed work without treating old state as equivalent. Normal new work also
has a detached, targeted guardian; that guardian may resume the same id after
administration classifies it `RECOVERABLE`.

## Persistence model

Reports are appended under `checkpoint_administration.reports` inside the
existing checkpoint state. They are audit metadata, not execution state. Their
deterministic ids use a canonical checkpoint fingerprint that excludes the
administration block, so unchanged repeated scans are idempotent. The
control-plane mutation lock protects all writes.

`HUMAN_DECISION_REQUIRED` becomes a persisted `desired_state=PAUSED` hold. It
does not set `terminal=true`, change Work Unit states, clear active executions,
or claim functional success.

## Completion proof

Terminalization requires a complete graph and independently verified Result
Store evidence for every Work Unit. The semantic worker footer is parsed using
the same completion-integrity function used by normal orchestration. Temporary
files and incomplete/blocked footers are diagnostic evidence only.

## Observability contract

The producer emits three sanitized events: detection, classification and
persistence. They carry correlation id, classification, action and digest-like
identifiers only. The existing JSONL sink remains the shared Control Room
projection source, so no Control Room schema migration is required for this
additive generic-event projection.
