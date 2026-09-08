from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import replace
from typing import Sequence
from uuid import uuid4

from application.agent_runtime import AgentRuntimeResult
from application.execution_coordinator import (
    DispatchOutcome,
    DispatchStatus,
    ExecutionCoordinator,
    DispatchFrontierRequest,
    WorkAssignment,
)
from application.run_project_orchestration import (
    ParallelWaveRecord,
    ProjectOrchestrationError,
    ProjectOrchestrationRequest,
    ProjectOrchestrationResult,
    ProjectRunStatus,
    RunProjectOrchestration,
    WorkUnitExecutionRecord,
)
from application.runtime_project_planner import ProjectPlanningRequest
from domain.evaluation import EvaluationVerdict
from domain.project_execution_plan import PlannedWorkUnit
from domain.work_unit import WorkUnitKind, WorkUnitState


class RunContinuousProjectOrchestration(RunProjectOrchestration):
    """Execute the ready frontier continuously instead of behind wave barriers.

    The scheduler keeps up to ``max_concurrency`` independent runtime sessions
    active. As soon as one result is available it is evaluated and finalized;
    newly-unblocked work can then consume the free slot while unrelated workers
    continue running. ``ParallelWaveRecord`` is retained as a compatibility name,
    but each record now represents one *dispatch generation*, not a barrier that
    waits for every worker in that generation to finish.

    Replanning is intentionally conservative: once a worker asks for a bounded
    replan, no new workers are launched until already-active work drains. This
    avoids exceeding the project concurrency budget with the planner itself and
    prevents graph mutation underneath in-flight work.
    """

    def execute(
        self,
        request: ProjectOrchestrationRequest,
    ) -> ProjectOrchestrationResult:
        orchestration_id = uuid4().hex
        planning_request = ProjectPlanningRequest(
            objective=request.objective,
            scope=request.scope,
            context=request.context,
            constraints=request.constraints,
            agent=request.planner_agent or request.agent,
            max_work_units=request.max_work_units,
            max_concurrency=request.max_concurrency,
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
        skill_sets = self._preflight_skill_sets(specs, request.agent)
        self._validate_graph(request, work_units, dependencies)

        attempts = {work_unit_id: 0 for work_unit_id in work_units}
        outputs: dict[str, str] = {}
        revision_feedback: dict[str, str] = {}
        records: list[WorkUnitExecutionRecord] = []
        dispatch_records: list[ParallelWaveRecord] = []
        max_parallelism_observed = 0
        replan_count = 0
        dispatch_generation = 0
        pending_replan = False

        active: dict[Future[AgentRuntimeResult], DispatchOutcome] = {}
        active_by_id: dict[str, DispatchOutcome] = {}

        with ThreadPoolExecutor(max_workers=request.max_concurrency) as executor:
            while True:
                unfinished = self._unfinished(work_units)
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

                if pending_replan and not active:
                    if replan_count >= request.max_replans:
                        pending_replan = False
                    elif hasattr(self._planner, "replan"):
                        old_edges = {
                            (dependency.source_id, dependency.target_id, dependency.required)
                            for dependency in dependencies
                        }
                        plan, new_ids = self._expand_plan(
                            planner_request=planning_request,
                            current_plan=plan,
                            specs=specs,
                            work_units=work_units,
                            dependencies=dependencies,
                            outputs=outputs,
                            request=request,
                        )
                        self._validate_replanned_edges(
                            old_edges=old_edges,
                            dependencies=dependencies,
                            work_units=work_units,
                        )
                        pending_replan = False
                        if new_ids:
                            replan_count += 1
                            for work_unit_id in new_ids:
                                attempts[work_unit_id] = 0
                            skill_sets = self._preflight_skill_sets(specs, request.agent)
                            self._validate_graph(request, work_units, dependencies)
                            continue

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
                        dispatch_generation += 1
                        dispatch_records.append(
                            ParallelWaveRecord(
                                wave=dispatch_generation,
                                ready_work_unit_ids=tuple(ready_ids),
                                selected_work_unit_ids=tuple(selected_ids),
                                conflict_deferred_ids=tuple(conflict_deferred_ids),
                            )
                        )
                        assignments = tuple(
                            self._build_continuous_assignment(
                                orchestration_id=orchestration_id,
                                wave=dispatch_generation,
                                attempt=attempts[work_unit_id] + 1,
                                spec=specs[work_unit_id],
                                work_unit=work_units[work_unit_id],
                                skills=skill_sets[work_unit_id],
                                dependencies=dependencies,
                                outputs=outputs,
                                revision_feedback=revision_feedback.get(work_unit_id, ""),
                                request=request,
                            )
                            for work_unit_id in selected_ids
                        )
                        dispatch = ExecutionCoordinator(
                            runtime=self._runtime,
                            claim_registry=self._claims,
                        ).dispatch_frontier(
                            DispatchFrontierRequest(
                                assignments=assignments,
                                dependencies=dependencies,
                                claimant_id=(
                                    f"project:{orchestration_id}:dispatch:"
                                    f"{dispatch_generation}"
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
                                active[future] = outcome
                                active_by_id[outcome.work_unit_id] = outcome
                                continue
                            self._record_dispatch_failure(
                                outcome=outcome,
                                wave=dispatch_generation,
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

                if active:
                    completed, _ = wait(
                        tuple(active),
                        return_when=FIRST_COMPLETED,
                    )
                    for future in completed:
                        outcome = active.pop(future)
                        active_by_id.pop(outcome.work_unit_id, None)
                        work_unit_id = outcome.work_unit_id
                        try:
                            runtime_result = future.result()
                        except Exception as exc:  # adapter exception families vary
                            self._handle_runtime_result_error(
                                outcome=outcome,
                                error=exc,
                                generation=dispatch_generation,
                                specs=specs,
                                work_units=work_units,
                                skill_sets=skill_sets,
                                attempts=attempts,
                                records=records,
                                revision_feedback=revision_feedback,
                                max_attempts=request.max_attempts_per_work_unit,
                            )
                            continue

                        record, replan_signal = self._finalize_result(
                            outcome=outcome,
                            runtime_result=runtime_result,
                            wave=dispatch_generation,
                            spec=specs[work_unit_id],
                            work_unit=work_units[work_unit_id],
                            skills=skill_sets[work_unit_id],
                            dependencies=dependencies,
                            attempts=attempts[work_unit_id],
                            max_attempts=request.max_attempts_per_work_unit,
                        )
                        records.append(record)
                        if record.output:
                            outputs[work_unit_id] = record.output
                        if record.verdict not in {
                            EvaluationVerdict.ACCEPTED.value,
                            EvaluationVerdict.ACCEPTED_WITH_CONDITIONS.value,
                        }:
                            revision_feedback[work_unit_id] = (
                                record.output
                                or record.reason
                                or "Previous result was not accepted."
                            )
                        else:
                            revision_feedback.pop(work_unit_id, None)
                        pending_replan = pending_replan or replan_signal
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
        )

    def _build_continuous_assignment(
        self,
        *,
        attempt: int,
        **kwargs,
    ) -> WorkAssignment:
        assignment = super()._build_assignment(**kwargs)
        task = assignment.task_package
        unique_task = replace(
            task,
            task_id=f"{task.task_id}:attempt-number:{attempt}",
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
        work_units: dict[str, object],
        skill_sets: dict[str, tuple[str, ...]],
        attempts: dict[str, int],
        records: list[WorkUnitExecutionRecord],
        revision_feedback: dict[str, str],
        max_attempts: int,
    ) -> None:
        assert outcome.claim is not None
        self._claims.release(outcome.claim)
        work_unit = work_units[outcome.work_unit_id]
        if work_unit.state is WorkUnitState.RUNNING:
            work_unit.start_evaluation()
            work_unit.require_revision()
        reason = f"runtime-result-error:{error}"
        revision_feedback[outcome.work_unit_id] = reason
        if attempts[outcome.work_unit_id] >= max_attempts:
            work_unit.mark_blocked()
        records.append(
            WorkUnitExecutionRecord(
                work_unit_id=outcome.work_unit_id,
                role=specs[outcome.work_unit_id].role,
                wave=generation,
                attempt=attempts[outcome.work_unit_id],
                status=work_unit.state.value,
                skills=skill_sets[outcome.work_unit_id],
                execution_id=(outcome.execution.id if outcome.execution else None),
                external_id=(
                    outcome.execution.external_id if outcome.execution else None
                ),
                reason=reason,
            )
        )

    @staticmethod
    def _validate_replanned_edges(
        *,
        old_edges: set[tuple[str, str, bool]],
        dependencies: Sequence[object],
        work_units: dict[str, object],
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
