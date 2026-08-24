# WU-055 Pre-Implementation Reconnaissance

**Project:** Adaptive AI Orchestrator  
**Work Unit:** WU-055 — Runtime Event Monitoring  
**Artifact type:** Pre-Implementation Reconnaissance / Technical Evidence  
**Status:** Completed — Authenticated Gateway Event Spike Required  
**Authority:** Supporting technical evidence; not the normative WU-055 design or implementation specification  
**Inspected repository baseline:** `bd37def fix project resume read order`  
**Validated local runtime:** OpenClaw `2026.7.1-2 (0790d9f)`  
**Repository mutation during reconnaissance:** None  
**Next gate:** Authenticated Gateway Event Spike  
**Recommended repository path:** `docs/process/RUNTIME-EVENT-MONITORING-RECONNAISSANCE-WU-055.md`

## Evidence and Authority Boundary

This artifact records the state observed during the WU-055 pre-implementation reconnaissance.

Its factual observations are evidence tied to the inspected repository baseline and local OpenClaw installation. Proposed architecture and file changes remain **provisional** until the authenticated Gateway event spike closes the runtime unknowns identified in this document.

This artifact must not silently override:

- Orchestrator requirements;
- current system architecture/design;
- the Phase 3 implementation plan;
- later authenticated runtime evidence;
- the final WU-055 architecture/implementation record.

When later evidence supersedes a provisional conclusion, preserve this document as traceability evidence and record the superseding decision in the canonical WU-055 artifact.

## Repository State

- Branch: `main`
- Working tree: clean
- Synchronization: `main` matches `origin/main`
- Current commit: `bd37def fix project resume read order`
- Previous commits:
  - `1b4c24c organize project knowledge and update continuity`
  - `c65f257 Strengthen new chat context and bootstrap`

Gateway checks:

```text
OpenClaw 2026.7.1-2 (0790d9f)
Gateway Health
OK (54ms)
```

No repository files were modified, created, deleted, moved, staged, committed, or pushed. Tests were not executed because the request prohibited creating repository-side test/cache artifacts.

## Current Runtime Architecture

The current execution path is:

```text
Application
  -> AgentRuntime
    -> OpenClawAdapter
      -> OpenClawClient
        -> OpenClawGatewayClient
          -> WebSocket Gateway
```

Relevant files:

- `src/application/agent_runtime.py`
- `src/infrastructure/openclaw_adapter.py`
- `src/infrastructure/openclaw_gateway_client.py`

### AgentRuntimeStatus

Path: `src/application/agent_runtime.py`

Public values:

```text
SUBMITTED
RUNNING
COMPLETED
FAILED
CANCELLED
```

Responsibility: runtime-neutral lifecycle status normalization. Layer: Application. Runtime-event support: none.

### ExecutionReference

Path: `src/application/agent_runtime.py`

Public fields:

```text
id
runtime
external_id
status
```

Responsibility: correlate an Orchestrator execution with an external runtime execution. Layer: Application. It contains no event sequence, session key, run metadata, or reconciliation state.

### AgentRuntime

Path: `src/application/agent_runtime.py`

Public API:

```python
submit(task) -> ExecutionReference
get_status(execution) -> AgentRuntimeStatus
retrieve_result(execution) -> AgentRuntimeResult
cancel(execution) -> ExecutionReference
```

Responsibility: runtime-neutral execution port. Layer: Application. It has no monitoring or event subscription method.

### OpenClawClient

Path: `src/infrastructure/openclaw_adapter.py`

Public API:

```python
submit(task_payload) -> str
get_status(external_id) -> str
retrieve_result(external_id) -> object
cancel(external_id) -> None
```

Responsibility: infrastructure-facing client contract used by `OpenClawAdapter`. Layer: Infrastructure. Runtime-event support: none.

### OpenClawAdapter

Path: `src/infrastructure/openclaw_adapter.py`

Responsibilities:

- convert `TaskPackage` into an OpenClaw payload;
- submit work and create `ExecutionReference`;
- normalize OpenClaw statuses;
- retrieve results;
- translate cancellation;
- reject references belonging to another runtime.

Layer: Infrastructure adapter implementing the Application `AgentRuntime` port. Runtime-event support: none.

### OpenClawGatewayClient

Path: `src/infrastructure/openclaw_gateway_client.py`

Public API:

```python
submit(task_payload) -> str
get_status(external_id) -> str
retrieve_result(external_id) -> object
cancel(external_id) -> None
```

