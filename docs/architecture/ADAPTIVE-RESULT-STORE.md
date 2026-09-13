# Adaptive Project-Local Result Store

## Purpose

OpenClaw remains the agent runtime and human-facing progress channel. Adaptive
owns the durable handoff protocol, while each project owns the runtime result
data produced for that project.

Human-facing progress and terminal summaries may be truncated or summarized.
They are never authoritative machine-result payloads.

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

A dispatched worker receives an absolute result-store target in its task payload.
It must:

1. write the complete authoritative payload to `result.txt.tmp`;
2. atomically rename it to `result.txt`;
3. optionally publish `summary.md` the same way;
4. write `manifest.json.tmp`;
5. atomically rename the manifest to `manifest.json` **last**;
6. keep its conversational reply short.

The result tree is organized by **orchestration -> Work Unit -> execution**, not
by agent name. A retry therefore receives another execution directory while the
previous attempt remains available for audit/recovery.

## Authority and integrity

The manifest is the completion sentinel. Adaptive accepts a stored result only
after verifying:

- orchestration identity;
- Work Unit identity;
- execution identity;
- `complete=true`;
- result file presence;
- byte length when supplied;
- SHA-256 when supplied.

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

## Design invariants

- Project results are project-local by default.
- One project's result tree must not contain another project's execution data.
- Progress truncation must not truncate the authoritative machine result.
- Terminal summaries are not machine results.
- A manifest is accepted only after the complete result exists.
- Result identity is scoped to orchestration, Work Unit and execution.
- Result integrity is verified before evaluation.
- Runtime result files are state, not source code, and are never committed.
