# Incident follow-up — durable single-worker continuity

**Date:** 2026-10-10  
**Status:** implementation and deterministic local integration validated; the
incident remains **not fully resolved operationally** pending a representative
installed end-to-end run with an approved real provider budget.  
**Predecessor:** `2026-10-10-single-unit-false-success.md`

## Scope and non-goals

Phase 1 remains preserved on
`fix/single-unit-completion-integrity` (`ddff729`, `43eaa5a`). It made bounded
`run` fail closed when semantic acceptance or the worker completion footer is
missing. This follow-up does not weaken that guard, create a second scheduler,
push, merge, deploy, contact a provider, or use the production SGFP project.

The scope is the missing admission choice: one Work Unit or one executor must
not be mistaken for a bounded, non-durable execution when the request needs a
checkpoint, controller guardian, recovery, or resume.

## Correction

The Bridge adds the private selector `--durable-single-worker`.

```text
Bridge --durable-single-worker
  -> Adaptive orchestrate --max-concurrency 1
  -> existing checkpoint / guardian / continuous scheduler / Recovery Loop
```

It requires an explicit existing `--project-root`, rejects a conflicting worker
ceiling, and keeps the bridge-allocated orchestration identity. It delegates to
the existing `orchestrate` path; no parallel scheduler was added.

`--single-unit` remains available only for genuinely bounded work and the
Bridge now rejects it before dispatch unless it includes a non-empty literal
`--accept`. This is compatible with the Phase 1 CLI contract and prevents a
consumer from discovering the missing criterion only after it has started a
runtime.

## Evidence map

| Required behavior | Deterministic evidence |
| --- | --- |
| One-worker durable routing | Bridge test asserts `--durable-single-worker` invokes `orchestrate` and appends `--max-concurrency 1`. |
| Bounded compatibility | Bridge tests require `--accept` for `--single-unit`; Adaptive CLI regression tests retain rejection of omitted/liveness-only criteria. |
| Durable checkpoint and semantic completion | Cross-process local E2E runs the actual Adaptive CLI with a simulated Gateway, a single-work-unit static plan, literal acceptance evidence, and structured completion footer. It asserts the durable checkpoint is terminal under the requested id. |
| Partial output remains open | `test_worker_assignment_requires_structured_completion_footer` rejects missing/partial completion as success. |
| Recoverable worker failure | `test_transient_result_failure_retries_then_completes` exercises retry to completion. |
| Controller death/recovery, same identity, no duplicate worker | `test_resume_reconciles_active_worker_then_continues_frontier_without_redispatch` recovers the persisted active execution, finishes its frontier, and proves a second resume performs no duplicate submit/retrieve. |
| Supervisor detection | Supervisor tests distinguish missing/stale controller from a fresh heartbeat and only resume the former. Guardian tests verify a detached watcher targets the exact id without exposing secrets in argv. |
| Persistent recovery after partial work | `test_strategy_exhaustion_reanalyzes_executes_retests_learns_and_closes` exercises partial output, remediation, retest, learning lifecycle, and closure. |
| Control Room update | The cross-process local E2E starts the real Control Room server with isolated source/store paths, lets it tail actual Adaptive JSONL, then asserts one closed operational session and one `COMPLETED` / `ACCEPTED` Work Unit. |

## Validation record

All runs are local and deterministic; the Gateway/provider is simulated where
execution is required.

- pre-change Adaptive suite: `608 passed`;
- pre-change Control Room source and active-runtime suites: `58 passed` each;
- post-change Bridge suite: `30 passed` using the Adaptive project virtualenv
  documented by the Bridge resolution contract;
- focused Phase 2 recovery/integration selection: `9 passed`, including the
  real Control Room cross-process projection test;
- final controlled-branch suites: Adaptive `609 passed`, Bridge `30 passed`,
  Control Room source `58 passed`, and active-runtime checkout `58 passed`;
  none was installed, merged, pushed, or deployed by this phase.

## Installed-state boundary

The tested Adaptive and Bridge source branches are not deployed by this phase.
The currently running Control Room service continues to use its unchanged
runtime checkout. Consequently the deterministic E2E proves integration of the
tested source and the matching Control Room commit, but it is not proof that a
new Bridge source version is installed. Do not mark the incident fully resolved
until the exact tested revisions are installed and a representative approved
non-production provider-backed execution demonstrates automatic recovery.