Current protocol:

```text
connect.challenge
  -> connect
  -> hello-ok
  -> one RPC request
  -> one matching RPC response
  -> close connection
```

It stores `GatewayRun(run_id, session_key)` and uses:

```text
sessionKey = orchestrator:<task_id>
```

Layer: Infrastructure. Runtime-event support: none.

## Current Telemetry Architecture

Repository search found no source definitions for:

```text
TelemetrySink
TelemetryEvent
ExecutionCost
ExecutionLatency
```

### EvidenceRecord

Path: `src/domain/evidence_record.py`

Public fields:

```text
id
source
evidence_type
content
confidence
timestamp
references
metadata
```

`EvidenceType` includes `OBSERVATION`, `TEST`, `RESULT`, `DECISION`, `EXECUTION`, and `TELEMETRY`.

Responsibility: represent evidence and provenance. Layer: Domain.

`EvidenceRecord` is not a telemetry transport, event listener, event store, or observability backend. WU-030 explicitly excludes telemetry collection and event streaming.

There is no TelemetrySink injection point in `OpenClawGatewayClient`, `OpenClawAdapter`, `AgentRuntime`, or `EvidenceRecord`. The architecture document describes TelemetrySink conceptually, but source implementation has not created that port.

## Installed Gateway Event Capabilities

The installed Gateway is healthy:

```text
OpenClaw 2026.7.1-2
Gateway port 18789
Health: OK
```

A raw unauthenticated WebSocket handshake reached the Gateway but was rejected with:

```text
NOT_PAIRED
DEVICE_IDENTITY_REQUIRED
```

Therefore the live authenticated `hello-ok` payload was not captured by an independent probe.

The installed package implements or advertises these event families:

```text
agent
chat
session.message
session.operation
session.tool
sessions.changed
presence
tick
health
heartbeat
cron
task
shutdown
```

It also contains:

```text
sessions.subscribe
sessions.unsubscribe
sessions.messages.subscribe
sessions.messages.unsubscribe
sessions.list
sessions.describe
sessions.preview
```

`sessions.subscribe` requires `operator.read`.

The installed server emits `sessions.changed` payloads containing, where available:

```text
sessionKey
reason
timestamp
hasActiveRun
activeRunIds
session snapshot data
```

Installed client code handles event sequence numbers, sequence-gap detection, and reconnection after a gap.

Capability status:

| Capability | Result |
|---|---|
| Protocol version | Confirmed as v4 by current client, tests, and installed package |
| hello-ok.features.events | Not captured from live authenticated handshake |
| hello-ok.features.methods | Not captured from live authenticated handshake |
| agent events | Implemented; live payload not captured |
| sessions.changed | Implemented and emitted |
| sessions.subscribe | Implemented; operator.read |
| chat.history | Confirmed by existing real Gateway validation |
| Active run information | hasActiveRun and activeRunIds are emitted in session snapshots |
| Frame-level event sequence | Used by installed client; live wire value not captured |
| Session message sequence | messageSeq and message-level seq are supported |
| Per-run event sequence | Not established |
| Event payload runId shape | Not fully confirmed live |

WU-055 must not assume every event has a per-run sequence or `runId`.

## Current WebSocket/Event Behavior

1. Event frames are discarded. `_receive_until_response()` executes:

```python
if frame.get("type") == "event":
    continue
```

2. There is no persistent receive loop.

3. Events and responses coexist only within one temporary connection; events are skipped and only the matching request ID is accepted. There is no shared connection, multiplexer, queue, or listener dispatch.

4. Responses are correlated by request ID, including the handshake response.

5. Unsolicited event frames are not retained.

6. Every RPC creates a new WebSocket connection and closes it after the response.

7. The implementation is synchronous, using `websockets.sync.client.connect` and blocking send/receive calls.

8. The least disruptive listener seam is inside Infrastructure:

```text
OpenClawGatewayClient
  -> Gateway event decoding
  -> Infrastructure event listener/callback
```

9. `AgentRuntime` need not change initially. Adding OpenClaw event methods there would force all runtimes to implement Gateway-specific monitoring.

10. There is no existing TelemetrySink injection point. A new Application-level runtime-neutral telemetry/event sink is required if WU-055 must deliver normalized metadata.

## Event Correlation Semantics

Current reliable correlation:

```text
TaskPackage.task_id
  -> sessionKey = orchestrator:<task_id>
  -> agent response runId
  -> external_id = gateway:<runId>
  -> ExecutionReference
```

