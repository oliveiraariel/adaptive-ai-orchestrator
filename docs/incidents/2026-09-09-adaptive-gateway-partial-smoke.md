# Incident: partial Phase 1 smoke execution

Date: 2026-09-09
Classification: Adaptive/Gateway operational incident

## Evidence

- `orchestration_id=e714834fcd3945e59dd464d55af595f0`
- task/session/run: `task:e714834fcd3945e59dd464d55af595f0`,
  `agent:main:orchestrator:task:e714834fcd3945e59dd464d55af595f0`,
  `orchestrator:task:e714834fcd3945e59dd464d55af595f0`
- persisted events contain routing, dispatch, runtime-result, and
  `evaluation-finalized` for `wu:e714834fcd3945e59dd464d55af595f0`, ending
  `COMPLETED/ACCEPTED`.
- no `work_unit_created`, `worker_dispatched`, or terminal event exists for a
  second Work Unit in that orchestration.
- Gateway logs record `session observer model call timed out or was cancelled`,
  followed by the observer being disabled, and the run ending with
  `stopReason=stop`.

## Determination

The partial result is not an LLM verdict failure and is not recoverable as a
two-Work-Unit run: one task-level execution completed, while the second unit
was never created or dispatched. There is no active worker to await and no
authoritative terminal record from which to reconstruct the missing unit.

The separate project run `b9f088fec4614905b45b78d47190ce48` showed the same
handoff failure: `discover-smoke-contract` completed, while dependent
`run-observability-smoke` remained unfinished after the planner returned
`ADAPTIVE_REPLAN_REQUIRED`.

## Boundary

No Control Room code was changed for this incident. The accepted
`work_unit_ready` fix and its 6/6 tests remain the current Control Room state.
