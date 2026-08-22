from application.evaluate_result import EvaluateResult, EvaluateResultRequest
from application.plan_work import PlanWork
from application.replan_project import ReplanProject, ReplanProjectRequest
from domain.dependency import Dependency
from domain.plan import Plan, PlanStatus, PlanVersion
from domain.project import Project, ProjectId
from domain.result_package import ResultPackage, ResultPackageStatus
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitState


def make_project() -> Project:
    return Project(
        id=ProjectId("project-001"),
        identity="Adaptive AI Orchestrator",
        baseline="baseline-001",
    )


def make_work_unit(
    work_unit_id: str,
    objective: str,
    priority: int = 0,
) -> WorkUnit:
    return WorkUnit(
        id=WorkUnitId(work_unit_id),
        objective=objective,
        priority=priority,
    )


def make_active_plan(work_unit_ids: tuple[str, ...]) -> Plan:
    plan = Plan(
        version=PlanVersion(1),
        baseline="baseline-001",
        work_unit_ids=work_unit_ids,
    )
    plan.activate()
    return plan


def test_evaluate_returned_result_and_replan_preserves_unaffected_work() -> None:
    project = make_project()

    affected = make_work_unit(
        "wu-001",
        "Implement feature A",
        priority=10,
    )
    unaffected = make_work_unit(
        "wu-002",
        "Implement feature B",
        priority=1,
    )

    affected.mark_ready()
    affected.start()
    affected.start_evaluation()

    current_plan = make_active_plan(("wu-001", "wu-002"))

    result_package = ResultPackage(
        task_id="task-001",
        status=ResultPackageStatus.SUCCEEDED,
        result={"tests": "partial"},
        evidence=("tests-pass",),
        discovered_issues=("acceptance-pass-missing",),
        recommendations=("revise-feature-a",),
    )

    evaluation = EvaluateResult().execute(
        EvaluateResultRequest(
            result_package=result_package,
            criteria=("tests-pass", "acceptance-pass"),
            evaluator_id="evaluator-001",
        )
    ).evaluation

    assert evaluation.verdict.value == "ACCEPTED_WITH_CONDITIONS"

    revision = ReplanProject(PlanWork()).execute(
        ReplanProjectRequest(
            project=project,
            current_plan=current_plan,
            work_units=(affected, unaffected),
            dependencies=(),
            trigger="evaluation-returned-conditions",
            affected_work_unit_ids=("wu-001",),
        )
    ).revision

    assert revision.previous_version == 1
    assert revision.new_plan.version.value == 2
    assert revision.new_plan.status is PlanStatus.ACTIVE
    assert revision.affected_work_unit_ids == ("wu-001",)
    assert affected.state is WorkUnitState.EVALUATING
    assert unaffected.state is WorkUnitState.PLANNED
    assert revision.new_plan.work_unit_ids == (
        "wu-001",
        "wu-002",
    )


def test_rejected_result_can_trigger_targeted_replanning() -> None:
    project = make_project()

    affected = make_work_unit(
        "wu-001",
        "Implement feature A",
    )
    unaffected = make_work_unit(
        "wu-002",
        "Implement feature B",
    )

    current_plan = make_active_plan(("wu-001", "wu-002"))

    result_package = ResultPackage(
        task_id="task-001",
        status=ResultPackageStatus.SUCCEEDED,
        result={"output": "invalid"},
        evidence=("runtime-complete",),
    )

    evaluation = EvaluateResult().execute(
        EvaluateResultRequest(
            result_package=result_package,
            criteria=("acceptance-pass",),
            evaluator_id="evaluator-001",
        )
    ).evaluation

    assert evaluation.verdict.value == "RETURNED"

    revision = ReplanProject(PlanWork()).execute(
        ReplanProjectRequest(
            project=project,
            current_plan=current_plan,
            work_units=(affected, unaffected),
            dependencies=(),
            trigger="evaluation-returned",
            affected_work_unit_ids=("wu-001",),
            added_work_units=(
                make_work_unit(
                    "wu-003",
                    "Analyze cause of rejected result",
                ),
            ),
        )
    ).revision

    assert revision.new_plan.version.value == 2
    assert revision.affected_work_unit_ids == ("wu-001",)
    assert revision.new_plan.work_unit_ids == (
        "wu-001",
        "wu-002",
        "wu-003",
    )
    assert "added-work-units:wu-003" in revision.changes


def test_dependency_changes_are_represented_in_revised_plan() -> None:
    project = make_project()

    first = make_work_unit("wu-001", "First step")
    second = make_work_unit("wu-002", "Second step")

    current_plan = make_active_plan(("wu-001", "wu-002"))

    dependency = Dependency(
        source_id="wu-001",
        target_id="wu-002",
        required=True,
    )

    revision = ReplanProject(PlanWork()).execute(
        ReplanProjectRequest(
            project=project,
            current_plan=current_plan,
            work_units=(first, second),
            dependencies=(dependency,),
            trigger="new-dependency-discovered",
        )
    ).revision

    assert revision.new_plan.version.value == 2
    assert revision.new_plan.dependency_ids == (
        "wu-001->wu-002",
    )
    assert "dependencies-changed" in revision.changes