Recommended event correlation precedence:

1. explicit event `runId`;
2. `sessionKey`;
3. existing `ExecutionReference`;
4. event/session snapshot correlation;
5. otherwise mark uncorrelated rather than guessing.

Do not treat these as interchangeable:

```text
Gateway frame sequence
!=
session message sequence
!=
per-run sequence
```

## Reconnection/Reconciliation Semantics

The current client has no reconnection or reconciliation behavior.

- Duplicate event: deduplicate using verified identity; prefer connection/event sequence when available; never derive identity from message text.
- Lower sequence: ignore as stale if the sequence is verified.
- Equal sequence: ignore as duplicate.
- Forward gap: mark the stream incomplete and reconcile; never invent lifecycle transitions.
- Disconnect: means event observation was interrupted, not that the run failed or was cancelled.
- Reconnect: handshake, verify features, resubscribe, reconcile active executions, then resume.
- Active run after reconnect: use authoritative runtime/session state.
- Terminal RPC result with missed events: terminal status/result is authoritative; event stream is observational evidence.

Potential reconciliation sources are `agent.wait`, `sessions.list`, `sessions.describe`, `chat.history`, and active session snapshots, subject to authenticated capability confirmation.

## Privacy Boundary

Do not persist by default:

- prompt text;
- assistant message bodies;
- reasoning/thinking;
- raw tool arguments;
- raw tool results;
- secrets;
- full transcript content.

Minimum safe metadata:

```text
runtime
event family/type
runId, when present
sessionKey, when present
verified sequence, when present
normalized lifecycle state
timestamp
agent/model/provider, when present
correlation identifiers
sanitized status/error
reconciliation/gap indicator
```

The current client excludes `thinking` blocks when extracting assistant output. WU-055 should preserve that boundary and avoid routing transcript content into telemetry.

## Provisional Architecture Decision

**Provisional recommendation: B — Infrastructure + Application changes, with no Domain contract change, pending the authenticated Gateway event spike.**

Infrastructure must handle Gateway connections, event frames, subscriptions, cursors, reconnects, and OpenClaw-specific payloads.

Application needs a runtime-neutral telemetry/event sink if normalized metadata must be delivered.

Domain must not receive OpenClaw event names, Gateway frames, WebSocket types, or Gateway sequence semantics.

`AgentRuntime` should remain unchanged initially, and `EvidenceRecord` should not become a telemetry transport.

```text
OpenClaw Gateway
  -> OpenClawGatewayClient
  -> OpenClaw event normalization
  -> Application telemetry/event sink
  -> optional evidence integration
```

## Provisional File Change Set

The following file changes are candidate implementation changes, not yet an approved or executed implementation plan. They must be revalidated after the authenticated Gateway event spike.

No files were modified.

### Files to modify

- `src/infrastructure/openclaw_gateway_client.py`: managed event-capable connection, request/response multiplexing, event dispatch, capability capture, subscription, sequence tracking, reconnect notification, and safe metadata projection.
- `src/infrastructure/openclaw_adapter.py`: optional wiring from infrastructure events to the Application telemetry sink while preserving AgentRuntime.
- `tests/infrastructure/test_openclaw_gateway_client.py`: event delivery, response correlation, sequences, gaps, subscription, reconnect, and RPC regression tests.
- `tests/infrastructure/test_openclaw_adapter.py`: safe normalization, correlation, optional sink, and no content leakage tests.
- `tests/system/test_openclaw_gateway_vertical_slice.py`: submit, event observation, status, terminal result, reconciliation, and cancel.

### Files to create

- `src/application/telemetry.py`: minimal runtime-neutral `TelemetryEvent` and `TelemetrySink` contract containing safe metadata only.
- `docs/architecture/OPENCLAW-GATEWAY-EVENT-MONITORING-WU-055.md`: authenticated capabilities, event contract, correlation, gaps, reconnect, privacy, evidence, and limitations.

`ExecutionCost` and `ExecutionLatency` should not be added unless WU-055 establishes a real need and source.

### Documentation to update after implementation

- `docs/process/PHASE-3-IMPLEMENTATION-PLAN.md`: WU-055 status/evidence.
- `docs/process/PHASE-3-GATE-REPORT.md`: only after automated and real Gateway validation.
- `docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md`: only after WU-055 completion.
- `docs/architecture/ORCHESTRATOR-SYSTEM-DESIGN.md`: only if the Application telemetry contract materially changes the formal design.

