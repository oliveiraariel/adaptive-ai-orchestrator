from __future__ import annotations

from dataclasses import replace

from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.automatic_learning import AutomaticLearningCycle
from application.continuous_project_orchestration import RunContinuousProjectOrchestration
from application.investigation_strategy import RecoveryStrategyError
from application.persistent_recovery import PersistentRecoveryCoordinator
from application.problem_solving_learning import (
    ProblemSolvingLearningStore,
    ValidatedKnowledgeStore,
)
from application.run_project_orchestration import (
    ProjectOrchestrationRequest,
    ProjectRunStatus,
)
from application.runtime_project_planner import ProjectPlanningRequest
from domain.incident import LearningScope
from domain.learning_analysis import SuccessfulRetestLearningAnalysis
from domain.investigation import (
    CandidateRecoveryPath,
    RecoveryDisposition,
    RecoveryStrategyAnalysis,
)
from domain.project_execution_plan import (
    PlannedDependency,
    PlannedWorkUnit,
    ProjectExecutionPlan,
)
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnitKind
from infrastructure.claim_registry import InMemoryClaimRegistry
from infrastructure.incident_registry import FileIncidentRegistry
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


def _wu(
    unit_id: str,
    *,
    reconciles_work_unit_id: str | None = None,
) -> PlannedWorkUnit:
    return PlannedWorkUnit(
        id=unit_id,
        objective=f"Execute {unit_id}",
        role="worker",
        kind=WorkUnitKind.EXECUTION,
        expected_output=("result",),
        acceptance_criteria=("runtime-completed",),
        parallel_safe=True,
        reconciles_work_unit_id=reconciles_work_unit_id,
    )


class RecoveryPlanner:
    def __init__(
        self,
        initial: ProjectExecutionPlan,
        revised: ProjectExecutionPlan,
    ) -> None:
        self.initial = initial
        self.revised = revised
        self.replan_calls = 0
        self.state_summaries: list[str] = []

    def plan(self, request: ProjectPlanningRequest) -> ProjectExecutionPlan:
        return self.initial

    def replan(
        self,
        request: ProjectPlanningRequest,
        current_plan: ProjectExecutionPlan,
        state_summary: str,
    ) -> ProjectExecutionPlan:
        self.replan_calls += 1
        self.state_summaries.append(state_summary)
        return self.revised


