# Incident: Planner result truncation and machine-result handoff gap

**Date:** 2026-09-13  
**Status:** corrected in Adaptive architecture; live SGFP E2E still pending  
**Scope:** OpenClaw ↔ Adaptive result transport, planner output integrity, agent-to-agent fan-in

## Executive summary

A large Adaptive Planner run failed with invalid JSON near the end of the payload.
The first visible symptom looked like a model formatting problem, but repeated
diagnostics showed that the model had produced a larger result and the corruption
happened in the transport/presentation path.

The investigation ultimately established three distinct channels:

1. **progress/history** — human-facing, allowed to truncate;
2. **terminal reply** — human-facing terminal summary, allowed to summarize;
3. **machine result** — must be complete, durable, identifiable, and verifiable.

OpenClaw exposed the first two but no durable full-result route suitable for
Adaptive's machine consumption. Rather than turning OpenClaw's presentation
channel into a result database, Adaptive adopted its own project-local durable
Result Store and changed dependency fan-in to pass references instead of copying
large outputs through conversations.

## Initial symptom

A large planning request failed before fan-out with a JSON decode error near the
end of the response. A controlled reproduction showed:

- SMALL: parsed successfully;
- MEDIUM: parsed successfully in the old history path;
- LARGE: failed at roughly the same output size;
- raw diagnostic artifact ended mid-property and contained literal
  `...(truncated)...`.

The critical point was that this marker was not emitted by the model.

## Root-cause trace

### 1. OpenClaw progress formatting

OpenClaw runtime code was traced to a presentation formatter with an 8000-character
default cap. It receives full text and formats a progress representation using a
truncation marker.

This established:

> the progress representation is not a safe machine-result channel.

Increasing the 8000-character cap was rejected as a structural fix. A progress
limit is legitimate for UI/human output; the defect was using that channel as
machine-readable transport.

### 2. agent.wait contract

The real `agent.wait` contract exposed run lifecycle metadata and a
`terminalReply.text` value. SMALL initially suggested that this might be the
full machine result.

A controlled MEDIUM test disproved that assumption:

- source payload: 5266 characters;
- `terminalReply.text`: 237 characters;
- source BEGIN marker: absent from terminal reply;
- source END marker: absent from terminal reply;
- terminal reply was not the original JSON.

Source inspection confirmed that terminal reply is built from visible/final
assistant text for terminal presentation and does not reference an authoritative
full-result object.

This established:

> a terminal-looking field is not automatically an authoritative result.

### 3. Wait timeout semantics

The client/runtime contract was also inspected because one MEDIUM attempt timed
out during waiting.

The investigation established:

- per-call `agent.wait` timeout is an observation window;
- wait timeout does not itself cancel the run;
- cancellation is a separate operation;
- same-run waiting/reconciliation is supported;
- Adaptive must preserve run identity before waiting and must not redispatch work
  only because observation timed out.

This is an independent lifecycle invariant even though the later MEDIUM test
completed without timeout.

### 4. Missing full-result API

No recoverable OpenClaw route was found that satisfied all of:

- complete original result;
- durable after worker completion;
- stable result identity;
- retrieval by run/session/result reference;
- integrity metadata;
- independence from progress formatting and terminal summaries.

Classification:

- `TERMINAL_REPLY_IS_SUMMARY`;
- `PROGRESS_CHANNEL_ONLY_EXPOSED`;
- `OPENCLAW_MACHINE_RESULT_API_GAP`;
- full result not proven persisted in a recoverable authoritative form.

## Failed or rejected approaches

### Treat chat.history as authoritative

Rejected. It may look complete for smaller outputs but is a presentation path and
can truncate larger payloads.

### Treat terminalReply.text as authoritative

Rejected by MEDIUM evidence. It was a short summary, not the original payload.

### Increase the 8000-character progress cap

Rejected as a structural fix. It would only move the failure boundary and keep
machine transport coupled to a human presentation channel.

### Retry the same large planner request blindly

Rejected. Repeating a transport-corrupted request does not diagnose the boundary
and can create waste or duplicate work.

### Permanently patch a hashed OpenClaw dist bundle

Rejected. Permanent behavior must not depend on fragile edits to generated
distribution artifacts.

## Adopted solution

Adaptive owns a **project-local Result Store**:

```text
<project>/.adaptive/runs/
  <orchestration>/
    <work-unit>/
      <execution>/
        result.txt
        summary.md
        manifest.json
```

The worker publishes the authoritative payload through an atomic protocol:

1. write `result.txt.tmp`;
2. atomically rename to `result.txt`;
3. optionally publish `summary.md`;
4. write `manifest.json.tmp`;
5. atomically rename `manifest.json` last.

The manifest carries execution identity, `complete=true`, byte length, and
SHA-256. Adaptive validates these fields before accepting the result.

OpenClaw remains the control/presentation plane:

- dispatch;
- liveness;
- bounded wait/reconciliation;
- progress;
- cancellation;
- short terminal summaries.

The Result Store is the authoritative data plane.

## Agent-to-agent consequence

Dependency fan-in now passes a stable manifest reference instead of copying the
dependency payload into the next worker conversation.

```text
Worker A -> result store -> manifest reference -> Worker B
```

The size of Worker A's result no longer determines the size of the orchestrator's
handoff message.

A bounded inline fallback remains only for legacy runtimes that have not adopted
the Result Store contract.

## Project ownership decision

Result data belongs to the project being operated on, not to the Adaptive source
repository.

Therefore SGFP runtime results live under `SGFP/.adaptive/`; another project
gets its own independent tree. Adaptive-owned global state remains limited to
orchestrator/runtime concerns such as telemetry, provider health, locks, and
global runtime metadata.

This avoids cross-project data ownership leakage and keeps runtime artifacts out
of Adaptive's own repository.

## Validation performed

Executable coverage now includes:

- result payload above 12,000 characters recovered intact;
- completion manifest written last;
- byte-length/SHA-256 mismatch rejection;
- execution identity mismatch rejection;
- path sanitization;
- project-local default result root;
- isolation between two projects with identical logical IDs;
- local Git exclusion without modifying tracked `.gitignore`;
- Gateway preference for authoritative Result Store without reading
  `chat.history`;
- wait timeout classified as RUNNING rather than cancelled/failed;
- dependency fan-in by reference with the large dependency body absent from the
  downstream context;
- bounded legacy inline fallback.

The final repository suite after related merges reported 396 passing tests. A
real SGFP SMALL/MEDIUM/LARGE E2E remains the next operational proof.

## Permanent lessons

1. **Terminal is not synonymous with integral.**
2. **Presentation is not transport.**
3. **Result integrity must be proven, not inferred from field names.**
4. **Persist run identity before waiting.**
5. **Wait timeout is not automatically run failure.**
6. **Reconcile the same run before redispatch.**
7. **Use staged payload tests to find transport boundaries.**
8. **Do not fix a data-plane problem by increasing a UI/progress limit.**
9. **Large agent outputs should move by durable reference, not conversation copy.**
10. **Project-owned runtime results belong inside the governed project boundary.**
11. **Manifest-last atomic publication prevents half-written results from being accepted.**
12. **Unit tests are necessary but the real runtime path still requires E2E proof.**

## Next proof

Before resuming broad SGFP multiagent work, execute a real, read-only validation
through the installed OpenClaw/Adaptive runtime:

1. SMALL;
2. MEDIUM;
3. LARGE (>12k);
4. dependency fan-in by reference;
5. verify the SGFP `.adaptive/runs/` tree;
6. verify no large dependency body is copied into downstream conversation context;
7. verify hashes/completeness;
8. only then classify the transport as operationally proven.
