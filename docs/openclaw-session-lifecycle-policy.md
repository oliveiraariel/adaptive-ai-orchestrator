# OpenClaw Session Lifecycle Policy

## Purpose

Adaptive creates one isolated OpenClaw session key per orchestrated task:

```text
agent:<agent-id>:orchestrator:<task-id>
```

Those sessions are execution containers, not the source of truth for project planning. Leaving every completed worker session active indefinitely clutters the OpenClaw Control UI and increases the active session population. Deleting them immediately, however, would be unnecessarily destructive while Adaptive still relies on OpenClaw transcripts as an important recovery and diagnostic source.

This policy therefore uses **state-based archival** rather than fixed elapsed-time cleanup.

## Decision

### Completed execution

Archive the OpenClaw session **immediately after all of the following are true**:

1. `agent.wait` reports a terminal successful runtime state;
2. `chat.history` is read successfully;
3. the final assistant output and available usage/cost metadata have been captured into the Adaptive runtime result.

There is intentionally no 30-minute, 60-minute, or multi-hour grace timer.

The archive operation preserves the transcript and removes the session from the default active-session view. Archived sessions remain available through OpenClaw's archived-session surfaces and can be restored if investigation is required.

### Cancelled execution

When Adaptive explicitly cancels a run, it first calls `sessions.abort`. Only after that abort boundary succeeds does it attempt to archive the corresponding session.

### Failed or incomplete result capture

Do **not** auto-archive when:

- the run is still running or times out;
- OpenClaw reports runtime failure before a usable result is recovered;
- `chat.history` cannot be read;
- no assistant output can be extracted;
- the session contains foreign active work that cannot be proven to belong to the completed Adaptive run.

These sessions remain visible because their operational value is diagnostic or recovery-oriented.

### Archive failure

Archival is a cleanup concern and must never turn a successfully completed Work Unit into a failed Work Unit.

Adaptive therefore treats archive failures as best-effort outcomes. A failed archive leaves the session active for later inspection. The returned runtime payload records a sanitized `session_lifecycle` outcome when automatic archival is enabled.

## Identity safety

OpenClaw requires archive/restore lifecycle changes to use an observed durable `sessionId` as `expectedSessionId`.

Adaptive follows that contract:

1. read the session with `sessions.describe`;
2. capture the returned `sessionId`;
3. refuse cleanup when unrelated active run IDs are visible;
4. call `sessions.patch` with:

```json
{
  "key": "<session-key>",
  "expectedSessionId": "<observed-session-id>",
  "archived": true
}
```

This prevents a stale task key from archiving a replacement session generation.

Retryable OpenClaw `UNAVAILABLE` archive responses are retried a small bounded number of times using the **same observed session ID**, so a retry cannot silently retarget a newer session generation.

## Why state-based archival instead of a timer

OpenClaw's native sub-agent lifecycle uses a default `archiveAfterMinutes` value of 60 minutes, but that timer is best-effort and pending timers can be lost when the Gateway restarts. Adaptive is not using those native sub-agent timers for its per-Work-Unit Gateway sessions.

For Adaptive, the meaningful lifecycle boundary is not elapsed time; it is **result ownership transfer**:

```text
OpenClaw run
    -> terminal runtime state
    -> history/result captured by Adaptive
    -> session archived
```

This is deterministic, restart-independent at the decision point, and avoids keeping completed worker sessions active merely to satisfy an arbitrary clock delay.

## Deletion policy

Adaptive does **not** automatically delete archived sessions in this phase.

Reasons:

- OpenClaw archive already removes completed workers from the active list while retaining the transcript;
- archived transcripts remain useful for debugging, audit, and recovery;
- Adaptive's current project-state repository still has an in-memory implementation, so irreversible retention cleanup should not be coupled to worker completion yet.

Automatic deletion/retention should be added only after durable Adaptive project/result persistence is the authoritative source of truth. At that point a separate retention policy can safely retire old archived worker sessions.

## Operational configuration

Lifecycle-safe automatic archival is a **core Adaptive default**. When no override is supplied, completed and explicitly cancelled Adaptive-owned worker sessions are archived according to the safety rules above regardless of how Adaptive is entered, including:

- OpenClaw Dashboard / Chat through `adaptive-orchestrator-bridge`;
- direct Adaptive CLI execution;
- the project activation script;
- library/integration construction of `OpenClawGatewayClient` with default lifecycle settings.

No shell activation step is required merely to enable this behavior.

To temporarily keep completed sessions active while diagnosing lifecycle behavior, set:

```bash
export ADAPTIVE_SESSION_AUTO_ARCHIVE=0
```

The project activation script preserves an explicitly supplied value. Without an explicit override, it continues to expose the enabled state for local development convenience.

Library/integration callers can override the environment-derived default explicitly through `GatewayConfig.archive_completed_sessions` and `GatewayConfig.archive_cancelled_sessions`.

## OpenClaw references

The implementation is based on OpenClaw's documented session lifecycle behavior:

- Sessions CLI and archive semantics: https://docs.openclaw.ai/cli/sessions
- Gateway session control and `expectedSessionId`: https://docs.openclaw.ai/gateway/protocol/rpc-session-control
- Session maintenance and retention: https://docs.openclaw.ai/sessions
- Native sub-agent auto-archive behavior: https://docs.openclaw.ai/gateway/config-tools/sessions-and-subagents

## Effective policy summary

| Session condition | Adaptive action |
| --- | --- |
| Running / queued | Keep active |
| Completed but result not captured | Keep active |
| Completed and result captured | Archive immediately |
| Completed but archive temporarily unavailable | Retry boundedly, then keep active on failure |
| Foreign active run detected on the session | Keep active |
| Explicitly cancelled and abort succeeded | Archive |
| Runtime/result retrieval error | Keep active for diagnosis |
| Archived session | Preserve; no automatic delete in this phase |