class SequencedRuntime:
    def __init__(self, outputs: dict[str, list[str]]) -> None:
        self.outputs = {key: list(value) for key, value in outputs.items()}
        self.tasks: list[TaskPackage] = []
        self.by_execution: dict[str, TaskPackage] = {}
        self.calls: dict[str, int] = {}

    def submit(self, task: TaskPackage) -> ExecutionReference:
        execution_id = f"execution:{task.work_unit_id}:{len(self.tasks) + 1}"
        self.tasks.append(task)
        self.by_execution[execution_id] = task
        return ExecutionReference(
            id=execution_id,
            runtime="fake",
            external_id=execution_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return AgentRuntimeStatus.COMPLETED

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        task = self.by_execution[execution.id]
        work_unit_id = task.work_unit_id
        index = self.calls.get(work_unit_id, 0)
        self.calls[work_unit_id] = index + 1
        values = self.outputs[work_unit_id]
        output = values[min(index, len(values) - 1)]
        return AgentRuntimeResult(
            execution=replace(execution, status=AgentRuntimeStatus.COMPLETED),
            raw_result={"output": output},
        )

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return replace(execution, status=AgentRuntimeStatus.CANCELLED)


class FakeRecoveryStrategist:
    def __init__(self) -> None:
        self.requests = []

    def analyze(self, request):
        self.requests.append(request)
        return RecoveryStrategyAnalysis(
            failure_class="strategy-exhausted",
            problem_summary=(
                "The original implementation path repeatedly missed the "
                "acceptance contract and needs a prerequisite remediation."
            ),
            previous_path_failures=(
                "direct retry repeated the same incomplete path",
            ),
            candidate_paths=(
                CandidateRecoveryPath(
                    id="remediate-before-retest",
                    title="Remediate before retesting original work",
                    rationale=(
                        "A bounded prerequisite can address the unmet finding "
                        "without replacing the original Work Unit identity."
                    ),
                    novelty="Moves correction into an explicit prerequisite.",
                    suggested_skills=("debugging",),
                    expected_evidence=("accepted remediation", "accepted retest"),
                ),
            ),
            recommended_path_id="remediate-before-retest",
            disposition=RecoveryDisposition.REPLAN_WITH_PREREQUISITE,
            work_graph_guidance=(
                "Add remediation -> original-review, accept remediation, then "
                "retest the original review."
            ),
            human_decision_required=False,
            external_research_required=False,
            confidence=0.9,
        )


class FakeLearningAnalyst:
    def __init__(self) -> None:
        self.requests = []

    def analyze(self, request):
        self.requests.append(request)
        return SuccessfulRetestLearningAnalysis(
            problem_summary=(
                "The first attempt did not satisfy the acceptance contract."
            ),
            root_cause=(
                "The successful retest used the missing verification/correction "
                "identified by the prior returned attempt."
            ),
            solution_summary=(
                "Apply the acceptance feedback, preserve prior valid work, and "
                "retest the same Work Unit."
            ),
            learning_statement=(
                "A successful retest after returned work should preserve the "
                "failed-path evidence and promote only the reusable correction pattern."
            ),
            scope=LearningScope.GENERALIZABLE,
            target_hints=(
                "adaptive:problem-solving",
                "skills:debugging",
                "skills:testing",
            ),
            confidence=0.91,
            should_promote=True,
            evidence_rationale=(
                "The same Work Unit changed from returned to accepted after the "
                "specific correction was applied."
            ),
        )


def test_strategy_exhaustion_reanalyzes_executes_retests_learns_and_closes(tmp_path):
    partial = (
        "Still incomplete.\n"
        "ADAPTIVE_WORK_STATUS: PARTIAL\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: fix the causal defect"
    )
    complete = (
        "Retest accepted after remediation.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    remediation = (
        "Causal defect remediated.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )

    initial = ProjectExecutionPlan(
        summary="original work",
        work_units=(_wu("original-review"),),
    )
    revised = ProjectExecutionPlan(
        summary="recovery prerequisite then original retest",
        work_units=(_wu("original-review"), _wu("remediation")),
        dependencies=(PlannedDependency("remediation", "original-review"),),
    )
    planner = RecoveryPlanner(initial, revised)
    runtime = SequencedRuntime(
        {
            "original-review": [partial, complete],
            "remediation": [remediation],
        }
    )

    registry = FileIncidentRegistry(tmp_path / "incidents")
    provisional = ProblemSolvingLearningStore(tmp_path / "provisional.jsonl")
    validated = ValidatedKnowledgeStore(tmp_path / "validated.jsonl")
    learning = AutomaticLearningCycle(
        registry=registry,
        learning_store=provisional,
        validated_store=validated,
    )
    strategist = FakeRecoveryStrategist()
    coordinator = PersistentRecoveryCoordinator(
        strategist=strategist,
        registry=registry,
        learning_cycle=learning,
    )

    result = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=planner,
        skill_profiles=(),
        persistent_recovery=coordinator,
    ).execute(
        ProjectOrchestrationRequest(
            objective="Resolve the failing acceptance contract completely.",
            orchestration_id="orch-persistent-recovery",
            project_id="project-a",
            max_attempts_per_work_unit=1,
            max_strategies_per_work_unit=1,
            max_replans=1,
            persistent_recovery=True,
            plan=initial,
        )
    )

    assert result.status is ProjectRunStatus.COMPLETED
    assert result.completed_work_unit_ids == ("original-review", "remediation")
    assert planner.replan_calls == 1
    assert len(strategist.requests) == 1
    assert strategist.requests[0].recovery_epoch == 1
    assert "RECOVERY STRATEGIST ANALYSIS" in planner.state_summaries[0]
    assert [task.work_unit_id for task in runtime.tasks] == [
        "original-review",
        "remediation",
        "original-review",
    ]

    incidents = registry.list_all()
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident.status.value == "CLOSED"
    assert incident.project_id == "project-a"
    assert incident.resolution_epoch == 1
    assert incident.attempted_path_ids == ("remediate-before-retest",)
    assert incident.validation_refs
    assert incident.fix_summary
    assert incident.learning_scope.value == "ARCHITECTURAL"
    assert set(incident.dissemination_completed) == set(
        incident.dissemination_targets
    )
    assert incident.consistency_check_passed is True

    report = coordinator.stop_report(incident.id)
    assert report["status"] == "CLOSED"
    assert report["problem"]
    assert report["validation_refs"]
    assert validated.path.is_file()
    assert provisional.path.is_file()


def test_accepted_corrective_child_can_formally_reconcile_original_without_rerun(tmp_path):
    partial = (
        "Original work returned.\n"
        "ADAPTIVE_WORK_STATUS: PARTIAL\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: exact corrective finding"
    )
    corrective = (
        "Exact corrective finding fully satisfied.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )

    initial = ProjectExecutionPlan(
        summary="returned original",
        work_units=(_wu("original"),),
    )
    revised = ProjectExecutionPlan(
        summary="corrective child reconciles original",
        work_units=(
            _wu("original"),
            _wu(
                "corrective",
                reconciles_work_unit_id="original",
            ),
        ),
        dependencies=(PlannedDependency("corrective", "original"),),
    )
    planner = RecoveryPlanner(initial, revised)
    runtime = SequencedRuntime(
        {
            "original": [partial],
            "corrective": [corrective],
        }
    )

    registry = FileIncidentRegistry(tmp_path / "incidents-reconcile")
    validated = ValidatedKnowledgeStore(tmp_path / "validated-reconcile.jsonl")
    coordinator = PersistentRecoveryCoordinator(
        strategist=FakeRecoveryStrategist(),
        registry=registry,
        learning_cycle=AutomaticLearningCycle(
            registry=registry,
            learning_store=ProblemSolvingLearningStore(
                tmp_path / "provisional-reconcile.jsonl"
            ),
            validated_store=validated,
        ),
    )

    result = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=planner,
        skill_profiles=(),
        persistent_recovery=coordinator,
    ).execute(
        ProjectOrchestrationRequest(
            objective="Resolve returned work through exact corrective evidence.",
            orchestration_id="orch-reconcile-child",
            project_id="project-a",
            max_attempts_per_work_unit=1,
            max_strategies_per_work_unit=1,
            max_replans=1,
            persistent_recovery=True,
            plan=initial,
        )
    )

    assert result.status is ProjectRunStatus.COMPLETED
    assert [task.work_unit_id for task in runtime.tasks] == [
        "original",
        "corrective",
    ]
    reconciled = [
        record
        for record in result.records
        if record.work_unit_id == "original"
        and record.reason == "reconciled-by:corrective"
    ]
    assert len(reconciled) == 1
    assert reconciled[0].verdict == "ACCEPTED"
    incident = registry.list_all()[0]
    assert incident.status.value == "CLOSED"
    assert incident.validation_refs
    assert validated.path.is_file()


def test_successful_ordinary_revision_retest_triggers_learning_without_strategy_exhaustion(tmp_path):
    partial = (
        "One acceptance item remains.\n"
        "ADAPTIVE_WORK_STATUS: PARTIAL\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: add the missing verification"
    )
    complete = (
        "Missing verification added; retest accepted.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    plan = ProjectExecutionPlan(
        summary="ordinary revision retest",
        work_units=(_wu("revision-worker"),),
    )
    runtime = SequencedRuntime({"revision-worker": [partial, complete]})
    planner = RecoveryPlanner(plan, plan)
    registry = FileIncidentRegistry(tmp_path / "incidents-ordinary-retest")
    validated = ValidatedKnowledgeStore(tmp_path / "validated-ordinary-retest.jsonl")
    analyst = FakeLearningAnalyst()
    strategist = FakeRecoveryStrategist()
    coordinator = PersistentRecoveryCoordinator(
        strategist=strategist,
        registry=registry,
        learning_analyst=analyst,
        learning_cycle=AutomaticLearningCycle(
            registry=registry,
            learning_store=ProblemSolvingLearningStore(
                tmp_path / "provisional-ordinary-retest.jsonl"
            ),
            validated_store=validated,
        ),
    )

    result = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=planner,
        skill_profiles=(),
        persistent_recovery=coordinator,
    ).execute(
        ProjectOrchestrationRequest(
            objective="Complete ordinary revision and learn from the retest.",
            orchestration_id="orch-ordinary-retest",
            project_id="project-a",
            max_attempts_per_work_unit=2,
            max_strategies_per_work_unit=1,
            max_replans=0,
            persistent_recovery=True,
            plan=plan,
        )
    )

    assert result.status is ProjectRunStatus.COMPLETED
    assert strategist.requests == []
    assert len(analyst.requests) == 1
    assert analyst.requests[0].previous_attempts
    assert [task.work_unit_id for task in runtime.tasks] == [
        "revision-worker",
        "revision-worker",
    ]

    incident = registry.list_all()[0]
    assert incident.category == "successful-retest"
    assert incident.status.value == "CLOSED"
    assert incident.resolution_epoch == 0
    assert incident.learning_scope is LearningScope.GENERALIZABLE
    assert "skills:testing" in incident.dissemination_targets
    assert incident.consistency_check_passed is True

    report = coordinator.stop_report(incident.id)
    assert report["closed"] is True
    assert "successful retest" in report["what_was_learned"].lower()
    assert report["learning_analysis_confidence"] == 0.91
    assert report["incorporated_in"]
    assert validated.path.is_file()



