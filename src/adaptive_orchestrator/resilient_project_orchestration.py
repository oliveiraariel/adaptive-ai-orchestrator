from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, replace
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any
from uuid import uuid4

from application.agent_runtime import (
    AgentRuntime,
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.continuous_project_orchestration import (
    RunContinuousProjectOrchestration as CoreContinuousProjectOrchestration,
)
from application.execution_liveness import (
    ExecutionLiveness,
    ExecutionLivenessState,
    ExecutionLivenessTimeout,
)
from application.observability import NullObservabilitySink, ObservabilitySink
from application.run_project_orchestration import (
    ProjectOrchestrationRequest,
    ProjectOrchestrationResult,
    ProjectRunStatus,
    WorkUnitExecutionRecord,
)
from domain.task_package import TaskPackage
from infrastructure.execution_liveness_store import FileExecutionLivenessStore


@dataclass(frozen=True)
class _ExecutionContext:
    orchestration_id: str
    work_unit_id: str


class SupervisedAgentRuntime(AgentRuntime):
    """Runtime decorator that turns silent project workers into bounded work.

    The underlying result retrieval is left intact (including Result Store
    reconciliation and provider failover), but it is observed from a daemon
    thread. While retrieval is pending, the decorator asks the runtime for a
    normalized status, persists liveness, and emits heartbeat evidence. A hard
    deadline cancels the stale external execution and raises a liveness timeout;
    the project scheduler then applies its normal bounded retry/strategy/replan
    policy instead of waiting forever.
    """

    def __init__(
        self,
        delegate: AgentRuntime,
        *,
        project_root: Path,
        observability: ObservabilitySink | None = None,
        heartbeat_interval_seconds: float | None = None,
        liveness_timeout_seconds: float | None = None,
        hard_deadline_seconds: float | None = None,
    ) -> None:
        self._delegate = delegate
        self._store = FileExecutionLivenessStore(project_root=project_root)
        self._observability = observability or NullObservabilitySink()
        self._heartbeat_interval = self._positive_seconds(
            heartbeat_interval_seconds,
            "ADAPTIVE_HEARTBEAT_INTERVAL_SECONDS",
            30.0,
        )
        self._liveness_timeout = self._positive_seconds(
            liveness_timeout_seconds,
            "ADAPTIVE_LIVENESS_TIMEOUT_SECONDS",
            90.0,
        )
        self._hard_deadline = self._positive_seconds(
            hard_deadline_seconds,
            "ADAPTIVE_EXECUTION_HARD_DEADLINE_SECONDS",
            600.0,
        )
        if self._liveness_timeout < self._heartbeat_interval:
            raise ValueError(
                "Project liveness timeout must be at least one heartbeat interval."
            )
        if self._hard_deadline < self._liveness_timeout:
            raise ValueError(
                "Project execution hard deadline must be at least the liveness timeout."
            )
        self._contexts_by_execution: dict[str, _ExecutionContext] = {}
        self._contexts_by_external: dict[str, _ExecutionContext] = {}

    @staticmethod
    def _positive_seconds(
        explicit: float | None,
        env_name: str,
        default: float,
    ) -> float:
        raw: float | str = explicit if explicit is not None else os.environ.get(env_name, str(default))
        value = float(raw)
        if value <= 0:
            raise ValueError(f"{env_name} must be positive.")
        return value

    def set_observability(self, observability: ObservabilitySink | None) -> None:
        self._observability = observability or NullObservabilitySink()

    def prebind_external_context(
        self,
        *,
        external_id: str,
        orchestration_id: str,
        work_unit_id: str,
    ) -> None:
        self._contexts_by_external[external_id] = _ExecutionContext(
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
        )

    def submit(self, task: TaskPackage) -> ExecutionReference:
        execution = self._delegate.submit(task)
        context = _ExecutionContext(
            orchestration_id=task.orchestration_id,
            work_unit_id=task.work_unit_id,
        )
        self._bind(execution, context)
        now = time.time()
        self._write_liveness(
            execution=execution,
            context=context,
            state=ExecutionLivenessState.SUBMITTED,
            sequence=0,
            started_at=now,
            last_progress_at=now,
            source="project-dispatch",
        )
        return execution

    def recover_execution(self, external_id: str) -> ExecutionReference:
        execution = self._delegate.recover_execution(external_id)
        context = self._contexts_by_external.get(external_id)
        if context is not None:
            self._bind(execution, context)
        return execution

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return self._delegate.get_status(execution)

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return self._delegate.cancel(execution)

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        context = self._context_for(execution)
        existing = self._store.read(execution.external_id)
        started_at = existing.started_at if existing is not None else time.time()
        sequence = existing.heartbeat_sequence if existing is not None else 0
        previous_state = existing.state if existing is not None else ExecutionLivenessState.SUBMITTED
        last_progress_at = existing.last_progress_at if existing is not None else started_at
        last_runtime_confirmation = time.monotonic()
        started_monotonic = time.monotonic()

        result_queue: Queue[tuple[str, object]] = Queue(maxsize=1)

        def retrieve() -> None:
            try:
                result_queue.put(("result", self._delegate.retrieve_result(execution)))
            except BaseException as exc:  # preserve adapter exception type for scheduler recovery
                result_queue.put(("error", exc))

        Thread(
            target=retrieve,
            name=f"adaptive-result-{execution.id[-24:]}",
            daemon=True,
        ).start()

        while True:
            elapsed = time.monotonic() - started_monotonic
            remaining = self._hard_deadline - elapsed
            if remaining <= 0:
                return self._hard_timeout(
                    execution=execution,
                    context=context,
                    sequence=sequence + 1,
                    started_at=started_at,
                    last_progress_at=last_progress_at,
                )

            try:
                kind, payload = result_queue.get(
                    timeout=min(self._heartbeat_interval, remaining)
                )
            except Empty:
                pass
            else:
                if kind == "error":
                    assert isinstance(payload, BaseException)
                    raise payload
                assert isinstance(payload, AgentRuntimeResult)
                final_state = self._map_status(payload.execution.status)
                sequence += 1
                now = time.time()
                self._write_liveness(
                    execution=payload.execution,
                    context=context,
                    state=final_state,
                    sequence=sequence,
                    started_at=started_at,
                    last_progress_at=now,
                    source="runtime-result",
                )
                return payload

            try:
                runtime_status = self._delegate.get_status(execution)
            except Exception:
                silence = time.monotonic() - last_runtime_confirmation
                if context is not None:
                    self._observability.emit(
                        "worker_observer_pulse",
                        orchestration_id=context.orchestration_id,
                        work_unit_id=context.work_unit_id,
                        execution_id=execution.id,
                        external_id=execution.external_id,
                        status="OBSERVATION_UNAVAILABLE",
                        silence_seconds=round(max(0.0, silence), 3),
                        action="CONTINUE_BOUNDED_WAIT",
                    )
                if silence >= self._liveness_timeout:
                    sequence += 1
                    self._write_liveness(
                        execution=execution,
                        context=context,
                        state=ExecutionLivenessState.SUSPECT,
                        sequence=sequence,
                        started_at=started_at,
                        last_progress_at=last_progress_at,
                        source="runtime-status-unavailable",
                    )
                continue

            last_runtime_confirmation = time.monotonic()
            state = self._map_status(runtime_status)
            now = time.time()
            if state != previous_state:
                last_progress_at = now
                previous_state = state
            sequence += 1
            self._write_liveness(
                execution=execution,
                context=context,
                state=state,
                sequence=sequence,
                started_at=started_at,
                last_progress_at=last_progress_at,
                source="runtime-status",
            )

    def _hard_timeout(
        self,
        *,
        execution: ExecutionReference,
        context: _ExecutionContext | None,
        sequence: int,
        started_at: float,
        last_progress_at: float,
    ) -> AgentRuntimeResult:
        cancellation = "CANCEL_REQUESTED"
        try:
            self._delegate.cancel(execution)
        except Exception:
            cancellation = "CANCEL_FAILED"
        self._write_liveness(
            execution=execution,
            context=context,
            state=ExecutionLivenessState.SUSPECT,
            sequence=sequence,
            started_at=started_at,
            last_progress_at=last_progress_at,
            source="project-hard-deadline",
        )
        if context is not None:
            self._observability.emit(
                "worker_liveness_timeout",
                orchestration_id=context.orchestration_id,
                work_unit_id=context.work_unit_id,
                execution_id=execution.id,
                external_id=execution.external_id,
                status="SUSPECT",
                action=cancellation,
                reason="project-execution-hard-deadline",
            )
        raise ExecutionLivenessTimeout(
            "Project worker exceeded the execution hard deadline; the stale run "
            "was cancellation-requested and the Work Unit is eligible for bounded recovery."
        )

    def _write_liveness(
        self,
        *,
        execution: ExecutionReference,
        context: _ExecutionContext | None,
        state: ExecutionLivenessState,
        sequence: int,
        started_at: float,
        last_progress_at: float,
        source: str,
    ) -> None:
        now = time.time()
        snapshot = ExecutionLiveness(
            external_id=execution.external_id,
            execution_id=execution.id,
            runtime=execution.runtime,
            state=state,
            heartbeat_sequence=sequence,
            started_at=started_at,
            last_heartbeat_at=now,
            last_progress_at=last_progress_at,
            source=source,
        )
        self._store.write(snapshot)
        if context is not None:
            self._observability.emit(
                "worker_heartbeat",
                orchestration_id=context.orchestration_id,
                work_unit_id=context.work_unit_id,
                execution_id=execution.id,
                external_id=execution.external_id,
                status=state.value,
                runtime_status=state.value,
                heartbeat_sequence=sequence,
                last_heartbeat_at=now,
                last_progress_at=last_progress_at,
                reason=source,
            )

    def _bind(self, execution: ExecutionReference, context: _ExecutionContext) -> None:
        self._contexts_by_execution[execution.id] = context
        self._contexts_by_external[execution.external_id] = context

    def _context_for(self, execution: ExecutionReference) -> _ExecutionContext | None:
        return self._contexts_by_execution.get(execution.id) or self._contexts_by_external.get(
            execution.external_id
        )

    @staticmethod
    def _map_status(status: AgentRuntimeStatus) -> ExecutionLivenessState:
        return ExecutionLivenessState(status.value)


class _OrchestrationHeartbeat:
    """Durable controller lease proving that project orchestration is alive."""

    def __init__(
        self,
        *,
        project_root: Path,
        orchestration_id: str,
        observability: ObservabilitySink,
        interval_seconds: float | None = None,
    ) -> None:
        self._orchestration_id = orchestration_id
        self._observability = observability
        self._interval = float(
            interval_seconds
            if interval_seconds is not None
            else os.environ.get("ADAPTIVE_ORCHESTRATION_HEARTBEAT_SECONDS", "15")
        )
        if self._interval <= 0:
            raise ValueError("ADAPTIVE_ORCHESTRATION_HEARTBEAT_SECONDS must be positive.")
        digest = hashlib.sha256(orchestration_id.encode("utf-8")).hexdigest()
        self._path = project_root / ".adaptive" / "orchestration-liveness" / f"{digest}.json"
        self._stop = Event()
        self._thread: Thread | None = None
        self._sequence = 0
        self._started_at = time.time()

    def start(self) -> None:
        self._pulse(controller_state="ACTIVE", status="RUNNING", terminal=False)
        self._thread = Thread(
            target=self._loop,
            name=f"adaptive-orchestration-heartbeat-{self._orchestration_id[:12]}",
            daemon=True,
        )
        self._thread.start()

    def close(self, status: str) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=min(1.0, self._interval))
        self._pulse(controller_state="TERMINAL", status=status, terminal=True)

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self._pulse(controller_state="ACTIVE", status="RUNNING", terminal=False)
            except Exception:
                # Heartbeat diagnostics must never crash governed project work.
                continue

    def _pulse(self, *, controller_state: str, status: str, terminal: bool) -> None:
        self._sequence += 1
        now = time.time()
        payload = {
            "schema_version": 1,
            "orchestration_id": self._orchestration_id,
            "controller_state": controller_state,
            "status": status,
            "terminal": terminal,
            "heartbeat_sequence": self._sequence,
            "started_at": self._started_at,
            "last_heartbeat_at": now,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self._path)
        self._observability.emit(
            "orchestration_heartbeat",
            orchestration_id=self._orchestration_id,
            status=status,
            controller_state=controller_state,
            terminal=terminal,
            heartbeat_sequence=self._sequence,
            last_heartbeat_at=now,
        )


