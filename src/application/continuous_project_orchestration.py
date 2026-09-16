from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import replace
from typing import Sequence
from uuid import uuid4

from application.agent_runtime import AgentRuntimeResult
from application.project_orchestration_checkpoint import ProjectOrchestrationCheckpointStore
from application.observability import NullObservabilitySink, ObservabilitySink
from application.execution_coordinator import (
    DispatchFrontierRequest,
    DispatchOutcome,
    DispatchStatus,
    ExecutionCoordinator,
    WorkAssignment,
)
from application.run_project_orchestration import (
    ParallelWaveRecord,
    ProjectOrchestrationError,
    RecoveryPlanTopologyError,
    ProjectOrchestrationRequest,
    ProjectOrchestrationResult,
    ProjectRunStatus,
    RunProjectOrchestration,
    WorkUnitExecutionRecord,
)
from application.runtime_project_planner import ProjectPlanningRequest
from domain.dependency import Dependency, DependencyStatus
from domain.evaluation import EvaluationVerdict
from domain.execution_policy import AutonomyClass, ExecutionPolicy
from domain.project_execution_plan import (
    PlannedDependency,
    PlannedWorkUnit,
    ProjectExecutionPlan,
)
from domain.work_unit import WorkUnit, WorkUnitKind, WorkUnitState


