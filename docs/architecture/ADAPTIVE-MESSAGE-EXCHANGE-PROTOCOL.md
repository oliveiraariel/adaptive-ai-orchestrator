# Adaptive Message Exchange Protocol (AMEP) v1

## Status

**Mandatory inter-component communication contract for Adaptive runtime payloads.**

AMEP v1 generalizes the proven Worker Result Store principle to every Adaptive component boundary. It separates a small control-plane reference from the complete authoritative payload.

Participants include Owner/bridge, Adaptive, Planner, Workers, Evaluator, Sentinel/watchers, and future subagents/runtime adapters.

## Core invariant

> The conversational/runtime channel carries the reference; the project-local Message Store carries the complete authoritative payload.

    sender
      | writes complete payload
      v
    <project>/.adaptive/messages/<message-id>/
      |-- payload.*
      |-- manifest.json
      |-- reference.json
      |-- events/
      |
      | publishes compact MESSAGE_REF last
      v
    runtime/chat/control plane
      |
      v
    recipient -> verifies reference -> manifest -> payload

This is a transport invariant, not a replacement for domain validation. For example, the Planner's raw response is preserved completely by AMEP before RuntimeProjectPlanner attempts JSON/schema/semantic validation.

## Project-local layout

    <project>/.adaptive/
      messages/<message-id>/
        payload.json | payload.txt | payload.md
        manifest.json
        reference.json
        events/
      inbox/<recipient>/<message-id>.ref.json
      runs/...  # existing Worker Result Store compatibility profile

.adaptive/ is runtime state, not source code. Adaptive keeps it out of normal Git tracking using the repository-local exclude mechanism where possible.

## Publication order

No receiver may observe a message before the complete payload exists:

1. write payload.tmp completely;
2. atomically rename to payload.*;
3. write manifest.json.tmp with identity, schema, byte count and SHA-256;
4. atomically rename to manifest.json;
5. write reference.json with manifest hash and reference hash;
6. publish inbox/<recipient>/<message-id>.ref.json **last**.

The inbox/reference publication is the visibility point.

## Control-plane reference

The wire message is intentionally small. It carries: type=adaptive.message.ref, protocol=adaptive-message-exchange-protocol, version=1, message_id, correlation_id, sender, recipient, message_type, manifest, manifest_sha256 and reference_sha256.

Formal schema: specifications/protocols/amep-message-ref-v1.schema.json

## Full-message manifest

manifest.json describes but does not embed the large payload. It records protocol/version, message identity/correlation, sender/recipient, message_type, versioned schema name, payload file/content-type/bytes/SHA-256, optional reply_to, complete=true and creation timestamp.

Formal schema: specifications/protocols/amep-manifest-v1.schema.json

## First-class payload contracts

| Direction | message_type | schema |
|---|---|---|
| Adaptive -> Planner | planner.request | planner-request/1 |
| Planner -> Adaptive | planner.plan | planner-output/1 |
| Adaptive -> Worker | work.assignment | task-package/1 |
| Worker -> Adaptive | worker.result | worker-result/1 |
| Evaluator -> Adaptive | evaluation.result | versioned evaluator schema |
| Sentinel -> Adaptive | incident.signal | versioned incident schema |

Future components must define a versioned message_type/schema pair instead of inventing an ad-hoc conversational format.

### Planner special rule

Planner output uses JSON under the versioned planner-output/1 contract. The Result Store preserves the original worker result for diagnostics, while Adaptive accepts a Planner document only after strict JSON Schema validation and semantic graph validation. See docs/architecture/PLANNER-STRUCTURED-OUTPUT-CONTRACT.md and specifications/protocols/planner-output-v1.schema.json.

## Responsibilities

### Sender

The sender produces semantic payload only. It does not invent message paths, ids, hashes, manifests or inbox paths.

### FileMessageStore

The shared infrastructure assigns message identity, writes atomically, generates manifest integrity metadata, generates the compact reference, publishes the inbox reference last, verifies reference/manifest/payload, and records lifecycle events.

### Recipient

The recipient validates the reference, verifies manifest SHA-256 and identity, verifies payload bytes/SHA-256, reads the complete payload, then applies payload-specific schema/semantic validation.

## Reply correlation

Replies are separate immutable messages. They keep the correlation_id, receive their own message_id, and may set reply_to to the request message. Published payloads/manifests are not mutated; lifecycle changes are events.

## Worker Result Store compatibility

The existing Worker Result Store remains a hardened compatibility/safety profile:

    worker writes result.txt.tmp -> atomic rename result.txt
    Adaptive finalizes Result Store manifest
    Adaptive publishes verified content as worker.result through AMEP
    Adaptive reads/verifies AMEP reference before exposing result upward

Worker Protocol v1 includes the AMEP contract in its hashed mandatory protocol. Skills, task prompts and worker context cannot override it.

The Result Store is not removed by AMEP v1. A future migration may collapse the stores only after equivalent recovery and integrity guarantees are proven.

## OpenClaw Gateway boundary

New dispatches publish the complete TaskPackage to FileMessageStore. The Gateway agent RPC receives only the AMEP MESSAGE_REF. On return, the verified Result Store payload is published again as an AMEP result and re-read through the reference before reaching the application layer.

chat.history may remain diagnostic/presentation fallback for legacy paths. It is never authoritative for mandatory AMEP/Worker Protocol execution.

## Failure semantics

AMEP separates transport from content failures:

- missing manifest: transport failure;
- manifest hash mismatch: integrity failure;
- payload byte/hash mismatch: integrity failure;
- payload unavailable: transport failure;
- raw Planner payload with malformed JSON: Planner/content failure, not AMEP transport failure;
- valid JSON with invalid plan schema: Planner/schema failure.

## Design invariants

1. Chat/history is control/presentation plane, never the authoritative home of large machine payloads.
2. Every important message has identity, correlation, sender, recipient, type, schema version and integrity metadata.
3. Payload publication precedes reference publication.
4. Writes are atomic.
5. Recipients verify before consuming.
6. Payload-specific validation happens after transport verification.
7. All Adaptive participants use shared infrastructure rather than inventing component-specific file protocols.
8. Planner, Worker, Evaluator, Sentinel and future components use versioned message types/contracts.
9. Existing hardened result/recovery mechanisms are integrated, not discarded.
10. Communication artifacts are reusable operational evidence for incidents and governed learning.

## Implementation map

- src/application/message_protocol.py — protocol/reference contract
- src/infrastructure/message_store.py — durable project-local data plane
- src/application/worker_protocol.py — mandatory worker binding
- src/domain/task_package.py — request/result message contract fields
- src/application/run_orchestration.py — propagation
- src/application/runtime_project_planner.py — Planner message typing
- src/infrastructure/openclaw_gateway_client.py — publication/resolution at runtime boundary
- tests/infrastructure/test_message_store.py — integrity and large-payload tests