class FailingRecoveryStrategist:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, request):
        self.calls += 1
        raise RecoveryStrategyError("temporary strategist result was not publishable")


def test_noop_recovery_replan_yields_nonterminal_instead_of_livelocking(tmp_path):
    partial = (
        "Still incomplete.\n"
        "ADAPTIVE_WORK_STATUS: PARTIAL\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: missing causal prerequisite"
    )
    initial = ProjectExecutionPlan(
        summary="original recovery target",
        work_units=(_wu("original"),),
    )
    # Returning the same graph used to count as a successful replan and could
    # spin indefinitely under max_recovery_epochs=0.
    planner = RecoveryPlanner(initial, initial)
    runtime = SequencedRuntime({"original": [partial]})
    registry = FileIncidentRegistry(tmp_path / "incidents-noop")
    coordinator = PersistentRecoveryCoordinator(
        strategist=FakeRecoveryStrategist(),
        registry=registry,
    )
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)

    result = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=planner,
        skill_profiles=(),
        persistent_recovery=coordinator,
        checkpoint_store=store,
    ).execute(
        ProjectOrchestrationRequest(
            objective="Recover without repeating a no-op graph.",
            orchestration_id="orch-noop-replan",
            project_id="project-a",
            max_attempts_per_work_unit=1,
            max_strategies_per_work_unit=1,
            max_replans=1,
            persistent_recovery=True,
            max_recovery_epochs=0,
            plan=initial,
        )
    )

    assert result.status is ProjectRunStatus.RECOVERY_REQUIRED
    assert result.recovery_required_work_unit_ids == ("original",)
    assert planner.replan_calls == 1
    checkpoint = store.load("orch-noop-replan")
    assert checkpoint is not None
    assert checkpoint["terminal"] is False
    assert checkpoint["pending_replan"] is True
    assert checkpoint["work_unit_states"]["original"] == "RECOVERY_REQUIRED"
    assert "no material structural progress" in checkpoint["replan_feedback"]