class RunResilientProjectOrchestration(CoreContinuousProjectOrchestration):
    """Continuous orchestration with liveness supervision and finite closure.

    The core already performs bounded retries, materially different strategy
    generations, and project-level replanning. This composition layer closes the
    two operational gaps that made stalled runs look alive forever:

    * every delegated execution has durable liveness and a hard deadline;
    * when bounded retry/replan budgets are exhausted, no Work Unit remains in a
      misleading WAITING/REVISION_REQUIRED state. Unfinished work is explicitly
      terminalized as BLOCKED and downstream work is closed with it.
    """

    def __init__(
        self,
        *,
        runtime: AgentRuntime,
        checkpoint_store=None,
        **kwargs: Any,
    ) -> None:
        self._resilient_checkpoint_store = checkpoint_store
        project_root = getattr(checkpoint_store, "project_root", None)
        self._project_root = (
            Path(project_root).expanduser().resolve()
            if project_root is not None
            else None
        )
        if self._project_root is not None:
            runtime = SupervisedAgentRuntime(
                runtime,
                project_root=self._project_root,
            )
        self._supervised_runtime = runtime if isinstance(runtime, SupervisedAgentRuntime) else None
        super().__init__(
            runtime=runtime,
            checkpoint_store=checkpoint_store,
            **kwargs,
        )

    def execute(
        self,
        request: ProjectOrchestrationRequest,
        *,
        observability: ObservabilitySink | None = None,
    ) -> ProjectOrchestrationResult:
        orchestration_id = request.orchestration_id or uuid4().hex
        if request.orchestration_id is None:
            request = replace(request, orchestration_id=orchestration_id)
        return self._run_resilient(
            orchestration_id=orchestration_id,
            operation=lambda sink: super(RunResilientProjectOrchestration, self).execute(
                request,
                observability=sink,
            ),
            observability=observability,
        )

    def resume(
        self,
        orchestration_id: str,
        *,
        observability: ObservabilitySink | None = None,
        recovery_loop_mode=None,
        acceptance_mode=None,
    ) -> ProjectOrchestrationResult:
        self._prebind_recovered_contexts(orchestration_id)
        return self._run_resilient(
            orchestration_id=orchestration_id,
            operation=lambda sink: super(RunResilientProjectOrchestration, self).resume(
                orchestration_id,
                observability=sink,
                recovery_loop_mode=recovery_loop_mode,
                acceptance_mode=acceptance_mode,
            ),
            observability=observability,
        )

    def _run_resilient(
        self,
        *,
        orchestration_id: str,
        operation,
        observability: ObservabilitySink | None,
    ) -> ProjectOrchestrationResult:
        sink = observability or NullObservabilitySink()
        if self._supervised_runtime is not None:
            self._supervised_runtime.set_observability(sink)
        heartbeat = (
            _OrchestrationHeartbeat(
                project_root=self._project_root,
                orchestration_id=orchestration_id,
                observability=sink,
            )
            if self._project_root is not None
            else None
        )
        if heartbeat is not None:
            heartbeat.start()
        try:
            result = operation(sink)
            result = self._terminalize_unfinished(result, sink)
        except BaseException:
            if heartbeat is not None:
                heartbeat.close("FAILED")
            raise
        if heartbeat is not None:
            heartbeat.close(result.status.value)
        return result

    def _prebind_recovered_contexts(self, orchestration_id: str) -> None:
        if self._supervised_runtime is None or self._resilient_checkpoint_store is None:
            return
        checkpoint = self._resilient_checkpoint_store.load(orchestration_id)
        if not isinstance(checkpoint, dict):
            return
        for row in checkpoint.get("active_executions") or ():
            if not isinstance(row, dict):
                continue
            external_id = row.get("external_id")
            work_unit_id = row.get("work_unit_id")
            if isinstance(external_id, str) and external_id and isinstance(work_unit_id, str) and work_unit_id:
                self._supervised_runtime.prebind_external_context(
                    external_id=external_id,
                    orchestration_id=orchestration_id,
                    work_unit_id=work_unit_id,
                )

    def _terminalize_unfinished(
        self,
        result: ProjectOrchestrationResult,
        observability: ObservabilitySink,
    ) -> ProjectOrchestrationResult:
        if result.status is ProjectRunStatus.PAUSED:
            return result

        checkpoint = None
        if self._resilient_checkpoint_store is not None:
            checkpoint = self._resilient_checkpoint_store.load(result.orchestration_id)

        # Persistent recovery may intentionally yield the controller between
        # bounded recovery epochs or after a transient control-plane failure.
        # In that state the durable checkpoint is explicitly non-terminal and
        # retains pending_replan=True so the detached supervisor can resume the
        # same orchestration later. Do not convert that governed yield into a
        # synthetic terminal BLOCKED project.
        if (
            result.status is ProjectRunStatus.RECOVERY_REQUIRED
            and isinstance(checkpoint, dict)
            and checkpoint.get("terminal") is False
            and bool(checkpoint.get("pending_replan", False))
            and isinstance(checkpoint.get("request"), dict)
            and bool(checkpoint["request"].get("persistent_recovery", False))
        ):
            return result

        if not result.unfinished_work_unit_ids:
            return result

        reasons: dict[str, str] = {}

        if isinstance(checkpoint, dict):
            states = checkpoint.get("work_unit_states")
            attempts = checkpoint.get("attempts")
            strategies = checkpoint.get("strategy_generations")
            plan = checkpoint.get("plan")
            records = checkpoint.get("records")
            dispatch_generation = checkpoint.get("dispatch_generation", 0)
            role_by_id: dict[str, str] = {}
            skills_by_id: dict[str, list[str]] = {}
            if isinstance(plan, dict):
                for row in plan.get("work_units") or ():
                    if not isinstance(row, dict):
                        continue
                    work_unit_id = row.get("id")
                    if isinstance(work_unit_id, str):
                        role_by_id[work_unit_id] = str(row.get("role") or "recovery")
                        raw_skills = row.get("requested_skills")
                        skills_by_id[work_unit_id] = (
                            [str(item) for item in raw_skills]
                            if isinstance(raw_skills, list)
                            else []
                        )
            if not isinstance(records, list):
                records = []
                checkpoint["records"] = records
            for work_unit_id in result.unfinished_work_unit_ids:
                previous_state = (
                    states.get(work_unit_id)
                    if isinstance(states, dict)
                    else None
                )
                reason = self._terminal_reason(previous_state)
                reasons[work_unit_id] = reason
                if isinstance(states, dict):
                    states[work_unit_id] = "BLOCKED"
                attempt = (
                    attempts.get(work_unit_id, 0)
                    if isinstance(attempts, dict)
                    else 0
                )
                strategy = (
                    strategies.get(work_unit_id, 1)
                    if isinstance(strategies, dict)
                    else 1
                )
                records.append(
                    {
                        "work_unit_id": work_unit_id,
                        "role": role_by_id.get(work_unit_id, "recovery"),
                        "wave": int(dispatch_generation) + 1,
                        "attempt": int(attempt),
                        "status": "BLOCKED",
                        "skills": skills_by_id.get(work_unit_id, []),
                        "execution_id": None,
                        "external_id": None,
                        "runtime_status": None,
                        "verdict": "BLOCKED",
                        "output": "",
                        "result_ref": None,
                        "result_authoritative": False,
                        "reason": reason,
                        "strategy": int(strategy),
                    }
                )
                observability.emit(
                    "work_unit_status_changed",
                    orchestration_id=result.orchestration_id,
                    work_unit_id=work_unit_id,
                    role=role_by_id.get(work_unit_id, "recovery"),
                    skills=skills_by_id.get(work_unit_id, []),
                    attempt=int(attempt),
                    wave=int(dispatch_generation) + 1,
                    status="BLOCKED",
                    verdict="BLOCKED",
                    reason=reason,
                )
            checkpoint["pending_replan"] = False
            checkpoint["active_executions"] = []
            checkpoint["terminal"] = True
            self._resilient_checkpoint_store.save(result.orchestration_id, checkpoint)
        else:
            reasons = {
                work_unit_id: "bounded-recovery-exhausted"
                for work_unit_id in result.unfinished_work_unit_ids
            }

        blocked_ids = tuple(
            sorted(set(result.blocked_work_unit_ids) | set(result.unfinished_work_unit_ids))
        )
        final_status = (
            ProjectRunStatus.PARTIAL
            if result.completed_work_unit_ids
            else ProjectRunStatus.BLOCKED
        )
        synthetic_records = tuple(
            WorkUnitExecutionRecord(
                work_unit_id=work_unit_id,
                role="recovery",
                wave=(max((record.wave for record in result.records), default=0) + 1),
                attempt=0,
                status="BLOCKED",
                verdict="BLOCKED",
                reason=reasons[work_unit_id],
            )
            for work_unit_id in result.unfinished_work_unit_ids
        )
        finalized = replace(
            result,
            status=final_status,
            blocked_work_unit_ids=blocked_ids,
            unfinished_work_unit_ids=(),
            recovery_required_work_unit_ids=(),
            records=(*result.records, *synthetic_records),
        )
        observability.emit(
            "orchestration_terminalized",
            orchestration_id=result.orchestration_id,
            status=finalized.status.value,
            terminal=True,
            reason="bounded-retry-strategy-replan-exhausted",
        )
        # The core emits its pre-terminal summary before this composition layer
        # closes unresolved work. Emit the authoritative later terminal event so
        # consumers such as Control Room project the actual final state.
        observability.emit(
            "orchestration_completed",
            orchestration_id=result.orchestration_id,
            status=finalized.status.value,
            terminal=True,
            reason="resilient-terminal-closure",
        )
        return finalized

    @staticmethod
    def _terminal_reason(previous_state: object) -> str:
        if previous_state == "RECOVERY_REQUIRED":
            return "auto-recovery-exhausted:max-replans-or-no-valid-remediation"
        if previous_state == "REVISION_REQUIRED":
            return "revision-exhausted:max-attempts-strategies-or-waves"
        if previous_state in {"RUNNING", "EVALUATING"}:
            return "runtime-ended-without-live-execution"
        return "blocked-by-terminal-dependency-or-scheduler-budget"
