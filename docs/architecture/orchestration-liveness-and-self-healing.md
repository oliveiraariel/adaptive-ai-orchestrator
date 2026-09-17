# Orchestration liveness and self-healing

## Purpose

Adaptive project orchestration must never imply that background work is active solely because a durable checkpoint still contains non-terminal Work Units. Runtime activity and persisted intent are separate facts.

This policy makes project-mode execution finite, observable, and self-healing within explicit budgets.

## Mandatory invariants

1. **Controller heartbeat** — while an orchestration controller is actually executing, it publishes a durable `orchestration_heartbeat` and refreshes `.adaptive/orchestration-liveness/<id>.json`.
2. **Worker heartbeat** — delegated project executions are supervised while their result is pending. Runtime-confirmed observations are persisted under `.adaptive/liveness/` and emitted as `worker_heartbeat` events.
3. **No silent infinite wait** — a worker has a bounded hard deadline. On expiry Adaptive requests cancellation, returns control to the scheduler, and treats the event as a recoverable runtime failure.
4. **RETURNED is active recovery work, not success** — a returned/revision-required Work Unit is retried within its attempt budget. After that, a materially different strategy generation is required.
5. **Strategy exhaustion triggers project recovery** — after all bounded strategies are exhausted, the Work Unit becomes `RECOVERY_REQUIRED`. The existing recovery planner may add corrective prerequisite Work Units and then retry the original objective.
6. **Recovery is bounded** — replanning is limited by `max_replans`. The scheduler must not create an infinite repair loop.
7. **Finite terminal closure** — if attempts, strategies, replans, dispatch generations, or dependency topology prevent further useful work, every unfinished Work Unit is terminalized as `BLOCKED`. A completed orchestration may not leave misleading `WAITING`, `REVISION_REQUIRED`, `RECOVERY_REQUIRED`, `RUNNING`, or `EVALUATING` rows behind.
8. **Downstream truthfulness** — work that cannot start because an upstream required dependency failed is reported as blocked, not as pending background work.
9. **Persistent state is not liveness** — a checkpoint proves what was planned and last persisted. Only a fresh heartbeat proves that a controller/worker is currently alive.
10. **No blind duplicate dispatch** — liveness supervision operates on the existing execution. Automatic retry occurs only after the prior run is terminal, returned, failed, or hard-deadline cancellation has been requested.

## Recovery ladder

For a Work Unit that does not satisfy its acceptance surface:

```text
attempt within current strategy
    -> RETURNED / REVISION_REQUIRED
    -> bounded retry
    -> strategy attempt budget exhausted
    -> replacement strategy generation
    -> all strategy generations exhausted
    -> RECOVERY_REQUIRED
    -> project-level corrective replan
    -> corrective prerequisite work
    -> retry original Work Unit
    -> recovery budget exhausted / no valid remediation
    -> BLOCKED (terminal)
    -> required downstream Work Units BLOCKED (terminal)
```

A project finishes only when it is either fully completed or explicitly terminal with its unresolved work closed as blocked.

## Default timing

Project worker supervision uses the existing environment controls:

- `ADAPTIVE_HEARTBEAT_INTERVAL_SECONDS` — default `30` seconds;
- `ADAPTIVE_LIVENESS_TIMEOUT_SECONDS` — default `90` seconds;
- `ADAPTIVE_EXECUTION_HARD_DEADLINE_SECONDS` — default `600` seconds.

The orchestration controller publishes its own heartbeat using:

- `ADAPTIVE_ORCHESTRATION_HEARTBEAT_SECONDS` — default `15` seconds.

The hard deadline is deliberately much shorter than an indefinite background wait while still allowing long model/tool turns. Deployments may tighten it when their workloads are known to be faster.

## Observability events

The canonical observability stream can now contain:

- `orchestration_heartbeat`;
- `worker_heartbeat`;
- `worker_observer_pulse`;
- `worker_liveness_timeout`;
- `orchestration_terminalized`.

These events contain identifiers and bounded operational metadata only. They do not contain prompts, source code, secrets, or raw model reasoning.

## Interpretation

`orchestration_heartbeat` with `controller_state=ACTIVE` is evidence that the controller was alive at that timestamp. If heartbeats stop and there is no later terminal heartbeat, consumers should present the run as **stale/suspect**, not "working in background".

`orchestration_heartbeat` with `controller_state=TERMINAL` is definitive controller closure for that invocation. The project result then states whether work completed, partially completed, or blocked.

`worker_heartbeat` proves that the runtime was observable at that instant. It does not by itself mean acceptance criteria were satisfied.

## Composition

The installed `adaptive-orchestrator` entry point and `python -m adaptive_orchestrator` route project execution through `RunResilientProjectOrchestration`. Single-Work-Unit `run`, `dispatch`, and explicit `wait` commands retain their existing behavior.
