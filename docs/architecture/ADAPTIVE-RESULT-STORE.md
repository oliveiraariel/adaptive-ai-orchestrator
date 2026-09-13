# Adaptive File Result Store

## Purpose

OpenClaw remains the agent runtime and progress channel. Adaptive owns the durable
handoff contract for machine-readable worker results.

Human-facing progress and terminal summaries may be truncated or summarized.
They are never authoritative result payloads.

```text
worker
  ├─ progress / terminal summary -> OpenClaw
  └─ authoritative result        -> Adaptive Result Store
                                      |
                                      v
                                  orchestrator
```

## Default location

The store is outside the project repository:

```text
${XDG_STATE_HOME:-~/.local/state}/adaptive-ai-orchestrator/result-store/
  <orchestration>/
    <work-unit>/
      <execution>/
        result.txt
        summary.md
        manifest.json
```

Set `ADAPTIVE_RESULT_STORE` to override the root for diagnostics/tests.

The manifest is written last and is the completion sentinel. Adaptive verifies
execution identity, byte length and SHA-256 before accepting the result.

## Worker contract

A dispatched worker receives an absolute result-store target in its task payload.
It must:

1. write the full requested payload to `result.txt.tmp`;
2. atomically rename it to `result.txt`;
3. optionally publish `summary.md` the same way;
4. write `manifest.json.tmp`;
5. atomically rename the manifest to `manifest.json` **last**;
6. keep its conversational reply short.

The result is organized by orchestration -> Work Unit -> execution, not by agent
name. This preserves retries and lets different agents execute later attempts of
the same Work Unit without losing provenance.

## Authority

When a verified store result exists, it is authoritative. OpenClaw
`chat.history` remains a backwards-compatible fallback for workers that have
not yet published through the store, but is treated as a presentation channel,
not a durable machine-result contract.

## Design invariants

- Progress truncation must not truncate the machine result.
- Terminal summaries are not machine results.
- A manifest is accepted only after the complete result exists.
- Result identity is scoped to orchestration, Work Unit and execution.
- Result integrity is verified before evaluation.
- Runtime result files are state, not source code, and are never committed.
