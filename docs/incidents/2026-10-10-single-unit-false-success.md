# Incident: single Work Unit false success

**Date:** 2026-10-10
**Status:** mitigated in `fix/single-unit-completion-integrity`
**Scope:** Adaptive core, OpenClaw runtime integration, Result Store and Control Room projection.

## Executive summary

Two SGFP chart executions were submitted through the bounded `run` path rather
than the durable project `orchestrate` path. Their Result Store manifests were
valid, but neither execution had a project checkpoint. The bounded runner used
`runtime-completed` as its implicit acceptance criterion and the evaluator
treated `authoritative-worker-complete` as proof of every semantic criterion.
Consequently a stopped runtime could be reported as `ACCEPTED` even when the
worker did not publish the structured completion footer and the requested
functional acceptance surface had not been independently demonstrated.

## Correlated evidence

| Field | First chart run | Later chart run |
| --- | --- | --- |
| orchestration id | `9b3bb7c886e14ba58fd55c07f97d331f` | `7c7623b689824fa093fa7be7fad51d2a` |
| work unit id | `wu:9b3bb7c886e14ba58fd55c07f97d331f` | `wu:7c7623b689824fa093fa7be7fad51d2a` |
| execution id | `912ea03f7af8497c8554ef4d7440627e` | `eeec03f79fe24340a5bec3b89ebb815c` |
| external id | `gateway:orchestrator:task:9b3bb7c886e14ba58fd55c07f97d331f` | `gateway:orchestrator:task:7c7623b689824fa093fa7be7fad51d2a` |
| project checkpoint | absent | absent |

The first assignment declared only `runtime-completed` as acceptance. Both
Result Store manifests have a verified hash and protocol identity, but hash
integrity proves only publication integrity. The later worker result starts
with `COMPLETE` and has no `ADAPTIVE_WORK_STATUS` footer, so it is not a
structured completion under the Worker Protocol.

The authoritative observable event sequences are in:

- `~/.local/state/adaptive-ai-orchestrator/observability.jsonl`;
- `~/.local/state/adaptive-control-room/events.jsonl`;
- `SGFP-orchestrator-core/.adaptive/runs/<orchestration>/<work-unit>/<execution>/`;
- `SGFP-orchestrator-core/.adaptive/messages/`.

`project-status` returns `No project checkpoint exists` for both identities.
They cannot be resumed through the project supervisor and must not be
redispatched under a new identity automatically.

## Root causes

1. **Admission-mode mismatch (root cause).** The graph work was routed to
   `run`, which intentionally has no durable project checkpoint, controller
   guardian, project supervisor or Recovery Loop. The observable
   `run-session` in Control Room was therefore a bounded operational session,
   not evidence of a resumable project controller.
2. **Implicit liveness acceptance (root cause).** `run` and `dispatch`
   defaulted to `runtime-completed`; runtime termination was therefore a
   sufficient default criterion.
3. **Over-broad evaluator sentinel (root cause).**
   `authoritative-worker-complete` satisfied arbitrary semantic criteria,
   conflating verified result transport with product acceptance.
4. **Incomplete bounded-worker completion validation (root cause).** The
   single-unit runner did not parse the Worker Protocol footer before
   evaluation, unlike the continuous project path.

## Correction

- `run` and `dispatch` now require explicit literal `--accept` criteria and
  reject `runtime-completed` as a criterion.
- The bounded runner parses the worker completion footer. Missing, partial or
  blocked completion changes an otherwise completed runtime into a `PARTIAL`
  Result Package, which evaluates to `RETURNED` / `REVISION_REQUIRED`.
- The evaluator accepts `authoritative-worker-complete` only for the legacy
  liveness criterion in persisted project plans; it can no longer prove an
  arbitrary product criterion.
- The README specifies the bounded-run contract and directs durable/recoverable
  objectives to `orchestrate`.

## Regression evidence

- A runtime completion with no footer is `RETURNED`.
- An explicit `PARTIAL` footer remains `RETURNED` even when its text repeats a
  semantic criterion.
- CLI calls without `--accept`, or with `--accept runtime-completed`, fail
  before dispatch.
- Full Adaptive suite: `608 passed`.
- Bridge suite: `27 passed`.
- Adaptive Control Room source and active-runtime checkouts: `58 passed` each.

## Remaining validation

No live paid-provider worker, browser/WordPress environment, or process-kill
test against a live controller was run in this incident because the local
deterministic suites cover those paths and this record does not authorize
unbudgeted provider use or production interaction. A non-production project
orchestration with an explicitly approved provider budget is required to prove
end-to-end guardian recovery with a real OpenClaw worker.
