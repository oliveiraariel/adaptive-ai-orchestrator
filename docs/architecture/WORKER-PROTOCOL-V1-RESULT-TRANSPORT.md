# Worker Protocol v1, Result Transport and Reference Fan-in

**Status:** validated architectural knowledge  
**Scope:** Adaptive-owned runtime transport and downstream context transfer

## Purpose and authority

The `adaptive-worker-protocol` is infrastructure owned by Adaptive. It is
inserted before task, context, skills and objective in the worker message. It
is mandatory and cannot be replaced or redefined by a Skill. Skills add
domain know-how; they do not override execution, result transport, completion,
recovery or integrity semantics.

This document records validated operational knowledge from:

```text
MEDIUM → LARGE → reference-only FAN-IN
```

It is evidence and architectural guidance, not a product-specific rule and not
a Skill. Existing normative architecture and implementation remain authoritative
for details not stated here.

## Worker Protocol v1 invariants

The protocol declares, at minimum:

```text
name: adaptive-worker-protocol
version: 1
mandatory: true
chat_authoritative: false
worker_writes_manifest: false
adaptive_finalizes_manifest: true
completion_requires: RESULT_VERIFIED
```

The worker owns only result content. It writes `result.txt.tmp` and atomically
renames it to `result.txt`; it may do the same for `summary.md`. The worker
must not create or edit `manifest.json` or `manifest.json.tmp`.

After runtime completion, Adaptive owns finalization: it reads the final result,
computes exact UTF-8 byte length and SHA-256, associates protocol identity and
contract hash, writes the manifest last, rereads the result, and emits
`RESULT_VERIFIED`. Runtime `COMPLETED` alone is not authoritative completion.

The manifest is a completion sentinel and must contain valid execution
identity, `complete: true`, `publisher: adaptive-result-store`, integer
`result_bytes`, a 64-character hexadecimal `result_sha256`, and Worker Protocol
identity/contract hash. Missing, malformed or mismatched metadata fails closed;
no silent coercion or fallback is allowed.

## Result transport boundary

Progress messages, terminal replies and `chat.history` are human/diagnostic
channels. They are not authoritative machine-result transport and may be
truncated or formatted differently. The project-local Result Store is the
authoritative channel for accepted results, especially large results. Size is
measured from the stored artifact's exact UTF-8 bytes, never UI token counts or
conversational text.

Hashes of content, contracts and Git commits are identifiers for integrity or
provenance, not credentials. Credentials must not appear in prompts, logs or
persisted learning artifacts.

## Liveness and same-run recovery

Heartbeat is emitted by the runtime/harness, not inferred from LLM messages.
The tested policy uses a 30-second heartbeat, a 90-second silence window that
may mark an execution `SUSPECT` without cancelling it, and a separate hard
observer deadline. Observer unavailability is not proof of worker failure.
Reconciliation must happen before recovery or redispatch.

`dispatch` and `wait` are distinct operations. Dispatch persists execution
identity before returning; a later process may wait on the same `external_id`,
`runId`, `execution_id` and Result Store target. Observation failure or process
restart must not create a duplicate execution automatically.

## Reference-only fan-in

For a large accepted upstream result, fan-in should prefer a structured
reference over copying the payload into the downstream prompt:

```text
Worker A
   → authoritative Result Store
   → structured result reference
   → Worker B loads the artifact on demand
```

The reference contains only minimum location and verification metadata: source,
orchestration/work-unit/execution identity, manifest location, byte length,
result hash and authoritative status. Worker B validates manifest, identity,
byte length and hash before consuming the upstream result. A reference is not
an inline substitute for the result.

Reference-only fan-in is preferred when the upstream artifact is authoritative,
readable by the downstream worker and materially larger than useful metadata.
Measure bytes not retransmitted and artifacts reused; do not claim exact token
savings without measuring the relevant tokenizer.

## Validated evidence

The real SGFP sequence established:

- MEDIUM: protocol ordering, Adaptive-owned manifest, deterministic bytes/SHA,
  contract hash, `RESULT_VERIFIED`, heartbeat and same-run recovery;
- LARGE: an authoritative 32,524-byte result survived without inline return;
- FAN-IN: Worker B consumed that upstream by structured reference, validated
  identity/bytes/SHA and produced a verified 4,339-byte synthesis without
  copying the upstream payload into dispatch context.

These observations validate transport and recovery. They do not prove semantic
correctness of the SGFP audit, WordPress integration, database behavior or any
product requirement.

## Causal failure lessons

Earlier failures exposed truncated progress output; manifests missing integrity
fields; `result_bytes` serialized as a string; trust in an LLM to construct a
machine envelope; runtime code-identity drift; virtual-environment symlink
dereferencing; observer timeout treated as worker failure; and absence of
separate dispatch/wait recovery.

> **Fix the contract, not the symptom.**

## Provenance and non-duplication

Existing documents already describe generic fan-in, execution references,
liveness, continuity and governed learning. This document consolidates their
cross-cutting Worker Protocol and reference-only transport invariants and
points to those documents rather than duplicating subsystem designs. The
learning is evidence-backed and must not silently become routing policy or a
product rule.
