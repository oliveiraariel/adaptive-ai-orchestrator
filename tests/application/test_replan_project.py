from application.plan_work import PlanWork
from application.replan_project import ReplanProject, ReplanProjectRequest
from domain.dependency import Dependency
from domain.plan import Plan, PlanStatus, PlanVersion
from domain.project import Project, ProjectId
from domain.work_unit import WorkUnit, WorkUnitId


def make_project() -> Project:
    return Project(
        id=ProjectId("project-001"),
        identity="Adaptive AI Orchestrator",
        baseline="baseline-001",
    )


def make_work_unit(work_unit_id: str, priority: int = 0) -> WorkUnit:
    return WorkUnit(
        id=WorkUnitId(work_unit_id),
        objective=f"Objective {work_unit_id}",
        priority=priority,
    )


def make_current_plan(work_unit_ids: tuple[str, ...]) -> Plan:
    plan = Plan(
        version=PlanVersion(1),
        baseline="baseline-001",
        work_unit_ids=work_unit_ids,
    )
    plan.activate()
    return plan


def test_replan_increments_version_and_preserves_unaffected_work() -> None:
    project = make_project()
    first = make_work_unit("wu-001", priority=5)
    second = make_work_unit("wu-002", priority=1)
    current_plan = make_current_plan(("wu-001", "wu-002"))

    result = ReplanProject(PlanWork()).execute(
        ReplanProjectRequest(
            project=project,
            current_plan=current_plan,
            work_units=(first, second),
            dependencies=(),
            trigger="new-project-information",
        )
    )

    revision = result.revision

    assert revision.previous_version == 1
    assert revision.new_plan.version.value == 2
    assert revision.new_plan.status is PlanStatus.ACTIVE
    assert revision.new_plan.work_unit_ids == ("wu-001", "wu-002")
    assert "plan-revalidated" in revision.changes


def test_replan_can_add_work_unit() -> None:
    project = make_project()
    existing = make_work_unit("wu-001")
    added = make_work_unit("wu-002")
    current_plan = make_current_plan(("wu-001",))

    result = ReplanProject(PlanWork()).execute(
        ReplanProjectRequest(
            project=project,
            current_plan=current_plan,
            work_units=(existing,),
            dependencies=(),
            trigger="discovered-new-work",
            added_work_units=(added,),
        )
    )

    assert result.revision.new_plan.version.value == 2
    assert result.revision.new_plan.work_unit_ids == ("wu-001", "wu-002")
    assert "added-work-units:wu-002" in result.revision.changes


def test_replan_can_remove_work_unit() -> None:
    project = make_project()
    first = make_work_unit("wu-001")
    second = make_work_unit("wu-002")
    current_plan = make_current_plan(("wu-001", "wu-002"))

    result = ReplanProject(PlanWork()).execute(
        ReplanProjectRequest(
            project=project,
            current_plan=current_plan,
            work_units=(first, second),
            dependencies=(),
            trigger="requirement-removed",
            removed_work_unit_ids=("wu-002",),
        )
    )

    assert result.revision.new_plan.work_unit_ids == ("wu-001",)
    assert "removed-work-units:wu-002" in result.revision.changes


def test_replan_reopens_affected_completed_work() -> None:
    project = make_project()
    work_unit = make_work_unit("wu-001")
    work_unit.mark_ready()
    work_unit.start()
    work_unit.start_evaluation()
    work_unit.complete()

    current_plan = make_current_plan(("wu-001",))

    result = ReplanProject(PlanWork()).execute(
        ReplanProjectRequest(
            project=project,
            current_plan=current_plan,
            work_units=(work_unit,),
            dependencies=(),
            trigger="later-result-contradicts-work",
            affected_work_unit_ids=("wu-001",),
        )
    )

    assert result.revision.affected_work_unit_ids == ("wu-001",)
    assert work_unit.state.value == "REOPENED"


def test_replan_keeps_unaffected_dependency_validity() -> None:
    project = make_project()
    prerequisite = make_work_unit("wu-001")
    dependent = make_work_unit("wu-002")

    dependency = Dependency(
        source_id="wu-001",
        target_id="wu-002",
        required=True,
    )

    current_plan = make_current_plan(("wu-001", "wu-002"))

    result = ReplanProject(PlanWork()).execute(
        ReplanProjectRequest(
            project=project,
            current_plan=current_plan,
            work_units=(prerequisite, dependent),
            dependencies=(dependency,),
            trigger="dependency-reassessment",
        )
    )

    assert result.revision.new_plan.dependency_ids == (
        "wu-001->wu-002",
    )
    assert result.revision.new_plan.version.value == 2
