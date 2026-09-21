from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence
from uuid import uuid4

from application.agent_runtime import (
    AgentRuntime,
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.claim_registry import ClaimRegistry
from application.completion_integrity import (
    WorkerCompletionStatus,
    parse_worker_completion,
)
from application.evaluate_result import EvaluateResult, EvaluateResultRequest
from application.execution_coordinator import (
    DispatchFrontierRequest,
    DispatchOutcome,
    DispatchStatus,
    ExecutionCoordinator,
    WorkAssignment,
)
from application.finalize_execution import FinalizeExecution, FinalizeExecutionRequest
from application.plan_work import PlanWork, PlanWorkRequest
from application.problem_solving_learning import (
    LEARNING_MARKER,
    ProblemSolvingKnowledgeBase,
    ProblemSolvingLearningStore,
)
from application.incident_management import (
    DEFECT_MARKER,
    IncidentSentinel,
    ResolutionPressureEngine,
)
from application.persistent_recovery import PersistentRecoveryCoordinator
from application.runtime_project_planner import (
    ProjectPlanner,
    ProjectPlanningRequest,
)
from application.skill_resolution import (
    SkillResolutionRequest,
    SkillResolver,
)
from domain.dependency import Dependency, DependencyType
from domain.evaluation import EvaluationVerdict
from domain.execution_policy import ExecutionPolicy
from domain.project import Project, ProjectId
from domain.project_execution_plan import (
    PlannedDependency,
    PlannedWorkUnit,
    ProjectExecutionPlan,
)
from domain.resource_configuration import ResourceConfiguration
from domain.result_package import ResultPackage, ResultPackageStatus
from domain.skill_profile import SkillProfile
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitKind, WorkUnitState
from domain.work_unit_readiness import ReadinessStatus, WorkUnitReadinessEvaluator


class ProjectOrchestrationError(RuntimeError):
    """Raised when project orchestration cannot preserve its invariants."""


class RecoveryPlanTopologyError(ProjectOrchestrationError):
    """Raised when recovery replanning creates unreachable remediation topology."""


class ProjectRunStatus(str, Enum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ProjectOrchestrationRequest:
    objective: str
    orchestration_id: str | None = None
    agent: str = "main"
    planner_agent: str | None = None
    scope: str = ""
    project_id: str = ""
    context: tuple[str, ...] = field(default_factory=tuple)
    constraints: tuple[str, ...] = field(default_factory=tuple)
    max_concurrency: int = 4
    max_work_units: int = 24
    max_waves: int = 24
    max_attempts_per_work_unit: int = 2
    max_strategies_per_work_unit: int = 2
    max_replans: int = 2
    persistent_recovery: bool = False
    max_recovery_epochs: int = 0
    max_stalled_recovery_cycles: int = 3
    pragmatic_low_criticality_acceptance: bool = True
    recovery_strategist_agent: str | None = None
    learning_after_successful_retest: bool = True
    dependency_context_chars: int = 6000
    execution_policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    human_approved: bool = False
    plan: ProjectExecutionPlan | None = None

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("Project orchestration objective must not be blank.")
        if not self.agent.strip():
            raise ValueError("Project orchestration agent must not be blank.")
        if self.max_concurrency < 1 or self.max_concurrency > 32:
            raise ValueError("max_concurrency must be between 1 and 32.")
        if self.max_work_units < 1 or self.max_work_units > 128:
            raise ValueError("max_work_units must be between 1 and 128.")
        if self.max_waves < 1 or self.max_waves > 256:
            raise ValueError("max_waves must be between 1 and 256.")
        if self.max_attempts_per_work_unit < 1 or self.max_attempts_per_work_unit > 8:
            raise ValueError("max_attempts_per_work_unit must be between 1 and 8.")
        if self.max_strategies_per_work_unit < 1 or self.max_strategies_per_work_unit > 4:
            raise ValueError("max_strategies_per_work_unit must be between 1 and 4.")
        if self.max_replans < 0 or self.max_replans > 8:
            raise ValueError("max_replans must be between 0 and 8.")
        if self.max_recovery_epochs < 0 or self.max_recovery_epochs > 1000:
            raise ValueError("max_recovery_epochs must be between 0 and 1000; 0 means no fixed epoch cap.")
        if (
            self.max_stalled_recovery_cycles < 1
            or self.max_stalled_recovery_cycles > 32
        ):
            raise ValueError(
                "max_stalled_recovery_cycles must be between 1 and 32."
            )
        if self.dependency_context_chars < 256:
            raise ValueError("dependency_context_chars must be at least 256.")


@dataclass(frozen=True)
class WorkUnitExecutionRecord:
    work_unit_id: str
    role: str
    wave: int
    attempt: int
    status: str
    skills: tuple[str, ...] = ()
    execution_id: str | None = None
    external_id: str | None = None
    runtime_status: str | None = None
    verdict: str | None = None
    output: str = ""
    result_ref: str | None = None
    result_authoritative: bool = False
    reason: str = ""
    strategy: int = 1


@dataclass(frozen=True)
class ParallelWaveRecord:
    wave: int
    ready_work_unit_ids: tuple[str, ...]
    selected_work_unit_ids: tuple[str, ...]
    conflict_deferred_ids: tuple[str, ...]


@dataclass(frozen=True)
class ProjectOrchestrationResult:
    orchestration_id: str
    status: ProjectRunStatus
    plan_summary: str
    work_unit_count: int
    completed_work_unit_ids: tuple[str, ...]
    blocked_work_unit_ids: tuple[str, ...]
    unfinished_work_unit_ids: tuple[str, ...]
    records: tuple[WorkUnitExecutionRecord, ...]
    waves: tuple[ParallelWaveRecord, ...]
    max_parallelism_observed: int
    replan_count: int
    recovery_required_work_unit_ids: tuple[str, ...] = ()


class RunProjectOrchestration:
    """Execute a planned project graph as synchronized parallel worker waves.

    A wave dispatches every conflict-free ready Work Unit (up to the configured
    cap) before waiting for any result. Those independent runtime sessions then
    execute concurrently. The orchestrator joins the wave, evaluates each
    result, advances accepted dependencies, optionally expands the plan, and
    recomputes the next ready frontier. No idle persistent worker pool exists.
    """

    RUNTIME_NAME = "openclaw"
    REPLAN_MARKER = "ADAPTIVE_REPLAN_REQUIRED"
    LEARNING_MARKER = LEARNING_MARKER
    DEFECT_MARKER = DEFECT_MARKER

    def __init__(
        self,
        *,
        runtime: AgentRuntime,
        claim_registry: ClaimRegistry,
        planner: ProjectPlanner,
        skill_profiles: Sequence[SkillProfile],
        learning_store: ProblemSolvingLearningStore | None = None,
        incident_sentinel: IncidentSentinel | None = None,
        persistent_recovery: PersistentRecoveryCoordinator | None = None,
    ) -> None:
        self._runtime = runtime
        self._claims = claim_registry
        self._planner = planner
        self._skill_profiles = tuple(skill_profiles)
        self._skill_resolver = SkillResolver(self._skill_profiles)
        self._readiness = WorkUnitReadinessEvaluator()
        self._learning_store = learning_store or ProblemSolvingLearningStore.from_env()
        self._knowledge_base = ProblemSolvingKnowledgeBase.load_default(
            learning_store=self._learning_store
        )
        self._incident_sentinel = incident_sentinel or IncidentSentinel()
        self._incident_pressure = ResolutionPressureEngine()
        self._persistent_recovery = persistent_recovery

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
        output_refs: dict[str, str] = {}
        revision_feedback: dict[str, str] = {}
        records: list[WorkUnitExecutionRecord] = []
        wave_records: list[ParallelWaveRecord] = []
        max_parallelism_observed = 0
        replan_count = 0
        wave = 0

        while wave < request.max_waves:
            unfinished = self._unfinished(work_units)
            if not unfinished:
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
                        wave=wave + 1,
                        attempt=attempts[work_unit_id],
                        status="BLOCKED",
                        skills=skill_sets[work_unit_id],
                        reason="human-action-work-unit",
                    )
                )
            ready_ids = [item for item in ready_ids if item not in human_ready]

            if not ready_ids:
                break

            selected_ids, conflict_deferred_ids = self._select_parallel_wave(
                ready_ids,
                specs,
                request.max_concurrency,
            )
            if not selected_ids:
                break

            wave += 1
            wave_records.append(
                ParallelWaveRecord(
                    wave=wave,
                    ready_work_unit_ids=tuple(ready_ids),
                    selected_work_unit_ids=tuple(selected_ids),
                    conflict_deferred_ids=tuple(conflict_deferred_ids),
                )
            )

            assignments = tuple(
                self._build_assignment(
                    orchestration_id=orchestration_id,
                    wave=wave,
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

            dispatch = ExecutionCoordinator(
                runtime=self._runtime,
                claim_registry=self._claims,
            ).dispatch_frontier(
                DispatchFrontierRequest(
                    assignments=assignments,
                    dependencies=dependencies,
                    claimant_id=f"project:{orchestration_id}:wave:{wave}",
                    concurrency_limit=len(assignments),
                    human_approved_work_unit_ids=(
                        tuple(selected_ids) if request.human_approved else ()
                    ),
                )
            )

            dispatched = [
                outcome
                for outcome in dispatch.outcomes
                if outcome.status is DispatchStatus.DISPATCHED
            ]
            max_parallelism_observed = max(
                max_parallelism_observed,
                len(dispatched),
            )

            for outcome in dispatch.outcomes:
                if outcome.status is DispatchStatus.DISPATCHED:
                    attempts[outcome.work_unit_id] += 1
                    continue
                self._record_dispatch_failure(
                    outcome=outcome,
                    wave=wave,
                    specs=specs,
                    work_units=work_units,
                    skill_sets=skill_sets,
                    attempts=attempts,
                    records=records,
                    max_attempts=request.max_attempts_per_work_unit,
                )

            completed_results = self._join_dispatched(dispatched)
            wave_requested_replan = False

            for outcome in dispatched:
                work_unit_id = outcome.work_unit_id
                result_or_error = completed_results[work_unit_id]
                if isinstance(result_or_error, Exception):
                    assert outcome.claim is not None
                    self._claims.release(outcome.claim)
                    work_unit = work_units[work_unit_id]
                    if work_unit.state is WorkUnitState.RUNNING:
                        work_unit.start_evaluation()
                        work_unit.require_revision()
                    reason = f"runtime-result-error:{result_or_error}"
                    revision_feedback[work_unit_id] = reason
                    if attempts[work_unit_id] >= request.max_attempts_per_work_unit:
                        work_unit.mark_blocked()
                        reason = f"circuit-breaker:max-attempts:{reason}"
                    records.append(
                        WorkUnitExecutionRecord(
                            work_unit_id=work_unit_id,
                            role=specs[work_unit_id].role,
                            wave=wave,
                            attempt=attempts[work_unit_id],
                            status=work_unit.state.value,
                            skills=skill_sets[work_unit_id],
                            execution_id=(outcome.execution.id if outcome.execution else None),
                            external_id=(
                                outcome.execution.external_id if outcome.execution else None
                            ),
                            reason=reason,
                        )
                    )
                    continue

                record, replan_signal = self._finalize_result(
                    outcome=outcome,
                    runtime_result=result_or_error,
                    wave=wave,
                    spec=specs[work_unit_id],
                    work_unit=work_units[work_unit_id],
                    skills=skill_sets[work_unit_id],
                    dependencies=dependencies,
                    orchestration_id=orchestration_id,
                    attempts=attempts[work_unit_id],
                    max_attempts=request.max_attempts_per_work_unit,
                )
                records.append(record)
                if record.output:
                    outputs[work_unit_id] = record.output
                if (
                    record.verdict == EvaluationVerdict.ACCEPTED.value
                    and record.result_authoritative
                    and record.result_ref
                ):
                    output_refs[work_unit_id] = record.result_ref
                if record.verdict != EvaluationVerdict.ACCEPTED.value:
                    revision_feedback[work_unit_id] = (
                        record.output or record.reason or "Previous result was not accepted."
                    )
                else:
                    revision_feedback.pop(work_unit_id, None)
                wave_requested_replan = wave_requested_replan or replan_signal

            if (
                wave_requested_replan
                and replan_count < request.max_replans
                and hasattr(self._planner, "replan")
            ):
                plan, new_ids = self._expand_plan(
                    planner_request=planning_request,
                    current_plan=plan,
                    specs=specs,
                    work_units=work_units,
                    dependencies=dependencies,
                    outputs=outputs,
                    output_refs=output_refs,
                    request=request,
                )
                if new_ids:
                    replan_count += 1
                    for work_unit_id in new_ids:
                        attempts[work_unit_id] = 0
                    skill_sets = self._preflight_skill_sets(specs, request.agent)
                    self._validate_graph(request, work_units, dependencies)

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
            waves=tuple(wave_records),
            max_parallelism_observed=max_parallelism_observed,
            replan_count=replan_count,
        )

    @staticmethod
    def _instantiate_work_unit(spec: PlannedWorkUnit) -> WorkUnit:
        return WorkUnit(
            id=WorkUnitId(spec.id),
            objective=spec.objective,
            scope=spec.scope,
            inputs=spec.inputs,
            outputs=spec.expected_output,
            required_capabilities=spec.required_capabilities,
            criteria=spec.acceptance_criteria,
            priority=spec.priority,
            criticality=spec.criticality,
            kind=spec.kind,
        )

    @staticmethod
    def _instantiate_dependency(spec: PlannedDependency) -> Dependency:
        return Dependency(
            source_id=spec.source_id,
            target_id=spec.target_id,
            type=DependencyType.COMPLETION,
            required=spec.required,
            condition=spec.condition,
        )

    def _preflight_skill_sets(
        self,
        specs: dict[str, PlannedWorkUnit],
        agent_id: str,
    ) -> dict[str, tuple[str, ...]]:
        return {
            work_unit_id: self._skill_resolver.execute(
                SkillResolutionRequest(
                    required_capabilities=spec.required_capabilities,
                    requested_skill_ids=spec.requested_skills,
                    agent_id=agent_id,
                    runtime=self.RUNTIME_NAME,
                )
            ).skill_ids
            for work_unit_id, spec in specs.items()
        }

    @staticmethod
    def _validate_graph(
        request: ProjectOrchestrationRequest,
        work_units: dict[str, WorkUnit],
        dependencies: Sequence[Dependency],
    ) -> None:
        project = Project(
            id=ProjectId("project-orchestration-validation"),
            identity=request.objective,
            objectives=(request.objective,),
            constraints=request.constraints,
            baseline="runtime-plan",
        )
        PlanWork().execute(
            PlanWorkRequest(
                project=project,
                work_units=tuple(work_units.values()),
                dependencies=tuple(dependencies),
            )
        )

    @staticmethod
    def _unfinished(work_units: dict[str, WorkUnit]) -> dict[str, WorkUnit]:
        return {
            work_unit_id: work_unit
            for work_unit_id, work_unit in work_units.items()
            if work_unit.state
            not in {WorkUnitState.COMPLETED, WorkUnitState.CANCELLED, WorkUnitState.BLOCKED}
        }

    def _ready_ids(
        self,
        work_units: dict[str, WorkUnit],
        dependencies: Sequence[Dependency],
    ) -> list[str]:
        evaluated = self._readiness.evaluate_all(
            tuple(work_units.values()),
            dependencies,
        )
        ready = [
            item.work_unit_id
            for item in evaluated
            if item.status is ReadinessStatus.READY
        ]
        ready.sort(
            key=lambda work_unit_id: (
                -work_units[work_unit_id].priority,
                -work_units[work_unit_id].criticality,
                work_unit_id,
            )
        )
        return ready

    @classmethod
    def _select_parallel_wave(
        cls,
        ready_ids: Sequence[str],
        specs: dict[str, PlannedWorkUnit],
        max_concurrency: int,
    ) -> tuple[list[str], list[str]]:
        selected: list[str] = []
        deferred: list[str] = []

        for work_unit_id in ready_ids:
            if len(selected) >= max_concurrency:
                deferred.append(work_unit_id)
                continue
            candidate = specs[work_unit_id]
            if all(cls._can_share_wave(candidate, specs[item]) for item in selected):
                selected.append(work_unit_id)
            else:
                deferred.append(work_unit_id)

        return selected, deferred

    @classmethod
    def _can_share_wave(cls, left: PlannedWorkUnit, right: PlannedWorkUnit) -> bool:
        if not left.parallel_safe or not right.parallel_safe:
            return False

        left_writes = bool(left.requested_side_effects)
        right_writes = bool(right.requested_side_effects)
        if not left_writes or not right_writes:
            return True

        if not left.write_paths or not right.write_paths:
            return False

        return not any(
            cls._paths_overlap(left_path, right_path)
            for left_path in left.write_paths
            for right_path in right.write_paths
        )

    @staticmethod
    def _paths_overlap(left: str, right: str) -> bool:
        def normalize(value: str) -> str:
            normalized = value.strip().replace("\\", "/").strip("/")
            while "//" in normalized:
                normalized = normalized.replace("//", "/")
            return normalized or "."

        a = normalize(left)
        b = normalize(right)
        if a in {".", "*", "**"} or b in {".", "*", "**"}:
            return True
        return a == b or a.startswith(f"{b}/") or b.startswith(f"{a}/")

    def _build_assignment(
        self,
        *,
        orchestration_id: str,
        wave: int,
        spec: PlannedWorkUnit,
        work_unit: WorkUnit,
        skills: tuple[str, ...],
        dependencies: Sequence[Dependency],
        outputs: dict[str, str],
        output_refs: dict[str, str],
        revision_feedback: str,
        request: ProjectOrchestrationRequest,
    ) -> WorkAssignment:
        configuration = ResourceConfiguration(
            agent=request.agent,
            skills=skills,
            tools=spec.tools,
            runtime=self.RUNTIME_NAME,
        )
        dependency_sources = tuple(
            dependency.source_id
            for dependency in dependencies
            if dependency.target_id == spec.id
        )
        context = [
            *request.context,
            f"Logical worker role: {spec.role}",
            f"Adaptive orchestration id: {orchestration_id}; synchronized wave: {wave}",
            (
                "Selected skills: " + ", ".join(skills)
                if skills
                else "Selected skills: none explicitly required"
            ),
        ]
        if spec.write_paths:
            context.append("Authorized write scope for this Work Unit: " + ", ".join(spec.write_paths))

        dependency_artifacts: list[str] = []
        for source_id in dependency_sources:
            result_ref = output_refs.get(source_id)
            if result_ref:
                dependency_artifacts.append(result_ref)
                context.append(
                    "Accepted dependency result from "
                    f"{source_id} is available by reference at manifest: {result_ref}. "
                    "Read that manifest and the referenced result_file from the same "
                    "execution directory when the dependency details are needed. "
                    "The dependency payload is intentionally not copied into this "
                    "conversation context."
                )
                continue
            if source_id not in outputs:
                continue
            text = outputs[source_id]
            if len(text) > request.dependency_context_chars:
                text = text[: request.dependency_context_chars] + "\n[dependency output truncated]"
            context.append(
                f"Legacy inline dependency result from {source_id}:\n{text}"
            )
        if revision_feedback:
            feedback = revision_feedback[: request.dependency_context_chars]
            context.append(f"Revision feedback from previous attempt:\n{feedback}")

        experience = self._knowledge_base.render_guidance(
            "\n".join(
                (
                    request.objective,
                    spec.objective,
                    spec.scope,
                    *request.context,
                    revision_feedback,
                )
            ),
            skills=skills,
            project_id=request.project_id,
        )
        if experience:
            context.append(
                experience
                + "\nUse learned experience as process guidance only. It does not "
                "override project facts, requirements, authority, or acceptance criteria."
            )

        constraints = (
            *request.constraints,
            "This is a bounded Work Unit under Adaptive AI Orchestrator control. Do not invoke adaptive-orchestrator-bridge or start another Adaptive run.",
            "Work only inside the delegated objective and declared scope. Do not expand authority.",
            "Return a concise result describing artifacts changed/produced, verification actually performed, blockers, and any next dependency-relevant fact.",
            "Missing implementation, wiring, tests, repositories, ports, or transactions that are already inside the authorized objective/scope are work to complete, not blockers. Continue the Work Unit instead of stopping merely because such changes are needed.",
            "Use BLOCKED only for a genuine stop. HUMAN_DECISION, AUTHORITY, ENVIRONMENT, RUNTIME, and EXTERNAL_DEPENDENCY are external/authority blockers. If the delegated plan itself is wrong (for example authorized write_paths/scope point to nonexistent or incorrect repository locations), use BLOCKED with ADAPTIVE_BLOCKER_TYPE: PLANNING and include ADAPTIVE_REPLAN_REQUIRED with a concise explanation. Do not classify an internal planner/scope defect as ENVIRONMENT.",
            f"If genuinely necessary new work is discovered that is not represented by this Work Unit, include the literal marker {self.REPLAN_MARKER}: followed by a concise reason. Do not use the marker for optional improvements.",
            self._learning_signal_constraint(),
            self._incident_signal_constraint(),
            "At the very end of the response emit exactly these three machine-readable lines: ADAPTIVE_WORK_STATUS: COMPLETE|PARTIAL|BLOCKED ; ADAPTIVE_BLOCKER_TYPE: NONE|HUMAN_DECISION|AUTHORITY|ENVIRONMENT|RUNTIME|EXTERNAL_DEPENDENCY|PLANNING ; ADAPTIVE_UNMET_CRITERIA: NONE|criterion one; criterion two. Use COMPLETE only when the delegated acceptance surface is actually finished.",
        )
        if spec.write_paths:
            constraints = (
                *constraints,
                "Do not write outside these repository-relative path prefixes: "
                + ", ".join(spec.write_paths),
            )

        task = TaskPackage(
            task_id=f"project:{orchestration_id}:wave:{wave}:{spec.id}:attempt:{work_unit.state.value}",
            work_unit_id=spec.id,
            objective=spec.objective,
            orchestration_id=orchestration_id,
            scope=spec.scope,
            context=tuple(context),
            inputs=spec.inputs,
            artifacts=tuple(dependency_artifacts),
            dependencies=dependency_sources,
            constraints=constraints,
            configuration=configuration,
            expected_output=spec.expected_output,
            acceptance_criteria=spec.acceptance_criteria,
            execution_policy=request.execution_policy,
            requested_side_effects=spec.requested_side_effects,
        )
        return WorkAssignment(
            work_unit=work_unit,
            configuration=configuration,
            task_package=task,
        )

    def _join_dispatched(
        self,
        dispatched: Sequence[DispatchOutcome],
    ) -> dict[str, AgentRuntimeResult | Exception]:
        results: dict[str, AgentRuntimeResult | Exception] = {}
        if not dispatched:
            return results

        with ThreadPoolExecutor(max_workers=len(dispatched)) as executor:
            future_to_id = {
                executor.submit(self._runtime.retrieve_result, outcome.execution): outcome.work_unit_id
                for outcome in dispatched
                if outcome.execution is not None
            }
            for future in as_completed(future_to_id):
                work_unit_id = future_to_id[future]
                try:
                    results[work_unit_id] = future.result()
                except Exception as exc:  # runtime adapter exceptions vary
                    results[work_unit_id] = exc
        return results

    def _finalize_result(
        self,
        *,
        outcome: DispatchOutcome,
        runtime_result: AgentRuntimeResult,
        wave: int,
        spec: PlannedWorkUnit,
        work_unit: WorkUnit,
        skills: tuple[str, ...],
        dependencies: Sequence[Dependency],
        orchestration_id: str,
        attempts: int,
        max_attempts: int,
        enforce_attempt_circuit_breaker: bool = True,
        pragmatic_low_criticality_acceptance: bool = False,
    ) -> tuple[WorkUnitExecutionRecord, bool]:
        assert outcome.claim is not None
        assert outcome.execution is not None
        runtime_status = runtime_result.execution.status
        raw_result = runtime_result.raw_result
        if runtime_status is AgentRuntimeStatus.COMPLETED and raw_result is None:
            raw_result = {"status": "completed"}

        output = self._extract_output(raw_result)
        observed_incident = self._incident_sentinel.observe_worker_output(
            output,
            orchestration_id=orchestration_id,
            work_unit_id=outcome.work_unit_id,
            execution_id=outcome.execution.id,
            runtime=outcome.execution.runtime,
        )
        incident_requires_replan = bool(
            observed_incident
            and (
                observed_incident.blocking
                or self._incident_pressure.score(observed_incident) >= 70
            )
        )
        result_ref, result_authoritative = self._extract_result_reference(raw_result)
        completion = parse_worker_completion(output)
        result_status = (
            ResultPackageStatus.SUCCEEDED
            if runtime_status is AgentRuntimeStatus.COMPLETED
            else ResultPackageStatus.FAILED
        )
        if (
            result_status is ResultPackageStatus.SUCCEEDED
            and completion.structured
            and completion.status in {
                WorkerCompletionStatus.PARTIAL,
                WorkerCompletionStatus.BLOCKED,
            }
        ):
            result_status = ResultPackageStatus.PARTIAL

        evidence_items: list[str] = []
        if runtime_status is AgentRuntimeStatus.COMPLETED:
            evidence_items.append("runtime-completed")
        if completion.structured:
            evidence_items.append(
                f"worker-status:{completion.status.value.casefold()}"
            )
        if (
            pragmatic_low_criticality_acceptance
            and spec.criticality == 0
            and runtime_status is AgentRuntimeStatus.COMPLETED
            and completion.is_terminal_success
            and result_authoritative
            and result_ref
        ):
            # For ordinary low-criticality Work Units, a transport-verified
            # authoritative result plus an explicit COMPLETE/no-unmet-criteria
            # footer is stronger evidence than literal criterion text matching.
            # Critical or independently-reviewed work remains on the strict path.
            evidence_items.append("authoritative-worker-complete")

        package = ResultPackage(
            task_id=f"project-result:{outcome.work_unit_id}:wave:{wave}",
            status=result_status,
            result=raw_result,
            evidence=tuple(evidence_items),
        )
        evaluation = EvaluateResult().execute(
            EvaluateResultRequest(
                result_package=package,
                criteria=spec.acceptance_criteria,
                evaluator_id="adaptive-orchestrator:project",
            )
        ).evaluation

        verdict = evaluation.verdict
        reason = "evaluation-returned"
        planning_recovery = False
        if completion.structured:
            if completion.is_recoverable_planning_blocker:
                verdict = EvaluationVerdict.RETURNED
                reason = "recovery-required:planning"
                planning_recovery = True
            elif completion.is_genuine_blocker:
                verdict = EvaluationVerdict.BLOCKED
                reason = f"worker-blocked:{completion.blocker_type.value}"
            elif completion.status is WorkerCompletionStatus.BLOCKED:
                verdict = EvaluationVerdict.RETURNED
                reason = "worker-blocker-unsubstantiated"
            elif completion.status is WorkerCompletionStatus.PARTIAL:
                verdict = EvaluationVerdict.RETURNED
                reason = "worker-partial"
            elif completion.status is WorkerCompletionStatus.COMPLETE:
                reason = (
                    "accepted"
                    if verdict is EvaluationVerdict.ACCEPTED
                    else "evaluation-returned"
                )
        elif verdict is EvaluationVerdict.ACCEPTED:
            reason = "accepted"

        finalized = FinalizeExecution(self._claims).execute(
            FinalizeExecutionRequest(
                work_unit=work_unit,
                claim=outcome.claim,
                verdict=verdict,
                dependencies=dependencies,
                orchestration_id=orchestration_id,
            )
        )
        if planning_recovery and work_unit.state is WorkUnitState.REVISION_REQUIRED:
            work_unit.mark_recovery_required()
        elif (
            enforce_attempt_circuit_breaker
            and finalized.work_unit_state is WorkUnitState.REVISION_REQUIRED
            and attempts >= max_attempts
        ):
            work_unit.mark_blocked()
            reason = f"circuit-breaker:max-attempts:{reason}"

        accepted = verdict is EvaluationVerdict.ACCEPTED
        if accepted and output:
            self._learning_store.record_worker_signal(
                output,
                orchestration_id=orchestration_id,
                work_unit_id=outcome.work_unit_id,
            )
        return (
            WorkUnitExecutionRecord(
                work_unit_id=outcome.work_unit_id,
                role=spec.role,
                wave=wave,
                attempt=attempts,
                status=work_unit.state.value,
                skills=skills,
                execution_id=outcome.execution.id,
                external_id=outcome.execution.external_id,
                runtime_status=runtime_status.value,
                verdict=verdict.value,
                output=output,
                result_ref=result_ref,
                result_authoritative=result_authoritative,
                reason=reason,
            ),
            (
                planning_recovery
                or incident_requires_replan
                or (accepted and self.REPLAN_MARKER in output)
            ),
        )

    def _incident_signal_constraint(self) -> str:
        return (
            "If you observe a real defect, protocol violation, runtime anomaly, "
            "transport/integrity failure, regression, unexpected state transition, "
            "or repeated human-correction-worthy failure, emit at most one bounded "
            f"{self.DEFECT_MARKER} JSON line with keys category, component, symptom, "
            "severity (LOW|MEDIUM|HIGH|CRITICAL), optional topics (list), and optional "
            "blocking (boolean). Report only the observable symptom; never include "
            "prompts, source code, secrets, credentials, chain-of-thought, or raw tool "
            "output. Do not create/close incidents or promote knowledge yourself; "
            "Adaptive owns that lifecycle."
        )

    def _learning_signal_constraint(self) -> str:
        return (
            "If a non-obvious, reusable problem-solving or decomposition strategy "
            "materially turned a blocker into progress, append exactly one final "
            f"single-line {self.LEARNING_MARKER} JSON object with keys "
            "strategy_id, trigger, action, result. Use a stable lowercase-hyphen "
            "strategy_id. Do not emit this marker for ordinary success. Never put "
            "prompts, source code, user data, secrets, credentials, model reasoning, "
            "or raw tool output in the learning signal."
        )

    @staticmethod
    def _record_dispatch_failure(
        *,
        outcome: DispatchOutcome,
        wave: int,
        specs: dict[str, PlannedWorkUnit],
        work_units: dict[str, WorkUnit],
        skill_sets: dict[str, tuple[str, ...]],
        attempts: dict[str, int],
        records: list[WorkUnitExecutionRecord],
        max_attempts: int,
    ) -> None:
        work_unit_id = outcome.work_unit_id
        work_unit = work_units[work_unit_id]
        reason = outcome.reason
        if outcome.status is DispatchStatus.FAILED:
            attempts[work_unit_id] += 1
            if attempts[work_unit_id] >= max_attempts:
                work_unit.mark_blocked()
                reason = f"circuit-breaker:max-attempts:{reason}"
        elif outcome.status is DispatchStatus.BLOCKED:
            work_unit.mark_blocked()
        records.append(
            WorkUnitExecutionRecord(
                work_unit_id=work_unit_id,
                role=specs[work_unit_id].role,
                wave=wave,
                attempt=attempts[work_unit_id],
                status=work_unit.state.value,
                skills=skill_sets[work_unit_id],
                reason=reason,
            )
        )

    def _expand_plan(
        self,
        *,
        planner_request: ProjectPlanningRequest,
        current_plan: ProjectExecutionPlan,
        specs: dict[str, PlannedWorkUnit],
        work_units: dict[str, WorkUnit],
        dependencies: list[Dependency],
        outputs: dict[str, str],
        output_refs: dict[str, str],
        request: ProjectOrchestrationRequest,
        planner_feedback: str = "",
    ) -> tuple[ProjectExecutionPlan, tuple[str, ...]]:
        replan = getattr(self._planner, "replan")
        state_summary = self._state_summary(work_units, outputs, output_refs)
        if planner_feedback.strip():
            state_summary += (
                "\nRECOVERY_PLAN_VALIDATION_FEEDBACK:\n"
                + planner_feedback.strip()
            )
        revised = replan(planner_request, current_plan, state_summary)

        new_specs = [spec for spec in revised.work_units if spec.id not in specs]
        self._validate_recovery_replan_topology(
            revised=revised,
            current_plan=current_plan,
            work_units=work_units,
            new_specs=new_specs,
        )
        if len(specs) + len(new_specs) > request.max_work_units:
            raise ProjectOrchestrationError(
                "Plan expansion would exceed max_work_units."
            )

        for spec in new_specs:
            specs[spec.id] = spec
            work_units[spec.id] = self._instantiate_work_unit(spec)

        existing_edges = {
            (dependency.source_id, dependency.target_id, dependency.required)
            for dependency in dependencies
        }
        known = set(specs)
        for item in revised.dependencies:
            edge = (item.source_id, item.target_id, item.required)
            if edge in existing_edges:
                continue
            if item.source_id not in known or item.target_id not in known:
                raise ProjectOrchestrationError(
                    "Replanned dependency references an unknown Work Unit."
                )
            dependency = self._instantiate_dependency(item)
            if work_units[item.source_id].state is WorkUnitState.COMPLETED:
                dependency.satisfy()
            dependencies.append(dependency)
            existing_edges.add(edge)

        merged = ProjectExecutionPlan(
            summary=revised.summary,
            work_units=tuple(specs.values()),
            dependencies=tuple(
                PlannedDependency(
                    source_id=dependency.source_id,
                    target_id=dependency.target_id,
                    required=dependency.required,
                    condition=dependency.condition,
                )
                for dependency in dependencies
            ),
        )
        return merged, tuple(spec.id for spec in new_specs)

    @staticmethod
    def _validate_recovery_replan_topology(
        *,
        revised: ProjectExecutionPlan,
        current_plan: ProjectExecutionPlan,
        work_units: dict[str, WorkUnit],
        new_specs: Sequence[PlannedWorkUnit],
    ) -> None:
        recovery_ids = {
            work_unit_id
            for work_unit_id, work_unit in work_units.items()
            if work_unit.state is WorkUnitState.RECOVERY_REQUIRED
        }
        if not recovery_ids or not new_specs:
            return

        new_ids = {spec.id for spec in new_specs}
        old_edges = {
            (item.source_id, item.target_id, item.required)
            for item in current_plan.dependencies
        }
        new_required_edges = {
            (item.source_id, item.target_id)
            for item in revised.dependencies
            if item.required
            and (item.source_id, item.target_id, item.required) not in old_edges
        }

        reversed_edges = sorted(
            (source_id, target_id)
            for source_id, target_id in new_required_edges
            if source_id in recovery_ids and target_id in new_ids
        )
        if reversed_edges:
            rendered = ", ".join(
                f"{source}->{target}" for source, target in reversed_edges
            )
            raise RecoveryPlanTopologyError(
                "Recovery dependency direction is invalid: source_id must "
                "complete before target_id becomes eligible. A new remediation "
                "Work Unit must be upstream of the RECOVERY_REQUIRED Work Unit "
                "(new-remediation -> original-recovery-unit), never downstream "
                f"of it. Invalid edge(s): {rendered}."
            )

        for recovery_id in sorted(recovery_ids):
            touches_new_recovery_work = any(
                source_id in new_ids or target_id in new_ids
                for source_id, target_id in new_required_edges
            )
            if not touches_new_recovery_work:
                continue
            has_upstream_recovery_edge = any(
                source_id in new_ids and target_id == recovery_id
                for source_id, target_id in new_required_edges
            )
            if not has_upstream_recovery_edge:
                raise RecoveryPlanTopologyError(
                    "Recovery plan added new Work Units but did not connect any "
                    "new required prerequisite into RECOVERY_REQUIRED Work Unit "
                    f"'{recovery_id}'. Dependency semantics are prerequisite "
                    "source_id -> dependent target_id."
                )

    @staticmethod
    def _state_summary(
        work_units: dict[str, WorkUnit],
        outputs: dict[str, str],
        output_refs: dict[str, str] | None = None,
    ) -> str:
        refs = output_refs or {}
        lines = []
        for work_unit_id in sorted(work_units):
            work_unit = work_units[work_unit_id]
            result_ref = refs.get(work_unit_id)
            if result_ref:
                output_description = f"authoritative_result_ref={result_ref!r}"
            else:
                output = outputs.get(work_unit_id, "")
                if len(output) > 2000:
                    output = output[:2000] + " [truncated]"
                output_description = f"output={output!r}"
            lines.append(
                f"{work_unit_id}: state={work_unit.state.value}; {output_description}"
            )
        return "\n".join(lines)

    @staticmethod
    def _extract_result_reference(raw_result: object) -> tuple[str | None, bool]:
        if not isinstance(raw_result, dict):
            return None, False
        transport = raw_result.get("result_transport")
        if not isinstance(transport, dict):
            return None, False
        authoritative = transport.get("authoritative") is True
        complete = transport.get("complete") is True
        result_ref = transport.get("result_ref")
        if authoritative and complete and isinstance(result_ref, str) and result_ref.strip():
            return result_ref, True
        return None, False

    @staticmethod
    def _extract_output(raw_result: object) -> str:
        if isinstance(raw_result, dict):
            output = raw_result.get("output")
            if isinstance(output, str):
                return output
        if raw_result is None:
            return ""
        return str(raw_result)
