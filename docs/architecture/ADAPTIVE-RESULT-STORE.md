# Adaptive Project-Local Result Store

## Purpose

OpenClaw remains the agent runtime and human-facing progress channel. Adaptive
owns the durable handoff protocol, while each project owns the runtime result
data produced for that project.

Human-facing progress and terminal summaries may be truncated or summarized.
They are never authoritative machine-result payloads.


This separation is incident-derived. A 2026-09-13 investigation proved that
OpenClaw progress/history could be truncated around a presentation limit and
that `terminalReply.text` could be a short visible summary rather than the
original payload. The architectural response is therefore not to increase a UI
limit, but to separate the **control/presentation plane** from the
**authoritative result plane**.

```text
worker
  ├─ progress / terminal summary -> OpenClaw
  └─ authoritative result        -> <project>/.adaptive/runs/
                                      |
                                      v
                                  orchestrator
```

## Ownership boundary

Adaptive source code, telemetry and provider-health state belong to Adaptive.
Worker outputs, orchestration artifacts and handoff results belong to the project
being operated on.

The default result tree is therefore **inside the project root**:

```text
<project>/
  .adaptive/
    runs/
      <orchestration>/
        <work-unit>/
          <execution>/
            result.txt
            summary.md
            manifest.json
```

For example, SGFP worker results belong under `SGFP/.adaptive/runs/`; another
project receives its own independent `.adaptive/runs/` tree.

The project-local runtime area is not source code. Adaptive adds `/.adaptive/`
to the repository-local Git exclude file when Git is available, avoiding tracked
`.gitignore` mutations and preventing runtime result data from polluting normal
Git status.

## Project root resolution

The public CLI accepts:

```bash
adaptive-orchestrator orchestrate \
  --project-root /absolute/path/to/project \
  --objective "..."
```

Resolution order for normal CLI use is:

1. explicit `--project-root`;
2. `ADAPTIVE_PROJECT_ROOT`;
3. current working directory.

The inbound OpenClaw bridge should pass the actual governed project root
explicitly. This prevents the Adaptive source repository from accidentally
becoming storage for another project's worker results.

`ADAPTIVE_RESULT_STORE` remains a diagnostic/test override when
`FileResultStore` is created without an explicit project root. Normal CLI
composition passes a project root and therefore uses project-local storage.

## Worker contract

A dispatched worker receives the mandatory Adaptive Worker Protocol and an
absolute result-store target in its task payload. The ownership boundary is:

```text
worker
  -> writes semantic result content
  -> result.txt.tmp
  -> atomic rename to result.txt
  -> may publish summary.md the same way

Adaptive
  -> reads final result.txt
  -> computes exact UTF-8 result_bytes
  -> computes result_sha256
  -> binds orchestration / Work Unit / execution identity
  -> binds Worker Protocol identity and contract hash
  -> writes manifest.json LAST
  -> rereads and verifies the published result
  -> emits RESULT_VERIFIED
```

The worker **must not create or edit** `manifest.json` or
`manifest.json.tmp`. Machine integrity metadata belongs to deterministic
Adaptive infrastructure, not to the LLM worker. Runtime `COMPLETED` alone does
not satisfy the authoritative completion contract.

The result tree is organized by **orchestration -> Work Unit -> execution**, not
by agent name. A retry therefore receives another execution directory while the
previous attempt remains available for audit/recovery.

The normative cross-cutting contract is documented in
[`WORKER-PROTOCOL-V1-RESULT-TRANSPORT.md`](WORKER-PROTOCOL-V1-RESULT-TRANSPORT.md).

## Dependency fan-in by reference

Accepted Work Units that were recovered from the authoritative Result Store carry
their `manifest.json` path as a stable result reference.

When a downstream Work Unit depends on such a result, Adaptive does **not** copy
the dependency payload into the next agent conversation. Instead it sends a
small dependency reference and exposes the manifest path through
`TaskPackage.artifacts`:

```text
Worker A
  -> result.txt + manifest.json
  -> Orchestrator validates result
  -> dependency reference only
  -> Worker B reads manifest/result_file when needed
```

This removes dependency-result size from the agent-to-agent message transport.
A 5 KB, 50 KB or larger result is represented in the downstream context by the
same small reference.

For compatibility with runtimes that have not adopted Result Store publication,
Adaptive retains a bounded legacy inline fallback controlled by
`dependency_context_chars`. The fallback is explicitly labeled legacy and is
not the preferred machine-result channel.

Replanning state summaries follow the same principle: when an authoritative
result reference exists, the planner receives the reference rather than a copied
result body.

## Authority and integrity

The manifest is the completion sentinel. Adaptive accepts a stored result only
after verifying:

- orchestration identity;
- Work Unit identity;
- execution identity;
- `complete=true`;
- result file presence;
- integer UTF-8 byte length (`result_bytes`);
- 64-character hexadecimal SHA-256 (`result_sha256`);
- Adaptive publisher identity;
- Worker Protocol identity and contract hash.

These fields are mandatory for the authoritative contract. Missing, malformed,
wrongly typed, or mismatched integrity metadata fails closed; Adaptive does not
silently coerce invalid machine-contract values.

When a verified Result Store payload exists it is authoritative.
`chat.history` is only a backwards-compatible presentation fallback for workers
that have not yet published through the Result Store. It is not a durable
machine-result contract.

## Isolation

A target path must remain below:

```text
<project>/.adaptive/runs/
```

Dynamic orchestration, Work Unit and execution identifiers are sanitized before
being used as directory components. Adaptive also checks that the resolved
execution directory is a descendant of the configured Result Store root.

The worker contract explicitly prohibits writing result-store data outside the
assigned execution directory.

## Global Adaptive state

Project result data does **not** belong under Adaptive's source repository.

Global Adaptive-owned operational state may continue under locations such as:

```text
~/.local/state/adaptive-ai-orchestrator/
  observability.jsonl
  provider-incidents.jsonl
  runtime/
  locks/
```

Those records describe the orchestrator/runtime itself. They are distinct from
project-owned worker results.


## Control plane vs result plane

```text
OpenClaw control/presentation plane
  dispatch | liveness | wait | progress | cancel | terminal summary

Adaptive project-local result plane
  result.txt | summary.md | manifest.json | integrity metadata | references
```

The control plane may use bounded or summarized representations. The result plane
must preserve the complete authoritative payload.

This distinction prevents:

- progress truncation from corrupting machine results;
- terminal summaries from masquerading as full results;
- agent-to-agent fan-in from scaling with conversation payload size;
- one project's runtime data from accumulating in Adaptive's own repository.

## Lifecycle and reconciliation invariant

Run identity is preserved before waiting. A wait timeout is treated as an
observation timeout unless execution failure is independently proven. The same
run is reconciled before redispatch so side-effecting work is not duplicated
merely because result observation was delayed.

## Design invariants

- Project results are project-local by default.
- One project's result tree must not contain another project's execution data.
- Progress truncation must not truncate the authoritative machine result.
- Terminal summaries are not machine results.
- The worker never owns the integrity manifest; Adaptive writes it last.
- A manifest is accepted only after the complete result exists.
- Runtime `COMPLETED` is not the same state as `RESULT_VERIFIED`.
- Result identity is scoped to orchestration, Work Unit and execution.
- Result integrity is verified before evaluation.
- Runtime result files are state, not source code, and are never committed.
- Run identity is preserved before waiting so the same execution can be reconciled.
- Wait timeout is not automatically run failure.
- Progress/history and terminal summary never become authoritative merely by field name.
- Transport robustness requires real SMALL/MEDIUM/LARGE E2E validation, not unit tests alone.