class RunContinuousProjectOrchestration(RunProjectOrchestration):
    """Continuously execute the safe ready frontier with bounded concurrency.

    The scheduler keeps up to ``max_concurrency`` independent runtime sessions
    active. As soon as one result is available it is evaluated and finalized;
    newly-unblocked work can consume the free slot while unrelated workers keep
    running. ``ParallelWaveRecord`` is retained as a compatibility data type, but
    each record represents one dispatch generation rather than a barrier.

    Replanning is intentionally conservative: once a worker requests bounded
    replanning, no new workers are launched until already-active work drains.
    This avoids exceeding the project concurrency budget with the planner itself
    and prevents graph mutation underneath in-flight work.
    """

    def __init__(
        self,
        *args,
        checkpoint_store: ProjectOrchestrationCheckpointStore | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._checkpoint_store = checkpoint_store

    def execute(
        self,
        request: ProjectOrchestrationRequest,
        *,
        observability: ObservabilitySink | None = None,
    ) -> ProjectOrchestrationResult:
        return self._execute(request, observability=observability, checkpoint=None)

    def resume(
        self,
        orchestration_id: str,
        *,
        observability: ObservabilitySink | None = None,
    ) -> ProjectOrchestrationResult:
        if self._checkpoint_store is None:
            raise ProjectOrchestrationError(
                "Project resume requires a durable checkpoint store."
            )
        checkpoint = self._checkpoint_store.load(orchestration_id)
        if checkpoint is None:
            raise ProjectOrchestrationError(
                f"No project checkpoint exists for orchestration '{orchestration_id}'."
            )
        request = self._request_from_checkpoint(checkpoint)
        return self._execute(
            request,
            observability=observability,
            checkpoint=checkpoint,
        )

    def _execute(
        self,
        request: ProjectOrchestrationRequest,
        *,
        observability: ObservabilitySink | None,
        checkpoint: dict | None,
    ) -> ProjectOrchestrationResult:
        observability = observability or NullObservabilitySink()
        orchestration_id = request.orchestration_id or uuid4().hex
        planning_request = ProjectPlanningRequest(
            objective=request.objective,
            scope=request.scope,
            context=request.context,
            constraints=request.constraints,
            agent=request.planner_agent or request.agent,
            max_work_units=request.max_work_units,
            max_concurrency=request.max_concurrency,
        )
        admission_only = (
            checkpoint is not None
            and checkpoint.get("phase") == "ADMITTED"
            and "plan" not in checkpoint
        )
        if checkpoint is None:
            self._save_admission_checkpoint(
                orchestration_id=orchestration_id,
                request=request,
            )
            observability.emit(
                "orchestration_admitted",
                orchestration_id=orchestration_id,
                phase="ADMITTED",
            )
        observability.emit(
            "orchestration_started",
            orchestration_id=orchestration_id,
            recovered=checkpoint is not None,
            phase="ADMITTED" if admission_only else "EXECUTION",
        )
        plan = request.plan or self._planner.plan(planning_request)
        if len(plan.work_units) > request.max_work_units:
            raise ProjectOrchestrationError(
                f"Plan contains {len(plan.work_units)} Work Units; "
                f"limit is {request.max_work_units}."
            )

        specs = {spec.id: spec for spec in plan.work_units}
        work_units = {
            spec.id: self._instantiate_work_unit(spec) for spec in plan.work_units
        }
        dependencies = [self._instantiate_dependency(item) for item in plan.dependencies]

        if checkpoint is None or admission_only:
            for spec in plan.work_units:
                observability.emit(
                    "work_unit_created", orchestration_id=orchestration_id,
                    work_unit_id=spec.id, role=spec.role,
                    skills=list(spec.requested_skills), status="WAITING",
                )
            attempts = {work_unit_id: 0 for work_unit_id in work_units}
            strategy_generations = {work_unit_id: 1 for work_unit_id in work_units}
            outputs: dict[str, str] = {}
            output_refs: dict[str, str] = {}
            revision_feedback: dict[str, str] = {}
            records: list[WorkUnitExecutionRecord] = []
            dispatch_records: list[ParallelWaveRecord] = []
            max_parallelism_observed = 0
            replan_count = 0
            dispatch_generation = 0
            pending_replan = False
            replan_feedback = ""
            recovered_active: list[dict] = []
        else:
            self._restore_work_unit_states(work_units, checkpoint)
            self._restore_dependency_states(dependencies, checkpoint)
            attempts = self._restore_int_map(
                checkpoint, "attempts", tuple(work_units)
            )
            strategy_generations = self._restore_strategy_generations(
                checkpoint, tuple(work_units)
            )
            outputs = self._restore_str_map(checkpoint, "outputs")
            output_refs = self._restore_str_map(checkpoint, "output_refs")
            revision_feedback = self._restore_str_map(
                checkpoint, "revision_feedback"
            )
            records = [
                self._record_from_payload(item)
                for item in self._require_list(checkpoint, "records")
            ]
            dispatch_records = [
                self._wave_from_payload(item)
                for item in self._require_list(checkpoint, "dispatch_records")
            ]
            max_parallelism_observed = self._require_nonnegative_int(
                checkpoint, "max_parallelism_observed"
            )
            replan_count = self._require_nonnegative_int(
                checkpoint, "replan_count"
            )
            dispatch_generation = self._require_nonnegative_int(
                checkpoint, "dispatch_generation"
            )
            pending_replan = bool(checkpoint.get("pending_replan", False))
            replan_feedback = str(checkpoint.get("replan_feedback") or "")
            recovered_active = self._require_list(
                checkpoint, "active_executions"
            )

        skill_sets = self._preflight_skill_sets(specs, request.agent)
        self._validate_graph(request, work_units, dependencies)

        if checkpoint is not None and checkpoint.get("terminal") is True:
            return self._result_from_state(
                orchestration_id=orchestration_id,
                plan=plan,
                work_units=work_units,
                records=records,
                dispatch_records=dispatch_records,
                max_parallelism_observed=max_parallelism_observed,
                replan_count=replan_count,
            )

        active: dict[
            Future[AgentRuntimeResult],
            tuple[DispatchOutcome, int],
        ] = {}
        active_by_id: dict[str, DispatchOutcome] = {}

        def persist(*, terminal: bool = False) -> None:
            self._save_checkpoint(
                orchestration_id=orchestration_id,
                request=request,
                plan=plan,
                work_units=work_units,
                dependencies=dependencies,
                attempts=attempts,
                strategy_generations=strategy_generations,
                outputs=outputs,
                output_refs=output_refs,
                revision_feedback=revision_feedback,
                records=records,
                dispatch_records=dispatch_records,
                max_parallelism_observed=max_parallelism_observed,
                replan_count=replan_count,
                dispatch_generation=dispatch_generation,
                pending_replan=pending_replan,
                replan_feedback=replan_feedback,
                active=tuple(active.values()),
                terminal=terminal,
            )

        if checkpoint is None or admission_only:
            persist()

        with ThreadPoolExecutor(max_workers=request.max_concurrency) as executor:
            if checkpoint is not None:
                for item in recovered_active:
                    work_unit_id = self._require_str(item, "work_unit_id")
                    if work_unit_id not in work_units:
                        raise ProjectOrchestrationError(
                            f"Recovered execution references unknown Work Unit '{work_unit_id}'."
                        )
                    if work_units[work_unit_id].state is not WorkUnitState.RUNNING:
                        raise ProjectOrchestrationError(
                            f"Recovered active Work Unit '{work_unit_id}' is not RUNNING."
                        )
                    external_id = self._require_str(item, "external_id")
                    expected_execution_id = self._require_str(item, "execution_id")
                    generation = self._require_nonnegative_int(item, "generation")
                    execution = self._runtime.recover_execution(external_id)
                    if execution.id != expected_execution_id:
                        raise ProjectOrchestrationError(
                            "Recovered runtime execution identity mismatch for "
                            f"Work Unit '{work_unit_id}'."
                        )
                    claim = self._claims.acquire(
                        work_unit_id=work_unit_id,
                        claimant_id=f"project:{orchestration_id}:recovery",
                    )
                    if claim is None:
                        raise ProjectOrchestrationError(
                            f"Recovered Work Unit '{work_unit_id}' is already claimed."
                        )
                    bound_claim = self._claims.bind_execution(
                        claim,
                        execution_id=execution.id,
                    )
                    outcome = DispatchOutcome(
                        work_unit_id=work_unit_id,
                        status=DispatchStatus.DISPATCHED,
                        reason="recovered-existing-execution",
                        execution=execution,
                        claim=bound_claim,
                    )
                    future = executor.submit(
                        self._runtime.retrieve_result,
                        execution,
                    )
                    active[future] = (outcome, generation)
                    active_by_id[work_unit_id] = outcome
                    observability.emit(
                        "worker_recovered",
                        orchestration_id=orchestration_id,
                        work_unit_id=work_unit_id,
                        execution_id=execution.id,
                        external_id=execution.external_id,
                        attempt=attempts[work_unit_id],
                        wave=generation,
                        status="RECOVERED",
                    )
                running_without_execution = [
                    work_unit_id
                    for work_unit_id, work_unit in work_units.items()
                    if work_unit.state is WorkUnitState.RUNNING
                    and work_unit_id not in active_by_id
                ]
                if running_without_execution:
                    raise ProjectOrchestrationError(
                        "Checkpoint contains RUNNING Work Units without persisted "
                        "execution identities: "
                        + ", ".join(sorted(running_without_execution))
                    )
                persist()
            while True:
                unfinished = self._unfinished(work_units)

                # A replan signal is itself pending orchestration work. Process it
                # before declaring the current graph terminal, because the worker
                # that requested replanning may have been the last current Work
                # Unit and the replan may legitimately add the next required unit.
                if pending_replan and not active:
                    if replan_count >= request.max_replans:
                        pending_replan = False
                    elif hasattr(self._planner, "replan"):
                        old_edges = {
                            (dependency.source_id, dependency.target_id, dependency.required)
                            for dependency in dependencies
                        }
                        recovery_before = {
                            work_unit_id
                            for work_unit_id, work_unit in work_units.items()
                            if work_unit.state is WorkUnitState.RECOVERY_REQUIRED
                        }
                        try:
                            plan, new_ids = self._expand_plan(
                                planner_request=planning_request,
                                current_plan=plan,
                                specs=specs,
                                work_units=work_units,
                                dependencies=dependencies,
                                outputs=outputs,
                                output_refs=output_refs,
                                request=request,
                                planner_feedback=replan_feedback,
                            )
                        except RecoveryPlanTopologyError as exc:
                            replan_count += 1
                            replan_feedback = str(exc)
                            pending_replan = replan_count < request.max_replans
                            observability.emit(
                                "recovery_plan_rejected",
                                orchestration_id=orchestration_id,
                                replan_count=replan_count,
                                reason=replan_feedback,
                            )
                            persist()
                            continue
                        replan_count += 1
                        replan_feedback = ""
                        self._validate_replanned_edges(
                            old_edges=old_edges,
                            dependencies=dependencies,
                            work_units=work_units,
                        )
                        new_edges = {
                            (
                                dependency.source_id,
                                dependency.target_id,
                                dependency.required,
                            )
                            for dependency in dependencies
                        } - old_edges
                        recovery_resumed: set[str] = set()
                        for work_unit_id in recovery_before:
                            has_new_required_prerequisite = any(
                                required and target_id == work_unit_id
                                for _, target_id, required in new_edges
                            )
                            if not has_new_required_prerequisite:
                                continue
                            work_units[work_unit_id].resume_after_recovery()
                            attempts[work_unit_id] = 0
                            strategy_generations[work_unit_id] = 1
                            revision_feedback[work_unit_id] = (
                                "Recovery planner added prerequisite work. Preserve "
                                "the current WIP and previous evidence; after the "
                                "new prerequisite is satisfied, retry the original "
                                "objective with a fresh strategy cycle.\n"
                                + outputs.get(work_unit_id, "")
                            )
                            recovery_resumed.add(work_unit_id)
                        for work_unit_id in new_ids:
                            attempts[work_unit_id] = 0
                            strategy_generations[work_unit_id] = 1
                        unresolved_recovery = recovery_before - recovery_resumed
                        pending_replan = bool(unresolved_recovery) and (
                            replan_count < request.max_replans
                        )
                        if new_ids:
                            skill_sets = self._preflight_skill_sets(specs, request.agent)
                        self._validate_graph(request, work_units, dependencies)
                        persist()
                        continue
                    else:
                        pending_replan = False

                if not unfinished and not active:
                    break

                ready_ids = self._ready_ids(unfinished, dependencies)
                human_ready = [
                    work_unit_id
                    for work_unit_id in ready_ids
                    if work_units[work_unit_id].kind is WorkUnitKind.HUMAN_ACTION
                ]
                for work_unit_id in human_ready:
                    work_units[work_unit_id].mark_blocked()
                    records.append(
                        WorkUnitExecutionRecord(
                            work_unit_id=work_unit_id,
                            role=specs[work_unit_id].role,
                            wave=dispatch_generation + 1,
                            attempt=attempts[work_unit_id],
                            status=WorkUnitState.BLOCKED.value,
                            skills=skill_sets[work_unit_id],
                            reason="human-action-work-unit",
                        )
                    )
                ready_ids = [item for item in ready_ids if item not in human_ready]
                if human_ready:
                    persist()

                available_slots = request.max_concurrency - len(active)
                if (
                    not pending_replan
                    and available_slots > 0
                    and ready_ids
                    and dispatch_generation < request.max_waves
                ):
                    selected_ids, conflict_deferred_ids = self._select_continuous_frontier(
                        ready_ids=ready_ids,
                        specs=specs,
                        active_ids=tuple(active_by_id),
                        max_new_workers=available_slots,
                    )
                    if selected_ids:
                        for work_unit_id in selected_ids:
                            observability.emit(
                                "work_unit_ready", orchestration_id=orchestration_id,
                                work_unit_id=work_unit_id, status="READY",
                            )
                        dispatch_generation += 1
                        generation = dispatch_generation
                        dispatch_records.append(
                            ParallelWaveRecord(
                                wave=generation,
                                ready_work_unit_ids=tuple(ready_ids),
                                selected_work_unit_ids=tuple(selected_ids),
                                conflict_deferred_ids=tuple(conflict_deferred_ids),
                            )
                        )
                        assignments = tuple(
                            self._build_continuous_assignment(
                                orchestration_id=orchestration_id,
                                wave=generation,
                                attempt=attempts[work_unit_id] + 1,
                                strategy_generation=strategy_generations[work_unit_id],
                                spec=specs[work_unit_id],
                                work_unit=work_units[work_unit_id],
                                skills=skill_sets[work_unit_id],
                                dependencies=dependencies,
                                outputs=outputs,
                                output_refs=output_refs,
                                revision_feedback=revision_feedback.get(work_unit_id, ""),
                                request=request,
                            )
                            for work_unit_id in selected_ids
                        )
                        assignment_by_id = {
                            assignment.work_unit.id.value: assignment
                            for assignment in assignments
                        }
                        dispatch = ExecutionCoordinator(
                            runtime=self._runtime,
                            claim_registry=self._claims,
                        ).dispatch_frontier(
                            DispatchFrontierRequest(
                                assignments=assignments,
                                dependencies=dependencies,
                                claimant_id=(
                                    f"project:{orchestration_id}:dispatch:{generation}"
                                ),
                                concurrency_limit=request.max_concurrency,
                                active_execution_count=len(active),
                                human_approved_work_unit_ids=(
                                    tuple(selected_ids) if request.human_approved else ()
                                ),
                            )
                        )

                        for outcome in dispatch.outcomes:
                            if outcome.status is DispatchStatus.DISPATCHED:
                                attempts[outcome.work_unit_id] += 1
                                assert outcome.execution is not None
                                future = executor.submit(
                                    self._runtime.retrieve_result,
                                    outcome.execution,
                                )
                                active[future] = (outcome, generation)
                                active_by_id[outcome.work_unit_id] = outcome
                                spec = specs[outcome.work_unit_id]
                                configuration = assignment_by_id[outcome.work_unit_id].configuration
                                observability.emit(
                                    "worker_dispatched", orchestration_id=orchestration_id,
                                    work_unit_id=outcome.work_unit_id,
                                    execution_id=outcome.execution.id,
                                    external_id=outcome.execution.external_id,
                                    role=spec.role,
                                    skills=list(skill_sets[outcome.work_unit_id]),
                                    model=configuration.model, provider=configuration.provider,
                                    attempt=attempts[outcome.work_unit_id],
                                    strategy=strategy_generations[outcome.work_unit_id],
                                    wave=generation,
                                    status="DISPATCHED",
                                )
                                continue
                            self._record_dispatch_failure(
                                outcome=outcome,
                                wave=generation,
                                specs=specs,
                                work_units=work_units,
                                skill_sets=skill_sets,
                                attempts=attempts,
                                records=records,
                                max_attempts=request.max_attempts_per_work_unit,
                            )

                        max_parallelism_observed = max(
                            max_parallelism_observed,
                            len(active),
                        )
                        # Persist external execution identities before waiting so a
                        # replacement controller can reconcile the same workers.
                        persist()

                if active:
                    completed, _ = wait(
                        tuple(active),
                        return_when=FIRST_COMPLETED,
                    )
                    for future in completed:
                        outcome, generation = active.pop(future)
                        active_by_id.pop(outcome.work_unit_id, None)
                        work_unit_id = outcome.work_unit_id
                        try:
                            runtime_result = future.result()
                        except Exception as exc:  # adapter exception families vary
                            runtime_recovery_signal = self._handle_runtime_result_error(
                                outcome=outcome,
                                error=exc,
                                generation=generation,
                                specs=specs,
                                work_units=work_units,
                                skill_sets=skill_sets,
                                attempts=attempts,
                                strategy_generations=strategy_generations,
                                records=records,
                                revision_feedback=revision_feedback,
                                max_attempts=request.max_attempts_per_work_unit,
                                max_strategies=request.max_strategies_per_work_unit,
                            )
                            pending_replan = (
                                pending_replan or runtime_recovery_signal
                            )
                            persist()
                            continue

                        record, replan_signal = self._finalize_result(
                            outcome=outcome,
                            runtime_result=runtime_result,
                            wave=generation,
                            spec=specs[work_unit_id],
                            work_unit=work_units[work_unit_id],
                            skills=skill_sets[work_unit_id],
                            dependencies=dependencies,
                            orchestration_id=orchestration_id,
                            attempts=attempts[work_unit_id],
                            max_attempts=request.max_attempts_per_work_unit,
                            enforce_attempt_circuit_breaker=False,
                        )
                        record, recovery_signal = self._apply_strategy_exhaustion(
                            record=record,
                            work_unit=work_units[work_unit_id],
                            attempts=attempts,
                            strategy_generations=strategy_generations,
                            work_unit_id=work_unit_id,
                            max_attempts=request.max_attempts_per_work_unit,
                            max_strategies=request.max_strategies_per_work_unit,
                        )
                        records.append(record)
                        observability.emit(
                            "work_unit_status_changed", orchestration_id=orchestration_id,
                            work_unit_id=record.work_unit_id, execution_id=record.execution_id,
                            external_id=record.external_id, role=record.role,
                            skills=list(record.skills), attempt=record.attempt,
                            strategy=record.strategy,
                            wave=record.wave, status=record.status,
                            runtime_status=record.runtime_status, verdict=record.verdict,
                        )
                        if record.output:
                            outputs[work_unit_id] = record.output
                        if (
                            record.verdict == EvaluationVerdict.ACCEPTED.value
                            and record.result_authoritative
                            and record.result_ref
                        ):
                            output_refs[work_unit_id] = record.result_ref
                        if record.verdict != EvaluationVerdict.ACCEPTED.value:
                            feedback = (
                                record.output
                                or record.reason
                                or "Previous result was not accepted."
                            )
                            if record.reason.startswith("strategy-exhausted:"):
                                feedback = (
                                    "The previous worker strategy exhausted its "
                                    "bounded attempts. Use a materially different "
                                    "approach, inspect the current WIP first, preserve "
                                    "valid prior work, and address the evaluator's "
                                    "unmet criteria instead of repeating the same "
                                    "method.\n" + feedback
                                )
                            revision_feedback[work_unit_id] = feedback
                        else:
                            revision_feedback.pop(work_unit_id, None)
                        pending_replan = (
                            pending_replan
                            or replan_signal
                            or recovery_signal
                        )
                        persist()
                    continue

                # Nothing is active. If the scheduler cannot dispatch another
                # eligible Work Unit, the graph has reached a governed stop.
                if not ready_ids or dispatch_generation >= request.max_waves:
                    break

                selected_ids, _ = self._select_continuous_frontier(
                    ready_ids=ready_ids,
                    specs=specs,
                    active_ids=(),
                    max_new_workers=request.max_concurrency,
                )
                if not selected_ids:
                    break

        completed_ids = tuple(
            sorted(
                work_unit_id
                for work_unit_id, work_unit in work_units.items()
                if work_unit.state is WorkUnitState.COMPLETED
            )
        )
        blocked_ids = tuple(
            sorted(
                work_unit_id
                for work_unit_id, work_unit in work_units.items()
                if work_unit.state is WorkUnitState.BLOCKED
            )
        )
        recovery_required_ids = tuple(
            sorted(
                work_unit_id
                for work_unit_id, work_unit in work_units.items()
                if work_unit.state is WorkUnitState.RECOVERY_REQUIRED
            )
        )
        unfinished_ids = tuple(
            sorted(
                work_unit_id
                for work_unit_id, work_unit in work_units.items()
                if work_unit.state not in {
                    WorkUnitState.COMPLETED,
                    WorkUnitState.CANCELLED,
                    WorkUnitState.BLOCKED,
                }
            )
        )

        if len(completed_ids) == len(work_units):
            status = ProjectRunStatus.COMPLETED
        elif recovery_required_ids and not blocked_ids:
            status = ProjectRunStatus.RECOVERY_REQUIRED
        elif completed_ids:
            status = ProjectRunStatus.PARTIAL
        else:
            status = ProjectRunStatus.BLOCKED

        result = ProjectOrchestrationResult(
            orchestration_id=orchestration_id,
            status=status,
            plan_summary=plan.summary,
            work_unit_count=len(work_units),
            completed_work_unit_ids=completed_ids,
            blocked_work_unit_ids=blocked_ids,
            unfinished_work_unit_ids=unfinished_ids,
            records=tuple(records),
            waves=tuple(dispatch_records),
            max_parallelism_observed=max_parallelism_observed,
            replan_count=replan_count,
            recovery_required_work_unit_ids=recovery_required_ids,
        )
        persist(terminal=True)
        observability.emit(
            "orchestration_completed", orchestration_id=orchestration_id,
            status=result.status.value, summary=plan.summary[:500],
        )
        return result

    def _save_admission_checkpoint(
        self,
        *,
        orchestration_id: str,
        request: ProjectOrchestrationRequest,
    ) -> None:
        """Persist durable project admission before planner/runtime side effects.

        The admission checkpoint intentionally contains no project plan yet.
        If the controller or planner fails after admission, resume-project can
        safely reconstruct the request and rerun planning under the same
        orchestration identity instead of creating a duplicate orchestration.
        """
        if self._checkpoint_store is None:
            return
        self._checkpoint_store.save(
            orchestration_id,
            {
                "orchestration_id": orchestration_id,
                "phase": "ADMITTED",
                "request": self._request_to_payload(request),
                "terminal": False,
            },
        )

    def _save_checkpoint(
        self,
        *,
        orchestration_id: str,
        request: ProjectOrchestrationRequest,
        plan: ProjectExecutionPlan,
        work_units: dict[str, WorkUnit],
        dependencies: Sequence[Dependency],
        attempts: dict[str, int],
        strategy_generations: dict[str, int],
        outputs: dict[str, str],
        output_refs: dict[str, str],
        revision_feedback: dict[str, str],
        records: Sequence[WorkUnitExecutionRecord],
        dispatch_records: Sequence[ParallelWaveRecord],
        max_parallelism_observed: int,
        replan_count: int,
        dispatch_generation: int,
        pending_replan: bool,
        replan_feedback: str,
        active: Sequence[tuple[DispatchOutcome, int]],
        terminal: bool,
    ) -> None:
        if self._checkpoint_store is None:
            return
        active_rows = []
        for outcome, generation in active:
            if outcome.execution is None:
                continue
            active_rows.append(
                {
                    "work_unit_id": outcome.work_unit_id,
                    "generation": generation,
                    "execution_id": outcome.execution.id,
                    "external_id": outcome.execution.external_id,
                    "runtime": outcome.execution.runtime,
                }
            )
        payload = {
            "orchestration_id": orchestration_id,
            "phase": "EXECUTION",
            "request": self._request_to_payload(request),
            "plan": self._plan_to_payload(plan),
            "work_unit_states": {
                key: value.state.value for key, value in work_units.items()
            },
            "dependency_states": [
                {
                    "source_id": item.source_id,
                    "target_id": item.target_id,
                    "required": item.required,
                    "status": item.status.value,
                }
                for item in dependencies
            ],
            "attempts": dict(attempts),
            "strategy_generations": dict(strategy_generations),
            "outputs": dict(outputs),
            "output_refs": dict(output_refs),
            "revision_feedback": dict(revision_feedback),
            "records": [self._record_to_payload(item) for item in records],
            "dispatch_records": [
                self._wave_to_payload(item) for item in dispatch_records
            ],
            "max_parallelism_observed": max_parallelism_observed,
            "replan_count": replan_count,
            "dispatch_generation": dispatch_generation,
            "pending_replan": pending_replan,
            "replan_feedback": replan_feedback,
            "active_executions": active_rows,
            "terminal": terminal,
        }
        self._checkpoint_store.save(orchestration_id, payload)

    @staticmethod
    def _request_to_payload(request: ProjectOrchestrationRequest) -> dict:
        policy = request.execution_policy
        return {
            "objective": request.objective,
            "agent": request.agent,
            "planner_agent": request.planner_agent,
            "scope": request.scope,
            "context": list(request.context),
            "constraints": list(request.constraints),
            "max_concurrency": request.max_concurrency,
            "max_work_units": request.max_work_units,
            "max_waves": request.max_waves,
            "max_attempts_per_work_unit": request.max_attempts_per_work_unit,
            "max_strategies_per_work_unit": request.max_strategies_per_work_unit,
            "max_replans": request.max_replans,
            "dependency_context_chars": request.dependency_context_chars,
            "human_approved": request.human_approved,
            "execution_policy": {
                "autonomy": policy.autonomy.value,
                "allowed_side_effects": list(policy.allowed_side_effects),
                "denied_tools": list(policy.denied_tools),
                "require_independent_review": policy.require_independent_review,
            },
        }

    @classmethod
    def _request_from_checkpoint(
        cls,
        checkpoint: dict,
    ) -> ProjectOrchestrationRequest:
        orchestration_id = cls._require_str(checkpoint, "orchestration_id")
        raw = checkpoint.get("request")
        if not isinstance(raw, dict):
            raise ProjectOrchestrationError(
                "Checkpoint is missing the orchestration request."
            )
        policy_raw = raw.get("execution_policy")
        if not isinstance(policy_raw, dict):
            raise ProjectOrchestrationError(
                "Checkpoint is missing the execution policy."
            )
        try:
            policy = ExecutionPolicy(
                autonomy=AutonomyClass(
                    cls._require_str(policy_raw, "autonomy")
                ),
                allowed_side_effects=tuple(
                    cls._require_string_list(
                        policy_raw, "allowed_side_effects"
                    )
                ),
                denied_tools=tuple(
                    cls._require_string_list(policy_raw, "denied_tools")
                ),
                require_independent_review=bool(
                    policy_raw.get("require_independent_review", False)
                ),
            )
            plan_raw = checkpoint.get("plan")
            phase = str(checkpoint.get("phase") or "")
            if isinstance(plan_raw, dict):
                plan = cls._plan_from_payload(plan_raw)
            elif phase == "ADMITTED":
                plan = None
            else:
                raise ProjectOrchestrationError(
                    "Checkpoint is missing the project plan."
                )
            planner_agent = raw.get("planner_agent")
            if planner_agent is not None and not isinstance(planner_agent, str):
                raise ProjectOrchestrationError(
                    "Checkpoint planner_agent is invalid."
                )
            return ProjectOrchestrationRequest(
                objective=cls._require_str(raw, "objective"),
                orchestration_id=orchestration_id,
                agent=cls._require_str(raw, "agent"),
                planner_agent=planner_agent,
                scope=str(raw.get("scope") or ""),
                context=tuple(cls._require_string_list(raw, "context")),
                constraints=tuple(
                    cls._require_string_list(raw, "constraints")
                ),
                max_concurrency=cls._require_nonnegative_int(
                    raw, "max_concurrency"
                ),
                max_work_units=cls._require_nonnegative_int(
                    raw, "max_work_units"
                ),
                max_waves=cls._require_nonnegative_int(raw, "max_waves"),
                max_attempts_per_work_unit=cls._require_nonnegative_int(
                    raw, "max_attempts_per_work_unit"
                ),
                max_strategies_per_work_unit=(
                    cls._require_nonnegative_int(
                        raw, "max_strategies_per_work_unit"
                    )
                    if "max_strategies_per_work_unit" in raw
                    else 2
                ),
                max_replans=cls._require_nonnegative_int(raw, "max_replans"),
                dependency_context_chars=cls._require_nonnegative_int(
                    raw, "dependency_context_chars"
                ),
                execution_policy=policy,
                human_approved=bool(raw.get("human_approved", False)),
                plan=plan,
            )
        except (ValueError, TypeError) as exc:
            if isinstance(exc, ProjectOrchestrationError):
                raise
            raise ProjectOrchestrationError(
                "Checkpoint orchestration request is invalid."
            ) from exc

    @staticmethod
    def _plan_to_payload(plan: ProjectExecutionPlan) -> dict:
        return {
            "summary": plan.summary,
            "work_units": [
                {
                    "id": item.id,
                    "objective": item.objective,
                    "role": item.role,
                    "scope": item.scope,
                    "kind": item.kind.value,
                    "required_capabilities": list(item.required_capabilities),
                    "requested_skills": list(item.requested_skills),
                    "tools": list(item.tools),
                    "inputs": list(item.inputs),
                    "expected_output": list(item.expected_output),
                    "acceptance_criteria": list(item.acceptance_criteria),
                    "requested_side_effects": list(item.requested_side_effects),
                    "write_paths": list(item.write_paths),
                    "priority": item.priority,
                    "criticality": item.criticality,
                    "parallel_safe": item.parallel_safe,
                }
                for item in plan.work_units
            ],
            "dependencies": [
                {
                    "source_id": item.source_id,
                    "target_id": item.target_id,
                    "required": item.required,
                    "condition": item.condition,
                }
                for item in plan.dependencies
            ],
        }

    @classmethod
    def _plan_from_payload(cls, payload: dict) -> ProjectExecutionPlan:
        raw_units = cls._require_list(payload, "work_units")
        raw_dependencies = cls._require_list(payload, "dependencies")
        try:
            units = []
            for raw in raw_units:
                units.append(
                    PlannedWorkUnit(
                        id=cls._require_str(raw, "id"),
                        objective=cls._require_str(raw, "objective"),
                        role=cls._require_str(raw, "role"),
                        scope=str(raw.get("scope") or ""),
                        kind=WorkUnitKind(cls._require_str(raw, "kind")),
                        required_capabilities=tuple(
                            cls._require_string_list(
                                raw, "required_capabilities"
                            )
                        ),
                        requested_skills=tuple(
                            cls._require_string_list(raw, "requested_skills")
                        ),
                        tools=tuple(cls._require_string_list(raw, "tools")),
                        inputs=tuple(cls._require_string_list(raw, "inputs")),
                        expected_output=tuple(
                            cls._require_string_list(raw, "expected_output")
                        ),
                        acceptance_criteria=tuple(
                            cls._require_string_list(
                                raw, "acceptance_criteria"
                            )
                        ),
                        requested_side_effects=tuple(
                            cls._require_string_list(
                                raw, "requested_side_effects"
                            )
                        ),
                        write_paths=tuple(
                            cls._require_string_list(raw, "write_paths")
                        ),
                        priority=cls._require_nonnegative_int(raw, "priority"),
                        criticality=cls._require_nonnegative_int(
                            raw, "criticality"
                        ),
                        parallel_safe=bool(raw.get("parallel_safe", False)),
                    )
                )
            dependencies = []
            for raw in raw_dependencies:
                condition = raw.get("condition")
                if condition is not None and not isinstance(condition, str):
                    raise ProjectOrchestrationError(
                        "Checkpoint dependency condition is invalid."
                    )
                dependencies.append(
                    PlannedDependency(
                        source_id=cls._require_str(raw, "source_id"),
                        target_id=cls._require_str(raw, "target_id"),
                        required=bool(raw.get("required", True)),
                        condition=condition,
                    )
                )
            return ProjectExecutionPlan(
                summary=cls._require_str(payload, "summary"),
                work_units=tuple(units),
                dependencies=tuple(dependencies),
            )
        except (ValueError, TypeError) as exc:
            if isinstance(exc, ProjectOrchestrationError):
                raise
            raise ProjectOrchestrationError(
                "Checkpoint project plan is invalid."
            ) from exc

    @classmethod
    def _restore_work_unit_states(
        cls,
        work_units: dict[str, WorkUnit],
        checkpoint: dict,
    ) -> None:
        raw = checkpoint.get("work_unit_states")
        if not isinstance(raw, dict) or set(raw) != set(work_units):
            raise ProjectOrchestrationError(
                "Checkpoint Work Unit state set does not match the project plan."
            )
        try:
            for work_unit_id, value in raw.items():
                work_units[work_unit_id].state = WorkUnitState(value)
        except (ValueError, TypeError) as exc:
            raise ProjectOrchestrationError(
                "Checkpoint contains an invalid Work Unit state."
            ) from exc

    @classmethod
    def _restore_dependency_states(
        cls,
        dependencies: Sequence[Dependency],
        checkpoint: dict,
    ) -> None:
        rows = cls._require_list(checkpoint, "dependency_states")
        state_by_edge = {}
        for row in rows:
            key = (
                cls._require_str(row, "source_id"),
                cls._require_str(row, "target_id"),
                bool(row.get("required", True)),
            )
            if key in state_by_edge:
                raise ProjectOrchestrationError(
                    "Checkpoint contains duplicate dependency state."
                )
            state_by_edge[key] = cls._require_str(row, "status")
        expected = {
            (item.source_id, item.target_id, item.required) for item in dependencies
        }
        if set(state_by_edge) != expected:
            raise ProjectOrchestrationError(
                "Checkpoint dependency state set does not match the project plan."
            )
        try:
            for item in dependencies:
                item.status = DependencyStatus(
                    state_by_edge[
                        (item.source_id, item.target_id, item.required)
                    ]
                )
        except ValueError as exc:
            raise ProjectOrchestrationError(
                "Checkpoint contains an invalid dependency state."
            ) from exc

    @staticmethod
    def _record_to_payload(item: WorkUnitExecutionRecord) -> dict:
        return {
            "work_unit_id": item.work_unit_id,
            "role": item.role,
            "wave": item.wave,
            "attempt": item.attempt,
            "status": item.status,
            "skills": list(item.skills),
            "execution_id": item.execution_id,
            "external_id": item.external_id,
            "runtime_status": item.runtime_status,
            "verdict": item.verdict,
            "output": item.output,
            "result_ref": item.result_ref,
            "result_authoritative": item.result_authoritative,
            "reason": item.reason,
            "strategy": item.strategy,
        }

    @classmethod
    def _record_from_payload(cls, raw: dict) -> WorkUnitExecutionRecord:
        def optional(name: str) -> str | None:
            value = raw.get(name)
            if value is None:
                return None
            if not isinstance(value, str):
                raise ProjectOrchestrationError(
                    f"Checkpoint record field '{name}' is invalid."
                )
            return value

        return WorkUnitExecutionRecord(
            work_unit_id=cls._require_str(raw, "work_unit_id"),
            role=cls._require_str(raw, "role"),
            wave=cls._require_nonnegative_int(raw, "wave"),
            attempt=cls._require_nonnegative_int(raw, "attempt"),
            status=cls._require_str(raw, "status"),
            skills=tuple(cls._require_string_list(raw, "skills")),
            execution_id=optional("execution_id"),
            external_id=optional("external_id"),
            runtime_status=optional("runtime_status"),
            verdict=optional("verdict"),
            output=str(raw.get("output") or ""),
            result_ref=optional("result_ref"),
            result_authoritative=bool(
                raw.get("result_authoritative", False)
            ),
            reason=str(raw.get("reason") or ""),
            strategy=(
                cls._require_nonnegative_int(raw, "strategy")
                if "strategy" in raw
                else 1
            ),
        )

    @staticmethod
    def _wave_to_payload(item: ParallelWaveRecord) -> dict:
        return {
            "wave": item.wave,
            "ready_work_unit_ids": list(item.ready_work_unit_ids),
            "selected_work_unit_ids": list(item.selected_work_unit_ids),
            "conflict_deferred_ids": list(item.conflict_deferred_ids),
        }

    @classmethod
    def _wave_from_payload(cls, raw: dict) -> ParallelWaveRecord:
        return ParallelWaveRecord(
            wave=cls._require_nonnegative_int(raw, "wave"),
            ready_work_unit_ids=tuple(
                cls._require_string_list(raw, "ready_work_unit_ids")
            ),
            selected_work_unit_ids=tuple(
                cls._require_string_list(raw, "selected_work_unit_ids")
            ),
            conflict_deferred_ids=tuple(
                cls._require_string_list(raw, "conflict_deferred_ids")
            ),
        )

    @classmethod
    def _restore_int_map(
        cls,
        checkpoint: dict,
        name: str,
        expected_keys: Sequence[str],
    ) -> dict[str, int]:
        raw = checkpoint.get(name)
        if not isinstance(raw, dict) or set(raw) != set(expected_keys):
            raise ProjectOrchestrationError(
                f"Checkpoint field '{name}' does not match Work Units."
            )
        result = {}
        for key, value in raw.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ProjectOrchestrationError(
                    f"Checkpoint field '{name}' contains an invalid count."
                )
            result[str(key)] = value
        return result

    @classmethod
    def _restore_strategy_generations(
        cls,
        checkpoint: dict,
        expected_keys: Sequence[str],
    ) -> dict[str, int]:
        raw = checkpoint.get("strategy_generations")
        if raw is None:
            # Backward compatibility for checkpoints produced by recovery #47
            # before strategy generations were persisted.
            return {str(key): 1 for key in expected_keys}
        restored = cls._restore_int_map(
            {"strategy_generations": raw},
            "strategy_generations",
            expected_keys,
        )
        if any(value < 1 for value in restored.values()):
            raise ProjectOrchestrationError(
                "Checkpoint strategy generations must be at least 1."
            )
        return restored

    @staticmethod
    def _restore_str_map(checkpoint: dict, name: str) -> dict[str, str]:
        raw = checkpoint.get(name)
        if not isinstance(raw, dict):
            raise ProjectOrchestrationError(
                f"Checkpoint field '{name}' must be an object."
            )
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in raw.items()
        ):
            raise ProjectOrchestrationError(
                f"Checkpoint field '{name}' contains invalid values."
            )
        return dict(raw)

    @staticmethod
    def _require_list(payload: dict, name: str) -> list[dict]:
        value = payload.get(name)
        if not isinstance(value, list) or any(
            not isinstance(item, dict) for item in value
        ):
            raise ProjectOrchestrationError(
                f"Checkpoint field '{name}' must be a list of objects."
            )
        return value

    @staticmethod
    def _require_string_list(payload: dict, name: str) -> list[str]:
        value = payload.get(name)
        if not isinstance(value, list) or any(
            not isinstance(item, str) for item in value
        ):
            raise ProjectOrchestrationError(
                f"Checkpoint field '{name}' must be a list of strings."
            )
        return value

    @staticmethod
    def _require_str(payload: dict, name: str) -> str:
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ProjectOrchestrationError(
                f"Checkpoint field '{name}' must be a non-empty string."
            )
        return value

    @staticmethod
    def _require_nonnegative_int(payload: dict, name: str) -> int:
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ProjectOrchestrationError(
                f"Checkpoint field '{name}' must be a non-negative integer."
            )
        return value

    @staticmethod
    def _result_from_state(
        *,
        orchestration_id: str,
        plan: ProjectExecutionPlan,
        work_units: dict[str, WorkUnit],
        records: Sequence[WorkUnitExecutionRecord],
        dispatch_records: Sequence[ParallelWaveRecord],
        max_parallelism_observed: int,
        replan_count: int,
    ) -> ProjectOrchestrationResult:
        completed_ids = tuple(
            sorted(
                key
                for key, item in work_units.items()
                if item.state is WorkUnitState.COMPLETED
            )
        )
        blocked_ids = tuple(
            sorted(
                key
                for key, item in work_units.items()
                if item.state is WorkUnitState.BLOCKED
            )
        )
        recovery_required_ids = tuple(
            sorted(
                key
                for key, item in work_units.items()
                if item.state is WorkUnitState.RECOVERY_REQUIRED
            )
        )
        unfinished_ids = tuple(
            sorted(
                key
                for key, item in work_units.items()
                if item.state
                not in {
                    WorkUnitState.COMPLETED,
                    WorkUnitState.CANCELLED,
                    WorkUnitState.BLOCKED,
                }
            )
        )
        if len(completed_ids) == len(work_units):
            status = ProjectRunStatus.COMPLETED
        elif recovery_required_ids and not blocked_ids:
            status = ProjectRunStatus.RECOVERY_REQUIRED
        elif completed_ids:
            status = ProjectRunStatus.PARTIAL
        else:
            status = ProjectRunStatus.BLOCKED
        return ProjectOrchestrationResult(
            orchestration_id=orchestration_id,
            status=status,
            plan_summary=plan.summary,
            work_unit_count=len(work_units),
            completed_work_unit_ids=completed_ids,
            blocked_work_unit_ids=blocked_ids,
            unfinished_work_unit_ids=unfinished_ids,
            records=tuple(records),
            waves=tuple(dispatch_records),
            max_parallelism_observed=max_parallelism_observed,
            replan_count=replan_count,
            recovery_required_work_unit_ids=recovery_required_ids,
        )

    def _build_continuous_assignment(
        self,
        *,
        attempt: int,
        strategy_generation: int,
        **kwargs,
    ) -> WorkAssignment:
        assignment = super()._build_assignment(**kwargs)
        task = assignment.task_package
        strategy_context = (
            f"Adaptive strategy generation: {strategy_generation}. "
            "Generation 1 is the initial strategy."
        )
        if strategy_generation > 1:
            strategy_context += (
                " A previous strategy exhausted its bounded attempts. This is "
                "a replacement strategy: inspect current WIP and prior feedback "
                "first, preserve valid work, and use a materially different "
                "problem-solving approach rather than repeating the exhausted one."
            )
        unique_task = replace(
            task,
            task_id=(
                f"{task.task_id}:strategy:{strategy_generation}:"
                f"attempt-number:{attempt}"
            ),
            context=(*task.context, strategy_context),
        )
        return WorkAssignment(
            work_unit=assignment.work_unit,
            configuration=assignment.configuration,
            task_package=unique_task,
        )

    @classmethod
    def _select_continuous_frontier(
        cls,
        *,
        ready_ids: Sequence[str],
        specs: dict[str, PlannedWorkUnit],
        active_ids: Sequence[str],
        max_new_workers: int,
    ) -> tuple[list[str], list[str]]:
        selected: list[str] = []
        deferred: list[str] = []
        active_specs = tuple(specs[work_unit_id] for work_unit_id in active_ids)

        for work_unit_id in ready_ids:
            if len(selected) >= max_new_workers:
                deferred.append(work_unit_id)
                continue
            candidate = specs[work_unit_id]
            compatible_with_active = all(
                cls._can_share_wave(candidate, active_spec)
                for active_spec in active_specs
            )
            compatible_with_new = all(
                cls._can_share_wave(candidate, specs[selected_id])
                for selected_id in selected
            )
            if compatible_with_active and compatible_with_new:
                selected.append(work_unit_id)
            else:
                deferred.append(work_unit_id)

        return selected, deferred

    def _handle_runtime_result_error(
        self,
        *,
        outcome: DispatchOutcome,
        error: Exception,
        generation: int,
        specs: dict[str, PlannedWorkUnit],
        work_units: dict[str, WorkUnit],
        skill_sets: dict[str, tuple[str, ...]],
        attempts: dict[str, int],
        strategy_generations: dict[str, int],
        records: list[WorkUnitExecutionRecord],
        revision_feedback: dict[str, str],
        max_attempts: int,
        max_strategies: int,
    ) -> bool:
        assert outcome.claim is not None
        self._claims.release(outcome.claim)
        work_unit_id = outcome.work_unit_id
        work_unit = work_units[work_unit_id]
        if work_unit.state is WorkUnitState.RUNNING:
            work_unit.start_evaluation()
            work_unit.require_revision()
        reason = f"runtime-result-error:{error}"
        record = WorkUnitExecutionRecord(
            work_unit_id=work_unit_id,
            role=specs[work_unit_id].role,
            wave=generation,
            attempt=attempts[work_unit_id],
            status=work_unit.state.value,
            skills=skill_sets[work_unit_id],
            execution_id=(outcome.execution.id if outcome.execution else None),
            external_id=(
                outcome.execution.external_id if outcome.execution else None
            ),
            reason=reason,
            strategy=strategy_generations[work_unit_id],
        )
        record, _ = self._apply_strategy_exhaustion(
            record=record,
            work_unit=work_unit,
            attempts=attempts,
            strategy_generations=strategy_generations,
            work_unit_id=work_unit_id,
            max_attempts=max_attempts,
            max_strategies=max_strategies,
        )
        feedback = record.reason
        if record.reason.startswith("strategy-exhausted:"):
            feedback = (
                "The previous runtime strategy exhausted its bounded attempts. "
                "Use a different recovery approach while preserving current WIP. "
                + feedback
            )
        revision_feedback[work_unit_id] = feedback
        records.append(record)
        return work_unit.state is WorkUnitState.RECOVERY_REQUIRED

    @staticmethod
    def _apply_strategy_exhaustion(
        *,
        record: WorkUnitExecutionRecord,
        work_unit: WorkUnit,
        attempts: dict[str, int],
        strategy_generations: dict[str, int],
        work_unit_id: str,
        max_attempts: int,
        max_strategies: int,
    ) -> tuple[WorkUnitExecutionRecord, bool]:
        current_strategy = strategy_generations[work_unit_id]
        record = replace(record, strategy=current_strategy)
        if (
            work_unit.state is not WorkUnitState.REVISION_REQUIRED
            or attempts[work_unit_id] < max_attempts
        ):
            return record, False

        if current_strategy < max_strategies:
            next_strategy = current_strategy + 1
            strategy_generations[work_unit_id] = next_strategy
            attempts[work_unit_id] = 0
            return (
                replace(
                    record,
                    reason=(
                        f"strategy-exhausted:{current_strategy}:"
                        f"replacement:{next_strategy}:{record.reason}"
                    ),
                ),
                False,
            )

        work_unit.mark_recovery_required()
        return (
            replace(
                record,
                status=WorkUnitState.RECOVERY_REQUIRED.value,
                reason=(
                    "recovery-required:strategies-exhausted:"
                    f"{current_strategy}:{record.reason}"
                ),
            ),
            True,
        )

    @staticmethod
    def _validate_replanned_edges(
        *,
        old_edges: set[tuple[str, str, bool]],
        dependencies: Sequence[Dependency],
        work_units: dict[str, WorkUnit],
    ) -> None:
        for dependency in dependencies:
            edge = (
                dependency.source_id,
                dependency.target_id,
                dependency.required,
            )
            if edge in old_edges or not dependency.required or dependency.is_satisfied:
                continue
            target = work_units[dependency.target_id]
            if target.state in {
                WorkUnitState.RUNNING,
                WorkUnitState.EVALUATING,
                WorkUnitState.COMPLETED,
            }:
                raise ProjectOrchestrationError(
                    "Replanning cannot add an unsatisfied required prerequisite "
                    f"to already-started Work Unit '{dependency.target_id}'."
                )