## Proposed Tests

These tests are candidate acceptance/verification coverage and must be finalized after the authenticated runtime evidence is available.

### Gateway client

- capability parsing;
- `sessions.subscribe`;
- unsolicited events before RPC responses;
- unrelated and matching response IDs;
- agent correlation;
- sessions.changed active-run metadata;
- sequence tracking;
- duplicate/stale events;
- forward gaps;
- closure, reconnect, and resubscription;
- terminal status after missed events;
- sanitized errors.

### Application telemetry

- safe event construction;
- required correlation;
- absent optional fields;
- no prompt/message/reasoning/tool content;
- sink delivery;
- no runtime-specific concepts in the Application contract.

### Adapter and system

- event-to-execution correlation;
- status/result/cancel compatibility;
- optional telemetry sink;
- OpenClaw-specific payload isolation;
- accepted event, duplicate event, gap, reconnect, authoritative reconciliation, and completed result.

## Proposed Acceptance Criteria

These criteria are provisional until the authenticated Gateway event spike confirms the installed runtime's event, sequence, subscription, and reconciliation semantics.

1. Relevant installed lifecycle events are observed when advertised and permitted.
2. Events correlate to runId, sessionKey, and ExecutionReference when available.
3. Missing correlation does not create invented associations.
4. Duplicate events do not duplicate state advancement or telemetry.
5. Lower/equal verified sequences do not regress state.
6. Verified gaps trigger reconciliation or explicit uncertainty.
7. Reconnection performs handshake and resubscription where supported.
8. Reconnection does not convert active runs into failures/cancellations.
9. Terminal agent.wait remains authoritative after missed streaming events.
10. Lifecycle normalization does not leak OpenClaw concepts into Domain.
11. AgentRuntime remains compatible unless a cross-runtime requirement is proven.
12. Telemetry receives safe normalized metadata only.
13. Sensitive content is not persisted by default.
14. Existing submit/status/result/cancel behavior remains compatible.
15. Architecture, Gateway infrastructure, adapter, and complete regression tests pass.
16. Real Gateway validation confirms authenticated event capability and an event/reconciliation path.
17. WU-055 evidence records version, protocol, capabilities, event shapes, limitations, and results.

## Unknowns Requiring a Spike

A research/spike is required before implementation design because the live authenticated `hello-ok` capability payload was not captured.

Determine:

1. Authenticated `hello-ok.features.events`.
2. Authenticated `hello-ok.features.methods`.
3. Whether `sessions.subscribe` is permitted for the Orchestrator client identity/scopes.
4. Whether agent events contain `runId`.
5. Whether agent events contain a reliable sequence.
6. Scope of frame-level `seq`.
7. Whether `sessions.changed` is sufficient for reconciliation.
8. Whether `sessions.describe`, `sessions.list`, or another method is authoritative.
9. Whether `sessions.messages.subscribe` is required.
10. Whether reconnect resumes from a cursor or requires snapshot reconciliation.
11. Whether `chat.history` can detect missed terminal output without persisting bodies.
12. Whether this client mode requires device identity in addition to token/password.

The spike should use the existing OpenClaw authentication/device-identity mechanism without changing Gateway configuration.

## Recommendation

The architecture is suitable for WU-055, but implementation should not assume event payloads or sequence semantics.

Smallest preserving direction:

```text
Infrastructure event-capable Gateway client
  -> runtime-neutral Application TelemetrySink
  -> existing execution correlation
```

Keep `AgentRuntime` and Domain unchanged initially. Do not turn `EvidenceRecord` into an event bus or telemetry transport.

**RESEARCH/SPIKE REQUIRED**

## Document Disposition

This reconnaissance is complete and should be preserved in the repository as WU-055 traceability evidence.

Recommended permanent location:

```text
docs/process/RUNTIME-EVENT-MONITORING-RECONNAISSANCE-WU-055.md
```

The next artifact should be the authenticated Gateway event spike report. After that spike:

1. close or explicitly retain every unknown listed above;
2. finalize the WU-055 architecture decision;
3. finalize the implementation file set;
4. implement and test WU-055;
5. create/update the canonical WU-055 architecture/evidence record;
6. update Phase 3 status and development continuity only after validation;
7. commit and push the resulting project changes.

This reconnaissance should **not be deleted** after WU-055 completion. It remains evidence of the pre-implementation state and the reasoning that led to the authenticated spike and final design.

