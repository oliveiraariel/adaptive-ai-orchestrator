from application.plan_work import PlanWork, PlanWorkRequest
from domain.dependency import Dependency
from domain.plan import PlanStatus
from domain.project import Project, ProjectId
from domain.work_unit import WorkUnit, WorkUnitId


def make_project() -> Project:
    return Project(
        id=ProjectId("project-001"),
        identity="Adaptive AI Orchestrator",
        baseline="baseline-001",
    )


def make_work_unit(work_unit_id: str, priority: int) -> WorkUnit:
    return WorkUnit(
        id=WorkUnitId(work_unit_id),
        objective=f"Objective {work_unit_id}",
        priority=priority,
    )


def test_planning_vertical_slice_produces_ready_and_blocked_work() -> None:
    project = make_project()

    prerequisite = make_work_unit("wu-prerequisite", priority=5)
    dependent = make_work_unit("wu-dependent", priority=10)
    independent = make_work_unit("wu-independent", priority=1)

    dependency = Dependency(
        source_id=prerequisite.id.value,
        target_id=dependent.id.value,
        required=True,
    )

    result = PlanWork().execute(
        PlanWorkRequest(
            project=project,
            work_units=[dependent, prerequisite, independent],
            dependencies=[dependency],
            version=1,
        )
    )

    assert result.plan.status is PlanStatus.ACTIVE

    assert result.ready_work_unit_ids == (
        "wu-prerequisite",
        "wu-independent",
    )

    assert result.blocked_work_unit_ids == (
        "wu-dependent",
    )

    assert result.plan.work_unit_ids == (
        "wu-dependent",
        "wu-prerequisite",
        "wu-independent",
    )

    assert result.plan.dependency_ids == (
        "wu-prerequisite->wu-dependent",
    )


def test_planning_vertical_slice_unblocks_dependent_after_dependency_satisfaction() -> None:
    project = make_project()

    prerequisite = make_work_unit("wu-prerequisite", priority=5)
    dependent = make_work_unit("wu-dependent", priority=10)

    dependency = Dependency(
        source_id=prerequisite.id.value,
        target_id=dependent.id.value,
        required=True,
    )

    first_plan = PlanWork().execute(
        PlanWorkRequest(
            project=project,
            work_units=[prerequisite, dependent],
            dependencies=[dependency],
        )
    )

    assert first_plan.ready_work_unit_ids == ("wu-prerequisite",)
    assert first_plan.blocked_work_unit_ids == ("wu-dependent",)

    dependency.satisfy()

    second_plan = PlanWork().execute(
        PlanWorkRequest(
            project=project,
            work_units=[prerequisite, dependent],
            dependencies=[dependency],
            version=2,
        )
    )

    assert second_plan.plan.version.value == 2
    assert second_plan.ready_work_unit_ids == (
        "wu-dependent",
        "wu-prerequisite",
    )
    assert second_plan.blocked_work_unit_ids == ()
