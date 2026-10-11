# Governed Work Unit takeover: direct owner execution and replacement

## Operational contract

An authenticated operator can override the strategy of an existing,
nonterminal Adaptive orchestration. The controller owns the **same Work Unit
ID**, existing dependencies, accepted evidence, and result validation. This
does not launch a second project or mark anything COMPLETE on request.

**Direct owner** means dispatching the existing Work Unit as a fresh
OpenClaw execution under the explicitly specified coordinator agent ID. It
does not grant a worker authority to recursively invoke the Adaptive Bridge.
The output must still pass the usual Result Store and acceptance semantics.

### Manual owner takeover

```bash
adaptive-orchestrator project-status \
  --project-root "/absolute/project/root" \
  --orchestration-id "existing-orchestration-id"

adaptive-orchestrator takeover-work-unit \
  --project-root "/absolute/project/root" \
  --orchestration-id "existing-orchestration-id" \
  --work-unit-id "existing-work-unit-id" \
  --mode direct \
  --owner-agent main \
  --actor operator \
  --reason "Work appears stalled in Control Room; owner takeover requested" \
  --authorize
```

Use the actual coordinator OpenClaw agent id instead of `main` when
configured differently. `takeover-work-unit` returns `REQUESTED`, not
`COMPLETE`. The running controller checks that the target still exists and is
unfinished, attempts cancellation of its current runtime executor and
requires a **confirmed terminal runtime status** before releasing ownership.
If status/cancellation cannot be confirmed, the request remains
`QUIESCING`, and no competing owner worker is dispatched.

The controller then resets the bounded attempt strategy for **that Work Unit
only**, preserves prior records and accepted outputs, and dispatches the
requested owner agent. An independently verified accepted result moves the
takeover to `COMPLETED`; normal policy rejection remains a real failure.

For a fresh worker rather than the owner use `--mode replacement` and
omit `--owner-agent`. Existing project pause and supervisor commands continue
to own pause/resume. For a **terminal** project, first use the existing
`continue-project` successor procedure; modifying terminal history is
not allowed.

`project-status` includes `governed_takeovers` when present. Control Room
consumers can render `REQUESTED`, `QUIESCING`, `APPLIED`,
`COMPLETED`, `FAILED`, or `SUPERSEDED`.

## Policy-driven owner takeover

When `ADAPTIVE_AUTO_DIRECT_TAKEOVER_ON_EXHAUSTION=1` (default),
the Adaptive controller may choose owner execution after a Work Unit
exhausts its runtime/strategy attempts **only** when:

- execution policy is `AUTONOMOUS` or `AUTONOMOUS_WITH_REVIEW`;
- a distinct `planner_agent` explicitly identifies the coordinator;
- the Work Unit has entered `RECOVERY_REQUIRED`;
- the Work Unit has not already received any takeover request.

For `HUMAN_APPROVAL_REQUIRED`, `HUMAN_EXECUTION_REQUIRED`, or
`FORBIDDEN`, there is no autonomous direct takeover.
Set `ADAPTIVE_AUTO_DIRECT_TAKEOVER_ON_EXHAUSTION=0` to disable
automatic owner escalation while keeping the user command available.

The existing supervised runtime still requests cancellation at its bounded
execution deadline. **Automatic retries fail closed if cancellation cannot be
confirmed**: they do not assume that an observer timeout grants new write
ownership.

## Governance and limitations

- The coordinator process must be alive or recovered by the existing
  supervisor to consume pending requests.
- The existing runtime handles hard deadlines. Status `RUNNING` or fresh
  controller heartbeat does not prove actual worker progress.
- An unresponsive Gateway that cannot confirm worker termination is not a
  safe basis for concurrent writes to a shared workspace; the request holds
  in `QUIESCING` instead of blindly redelegating.
- File state is atomically persisted in
  `.adaptive/governed-takeovers/<sha256(orch_id)>.json`, with locked updates.
  Operator identity/reason and transitions are audited there.
- This change does not deploy the Gateway or modify the project repository.
  It requires the local Adaptive and Bridge installations to be updated.