def test_strategist_transient_failure_yields_nonterminal_recovery(tmp_path):
    partial = (
        "Still incomplete.\n"
        "ADAPTIVE_WORK_STATUS: PARTIAL\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: investigate missing evidence"
    )
    initial = ProjectExecutionPlan(
        summary="strategist transient failure",
        work_units=(_wu("original"),),
    )
    planner = RecoveryPlanner(initial, initial)
    runtime = SequencedRuntime({"original": [partial]})
    registry = FileIncidentRegistry(tmp_path / "incidents-strategist-failure")
    strategist = FailingRecoveryStrategist()
    coordinator = PersistentRecoveryCoordinator(
        strategist=strategist,
        registry=registry,
    )
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)

    result = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=planner,
        skill_profiles=(),
        persistent_recovery=coordinator,
        checkpoint_store=store,
    ).execute(
        ProjectOrchestrationRequest(
            objective="Preserve recovery through strategist provider failure.",
            orchestration_id="orch-strategist-failure",
            project_id="project-a",
            max_attempts_per_work_unit=1,
            max_strategies_per_work_unit=1,
            max_replans=1,
            persistent_recovery=True,
            max_recovery_epochs=0,
            plan=initial,
        )
    )

    assert result.status is ProjectRunStatus.RECOVERY_REQUIRED
    assert strategist.calls == 1
    assert planner.replan_calls == 0
    checkpoint = store.load("orch-strategist-failure")
    assert checkpoint is not None
    assert checkpoint["terminal"] is False
    assert checkpoint["pending_replan"] is True
    assert checkpoint["work_unit_states"]["original"] == "RECOVERY_REQUIRED"
    assert "Recovery Strategist could not complete" in checkpoint["replan_feedback"]
